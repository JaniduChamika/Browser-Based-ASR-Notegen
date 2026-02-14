# asr_engine.py
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import numpy as np
import webrtcvad
import queue
import threading
import time
import re
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from pyctcdecode import build_ctcdecoder
from config import *


class AsrEngine:
    def __init__(self, output_queue):
        self.output_queue = output_queue
        self.transcription_queue = queue.Queue()
        self.vad = webrtcvad.Vad(VAD_MODE)
        self.processor = None
        self.model = None
        self.decoder = None # NEW: CTC Decoder

        self.input_buffer = []
        self.audio_buffer = []
        
        # NEW: Buffer to hold audio just BEFORE speech starts (prevents cutting start of words)
        self.pre_speech_buffer = [] 
        
        self.silence_counter = 0
        self.is_speaking = False
        self.stop_event = threading.Event()

    def load_models(self):
        print("⏳ [Engine] Loading Wav2Vec2 Sinhala Model...")
        try:
            model_id = "janiduchamika/wav2vec2-xls-r-300m-sinhala-politics-185k-5h"
            self.processor = Wav2Vec2Processor.from_pretrained(model_id)
            self.model = Wav2Vec2ForCTC.from_pretrained(model_id)
            self.model.to("cpu")
            self.model.eval()
            print(f"✅ [Engine] Wav2Vec2 model loaded successfully.")

            # --- NEW: Load N-gram Decoder ---
            if os.path.exists(NGRAM_MODEL_PATH):
                print(f"⏳ [Engine] Loading N-gram Model ({NGRAM_MODEL_PATH})...")
                vocab = self.processor.tokenizer.get_vocab()
                sorted_vocab = [k for k, v in sorted(vocab.items(), key=lambda item: item[1])]
                
                self.decoder = build_ctcdecoder(
                    labels=sorted_vocab,
                    kenlm_model_path=NGRAM_MODEL_PATH,
                    alpha=LM_ALPHA,
                    beta=LM_BETA,
                )
                print(f"✅ [Engine] Decoder with N-gram LM loaded successfully.")
            else:
                print(f"⚠️ [Engine] N-gram model not found at {NGRAM_MODEL_PATH}. Using standard greedy decoding.")
            
            return True
        except Exception as e:
            print(f"❌ [Engine] Error loading model: {e}")
            return False

    def clean_text(self, text):
        """
        Aggressively cleans model hallucinations and repetitive loops.
        """
        if not text: return None

        # 1. Remove severe character repetitions (e.g. "ත්ත්ත්" -> "")
        text = re.sub(r'(.)\1{2,}', '', text)

        # 2. Fix stuttering/looping words (e.g. "වස් වස්" -> "වස්")
        text = re.sub(r'(\S+)(?:\s+\1)+', r'\1', text)
        text = re.sub(r'(\S+)(?:\s+\1)+', r'\1', text)

        # 3. Standard whitespace cleanup
        text = re.sub(r"\s+", " ", text).strip()
        
        # 4. Filter out short garbage
        if len(text) < 2:
            return None

        return text

    def process_stream(self, audio_chunk_float):
        self.input_buffer.extend(audio_chunk_float)
        while len(self.input_buffer) >= FRAME_SIZE:
            frame_float = np.array(self.input_buffer[:FRAME_SIZE], dtype=np.float32)
            self.input_buffer = self.input_buffer[FRAME_SIZE:]
            self._process_frame(frame_float)

    def _process_frame(self, frame_float):
        # 1. Volume Analysis
        volume = np.sqrt(np.mean(frame_float**2))
        is_low_volume = volume < MIN_VOLUME_THRESHOLD

        # 2. VAD Check
        # Even if volume is low, we treat it as silence, but we DON'T discard it immediately
        # if we are buffering pre-speech context.
        is_speech = False
        
        if not is_low_volume:
            audio_int16 = np.clip(frame_float * 32767, -32768, 32767).astype(np.int16)
            try:
                is_speech = self.vad.is_speech(audio_int16.tobytes(), SAMPLE_RATE)
            except:
                is_speech = False

        # --- LOGIC CONTROL ---
        
        if is_speech:
            if not self.is_speaking:
                # SPEECH DETECTED (Start of Sentence)
                self.is_speaking = True
                print(f"🗣️ [Start] (Vol: {volume:.3f})")
                
                # CRITICAL FIX: Prepend the "Pre-Speech Buffer" to capture the start of the word
                # that might have happened while VAD was deciding.
                if self.pre_speech_buffer:
                    self.audio_buffer.extend(self.pre_speech_buffer)
                    self.pre_speech_buffer = []

            self.audio_buffer.extend(frame_float)
            self.silence_counter = 0
            
        else:
            # SILENCE DETECTED
            if self.is_speaking:
                # We are inside a sentence, counting silence
                self.silence_counter += len(frame_float)
                self.audio_buffer.extend(frame_float)
                
                # --- Smart Cut Logic ---
                SOFT_LIMIT_FRAMES = int(2.5 * SAMPLE_RATE)
                SHORT_PAUSE_FRAMES = int(0.2 * SAMPLE_RATE)

                # Case A: Long Silence (End of Sentence)
                if self.silence_counter >= MAX_SILENCE_FRAMES:
                    self._commit_audio(retain_overlap=False)
                    return

                # Case B: Smart Cut (Buffer Long + Short Pause Found)
                if len(self.audio_buffer) > SOFT_LIMIT_FRAMES and self.silence_counter >= SHORT_PAUSE_FRAMES:
                    print("✂️ [Smart Cut] Found pause between words, cutting now...")
                    self._commit_audio(retain_overlap=False)
                    return
            else:
                # We are in pure silence (not speaking). 
                # Keep a small rolling buffer of silence (e.g., 0.5s) to catch fade-ins.
                self.pre_speech_buffer.extend(frame_float)
                
                # Limit Pre-Speech Buffer to ~0.5 seconds (approx 16 frames)
                MAX_PRE_SPEECH = 16 * FRAME_SIZE
                if len(self.pre_speech_buffer) > MAX_PRE_SPEECH:
                    self.pre_speech_buffer = self.pre_speech_buffer[-MAX_PRE_SPEECH:]

        # --- FAILSAFE: HARD CUT ---
        if len(self.audio_buffer) >= MAX_SPEECH_FRAMES:
            print("✂️ [Forced Cut] Audio too long (no silence), forcing split...")
            self._commit_audio(retain_overlap=True)
            self.is_speaking = True 

    def _commit_audio(self, retain_overlap=False):
        """Helper to send audio to queue and reset buffer"""
        
        # Validation: Don't send tiny chunks unless we forced a cut (continuation)
        # If we forced a cut, we accept ANY length because it's part of a stream.
        min_length = MIN_SPEECH_FRAMES
        if retain_overlap: 
            min_length = int(0.1 * SAMPLE_RATE) # Lower threshold for continuous stream

        if len(self.audio_buffer) >= min_length:
            speech_audio = np.array(self.audio_buffer, dtype=np.float32)
            self.transcription_queue.put(speech_audio.copy())
        
        # Overlap Logic
        if retain_overlap and len(self.audio_buffer) > OVERLAP_FRAMES:
            self.audio_buffer = self.audio_buffer[-OVERLAP_FRAMES:]
        else:
            self.audio_buffer = []
            self.is_speaking = False
            # Important: Clear pre-speech buffer so we don't duplicate old silence
            self.pre_speech_buffer = []

        self.silence_counter = 0

    def transcription_worker(self):
        if self.model is None: self.load_models()

        while not self.stop_event.is_set():
            try:
                audio = self.transcription_queue.get(timeout=1)
                self.output_queue.put(("status", "Transcribing..."))
                
                start_time = time.time()
                input_values = self.processor(audio, sampling_rate=16000, return_tensors="pt", padding=True).input_values
                with torch.no_grad():
                    logits = self.model(input_values).logits
                
                # --- NEW: N-gram Decoding ---
                if self.decoder:
                    # pyctcdecode expects logits as numpy array [time_steps, vocab_size]
                    logits_np = logits.cpu().numpy()[0] 
                    full_text = self.decoder.decode(logits_np, beam_width=BEAM_WIDTH)
                else:
                    # Fallback to standard greedy decoding
                    predicted_ids = torch.argmax(logits, dim=-1)
                    full_text = self.processor.batch_decode(predicted_ids)[0]
                
                full_text = self.clean_text(full_text)
                
                duration = time.time() - start_time
                if full_text:
                    print(f"📝 Text ({duration:.2f}s): {full_text}")
                    self.output_queue.put(("text", full_text + " "))
                
                self.output_queue.put(("status", "Listening..."))

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker Error: {e}")
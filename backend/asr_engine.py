# asr_engine.py
import numpy as np
import torch
from transformers import pipeline
import webrtcvad
import queue
import threading
import time
import re
from config import *

class AsrEngine:
    def __init__(self, output_queue):
        self.output_queue = output_queue
        self.transcription_queue = queue.Queue()
        
        # VAD Setup
        self.vad = webrtcvad.Vad(VAD_MODE)
        
        self.pipe = None
        self.input_buffer = [] 
        self.audio_buffer = []
        self.silence_counter = 0
        self.is_speaking = False
        self.stop_event = threading.Event()

    def load_models(self):
        print("⏳ [Engine] Loading Whisper Model...")
        try:
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model="Lingalingeswaran/whisper-small-sinhala_v3",
                device=0 if DEVICE == "cuda" else -1,
                torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
            )
            print("✅ [Engine] Model Loaded Successfully.")
            return True
        except Exception as e:
            print(f"❌ [Engine] Error loading model: {e}")
            return False

    def clean_hallucinations(self, text):
        """Filters out repetitive garbage."""
        if not text: return None
        
        # 1. Remove character repetition (e.g., "ත්ත්ත්")
        text = re.sub(r'(.)\1{3,}', r'', text)

        # 2. Check for "Looping"
        if len(text) > 5:
            unique_chars = set(text)
            if len(unique_chars) < 3: return None
        
        text = text.strip()
        if len(text) == 0: return None
        return text

    def process_stream(self, audio_chunk_float):
        """Buffer and process audio in 30ms frames."""
        self.input_buffer.extend(audio_chunk_float)
        
        while len(self.input_buffer) >= FRAME_SIZE:
            frame_float = np.array(self.input_buffer[:FRAME_SIZE], dtype=np.float32)
            self.input_buffer = self.input_buffer[FRAME_SIZE:]
            self._process_frame(frame_float)

    def _process_frame(self, frame_float):
        # --- 1. NOISE GATE CHECK ---
        # Calculate "RMS" (Root Mean Square) volume
        volume = np.sqrt(np.mean(frame_float**2))
        
        # Default: Assume it's NOT speech
        is_speech = False

        # Only run VAD if the volume is loud enough
        if volume > MIN_VOLUME_THRESHOLD:
            audio_int16 = np.clip(frame_float * 32767, -32768, 32767).astype(np.int16)
            try:
                is_speech = self.vad.is_speech(audio_int16.tobytes(), SAMPLE_RATE)
            except:
                is_speech = False
        
        # --- 2. LOGIC TO HANDLE SPEECH/SILENCE ---
        if is_speech:
            if not self.is_speaking:
                self.is_speaking = True
                print(f"🗣️ [Started] (Vol: {volume:.4f})")
            
            self.audio_buffer.extend(frame_float)
            self.silence_counter = 0
        else:
            if self.is_speaking:
                # We are in a silence gap inside a sentence
                self.silence_counter += len(frame_float)
                self.audio_buffer.extend(frame_float)
                
                # If silence is too long, cut the sentence
                if self.silence_counter >= MAX_SILENCE_FRAMES:
                    print("🤫 [Ended] Processing...")
                    
                    if len(self.audio_buffer) >= MIN_SPEECH_FRAMES:
                        speech_audio = np.array(self.audio_buffer, dtype=np.float32)
                        self.transcription_queue.put(speech_audio.copy())
                    else:
                        print("   (Ignored: Too short)")
                    
                    self.audio_buffer = []
                    self.silence_counter = 0
                    self.is_speaking = False

    def transcribe_audio(self, audio_chunk):
        try:
            result = self.pipe(
                audio_chunk, 
                generate_kwargs={
                    "language": "si", 
                    "repetition_penalty": 1.3,
                    "no_repeat_ngram_size": 0
                }
            )
            return self.clean_hallucinations(result["text"].strip())
        except Exception as e:
            print(f"❌ Inference Error: {e}")
            return None

    def transcription_worker(self):
        if self.pipe is None: self.load_models()

        while not self.stop_event.is_set():
            try:
                audio = self.transcription_queue.get(timeout=1)
                if audio is not None:
                    self.output_queue.put(("status", "Transcribing..."))
                    
                    text = self.transcribe_audio(audio)
                    
                    if text:
                        print(f"📝 Result: {text}")
                        self.output_queue.put(("text", text + " "))
                        self.output_queue.put(("status", "Listening..."))
                    else:
                        # print(f"🗑️ Discarded hallucination.")
                        self.output_queue.put(("status", "Listening..."))

            except queue.Empty:
                continue
import os

# Keep your CPU force if needed, though usually better to let Torch decide
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import numpy as np
import webrtcvad
import queue
import threading
import time
import re
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from config import *


class AsrEngine:
    def __init__(self, output_queue):
        self.output_queue = output_queue
        self.transcription_queue = queue.Queue()

        # VAD Setup (Unchanged)
        self.vad = webrtcvad.Vad(VAD_MODE)

        self.processor = None
        self.model = None

        self.input_buffer = []
        self.audio_buffer = []
        self.silence_counter = 0
        self.is_speaking = False
        self.stop_event = threading.Event()

    def load_models(self):
        print("⏳ [Engine] Loading Wav2Vec2 Sinhala Model...")
        try:
            # SUGGESTION: Use a robust Sinhala Wav2Vec2 model from HuggingFace
            # Example: "facebook/wav2vec2-large-xlsr-53" fine-tuned for Sinhala
            # You might need to find a specific fine-tuned ID, e.g.:
            # model_id = "kavimal/wav2vec2-large-xlsr-sinhala" (Hypothetical example, check HF Hub)
            # For this code, I will use a generic placeholder you must update:
            model_id = "janiduchamika/wav2vec2-xls-r-300m-sinhala-general-185k"

            self.processor = Wav2Vec2Processor.from_pretrained(model_id)
            self.model = Wav2Vec2ForCTC.from_pretrained(model_id)

            # Optimization for CPU
            self.model.to("cpu")
            self.model.eval()  # Set to evaluation mode

            print(f"✅ [Engine] Wav2Vec2 model loaded successfully.")
            return True
        except Exception as e:
            print(f"❌ [Engine] Error loading model: {e}")
            return False

    def clean_text(self, text):
        if not text:
            return None
        # Basic cleanup
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def process_stream(self, audio_chunk_float):
        # (This entire function remains UNCHANGED from your original code)
        self.input_buffer.extend(audio_chunk_float)

        while len(self.input_buffer) >= FRAME_SIZE:
            frame_float = np.array(self.input_buffer[:FRAME_SIZE], dtype=np.float32)
            self.input_buffer = self.input_buffer[FRAME_SIZE:]
            self._process_frame(frame_float)

    def _process_frame(self, frame_float):
        # (This entire function remains UNCHANGED from your original code)
        # Your VAD logic is solid and works for any ASR model.
        volume = np.sqrt(np.mean(frame_float**2))

        if volume < MIN_VOLUME_THRESHOLD and not self.is_speaking:
            return

        audio_int16 = np.clip(frame_float * 32767, -32768, 32767).astype(np.int16)
        try:
            is_speech = self.vad.is_speech(audio_int16.tobytes(), SAMPLE_RATE)
        except:
            is_speech = False

        if is_speech:
            if not self.is_speaking:
                self.is_speaking = True
                print(f"🗣️ [Speech Start] (Vol: {volume:.3f})")

            self.audio_buffer.extend(frame_float)
            self.silence_counter = 0
        else:
            if self.is_speaking:
                self.silence_counter += len(frame_float)
                self.audio_buffer.extend(frame_float)

                if self.silence_counter >= MAX_SILENCE_FRAMES:
                    if len(self.audio_buffer) >= MIN_SPEECH_FRAMES:
                        print("✅ [Speech End] Processing...")
                        speech_audio = np.array(self.audio_buffer, dtype=np.float32)
                        self.transcription_queue.put(speech_audio.copy())
                    else:
                        print("❌ [Ignored] Too short")

                    self.audio_buffer = []
                    self.silence_counter = 0
                    self.is_speaking = False

    def transcription_worker(self):
        if self.model is None:
            self.load_models()

        while not self.stop_event.is_set():
            try:
                audio = self.transcription_queue.get(timeout=1)
                self.output_queue.put(("status", "Transcribing..."))

                start_time = time.time()

                # --- NEW WAV2VEC2 INFERENCE LOGIC ---

                # 1. Process inputs
                # We assume audio is already 16kHz because of config.py settings
                input_values = self.processor(
                    audio, sampling_rate=16000, return_tensors="pt", padding=True
                ).input_values

                # 2. Inference (No Gradients needed)
                with torch.no_grad():
                    logits = self.model(input_values).logits

                # 3. Decode
                # Take the argmax (highest probability) for each time step
                predicted_ids = torch.argmax(logits, dim=-1)

                # Convert IDs back to String
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

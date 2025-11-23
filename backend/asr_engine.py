import os
# Force CPU mode to bypass the "Missing DLL" / "No Device" errors
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import numpy as np
import webrtcvad
import queue
import threading
import time
import re
from faster_whisper import WhisperModel
from config import *

class AsrEngine:
    def __init__(self, output_queue):
        self.output_queue = output_queue
        self.transcription_queue = queue.Queue()
        
        # VAD Setup
        self.vad = webrtcvad.Vad(VAD_MODE)
        
        self.model = None
        self.input_buffer = [] 
        self.audio_buffer = []
        self.silence_counter = 0
        self.is_speaking = False
        self.stop_event = threading.Event()

    def load_models(self):
        print("⏳ [Engine] Loading Custom Sinhala Model (CPU Mode)...")
        try:
            # Your specific custom model
            model_id = "janiduchamika/faster-whisper-small-sinhala-ct2-float16"
            
            # CRITICAL SETTINGS FOR CPU:
            # 1. device="cpu": Runs on processor (fixes "No CUDA device" error)
            # 2. compute_type="int8": Makes it run 4x faster on CPU
            self.model = WhisperModel(model_id, device="cpu", compute_type="int8")
            
            print(f"✅ [Engine] Custom model loaded successfully.")
            return True
        except Exception as e:
            print(f"❌ [Engine] Error loading model: {e}")
            return False

    def clean_text(self, text):
        if not text: return None
        # Remove repetitive garbage like "තතතත"
        text = re.sub(r'(.)\1{3,}', r'', text)
        return text.strip() if len(text) > 1 else None

    def process_stream(self, audio_chunk_float):
        self.input_buffer.extend(audio_chunk_float)
        
        while len(self.input_buffer) >= FRAME_SIZE:
            frame_float = np.array(self.input_buffer[:FRAME_SIZE], dtype=np.float32)
            self.input_buffer = self.input_buffer[FRAME_SIZE:]
            self._process_frame(frame_float)

    def _process_frame(self, frame_float):
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
        if self.model is None: self.load_models()

        while not self.stop_event.is_set():
            try:
                audio = self.transcription_queue.get(timeout=1)
                self.output_queue.put(("status", "Transcribing..."))
                
                start_time = time.time()
                
                # Transcribe using the custom model
                segments, _ = self.model.transcribe(
                    audio, 
                    language="si", 
                    beam_size=5,
                    vad_filter=True 
                )
                
                full_text = " ".join([s.text for s in segments])
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
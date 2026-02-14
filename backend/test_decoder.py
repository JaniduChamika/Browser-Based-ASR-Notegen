import os
import torch
import numpy as np
from asr_engine import AsrEngine
from config import *

def test_decoder():
    print("Testing AsrEngine with N-gram Decoder...")
    
    # Mock Queue
    import queue
    q = queue.Queue()
    
    engine = AsrEngine(q)
    
    # 1. Test Loading
    print("\n--- 1. Testing Model Loading ---")
    success = engine.load_models()
    if not success:
        print("❌ Model loading failed.")
        return
    
    if engine.decoder:
        print("✅ Decoder loaded successfully.")
    else:
        print("⚠️ Decoder NOT loaded (Check if .binary file exists).")
        return

    # 2. Test Inference (Mock Audio)
    print("\n--- 2. Testing Inference (Mock) ---")
    
    # Create dummy audio (1 second of silence/noise)
    dummy_audio = np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)
    
    # We need to process it to get logits manually since transcrption_worker loops
    print("Running forward pass...")
    input_values = engine.processor(dummy_audio, sampling_rate=16000, return_tensors="pt", padding=True).input_values
    with torch.no_grad():
        logits = engine.model(input_values).logits
    
    logits_np = logits.cpu().numpy()[0]
    
    print("Decoding...")
    text = engine.decoder.decode(logits_np, beam_width=BEAM_WIDTH)
    print(f"✅ Decoded Text: '{text}'")

if __name__ == "__main__":
    test_decoder()

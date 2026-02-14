# config.py
# All configuration constants for the application

import torch

# --- Audio & VAD ---
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHUNK_DURATION = 0.03  # 30ms for VAD frames
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
VAD_MODE = 1  # 0-3, aggressiveness of VAD | 3 old fine
FRAME_DURATION_MS = 30  # WebRTC VAD frame size in ms (10, 20, or 30)
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- N-gram Language Model ---
NGRAM_MODEL_PATH = "political_science_v3.binary"
BEAM_WIDTH = 100 
LM_ALPHA = 0.9 # Weight for the Language Model
LM_BETA = 2.5 # Bonus for word insertion

# --- NEW: NOISE GATE ---
# Audio is between 0.0 and 1.0.
# 0.01 is a good starting point. Increase to 0.02 or 0.03 if you have a noisy fan.
MIN_VOLUME_THRESHOLD = 0.03 

# --- Speech Detection Parameters ---
MIN_SPEECH_DURATION = 0.4  # Minimum speech duration (seconds) |0.5 old fine
MIN_SPEECH_FRAMES = int(MIN_SPEECH_DURATION * SAMPLE_RATE)
MAX_SILENCE_DURATION = 0.4  # Max silence before ending speech (seconds) |0.5 old fine
MAX_SILENCE_FRAMES = int(MAX_SILENCE_DURATION * SAMPLE_RATE)

# --- Concurrency Parameters ---
MAX_SPEECH_DURATION = 10.0 # Max speech before forcing transcript (seconds)
MAX_SPEECH_FRAMES = int(MAX_SPEECH_DURATION * SAMPLE_RATE)
OVERLAP_DURATION = 1.0 # Overlap for concurrent chunks (seconds)
OVERLAP_FRAMES = int(OVERLAP_DURATION * SAMPLE_RATE)

# --- LLM Configuration ---
# We use Mistral because it is free and has fewer moderation issues than Llama
# LLM_MODEL_NAME = "mistralai/mistral-7b-instruct:free"
LLM_MODEL_NAME = "google/gemini-2.5-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# The Prompt for the LLM
CORRECTION_SYSTEM_PROMPT = """You are an expert Sinhala Political Science editor. Correct the provided ASR transcript:
Fix Errors: Correct spelling and phonetic errors. Replace meaningless words with the most logical Political Science term based on context (e.g., 'ආක්පිතියි' → 'ආකෘතියකි').
Clean: Remove all filler sounds (e.g., 'අ...', 'ම්ම්') and stutters.
Constraint: Preserve the exact original meaning. Do not add new information.
Output: Provide ONLY the corrected Sinhala text with no introductory or concluding remarks.
"""

SUMMARIZATION_SYSTEM_PROMPT = """
Convert the following Spoken Sinhala lecture note into a Formal Written Sinhala summary.
    Rules:
    1. Grammar: Use formal 'Granthika' style (e.g., replace 'කියන්නේ' with 'යනු', 'තියෙනවා' with 'තිබේ').
    2. Content: Remove conversational fillers like "දරුවනේ" or "අපි බලමු".
    3. Output: **Structure:**
       - Identify the Main Topic.
       - List 3-5 key facts or definitions as bullet points.
       - Be extremely concise.
"""
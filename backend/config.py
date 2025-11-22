# config.py
# All configuration constants for the application

import torch

# --- Audio & VAD ---
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHUNK_DURATION = 0.03  # 30ms for VAD frames
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
VAD_MODE = 2  # 0-3, aggressiveness of VAD
FRAME_DURATION_MS = 30  # WebRTC VAD frame size in ms (10, 20, or 30)
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- NEW: NOISE GATE ---
# Audio is between 0.0 and 1.0.
# 0.01 is a good starting point. Increase to 0.02 or 0.03 if you have a noisy fan.
MIN_VOLUME_THRESHOLD = 0.02 

# --- Speech Detection Parameters ---
MIN_SPEECH_DURATION = 0.5  # Minimum speech duration (seconds)
MIN_SPEECH_FRAMES = int(MIN_SPEECH_DURATION * SAMPLE_RATE)
MAX_SILENCE_DURATION = 0.6  # Max silence before ending speech (seconds)
MAX_SILENCE_FRAMES = int(MAX_SILENCE_DURATION * SAMPLE_RATE)

# --- Concurrency Parameters ---
MAX_SPEECH_DURATION = 5.0 # Max speech before forcing transcript (seconds)
MAX_SPEECH_FRAMES = int(MAX_SPEECH_DURATION * SAMPLE_RATE)
OVERLAP_DURATION = 1.0 # Overlap for concurrent chunks (seconds)
OVERLAP_FRAMES = int(OVERLAP_DURATION * SAMPLE_RATE)

# --- LLM Configuration ---
# We use Mistral because it is free and has fewer moderation issues than Llama
# LLM_MODEL_NAME = "mistralai/mistral-7b-instruct:free"
LLM_MODEL_NAME = "x-ai/grok-4.1-fast:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# The Prompt for the LLM
CORRECTION_SYSTEM_PROMPT = """
You are an expert Sinhala editor and proofreader with a strong background in Political Science.
Your task is to correct a raw, real-time transcription of spoken Sinhala,
which is on the topic of Political Science.

Follow these rules strictly:
1.  **Correct Spelling:** Fix any Sinhala spelling mistakes (e.g., "වරදි" -> "වැරදි").

2.  **Fix Pronunciation Errors:** The ASR may write a phonetically similar but incorrect word.
    Change it to the nearest correct word that makes sense in the context.
    (e.g., ASR: "විශිය" -> Correct: "විෂය").

3.  **Contextual Word Correction:** The ASR may produce words that are phonetically plausible
    but are invalid or meaningless in the context (e.g., "ආක්පිතියි").
    First, analyze the entire speech flow to understand the topic. Then,
    use your **Political Science knowledge** to change these words to the
    *most logical and meaningful word* that fits the context.
    (e.g., "රාජ්‍ය ආණ්ඩු ක්‍රම ආක්පිතියි." -> "රාජ්‍ය ආණ්ඩු ක්‍රම ආකෘතියකි.")

4.  **Remove Filler Words:** Remove all filler words, "dumb text," and stutters
    (e.g., "අ...", "ම්ම්...", "ආ...", "හ්ම්", "ත්ත්ත්", "ත්ත්", etc.).

5.  **Fix Grammar:** Correct basic grammatical errors to ensure the text is readable.

6.  **Preserve Meaning:** Do NOT add new information or change the original speaker's intended meaning.
    Your goal is to clarify, not to rewrite.

7.  **RESPONSE:** Respond ONLY with the corrected, clean Sinhala text.
    Do not add any pre-amble, explanation, or chat text like "Here is the correction:".
    Just give the text.
"""


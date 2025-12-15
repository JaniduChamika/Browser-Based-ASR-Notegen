# backend/llm_handler.py
import os
import openai 
from openai import OpenAI
from dotenv import load_dotenv
from config import *


class LLMHandler:
    def __init__(self):
        load_dotenv()
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.client = None

        if self.api_key:
            try:
                self.client = OpenAI(
                    base_url=OPENROUTER_BASE_URL,
                    api_key=self.api_key,
                )
            except Exception as e:
                print(f"Error initializing LLM Client: {e}")

    def correct_transcript(self, raw_text, task):
        """Handles both Correction and Summarization based on prefix."""

        # 1. Validation
        if not raw_text or not raw_text.strip():
            return None

        if not self.client:
            print("LLM Client is not initialized (Missing API Key?).")
            return raw_text

        try:
            TEMP = 0
            # 2. Determine Task
            if task == "summarize":
                # Summarization Mode
                system_prompt = SUMMARIZATION_SYSTEM_PROMPT
                user_content = raw_text
                TEMP = 0.3
            else:
                # Correction Mode (Default)
                system_prompt = CORRECTION_SYSTEM_PROMPT
                user_content = raw_text

            # 3. Call API
            print(f"Sending text to LLM ({len(user_content)} chars)...")
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost/sinhala-asr-final",
                    "X-Title": "Sinhala ASR",
                },
                extra_body={
                    "provider": {"order": ["Google"], "allow_fallbacks": False}
                },
                model=LLM_MODEL_NAME,
                max_tokens=1024,
                temperature=TEMP,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )

            result_text = completion.choices[0].message.content.strip()
            print("LLM Result received.")
            return result_text
        except openai.APIStatusError as e:
            print(f"LLM API Status Error: {e.status} - {e.message}")
            return raw_text
        except Exception as e:
            print(f"LLM Error: {e}")
            return raw_text

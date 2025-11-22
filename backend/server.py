# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import numpy as np
import json
import queue
import threading
import asyncio

from asr_engine import AsrEngine
from llm_handler import LLMHandler

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Redirect root to index.html
@app.get("/")
async def read_root():
    return RedirectResponse(url="/static/index.html")

# --- Global State ---
response_queue = queue.Queue()
asr_engine = AsrEngine(response_queue)
llm_handler = LLMHandler()

# Start worker
worker_thread = threading.Thread(target=asr_engine.transcription_worker, daemon=True)
worker_thread.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"✅ [WS] Browser Connected: {websocket.client}")
    
    packet_count = 0
    
    try:
        while True:
            # 1. Receive Data
            data = await websocket.receive_bytes()
            packet_count += 1
            
            # Log every 100 packets (approx every 3 seconds) just to show it's alive
            if packet_count % 100 == 0:
                print(f"⬇ [WS] Receiving audio stream... (Packet #{packet_count})")
            
            # 2. Process Audio
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            
            # 3. Send to Engine
            asr_engine.process_stream(audio_float)
            
            # 4. Send Responses back to Browser
            while not response_queue.empty():
                msg_type, content = response_queue.get()
                
                if msg_type == "text":
                    print(f"📤 [WS] Sending Transcript: '{content}'")
                elif msg_type == "status":
                    print(f"ℹ️ [WS] Status Update: {content}")
                    
                response = {"type": msg_type, "content": content}
                await websocket.send_text(json.dumps(response))
                
            await asyncio.sleep(0.001)
            
    except WebSocketDisconnect:
        print("❌ [WS] Browser Disconnected")
    except Exception as e:
        print(f"⚠️ [WS] Error: {e}")

@app.post("/correct")
async def correct_transcript(payload: dict):
    raw_text = payload.get("text", "")
    print(f"🧠 [LLM] Requesting correction for: {raw_text[:30]}...")
    corrected = llm_handler.correct_transcript(raw_text)
    return {"corrected_text": corrected}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

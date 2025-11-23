# backend/server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
import json
import queue
import threading
import asyncio
import shutil
import os
from pydub import AudioSegment

from asr_engine import AsrEngine
from llm_handler import LLMHandler
from config import SAMPLE_RATE

app = FastAPI()

# CORS to allow React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global State ---
response_queue = queue.Queue()
asr_engine = AsrEngine(response_queue)
llm_handler = LLMHandler()

# Start ASR Worker Thread
worker_thread = threading.Thread(target=asr_engine.transcription_worker, daemon=True)
worker_thread.start()

# --- 1. WebSocket for Real-Time Transcription ---
@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"✅ [WS] React Client Connected")
    
    try:
        while True:
            # 1. Receive Raw Int16 PCM Data from React
            data = await websocket.receive_bytes()
            
            # 2. Convert to Float32 for Engine
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            
            # 3. Send to ASR Engine
            asr_engine.process_stream(audio_float)
            
            # 4. Check for Results
            while not response_queue.empty():
                msg_type, content = response_queue.get()
                
                # Format for React Frontend
                response = {}
                if msg_type == "text":
                    # "final" tells React this is committed text
                    response = {"type": "final", "text": content}
                elif msg_type == "status":
                    # "status" helps debug
                    response = {"type": "status", "text": content}
                
                await websocket.send_text(json.dumps(response))
                
            await asyncio.sleep(0.001)
            
    except WebSocketDisconnect:
        print("❌ [WS] Disconnected")
    except Exception as e:
        print(f"⚠️ [WS] Error: {e}")

# --- 2. File Upload Endpoint for "Audio Clip" Page ---
@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    try:
        print(f"📂 Receiving file: {file.filename}")
        
        # Save temporary file
        temp_filename = f"temp_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Convert to WAV 16kHz Mono using Pydub (requires ffmpeg)
        print("Converting audio...")
        audio = AudioSegment.from_file(temp_filename)
        audio = audio.set_frame_rate(16000).set_channels(1)
        
        # Export as raw float32 array
        samples = np.array(audio.get_array_of_samples())
        
        # Normalize to float32
        if audio.sample_width == 2: # 16-bit
            samples = samples.astype(np.float32) / 32768.0
        elif audio.sample_width == 4: # 32-bit
            samples = samples.astype(np.float32) / 2147483648.0
            
        # Run Transcription
        print("Transcribing file...")
        transcript = asr_engine.transcribe_audio(samples)
        
        if not transcript:
            transcript = "No speech detected in this audio file."

        # Generate Summary via LLM
        print("Generating Summary...")
        summary = llm_handler.correct_transcript(f"SUMMARIZE: {transcript}")

        # Cleanup
        os.remove(temp_filename)
        
        return {
            "filename": file.filename,
            "transcript": transcript,
            "summary": summary
        }

    except Exception as e:
        print(f"Upload Error: {e}")
        return {"error": f"Server error: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
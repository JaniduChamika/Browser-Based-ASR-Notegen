import os

# --- CRITICAL: FORCE CPU MODE ---
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # NEW: For data validation
import uvicorn
import numpy as np
import json
import queue
import threading
import asyncio
import shutil
import time

from asr_engine import AsrEngine
from llm_handler import LLMHandler

app = FastAPI()

# Allow React
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

worker_thread = threading.Thread(target=asr_engine.transcription_worker, daemon=True)
worker_thread.start()

# --- NEW: Request Model ---
class ProcessTextRequest(BaseModel):
    text: str
    task: str  # "correct" or "summarize"

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"✅ [WS] Connected")
    
    try:
        while True:
            data = await websocket.receive_bytes()
            
            # Convert Int16 -> Float32
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            
            asr_engine.process_stream(audio_float)
            
            # Send results
            while not response_queue.empty():
                msg_type, content = response_queue.get()
                
                response = {}
                if msg_type == "text":
                    response = {"type": "final", "text": content}
                elif msg_type == "status":
                    response = {"type": "status", "text": content}
                
                await websocket.send_text(json.dumps(response))
                
            await asyncio.sleep(0.001)
            
    except WebSocketDisconnect:
        print("❌ [WS] Disconnected")
    except Exception as e:
        print(f"⚠️ [WS] Error: {e}")

# --- NEW: Text Processing Endpoint ---
@app.post("/process-text")
async def process_text(request: ProcessTextRequest):
    print(f"🧠 Processing Request: {request.task}")
    
    try:
        input_text = request.text
        
       
        # Call LLM
        result = llm_handler.correct_transcript(input_text,task=request.task)
        
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    try:
        print(f"📂 Processing file: {file.filename}")
        
        temp_filename = f"temp_{int(time.time())}_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        from pydub import AudioSegment
        audio = AudioSegment.from_file(temp_filename)
        audio = audio.set_frame_rate(16000).set_channels(1)
        samples = np.array(audio.get_array_of_samples())
        
        if audio.sample_width == 2:
            samples = samples.astype(np.float32) / 32768.0
        elif audio.sample_width == 4:
            samples = samples.astype(np.float32) / 2147483648.0
            
        print("Transcribing...")
        transcript = asr_engine.transcribe_audio(samples)
        if not transcript: transcript = "No speech detected."

        print("Summarizing...")
        summary = llm_handler.correct_transcript(f"SUMMARIZE: {transcript}")

        os.remove(temp_filename)
        
        return {
            "filename": file.filename,
            "transcript": transcript,
            "summary": summary
        }

    except Exception as e:
        print(f"Upload Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
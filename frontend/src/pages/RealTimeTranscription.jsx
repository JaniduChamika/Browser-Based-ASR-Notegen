import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Download, Wifi, WifiOff } from 'lucide-react';

const RealTimeTranscription = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // disconnected, connecting, connected, error
  const [errorMessage, setErrorMessage] = useState('');

  // Refs for technical objects
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const mediaStreamRef = useRef(null);

  // WebSocket URL
  const WS_URL = 'ws://localhost:8000/ws/audio';

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      stopRecording();
    };
  }, []);

  const connectWebSocket = () => {
    return new Promise((resolve, reject) => {
      setConnectionStatus('connecting');

      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        setErrorMessage('');
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle backend message types
          if (data.type === 'final') {
             // Append to final transcript
            setTranscript(prev => prev + (data.text || '') + ' ');
            setInterimTranscript(''); // Clear interim
          } else if (data.type === 'interim') {
            // Update interim (grey text)
            setInterimTranscript(data.text || '');
          } else if (data.type === 'status') {
             // Optional: handle status updates like "Listening..."
             console.log("Status:", data.text);
          } else if (data.type === 'error') {
            console.error('Backend error:', data.message);
            setErrorMessage(data.message || 'Transcription error occurred');
          }
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        setErrorMessage('WebSocket connection error. Is the server running?');
        reject(error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('disconnected');
        setIsRecording(false);
      };

      wsRef.current = ws;
    });
  };

  const startRecording = async () => {
    try {
      setErrorMessage('');
      
      // Step 1: Connect to WebSocket first
      await connectWebSocket();

      // Step 2: Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000, // Desired sample rate for Whisper
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      mediaStreamRef.current = stream;

      // Step 3: Initialize Audio Context (Raw PCM processing)
      // We use AudioContext instead of MediaRecorder to get raw Int16 bytes
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      
      // Create ScriptProcessor (Buffer size 4096 ≈ 256ms latency)
      // Input 1 channel, Output 1 channel
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      // Step 4: Handle audio processing events
      processor.onaudioprocess = (e) => {
        // Ensure socket is open before sending
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          
          // Convert Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
          // This is what the Python backend expects
          const buffer = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            let s = Math.max(-1, Math.min(1, inputData[i]));
            buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          
          // Send binary data
          wsRef.current.send(buffer);
        }
      };

      setIsRecording(true);

    } catch (error) {
      console.error('Error starting recording:', error);

      if (error.name === 'NotAllowedError') {
        setErrorMessage('Microphone access denied. Please allow microphone access.');
      } else if (error.name === 'NotFoundError') {
        setErrorMessage('No microphone found. Please connect a microphone.');
      } else {
        setErrorMessage('Failed to start recording: ' + error.message);
      }

      stopRecording();
    }
  };

  const stopRecording = () => {
    // Stop Microphone Stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    // Disconnect Audio Nodes
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    setIsRecording(false);
    // We do NOT clear transcript here so user can see result
  };

  const clearTranscript = () => {
    setTranscript('');
    setInterimTranscript('');
    setErrorMessage('');
  };

  const downloadTranscript = () => {
    const fullTranscript = transcript + interimTranscript;
    if (!fullTranscript.trim()) {
      alert('No transcript to download');
      return;
    }

    const blob = new Blob([fullTranscript], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-600';
      case 'connecting': return 'text-yellow-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getConnectionStatusIcon = () => {
    return connectionStatus === 'connected' || connectionStatus === 'connecting'
      ? <Wifi size={16} />
      : <WifiOff size={16} />;
  };

  return (
    <div className="mx-auto p-6 bg-white min-h-screen">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-8 shadow-lg">
        <h1 className="text-3xl font-bold text-gray-800 mb-2 text-center">
          Real-time Voice Transcription
        </h1>
        
        {/* Connection Status */}
        <div className={`flex items-center justify-center gap-2 mb-6 ${getConnectionStatusColor()}`}>
          {getConnectionStatusIcon()}
          <span className="font-medium capitalize">{connectionStatus}</span>
        </div>

        {/* Error Message */}
        {errorMessage && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            <p className="font-semibold">Error</p>
            <p>{errorMessage}</p>
          </div>
        )}

        {/* Recording Controls */}
        <div className="flex justify-center items-center gap-4 mb-8">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`
              flex items-center gap-3 px-8 py-4 rounded-full font-semibold text-lg transition-all duration-300 transform hover:scale-105 shadow-lg
              ${isRecording
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
              }
              ${!isRecording && connectionStatus === 'connecting' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {isRecording ? (
              <>
                <Square size={24} />
                Stop Recording
              </>
            ) : (
              <>
                <Mic size={24} />
                Start Recording
              </>
            )}
          </button>

          {(transcript || interimTranscript) && (
            <button
              onClick={clearTranscript}
              className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors duration-200"
            >
              Clear
            </button>
          )}
        </div>

        {/* Recording Status */}
        {isRecording && (
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
            <span className="text-red-600 font-medium">Recording... Speak now</span>
          </div>
        )}

        {/* Transcript Box */}
        <div className="bg-white rounded-lg shadow-inner border-2 border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Mic size={20} />
            Live Transcript
          </h2>

          <div className="min-h-[300px] max-h-[400px] overflow-y-auto bg-gray-50 rounded-lg p-4 border">
            {!transcript && !interimTranscript ? (
              <p className="text-gray-400 italic text-center py-8">
                Click "Start Recording" to begin transcription...
              </p>
            ) : (
              <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                <span className="text-gray-900">{transcript}</span>
                <span className="text-blue-600 italic ml-1">{interimTranscript}</span>
                {isRecording && <span className="inline-block w-2 h-5 bg-blue-500 ml-1 animate-pulse"></span>}
              </div>
            )}
          </div>

          <div className="text-sm text-gray-500 mt-2">
             <span className="text-gray-900 font-medium">Final text</span> |
             <span className="text-blue-600 font-medium italic ml-1">Interim/Processing</span>
          </div>
        </div>

        {/* Download Button */}
        <div className="flex justify-center">
          <button
            onClick={downloadTranscript}
            disabled={!transcript && !interimTranscript}
            className={`
              flex items-center gap-3 px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-md
              ${(transcript || interimTranscript)
                ? 'bg-green-500 hover:bg-green-600 text-white transform hover:scale-105'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            <Download size={20} />
            Download Notes
          </button>
        </div>

        {/* Instructions */}
        <div className="mt-4 p-4 bg-green-100 rounded-lg border border-green-200">
          <h3 className="font-semibold text-green-800 mb-2">How to use:</h3>
          <ul className="text-green-700 text-sm space-y-1">
            <li>• Ensure your Python backend is running on localhost:8000</li>
            <li>• Click "Start Recording" and allow microphone access</li>
            <li>• Speak clearly - audio streams to backend in real-time</li>
            <li>• See real-time transcription from your ASR model</li>
            <li>• Click "Stop Recording" when finished</li>
            <li>• Download your transcript as a text file</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default RealTimeTranscription;
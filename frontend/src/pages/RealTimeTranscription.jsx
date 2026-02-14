import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Download, Wifi, WifiOff, Sparkles, FileText, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import "../App.css"
import generateWordDocument from '../components/NoteDownload';
const RealTimeTranscription = () => {
  const [isRecording, setIsRecording] = useState(false);

  // Transcription States
  const [transcript, setTranscript] = useState('');
  // const [transcript, setTranscript] = useState('අද නොම ඔබ සමඟ බිදාගන්නේ දීශපාලන විද්‍යාව ලූකික් ලොකේ මූලික පියවා. ඇන් මෙය කිසිම නිශ්චිත විෂයක් නොවේ. එය අපගේ ජීවිතේ සෑම අයියි. ඉතේ සෑම අන්සේයකටම බලපාන සමාජ්‍ය බලවේග, බලධාරිං සතීරණ ගැනීම් වල ඉංහිංවළ රහස් විස්තර විශයක් ඒ පමණක් නොවෙයි. අපගී රටි ඉතිහාසී සිට නූතන ලෝකය දක්වා මිනිස්සුන්ගේ අනාගත් ඉස්සුන්ගේ අනාගතය හැඩ ගස්සන බල වීගිය ත්ත්ත් යොක් ප්‍රතියි. ඔබ කවදා හා සිට්වද ඔබ චන්දයක් තැබීම නොබේ ජීවිතය මග පෙන්වන සම්පත් අධ්‍යාපනය සෞඛි සේවා සෞඛ්‍ය සේභාවන් වෙනස් වෙන්නෙ කිහිත් කොහොමද කියලා. නැතම් ලෝක ලෝක නායකයංගේ තිර්ණය වලි අපගේ දෛනික ජීමිතියට බල බලපෑම් ඇතිවන්නේ කෙහෙම කොහොමද කිය මේ දේශපාලන විද්‍යාව එස් යල්ල පැහැදිරි කරනව. එය රාජ්‍යයන්ගේ බලගැන් වී ප්‍රහදී සිහත් ජාත්‍යනතර සබඳතා සබද තා සහ සමාධි සාධ්‍යාරණත්තේ අධී ගැන ස්වාභයනු ඉසා පලනු ත්ත්ත් යොක් ප්‍රත්ත් ත්ත්ත් යොක් ප්‍රත්ත් ත්ත්ත් යොක් ප්‍රත්ත් ත්ත්ත් යොක් ප්‍රත්ත් අපි මොලිම බලමු දේශ්‍යපාලන විද්‍යාවෙ මූලික සංකල්ප ත්ත්ත් ත්ත්ත් යොක් ප්‍රතියි.');
  const [interimTranscript, setInterimTranscript] = useState('');


  // AI Feature States
  const [correctedText, setCorrectedText] = useState('');
  const [summaryText, setSummaryText] = useState('');
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const [activeAITask, setActiveAITask] = useState(null); // 'correct' or 'summarize'

  // Connection States
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [errorMessage, setErrorMessage] = useState('');

  // Refs
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const WS_URL = 'ws://localhost:8000/ws/audio';

  useEffect(() => {
    return () => stopRecording();
  }, []);

  // --- WebSocket & Audio Logic (Kept Modular) ---

  const connectWebSocket = () => {
    return new Promise((resolve, reject) => {
      setConnectionStatus('connecting');
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setConnectionStatus('connected');
        setErrorMessage('');
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'final') {
            setTranscript(prev => prev + (data.text || '') + ' ');
            setInterimTranscript('');
          } else if (data.type === 'interim') {
            setInterimTranscript(data.text || '');
          } else if (data.type === 'error') {
            setErrorMessage(data.message);
          }
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };

      ws.onerror = (error) => {
        setConnectionStatus('error');
        setErrorMessage('WebSocket connection error. Is the server running?');
        reject(error);
      };

      ws.onclose = () => {
        setConnectionStatus('disconnected');
        setIsRecording(false);
      };

      wsRef.current = ws;
    });
  };

  const startRecording = async () => {
    try {
      // Clear previous AI results when starting new recording
      setErrorMessage('');
      setCorrectedText('');
      setSummaryText('');

      await connectWebSocket();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true }
      });
      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      processor.onaudioprocess = (e) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          const buffer = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            let s = Math.max(-1, Math.min(1, inputData[i]));
            buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          wsRef.current.send(buffer);
        }
      };

      setIsRecording(true);

    } catch (error) {
      console.error('Error starting recording:', error);
      setErrorMessage('Failed to start recording: ' + error.message);
      stopRecording();
    }
  };

  const stopRecording = () => {
    if (mediaStreamRef.current) mediaStreamRef.current.getTracks().forEach(track => track.stop());
    if (processorRef.current) processorRef.current.disconnect();
    if (audioContextRef.current) audioContextRef.current.close();
    if (wsRef.current) wsRef.current.close();
    setIsRecording(false);
  };

  // --- NEW: AI Processing Functions ---

  const processTextWithAI = async (task) => {
    const fullText = transcript + interimTranscript;

    if (!fullText.trim()) return;

    setIsProcessingAI(true);
    setActiveAITask(task);

    try {
      const response = await fetch('http://localhost:8000/process-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: fullText, task: task }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        if (task === 'correct') {
          setCorrectedText(data.result);
        } else if (task === 'summarize') {
          setSummaryText(data.result);
        }
      } else {
        setErrorMessage('AI Error: ' + data.message);
      }
    } catch (error) {
      setErrorMessage('Failed to connect to AI server.');
    } finally {
      setIsProcessingAI(false);
      setActiveAITask(null);
    }
  };

  const handleCorrection = () => processTextWithAI('correct');
  const handleSummarization = () => processTextWithAI('summarize');

  // --- Helpers ---

  const clearTranscript = () => {
    setTranscript('');
    setInterimTranscript('');
    setCorrectedText('');
    setSummaryText('');
    setErrorMessage('');
  };

  // const downloadTranscript = () => {
  //   const fullContent = `RAW TRANSCRIPT:\n${transcript}\n\nCORRECTED:\n${correctedText}\n\nSUMMARY:\n${summaryText}`;
  //   const blob = new Blob([fullContent], { type: 'text/plain' });
  //   const url = URL.createObjectURL(blob);
  //   const a = document.createElement('a');
  //   a.href = url;
  //   a.download = `notes-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
  //   document.body.appendChild(a);
  //   a.click();
  //   document.body.removeChild(a);
  //   URL.revokeObjectURL(url);
  // };

  return (
    <div className="mx-auto p-6 bg-white min-h-screen">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-8 shadow-lg">
        <h1 className="text-3xl font-bold text-gray-800 mb-2 text-center">
          Real-time Voice Transcription
        </h1>

        {/* Connection Status */}
        <div className={`flex items-center justify-center gap-2 mb-6 ${connectionStatus === 'connected' ? 'text-green-600' :
          connectionStatus === 'error' ? 'text-red-600' : 'text-gray-600'
          }`}>
          {connectionStatus === 'connected' ? <Wifi size={16} /> : <WifiOff size={16} />}
          <span className="font-medium capitalize">{connectionStatus}</span>
        </div>

        {errorMessage && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            <p className="font-semibold">Error</p>
            <p>{errorMessage}</p>
          </div>
        )}

        {/* --- CONTROLS SECTION --- */}
        <div className="flex flex-wrap justify-center items-center gap-4 mb-8">
          {/* Record Button */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`
              flex items-center gap-3 px-8 py-4 rounded-full font-semibold text-lg transition-all duration-300 transform hover:scale-105 shadow-lg
              ${isRecording
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
              }
            `}
          >
            {isRecording ? <><Square size={24} /> Stop Recording</> : <><Mic size={24} /> Start Recording</>}
          </button>

          {/* AI Correct Button */}
          <button
            onClick={handleCorrection}
            disabled={isRecording || (!transcript && !interimTranscript) || isProcessingAI}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all shadow-md
              ${isRecording || (!transcript && !interimTranscript)
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }
            `}
          >
            {isProcessingAI && activeAITask === 'correct' ? <Loader2 className="animate-spin" size={20} /> : <Sparkles size={20} />}
            Correct Transcript
          </button>

          {/* Summarize Button */}
          <button
            onClick={handleSummarization}
            disabled={isRecording || (!transcript && !interimTranscript) || isProcessingAI}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all shadow-md
              ${isRecording || (!transcript && !interimTranscript)
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-purple-600 text-white hover:bg-purple-700'
              }
            `}
          >
            {isProcessingAI && activeAITask === 'summarize' ? <Loader2 className="animate-spin" size={20} /> : <FileText size={20} />}
            Summarize Note
          </button>

          {/* Clear Button */}
          {(transcript || interimTranscript) && (
            <button
              onClick={clearTranscript}
              disabled={isRecording}
              className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {isRecording && (
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
            <span className="text-red-600 font-medium">Recording... Speak now</span>
          </div>
        )}

        {/* --- RAW TRANSCRIPT --- */}
        <div className="bg-white rounded-lg shadow-inner border-2 border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Mic size={20} /> Live Transcript
          </h2>
          <div className="min-h-[200px] max-h-[300px] overflow-y-auto bg-gray-50 rounded-lg p-4 border">
            {!transcript && !interimTranscript ? (
              <p className="text-gray-400 italic text-center py-8">Ready...</p>
            ) : (
              <div className="whitespace-pre-wrap text-gray-800 leading-relaxed text-left">
                <span className="text-gray-900">{transcript}</span>
                <span className="text-blue-600 italic ml-1">{interimTranscript}</span>
              </div>
            )}
          </div>
        </div>

        {/* --- CORRECTED TRANSCRIPT (Shown if data exists) --- */}
        {correctedText && (
          <div className="bg-indigo-50 rounded-lg shadow-inner border-2 border-indigo-200 p-6 mb-6 animate-in fade-in slide-in-from-bottom-4">
            <h2 className="text-xl font-semibold text-indigo-800 mb-4 flex items-center gap-2">
              <Sparkles size={20} /> Corrected Version
            </h2>
            <div className="bg-white rounded-lg p-4 border border-indigo-100 min-h-[150px] text-left">
              <p className="whitespace-pre-wrap text-gray-800 leading-relaxed">{correctedText}</p>
            </div>
          </div>
        )}

        {/* --- SUMMARY (Shown if data exists) --- */}
        {summaryText && (
          <div className="bg-purple-50 rounded-lg shadow-inner border-2 border-purple-200 p-6 mb-6 animate-in fade-in slide-in-from-bottom-4">
            <h2 className="text-xl font-semibold text-purple-800 mb-4 flex items-center gap-2">
              <FileText size={20} /> Summarized Note
            </h2>
            <div className="bg-white rounded-lg p-4 border border-purple-100 min-h-[150px] note-container">
              {/* <p className="whitespace-pre-wrap text-gray-800 leading-relaxed">{summaryText}</p> */}
              <ReactMarkdown>
                {summaryText}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Download Button */}
        <div className="flex justify-center">
          <button
            onClick={() => generateWordDocument(summaryText + '\n # Transcript \n //' + correctedText + "//")}
            disabled={!transcript && !interimTranscript}
            className={`
              flex items-center gap-3 px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-md
              ${(transcript || interimTranscript)
                ? 'bg-green-600 hover:bg-green-700 text-white transform hover:scale-105'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            <Download size={20} />
            Download All Notes
          </button>
        </div>

      </div>
    </div>
  );
};

export default RealTimeTranscription;
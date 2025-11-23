import { useState, useRef } from 'react';
import { Upload, Download, FileAudio, X } from 'lucide-react';
import ProgressIndicator from '../components/ProgressIndicator';

function AudioClipTranscription() {
  const [audioFile, setAudioFile] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [summary, setSummary] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [downloadEnabled, setDownloadEnabled] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setAudioFile(file);
      setTranscript('');
      setSummary('');
      setDownloadEnabled(false);
      processAudioFile(file);
    }
  };

  const processAudioFile = async (file) => {
    setIsProcessing(true);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Call Python Backend
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      
      if (data.error) {
        alert(`Error: ${data.error}`);
      } else {
        setTranscript(data.transcript);
        setSummary(data.summary);
        setDownloadEnabled(true);
      }
    } catch (error) {
      console.error("Error uploading:", error);
      alert("Failed to process audio file. Is the backend running?");
    } finally {
      setIsProcessing(false);
    }
  };

  const downloadFiles = () => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // Download transcript
    const transcriptBlob = new Blob([transcript], { type: 'text/plain' });
    const transcriptUrl = URL.createObjectURL(transcriptBlob);
    const transcriptLink = document.createElement('a');
    transcriptLink.href = transcriptUrl;
    transcriptLink.download = `transcript-${timestamp}.txt`;
    document.body.appendChild(transcriptLink);
    transcriptLink.click();
    document.body.removeChild(transcriptLink);
    URL.revokeObjectURL(transcriptUrl);

    // Download summary
    if (summary) {
        setTimeout(() => {
            const summaryBlob = new Blob([summary], { type: 'text/plain' });
            const summaryUrl = URL.createObjectURL(summaryBlob);
            const summaryLink = document.createElement('a');
            summaryLink.href = summaryUrl;
            summaryLink.download = `summary-${timestamp}.txt`;
            document.body.appendChild(summaryLink);
            summaryLink.click();
            document.body.removeChild(summaryLink);
            URL.revokeObjectURL(summaryUrl);
        }, 100);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const removeFile = () => {
    setAudioFile(null);
    setTranscript('');
    setSummary('');
    setDownloadEnabled(false);
    setIsProcessing(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">
          Audio Clip Transcription
        </h2>

        {/* File Upload Area */}
        <div className="mb-6">
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac"
            onChange={handleFileSelect}
            className="hidden"
          />
          
          {!audioFile ? (
            <div
              onClick={triggerFileInput}
              className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-500 hover:bg-indigo-50 transition-all cursor-pointer"
            >
              <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 font-medium mb-2">
                Click to upload audio file
              </p>
              <p className="text-sm text-gray-500">
                Supports MP3, WAV, M4A, AAC, OGG, FLAC
              </p>
            </div>
          ) : (
            <div className="border-2 border-indigo-300 rounded-lg p-6 bg-indigo-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 flex-1">
                  <FileAudio className="w-8 h-8 text-indigo-600 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-indigo-900 font-medium truncate">
                      {audioFile.name}
                    </p>
                    <p className="text-indigo-600 text-sm">
                      {(audioFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <button
                  onClick={removeFile}
                  className="ml-4 p-2 text-indigo-600 hover:bg-indigo-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="mb-6 bg-indigo-50 rounded-lg border border-indigo-200">
            <ProgressIndicator message="Uploading, Converting & Transcribing..." />
          </div>
        )}

        {/* Download Button */}
        {!isProcessing && (transcript || summary) && (
          <div className="flex justify-center mb-6">
            <button
              onClick={downloadFiles}
              disabled={!downloadEnabled}
              className={`flex items-center px-6 py-3 rounded-lg transition-all shadow-md font-medium ${
                downloadEnabled
                  ? 'bg-green-600 text-white hover:bg-green-700 hover:shadow-lg'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              <Download className="w-5 h-5 mr-2" />
              Download Transcript & Summary
            </button>
          </div>
        )}

        {/* Transcript Display Area */}
        {transcript && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-semibold text-gray-700">
                Transcript
              </label>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 min-h-64 max-h-96 overflow-y-auto border border-gray-200">
              <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                {transcript}
              </p>
            </div>
          </div>
        )}

        {/* Summary Display Area */}
        {summary && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-semibold text-gray-700">
                Summary & Key Points
              </label>
            </div>
            <div className="bg-indigo-50 rounded-lg p-4 min-h-32 border border-indigo-200">
              <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                {summary}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AudioClipTranscription;
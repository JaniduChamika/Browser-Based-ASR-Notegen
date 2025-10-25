import { Loader2 } from 'lucide-react';

function ProgressIndicator({ message }) {
  return (
    <div className="flex flex-col items-center justify-center space-y-4 py-6">
      {/* Spinning Loader */}
      <div className="relative">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
      
      {/* Progress Message */}
      <div className="text-center">
        <p className="text-gray-700 font-medium text-lg">{message}</p>
        <p className="text-gray-500 text-sm mt-1">Please wait...</p>
      </div>
      
      {/* Animated Dots */}
      <div className="flex space-x-2">
        <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce"></div>
        <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
        <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
      </div>
    </div>
  );
}

export default ProgressIndicator;
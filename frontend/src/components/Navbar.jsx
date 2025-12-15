import { Mic, Upload } from 'lucide-react';

function Navbar({ currentPage, setCurrentPage }) {
  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Title Section */}
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-indigo-600">
              Lecture Transcription
            </h1>
          </div>
          
          {/* Navigation Buttons */}
          <div className="flex space-x-4">
            <button
              onClick={() => setCurrentPage('realtime')}
              className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors duration-200 ${
                currentPage === 'realtime'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Mic className="w-5 h-5 mr-2" />
              Real-Time
            </button>
            
            {/* <button
              onClick={() => setCurrentPage('clip')}
              className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors duration-200 ${
                currentPage === 'clip'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Upload className="w-5 h-5 mr-2" />
              Upload Clip
            </button> */}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
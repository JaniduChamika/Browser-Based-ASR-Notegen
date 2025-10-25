import { useState } from 'react';
import Navbar from './components/Navbar';
import Layout from './components/Layout';
import RealTimeTranscription from './pages/RealTimeTranscription';
import AudioClipTranscription from './pages/AudioClipTranscription';

function App() {
  const [currentPage, setCurrentPage] = useState('realtime');

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <Layout>
        {currentPage === 'realtime' ? (
          <RealTimeTranscription />
        ) : (
          <AudioClipTranscription />
        )}
      </Layout>
    </div>
  );
}

export default App;
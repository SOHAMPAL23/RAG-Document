import React, { useState } from 'react';
import UploadPanel from './components/UploadPanel';
import ChatInterface from './components/ChatInterface';
import DatabaseInspector from './components/DatabaseInspector';
import Ticker from './components/Ticker';
import { resetDatabase } from './api';
import { Trash2, Zap } from 'lucide-react';

function App() {
  const [dbRefreshKey, setDbRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    setDbRefreshKey(prev => prev + 1);
  };

  const handleReset = async () => {
    if (confirm("Are you sure you want to reset the database? All chunks will be deleted.")) {
      try {
        await resetDatabase();
        setDbRefreshKey(prev => prev + 1);
        alert("Database reset successfully.");
      } catch (e) {
        alert("Reset failed: " + e.message);
      }
    }
  };

  return (
    <div className="h-screen flex flex-col bg-mesh text-white overflow-hidden">
      
      {/* ── Stock Ticker Bar ── */}
      <Ticker />

      {/* ── Main Layout ── */}
      <div className="flex flex-1 overflow-hidden p-4 gap-4">
        
        {/* ── Left Column: Upload & Controls ── */}
        <div className="w-[280px] flex-shrink-0 flex flex-col gap-4">
          
          {/* Brand */}
          <div className="flex items-center gap-3 px-2">
            <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center shadow-glow-sm">
              <Zap className="w-5 h-5 text-primaryLight" />
            </div>
            <div>
              <h1 className="text-xl font-bold gradient-text tracking-tight">RAG Invest</h1>
              <p className="text-[10px] text-gray-500 uppercase tracking-[0.2em]">Investment Analysis</p>
            </div>
          </div>

          {/* Upload */}
          <UploadPanel onSuccess={handleUploadSuccess} />

          {/* Reset */}
          <button
            onClick={handleReset}
            className="mt-auto flex items-center justify-center gap-2 w-full px-4 py-2.5 glass rounded-xl text-red-400/80 text-xs font-medium hover:bg-error/10 hover:border-error/30 hover:text-red-400 transition-all duration-300"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Reset Database
          </button>
        </div>

        {/* ── Center Column: Chat ── */}
        <div className="flex-1 flex flex-col glass rounded-2xl overflow-hidden glow-border">
          <ChatInterface />
        </div>

        {/* ── Right Column: DB Inspector ── */}
        <div className="w-[320px] flex-shrink-0 flex flex-col glass rounded-2xl overflow-hidden glow-border">
          <DatabaseInspector key={dbRefreshKey} />
        </div>

      </div>
    </div>
  );
}

export default App;

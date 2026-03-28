import React, { useState, useEffect } from 'react';
import { getChunks, getDebug, checkBackendHealth } from '../api';
import { Database, ChevronDown, ChevronRight, Loader, WifiOff, Bug, Layers, Brain } from 'lucide-react';

export default function DatabaseInspector() {
  const [chunks, setChunks] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState(null);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const [debugInfo, setDebugInfo] = useState(null);
  const [showDebug, setShowDebug] = useState(false);

  const limit = 5;

  const fetchChunks = async () => {
    setLoading(true);
    try {
      const res = await getChunks(limit, page * limit);
      setChunks(res.data.chunks);
      setTotal(res.data.total);
    } catch (e) {
      setChunks([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const fetchDebugInfo = async () => {
    try {
      const res = await getDebug();
      setDebugInfo(res.data);
    } catch (e) {
      setDebugInfo(null);
    }
  };

  useEffect(() => {
    const checkHealth = async () => {
      const health = await checkBackendHealth();
      setBackendAvailable(health.available);
    };
    checkHealth();
    fetchChunks();
  }, [page]);

  useEffect(() => {
    if (showDebug && backendAvailable) fetchDebugInfo();
  }, [showDebug, backendAvailable]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-white/5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center">
          <Database className="w-4 h-4 text-accent" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-sm font-semibold text-gray-200">Chunks DB</h2>
          <p className="text-[10px] text-gray-500">Vector store inspector</p>
        </div>
        <span className="text-[10px] font-bold glass px-2.5 py-1 rounded-full text-primaryLight">
          {total}
        </span>
      </div>

      {!backendAvailable && (
        <div className="mx-4 mt-3 p-2 bg-error/8 border border-error/20 rounded-lg flex items-center gap-2">
          <WifiOff className="text-error w-3.5 h-3.5" />
          <span className="text-[10px] text-error">Disconnected</span>
        </div>
      )}

      {/* ── Debug Toggle ── */}
      <div className="px-4 pt-3">
        <button
          onClick={() => { setShowDebug(!showDebug); if (!showDebug) fetchDebugInfo(); }}
          className="flex items-center gap-1.5 text-[10px] font-medium glass px-2.5 py-1.5 rounded-lg transition-all hover:border-primary/30 hover:text-primaryLight text-gray-500"
        >
          <Bug className="w-3 h-3" />
          {showDebug ? 'Hide Debug' : 'Debug Info'}
        </button>
      </div>

      {/* ── Debug Panel ── */}
      {showDebug && (
        <div className="mx-4 mt-2 p-3 glass rounded-xl animate-fade-in">
          <h3 className="text-[10px] font-bold text-primaryLight mb-2 flex items-center gap-1.5 uppercase tracking-wider">
            <Brain className="w-3 h-3" /> System
          </h3>
          {debugInfo ? (
            <div className="space-y-1.5 text-[10px] font-mono">
              <div className="flex justify-between">
                <span className="text-gray-500">Model</span>
                <span className="text-accent">{debugInfo.model}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Embed Dim</span>
                <span className="text-accent">{debugInfo.embedding_dimension}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Chunks</span>
                <span className="text-accent">{debugInfo.total_chunks}</span>
              </div>
              {debugInfo.sample_chunks?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/5">
                  <p className="text-gray-500 mb-1">Embedding samples:</p>
                  {debugInfo.sample_chunks.map((chunk, i) => (
                    <div key={i} className="mb-1.5 p-1.5 bg-black/30 rounded-lg">
                      <p className="text-gray-400 truncate text-[9px]">{chunk.text_preview || chunk.text}</p>
                      <p className="text-accentTeal mt-0.5 text-[9px]">
                        [{(chunk.embedding_sample || chunk.embedding_first_5 || []).map(v => v?.toFixed(4)).join(', ')}…]
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-600 text-[10px]">Loading…</p>
          )}
        </div>
      )}

      {/* ── Chunks List ── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {loading ? (
          <div className="flex justify-center items-center h-24">
            <Loader className="w-6 h-6 animate-spin text-primaryLight" />
          </div>
        ) : chunks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-36 glass rounded-xl">
            <Layers className="w-6 h-6 text-gray-700 mb-2" />
            <p className="text-gray-600 text-xs font-medium">
              {backendAvailable ? 'No chunks yet' : 'Cannot connect'}
            </p>
            <p className="text-[10px] text-gray-700 mt-0.5">Upload a PDF to begin</p>
          </div>
        ) : (
          chunks.map((chunk) => {
            const isExpanded = expandedId === chunk.id;
            return (
              <div key={chunk.id} className="glass glass-hover rounded-xl overflow-hidden transition-all duration-200">
                <div
                  className="flex items-center justify-between cursor-pointer px-3 py-2.5"
                  onClick={() => setExpandedId(isExpanded ? null : chunk.id)}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] font-mono text-gray-600">#{chunk.id}</span>
                    <div className="w-1 h-1 bg-accent rounded-full flex-shrink-0" />
                    <span className="text-[11px] text-gray-400 font-medium">Doc {chunk.document_id}</span>
                  </div>
                  {isExpanded 
                    ? <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" /> 
                    : <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />}
                </div>

                {isExpanded && (
                  <div className="px-3 pb-3 pt-0 animate-fade-in">
                    <div className="border-t border-white/5 pt-2.5">
                      <p className="text-[11px] text-gray-400 leading-relaxed bg-black/20 p-2.5 rounded-lg max-h-32 overflow-y-auto mb-2">
                        {chunk.text_content}
                      </p>
                      <div className="bg-black/30 p-2.5 rounded-lg font-mono">
                        <div className="flex justify-between items-center mb-1.5 text-[9px]">
                          <span className="text-primaryLight font-bold uppercase tracking-wider">Embedding</span>
                          <span className="glass px-1.5 py-0.5 rounded text-accentTeal">{chunk.embedding?.length || 0}d</span>
                        </div>
                        <p className="text-[9px] text-gray-500 break-all leading-relaxed">
                          [<span className="text-accentTeal">{chunk.embedding?.slice(0, 8).map(v => v?.toFixed(4)).join(', ')}</span>
                          <span className="text-gray-600"> … {(chunk.embedding?.length || 0) - 8} more</span>]
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* ── Pagination ── */}
      {total > 0 && (
        <div className="flex justify-between items-center px-4 py-2.5 border-t border-white/5">
          <button
            disabled={page === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
            className="text-[10px] font-medium glass px-3 py-1.5 rounded-lg disabled:opacity-30 hover:border-primary/30 transition-all"
          >
            Prev
          </button>
          <span className="text-[10px] font-mono text-gray-500">
            {page + 1} / {Math.ceil(total / limit) || 1}
          </span>
          <button
            disabled={(page + 1) * limit >= total}
            onClick={() => setPage(p => p + 1)}
            className="text-[10px] font-medium glass px-3 py-1.5 rounded-lg disabled:opacity-30 hover:border-primary/30 transition-all"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

import React, { useState, useRef, useEffect } from 'react';
import { queryRAG, checkBackendHealth } from '../api';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, Loader, WifiOff, Sparkles, BookOpen } from 'lucide-react';

const SUGGESTIONS = [
  "how to deal with brokerage houses?",
  "what is theory of diversification?",
  "how to become intelligent investor?",
  "how to do business valuation?",
  "what is putting all eggs in one basket analogy?"
];

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages, loading]);

  useEffect(() => {
    const checkHealth = async () => {
      const health = await checkBackendHealth();
      setBackendAvailable(health.available);
    };
    checkHealth();
  }, []);

  const handleSend = async (queryText) => {
    if (!queryText.trim() || loading) return;

    if (!backendAvailable) {
      setMessages(prev => [...prev, {
        role: 'bot',
        content: 'Backend server is not running. Please start the backend on port 8000.',
        isError: true
      }]);
      return;
    }

    setInput('');
    const userMsg = { role: 'user', content: queryText };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await queryRAG(queryText);
      const botMsg = {
        role: 'bot',
        content: res.data.answer,
        sources: res.data.sources
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (e) {
      const errorMsg = e.code === 'BACKEND_NOT_RUNNING'
        ? 'Backend server is not running. Please start it on port 8000.'
        : `Error: ${e.response?.data?.detail || e.message}`;
      setMessages(prev => [...prev, { role: 'bot', content: errorMsg, isError: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Header ── */}
      <div className="px-5 py-3 border-b border-white/5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-primaryLight" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-200">AI Assistant</h2>
          <div className="flex items-center gap-1.5">
            <div className={`pulse-dot ${!backendAvailable ? 'bg-red-500' : ''}`} style={!backendAvailable ? {background:'#ef4444', boxShadow:'0 0 0 0 rgba(239,68,68,0.7)'} : {}}></div>
            <span className="text-[10px] text-gray-500">{backendAvailable ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      {!backendAvailable && (
        <div className="mx-4 mt-3 p-3 bg-error/10 border border-error/30 rounded-xl flex items-center gap-2 animate-fade-in">
          <WifiOff className="text-error w-4 h-4" />
          <span className="text-xs text-error">Backend not connected — start server on port 8000</span>
        </div>
      )}

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4 animate-float">
              <BookOpen className="w-8 h-8 text-primaryLight" />
            </div>
            <h3 className="text-lg font-semibold gradient-text mb-2">Ask About Your Investments</h3>
            <p className="text-xs text-gray-500 max-w-md mb-6">
              Upload an investment PDF, then ask questions. The AI retrieves relevant chunks and generates grounded answers.
            </p>
            <div className="flex flex-wrap justify-center gap-2 max-w-lg">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(s)}
                  disabled={!backendAvailable || loading}
                  className="text-[11px] font-medium glass glass-hover px-3 py-2 rounded-full transition-all text-gray-400 hover:text-primaryLight disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 animate-slide-up ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'bot' && (
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-1
                ${msg.isError ? 'bg-error/15 border border-error/30' : 'bg-primary/15 border border-primary/30'}`}>
                <Bot className={`w-4 h-4 ${msg.isError ? 'text-error' : 'text-primaryLight'}`} />
              </div>
            )}
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-lg
              ${msg.role === 'user'
                ? 'bg-gradient-to-br from-primary to-primary/80 text-white rounded-tr-md'
                : msg.isError
                  ? 'bg-error/8 border border-error/20 text-error rounded-tl-md'
                  : 'glass rounded-tl-md'}`}>
              <div className="prose-chat text-sm leading-relaxed">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <p className="text-[10px] font-bold text-gray-500 mb-2 uppercase tracking-wider">Sources ({msg.sources.length})</p>
                  <div className="flex flex-col gap-1.5">
                    {msg.sources.map(src => (
                      <div key={src.id} className="text-[11px] glass px-3 py-2 rounded-lg">
                        <div className="flex justify-between items-center text-gray-500 mb-1">
                          <span className="font-mono">Chunk #{src.id}</span>
                          <span className="text-accent font-mono font-semibold">{(src.score).toFixed(3)}</span>
                        </div>
                        <p className="text-gray-400 line-clamp-2 hover:line-clamp-none transition-all cursor-pointer">{src.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center animate-pulse flex-shrink-0">
              <Bot className="w-4 h-4 text-primaryLight" />
            </div>
            <div className="glass rounded-2xl rounded-tl-md px-4 py-3 flex items-center gap-3">
              <Loader className="w-4 h-4 animate-spin text-primaryLight" />
              <span className="text-xs font-medium text-gray-400">Analyzing documents...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input ── */}
      <div className="px-5 py-3 border-t border-white/5">
        {messages.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSend(s)}
                disabled={!backendAvailable || loading}
                className="text-[10px] font-medium glass px-2.5 py-1.5 rounded-full transition-all text-gray-500 hover:text-primaryLight hover:border-primary/30 disabled:opacity-30"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 glass rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-primary/50 focus:shadow-glow-sm transition-all disabled:opacity-40 placeholder-gray-600"
            placeholder={backendAvailable ? "Ask about your investment documents..." : "Start backend to chat"}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend(input)}
            disabled={!backendAvailable || loading}
          />
          <button
            onClick={() => handleSend(input)}
            disabled={loading || !input.trim() || !backendAvailable}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary/80 text-white flex items-center justify-center transition-all disabled:opacity-30 disabled:from-gray-700 disabled:to-gray-800 hover:shadow-glow-md active:scale-95"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

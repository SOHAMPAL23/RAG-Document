import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile, getUploadProgress, checkBackendHealth } from '../api';
import { UploadCloud, CheckCircle, AlertCircle, Loader, WifiOff, FileText } from 'lucide-react';

export default function UploadPanel({ onSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const [backendAvailable, setBackendAvailable] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      const health = await checkBackendHealth();
      setBackendAvailable(health.available);
      if (!health.available) {
        setError('Backend server is not running. Start on port 8000.');
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const pollProgress = async () => {
    try {
      const res = await getUploadProgress();
      setProgress(res.data);
      if (res.data.status === 'completed') {
        setUploading(false);
        onSuccess();
      } else if (res.data.status === 'error') {
        setError(res.data.message);
        setUploading(false);
      } else {
        setTimeout(pollProgress, 1000);
      }
    } catch (e) {
      setTimeout(pollProgress, 2000);
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file || !backendAvailable) {
      if (!backendAvailable) setError('Backend not running.');
      return;
    }

    setUploading(true);
    setProgress({ status: 'started', message: 'Uploading...', progress: 0 });
    setError(null);

    try {
      await uploadFile(file);
      pollProgress();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Upload failed');
      setUploading(false);
    }
  }, [backendAvailable]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false
  });

  const progressPercent = progress?.progress ? Math.round(progress.progress * 100) : 0;

  return (
    <div className="glass rounded-2xl p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-accent/15 flex items-center justify-center">
          <FileText className="w-3.5 h-3.5 text-accent" />
        </div>
        <h2 className="text-sm font-semibold text-gray-200">Upload PDF</h2>
      </div>

      {!backendAvailable && (
        <div className="p-2.5 bg-error/8 border border-error/20 rounded-xl flex items-center gap-2 animate-fade-in">
          <WifiOff className="text-error w-3.5 h-3.5 flex-shrink-0" />
          <span className="text-[10px] text-error font-medium">Backend not connected</span>
        </div>
      )}

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`border border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-300 group
          ${isDragActive 
            ? 'border-primary bg-primary/8 scale-[1.02]' 
            : 'border-white/10 hover:border-primary/40 hover:bg-primary/5'}
          ${uploading || !backendAvailable ? 'opacity-40 pointer-events-none' : ''}`}
      >
        <input {...getInputProps()} />
        <UploadCloud className={`w-8 h-8 mx-auto mb-2 transition-all duration-300 group-hover:scale-110
          ${isDragActive ? 'text-primaryLight animate-float' : 'text-gray-600 group-hover:text-primaryLight'}`} />
        {isDragActive ? (
          <p className="text-xs font-medium text-primaryLight">Drop here …</p>
        ) : (
          <div>
            <p className="text-xs font-medium text-gray-400">Drag & drop investment PDF</p>
            <p className="text-[10px] text-gray-600 mt-0.5">or click to browse</p>
          </div>
        )}
      </div>

      {/* Progress */}
      {(uploading || progress) && !error && (
        <div className="glass rounded-xl p-3 animate-fade-in">
          <div className="flex items-center gap-2.5 mb-2">
            {progress?.status === 'completed' ? (
              <CheckCircle className="text-accent w-4 h-4 flex-shrink-0" />
            ) : (
              <Loader className="text-primaryLight w-4 h-4 animate-spin flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-semibold text-gray-300 capitalize">{progress?.status || 'Processing'}</p>
              <p className="text-[10px] text-gray-500 truncate">{progress?.message || 'Please wait...'}</p>
            </div>
          </div>
          {/* Progress bar */}
          <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-primary to-primaryLight rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-2.5 bg-error/8 border border-error/20 rounded-xl flex gap-2 animate-fade-in">
          <AlertCircle className="w-3.5 h-3.5 text-error flex-shrink-0 mt-0.5" />
          <p className="text-[10px] text-error leading-relaxed">{error}</p>
        </div>
      )}
    </div>
  );
}

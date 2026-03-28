import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Create axios instance with timeout and error handling
export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for better error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      error.message = 'Backend server is not running. Please start the backend on port 8000.';
      error.code = 'BACKEND_NOT_RUNNING';
    } else if (error.response.status === 500) {
      error.message = error.response.data.detail || 'Server error occurred';
    }
    return Promise.reject(error);
  }
);

export const getStatus = () => api.get('/status');
export const getHealth = () => api.get('/health');
export const resetDatabase = () => api.delete('/reset');
export const getUploadProgress = () => api.get('/upload/progress');
export const getChunks = (limit = 20, offset = 0) => api.get(`/chunks?limit=${limit}&offset=${offset}`);
export const queryRAG = (queryStr) => api.post('/query', { query: queryStr });
export const getDebug = () => api.get('/debug');

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Check if backend is available
export const checkBackendHealth = async () => {
  try {
    const response = await api.get('/health');
    return { available: true, status: response.data };
  } catch (error) {
    return { available: false, error: error.message };
  }
};

import axios from 'axios';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const apiUrl = (path) => `${API_BASE}${path}`;
const API = axios.create({ baseURL: API_BASE || undefined });

API.interceptors.response.use(
  (response) => response,
  (error) => {
    error.message = error?.response?.data?.detail || error?.response?.data?.message || error.message || 'Request failed';
    return Promise.reject(error);
  }
);

export const getUsers = () => API.get('/api/users');
export const createUser = (data) => API.post('/api/users', data);
export const deleteUser = (userId) => API.delete(`/api/users/${userId}`);
export const getProfile = (userId) => API.get(`/api/profile/${userId}`);
export const updateProfile = (userId, data) => API.put(`/api/profile/${userId}`, data);
export const getDashboard = (userId) => API.get(`/api/dashboard/${userId}`);
export const getNutritionDay = (userId, day) => API.get(`/api/nutrition-day/${userId}`, { params: { day } });
export const resetTodayNutrition = (userId) => API.post(`/api/nutrition-day/${userId}/reset-today`);
export const getFormulaBreakdown = (userId, metric) => API.get(`/api/formula-breakdown/${userId}/${metric}`);
export const uploadFile = (formData) => API.post('/api/ingest', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const uploadFaceAge = (formData) => API.post('/api/face-age', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const uploadAppleHealth = (formData) => API.post('/api/apple-health', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const uploadMeal = (payload) => {
  if (payload instanceof FormData) {
    return API.post('/api/meal', payload, { headers: { 'Content-Type': 'multipart/form-data' } });
  }
  return API.post('/api/meal', payload);
};
export const logWater = (userId, amount_ml) => API.post('/api/water', { user_id: userId, amount_ml });
export const simulate = (userId, changes) => API.post('/api/simulate', { user_id: userId, changes });
export const getGamification = (userId) => API.get(`/api/gamification/${userId}`);
export const logAction = (userId, action) => API.post(`/api/gamification/${userId}/action`, { action });
export const getLeaderboard = () => API.get('/api/gamification/leaderboard');
export const createFamily = (name, userId) => API.post('/api/family', { name, created_by: userId });
export const joinFamily = (joinCode, userId, relationship, privacy) => API.post('/api/family/join', { join_code: joinCode, user_id: userId, relationship, privacy_level: privacy });
export const getFamily = (familyId) => API.get(`/api/family/${familyId}`);
export const getReminders = (userId) => API.get(`/api/reminders/${userId}`);
export const getSmartReminders = (userId) => API.post(`/api/reminders/smart/${userId}`);
export const getDataFreshness = (userId) => API.get(`/api/data-freshness/${userId}`);
export const getAlerts = (userId) => API.get(`/api/alerts/${userId}`);
export const notifyDoctor = (userId, alertId) => API.post(`/api/alerts/${userId}/notify-doctor`, { alert_id: alertId });
export const getSpecialists = (userId) => API.get(`/api/specialists/${userId}`);
export const getWorkouts = (userId) => API.get(`/api/workouts/${userId}`);
export const logWorkout = (userId, data) => API.post(`/api/workouts/${userId}`, data);
export const getWorkoutSummary = (userId) => API.get(`/api/workouts/${userId}/summary`);
export const getWorkoutTargets = (userId) => API.get(`/api/workouts/${userId}/targets`);
export const analyzePosture = (formData) => API.post('/api/posture/analyze', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const getPostureHistory = (userId) => API.get(`/api/posture/${userId}`);
export const savePostureReading = (userId, reading) => API.post('/api/posture', { user_id: userId, ...reading });
export const getSpotifySync = (userId) => API.get(`/api/spotify/sync/${userId}`);
export const getSpotifyStatus = (userId) => API.get(`/api/spotify/status/${userId}`);
export const getSpotifyMood = (userId) => API.get(`/api/spotify/mood/${userId}`);
export const getResearchFeatures = (userId) => API.get(`/api/research-features/${userId}`);
export const getReflections = (userId) => API.get(`/api/reflections/${userId}`);
export const clearReflections = (userId) => API.delete(`/api/reflections/${userId}`);
export const getMobileHealth = () => API.get('/api/mobile/health');
export const getMobileProfile = (userId) => API.get(`/api/mobile/profile/${userId}`);
export const getServerInfo = () => API.get('/api/server-info');

export const streamChat = async (endpoint, userId, message, history, onText, onReasoning, onDone, context = '') => {
  const response = await fetch(apiUrl(`/api/chat/${endpoint}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, message, history, context })
  });
  if (!response.ok) {
    let detail = 'Streaming request failed';
    try {
      const payload = await response.json();
      detail = payload?.detail || payload?.message || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  if (!response.body) {
    throw new Error('Streaming response body is unavailable');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    onDone?.();
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'text') onText(data.content);
          else if (data.type === 'thought' || data.type === 'action' || data.type === 'observation') onReasoning(data);
          else if (data.type === 'done') finish();
        } catch {
          // ignore malformed chunks
        }
      }
      if (done) break;
    }

    if (buffer.startsWith('data: ')) {
      try {
        const data = JSON.parse(buffer.slice(6));
        if (data.type === 'done') finish();
      } catch {
        // ignore trailing malformed chunk
      }
    }
  } finally {
    reader.releaseLock();
    finish();
  }
};

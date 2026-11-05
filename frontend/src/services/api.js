import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing = null;

function expireSession() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  if (window.location.pathname !== '/login') window.location.assign('/login');
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const authEndpoint = /\/auth\/(login|refresh)\/?$/.test(original?.url || '');

    if (status === 403 || status !== 401 || authEndpoint) return Promise.reject(error);
    if (original?._retry || !localStorage.getItem('refresh_token')) {
      expireSession();
      return Promise.reject(error);
    }

    original._retry = true;
    refreshing ||= axios.post(`${api.defaults.baseURL}/auth/refresh/`, {
      refresh: localStorage.getItem('refresh_token'),
    });

    try {
      const { data } = await refreshing;
      localStorage.setItem('access_token', data.access);
      original.headers.Authorization = `Bearer ${data.access}`;
      return api(original);
    } catch (refreshError) {
      expireSession();
      return Promise.reject(refreshError);
    } finally {
      refreshing = null;
    }
  },
);

export default api;

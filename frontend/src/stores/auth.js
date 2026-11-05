import { defineStore } from 'pinia';
import api from '../services/api';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    token: localStorage.getItem('access_token') || null,
    loading: false,
  }),
  actions: {
    setAuth(data) {
      this.user = data.user;
      this.token = data.access;
      localStorage.setItem('user', JSON.stringify(data.user));
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
    },
    logout() {
      this.user = null;
      this.token = null;
      this.loading = false;
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    },
    async fetchCurrentUser() {
      if (!this.token) return;

      this.loading = true;
      try {
        const { data } = await api.get('/usuarios/me/');
        this.user = data;
        localStorage.setItem('user', JSON.stringify(data));
      } catch (error) {
        this.logout();
      } finally {
        this.loading = false;
      }
    },
  },
});

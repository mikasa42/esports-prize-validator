import { useEffect, useRef, useState } from 'react';
import api, { API_URL } from '../api';

export default function useAuth() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const request = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    api.get(`${API_URL}/api/auth/me`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setUser(data); })
      .catch(error => {
        if (!controller.signal.aborted && error.response?.status !== 401) setError('Não foi possível verificar sua sessão. Tente entrar novamente.');
      })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
    const interceptor = api.interceptors.response.use(response => response, error => {
      if (error.response?.status === 401 && !/\/api\/auth\/(login|cadastro|me)(?:$|\?)/.test(error.config?.url || '')) {
        request.current?.abort();
        setUser(null);
        setError('Sua sessão expirou. Entre novamente.');
      }
      return Promise.reject(error);
    });
    return () => {
      controller.abort();
      request.current?.abort();
      api.interceptors.response.eject(interceptor);
    };
  }, []);

  async function authenticate(mode, fields) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError('');
    try {
      const { data } = await api.post(`${API_URL}/api/auth/${mode}`, fields, { signal: controller.signal });
      if (!controller.signal.aborted) setUser(data);
    } catch (error) {
      if (controller.signal.aborted) return;
      const detail = error.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Não foi possível concluir. Confira os campos e tente novamente.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    setError('');
    try {
      await api.post(`${API_URL}/api/auth/logout`);
      setUser(null);
    } catch {
      setError('Não foi possível encerrar sua sessão. Tente novamente.');
    } finally {
      setBusy(false);
    }
  }

  return { user, checking, busy, error, authenticate, logout, updateUser: setUser };
}

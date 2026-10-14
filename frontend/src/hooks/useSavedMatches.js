import { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';
export default function useSavedMatches({ page, pageSize, search, refresh }) {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading', data: null, error: '' });
    async function load() {
      try {
        const { data } = await axios.get(`${API_URL}/api/historico`, {
          params: { limit: pageSize, offset: (page - 1) * pageSize, busca: search },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setState({ status: 'success', data, error: '' });
      } catch (error) {
        if (controller.signal.aborted) return;
        const detail = error.response?.data?.detail;
        setState({ status: 'error', data: null, error: typeof detail === 'string' ? detail : 'Não foi possível carregar o histórico. Tente novamente.' });
      }
    }
    load();
    return () => controller.abort();
  }, [page, pageSize, search, refresh]);
  return state;
}

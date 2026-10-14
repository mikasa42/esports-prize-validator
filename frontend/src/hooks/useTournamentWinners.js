import { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';
export default function useTournamentWinners({ year, tournament, criterion, refresh }) {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' });
  useEffect(() => {
    const controller = new AbortController();
    setState(previous => ({ ...previous, status: 'loading', error: '' }));
    async function load() {
      try {
        const { data } = await axios.get(`${API_URL}/api/ganhadores`, {
          params: { ...(year ? { ano: Number(year) } : {}), ...(tournament ? { torneio: tournament } : {}), criterio: criterion },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setState({ status: 'success', data, error: '' });
      } catch (error) {
        if (controller.signal.aborted) return;
        const detail = error.response?.data?.detail;
        setState(previous => ({ ...previous, status: 'error', error: typeof detail === 'string' ? detail : 'Não foi possível carregar os ganhadores. Tente novamente.' }));
      }
    }
    load();
    return () => controller.abort();
  }, [year, tournament, criterion, refresh]);
  return state;
}

import { useEffect, useState } from 'react';

export default function usePublicResults(year, tournament, refresh) {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' });
  useEffect(() => {
    const controller = new AbortController();
    setState(current => ({ ...current, status: 'loading', error: '' }));
    const params = new URLSearchParams();
    if (year) params.set('ano', year);
    if (tournament) params.set('torneio', tournament);
    async function load() {
      try {
        const response = await fetch(`${process.env.REACT_APP_API_URL || ''}/api/publico/resultados?${params}`, { signal: controller.signal, credentials: 'omit' });
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Não foi possível carregar os resultados.');
        if (!controller.signal.aborted) setState({ status: 'success', data, error: '' });
      } catch (error) {
        if (!controller.signal.aborted) setState(current => ({ ...current, status: 'error', error: error.message || 'Não foi possível carregar os resultados.' }));
      }
    }
    load();
    return () => controller.abort();
  }, [year, tournament, refresh]);
  return state;
}

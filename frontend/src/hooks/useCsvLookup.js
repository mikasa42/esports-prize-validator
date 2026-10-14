import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';
export default function useCsvLookup() {
  const [state, setState] = useState({ status: 'idle', data: null, error: '' });
  const request = useRef(null);
  useEffect(() => () => request.current?.abort(), []);
  const clear = () => {
    request.current?.abort();
    setState({ status: 'idle', data: null, error: '' });
  };
  const submit = async (file, criterio) => {
    request.current?.abort();
    if (!file || !file.name.toLowerCase().endsWith('.csv')) {
      setState({ status: 'error', data: null, error: 'Selecione um arquivo .csv.' });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setState({ status: 'error', data: null, error: 'O CSV deve ter no máximo 10 MB.' });
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    const form = new FormData();
    form.append('arquivo', file);
    form.append('criterio', criterio);
    setState({ status: 'loading', data: null, error: '' });
    try {
      const { data } = await axios.post(`${API_URL}/api/consultar-csv`, form, { signal: controller.signal });
      if (!controller.signal.aborted) setState({ status: 'success', data, error: '' });
    } catch (error) {
      if (controller.signal.aborted) return;
      const detail = error.response?.data?.detail;
      setState({ status: 'error', data: null, error: typeof detail === 'string' ? detail : 'Não foi possível consultar as partidas. Tente novamente.' });
    }
  };
  return { ...state, submit, clear };
}

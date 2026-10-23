import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';
const initial = { status: 'idle', data: null, error: '', progress: null };
const message = (error, fallback) => typeof error.response?.data?.detail === 'string' ? error.response.data.detail : fallback;

export default function useCsvLookup() {
  const [state, setState] = useState(initial);
  const [queries, setQueries] = useState([]);
  const [selected, setSelected] = useState(null);
  const request = useRef(null);
  const generation = useRef(0);
  const stop = useCallback(() => { generation.current += 1; request.current?.abort(); }, []);
  const open = useCallback(id => {
    stop();
    setState({ ...initial, status: 'loading' });
    setSelected(id);
  }, [stop]);

  useEffect(() => {
    const controller = new AbortController();
    const version = generation.current;
    axios.get(`${API_URL}/api/consultas`, { signal: controller.signal }).then(({ data }) => {
      if (controller.signal.aborted) return;
      setQueries(data.consultas);
      if (version === generation.current && data.consultas.length) open(data.consultas[0].id);
    }).catch(error => {
      if (!controller.signal.aborted && version === generation.current) {
        setState({ ...initial, status: 'error', error: message(error, 'Não foi possível recuperar as consultas anteriores. Recarregue a página para tentar novamente.') });
      }
    });
    return () => { controller.abort(); stop(); };
  }, [open, stop]);

  useEffect(() => {
    if (!selected) return undefined;
    const controller = new AbortController();
    request.current = controller;
    let timer;
    const poll = async () => {
      try {
        const { data: progress } = await axios.get(`${API_URL}/api/consultas/${selected}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setQueries(previous => [progress, ...previous.filter(item => item.id !== selected)].slice(0, 20));
        if (progress.status === 'concluida') {
          const { data } = await axios.get(`${API_URL}/api/consultas/${selected}/resultado`, { signal: controller.signal });
          if (!controller.signal.aborted) setState({ status: 'success', data, progress, error: '' });
          return;
        }
        if (progress.status === 'erro') {
          setState({ status: 'error', data: null, progress, error: progress.erro });
          return;
        }
        setState({ status: 'loading', data: null, progress, error: '' });
        timer = setTimeout(poll, 2500);
      } catch (error) {
        if (controller.signal.aborted) return;
        const terminal = [401, 403, 404, 422].includes(error.response?.status);
        setState(previous => ({ ...previous, status: terminal ? 'error' : 'loading',
          error: message(error, 'Não foi possível atualizar o andamento. Tentaremos novamente automaticamente.') }));
        if (!terminal) timer = setTimeout(poll, 5000);
      }
    };
    poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [selected]);

  const clear = () => { stop(); setSelected(null); setState(initial); };
  const submit = async (file, criterio) => {
    stop();
    setSelected(null);
    if (!file || !file.name.toLowerCase().endsWith('.csv') || file.size > 10 * 1024 * 1024) {
      setState({ ...initial, status: 'error', error: !file || !file.name.toLowerCase().endsWith('.csv') ? 'Selecione um arquivo .csv.' : 'O CSV deve ter no máximo 10 MB.' });
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    const form = new FormData();
    form.append('arquivo', file);
    form.append('criterio', criterio);
    setState({ ...initial, status: 'loading' });
    try {
      const { data } = await axios.post(`${API_URL}/api/consultas`, form, { signal: controller.signal });
      if (!controller.signal.aborted) {
        setState({ ...initial, status: 'loading', progress: data });
        setSelected(data.id);
      }
    } catch (error) {
      if (!controller.signal.aborted) setState({ ...initial, status: 'error',
        error: message(error, 'Não foi possível confirmar o envio. Recarregue a página para conferir se a consulta foi recebida antes de reenviar.') });
    }
  };
  return { ...state, queries, selected, open, submit, clear };
}

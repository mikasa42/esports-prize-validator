import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import useCsvLookup from './useCsvLookup';

jest.mock('axios');
let root, container, lookup;
function Harness() { lookup = useCsvLookup(); return <span>{lookup.status}</span>; }
beforeEach(() => {
  jest.resetAllMocks();
  jest.useFakeTimers();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); jest.useRealTimers(); });
const progress = (status, processadas = 0) => ({ id: 'saved', nome_arquivo: 'a.csv', status, processadas, total: 2 });
async function mount() { await act(async () => root.render(<Harness />)); }
async function tick(ms = 2500) { await act(async () => jest.advanceTimersByTime(ms)); }

test('recupera consulta no servidor e acompanha progresso até obter resultado', async () => {
  axios.get.mockResolvedValueOnce({ data: { consultas: [progress('pendente')] } })
    .mockResolvedValueOnce({ data: progress('processando', 1) })
    .mockResolvedValueOnce({ data: progress('concluida', 2) })
    .mockResolvedValueOnce({ data: { partidas: [], falhas: [] } });
  await mount();
  expect(lookup.progress.processadas).toBe(1);
  expect(lookup.status).toBe('loading');
  await tick();
  expect(lookup.status).toBe('success');
  expect(axios.get).toHaveBeenLastCalledWith('/api/consultas/saved/resultado', expect.anything());
  await tick(10000);
  expect(axios.get).toHaveBeenCalledTimes(4);
});

test('falha transitória no acompanhamento é recuperada automaticamente', async () => {
  axios.get.mockResolvedValueOnce({ data: { consultas: [progress('pendente')] } })
    .mockRejectedValueOnce({ response: { status: 503 } })
    .mockResolvedValueOnce({ data: progress('processando', 1) });
  await mount();
  expect(lookup.error).toContain('automaticamente');
  await tick(5000);
  expect(lookup.error).toBe('');
  expect(lookup.progress.processadas).toBe(1);
});

test('falha definitiva encerra acompanhamento sem pedir resultado', async () => {
  axios.get.mockResolvedValueOnce({ data: { consultas: [progress('pendente')] } })
    .mockResolvedValueOnce({ data: { ...progress('erro'), erro: 'Falha no processamento' } });
  await mount();
  expect(lookup.status).toBe('error');
  expect(lookup.error).toBe('Falha no processamento');
  await tick(10000);
  expect(axios.get).toHaveBeenCalledTimes(2);
});

test('trocar consulta aborta a anterior e ignora sua resposta atrasada', async () => {
  let resolveOld;
  axios.get.mockResolvedValueOnce({ data: { consultas: [progress('pendente')] } })
    .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce({ data: { ...progress('processando'), id: 'new' } });
  await mount();
  const signal = axios.get.mock.calls[1][1].signal;
  await act(async () => lookup.open('new'));
  expect(signal.aborted).toBe(true);
  await act(async () => resolveOld({ data: progress('erro') }));
  expect(lookup.selected).toBe('new');
  expect(lookup.status).toBe('loading');
});

test('sair da tela cancela polling sem enviar cancelamento da tarefa', async () => {
  axios.get.mockResolvedValueOnce({ data: { consultas: [progress('pendente')] } })
    .mockResolvedValueOnce({ data: progress('processando') });
  await mount();
  await act(async () => lookup.clear());
  await tick(10000);
  expect(lookup.status).toBe('idle');
  expect(axios.get).toHaveBeenCalledTimes(2);
  expect(axios.post).not.toHaveBeenCalled();
});

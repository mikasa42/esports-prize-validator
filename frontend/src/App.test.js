import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import App from './App';

jest.mock('axios');
let container;
let root;
beforeEach(async () => {
  jest.resetAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root.render(<App />));
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function submit() {
  const file = new File(['id_partida\nMATCH-101\nMATCH-202'], 'partidas.csv', { type: 'text/csv' });
  const input = container.querySelector('input[type="file"]');
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  await act(async () => input.dispatchEvent(new Event('change', { bubbles: true })));
  await act(async () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  return file;
}
const match = (id, origem) => ({ match_id_externo: id, origem, data_partida: '2026-09-01', rodada: 1,
  confronto: 'Alpha vs Beta', participantes: [{ time_nick: 'Alpha / Ana', minutos: 35, kills: 12, venceu: true }] });

test('abre sem nome de torneio e aguarda CSV para consultar', () => {
  expect(container.textContent).not.toContain('Nome do torneio');
  expect(container.querySelector('input[type="text"]')).toBeNull();
  expect(axios.get).not.toHaveBeenCalled();
  expect(axios.post).not.toHaveBeenCalled();
});

test('envia apenas CSV e critério e mostra partidas retornadas pela API', async () => {
  axios.post.mockResolvedValue({ data: {
    total_solicitado: 2, partidas: [match('MATCH-101', 'api'), match('MATCH-202', 'api')], falhas: [],
    classificacao: [{ time: 'Alpha', vitorias: 2 }],
    premios: { criterio_utilizado: 'kills', premio_jogadores: [{ time: 'Alpha', jogador: 'Ana', total_kills: 24, premio_rs: 5000 }] },
  } });
  await act(async () => {
    const select = container.querySelector('select');
    select.value = 'kills';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
  const file = await submit();
  const [url, form] = axios.post.mock.calls[0];
  expect(url).toBe('/api/consultar-csv');
  expect(form.get('arquivo')).toBe(file);
  expect(form.get('criterio')).toBe('kills');
  expect(form.has('nome')).toBe(false);
  expect(axios.post).toHaveBeenCalledTimes(1);
  expect(axios.get).not.toHaveBeenCalled();
  expect(container.querySelectorAll('details')).toHaveLength(2);
  expect(container.textContent).not.toContain('Banco de dados');
  expect(container.textContent).toContain('salvas para consultas posteriores.');
  expect(container.textContent).toContain('API oficial');
  expect(container.textContent).toContain('R$ 5000.00');
});

test('mantém partidas encontradas visíveis quando outros IDs falham', async () => {
  axios.post.mockResolvedValue({ data: {
    total_solicitado: 2, partidas: [match('MATCH-101', 'api')],
    falhas: [{ match_id_externo: 'MATCH-202', erro: 'API indisponível' }], classificacao: [], premios: null,
  } });
  await submit();
  expect(container.querySelector('details').textContent).toContain('Alpha / Ana');
  expect(container.querySelector('[role="alert"]').textContent).toContain('MATCH-202: API indisponível');
  expect(container.querySelectorAll('section > table tbody tr')).toHaveLength(0);
});

test('limpa resultados anteriores quando uma nova consulta falha', async () => {
  axios.post.mockResolvedValueOnce({ data: { total_solicitado: 1, partidas: [match('MATCH-101', 'api')], falhas: [], classificacao: [], premios: null } });
  await submit();
  expect(container.querySelector('details')).not.toBeNull();
  axios.post.mockRejectedValueOnce({ response: { data: { detail: 'CSV sem IDs' } } });
  await submit();
  expect(container.querySelector('details')).toBeNull();
  expect(container.querySelector('[role="alert"]').textContent).toBe('CSV sem IDs');
});

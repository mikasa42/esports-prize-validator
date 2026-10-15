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
async function click(button) {
  await act(async () => button.dispatchEvent(new MouseEvent('click', { bubbles: true })));
}
async function navigate(label) {
  await click([...container.querySelectorAll('nav button')].find(button => button.textContent === label));
}
async function submit() {
  const file = new File(['id_partida\nMATCH-101\nMATCH-202'], 'partidas.csv', { type: 'text/csv' });
  const input = container.querySelector('input[type="file"]');
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  await act(async () => input.dispatchEvent(new Event('change', { bubbles: true })));
  await act(async () => container.querySelector('.upload-panel form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  return file;
}
const match = (id, origem = 'api') => ({ match_id_externo: id, origem, data_partida: '2026-09-01', rodada: 1,
  confronto: 'Alpha vs Beta', participantes: [{ time_nick: 'Alpha / Ana', minutos: 35, kills: 12, venceu: true }] });
const result = (partidas, extra = {}) => ({ total_solicitado: partidas.length, partidas, falhas: [], classificacao: [], premios: null, ...extra });

test('abre com informações e quatro opções na navegação horizontal', () => {
  expect(container.querySelectorAll('nav button')).toHaveLength(4);
  expect(container.querySelector('nav [aria-current="page"]').textContent).toBe('Sobre o site');
  expect(container.textContent).toContain('Cada partida conta.');
  expect(axios.get).not.toHaveBeenCalled();
  expect(axios.post).not.toHaveBeenCalled();
});

test('envia CSV e critério e mostra resultados, jogadores e premiações', async () => {
  await navigate('Nova consulta');
  axios.post.mockResolvedValue({ data: result([match('MATCH-101'), match('MATCH-202')], {
    classificacao: [{ time: 'Alpha', vitorias: 2 }],
    premios: { criterio_utilizado: 'kills', premio_jogadores: [{ time: 'Alpha', jogador: 'Ana', total_kills: 24, premio_rs: 5000 }] },
  }) });
  await click(container.querySelector('input[value="kills"]'));
  const file = await submit();
  const [url, form] = axios.post.mock.calls[0];
  expect(url).toBe('/api/consultar-csv');
  expect(form.get('arquivo')).toBe(file);
  expect(form.get('criterio')).toBe('kills');
  expect(axios.post).toHaveBeenCalledTimes(1);
  expect(axios.get).not.toHaveBeenCalled();
  expect(container.querySelectorAll('.matches-table > tbody > tr')).toHaveLength(2);
  expect(container.querySelector('.matches-table').textContent).not.toContain('Origem');
  expect(container.textContent).toContain('5.000,00');
  await click(container.querySelector('[aria-label="Ver jogadores de MATCH-101"]'));
  expect(container.querySelector('.players-table').textContent).toContain('Alpha / Ana');
});

test('pagina os resultados da consulta sem fazer novas requisições', async () => {
  await navigate('Nova consulta');
  axios.post.mockResolvedValue({ data: result(Array.from({ length: 6 }, (_, index) => match(`MATCH-${index + 1}`))) });
  await submit();
  expect(container.querySelectorAll('.matches-table > tbody > tr')).toHaveLength(5);
  expect(container.querySelector('[aria-label="Página anterior"]').disabled).toBe(true);
  await click(container.querySelector('[aria-label="Próxima página"]'));
  expect(container.querySelectorAll('.matches-table > tbody > tr')).toHaveLength(1);
  expect(container.querySelector('.matches-table').textContent).toContain('MATCH-6');
  expect(container.querySelector('[aria-label="Próxima página"]').disabled).toBe(true);
  expect(axios.post).toHaveBeenCalledTimes(1);
  expect(axios.get).not.toHaveBeenCalled();
});

test('mantém resultados disponíveis quando outros IDs falham', async () => {
  await navigate('Nova consulta');
  axios.post.mockResolvedValue({ data: result([match('MATCH-101')], {
    total_solicitado: 2, falhas: [{ match_id_externo: 'MATCH-202', erro: 'API indisponível' }],
  }) });
  await submit();
  expect(container.querySelector('.matches-table').textContent).toContain('MATCH-101');
  expect(container.querySelector('[role="alert"]').textContent).toContain('MATCH-202: API indisponível');
  expect(container.querySelector('.prize-panel')).toBeNull();
});

test('limpa resultados anteriores quando uma nova consulta falha', async () => {
  await navigate('Nova consulta');
  axios.post.mockResolvedValueOnce({ data: result([match('MATCH-101')]) });
  await submit();
  expect(container.querySelector('.matches-table')).not.toBeNull();
  axios.post.mockRejectedValueOnce({ response: { data: { detail: 'CSV sem IDs' } } });
  await submit();
  expect(container.querySelector('.matches-table')).toBeNull();
  expect(container.querySelector('[role="alert"]').textContent).toBe('CSV sem IDs');
});

test('consulta histórico no servidor e busca a próxima página', async () => {
  axios.get.mockResolvedValueOnce({ data: { partidas: [match('MATCH-101', 'banco')], total: 6 } });
  await navigate('Histórico');
  expect(axios.get).toHaveBeenLastCalledWith('/api/historico', expect.objectContaining({ params: { limit: 5, offset: 0, busca: '' } }));
  expect(container.querySelector('.matches-table').textContent).not.toContain('Banco local');
  axios.get.mockResolvedValueOnce({ data: { partidas: [match('MATCH-106', 'banco')], total: 6 } });
  await click(container.querySelector('[aria-label="Próxima página"]'));
  expect(axios.get).toHaveBeenLastCalledWith('/api/historico', expect.objectContaining({ params: { limit: 5, offset: 5, busca: '' } }));
  expect(container.querySelector('.matches-table').textContent).toContain('MATCH-106');
  expect(axios.post).not.toHaveBeenCalled();
});

test('busca no histórico volta para a primeira página', async () => {
  axios.get.mockResolvedValue({ data: { partidas: [match('MATCH-101', 'banco')], total: 10 } });
  await navigate('Histórico');
  await click(container.querySelector('[aria-label="Próxima página"]'));
  const input = container.querySelector('input[type="search"]');
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'Alpha');
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  axios.get.mockResolvedValue({ data: { partidas: [match('MATCH-101', 'banco')], total: 1 } });
  await act(async () => container.querySelector('.search-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  expect(axios.get).toHaveBeenLastCalledWith('/api/historico', expect.objectContaining({ params: { limit: 5, offset: 0, busca: 'Alpha' } }));
});

test('apresenta histórico vazio e permite tentar novamente após erro', async () => {
  axios.get.mockRejectedValueOnce({ response: { data: { detail: 'Banco indisponível' } } });
  await navigate('Histórico');
  expect(container.querySelector('[role="alert"]').textContent).toContain('Banco indisponível');
  axios.get.mockResolvedValueOnce({ data: { partidas: [], total: 0 } });
  await click([...container.querySelectorAll('button')].find(button => button.textContent === 'Tentar novamente'));
  expect(container.textContent).toContain('Seu histórico começa com uma consulta');
  expect(container.querySelector('[aria-label="Próxima página"]').disabled).toBe(true);
});

test('preserva a nova consulta ao navegar e ignora respostas antigas do histórico', async () => {
  await navigate('Nova consulta');
  axios.post.mockResolvedValueOnce({ data: result([match('MATCH-101')]) });
  await submit();
  let resolveHistory;
  axios.get.mockImplementationOnce(() => new Promise(resolve => { resolveHistory = resolve; }));
  await navigate('Histórico');
  const config = axios.get.mock.calls[0][1];
  await navigate('Nova consulta');
  expect(config.signal.aborted).toBe(true);
  await act(async () => resolveHistory({ data: { partidas: [], total: 0 } }));
  expect(container.querySelector('.matches-table').textContent).toContain('MATCH-101');
  expect(axios.post).toHaveBeenCalledTimes(1);
});

test('ignora resposta de upload cancelado ao trocar de arquivo', async () => {
  await navigate('Nova consulta');
  let resolveUpload;
  axios.post.mockImplementationOnce(() => new Promise(resolve => { resolveUpload = resolve; }));
  await submit();
  const config = axios.post.mock.calls[0][2];
  const input = container.querySelector('input[type="file"]');
  Object.defineProperty(input, 'files', { value: [], configurable: true });
  await act(async () => input.dispatchEvent(new Event('change', { bubbles: true })));
  expect(config.signal.aborted).toBe(true);
  await act(async () => resolveUpload({ data: result([match('MATCH-101')]) }));
  expect(container.querySelector('.matches-table')).toBeNull();
});

const winnersResult = (extra = {}) => ({
  anos: [2026, 2025], torneios: ['T1', 'T2'], ano: 2026, torneio: 'T1', total_partidas: 2,
  ganhadores: [{ time: 'Beta', posicao: 1, vitorias: 1, kills: 30, premio_rs: 5000, percentual: 0.5 }],
  classificacao: [{ time: 'Beta', posicao: 1, vitorias: 1, kills: 30, premio_rs: 5000, percentual: 0.5 }],
  premios: { criterio_utilizado: 'minutos', premios_times: [], premio_jogadores: [
    { time: 'Beta', jogador: 'B', total_minutos: 40, premio_rs: 5000 }] }, ...extra,
});

test('mostra ganhador, classificação e rateio do torneio anual', async () => {
  axios.get.mockResolvedValue({ data: winnersResult() });
  await navigate('Ganhadores');
  expect(axios.get).toHaveBeenLastCalledWith('/api/ganhadores', expect.objectContaining({ params: { criterio: 'minutos' } }));
  expect(container.querySelector('#champion-title').textContent).toBe('Beta');
  expect(container.querySelector('.tournament-ranking').textContent).toContain('Abates totais');
  expect(container.querySelector('.champion-stats').textContent).toContain('30');
  expect(container.querySelector('.prize-panel').textContent).toContain('Minutos jogados');
  expect(container.querySelector('.ranking-rules').textContent).toContain('Prêmios das posições divididos igualmente');
});

test('trocar ano limpa torneio e alterar critério solicita novo rateio', async () => {
  axios.get.mockResolvedValue({ data: winnersResult() });
  await navigate('Ganhadores');
  await act(async () => {
    const input = container.querySelector('[aria-label="Torneio"]');
    input.value = 'T2'; input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  expect(axios.get).toHaveBeenLastCalledWith('/api/ganhadores', expect.objectContaining({ params: { torneio: 'T2', criterio: 'minutos' } }));
  axios.get.mockResolvedValue({ data: winnersResult({ ano: 2025, torneios: ['T1'] }) });
  await act(async () => {
    const input = container.querySelector('[aria-label="Ano do torneio"]');
    input.value = '2025'; input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  expect(axios.get).toHaveBeenLastCalledWith('/api/ganhadores', expect.objectContaining({ params: { ano: 2025, criterio: 'minutos' } }));
  axios.get.mockResolvedValue({ data: winnersResult({ ano: 2025, premios: { criterio_utilizado: 'kills', premio_jogadores: [] } }) });
  await act(async () => {
    const input = container.querySelector('[aria-label="Critério de rateio dos ganhadores"]');
    input.value = 'kills'; input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  expect(axios.get).toHaveBeenLastCalledWith('/api/ganhadores', expect.objectContaining({ params: { ano: 2025, criterio: 'kills' } }));
  expect(container.querySelector('.prize-panel').textContent).toContain('RATEIO POR ABATES');
});

test('exibe todos os campeões empatados sem inventar desempate adicional', async () => {
  const tied = [
    { time: 'Alpha', posicao: 1, vitorias: 3, kills: 50, premio_rs: 4000, percentual: 0.4 },
    { time: 'Beta', posicao: 1, vitorias: 3, kills: 50, premio_rs: 4000, percentual: 0.4 },
  ];
  axios.get.mockResolvedValue({ data: winnersResult({ ganhadores: tied, classificacao: tied }) });
  await navigate('Ganhadores');
  expect(container.querySelector('#champion-title').textContent).toBe('Alpha & Beta');
  expect(container.querySelector('.champion-card').textContent).toContain('CAMPEÕES EMPATADOS');
  expect(container.querySelector('.champion-stats').textContent).toContain('4.000,00');
  expect(container.querySelectorAll('.rank-number')[1].textContent).toBe('01');
});

test('mostra vazio e erro dos ganhadores com opção de tentar novamente', async () => {
  axios.get.mockRejectedValueOnce({ response: { data: { detail: 'Banco indisponível' } } });
  await navigate('Ganhadores');
  expect(container.querySelector('[role="alert"]').textContent).toContain('Banco indisponível');
  axios.get.mockResolvedValueOnce({ data: winnersResult({ anos: [], torneios: [], ano: null, total_partidas: 0, ganhadores: [], classificacao: [], premios: null }) });
  await click([...container.querySelectorAll('button')].find(button => button.textContent === 'Tentar novamente'));
  expect(container.textContent).toContain('Nenhum resultado nesta temporada');
  expect(container.querySelector('#champion-title')).toBeNull();
});

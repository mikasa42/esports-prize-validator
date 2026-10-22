import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

let container, root;
const players = Array.from({ length: 12 }, (_, index) => ({ jogador: index === 0 ? 'Águia' : `Jogador${String(index).padStart(2, '0')}`, time: index < 6 ? 'Alpha' : 'Beta', minutos: 10, kills: index, partidas: 1, premio_rs: index < 6 ? 100 : 0 }));
const data = { anos: [2026, 2025], torneios: ['T1', 'T2'], ano: 2026, torneio: 'T1', total_partidas: 1, criterio: 'minutos', status: 'parcial', premio_base_rs: 10000,
  classificacao: [{ time: 'Alpha', posicao: 1, vitorias: 1, kills: 10, premio_rs: 5000 }, { time: 'Beta', posicao: 2, vitorias: 0, kills: 5, premio_rs: 0 }], jogadores: players };
const response = value => Promise.resolve({ ok: true, json: async () => value });
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  window.history.replaceState(null, '', '/');
  global.fetch = jest.fn().mockImplementation(() => response(data));
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  delete global.fetch;
});
async function render() { await act(async () => root.render(<App />)); }
async function click(button) { await act(async () => button.click()); }
async function search(value) {
  const input = container.querySelector('input[type="search"]');
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

test('consulta sem cookies e apresenta pódio, tabela e resultados parciais', async () => {
  await render();
  expect(fetch).toHaveBeenCalledWith('/api/publico/resultados?', expect.objectContaining({ credentials: 'omit', signal: expect.anything() }));
  expect(container.textContent).toContain('Resultado parcial');
  expect(container.querySelectorAll('.podium-card')).toHaveLength(1);
  expect(container.querySelector('.podium-card').textContent).toContain('Alpha');
  expect(container.querySelectorAll('tbody>tr')).toHaveLength(10);
  expect(window.location.search).toBe('?ano=2026&torneio=T1');
});

test('busca ignora acentos e detalhes explicam a divisão', async () => {
  await render();
  await search('aguia');
  expect(container.querySelectorAll('tbody>tr')).toHaveLength(1);
  await click(container.querySelector('.details-button'));
  expect(container.querySelector('.details-row').textContent).toContain('total do time: 60');
  expect(container.querySelector('.details-row').textContent).toContain('Não é uma confirmação de pagamento.');
  expect(container.querySelector('.details-button').getAttribute('aria-expanded')).toBe('true');
  expect(window.location.search).toContain('jogador=aguia');
  expect(fetch).toHaveBeenCalledTimes(1);
});

test('pagina localmente e inclui jogadores com prêmio zero', async () => {
  await render();
  await click(container.querySelector('[aria-label="Próxima página"]'));
  expect(container.querySelectorAll('tbody>tr')).toHaveLength(2);
  expect(container.querySelector('tbody').textContent).toContain('Jogador11');
  expect(container.querySelector('[aria-label="Próxima página"]').disabled).toBe(true);
  expect(container.querySelector('[aria-current="page"]').textContent).toBe('2 / 2');
  await search('aguia');
  expect(container.querySelector('[aria-current="page"]').textContent).toBe('1 / 1');
  expect(fetch).toHaveBeenCalledTimes(1);
});

test('busca vazia tem mensagem e permite limpar', async () => {
  await render();
  await search('inexistente');
  expect(container.querySelector('.no-players').textContent).toContain('Nenhum jogador encontrado');
  await click(container.querySelector('.no-players button'));
  expect(container.querySelectorAll('tbody>tr')).toHaveLength(10);
});

test('troca de ano limpa torneio anterior na requisição', async () => {
  await render();
  fetch.mockImplementationOnce(() => response({ ...data, ano: 2025, torneio: 'T3', torneios: ['T3'] }));
  await act(async () => {
    const select = container.querySelector('#year');
    select.value = '2025';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
  expect(fetch.mock.calls[1][0]).toBe('/api/publico/resultados?ano=2025');
  expect(container.querySelector('#tournament').value).toBe('T3');
  expect(window.location.search).toBe('?ano=2025&torneio=T3');
});

test('URL compartilhada restaura torneio e busca', async () => {
  window.history.replaceState(null, '', '/?ano=2026&torneio=T1&jogador=aguia');
  await render();
  expect(fetch.mock.calls[0][0]).toBe('/api/publico/resultados?ano=2026&torneio=T1');
  expect(container.querySelector('input[type="search"]').value).toBe('aguia');
  expect(container.querySelectorAll('tbody>tr')).toHaveLength(1);
});

test('banco vazio não mostra premiações fictícias', async () => {
  fetch.mockImplementationOnce(() => response({ ...data, anos: [], torneios: [], ano: null, torneio: null, total_partidas: 0, jogadores: [], classificacao: [] }));
  await render();
  expect(container.querySelector('.empty-state')).not.toBeNull();
  expect(container.querySelector('.stats-grid')).toBeNull();
  expect(container.querySelector('#year').textContent).toContain('Sem anos disponíveis');
});

test('erro permite repetir consulta e recuperar resultados', async () => {
  fetch.mockImplementationOnce(async () => ({ ok: false, json: async () => ({ detail: 'Banco de dados indisponível.' }) }));
  await render();
  expect(container.querySelector('[role="alert"]').textContent).toContain('Banco de dados indisponível');
  await click(container.querySelector('.error-state button'));
  expect(container.querySelector('.players-panel')).not.toBeNull();
});

test('carregamento é anunciado e sair cancela consulta', async () => {
  fetch.mockImplementationOnce(() => new Promise(() => {}));
  await render();
  expect(container.querySelector('.loading-state').getAttribute('role')).toBe('status');
  const signal = fetch.mock.calls[0][1].signal;
  await act(async () => root.render(<div />));
  expect(signal.aborted).toBe(true);
});

test('compartilha URL e anuncia cópia', async () => {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: jest.fn().mockResolvedValue() } });
  await render();
  await click(container.querySelector('.share-button'));
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(window.location.href);
  expect(container.querySelector('.share-status').textContent).toBe('Link copiado!');
});

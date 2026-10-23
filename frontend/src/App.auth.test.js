import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import App from './App';

jest.mock('axios');
const user = { id: 3, nome: 'Ana Silva', login: 'ana', empresa: 'Minha Empresa' };
let container;
let root;
beforeEach(() => {
  jest.resetAllMocks();
  axios.get.mockResolvedValue({ data: { consultas: [] } });
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function render() {
  await act(async () => root.render(<App />));
}
async function click(button) {
  await act(async () => button.click());
}

test('sem sessão mostra login, autentica e exibe nome e empresa do servidor', async () => {
  axios.get.mockRejectedValueOnce({ response: { status: 401 } });
  await render();
  expect(container.querySelector('nav')).toBeNull();
  expect(axios.get).toHaveBeenCalledTimes(1);
  axios.post.mockResolvedValueOnce({ data: user });
  container.querySelector('[name="login"]').value = 'ana';
  container.querySelector('[name="senha"]').value = 'uma senha segura';
  await act(async () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  expect(axios.post).toHaveBeenCalledWith('/api/auth/login', { login: 'ana', senha: 'uma senha segura' }, expect.objectContaining({ signal: expect.anything() }));
  expect(container.querySelector('.header-profile').textContent).toContain('Ana SilvaMinha Empresa');
});

test('restaura sessão e logout retorna ao login', async () => {
  axios.get.mockResolvedValueOnce({ data: user });
  await render();
  expect(container.querySelector('nav')).not.toBeNull();
  axios.post.mockResolvedValueOnce({});
  await click(container.querySelector('[aria-controls="account-options"]'));
  await click([...container.querySelectorAll('button')].find(button => button.textContent === 'Sair da conta'));
  expect(axios.post).toHaveBeenCalledWith('/api/auth/logout');
  expect(container.querySelector('nav')).toBeNull();
  expect(container.querySelector('[name="login"]')).not.toBeNull();
});

test('erro de login é exibido e mantém formulário disponível', async () => {
  axios.get.mockRejectedValueOnce({ response: { status: 401 } });
  await render();
  axios.post.mockRejectedValueOnce({ response: { status: 401, data: { detail: 'Login ou senha inválidos.' } } });
  await act(async () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  expect(container.querySelector('[role="status"]').textContent).toContain('Login ou senha inválidos.');
  expect(container.querySelector('fieldset').disabled).toBe(false);
});

test('sessão expirada nas APIs fecha o painel', async () => {
  axios.get.mockResolvedValueOnce({ data: user });
  await render();
  const rejectResponse = axios.interceptors.response.use.mock.calls[0][1];
  await act(async () => {
    await rejectResponse({ response: { status: 401 }, config: { url: '/api/historico' } }).catch(() => {});
  });
  expect(container.querySelector('nav')).toBeNull();
  expect(container.textContent).toContain('Sua sessão expirou. Entre novamente.');
});


test('menu abre, fecha com Escape e permite editar dados refletidos no cabeçalho', async () => {
  axios.get.mockResolvedValueOnce({ data: user });
  await render();
  const trigger = container.querySelector('[aria-controls="account-options"]');
  await click(trigger);
  expect(trigger.getAttribute('aria-expanded')).toBe('true');
  await act(async () => trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })));
  expect(trigger.getAttribute('aria-expanded')).toBe('false');
  expect(document.activeElement).toBe(trigger);
  await click(trigger);
  await click([...container.querySelectorAll('button')].find(button => button.textContent.startsWith('Editar informações')));
  expect(container.querySelector('#account-options')).toBeNull();
  expect(container.querySelector('#account-name').value).toBe('Ana Silva');
  axios.post.mockResolvedValueOnce({ data: { ...user, nome: 'Ana Souza', empresa: 'Outra Empresa' } });
  await act(async () => container.querySelector('.account-panel').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  expect(container.querySelector('.header-profile').textContent).toContain('Ana SouzaOutra Empresa');
  expect(container.textContent).toContain('Informações atualizadas com sucesso.');
});

test('menu fecha ao clicar fora e abre a tela de troca de senha', async () => {
  axios.get.mockResolvedValueOnce({ data: user });
  await render();
  const trigger = container.querySelector('[aria-controls="account-options"]');
  await click(trigger);
  await act(async () => document.body.dispatchEvent(new Event('pointerdown', { bubbles: true })));
  expect(trigger.getAttribute('aria-expanded')).toBe('false');
  await click(trigger);
  await click([...container.querySelectorAll('button')].find(button => button.textContent.startsWith('Trocar senha')));
  expect(container.querySelector('#current-password')).not.toBeNull();
  expect(container.querySelector('#new-password')).not.toBeNull();
});

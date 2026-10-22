import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import LoginPage from './LoginPage';

let container;
let root;
let onAuthenticate;
beforeEach(async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  onAuthenticate = jest.fn();
  await act(async () => root.render(<LoginPage onAuthenticate={onAuthenticate} />));
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function submit() {
  await act(async () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
}

test('mostra e oculta a senha com controle acessível', async () => {
  const password = container.querySelector('#login-password');
  const toggle = container.querySelector('[aria-label="Mostrar senha"]');
  expect(password.type).toBe('password');
  await act(async () => toggle.click());
  expect(password.type).toBe('text');
  expect(toggle.getAttribute('aria-pressed')).toBe('true');
  await act(async () => toggle.click());
  expect(password.type).toBe('password');
});

test('envia login e senha para autenticação', async () => {
  container.querySelector('[name="login"]').value = 'maria';
  container.querySelector('[name="senha"]').value = 'minha senha segura';
  await submit();
  expect(onAuthenticate).toHaveBeenCalledWith('login', { login: 'maria', senha: 'minha senha segura' });
});

test('cadastro envia nome, login, senha e empresa', async () => {
  await act(async () => container.querySelector('.login-demo').click());
  container.querySelector('[name="nome"]').value = 'Maria Clara';
  container.querySelector('[name="empresa"]').value = 'PowerRev';
  container.querySelector('[name="login"]').value = 'maria';
  container.querySelector('[name="senha"]').value = 'minha senha segura';
  await submit();
  expect(onAuthenticate).toHaveBeenCalledWith('cadastro', { nome: 'Maria Clara', empresa: 'PowerRev', login: 'maria', senha: 'minha senha segura' });
  expect(container.querySelector('[name="senha"]').minLength).toBe(12);
});

test('exibe erro e desabilita controles durante a requisição', async () => {
  await act(async () => root.render(<LoginPage onAuthenticate={onAuthenticate} busy error="Login ou senha inválidos." />));
  expect(container.querySelector('fieldset').disabled).toBe(true);
  expect(container.querySelector('[role="status"]').textContent).toBe('Login ou senha inválidos.');
});

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import AccountPage from './AccountPage';

jest.mock('axios');
let container, root, update;
const user = { id: 1, nome: 'Maria Clara', login: 'maria', empresa: 'PowerRev' };
beforeEach(() => {
  jest.resetAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  update = jest.fn();
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function render(mode = 'senha') {
  await act(async () => root.render(<AccountPage user={user} mode={mode} onUpdate={update} navigate={jest.fn()} />));
}
async function change(name, value) {
  const input = container.querySelector(`[name="${name}"]`);
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}
async function submit() {
  await act(async () => container.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
}
async function passwords(confirm = 'nova senha segura') {
  await change('senha_atual', 'senha atual segura');
  await change('nova_senha', 'nova senha segura');
  await change('confirmar_senha', confirm);
}

test('confirmação diferente impede envio de senha', async () => {
  await render();
  await passwords('outra senha segura');
  await submit();
  expect(axios.post).not.toHaveBeenCalled();
  expect(container.querySelector('[role="alert"]').textContent).toContain('confirmação');
});

test('envia senha atual e nova, limpa os campos e anuncia sucesso', async () => {
  await render();
  await passwords();
  axios.post.mockResolvedValueOnce({});
  await submit();
  expect(axios.post).toHaveBeenCalledWith('/api/auth/senha', { senha_atual: 'senha atual segura', nova_senha: 'nova senha segura' }, expect.objectContaining({ signal: expect.anything() }));
  expect(container.querySelector('#current-password').value).toBe('');
  expect(container.querySelector('#new-password').value).toBe('');
  expect(container.querySelector('#confirm-password').value).toBe('');
  expect(container.querySelector('[role="status"]').textContent).toContain('Senha alterada');
});

test('salva nome, login e empresa e usa resposta normalizada do servidor', async () => {
  await render('perfil');
  await change('nome', 'Maria Souza');
  await change('login', 'MARIA.SOUZA');
  await change('empresa', 'Empresa Nova');
  const saved = { ...user, nome: 'Maria Souza', login: 'maria.souza', empresa: 'Empresa Nova' };
  axios.post.mockResolvedValueOnce({ data: saved });
  await submit();
  expect(axios.post).toHaveBeenCalledWith('/api/auth/perfil', { nome: 'Maria Souza', login: 'MARIA.SOUZA', empresa: 'Empresa Nova' }, expect.anything());
  expect(update).toHaveBeenCalledWith(saved);
  expect(container.querySelector('#account-login').value).toBe('maria.souza');
});

test('erro do servidor mantém dados para correção', async () => {
  await render('perfil');
  axios.post.mockRejectedValueOnce({ response: { data: { detail: 'Este login já está em uso.' } } });
  await submit();
  expect(container.querySelector('[role="alert"]').textContent).toBe('Este login já está em uso.');
  expect(container.querySelector('#account-name').value).toBe('Maria Clara');
  expect(update).not.toHaveBeenCalled();
});

test('sair da tela cancela requisição pendente', async () => {
  await render('perfil');
  axios.post.mockImplementationOnce(() => new Promise(() => {}));
  await submit();
  const signal = axios.post.mock.calls[0][2].signal;
  expect(container.querySelector('fieldset').disabled).toBe(true);
  await act(async () => root.render(<div />));
  expect(signal.aborted).toBe(true);
});

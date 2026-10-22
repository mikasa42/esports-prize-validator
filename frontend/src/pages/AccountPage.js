import React, { useEffect, useRef, useState } from 'react';
import api, { API_URL } from '../api';
import Icon from '../components/Icon';
import './AccountPage.css';

export default function AccountPage({ user, mode, onUpdate, navigate }) {
  const passwordMode = mode === 'senha';
  const [fields, setFields] = useState({ nome: user.nome, login: user.login, empresa: user.empresa, senha_atual: '', nova_senha: '', confirmar_senha: '' });
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState({ error: '', success: '' });
  const request = useRef(null);
  const heading = useRef(null);
  useEffect(() => {
    heading.current?.focus();
    return () => request.current?.abort();
  }, []);

  function change(event) {
    setFields(current => ({ ...current, [event.target.name]: event.target.value }));
    setFeedback({ error: '', success: '' });
  }

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setFeedback({ error: '', success: '' });
    if (passwordMode && fields.nova_senha !== fields.confirmar_senha) {
      setFeedback({ error: 'A confirmação deve ser igual à nova senha.', success: '' });
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const payload = passwordMode
        ? { senha_atual: fields.senha_atual, nova_senha: fields.nova_senha }
        : { nome: fields.nome.trim(), login: fields.login.trim(), empresa: fields.empresa.trim() };
      const { data } = await api.post(`${API_URL}/api/auth/${passwordMode ? 'senha' : 'perfil'}`, payload, { signal: controller.signal });
      if (controller.signal.aborted) return;
      if (passwordMode) setFields(current => ({ ...current, senha_atual: '', nova_senha: '', confirmar_senha: '' }));
      else {
        onUpdate(data);
        setFields(current => ({ ...current, nome: data.nome, login: data.login, empresa: data.empresa }));
      }
      setFeedback({ error: '', success: passwordMode ? 'Senha alterada. As outras sessões foram encerradas.' : 'Informações atualizadas com sucesso.' });
    } catch (error) {
      if (controller.signal.aborted) return;
      const detail = error.response?.data?.detail;
      setFeedback({ error: typeof detail === 'string' ? detail : 'Não foi possível salvar. Confira os campos e tente novamente.', success: '' });
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <section className="account-page">
    <div className="page-heading"><span className="eyebrow">MINHA CONTA</span><h1 ref={heading} tabIndex={-1}>{passwordMode ? 'Trocar senha' : 'Editar informações'}</h1><p>{passwordMode ? 'Mantenha sua conta protegida com uma senha exclusiva.' : 'Mantenha suas informações pessoais e da empresa atualizadas.'}</p></div>
    <div className="account-layout">
      <nav className="account-navigation" aria-label="Configurações da conta">
        <button aria-current={!passwordMode ? 'page' : undefined} onClick={() => navigate('perfil')}>Informações pessoais <Icon name="chevron" size={15} /></button>
        <button aria-current={passwordMode ? 'page' : undefined} onClick={() => navigate('senha')}>Senha e segurança <Icon name="chevron" size={15} /></button>
        <button className="account-back" onClick={() => navigate('sobre')}>Voltar ao painel</button>
      </nav>
      <form className="account-panel" onSubmit={submit}>
        <div className="account-panel-heading"><Icon name={passwordMode ? 'check' : 'grid'} size={22} /><div><h2>{passwordMode ? 'Sua senha de acesso' : 'Informações pessoais'}</h2><p>{passwordMode ? 'Confirme sua senha atual para continuar.' : 'Esses dados identificam você no Tournament Hub.'}</p></div></div>
        <fieldset disabled={busy}>
          {!passwordMode ? <>
            <label htmlFor="account-name">Nome completo</label><input id="account-name" name="nome" value={fields.nome} onChange={change} autoComplete="name" maxLength={150} required pattern=".*\S.*" />
            <label htmlFor="account-login">Login</label><input id="account-login" name="login" value={fields.login} onChange={change} autoComplete="username" minLength={3} maxLength={100} required autoCapitalize="none" spellCheck="false" aria-describedby="account-login-hint" /><small id="account-login-hint">Use este login para entrar na sua conta. Letras, números, ponto, _, @, + e hífen.</small>
            <label htmlFor="account-company">Empresa</label><input id="account-company" name="empresa" value={fields.empresa} onChange={change} autoComplete="organization" maxLength={150} required pattern=".*\S.*" />
          </> : <>
            <label htmlFor="current-password">Senha atual</label><input id="current-password" name="senha_atual" type="password" value={fields.senha_atual} onChange={change} autoComplete="current-password" maxLength={128} required />
            <label htmlFor="new-password">Nova senha</label><input id="new-password" name="nova_senha" type="password" value={fields.nova_senha} onChange={change} autoComplete="new-password" minLength={12} maxLength={128} required aria-describedby="account-password-hint" /><small id="account-password-hint">Use entre 12 e 128 caracteres. As outras sessões serão encerradas após a troca.</small>
            <label htmlFor="confirm-password">Confirmar nova senha</label><input id="confirm-password" name="confirmar_senha" type="password" value={fields.confirmar_senha} onChange={change} autoComplete="new-password" minLength={12} maxLength={128} required />
          </>}
          {feedback.error && <p className="account-feedback error" role="alert">{feedback.error}</p>}
          <p className={feedback.success ? 'account-feedback success' : 'sr-only'} role="status">{feedback.success}</p>
          <div className="account-form-actions"><button className="button button-secondary" type="button" onClick={() => navigate('sobre')}>Cancelar</button><button className="button button-primary" type="submit">{busy ? 'Salvando…' : passwordMode ? 'Alterar senha' : 'Salvar alterações'}<Icon name="check" size={16} /></button></div>
        </fieldset>
      </form>
    </div>
  </section>;
}

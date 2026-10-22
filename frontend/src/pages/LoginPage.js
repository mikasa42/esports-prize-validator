import React, { useState } from 'react';
import Icon from '../components/Icon';
import './LoginPage.css';

export default function LoginPage({ onAuthenticate, busy = false, error = '' }) {
  const [showPassword, setShowPassword] = useState(false);
  const [register, setRegister] = useState(false);

  function handleSubmit(event) {
    event.preventDefault();
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    onAuthenticate(register ? 'cadastro' : 'login', fields);
  }

  return <main className="login-page">
    <section className="login-story" aria-labelledby="login-story-title">
      <a className="brand login-brand" href="#login-form"><span className="brand-mark"><span /><span /><span /></span><span>TOURNAMENT<span className="brand-light"> HUB</span></span></a>
      <div className="login-story-content">
        <span className="login-kicker"><span className="status-dot" /> GESTÃO DE TORNEIOS, SIMPLIFICADA</span>
        <h1 id="login-story-title">Cada partida conta.<br /><span>Cada conquista<br />também.</span></h1>
        <p>Das primeiras estatísticas ao pódio final. Um só lugar para acompanhar partidas e distribuir premiações com clareza.</p>
        <div className="login-podium" aria-hidden="true">
          <div className="login-podium-heading"><span>O MÉRITO EM PRIMEIRO LUGAR</span><Icon name="trophy" size={24} /></div>
          <div className="login-podium-bars"><div><span>02</span><strong>30%</strong></div><div><Icon name="trophy" size={27} /><span>01</span><strong>50%</strong></div><div><span>03</span><strong>20%</strong></div></div>
          <div className="login-podium-caption"><Icon name="check" size={15} /> Dados claros. Decisões justas.</div>
        </div>
      </div>
      <span className="login-story-footer">POWERREV TECH CHALLENGE <span>EST. 2026</span></span>
    </section>
    <section className="login-access" aria-labelledby="login-title">
      <div className="login-form-wrap">
        <span className="eyebrow">SEU PRÓXIMO TORNEIO COMEÇA AQUI</span>
        <h2 id="login-title">{register ? 'Crie sua conta.' : 'Bom ter você de volta.'}</h2>
        <p className="login-intro">{register ? 'Preencha seus dados para começar.' : 'Entre para acompanhar cada resultado.'}</p>
        <form id="login-form" className="login-form" onSubmit={handleSubmit}>
          <fieldset disabled={busy} className="login-fields">
          {register && <><label htmlFor="register-name">Nome</label><input id="register-name" name="nome" autoComplete="name" required maxLength={150} placeholder="Seu nome completo" /><label htmlFor="register-company">Empresa</label><input id="register-company" name="empresa" autoComplete="organization" required maxLength={150} placeholder="Nome da sua empresa" /></>}
          <label htmlFor="login-email">Login</label>
          <input id="login-email" name="login" type="text" maxLength={100} minLength={register ? 3 : 1} autoComplete="username" placeholder="Seu usuário ou e-mail" autoCapitalize="none" spellCheck="false" required />
          <label htmlFor="login-password">Senha</label>
          <div className="login-password"><input id="login-password" name="senha" type={showPassword ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'} minLength={register ? 12 : 1} maxLength={128} placeholder={register ? 'Pelo menos 12 caracteres' : 'Digite sua senha'} required /><button type="button" aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? 'Ocultar' : 'Mostrar'}</button></div>
          <p className="login-feedback" role="status">{error}</p>
          <button className="button button-primary login-submit" type="submit">{busy ? 'Aguarde…' : register ? 'Criar conta' : 'Entrar'} <Icon name="arrow" size={18} /></button>
        </fieldset></form>
        <div className="login-divider"><span>{register ? 'JÁ TEM UMA CONTA?' : 'PRIMEIRO ACESSO?'}</span></div>
        <button className="button button-secondary login-demo" type="button" disabled={busy} onClick={() => setRegister(!register)}>{register ? 'Voltar ao login' : 'Criar minha conta'} <Icon name="arrow" size={17} /></button>
        <p className="login-demo-note">Seus dados de acesso são pessoais.<br />Use uma senha exclusiva para sua conta.</p>
      </div>
      <footer className="login-access-footer"><span>Tournament Hub</span><span>Partidas. Resultados. Conquistas.</span></footer>
    </section>
  </main>;
}

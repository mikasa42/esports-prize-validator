import React, { useState } from 'react';
import Icon from './components/Icon';
import AboutPage from './pages/AboutPage';
import HistoryPage from './pages/HistoryPage';
import NewQueryPage from './pages/NewQueryPage';
import WinnersPage from './pages/WinnersPage';
import LoginPage from './pages/LoginPage';
import useAuth from './hooks/useAuth';
import useCsvLookup from './hooks/useCsvLookup';
import './App.css';

const tabs = [['sobre', 'Sobre o site'], ['historico', 'Histórico'], ['ganhadores', 'Ganhadores'], ['nova', 'Nova consulta']];
export default function App() {
  const auth = useAuth();
  if (auth.checking) return <main className="session-loading" role="status">Verificando sua sessão…</main>;
  if (!auth.user) return <LoginPage onAuthenticate={auth.authenticate} busy={auth.busy} error={auth.error} />;
  return <Dashboard key={auth.user.id} auth={auth} />;
}

function Dashboard({ auth }) {
  const [tab, setTab] = useState('sobre');
  const [file, setFile] = useState(null);
  const [criterio, setCriterio] = useState('minutos');
  const lookup = useCsvLookup();
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
    <header className="site-header"><div className="header-inner"><button className="brand" aria-label="Tournament Hub, início" onClick={() => setTab('sobre')}><span className="brand-mark"><span /><span /><span /></span><span>TOURNAMENT<span className="brand-light"> HUB</span></span></button><nav className="main-nav" aria-label="Navegação principal">{tabs.map(([value, label]) => <button key={value} className={tab === value ? 'nav-item active' : 'nav-item'} aria-current={tab === value ? 'page' : undefined} onClick={() => setTab(value)}>{label}{value === 'nova' && <Icon name="arrow" size={15} />}</button>)}</nav><div className="header-profile"><span className="profile-avatar">{auth.user.nome.split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</span><div><strong>{auth.user.nome}</strong><span>{auth.user.empresa}</span></div></div></div></header>
    <div className="context-bar"><div><span><Icon name="grid" size={14} />WORKSPACE / <strong>GESTÃO DE PARTIDAS</strong></span><span className="context-label">POWERREV TECH CHALLENGE</span></div></div>
    <main id="main-content" className="main-content">
      {auth.error && <p className="alert" role="alert">{auth.error}</p>}
      {tab === 'sobre' && <AboutPage navigate={setTab} />}
      {tab === 'historico' && <HistoryPage navigate={setTab} />}
      {tab === 'ganhadores' && <WinnersPage navigate={setTab} />}
      <div hidden={tab !== 'nova'}><NewQueryPage lookup={lookup} file={file} setFile={setFile} criterio={criterio} setCriterio={setCriterio} /></div>
    </main>
    <footer className="site-footer"><span><strong>Tournament Hub</strong> · Dados claros. Decisões justas.</span><button className="button button-text button-small" onClick={auth.logout} disabled={auth.busy}>{auth.busy ? 'Saindo…' : 'Sair da conta'}</button><span>{auth.user.empresa}</span></footer>
  </div>;
}

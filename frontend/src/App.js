import React, { useState } from 'react';
import Icon from './components/Icon';
import AboutPage from './pages/AboutPage';
import HistoryPage from './pages/HistoryPage';
import NewQueryPage from './pages/NewQueryPage';
import WinnersPage from './pages/WinnersPage';
import LoginPage from './pages/LoginPage';
import useCsvLookup from './hooks/useCsvLookup';
import './App.css';

const tabs = [['sobre', 'Sobre o site'], ['historico', 'Histórico'], ['ganhadores', 'Ganhadores'], ['nova', 'Nova consulta']];
export default function App() {
  const [showLogin, setShowLogin] = useState(true);
  const [tab, setTab] = useState('sobre');
  const [file, setFile] = useState(null);
  const [criterio, setCriterio] = useState('minutos');
  const lookup = useCsvLookup();
  if (showLogin) return <LoginPage onExplore={() => setShowLogin(false)} />;
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
    <header className="site-header"><div className="header-inner"><button className="brand" aria-label="Tournament Hub, início" onClick={() => setTab('sobre')}><span className="brand-mark"><span /><span /><span /></span><span>TOURNAMENT<span className="brand-light"> HUB</span></span></button><nav className="main-nav" aria-label="Navegação principal">{tabs.map(([value, label]) => <button key={value} className={tab === value ? 'nav-item active' : 'nav-item'} aria-current={tab === value ? 'page' : undefined} onClick={() => setTab(value)}>{label}{value === 'nova' && <Icon name="arrow" size={15} />}</button>)}</nav><div className="header-profile"><span className="profile-avatar">MC</span><div><strong>Maria Clara</strong><span>Gestão de torneios</span></div></div></div></header>
    <div className="context-bar"><div><span><Icon name="grid" size={14} />WORKSPACE / <strong>GESTÃO DE PARTIDAS</strong></span><span className="context-label">POWERREV TECH CHALLENGE</span></div></div>
    <main id="main-content" className="main-content">
      {tab === 'sobre' && <AboutPage navigate={setTab} />}
      {tab === 'historico' && <HistoryPage navigate={setTab} />}
      {tab === 'ganhadores' && <WinnersPage navigate={setTab} />}
      <div hidden={tab !== 'nova'}><NewQueryPage lookup={lookup} file={file} setFile={setFile} criterio={criterio} setCriterio={setCriterio} /></div>
    </main>
    <footer className="site-footer"><span><strong>Tournament Hub</strong> · Dados claros. Decisões justas.</span><button className="button button-text button-small" onClick={() => setShowLogin(true)}>Voltar ao login</button><span>PowerRev · Painel da Maria Clara</span></footer>
  </div>;
}

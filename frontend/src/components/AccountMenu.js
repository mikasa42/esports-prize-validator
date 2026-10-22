import React, { useEffect, useRef, useState } from 'react';
import Icon from './Icon';

export default function AccountMenu({ user, busy, onNavigate, onLogout }) {
  const [open, setOpen] = useState(false);
  const container = useRef(null);
  const trigger = useRef(null);

  useEffect(() => {
    if (!open) return;
    function outside(event) {
      if (!container.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);

  function select(page) {
    setOpen(false);
    onNavigate(page);
  }

  return <div className="account-menu" ref={container} onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
  }} onKeyDown={event => {
    if (event.key === 'Escape') {
      setOpen(false);
      trigger.current.focus();
    }
  }}>
    <button className="header-profile account-trigger" ref={trigger} aria-expanded={open} aria-controls="account-options" aria-label={`Opções da conta de ${user.nome}`} onClick={() => setOpen(!open)}>
      <span className="profile-avatar">{user.nome.split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</span>
      <span className="profile-info"><strong>{user.nome}</strong><span>{user.empresa}</span></span>
      <Icon name="chevron" size={14} className={open ? 'account-chevron expanded' : 'account-chevron'} />
    </button>
    {open && <div className="account-dropdown" id="account-options">
      <p>MINHA CONTA<span>{user.login}</span></p>
      <ul aria-label="Opções da conta">
        <li><button onClick={() => select('perfil')}>Editar informações <Icon name="arrow" size={15} /></button></li>
        <li><button onClick={() => select('senha')}>Trocar senha <Icon name="arrow" size={15} /></button></li>
        <li><button className="account-logout" disabled={busy} onClick={() => { setOpen(false); onLogout(); }}>{busy ? 'Saindo…' : 'Sair da conta'}</button></li>
      </ul>
    </div>}
  </div>;
}

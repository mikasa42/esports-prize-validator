import React, { useEffect, useState } from 'react';
import Icon from './Icon';

export function formatDate(value) {
  if (!value) return 'Não informada';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(date);
}

export default function MatchTable({ partidas, loading = false, emptyTitle = 'Nenhuma partida por aqui', emptyMessage = 'As partidas encontradas aparecerão nesta tabela.' }) {
  const [expanded, setExpanded] = useState(null);
  useEffect(() => setExpanded(null), [partidas]);
  if (loading) return <div className="table-loading" role="status" aria-label="Carregando partidas"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /><p>Carregando partidas…</p></div>;
  if (!partidas.length) return <div className="empty-state"><div className="empty-icon"><Icon name="grid" size={28} /></div><h3>{emptyTitle}</h3><p>{emptyMessage}</p></div>;
  return <div className="table-scroll"><table className="matches-table">
    <caption className="sr-only">Partidas e seus resultados. Use Ver jogadores para consultar as estatísticas.</caption>
    <thead><tr><th scope="col">Partida</th><th scope="col">Data / rodada</th><th scope="col">Vencedor</th><th scope="col"><span className="sr-only">Detalhes</span></th></tr></thead>
    <tbody>{partidas.map((match, index) => {
      const winner = match.participantes.find(player => player.venceu)?.time_nick.split(' / ')[0];
      const open = expanded === index;
      return <React.Fragment key={`${match.match_id_externo}-${index}`}>
        <tr className={open ? 'expanded-row' : ''}>
          <td><span className="match-id">{match.match_id_externo}</span><strong className="match-title">{match.confronto}</strong><span className="cell-note">{match.participantes.length} jogadores</span></td>
          <td><span>{formatDate(match.data_partida)}</span><span className="cell-note">Rodada {match.rodada}</span></td>
          <td><span className="winner"><span className="winner-dot" />{winner || 'Não informado'}</span></td>
          <td><button className="row-action" aria-label={`${open ? 'Ocultar' : 'Ver'} jogadores de ${match.match_id_externo}`} aria-expanded={open} aria-controls={`players-${index}`} onClick={() => setExpanded(open ? null : index)}>{open ? 'Ocultar' : 'Ver jogadores'}<Icon name="chevron" size={15} className={open ? 'rotate' : ''} /></button></td>
        </tr>
        {open && <tr id={`players-${index}`} className="player-detail"><td colSpan={4}>
          <div className="player-heading"><Icon name="grid" size={16} /><strong>Estatísticas dos jogadores</strong><span>{match.match_id_externo}</span></div>
          <table className="players-table"><caption className="sr-only">Jogadores de {match.match_id_externo}</caption><thead><tr><th scope="col">Time / jogador</th><th scope="col">Minutos</th><th scope="col">Abates</th><th scope="col">Resultado</th></tr></thead>
            <tbody>{match.participantes.map(player => <tr key={player.time_nick}><td>{player.time_nick}</td><td>{player.minutos}</td><td>{player.kills}</td><td><span className={player.venceu ? 'result-won' : 'result-lost'}>{player.venceu ? 'Vitória' : 'Derrota'}</span></td></tr>)}</tbody>
          </table>
        </td></tr>}
      </React.Fragment>;
    })}</tbody>
  </table></div>;
}

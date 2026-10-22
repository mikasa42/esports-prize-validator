import React, { useEffect, useState } from 'react';
import Icon from './components/Icon';
import usePublicResults from './hooks/usePublicResults';
import './App.css';

const money = value => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const playerKey = player => JSON.stringify([player.time, player.jogador]);

export default function App() {
  const [initial] = useState(() => new URLSearchParams(window.location.search));
  const [year, setYear] = useState(initial.get('ano') || '');
  const [tournament, setTournament] = useState(initial.get('torneio') || '');
  const [search, setSearch] = useState(initial.get('jogador') || '');
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const [shareStatus, setShareStatus] = useState('');
  const { status, data, error } = usePublicResults(year, tournament, refresh);
  const ready = status === 'success';
  const hasMatches = ready && data.total_partidas > 0;
  const players = data?.jogadores || [];
  const filtered = players.filter(player => normalize(`${player.jogador} ${player.time}`).includes(normalize(search.trim())));
  const pages = Math.max(1, Math.ceil(filtered.length / 10));
  const currentPage = Math.min(page, pages);
  const rows = filtered.slice((currentPage - 1) * 10, currentPage * 10);
  const ranking = data?.classificacao || [];
  const criterionLabel = data?.criterio === 'kills' ? 'Abates' : 'Minutos jogados';

  useEffect(() => {
    setPage(1);
    setExpanded(null);
  }, [data]);

  useEffect(() => {
    if (!ready) return;
    const url = new URL(window.location.href);
    if (data.ano) url.searchParams.set('ano', data.ano); else url.searchParams.delete('ano');
    if (data.torneio) url.searchParams.set('torneio', data.torneio); else url.searchParams.delete('torneio');
    if (search) url.searchParams.set('jogador', search); else url.searchParams.delete('jogador');
    window.history.replaceState(null, '', url);
    setShareStatus('');
  }, [ready, data, search]);

  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareStatus('Link copiado!');
    } catch {
      setShareStatus('Copie o endereço desta página para compartilhar.');
    }
  }

  return <div className="public-shell">
    <a className="skip-link" href="#results">Pular para os resultados</a>
    <header className="site-header"><div className="header-inner">
      <a href="/" className="brand" aria-label="Tournament Hub, início"><span className="brand-mark"><i /><i /><i /></span><span>TOURNAMENT <b>HUB</b></span></a>
      <span className="header-section"><span /> RESULTADOS E PREMIAÇÕES</span><span className="public-access">ACESSO PÚBLICO <Icon name="users" size={15} /></span>
    </div></header>
    <main>
      <section className="hero"><div className="hero-inner"><div className="hero-copy">
        <span className="eyebrow">DENTRO DO JOGO. POR DENTRO DOS RESULTADOS.</span>
        <h1>Seu esforço em campo.<br /><span>Seu lugar na conquista.</span></h1>
        <p>Acompanhe a classificação, encontre seu nome e veja a sua parte na premiação. Cada partida conta.</p>
        <a className="hero-link" href="#players">Encontre sua premiação <Icon name="arrow" size={18} /></a>
      </div><div className="hero-emblem" aria-hidden="true"><div className="emblem-ring"><Icon name="trophy" size={80} /></div><span>O MÉRITO EM PRIMEIRO LUGAR</span></div></div></section>
      <div className="content" id="results">
        <div className="section-heading"><div><span className="eyebrow">ACOMPANHE A COMPETIÇÃO</span><h2>Resultados do torneio</h2></div><span className="partial-badge"><span /> Resultado parcial</span></div>
        <div className="filters">
          <div className="filter-fields"><label htmlFor="year">Ano<select id="year" disabled={!data || status === 'loading'} value={year || data?.ano || ''} onChange={event => { setYear(event.target.value); setTournament(''); setExpanded(null); }}>
            {!data?.anos.length && <option value="">Sem anos disponíveis</option>}{data?.anos.map(value => <option key={value} value={value}>{value}</option>)}
          </select></label><label htmlFor="tournament">Torneio<select id="tournament" disabled={!data || status === 'loading' || !data.torneios.length} value={tournament || data?.torneio || ''} onChange={event => setTournament(event.target.value)}>
            {!data?.torneios.length && <option value="">Sem torneios disponíveis</option>}{data?.torneios.map(value => <option key={value} value={value}>{value}</option>)}
          </select></label></div>
          <div className="filter-note"><Icon name="info" size={19} /><p>Os valores refletem as partidas disponíveis.<br /> Novos resultados podem alterar a premiação.</p></div>
        </div>
        {status === 'loading' && <div className="loading-state" role="status"><span className="loader" /> Consultando os resultados do torneio…</div>}
        {status === 'error' && <div className="error-state" role="alert"><Icon name="info" size={24} /><div><h3>Não conseguimos carregar os resultados.</h3><p>{error}</p></div><button onClick={() => setRefresh(value => value + 1)}>Tentar novamente</button></div>}
        {ready && !hasMatches && <div className="empty-state"><Icon name="trophy" size={38} /><h3>Os próximos destaques estão por vir.</h3><p>Ainda não há partidas disponíveis para esta seleção. Os resultados aparecerão aqui quando forem registrados.</p><button onClick={() => { setYear(''); setTournament(''); setRefresh(value => value + 1); }}>Consultar torneios disponíveis</button></div>}
        {hasMatches && <>
          <div className="stats-grid">
            <Stat icon="trophy" label="PREMIAÇÃO BASE" value={money(data.premio_base_rs)} note="Valor de referência para o pódio" />
            <Stat icon="grid" label="PARTIDAS CONSIDERADAS" value={String(data.total_partidas).padStart(2, '0')} note="Resultados registrados no torneio" />
            <Stat icon="users" label="JOGADORES NA DISPUTA" value={String(players.length).padStart(2, '0')} note={`${ranking.length} times na classificação`} />
          </div>
          <section className="podium-section" aria-labelledby="podium-title"><div className="section-heading"><div><span className="eyebrow">QUEM ESTÁ NO TOPO</span><h2 id="podium-title">O pódio até aqui</h2></div><span className="section-caption">Classificação por vitórias e abates</span></div>
            {ranking.some(team => team.premio_rs > 0) ? <div className="podium-grid">{ranking.filter(team => team.posicao <= 3 && team.premio_rs > 0).map(team => <article key={team.time} className={team.posicao === 1 ? 'podium-card first' : 'podium-card'}>
              <div className="podium-top"><span>{String(team.posicao).padStart(2, '0')} <small>LUGAR</small></span><Icon name="trophy" size={25} /></div><h3>{team.time}</h3><p>{team.vitorias} {team.vitorias === 1 ? 'vitória' : 'vitórias'} <span>·</span> {team.kills} abates</p><div className="podium-prize"><span>PREMIAÇÃO DO TIME</span><strong>{money(team.premio_rs)}</strong></div>
            </article>)}</div> : <p className="inline-note">Ainda não há times com vitórias elegíveis para premiação.</p>}
            <p className="podium-note">Empates em vitórias e abates compartilham a posição e as parcelas correspondentes do prêmio.</p>
          </section>
          <section id="players" aria-labelledby="players-title" className="players-section">
            <div className="section-heading"><div><span className="eyebrow">CADA JOGADOR TEM SUA PARTE</span><h2 id="players-title">Sua premiação, em detalhes.</h2></div><button className="share-button" onClick={share}><Icon name="link" size={17} /> Compartilhar resultado</button></div>
            <p className="share-status" role="status">{shareStatus}</p>
            <div className="players-panel"><div className="table-toolbar"><label className="search-field"><Icon name="search" size={18} /><span className="sr-only">Buscar jogador ou time</span><input type="search" placeholder="Busque seu nickname ou time" value={search} onChange={event => { setSearch(event.target.value); setPage(1); setExpanded(null); }} /></label><span>Critério de divisão: <strong>{criterionLabel}</strong></span></div>
              <div className="table-scroll"><table><caption className="sr-only">Premiações parciais por jogador, ordenadas por valor, time e nickname</caption><thead><tr><th scope="col">JOGADOR / TIME</th><th scope="col">PARTIDAS</th><th scope="col">MINUTOS</th><th scope="col">ABATES</th><th scope="col">PREMIAÇÃO</th><th scope="col"><span className="sr-only">Detalhes</span></th></tr></thead><tbody>
                {rows.map((player, index) => {
                  const key = playerKey(player);
                  const team = ranking.find(item => item.time === player.time);
                  const teamTotal = players.filter(item => item.time === player.time).reduce((sum, item) => sum + (data.criterio === 'kills' ? item.kills : item.minutos), 0);
                  const points = data.criterio === 'kills' ? player.kills : player.minutos;
                  const detailsId = `details-${index}`;
                  return <React.Fragment key={key}><tr><th scope="row"><div className="player-cell"><span className="player-avatar" aria-hidden="true">{player.jogador.slice(0, 2).toUpperCase()}</span><span><strong>{player.jogador}</strong><small>{player.time}</small></span></div></th><td>{player.partidas}</td><td>{player.minutos}<small> min</small></td><td>{player.kills}</td><td><strong className="player-prize">{money(player.premio_rs)}</strong></td><td><button className="details-button" aria-label={`Ver cálculo de ${player.jogador}, ${player.time}`} aria-expanded={expanded === key} aria-controls={expanded === key ? detailsId : undefined} onClick={() => setExpanded(expanded === key ? null : key)}>{expanded === key ? 'Fechar' : 'Ver cálculo'}</button></td></tr>
                    {expanded === key && <tr id={detailsId} className="details-row"><td colSpan={6}><strong>Como o valor foi calculado</strong><p>Premiação do time: {money(team?.premio_rs || 0)}. {criterionLabel} do jogador: {points}; total do time: {teamTotal}.</p><p>{teamTotal > 0 ? `Participação no critério: ${(points / teamTotal * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%.` : 'Sem pontos no critério, o valor individual é zero.'} Valor individual: {money(player.premio_rs)}.</p><span>Valor calculado e arredondado a centavos. Não é uma confirmação de pagamento.</span></td></tr>}
                  </React.Fragment>;
                })}
              </tbody></table></div>
              {!filtered.length && <div className="no-players"><Icon name="search" size={28} /><h3>{search ? 'Nenhum jogador encontrado.' : 'Ainda não há jogadores disponíveis.'}</h3><p>{search ? 'Tente outro nickname ou nome de time.' : 'As estatísticas aparecerão com os próximos resultados.'}</p>{search && <button onClick={() => { setSearch(''); setPage(1); }}>Limpar busca</button>}</div>}
              <div className="pagination"><span role="status">{filtered.length ? `${(currentPage - 1) * 10 + 1}–${Math.min(currentPage * 10, filtered.length)} de ${filtered.length} jogadores` : '0 jogadores'}</span><nav aria-label="Paginação dos jogadores"><button aria-label="Página anterior" disabled={currentPage === 1} onClick={() => { setPage(currentPage - 1); setExpanded(null); }}>←</button><span aria-current="page">{currentPage} / {pages}</span><button aria-label="Próxima página" disabled={currentPage === pages} onClick={() => { setPage(currentPage + 1); setExpanded(null); }}>→</button></nav></div>
            </div>
          </section>
          <section className="rules-note"><span className="note-icon"><Icon name="info" size={23} /></span><div><h3>Transparência em cada resultado.</h3><p>O pódio recebe 50%, 30% e 20% do prêmio base, respeitando os empates. Dentro de cada time, a divisão é proporcional a {criterionLabel.toLowerCase()}. Times sem vitórias não recebem premiação; parcelas não ocupadas não são redistribuídas.</p><p>Os valores são parciais e não indicam pagamento realizado.</p></div></section>
        </>}
      </div>
    </main>
    <footer className="site-footer"><span><strong>Tournament Hub</strong> · Dados claros. Decisões justas.</span><span>Consulta pública · Sem necessidade de login</span></footer>
  </div>;
}

function Stat({ icon, label, value, note }) {
  return <div className="stat-card"><div><span>{label}</span><Icon name={icon} size={21} /></div><strong>{value}</strong><p>{note}</p></div>;
}

import React, { useEffect, useState } from 'react';
import Icon from '../components/Icon';
import MatchTable from '../components/MatchTable';
import Pagination from '../components/Pagination';
import useSavedMatches from '../hooks/useSavedMatches';

export default function HistoryPage({ navigate }) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [refresh, setRefresh] = useState(0);
  const state = useSavedMatches({ page, pageSize, search, refresh });
  const loading = state.status === 'loading';
  const total = state.data?.total || 0;
  useEffect(() => {
    if (state.status === 'success' && page > 1 && (page - 1) * pageSize >= total) setPage(Math.max(1, Math.ceil(total / pageSize)));
  }, [state.status, page, pageSize, total]);
  return <>
    <div className="page-heading heading-with-action"><div><span className="eyebrow">SEU HISTÓRICO</span><h1>Resultados que ficam.</h1><p>Revisite as partidas já consultadas e salvas no banco.</p></div><button className="button button-primary" onClick={() => navigate('nova')}>Nova consulta<Icon name="arrow" size={18} /></button></div>
    <div className="history-banner"><span className="history-banner-icon"><Icon name="clock" size={26} /></span><div><strong>Seu acervo de partidas</strong><p>Cada partida salva aparece uma vez, mesmo que tenha sido consultada em mais de um CSV.</p></div><span className="badge badge-green"><span className="status-dot" />Salvas no banco</span></div>
    <section className="panel match-panel" aria-labelledby="history-title"><div className="panel-heading"><div><span className="eyebrow">CONSULTAS ANTERIORES</span><h2 id="history-title">Partidas salvas {state.data && <span className="inline-count">{total}</span>}</h2></div><button className="button button-secondary button-small" disabled={loading} onClick={() => setRefresh(value => value + 1)}><Icon name="refresh" size={16} />Atualizar</button></div>
      <div className="table-toolbar"><form className="search-form" onSubmit={event => { event.preventDefault(); setSearch(searchInput.trim()); setPage(1); setRefresh(value => value + 1); }}><Icon name="search" size={18} /><input aria-label="Buscar partidas salvas" type="search" placeholder="Buscar por ID ou confronto…" maxLength={100} value={searchInput} onChange={event => setSearchInput(event.target.value)} /><button className="button button-secondary button-small" disabled={loading} type="submit">Buscar</button></form><span className="toolbar-note">Mais recentes primeiro</span></div>
      {state.error ? <div className="history-error" role="alert"><h3>Não foi possível carregar o histórico</h3><p>{state.error}</p><button className="button button-secondary" onClick={() => setRefresh(value => value + 1)}>Tentar novamente</button></div> : <MatchTable partidas={state.data?.partidas || []} loading={loading} emptyTitle={search ? 'Nenhum resultado para essa busca' : 'Seu histórico começa com uma consulta'} emptyMessage={search ? 'Tente outro ID ou nome de time.' : 'Envie um CSV na aba Nova consulta. As partidas salvas aparecerão aqui.'} />}
      <Pagination page={page} pageSize={pageSize} total={total} disabled={loading || state.status === 'error'} onPageChange={setPage} onPageSizeChange={size => { setPageSize(size); setPage(1); }} />
    </section>
  </>;
}

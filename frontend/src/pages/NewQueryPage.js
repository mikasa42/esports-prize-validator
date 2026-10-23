import React, { useEffect, useState } from 'react';
import Icon from '../components/Icon';
import MatchTable from '../components/MatchTable';
import Pagination from '../components/Pagination';
import PrizeResults from '../components/PrizeResults';
import CsvComparison from '../components/CsvComparison';

export default function NewQueryPage({ lookup, file, setFile, criterio, setCriterio }) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [dragging, setDragging] = useState(false);
  const loading = lookup.status === 'loading';
  const data = lookup.data;
  const matches = data?.partidas || [];
  useEffect(() => setPage(1), [data]);
  function chooseFile(nextFile) {
    setFile(nextFile || null);
    lookup.clear();
    setPage(1);
  }
  return <>
    <div className="page-heading"><span className="eyebrow">NOVA CONSULTA</span><h1>Da planilha ao resultado.</h1><p>Confira os dados da sua planilha com a API oficial e consulte a premiação.</p></div>
    {lookup.queries?.length > 0 && <section className="panel" aria-label="Consultas recentes"><label htmlFor="recent-query">Suas últimas consultas</label><select id="recent-query" value={lookup.selected || ''} onChange={event => event.target.value ? lookup.open(event.target.value) : lookup.clear()}><option value="">Nova consulta</option>{lookup.queries.map(query => <option key={query.id} value={query.id}>{query.nome_arquivo} · {query.criterio} · {query.status} · {query.processadas}/{query.total}</option>)}</select></section>}
    <div className="query-grid"><section className="panel upload-panel" aria-labelledby="upload-title"><div className="panel-heading"><div><span className="eyebrow">01 / SEU ARQUIVO</span><h2 id="upload-title">Consultar partidas pelo CSV</h2></div><span className="badge badge-neutral">Até 10 MB</span></div>
      <form onSubmit={event => { event.preventDefault(); lookup.submit(file, criterio); }}>
        <label className={`upload-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''} ${loading ? 'is-disabled' : ''}`} onDragOver={event => { event.preventDefault(); if (!loading) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); if (!loading) chooseFile(event.dataTransfer.files[0]); }}>
          <input className="upload-input" type="file" aria-label="Arquivo CSV" accept=".csv,text/csv" disabled={loading} onChange={event => chooseFile(event.target.files?.[0])} />
          <span className="upload-icon"><Icon name={file ? 'file' : 'upload'} size={26} /></span>
          <strong>{file ? file.name : 'Arraste seu CSV para cá'}</strong><span>{file ? `${(file.size / 1024).toFixed(1)} KB · Clique para trocar o arquivo` : 'ou clique para selecionar um arquivo'}</span><small>Arquivo .csv em UTF-8</small>
        </label>
        <fieldset className="criteria-fieldset" disabled={loading}><legend>02 / CRITÉRIO DE RATEIO</legend><div className="criteria-options">{[['minutos', 'clock', 'Minutos jogados', 'Tempo de participação'], ['kills', 'trophy', 'Abates', 'Desempenho em kills']].map(([value, icon, title, subtitle]) => <label className={`criterion-option ${criterio === value ? 'selected' : ''}`} key={value}><input type="radio" name="criterio" value={value} checked={criterio === value} onChange={() => setCriterio(value)} /><Icon name={icon} size={20} /><span><strong>{title}</strong><small>{subtitle}</small></span><span className="radio-mark" /></label>)}</div></fieldset>
        <div className="form-bottom"><span><Icon name="check" size={15} />Dados salvos para consultas posteriores.</span><button className="button button-primary" type="submit" disabled={loading || !file}>{loading ? 'Consultando…' : 'Consultar partidas'}<Icon name={loading ? 'refresh' : 'arrow'} className={loading ? 'spinning' : ''} size={18} /></button></div>
      </form>
    </section><aside className="csv-guide"><span className="eyebrow">ANTES DE COMEÇAR</span><h2>Um arquivo.<br />Todas as partidas.</h2><p>Use a coluna <code>id_partida</code> ou <code>ID Partida</code>. Inclua time, jogador, Minutos, Kills e Rodada para comparar. Data, torneio, mortes, assistências e resultado também podem ser conferidos.</p><div className="csv-preview"><div><Icon name="file" size={16} /><span>partidas.csv</span><span className="file-dot" /></div><pre><span>id_partida,time,jogador,Minutos,Kills,Rodada</span>{'\nMATCH-1001,FURIA,chelo,24,12,1\nMATCH-1001,FURIA,FalleN,28,15,1'}</pre></div><a className="download-link" href={`data:text/csv;charset=utf-8,${encodeURIComponent('id_partida,time,jogador,Minutos,Kills,Rodada,Data,torneio,Deaths,Assists,Venceu?,Observação\nMATCH-1001,FURIA,chelo,24,12,1,2026-10-01,tournament-55,15,5,Sim,Exemplo de conferência\nMATCH-1001,FURIA,FalleN,28,15,1,2026-10-01,tournament-55,11,10,Sim,Exemplo de conferência\n')}`} download="partidas-exemplo.csv">Baixar CSV de exemplo<Icon name="arrow" size={16} /></a><div className="guide-footnote"><Icon name="clock" size={17} /><span>Partidas já salvas são reutilizadas automaticamente.</span></div></aside></div>
    {lookup.error && <div className="alert alert-error" role="alert">{lookup.error}</div>}
    {loading && <div className="alert alert-info" role="status" aria-live="polite">{!lookup.progress ? 'Enviando o arquivo…' : lookup.progress.status === 'pendente' ? 'Consulta na fila. O processamento começará em breve.' : `Processando ${lookup.progress.processadas} de ${lookup.progress.total} partidas.`} Você pode navegar pelo painel; a consulta continuará em segundo plano.{lookup.progress && <progress aria-label="Progresso da consulta" value={lookup.progress.processadas} max={lookup.progress.total || 1} />}</div>}
    {data && <>
      <div className="result-summary" role="status"><span className="summary-icon"><Icon name="check" size={20} /></span><div><strong>{matches.length} de {data.total_solicitado} partidas encontradas.</strong><span>{data.falhas.length ? 'Confira as partidas disponíveis e os IDs que precisam de atenção.' : 'Tudo pronto. Confira os jogadores, a classificação e os prêmios.'}</span></div><span className="badge badge-neutral">Consulta concluída</span></div>
      {data.falhas.map((failure, index) => <div className="alert alert-error" role="alert" key={`${failure.match_id_externo}-${index}`}>{failure.match_id_externo}: {failure.erro}</div>)}
      {data.falhas.length > 0 && <p className="panel-note">Consulte novamente os IDs com falha para completar a classificação e as premiações.</p>}
      <section className="panel match-panel" aria-labelledby="new-matches-title"><div className="panel-heading"><div><span className="eyebrow">RESULTADOS DA CONSULTA</span><h2 id="new-matches-title">Partidas encontradas</h2></div><span className="count-tag">{matches.length}</span></div><MatchTable partidas={matches.slice((page - 1) * pageSize, page * pageSize)} emptyTitle="Nenhuma partida encontrada" emptyMessage="Confira os IDs do arquivo e tente novamente." /><Pagination page={page} pageSize={pageSize} total={matches.length} onPageChange={setPage} onPageSizeChange={size => { setPageSize(size); setPage(1); }} /></section>
      <CsvComparison comparison={data.comparacao_csv} />
      <PrizeResults classificacao={data.classificacao} premios={data.premios} />
    </>}
  </>;
}

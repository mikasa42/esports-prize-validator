import React, { useEffect, useState } from 'react';
import Icon from './Icon';
import './CsvComparison.css';

const labels = { conferente: 'Confere', divergente: 'Divergência', ausente_csv: 'Ausente no CSV', invalido_csv: 'Valor inválido', nao_comparavel: 'Não comparável', sem_referencia: 'Sem referência oficial' };
const display = value => value === null || value === undefined ? '—' : typeof value === 'boolean' ? (value ? 'Sim' : 'Não') : String(value) === '' ? '(vazio)' : String(value);
const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

export default function CsvComparison({ comparison }) {
  const [filter, setFilter] = useState('todos');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  useEffect(() => { setPage(1); setFilter('todos'); setSearch(''); }, [comparison]);
  if (!comparison) return null;
  const summary = comparison.resumo;
  const all = comparison.linhas.flatMap(row => row.campos.map(cell => ({ ...cell, linha: row.linha, matchId: row.match_id_externo, jogador: row.jogador, origem: row.origem, duplicada: row.duplicada_de })));
  const query = normalize(search.trim());
  const filtered = all.filter(cell => (filter === 'todos' || (filter === 'atencao' ? ['divergente', 'ausente_csv', 'invalido_csv'].includes(cell.status) : cell.status === filter)) && normalize(`${cell.matchId} ${cell.jogador} ${cell.coluna} ${cell.csv}`).includes(query));
  const pages = Math.max(1, Math.ceil(filtered.length / 20));
  const current = Math.min(page, pages);
  return <section className="panel comparison-panel" aria-labelledby="comparison-title">
    <div className="panel-heading"><div><span className="eyebrow">CONFERÊNCIA DO ARQUIVO</span><h2 id="comparison-title">CSV × API oficial</h2></div><span className="count-tag">{summary.total_linhas} linhas</span></div>
    <p className="comparison-intro">Cada valor enviado é exibido ao lado da referência oficial. A classificação e os prêmios continuam usando os dados oficiais.</p>
    {comparison.somente_ids && <p className="comparison-notice"><Icon name="info" size={17} />Este CSV contém apenas IDs. Inclua time, jogador e as estatísticas para conferir abates, minutos e outros dados.</p>}
    <div className="comparison-summary" role="status"><div><strong>{summary.conferente}</strong><span>Campos conferem</span></div><div><strong>{summary.linhas_divergentes}</strong><span>Linhas com divergências</span></div><div><strong>{summary.nao_comparavel + summary.sem_referencia}</strong><span>Campos não comparados</span></div></div>
    {summary.linhas_duplicadas > 0 && <p className="comparison-note">{summary.linhas_duplicadas} linha(s) repetida(s) preservada(s) na conferência. Cada ID conta uma única vez para consultas e premiações.</p>}
    <div className="comparison-toolbar"><label><span>Buscar na conferência</span><input type="search" value={search} placeholder="Partida, jogador, coluna ou valor" onChange={event => { setSearch(event.target.value); setPage(1); }} /></label><label><span>Mostrar campos</span><select value={filter} onChange={event => { setFilter(event.target.value); setPage(1); }}><option value="todos">Todos os campos</option><option value="atencao">Divergentes, inválidos ou ausentes</option><option value="conferente">Apenas os que conferem</option><option value="nao_comparavel">Não comparáveis</option><option value="sem_referencia">Sem referência oficial</option></select></label></div>
    <p className="comparison-scroll-hint">Deslize a tabela para ver os valores do CSV e da API lado a lado.</p>
    <div className="table-scroll"><table className="comparison-table"><caption className="sr-only">Comparação de cada coluna por linha do CSV com a resposta oficial. Valores originais do arquivo são preservados.</caption><thead><tr><th scope="col">Linha / identificação</th><th scope="col">Coluna do CSV</th><th scope="col">Valor no CSV</th><th scope="col">API oficial</th><th scope="col">Conferência</th></tr></thead><tbody>{filtered.slice((current - 1) * 20, current * 20).map(cell => <tr key={`${cell.linha}-${cell.coluna}`} className={['divergente', 'ausente_csv', 'invalido_csv'].includes(cell.status) ? 'comparison-different' : ''}>
      <th scope="row"><strong>Linha {cell.linha}</strong><span>{cell.matchId}</span>{cell.jogador && <small>{cell.jogador}</small>}{cell.duplicada && <small>Repetida da linha {cell.duplicada}</small>}</th><td>{cell.coluna}</td><td className="comparison-value">{display(cell.csv)}</td><td className="comparison-value">{display(cell.oficial)}{cell.origem && <small>{cell.origem === 'banco' ? 'Resposta oficial salva' : 'Consultada na API'}</small>}</td><td><span className={`comparison-status ${cell.status}`}>{labels[cell.status]}</span>{cell.motivo && <p className="comparison-reason">{cell.motivo}</p>}</td>
    </tr>)}</tbody></table></div>
    {!filtered.length && <div className="comparison-empty">Nenhum campo corresponde aos filtros selecionados.</div>}
    <div className="comparison-pagination"><span role="status">{filtered.length ? `${(current - 1) * 20 + 1}–${Math.min(current * 20, filtered.length)} de ${filtered.length} campos` : '0 campos'}</span><nav aria-label="Paginação da conferência"><button className="button button-secondary button-small" aria-label="Página anterior da conferência" disabled={current <= 1} onClick={() => setPage(current - 1)}>Anterior</button><span aria-current="page">{current} / {pages}</span><button className="button button-secondary button-small" aria-label="Próxima página da conferência" disabled={current >= pages} onClick={() => setPage(current + 1)}>Próxima</button></nav></div>
    <p className="comparison-note">Campos sem equivalente, jogadores não identificados e respostas oficiais indisponíveis não são tratados como dados conferidos. O CSV e a conferência não são armazenados no histórico.</p>
  </section>;
}

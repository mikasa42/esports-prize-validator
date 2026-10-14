import React from 'react';
import Icon from './Icon';

export const currency = value => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
export default function PrizeResults({ classificacao, premios }) {
  if (!premios) return null;
  const label = premios.criterio_utilizado === 'minutos' ? 'Minutos jogados' : 'Abates';
  return <div className="results-grid">
    <section className="panel ranking-panel" aria-labelledby="ranking-title">
      <div className="panel-heading"><div><span className="eyebrow">O PÓDIO</span><h2 id="ranking-title">Classificação dos times</h2></div><Icon name="trophy" /></div>
      <ol className="ranking-list">{classificacao.map((item, index) => <li key={item.time}><span className={`ranking-position position-${index}`}>{String(index + 1).padStart(2, '0')}</span><strong>{item.time}</strong><span>{item.vitorias} {item.vitorias === 1 ? 'vitória' : 'vitórias'}</span></li>)}</ol>
      {!classificacao.length && <p className="panel-note">Nenhuma vitória registrada nas partidas consultadas.</p>}
      <div className="podium-note">Prêmio por colocação <strong>50% · 30% · 20%</strong></div>
    </section>
    <section className="panel prize-panel" aria-labelledby="prize-title">
      <div className="panel-heading"><div><span className="eyebrow">RATEIO POR {label.toUpperCase()}</span><h2 id="prize-title">Premiação dos jogadores</h2></div><span className="prize-total">{currency(10000)}</span></div>
      <div className="table-scroll"><table><caption className="sr-only">Distribuição de prêmios por {label.toLowerCase()}</caption><thead><tr><th scope="col">Jogador / time</th><th scope="col">{label}</th><th scope="col">Prêmio</th></tr></thead><tbody>{premios.premio_jogadores.map(player => <tr key={`${player.time}-${player.jogador}`}><td><strong>{player.jogador}</strong><span className="cell-note">{player.time}</span></td><td>{player[`total_${premios.criterio_utilizado}`]}</td><td className="prize-value">{currency(player.premio_rs)}</td></tr>)}</tbody></table></div>
      {!premios.premio_jogadores.length && <p className="panel-note">Nenhum jogador elegível para premiação.</p>}
    </section>
  </div>;
}

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function App() {
  const [arquivoCsv, setArquivoCsv] = useState(null);
  const [criterio, setCriterio] = useState('minutos');
  const [criterioSalvo, setCriterioSalvo] = useState('minutos');
  const [classificacao, setClassificacao] = useState([]);
  const [premios, setPremios] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(false);
  const requisicaoAtual = useRef(null);
  const API_URL = process.env.REACT_APP_API_URL || '';
  useEffect(() => () => requisicaoAtual.current?.abort(), []);

  const consultarCsv = async (event) => {
    event.preventDefault();
    requisicaoAtual.current?.abort();
    const controller = new AbortController();
    requisicaoAtual.current = controller;
    setErro('');
    setResultado(null);
    setClassificacao([]);
    setPremios(null);
    if (!arquivoCsv || !arquivoCsv.name.toLowerCase().endsWith('.csv')) {
      setErro('Selecione um arquivo .csv.');
      return;
    }
    if (arquivoCsv.size > 10 * 1024 * 1024) {
      setErro('O CSV deve ter no máximo 10 MB.');
      return;
    }
    const form = new FormData();
    form.append('arquivo', arquivoCsv);
    form.append('criterio', criterio);
    setLoading(true);
    try {
      const { data } = await axios.post(`${API_URL}/api/consultar-csv`, form, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setResultado(data);
      setClassificacao(data.classificacao);
      setPremios(data.premios);
      setCriterioSalvo(criterio);
    } catch (err) {
      if (controller.signal.aborted) return;
      const detail = err.response?.data?.detail;
      setErro(typeof detail === 'string' ? detail : 'Não foi possível consultar as partidas. Tente novamente.');
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '30px', maxWidth: '900px', margin: '0 auto', color: '#333' }}>
      <header style={{ borderBottom: '2px solid #eaeaea', paddingBottom: '20px', marginBottom: '30px' }}>
        <h1 style={{ color: '#2563eb', margin: '0 0 10px 0' }}>🏆 Painel de Gestão da Maria Clara</h1>
        <p style={{ margin: 0, color: '#666' }}>PowerRev Tech Challenge — Consulta de Partidas e Premiações</p>
      </header>
      <section style={{ margin: '25px 0', padding: '20px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
        <h2>Consultar partidas pelo CSV</h2>
        <p>Envie um CSV com a coluna id_partida ou ID Partida. Cada linha será consultada na API oficial, uma por vez, inclusive IDs repetidos. Os dados não são salvos.</p>
        <form onSubmit={consultarCsv} style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'end' }}>
          <label style={{ display: 'grid', gap: '6px' }}>
            Arquivo CSV (UTF-8, até 10 MB)
            <input type="file" accept=".csv,text/csv" disabled={loading} onChange={(event) => {
              setArquivoCsv(event.target.files?.[0] || null);
              setErro('');
              setResultado(null);
              setClassificacao([]);
              setPremios(null);
            }} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            Critério de rateio do prêmio
            <select value={criterio} disabled={loading} onChange={(event) => setCriterio(event.target.value)} style={{ padding: '8px' }}>
              <option value="minutos">Minutos Jogados</option>
              <option value="kills">Kills / Abates</option>
            </select>
          </label>
          <button type="submit" disabled={loading || !arquivoCsv} style={{ padding: '10px 20px', background: '#2563eb', color: 'white', border: 0, borderRadius: '5px', cursor: 'pointer' }}>
            {loading ? 'Consultando...' : 'Consultar partidas'}
          </button>
        </form>
        {erro && <p role="alert" style={{ color: '#b91c1c' }}>{erro}</p>}
        {resultado && <p role="status">{resultado.partidas.length} de {resultado.total_solicitado} partidas encontradas.</p>}
        {resultado?.falhas.map((falha, index) => (
          <p role="alert" key={`${index}-${falha.match_id_externo}`} style={{ color: '#b91c1c' }}>{falha.match_id_externo}: {falha.erro}</p>
        ))}
        {resultado?.falhas.length > 0 && <p>As partidas encontradas estão disponíveis abaixo. Consulte novamente para completar a classificação e as premiações.</p>}
        {resultado?.partidas.map((partida, index) => (
          <details key={`${index}-${partida.match_id_externo}`} style={{ marginTop: '16px' }} open>
            <summary>{partida.match_id_externo}: {partida.confronto} ({partida.data_partida}, rodada {partida.rodada}) — API oficial</summary>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', textAlign: 'left', marginTop: '10px' }}>
                <thead><tr><th>Time / Jogador</th><th>Minutos</th><th>Abates</th><th>Venceu?</th></tr></thead>
                <tbody>{partida.participantes.map((jogador) => (
                  <tr key={jogador.time_nick}>
                    <td>{jogador.time_nick}</td><td>{jogador.minutos}</td><td>{jogador.kills}</td><td>{jogador.venceu ? 'Sim' : 'Não'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </details>
        ))}
      </section>

      {/* Classificação dos Times */}
      <section style={{ marginBottom: '30px' }}>
        <h2>Classificação dos Times (por Vitórias)</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
              <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Time</th>
              <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Vitórias</th>
            </tr>
          </thead>
          <tbody>
            {classificacao.map((item, idx) => (
              <tr key={idx}>
                <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{item.time}</td>
                <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{item.vitorias}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Extrato de Prêmios */}
      <section>
          <h2>Distribuição de Prêmios (Base: R$ 10.000,00 | Critério: {premios?.criterio_utilizado || criterioSalvo})</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
            <thead>
              <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Time</th>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Jogador</th>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Total ({premios?.criterio_utilizado || criterioSalvo})</th>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Prêmio (R$)</th>
              </tr>
            </thead>
            <tbody>
              {(premios?.premio_jogadores || []).map((p, idx) => (
                <tr key={idx}>
                  <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{p.time}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{p.jogador}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>{p[`total_${premios?.criterio_utilizado || criterioSalvo}`]}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0', fontWeight: 'bold', color: '#16a34a' }}>
                    R$ {p.premio_rs.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
      </section>
    </div>
  );
}

export default App;

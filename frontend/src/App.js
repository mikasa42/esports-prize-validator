import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function App() {
  const [classificacao, setClassificacao] = useState([]);
  const [criterio, setCriterio] = useState('minutos');
  const [premios, setPremios] = useState(null);
  const [statusVerificacao, setStatusVerificacao] = useState(null);
  const [loading, setLoading] = useState(false);

  const [arquivoCsv, setArquivoCsv] = useState(null);
  const [nomeTorneio, setNomeTorneio] = useState('Torneio Setembro');
  const [torneioId, setTorneioId] = useState(1);
  const [importando, setImportando] = useState(false);
  const [resultadoImportacao, setResultadoImportacao] = useState(null);
  const [erroImportacao, setErroImportacao] = useState('');
  const [erroDados, setErroDados] = useState('');
  const [atualizacao, setAtualizacao] = useState(0);
  const inputCsv = useRef(null);

  const API_URL = process.env.REACT_APP_API_URL || "";

  useEffect(() => {
    const controller = new AbortController();
    setErroDados('');
    Promise.all([
      axios.get(`${API_URL}/api/classificacao`, { params: { torneio_id: torneioId }, signal: controller.signal }),
      axios.get(`${API_URL}/api/premios`, { params: { criterio, torneio_id: torneioId }, signal: controller.signal }),
    ]).then(([resClass, resPremios]) => {
      setClassificacao(resClass.data.classificacao);
      setPremios(resPremios.data);
    }).catch((err) => {
      if (!axios.isCancel(err)) {
        setClassificacao([]);
        setPremios(null);
        setErroDados('Não foi possível carregar os dados. Importe um CSV ou tente novamente.');
      }
    });
    return () => controller.abort();
  }, [API_URL, criterio, torneioId, atualizacao]);

  const importarCsv = async (event) => {
    event.preventDefault();
    setErroImportacao('');
    setResultadoImportacao(null);
    if (!arquivoCsv || !arquivoCsv.name.toLowerCase().endsWith('.csv')) {
      setErroImportacao('Selecione um arquivo .csv.');
      return;
    }
    if (arquivoCsv.size > 10 * 1024 * 1024) {
      setErroImportacao('O CSV deve ter no máximo 10 MB.');
      return;
    }
    setImportando(true);
    const form = new FormData();
    form.append('arquivo', arquivoCsv);
    form.append('nome', nomeTorneio.trim());
    try {
      const { data } = await axios.post(`${API_URL}/api/importar-csv`, form);
      setResultadoImportacao(data);
      setTorneioId(data.torneio_id);
      setStatusVerificacao(null);
      setClassificacao([]);
      setPremios(null);
      setAtualizacao((value) => value + 1);
      setArquivoCsv(null);
      if (inputCsv.current) inputCsv.current.value = '';
    } catch (err) {
      const detail = err.response?.data?.detail;
      setErroImportacao(typeof detail === 'string' ? detail : 'Não foi possível importar o CSV. Verifique a conexão e tente novamente.');
    } finally {
      setImportando(false);
    }
  };

  const dispararVerificacao = async () => {
    setLoading(true);
    setStatusVerificacao(null);
    try {
      const res = await axios.post(`${API_URL}/api/verificar-partidas`, null, { params: { torneio_id: torneioId } });
      setStatusVerificacao(res.data);
    } catch (err) {
      alert("Erro ao verificar partidas com o site oficial.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '30px', maxWidth: '900px', margin: '0 auto', color: '#333' }}>
      <header style={{ borderBottom: '2px solid #eaeaea', paddingBottom: '20px', marginBottom: '30px' }}>
        <h1 style={{ color: '#2563eb', margin: '0 0 10px 0' }}>🏆 Painel de Gestão da Maria Clara</h1>
        <p style={{ margin: 0, color: '#666' }}>PowerRev Tech Challenge — Conferência de Torneios e Premiações</p>
      </header>

      <section style={{ margin: '25px 0', padding: '20px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
        <h2>Importar dados do torneio</h2>
        <p>Selecione um CSV para atualizar os dados do torneio. A importação substitui as partidas, participantes e conferências do torneio com o mesmo nome.</p>
        <form onSubmit={importarCsv} style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'end' }}>
          <label style={{ display: 'grid', gap: '6px' }}>
            Nome do torneio
            <input value={nomeTorneio} onChange={(event) => setNomeTorneio(event.target.value)} required maxLength={100} disabled={importando || loading} style={{ padding: '8px' }} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>
            Arquivo CSV (UTF-8, até 10 MB)
            <input ref={inputCsv} type="file" accept=".csv,text/csv" disabled={importando || loading} onChange={(event) => {
              setArquivoCsv(event.target.files?.[0] || null);
              setErroImportacao('');
              setResultadoImportacao(null);
            }} />
          </label>
          <button type="submit" disabled={importando || loading || !arquivoCsv || !nomeTorneio.trim()} style={{ padding: '10px 20px', background: '#2563eb', color: 'white', border: 0, borderRadius: '5px', cursor: 'pointer' }}>
            {importando ? 'Enviando...' : 'Enviar'}
          </button>
        </form>
        <p style={{ fontSize: '13px', color: '#475569', overflowWrap: 'anywhere' }}>Colunas: Data, Rodada, ID Partida, Partida, Time / Nick, Minutos, Kills, Venceu?</p>
        {erroImportacao && <p role="alert" style={{ color: '#b91c1c' }}>{erroImportacao}</p>}
        {resultadoImportacao && <p role="status" style={{ color: '#166534' }}>Importação concluída: {resultadoImportacao.partidas} partidas e {resultadoImportacao.participantes} participações de jogadores. Os dados foram salvos.</p>}
      </section>
      {erroDados && <p role="alert" style={{ color: '#b91c1c' }}>{erroDados}</p>}

      {/* Seção de Ações */}
      <section style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', marginBottom: '30px', border: '1px solid #e2e8f0' }}>
        <h2>Painel de Controle</h2>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center', marginTop: '15px' }}>
          <button 
            onClick={dispararVerificacao} 
            disabled={loading || importando}
            style={{ background: '#2563eb', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            {loading ? "Conferindo no Site Oficial..." : "🔄 Conferir Partidas no Site Oficial"}
          </button>

          <label style={{ fontWeight: 'bold', marginLeft: '20px' }}>Critério de Rateio do Prêmio:</label>
          <select 
            value={criterio} 
            disabled={importando || loading}
            onChange={(e) => setCriterio(e.target.value)}
            style={{ padding: '8px', borderRadius: '5px', border: '1px solid #cbd5e1' }}
          >
            <option value="minutos">Minutos Jogados (Atual)</option>
            <option value="kills">Kills / Abates (Nova Ideia)</option>
          </select>
        </div>

        {statusVerificacao && (
          <div style={{ marginTop: '20px', background: '#e2e8f0', padding: '15px', borderRadius: '5px' }}>
            <strong>Resultado da Verificação:</strong> {statusVerificacao.status_geral}
            <p>Total de Partidas Validadas: {statusVerificacao.total_partidas_verificadas}</p>
            {statusVerificacao.divergencias_ou_falhas.length > 0 && (
              <p style={{ color: '#dc2626' }}>Atenção: Foram encontradas divergências ou instabilidades em algumas partidas.</p>
            )}
          </div>
        )}
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
      {premios && (
        <section>
          <h2>Distribuição de Prêmios (Base: R$ 10.000,00 | Critério: {premios.criterio_utilizado})</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
            <thead>
              <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Time</th>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Jogador</th>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Total ({premios.criterio_utilizado})</th>
                <th style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>Prêmio (R$)</th>
              </tr>
            </thead>
            <tbody>
              {premios.premio_jogadores.map((p, idx) => (
                <tr key={idx}>
                  <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{p.time}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{p.jogador}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #cbd5e1' }}>{p[`total_${premios.criterio_utilizado}`]}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0', fontWeight: 'bold', color: '#16a34a' }}>
                    R$ {p.premio_rs.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

export default App;

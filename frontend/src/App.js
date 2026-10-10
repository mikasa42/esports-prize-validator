import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [classificacao, setClassificacao] = useState([]);
  const [criterio, setCriterio] = useState('minutos');
  const [premios, setPremios] = useState(null);
  const [statusVerificacao, setStatusVerificacao] = useState(null);
  const [loading, setLoading] = useState(false);

  const API_URL = "http://localhost:8000";

  const carregarDados = async () => {
    try {
      const resClass = await axios.get(`${API_URL}/api/classificacao`);
      setClassificacao(resClass.data.classificacao);

      const resPremios = await axios.get(`${API_URL}/api/premios?criterio=${criterio}`);
      setPremios(resPremios.data);
    } catch (err) {
      console.error("Erro ao carregar dados da API:", err);
    }
  };

  useEffect(() => {
    carregarDados();
  }, [criterio]);

  const dispararVerificacao = async () => {
    setLoading(true);
    setStatusVerificacao(null);
    try {
      const res = await axios.post(`${API_URL}/api/verificar-partidas`);
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

      {/* Seção de Ações */}
      <section style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', marginBottom: '30px', border: '1px solid #e2e8f0' }}>
        <h2>Painel de Controle</h2>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center', marginTop: '15px' }}>
          <button 
            onClick={dispararVerificacao} 
            disabled={loading}
            style={{ background: '#2563eb', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            {loading ? "Conferindo no Site Oficial..." : "🔄 Conferir Partidas no Site Oficial"}
          </button>

          <label style={{ fontWeight: 'bold', marginLeft: '20px' }}>Critério de Rateio do Prêmio:</label>
          <select 
            value={criterio} 
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
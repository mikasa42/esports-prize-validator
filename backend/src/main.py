from fastapi import FastAPI, HTTPException, Query
from src.services.tournament_service import TournamentService
from src.simulator.api_simulator import OficialApiSimulator

app = FastAPI(title="PowerRev Tournament API", version="1.0")
tournament_service = TournamentService()

@app.get("/")
def read_root():
    return {"message": "API de Gestão de Torneios operando com sucesso!"}

@app.get("/api/classificacao")
def obter_classificacao():
    try:
        classificacao = tournament_service.calcular_vitorias_por_time()
        return {"classificacao": classificacao}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/premios")
def calcular_premios(
    premio_total: float = Query(10000.00, description="Valor total do prêmio em dinheiro"),
    criterio: str = Query("minutos", description="Critério de rateio: 'minutos' ou 'kills'")
):
    try:
        resultado = tournament_service.calcular_rateio_premios(premio_total, criterio)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verificar-partidas")
def verificar_partidas():
    """
    Lê o CSV da Maria Clara, extrai os IDs de partidas únicos e valida cada um 
    contra o simulador da API oficial (tratando lentidão e instabilidades).
    """
    try:
        df = tournament_service.carregar_dados()
        match_ids = df['ID Partida'].unique().tolist()
        
        resultados_verificacao = []
        erros_encontrados = []
        
        for match_id in match_ids:
            try:
                res = OficialApiSimulator.consultar_partida(match_id)
                resultados_verificacao.append(res)
            except Exception as err:
                erros_encontrados.append({
                    "match_id_externo": match_id,
                    "status": "divergente_ou_erro",
                    "detalhe": str(err)
                })
                
        return {
            "total_partidas_verificadas": len(match_ids),
            "sucessos": resultados_verificacao,
            "divergencias_ou_falhas": erros_encontrados,
            "status_geral": "Conferência concluída com sucesso" if not erros_encontrados else "Conferência concluída com divergências"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
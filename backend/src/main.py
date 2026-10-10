from fastapi import FastAPI, HTTPException, Query
from src.services.tournament_service import TournamentService

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
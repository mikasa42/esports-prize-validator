from concurrent.futures import ThreadPoolExecutor

import logging
import json
import os
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.import_csv import CsvConflitante, importar_csv_conteudo
from src.database import engine, partidas
from src.services.tournament_service import TournamentService
from src.services.verification_service import verificar_grupo

app = FastAPI(title="PowerRev Tournament API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
tournament_service = TournamentService()

@app.get("/")
def read_root():
    return {"message": "API de Gestão de Torneios operando com sucesso!"}

MAX_CSV_BYTES = 10 * 1024 * 1024


@app.post("/api/importar-csv", status_code=201)
def upload_csv(
    arquivo: UploadFile = File(...),
    nome: str = Form("Torneio Setembro"),
    criterio: Literal["minutos", "kills"] = Form("minutos"),
):
    """Valida o CSV enviado e substitui os dados do torneio em uma transação."""
    try:
        if not arquivo.filename or not arquivo.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Selecione um arquivo .csv.")
        content = arquivo.file.read(MAX_CSV_BYTES + 1)
        if len(content) > MAX_CSV_BYTES:
            raise HTTPException(status_code=413, detail="O CSV deve ter no máximo 10 MB.")
        if not content.strip():
            raise HTTPException(status_code=400, detail="O arquivo CSV está vazio.")
        resultado = importar_csv_conteudo(content, nome, criterio)
        mensagem = "CSV já cadastrado. Dados existentes carregados." if resultado.get("reutilizado") else "CSV importado com sucesso."
        return {"mensagem": mensagem, **resultado}
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Salve o CSV com codificação UTF-8.")
    except CsvConflitante as err:
        raise HTTPException(status_code=409, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Uma partida deste CSV já pertence a outro torneio. Os dados anteriores foram preservados.")
    except SQLAlchemyError:
        logging.exception("Falha na carga do CSV no banco")
        raise HTTPException(status_code=503, detail="Não foi possível salvar no banco. Tente novamente.")
    finally:
        arquivo.file.close()


@app.get("/api/classificacao")
def obter_classificacao(torneio_id: int = Query(1, ge=1)):
    try:
        classificacao = tournament_service.calcular_vitorias_por_time(torneio_id)
        return {"classificacao": classificacao}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/premios")
def calcular_premios(
    premio_total: float = Query(10000.00, ge=0, description="Valor total do prêmio em dinheiro"),
    criterio: Literal["minutos", "kills"] = Query("minutos", description="Critério de rateio: 'minutos' ou 'kills'"),
    torneio_id: int = Query(1, ge=1)
):
    try:
        resultado = tournament_service.calcular_rateio_premios(premio_total, criterio, torneio_id)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verificar-partidas")
def verificar_partidas(torneio_id: int = Query(1, ge=1)):
    """
    Consulta as partidas importadas no banco, extrai os IDs de partidas únicos e valida cada um
    contra o simulador da API oficial (tratando lentidão e instabilidades).
    """
    try:
        df = tournament_service.carregar_dados(torneio_id)
        # Limita a cinco consultas simultâneas para conferir o torneio completo.
        with ThreadPoolExecutor(max_workers=5) as executor:
            resultados = list(executor.map(verificar_grupo, df.groupby('ID Partida', sort=False)))
        resultados_verificacao = [res for res in resultados if res['verificado']]
        erros_encontrados = [res for res in resultados if not res['verificado']]

        with engine.begin() as conn:
            for resultado in resultados_verificacao + erros_encontrados:
                conn.execute(update(partidas).where(
                    partidas.c.torneio_id == torneio_id,
                    partidas.c.match_id_externo == resultado['match_id_externo'],
                ).values(
                    status_verificacao=resultado['status'],
                    detalhes_verificacao=json.dumps(resultado, ensure_ascii=False),
                ))
        tem_divergencias = any(res['status'] == 'divergente' for res in erros_encontrados)
        tem_instabilidade = any(res['status'] == 'erro_api' for res in erros_encontrados)
        if tem_divergencias and tem_instabilidade:
            status_geral = "Conferência concluída com divergências nos dados e instabilidade da API oficial"
        elif tem_instabilidade:
            status_geral = "Conferência incompleta por instabilidade da API oficial"
        elif tem_divergencias:
            status_geral = "Conferência concluída com divergências nos dados"
        else:
            status_geral = "Conferência concluída com sucesso"
        return {
            "total_partidas_verificadas": len(resultados),
            "sucessos": resultados_verificacao,
            "divergencias_ou_falhas": erros_encontrados,
            "status_geral": status_geral
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

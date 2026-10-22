"""Consultas anônimas somente de leitura, com contrato explícito de dados públicos."""
import os
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from src.services.tournament_winners_service import consultar_ganhadores

router = APIRouter(prefix='/api/publico', tags=['Resultados públicos'])


class TimePublico(BaseModel):
    time: str
    posicao: int
    vitorias: int
    kills: int
    premio_rs: float


class JogadorPublico(BaseModel):
    jogador: str
    time: str
    minutos: int
    kills: int
    partidas: int
    premio_rs: float


class ResultadosPublicos(BaseModel):
    anos: list[int]
    torneios: list[str]
    ano: int | None
    torneio: str | None
    total_partidas: int
    criterio: Literal['minutos', 'kills']
    status: Literal['parcial']
    premio_base_rs: float
    classificacao: list[TimePublico]
    jogadores: list[JogadorPublico]


@router.get('/resultados', response_model=ResultadosPublicos)
def resultados_publicos(
    ano: int | None = Query(None, ge=1900, le=9999),
    torneio: str | None = Query(None, min_length=1, max_length=100),
):
    # O visitante não escolhe um critério que altere os valores apresentados.
    criterio = os.environ.get('PUBLIC_PRIZE_CRITERION', 'minutos')
    if criterio not in {'minutos', 'kills'}:
        raise RuntimeError('PUBLIC_PRIZE_CRITERION deve ser minutos ou kills.')
    result = consultar_ganhadores(ano=ano, torneio=torneio, criterio=criterio)
    return {key: result[key] for key in (
        'anos', 'torneios', 'ano', 'torneio', 'total_partidas', 'criterio', 'classificacao', 'jogadores',
    )} | {'status': 'parcial', 'premio_base_rs': 10000.0}

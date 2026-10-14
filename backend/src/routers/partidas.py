"""Entrada HTTP para consultas de partidas e uploads CSV."""
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from src.repositories.match_repository import BancoIndisponivel
from src.services.match_lookup_service import consultar_csv, consultar_id

router = APIRouter(prefix='/api', tags=['Partidas'])

MAX_CSV_BYTES = 10 * 1024 * 1024


@router.get('/partidas/{match_id}')
def consultar_partida(match_id: str):
    try:
        result = consultar_id(match_id)
    except BancoIndisponivel as err:
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    if 'erro' in result:
        raise HTTPException(status_code=404 if result['status'] == 'nao_encontrada' else 502, detail=result)
    return result


@router.post('/consultar-csv')
def consultar_partidas_csv(
    arquivo: UploadFile = File(...),
    criterio: Literal['minutos', 'kills'] = Form('minutos'),
):
    try:
        if not arquivo.filename or not arquivo.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail='Selecione um arquivo .csv.')
        content = arquivo.file.read(MAX_CSV_BYTES + 1)
        if len(content) > MAX_CSV_BYTES:
            raise HTTPException(status_code=413, detail='O CSV deve ter no máximo 10 MB.')
        if not content.strip():
            raise HTTPException(status_code=400, detail='O arquivo CSV está vazio.')
        return consultar_csv(content, criterio)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail='Salve o CSV com codificação UTF-8.')
    except BancoIndisponivel as err:
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        arquivo.file.close()

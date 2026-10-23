"""Criação e acompanhamento de consultas assíncronas autenticadas."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from typing import Literal
from src.routers.auth import usuario_atual, validar_requisicao
from src.routers.partidas import MAX_CSV_BYTES
from src.repositories import query_repository as repository
from src.services.match_lookup_service import ler_ids
from src.tasks import processar_consulta

router = APIRouter(prefix='/api/consultas', tags=['Consultas'], dependencies=[Depends(validar_requisicao)])
logger = logging.getLogger(__name__)


@router.post('', status_code=202)
def criar_consulta(response: Response, arquivo: UploadFile = File(...),
                   criterio: Literal['minutos', 'kills'] = Form('minutos'), usuario=Depends(usuario_atual)):
    try:
        if not arquivo.filename or not arquivo.filename.lower().endswith('.csv'):
            raise HTTPException(400, 'Selecione um arquivo .csv.')
        content = arquivo.file.read(MAX_CSV_BYTES + 1)
        if len(content) > MAX_CSV_BYTES:
            raise HTTPException(413, 'O CSV deve ter no máximo 10 MB.')
        if not content.strip():
            raise HTTPException(400, 'O arquivo CSV está vazio.')
        total = len(set(ler_ids(content)))
        consulta_id = repository.criar(usuario['id'], arquivo.filename, content, criterio, total)
    except UnicodeDecodeError:
        raise HTTPException(400, 'Salve o CSV com codificação UTF-8.')
    except ValueError as err:
        raise HTTPException(400, str(err))
    finally:
        arquivo.file.close()
    try:
        processar_consulta.apply_async(args=[consulta_id], expires=60, retry=False)
    except Exception:
        # A entrada já foi confirmada no banco. Beat vai reenviar após a recuperação.
        logger.exception('Consulta %s aguarda recuperação da fila', consulta_id)
    response.headers['Location'] = f'/api/consultas/{consulta_id}'
    response.headers['Cache-Control'] = 'no-store'
    return {'id': consulta_id, 'status': 'pendente', 'total': total, 'processadas': 0}


@router.get('')
def listar_consultas(response: Response, limit: int = Query(20, ge=1, le=100),
                     offset: int = Query(0, ge=0), usuario=Depends(usuario_atual)):
    response.headers['Cache-Control'] = 'no-store'
    return {'consultas': repository.listar(usuario['id'], limit, offset)}


def obter(consulta_id, usuario):
    consulta = repository.buscar(str(consulta_id), usuario['id'])
    if consulta is None:
        raise HTTPException(404, 'Consulta não encontrada.')
    return consulta


@router.get('/{consulta_id}')
def status_consulta(consulta_id: UUID, response: Response, usuario=Depends(usuario_atual)):
    response.headers['Cache-Control'] = 'no-store'
    consulta = obter(consulta_id, usuario)
    consulta.pop('resultado')
    return consulta


@router.get('/{consulta_id}/resultado')
def resultado_consulta(consulta_id: UUID, response: Response, usuario=Depends(usuario_atual)):
    response.headers['Cache-Control'] = 'no-store'
    consulta = obter(consulta_id, usuario)
    if consulta['status'] != 'concluida':
        raise HTTPException(409, consulta['erro'] or 'A consulta ainda não foi concluída.')
    return consulta['resultado']

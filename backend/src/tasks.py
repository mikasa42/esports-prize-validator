"""O MySQL é a fonte de verdade, inclusive quando Redis está indisponível."""
import logging
from src.celery_app import app
from src.repositories import query_repository as repository
from src.services.match_lookup_service import consultar_csv

logger = logging.getLogger(__name__)


@app.task
def processar_consulta(consulta_id):
    with repository.executar(consulta_id) as execution:
        if execution is None:
            return
        connection, row = execution
        try:
            resultado = consultar_csv(row['conteudo'], row['criterio'],
                progresso=lambda quantidade: repository.progresso(connection, consulta_id, quantidade))
        except Exception:
            logger.exception('Falha no processamento da consulta %s', consulta_id)
            # Falhas transitórias são retomadas pelo dispatcher; limite persistido de 3 tentativas.
            if row['tentativas'] + 1 >= 3:
                repository.finalizar(connection, consulta_id,
                    erro='Não foi possível processar a consulta após três tentativas. Envie novamente.')
            else:
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE consultas SET status='pendente' WHERE id=%s", (consulta_id,))
                connection.commit()
            return
        repository.finalizar(connection, consulta_id, resultado=resultado)


@app.task
def despachar_pendentes():
    for consulta_id in repository.pendentes():
        processar_consulta.apply_async(args=[consulta_id], expires=60, retry=False)

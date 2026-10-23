import io
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException, Response, UploadFile
from src.routers import consultas
from src.repositories import query_repository as repository
from src import tasks


class QueryRouteTests(unittest.TestCase):
    def upload(self, content=b'id_partida\nMATCH-1001\nMATCH-1001\nMATCH-1002\n'):
        return UploadFile(filename='partidas.csv', file=io.BytesIO(content))

    @patch.object(consultas.repository, 'criar', return_value='query-id')
    @patch.object(consultas.processar_consulta, 'apply_async')
    def test_accepts_and_persists_input_before_enqueue(self, enqueue, create):
        file = self.upload()
        response = Response()
        data = consultas.criar_consulta(response, file, 'kills', {'id': 7})
        self.assertEqual(data['total'], 2)
        self.assertEqual(create.call_args.args[0], 7)
        self.assertEqual(create.call_args.args[2], b'id_partida\nMATCH-1001\nMATCH-1001\nMATCH-1002\n')
        self.assertTrue(file.file.closed)
        enqueue.assert_called_once_with(args=['query-id'], expires=60, retry=False)
        self.assertEqual(response.headers['location'], '/api/consultas/query-id')

    @patch.object(consultas.repository, 'criar', return_value='query-id')
    @patch.object(consultas.processar_consulta, 'apply_async', side_effect=ConnectionError('offline'))
    def test_redis_outage_keeps_durable_job_accepted(self, enqueue, create):
        with self.assertLogs(consultas.logger, level='ERROR'):
            result = consultas.criar_consulta(Response(), self.upload(), 'minutos', {'id': 7})
        self.assertEqual(result['status'], 'pendente')
        create.assert_called_once()

    @patch.object(consultas.repository, 'criar')
    def test_invalid_csv_not_persisted(self, create):
        with self.assertRaises(HTTPException) as error:
            consultas.criar_consulta(Response(), self.upload(b'outra_coluna\na\n'), 'minutos', {'id': 7})
        self.assertEqual(error.exception.status_code, 400)
        create.assert_not_called()

    @patch.object(consultas.repository, 'buscar', return_value=None)
    def test_other_users_job_is_not_disclosed(self, buscar):
        query_id = uuid4()
        with self.assertRaises(HTTPException) as error:
            consultas.status_consulta(query_id, Response(), {'id': 8})
        self.assertEqual(error.exception.status_code, 404)
        buscar.assert_called_once_with(str(query_id), 8)

    @patch.object(consultas.repository, 'buscar', return_value={'status': 'processando', 'erro': None})
    def test_unfinished_result_returns_conflict(self, buscar):
        with self.assertRaises(HTTPException) as error:
            consultas.resultado_consulta(uuid4(), Response(), {'id': 7})
        self.assertEqual(error.exception.status_code, 409)

    @patch.object(consultas.repository, 'buscar', return_value={'status': 'concluida', 'resultado': {'partidas': []}})
    def test_completed_result_is_returned(self, buscar):
        self.assertEqual(consultas.resultado_consulta(uuid4(), Response(), {'id': 7}), {'partidas': []})


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.row = {'conteudo': b'csv', 'criterio': 'kills', 'tentativas': 0}

    @contextmanager
    def execution(self, query_id):
        yield self.connection, self.row

    @patch.object(tasks.repository, 'finalizar')
    @patch.object(tasks.repository, 'progresso')
    @patch.object(tasks, 'consultar_csv')
    def test_worker_reports_progress_and_persists_business_result(self, consult, progress, finish):
        expected = {'partidas': [], 'falhas': [{'erro': 'Partida não encontrada'}], 'premios': None}
        def process(content, criterion, progresso):
            progresso(1)
            return expected
        consult.side_effect = process
        with patch.object(tasks.repository, 'executar', self.execution):
            tasks.processar_consulta.run('id')
        progress.assert_called_once_with(self.connection, 'id', 1)
        finish.assert_called_once_with(self.connection, 'id', resultado=expected)

    @patch.object(tasks, 'consultar_csv')
    def test_duplicate_message_does_not_process_when_lock_unavailable(self, consult):
        @contextmanager
        def locked(query_id):
            yield None
        with patch.object(tasks.repository, 'executar', locked):
            tasks.processar_consulta.run('id')
        consult.assert_not_called()

    @patch.object(tasks.repository, 'finalizar')
    @patch.object(tasks, 'consultar_csv', side_effect=RuntimeError('db interrupted'))
    def test_transient_failure_requeues_until_third_attempt(self, consult, finish):
        with patch.object(tasks.repository, 'executar', self.execution), self.assertLogs(tasks.logger, level='ERROR'):
            tasks.processar_consulta.run('id')
            finish.assert_not_called()
            self.row['tentativas'] = 2
            tasks.processar_consulta.run('id')
        self.assertIn('três tentativas', finish.call_args.kwargs['erro'])

    @patch.object(tasks.repository, 'pendentes', return_value=['one', 'two'])
    @patch.object(tasks.processar_consulta, 'apply_async')
    def test_beat_recovers_jobs_using_only_ids(self, enqueue, pending):
        tasks.despachar_pendentes.run()
        self.assertEqual(enqueue.call_count, 2)
        enqueue.assert_any_call(args=['one'], expires=60, retry=False)


class RepositoryTests(unittest.TestCase):
    @patch.object(repository, 'conectar')
    def test_reads_are_scoped_to_owner(self, connect):
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        repository.buscar('query', 42)
        sql, params = cursor.execute.call_args.args
        self.assertIn('usuario_id=%s', sql)
        self.assertEqual(params, ('query', 42))

    @patch.object(repository, 'conectar')
    def test_completed_job_is_not_claimed_again_and_lock_released(self, connect):
        connection = connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [{'adquirido': 1}, {'status': 'concluida'}]
        with repository.executar('query') as execution:
            self.assertIsNone(execution)
        self.assertFalse(any('UPDATE' in call.args[0] for call in cursor.execute.call_args_list))
        cursor.execute.assert_any_call('SELECT RELEASE_LOCK(%s)', ('consulta:query',))
        connection.close.assert_called_once()

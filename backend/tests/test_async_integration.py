"""Opt-in: API, MySQL, Redis, worker e Beat reais; remove somente contas temporárias."""
import os
import secrets
import time
import unittest
from uuid import uuid4

import requests
from src.repositories.match_repository import conectar
from src.repositories import query_repository


@unittest.skipUnless(os.environ.get('ASYNC_TEST_BASE_URL'), 'Defina ASYNC_TEST_BASE_URL para testar Celery e Redis reais.')
class AsyncIntegrationTests(unittest.TestCase):
    def test_upload_isolated_results_duplicate_delivery_and_beat_recovery(self):
        base = os.environ['ASYNC_TEST_BASE_URL'].rstrip('/')
        users = []
        sessions = []
        try:
            for _ in range(2):
                session = requests.Session()
                session.headers['X-Requested-With'] = 'TournamentHub'
                login = f'async-test-{uuid4().hex}'
                response = session.post(f'{base}/api/auth/cadastro', json={
                    'nome': 'Teste temporário async', 'login': login,
                    'senha': secrets.token_urlsafe(24), 'empresa': 'Integração'}, timeout=10)
                response.raise_for_status()
                users.append(response.json()['id'])
                sessions.append(session)
            client, other = sessions
            # ID inexistente não cria ou altera partidas na instalação do usuário.
            content = f'id_partida\nASYNC-TEST-{uuid4().hex}\n'.encode()
            response = client.post(f'{base}/api/consultas', files={'arquivo': ('teste.csv', content, 'text/csv')},
                                   data={'criterio': 'kills'}, timeout=10)
            self.assertEqual(response.status_code, 202, response.text)
            query_id = response.json()['id']
            self.assertEqual(other.get(f'{base}/api/consultas/{query_id}', timeout=10).status_code, 404)
            self.assertEqual(other.get(f'{base}/api/consultas/{query_id}/resultado', timeout=10).status_code, 404)
            self.assertEqual(other.get(f'{base}/api/consultas', timeout=10).json()['consultas'], [])

            def await_result(query):
                deadline = time.monotonic() + 50
                while time.monotonic() < deadline:
                    status = client.get(f'{base}/api/consultas/{query}', timeout=10)
                    status.raise_for_status()
                    data = status.json()
                    if data['status'] in ('erro', 'concluida'):
                        self.assertEqual(data['status'], 'concluida', data)
                        self.assertEqual(data['processadas'], 1)
                        result = client.get(f'{base}/api/consultas/{query}/resultado', timeout=10)
                        result.raise_for_status()
                        self.assertEqual(len(result.json()['falhas']), 1)
                        self.assertIsNone(result.json()['premios'])
                        return
                    time.sleep(0.5)
                self.fail('Worker/Beat não concluiu a consulta em 50 segundos.')

            await_result(query_id)
            # Entrega duplicada após conclusão precisa ser inofensiva.
            from src.tasks import processar_consulta
            processar_consulta.run(query_id)
            connection = conectar()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT tentativas FROM consultas WHERE id=%s', (query_id,))
                    self.assertEqual(cursor.fetchone()['tentativas'], 1)
            finally:
                connection.close()
            # Simula commit no MySQL seguido de perda antes de publicar no Redis.
            recovered_id = query_repository.criar(users[0], 'recuperada.csv', content, 'minutos', 1)
            await_result(recovered_id)
            items = client.get(f'{base}/api/consultas', timeout=10).json()['consultas']
            self.assertEqual({item['id'] for item in items}, {query_id, recovered_id})
        finally:
            for session in sessions:
                session.close()
            if users:
                connection = conectar()
                try:
                    with connection.cursor() as cursor:
                        for user_id in users:
                            cursor.execute('DELETE FROM usuarios WHERE id=%s', (user_id,))
                    connection.commit()
                finally:
                    connection.close()

"""Fluxo real HTTP/MySQL, opcional: AUTH_TEST_BASE_URL=http://frontend."""
import os
import secrets
import unittest

import requests
from src.repositories.match_repository import conectar


@unittest.skipUnless(os.environ.get('AUTH_TEST_BASE_URL'), 'Requer serviços reais e AUTH_TEST_BASE_URL.')
class AuthIntegrationTests(unittest.TestCase):
    def test_registration_login_session_expiration_and_logout(self):
        base = os.environ['AUTH_TEST_BASE_URL'].rstrip('/')
        login = f'auth_test_{secrets.token_hex(8)}'
        password = secrets.token_urlsafe(24)
        session = requests.Session()
        session.headers.update({'X-Requested-With': 'TournamentHub', 'Origin': 'http://localhost:3000'})
        data = {'nome': 'Teste Autenticação', 'login': login, 'senha': password, 'empresa': 'Empresa de teste'}
        try:
            response = session.get(f'{base}/api/historico', timeout=10)
            self.assertEqual(response.status_code, 401)
            response = session.post(f'{base}/api/auth/cadastro', json=data, timeout=10)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()['empresa'], data['empresa'])
            self.assertNotIn('senha', response.json())
            original_cookie = session.cookies.get('tournament_session')
            self.assertTrue(original_cookie)
            self.assertEqual(session.get(f'{base}/api/auth/me', timeout=10).json()['login'], login)
            self.assertEqual(session.get(f'{base}/api/historico', timeout=10).status_code, 200)
            self.assertEqual(session.post(f'{base}/api/auth/cadastro', json=data, timeout=10).status_code, 409)
            self.assertEqual(session.post(f'{base}/api/auth/login', json={'login': login, 'senha': 'incorrect'}, timeout=10).status_code, 401)
            self.assertEqual(session.post(f'{base}/api/auth/login', json={'login': login.upper(), 'senha': password}, timeout=10).status_code, 200)
            self.assertNotEqual(session.cookies.get('tournament_session'), original_cookie)
            self.assertEqual(requests.get(f'{base}/api/auth/me', cookies={'tournament_session': original_cookie}, timeout=10).status_code, 401)
            connection = conectar()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT id, senha_hash FROM usuarios WHERE login = %s', (login,))
                    user = cursor.fetchone()
                    self.assertNotEqual(user['senha_hash'], password)
                    cursor.execute('UPDATE sessoes_usuario SET expira_em = DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 SECOND) WHERE usuario_id = %s', (user['id'],))
                connection.commit()
            finally:
                connection.close()
            self.assertEqual(session.get(f'{base}/api/auth/me', timeout=10).status_code, 401)
            self.assertEqual(session.post(f'{base}/api/auth/login', json={'login': login, 'senha': password}, timeout=10).status_code, 200)
            new_login = f'{login}_new'
            response = session.post(f'{base}/api/auth/perfil', json={'nome': 'Nome atualizado', 'login': new_login.upper(), 'empresa': 'Empresa atualizada'}, timeout=10)
            self.assertEqual(response.status_code, 200, response.text)
            login = new_login
            self.assertEqual(response.json()['login'], login)
            self.assertEqual(session.get(f'{base}/api/auth/me', timeout=10).json()['nome'], 'Nome atualizado')
            other = requests.Session()
            other.headers.update(session.headers)
            try:
                self.assertEqual(other.post(f'{base}/api/auth/login', json={'login': login, 'senha': password}, timeout=10).status_code, 200)
                response = session.post(f'{base}/api/auth/senha', json={'senha_atual': 'wrong', 'nova_senha': 'nova senha segura 123'}, timeout=10)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(other.get(f'{base}/api/auth/me', timeout=10).status_code, 200)
                response = session.post(f'{base}/api/auth/senha', json={'senha_atual': password, 'nova_senha': 'nova senha segura 123'}, timeout=10)
                self.assertEqual(response.status_code, 204, response.text)
                self.assertEqual(other.get(f'{base}/api/auth/me', timeout=10).status_code, 401)
                self.assertEqual(session.get(f'{base}/api/auth/me', timeout=10).status_code, 200)
                self.assertEqual(other.post(f'{base}/api/auth/login', json={'login': login, 'senha': password}, timeout=10).status_code, 401)
                self.assertEqual(other.post(f'{base}/api/auth/login', json={'login': login, 'senha': 'nova senha segura 123'}, timeout=10).status_code, 200)
            finally:
                other.close()
            logout_cookie = session.cookies.get('tournament_session')
            self.assertEqual(session.post(f'{base}/api/auth/logout', timeout=10).status_code, 204)
            self.assertEqual(session.get(f'{base}/api/historico', timeout=10).status_code, 401)
            self.assertEqual(requests.get(f'{base}/api/auth/me', cookies={'tournament_session': logout_cookie}, timeout=10).status_code, 401)
        finally:
            session.close()
            connection = conectar()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('DELETE FROM usuarios WHERE login = %s', (login,))
                connection.commit()
            finally:
                connection.close()

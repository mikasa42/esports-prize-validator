"""Contratos HTTP da autenticação sem dependência de um banco real."""
import asyncio
import json
import unittest
from unittest.mock import patch

import pymysql
from src.main import app
from src.repositories.auth_repository import LoginEmUso
from src.repositories.match_repository import BancoIndisponivel
from src.services.auth_security import COOKIE_NAME, hash_senha, hash_token, verificar_senha

USER = {'id': 1, 'nome': 'Maria Clara', 'login': 'maria', 'empresa': 'PowerRev'}
PASSWORD = 'uma senha segura 123'


def http(method, path, data=None, cookie=None, headers=None):
    """Exercita roteamento, dependências, validação e serialização ASGI reais."""
    body = json.dumps(data).encode() if data is not None else b''
    request_headers = {'content-type': 'application/json', 'x-requested-with': 'TournamentHub', **(headers or {})}
    if cookie:
        request_headers['cookie'] = f'{COOKIE_NAME}={cookie}'
    messages = []
    async def run():
        received = False
        async def receive():
            nonlocal received
            if received:
                await asyncio.Event().wait()
            received = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
        async def send(message):
            messages.append(message)
        await app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                   'method': method, 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
                   'query_string': b'', 'root_path': '', 'server': ('testserver', 80),
                   'client': ('127.0.0.1', 1234),
                   'headers': [(key.encode(), value.encode()) for key, value in request_headers.items()]}, receive, send)
    asyncio.run(run())
    status = messages[0]['status']
    response_headers = {key.decode(): value.decode() for key, value in messages[0]['headers']}
    content = b''.join(message.get('body', b'') for message in messages[1:])
    return status, response_headers, json.loads(content) if content else None


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_senha(PASSWORD)

    def setUp(self):
        self.rate = patch('src.routers.auth.repository.registrar_tentativa', return_value=True)
        self.rate.start()
        self.addCleanup(self.rate.stop)

    def test_password_hash_has_unique_salt_and_checks_password(self):
        other = hash_senha(PASSWORD)
        self.assertNotEqual(other, self.password_hash)
        self.assertNotIn(PASSWORD, other)
        self.assertTrue(verificar_senha(PASSWORD, other))
        self.assertFalse(verificar_senha('senha incorreta', other))
        self.assertFalse(verificar_senha(PASSWORD, 'invalid'))

    @patch('src.routers.auth.repository.criar_sessao')
    @patch('src.routers.auth.repository.criar_usuario', return_value=USER)
    def test_registration_hashes_password_and_creates_session(self, create, session):
        status, headers, body = http('POST', '/api/auth/cadastro', {**USER, 'login': ' MARIA ', 'senha': PASSWORD})
        self.assertEqual(status, 201)
        self.assertEqual(body, USER)
        self.assertTrue(verificar_senha(PASSWORD, create.call_args.args[2]))
        self.assertEqual(create.call_args.args[1], 'maria')
        cookie = headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=lax', cookie)
        self.assertIn('Path=/api', cookie)
        token = cookie.split(';')[0].split('=', 1)[1]
        self.assertEqual(session.call_args.args[:2], (1, hash_token(token)))
        self.assertEqual(headers['cache-control'], 'no-store')

    @patch('src.routers.auth.repository.criar_usuario', side_effect=LoginEmUso)
    def test_duplicate_login(self, create):
        self.assertEqual(http('POST', '/api/auth/cadastro', {**USER, 'senha': PASSWORD})[0], 409)

    def test_invalid_registration_does_not_expose_password(self):
        for changes in ({'senha': 'abc123'}, {'nome': ' '}, {'empresa': ' '}, {'login': 'invalid name'}):
            data = {**USER, 'senha': PASSWORD, **changes}
            status, _, body = http('POST', '/api/auth/cadastro', data)
            self.assertEqual(status, 422)
            self.assertNotIn(data['senha'], json.dumps(body))

    @patch('src.routers.auth.repository.criar_sessao')
    @patch('src.routers.auth.repository.buscar_usuario')
    def test_login_rotates_cookie_and_never_returns_hash(self, find, session):
        find.return_value = {**USER, 'senha_hash': self.password_hash}
        status, _, body = http('POST', '/api/auth/login', {'login': 'MARIA', 'senha': PASSWORD}, cookie='old')
        self.assertEqual(status, 200)
        self.assertEqual(body, USER)
        find.assert_called_once_with('maria')
        self.assertEqual(session.call_args.args[2], hash_token('old'))

    @patch('src.routers.auth.repository.buscar_usuario')
    def test_wrong_password_and_unknown_login_have_same_error(self, find):
        find.return_value = {**USER, 'senha_hash': self.password_hash}
        invalid = http('POST', '/api/auth/login', {'login': 'maria', 'senha': 'incorrect'})
        find.return_value = None
        unknown = http('POST', '/api/auth/login', {'login': 'absent', 'senha': 'incorrect'})
        self.assertEqual(invalid[0], 401)
        self.assertEqual(invalid[2], unknown[2])
        self.assertNotIn('set-cookie', invalid[1])

    @patch('src.routers.auth.repository.buscar_sessao', return_value=USER)
    def test_me_returns_only_public_user(self, find):
        status, headers, body = http('GET', '/api/auth/me', cookie='secret')
        self.assertEqual(status, 200)
        self.assertEqual(body, USER)
        self.assertEqual(headers['cache-control'], 'no-store')
        find.assert_called_once_with(hash_token('secret'))

    @patch('src.routers.auth.repository.buscar_sessao', return_value=None)
    def test_missing_invalid_or_expired_session_is_rejected(self, find):
        for path in ('/api/auth/me', '/api/historico', '/api/ganhadores', '/api/partidas/MATCH-1001'):
            self.assertEqual(http('GET', path)[0], 401)
            self.assertEqual(http('GET', path, cookie='expired')[0], 401)
        self.assertEqual(http('POST', '/api/upload')[0], 401)

    @patch('src.routers.auth.repository.remover_sessao')
    def test_logout_revokes_server_session_and_cookie(self, remove):
        status, headers, _ = http('POST', '/api/auth/logout', cookie='secret')
        self.assertEqual(status, 204)
        remove.assert_called_once_with(hash_token('secret'))
        self.assertIn('Max-Age=0', headers['set-cookie'])
        self.assertEqual(http('POST', '/api/auth/logout')[0], 204)

    def test_rejects_missing_csrf_header_and_foreign_origin(self):
        for headers in ({'x-requested-with': ''}, {'origin': 'https://evil.example'}):
            self.assertEqual(http('POST', '/api/auth/login', {'login': 'maria', 'senha': PASSWORD}, headers=headers)[0], 403)
        self.assertEqual(http('POST', '/api/upload', headers={'x-requested-with': ''})[0], 403)

    @patch('src.routers.auth.repository.registrar_tentativa', return_value=False)
    def test_rate_limit(self, rate):
        status, headers, _ = http('POST', '/api/auth/login', {'login': 'maria', 'senha': PASSWORD})
        self.assertEqual(status, 429)
        self.assertEqual(headers['retry-after'], '900')

    @patch('src.routers.auth.repository.buscar_sessao', side_effect=BancoIndisponivel('internal secret'))
    def test_database_failure_returns_safe_503(self, find):
        status, _, body = http('GET', '/api/auth/me', cookie='secret')
        self.assertEqual(status, 503)
        self.assertNotIn('internal secret', json.dumps(body))


class AuthRepositoryTests(unittest.TestCase):
    @patch('src.repositories.auth_repository.conectar')
    def test_duplicate_registration_rolls_back(self, connect):
        from src.repositories.auth_repository import criar_usuario
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = pymysql.IntegrityError(1062, 'duplicate')
        with self.assertRaises(LoginEmUso):
            criar_usuario('Maria', 'maria', 'hash', 'Empresa')
        connect.return_value.rollback.assert_called_once()
        connect.return_value.close.assert_called_once()

    @patch('src.repositories.auth_repository.conectar')
    def test_session_lookup_checks_expiration_and_binds_token(self, connect):
        from src.repositories.auth_repository import buscar_sessao
        buscar_sessao('token-hash')
        query, params = connect.return_value.cursor.return_value.__enter__.return_value.execute.call_args.args
        self.assertIn('expira_em > UTC_TIMESTAMP()', query)
        self.assertEqual(params, ('token-hash',))
        connect.return_value.close.assert_called_once()


class AccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_senha(PASSWORD)

    def setUp(self):
        session = patch('src.routers.auth.repository.buscar_sessao', return_value=USER)
        rate = patch('src.routers.auth.repository.registrar_tentativa', return_value=True)
        session.start()
        rate.start()
        self.addCleanup(session.stop)
        self.addCleanup(rate.stop)

    @patch('src.routers.auth.repository.atualizar_usuario')
    def test_profile_updates_only_authenticated_user(self, update):
        update.return_value = {**USER, 'nome': 'Maria Souza'}
        status, headers, body = http('POST', '/api/auth/perfil', {**USER, 'id': 999, 'nome': ' Maria Souza ', 'login': ' MARIA '}, cookie='session')
        self.assertEqual(status, 200)
        update.assert_called_once_with(1, 'Maria Souza', 'maria', 'PowerRev')
        self.assertEqual(body['nome'], 'Maria Souza')
        self.assertEqual(headers['cache-control'], 'no-store')

    @patch('src.routers.auth.repository.atualizar_usuario', side_effect=LoginEmUso)
    def test_duplicate_login_is_rejected(self, update):
        self.assertEqual(http('POST', '/api/auth/perfil', USER, cookie='session')[0], 409)

    def test_missing_session_and_invalid_profile_are_rejected(self):
        self.assertEqual(http('POST', '/api/auth/perfil', USER)[0], 401)
        self.assertEqual(http('POST', '/api/auth/senha', {'senha_atual': PASSWORD, 'nova_senha': 'uma nova senha segura'})[0], 401)
        for changes in ({'nome': ' '}, {'empresa': ' '}, {'login': 'invalid name'}):
            self.assertEqual(http('POST', '/api/auth/perfil', {**USER, **changes}, cookie='session')[0], 422)

    @patch('src.routers.auth.repository.trocar_senha', return_value=True)
    @patch('src.routers.auth.repository.buscar_usuario')
    def test_password_change_requires_current_password_and_hashes_new_password(self, find, change):
        find.return_value = {**USER, 'senha_hash': self.password_hash}
        status, _, body = http('POST', '/api/auth/senha', {'senha_atual': PASSWORD, 'nova_senha': 'uma nova senha segura'}, cookie='session')
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        args = change.call_args.args
        self.assertEqual(args[0], USER['id'])
        self.assertEqual(args[1], self.password_hash)
        self.assertTrue(verificar_senha('uma nova senha segura', args[2]))
        self.assertEqual(args[3], hash_token('session'))

    @patch('src.routers.auth.repository.trocar_senha')
    @patch('src.routers.auth.repository.buscar_usuario')
    def test_incorrect_unchanged_and_weak_passwords_are_rejected(self, find, change):
        find.return_value = {**USER, 'senha_hash': self.password_hash}
        for fields, expected in (({'senha_atual': 'wrong', 'nova_senha': 'uma nova senha segura'}, 400),
                                 ({'senha_atual': PASSWORD, 'nova_senha': PASSWORD}, 400),
                                 ({'senha_atual': PASSWORD, 'nova_senha': 'abc123'}, 422)):
            status, _, body = http('POST', '/api/auth/senha', fields, cookie='session')
            self.assertEqual(status, expected)
            self.assertNotIn(fields['nova_senha'], json.dumps(body))
        change.assert_not_called()

    @patch('src.routers.auth.repository.trocar_senha', return_value=False)
    @patch('src.routers.auth.repository.buscar_usuario')
    def test_concurrent_password_change_returns_conflict(self, find, change):
        find.return_value = {**USER, 'senha_hash': self.password_hash}
        self.assertEqual(http('POST', '/api/auth/senha', {'senha_atual': PASSWORD, 'nova_senha': 'uma nova senha segura'}, cookie='session')[0], 409)

    @patch('src.repositories.auth_repository.conectar')
    def test_password_and_other_session_revocation_commit_together(self, connect):
        from src.repositories.auth_repository import trocar_senha
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.rowcount = 1
        self.assertTrue(trocar_senha(1, 'old-hash', 'new-hash', 'current-session-hash'))
        calls = cursor.execute.call_args_list
        self.assertEqual(calls[0].args[1], ('new-hash', 1, 'old-hash'))
        self.assertEqual(calls[1].args[1], (1, 'current-session-hash'))
        self.assertIn('token_hash <> %s', calls[1].args[0])
        connect.return_value.commit.assert_called_once()

    @patch('src.repositories.auth_repository.conectar')
    def test_revocation_failure_rolls_back_password(self, connect):
        from src.repositories.auth_repository import trocar_senha
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.rowcount = 1
        cursor.execute.side_effect = [None, pymysql.OperationalError('offline')]
        with self.assertRaises(BancoIndisponivel):
            trocar_senha(1, 'old', 'new', 'current')
        connect.return_value.commit.assert_not_called()
        connect.return_value.rollback.assert_called_once()

    @patch('src.repositories.auth_repository.conectar')
    def test_concurrent_change_does_not_revoke_sessions(self, connect):
        from src.repositories.auth_repository import trocar_senha
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.rowcount = 0
        self.assertFalse(trocar_senha(1, 'old', 'new', 'current'))
        self.assertEqual(cursor.execute.call_count, 1)

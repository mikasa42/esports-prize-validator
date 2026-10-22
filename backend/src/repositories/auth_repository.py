"""Contas, sessões e limite de tentativas persistidos no MySQL."""
from contextlib import contextmanager

import pymysql
from src.repositories.match_repository import BancoIndisponivel, conectar
from src.services.auth_security import SESSION_SECONDS


class LoginEmUso(Exception):
    pass


@contextmanager
def transacao():
    connection = conectar()
    try:
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except pymysql.MySQLError as err:
        connection.rollback()
        raise BancoIndisponivel('Serviço de autenticação indisponível. Tente novamente.') from err
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def criar_usuario(nome, login, senha_hash, empresa):
    with transacao() as cursor:
        try:
            cursor.execute('INSERT INTO usuarios (nome, login, senha_hash, empresa) VALUES (%s, %s, %s, %s)',
                           (nome, login, senha_hash, empresa))
        except pymysql.IntegrityError as err:
            if err.args[0] == 1062:
                raise LoginEmUso() from err
            raise
        return {'id': cursor.lastrowid, 'nome': nome, 'login': login, 'empresa': empresa}


def buscar_usuario(login):
    with transacao() as cursor:
        cursor.execute('SELECT id, nome, login, empresa, senha_hash FROM usuarios WHERE login = %s', (login,))
        return cursor.fetchone()


def criar_sessao(usuario_id, token_hash, token_anterior=None):
    with transacao() as cursor:
        cursor.execute('DELETE FROM sessoes_usuario WHERE expira_em <= UTC_TIMESTAMP()')
        if token_anterior:
            cursor.execute('DELETE FROM sessoes_usuario WHERE token_hash = %s', (token_anterior,))
        cursor.execute('''INSERT INTO sessoes_usuario (usuario_id, token_hash, expira_em)
            VALUES (%s, %s, DATE_ADD(UTC_TIMESTAMP(), INTERVAL %s SECOND))''',
                       (usuario_id, token_hash, SESSION_SECONDS))


def buscar_sessao(token_hash):
    with transacao() as cursor:
        cursor.execute('''SELECT u.id, u.nome, u.login, u.empresa FROM usuarios u
            JOIN sessoes_usuario s ON s.usuario_id = u.id
            WHERE s.token_hash = %s AND s.expira_em > UTC_TIMESTAMP()''', (token_hash,))
        return cursor.fetchone()


def remover_sessao(token_hash):
    with transacao() as cursor:
        cursor.execute('DELETE FROM sessoes_usuario WHERE token_hash = %s', (token_hash,))


def registrar_tentativa(chave):
    """O UPSERT bloqueia a linha, serializando tentativas concorrentes."""
    with transacao() as cursor:
        cursor.execute('DELETE FROM tentativas_autenticacao WHERE expira_em <= UTC_TIMESTAMP()')
        cursor.execute('''INSERT INTO tentativas_autenticacao (chave, tentativas, expira_em)
            VALUES (%s, 1, DATE_ADD(UTC_TIMESTAMP(), INTERVAL 15 MINUTE))
            ON DUPLICATE KEY UPDATE tentativas = tentativas + 1''', (chave,))
        cursor.execute('SELECT tentativas FROM tentativas_autenticacao WHERE chave = %s', (chave,))
        return cursor.fetchone()['tentativas'] <= 20


def atualizar_usuario(usuario_id, nome, login, empresa):
    with transacao() as cursor:
        try:
            cursor.execute('UPDATE usuarios SET nome = %s, login = %s, empresa = %s WHERE id = %s',
                           (nome, login, empresa, usuario_id))
        except pymysql.IntegrityError as err:
            if err.args[0] == 1062:
                raise LoginEmUso() from err
            raise
        return {'id': usuario_id, 'nome': nome, 'login': login, 'empresa': empresa}


def trocar_senha(usuario_id, senha_anterior_hash, nova_senha_hash, sessao_atual_hash):
    """Atualiza a senha e revoga outras sessões na mesma transação.

    A comparação com o hash anterior impede duas trocas concorrentes de senha.
    """
    with transacao() as cursor:
        cursor.execute('UPDATE usuarios SET senha_hash = %s WHERE id = %s AND senha_hash = %s',
                       (nova_senha_hash, usuario_id, senha_anterior_hash))
        if cursor.rowcount != 1:
            return False
        cursor.execute('DELETE FROM sessoes_usuario WHERE usuario_id = %s AND token_hash <> %s',
                       (usuario_id, sessao_atual_hash))
        return True

"""Consultas duráveis; Redis transporta apenas seus identificadores."""
import json
from contextlib import contextmanager
from uuid import uuid4

import pymysql
from src.repositories.match_repository import BancoIndisponivel, conectar

CAMPOS = 'id, nome_arquivo, criterio, status, total, processadas, erro, criada_em, atualizada_em'


@contextmanager
def banco():
    connection = conectar()
    try:
        yield connection
        connection.commit()
    except pymysql.MySQLError as err:
        connection.rollback()
        raise BancoIndisponivel('Não foi possível acessar as consultas.') from err
    finally:
        connection.close()


def criar(usuario_id, nome, conteudo, criterio, total):
    consulta_id = str(uuid4())
    with banco() as connection, connection.cursor() as cursor:
        cursor.execute('''INSERT INTO consultas
            (id, usuario_id, nome_arquivo, conteudo, criterio, total)
            VALUES (%s, %s, %s, %s, %s, %s)''',
            (consulta_id, usuario_id, nome[:255], conteudo, criterio, total))
    return consulta_id


def listar(usuario_id, limit=20, offset=0):
    with banco() as connection, connection.cursor() as cursor:
        cursor.execute(f'''SELECT {CAMPOS} FROM consultas WHERE usuario_id=%s
            ORDER BY criada_em DESC, id DESC LIMIT %s OFFSET %s''', (usuario_id, limit, offset))
        return cursor.fetchall()


def buscar(consulta_id, usuario_id):
    with banco() as connection, connection.cursor() as cursor:
        cursor.execute(f'SELECT {CAMPOS}, resultado FROM consultas WHERE id=%s AND usuario_id=%s',
                       (consulta_id, usuario_id))
        row = cursor.fetchone()
        if row:
            row['resultado'] = json.loads(row['resultado']) if row['resultado'] else None
        return row


def pendentes():
    with banco() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM consultas WHERE status IN ('pendente', 'processando') ORDER BY atualizada_em LIMIT 100")
        return [row['id'] for row in cursor.fetchall()]


@contextmanager
def executar(consulta_id):
    # Lock de sessão: liberado inclusive quando o processo do worker é morto.
    with banco() as connection, connection.cursor() as cursor:
        lock = f'consulta:{consulta_id}'
        cursor.execute('SELECT GET_LOCK(%s, 0) AS adquirido', (lock,))
        if not cursor.fetchone()['adquirido']:
            yield None
            return
        try:
            cursor.execute('SELECT * FROM consultas WHERE id=%s', (consulta_id,))
            row = cursor.fetchone()
            if not row or row['status'] in ('concluida', 'erro'):
                yield None
                return
            if row['tentativas'] >= 3:
                cursor.execute("UPDATE consultas SET status='erro', erro=%s WHERE id=%s",
                               ('O processamento foi interrompido após três tentativas.', consulta_id))
                yield None
                return
            cursor.execute("""UPDATE consultas SET status='processando', processadas=0,
                tentativas=tentativas+1, erro=NULL WHERE id=%s""", (consulta_id,))
            connection.commit()
            yield (connection, row)
        finally:
            cursor.execute('SELECT RELEASE_LOCK(%s)', (lock,))


def progresso(connection, consulta_id, quantidade):
    with connection.cursor() as cursor:
        cursor.execute('UPDATE consultas SET processadas=%s WHERE id=%s', (quantidade, consulta_id))
    connection.commit()


def finalizar(connection, consulta_id, resultado=None, erro=None):
    with connection.cursor() as cursor:
        cursor.execute('UPDATE consultas SET status=%s, resultado=%s, erro=%s WHERE id=%s',
                       ('erro' if erro else 'concluida', json.dumps(resultado, ensure_ascii=False) if resultado is not None else None,
                        erro, consulta_id))
    connection.commit()

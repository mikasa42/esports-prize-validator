"""Cria as tabelas uma vez durante a inicialização do backend."""
from pathlib import Path

import pymysql
from src.repositories.match_repository import BancoIndisponivel, conectar

SCHEMA_PATH = Path(__file__).with_name('schema.sql')


def inicializar_banco():
    schema = SCHEMA_PATH.read_text(encoding='utf-8')
    connection = conectar()
    try:
        with connection.cursor() as cursor:
            for statement in schema.split(';'):
                if statement.strip():
                    cursor.execute(statement)
        connection.commit()
    except pymysql.MySQLError as err:
        raise BancoIndisponivel('Não foi possível inicializar as tabelas do banco.') from err
    finally:
        connection.close()

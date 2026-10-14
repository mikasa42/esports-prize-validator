"""Persistência MySQL das respostas oficiais validadas."""
import json
import os

import pymysql


class BancoIndisponivel(Exception):
    pass


def conectar():
    try:
        connection = pymysql.connect(
            host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
            port=int(os.environ.get('MYSQL_PORT', '3306')),
            user=os.environ.get('MYSQL_USER', 'backend_user'),
            password=os.environ.get('MYSQL_PASSWORD', 'backend_password'),
            database=os.environ.get('MYSQL_DATABASE', 'esports_backend'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except pymysql.MySQLError as err:
        raise BancoIndisponivel('Banco de partidas indisponível.') from err


def buscar_partida(match_id_externo):
    connection = conectar()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT resposta FROM respostas_oficiais WHERE id_partida_externo = %s',
                           (match_id_externo,))
            row = cursor.fetchone()
            return json.loads(row['resposta']) if row else None
    except pymysql.MySQLError as err:
        raise BancoIndisponivel('Não foi possível ler a partida salva.') from err
    finally:
        connection.close()


def salvar_partida(partida_data):
    """Persiste a resposta completa e as estatísticas em uma única transação."""
    connection = conectar()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''INSERT INTO partidas (id_partida_externo, data_partida, rodada)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE data_partida = VALUES(data_partida), rodada = VALUES(rodada)''',
                (partida_data['match_id_externo'], partida_data['data_partida'][:10], partida_data['rodada']),
            )
            cursor.execute('SELECT id FROM partidas WHERE id_partida_externo = %s',
                           (partida_data['match_id_externo'],))
            partida_id = cursor.fetchone()['id']
            cursor.execute('DELETE FROM estatisticas_partida WHERE partida_id = %s', (partida_id,))
            for item in partida_data['participantes']:
                equipe_nome, nick = item['time_nick'].split(' / ', 1)
                cursor.execute(
                    'INSERT INTO equipes (nome) VALUES (%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)',
                    (equipe_nome,),
                )
                equipe_id = cursor.lastrowid
                cursor.execute('SELECT id FROM jogadores WHERE nick = %s AND equipe_id = %s',
                               (nick, equipe_id))
                jogador = cursor.fetchone()
                if jogador:
                    jogador_id = jogador['id']
                else:
                    cursor.execute('INSERT INTO jogadores (equipe_id, nick) VALUES (%s, %s)', (equipe_id, nick))
                    jogador_id = cursor.lastrowid
                cursor.execute(
                    '''INSERT INTO estatisticas_partida (partida_id, jogador_id, equipe_id, minutos, kills, venceu)
                       VALUES (%s, %s, %s, %s, %s, %s)''',
                    (partida_id, jogador_id, equipe_id, item['minutos'], item['kills'],
                     'Sim' if item['venceu'] else 'Não'),
                )
            cursor.execute(
                '''INSERT INTO respostas_oficiais (id_partida_externo, resposta) VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE resposta = VALUES(resposta)''',
                (partida_data['match_id_externo'], json.dumps(partida_data, ensure_ascii=False)),
            )
        connection.commit()
    except pymysql.MySQLError as err:
        connection.rollback()
        raise BancoIndisponivel('Não foi possível salvar a partida.') from err
    finally:
        connection.close()


def buscar_partidas_por_rodada(rodada_num):
    """Cruza os dados e retorna todas as partidas e desempenhos de uma rodada específica"""
    connection = conectar()
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT p.id_partida_externo, p.data_partida, p.rodada, 
                       e.nome AS equipe, j.nick, ep.minutos, ep.kills, ep.venceu
                FROM partidas p
                JOIN estatisticas_partida ep ON p.id = ep.partida_id
                JOIN jogadores j ON ep.jogador_id = j.id
                JOIN equipes e ON ep.equipe_id = e.id
                WHERE p.rodada = %s
                ORDER BY p.id_partida_externo, e.nome
            """
            cursor.execute(query, (rodada_num,))
            return cursor.fetchall()
    except pymysql.MySQLError as err:
        raise RuntimeError('Não foi possível buscar as partidas da rodada.') from err
    finally:
        connection.close()
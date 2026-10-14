"""API oficial simulada, com partidas carregadas de um arquivo JSON."""
import json
import logging
import os
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Query
from src.match_ids import normalizar_id_partida

DATA_PATH = Path(os.environ.get(
    'OFFICIAL_DATA_PATH', str(Path(__file__).with_name('Partidas_oficiais.json')),
))
app = FastAPI(title='Site Oficial — API simulada', version='1.0')


def carregar_partidas():
    """Relê o arquivo para refletir alterações sem reiniciar o simulador."""
    try:
        with DATA_PATH.open(encoding='utf-8-sig') as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, list):
            raise ValueError('O JSON deve conter uma lista de partidas.')
        partidas = {}
        for match in dados:
            match_id = normalizar_id_partida(match['matchId'])
            if match_id in partidas:
                raise ValueError('ID de partida duplicado no JSON.')
            participantes = []
            for team in (match['teamA'], match['teamB']):
                for player in team['players']:
                    participantes.append({
                        'time_nick': f"{team['name']} / {player['nickname']}",
                        'minutos': player.get('minutesPlayed'),
                        'kills': player['kills'],
                        'deaths': player['deaths'],
                        'assists': player['assists'],
                        'venceu': team['name'] == match['winnerTeam'],
                    })
            partidas[match_id] = {
                'match_id_externo': match_id,
                'data_partida': match.get('matchDate'),
                'rodada': match['round'],
                'confronto': f"{match['teamA']['name']} vs {match['teamB']['name']}",
                'tournamentId': match['tournamentId'],
                'participantes': participantes,
            }
        return partidas
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        logging.exception('Falha ao carregar o arquivo oficial de partidas')
        raise HTTPException(status_code=503, detail='Arquivo oficial indisponível ou inválido.')


@app.get('/health')
def health():
    carregar_partidas()
    return {'status': 'ok'}


@app.get('/api/partidas')
def listar_partidas(limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    partidas = carregar_partidas()
    rows = [{
        'id_partida': match['match_id_externo'],
        'data_partida': match['data_partida'],
        'rodada': match['rodada'],
        'partida': match['confronto'],
        'participantes': len(match['participantes']),
    } for _, match in sorted(partidas.items())]
    return {'partidas': rows[offset:offset + limit], 'limit': limit, 'offset': offset}


@app.get('/api/partidas/{match_id}')
def obter_partida(match_id: str):
    match_id = normalizar_id_partida(match_id)
    inicio = perf_counter()
    partida = carregar_partidas().get(match_id)
    if partida is None:
        raise HTTPException(status_code=404, detail='Partida não encontrada no arquivo oficial.')
    return {**partida, 'tempo_resposta_segundos': round(perf_counter() - inicio, 3)}

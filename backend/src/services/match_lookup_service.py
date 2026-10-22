"""Consulta partidas salvas e persiste respostas válidas da API oficial."""

import pandas as pd
from src.match_ids import normalizar_id_partida
from src.services.csv_comparison_service import ler_csv, comparar_csv
from src.simulator.official_api_client import OfficialApiClient, APIOficialIndisponivel, PartidaNaoEncontrada
from src.services.tournament_service import TournamentService
from src.repositories.match_repository import buscar_partida, salvar_partida


def ler_ids(content):
    _, rows = ler_csv(content)
    return [row['match_id_externo'] for row in rows]


def consultar_id(match_id):
    match_id = normalizar_id_partida(match_id)
    if not match_id or len(match_id) > 100:
        raise ValueError('ID de partida vazio ou maior que 100 caracteres.')
    saved = buscar_partida(match_id)
    if saved is not None:
        return {**saved, 'origem': 'banco'}
    try:
        official = OfficialApiClient.consultar_partida(match_id)
        # Valida os dados antes de devolver ao frontend.
        if not official['participantes']:
            raise ValueError('A API retornou uma partida sem jogadores.')
        for player in official['participantes']:
            team, nick = player['time_nick'].split(' / ', 1)
            if not team.strip() or not nick.strip():
                raise ValueError('Jogador inválido na resposta da API.')
            for key in ('minutos', 'kills'):
                value = player[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError('Estatísticas inválidas na resposta da API.')
            if not isinstance(player['venceu'], bool):
                raise ValueError('Resultado inválido na resposta da API.')
    except PartidaNaoEncontrada as err:
        return {'match_id_externo': match_id, 'erro': str(err), 'status': 'nao_encontrada'}
    except (APIOficialIndisponivel, KeyError, TypeError, ValueError) as err:
        return {'match_id_externo': match_id, 'erro': str(err), 'status': 'erro_api'}
    salvar_partida(official)
    return {**official, 'origem': 'api'}


def consultar_csv(content, criterio):
    # Agrupa após normalizar, preservando a ordem da primeira ocorrência de cada ID.
    columns, rows = ler_csv(content)
    ids = list(dict.fromkeys(row['match_id_externo'] for row in rows))
    # Resolve cada partida uma única vez, inclusive quando a consulta falha.
    results = [consultar_id(match_id) for match_id in ids]
    found = [r for r in results if 'erro' not in r]
    errors = [r for r in results if 'erro' in r]
    response = {'partidas': found, 'falhas': errors, 'total_solicitado': len(ids),
                'classificacao': [], 'premios': None,
                'comparacao_csv': comparar_csv(columns, rows, results)}
    if found and not errors:
        records = []
        for match in found:
            for player in match['participantes']:
                team, nick = player['time_nick'].split(' / ', 1)
                records.append({'ID Partida': match['match_id_externo'], 'time': team, 'jogador': nick,
                                'Minutos': player['minutos'], 'Kills': player['kills'],
                                'Venceu?': 'Sim' if player['venceu'] else 'Não'})
        data = pd.DataFrame(records)
        service = TournamentService()
        response['classificacao'] = service.calcular_vitorias_por_time(dados=data)
        response['premios'] = service.calcular_rateio_premios(criterio=criterio, dados=data)
    return response

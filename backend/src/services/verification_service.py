"""Compara o CSV persistido com os resultados retornados pelo site oficial."""
from src.match_ids import normalizar_id_partida
from src.simulator.official_api_client import (APIOficialIndisponivel, OfficialApiClient,
                                        PartidaNaoEncontrada)


def comparar_partida(df, official):
    differences = []
    first = df.iloc[0]
    for column, key in [('Data', 'data_partida'), ('Rodada', 'rodada'), ('Partida', 'confronto')]:
        imported = int(first[column]) if column == 'Rodada' else str(first[column])
        expected = official[key]
        if imported != expected:
            differences.append({'campo': key, 'csv': imported, 'oficial': expected})
    imported_players = {
        f"{row['time']} / {row['jogador']}": {
            'minutos': int(row['Minutos']), 'kills': int(row['Kills']), 'venceu': bool(row['venceu']),
        } for _, row in df.iterrows()
    }
    official_players = {row['time_nick']: row for row in official['participantes']}
    if len(official_players) != len(official['participantes']):
        raise APIOficialIndisponivel('Participantes duplicados na resposta oficial.')
    for player in sorted(imported_players.keys() | official_players.keys()):
        if player not in imported_players:
            differences.append({'jogador': player, 'campo': 'participante', 'csv': 'ausente', 'oficial': 'presente'})
        elif player not in official_players:
            differences.append({'jogador': player, 'campo': 'participante', 'csv': 'presente', 'oficial': 'ausente'})
        else:
            for field in ('minutos', 'kills', 'venceu'):
                if imported_players[player][field] != official_players[player][field]:
                    differences.append({'jogador': player, 'campo': field,
                                        'csv': imported_players[player][field], 'oficial': official_players[player][field]})
    return differences


def verificar_grupo(item):
    match_id, df = item
    match_id = normalizar_id_partida(match_id)
    base = {'match_id_externo': match_id}
    try:
        official = OfficialApiClient.consultar_partida(str(match_id))
        differences = comparar_partida(df, official)
        present = {f"{r['time']} / {r['jogador']}" for _, r in df.iterrows()}
        roster = [{**player, 'presente_no_csv': player['time_nick'] in present} for player in official['participantes']]
        return {
            **base, 'participantes_oficiais': roster,
            'jogadores_ausentes_csv': [player['time_nick'] for player in roster if not player['presente_no_csv']], 'status': 'divergente' if differences else 'verificado',
            'verificado': not differences, 'divergencias': differences,
            'tentativas_realizadas': official['tentativas_realizadas'],
            'tempo_resposta_segundos': official.get('tempo_resposta_segundos'),
            'mensagem': 'Dados divergem do banco oficial.' if differences else 'Dados conferidos com o banco oficial.',
        }
    except PartidaNaoEncontrada as err:
        return {**base, 'status': 'divergente', 'verificado': False, 'detalhe': str(err)}
    except (APIOficialIndisponivel, KeyError, TypeError, ValueError) as err:
        return {**base, 'status': 'erro_api', 'verificado': False, 'detalhe': str(err)}

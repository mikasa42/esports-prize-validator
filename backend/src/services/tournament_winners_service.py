"""Ganhadores por ano e torneio a partir das partidas já persistidas."""
from datetime import date

import pandas as pd

from src.repositories.match_repository import buscar_partidas_dos_torneios
from src.services.tournament_service import TournamentService


def consultar_ganhadores(ano=None, torneio=None, criterio='minutos'):
    groups = {}
    # O ID externo evita contar novamente uma partida em uploads repetidos.
    matches = {match['match_id_externo']: match for match in buscar_partidas_dos_torneios()}
    for match in matches.values():
        year = date.fromisoformat(match['data_partida'][:10]).year
        tournament = match.get('tournamentId') or 'sem-identificacao'
        groups.setdefault((year, tournament), []).append(match)
    years = sorted({year for year, _ in groups}, reverse=True)
    selected_year = ano if ano is not None else (years[0] if years else None)
    tournaments = sorted(tournament for year, tournament in groups if year == selected_year)
    selected_tournament = torneio if torneio is not None else (tournaments[0] if tournaments else None)
    selected = groups.get((selected_year, selected_tournament), [])
    response = {
        'anos': years, 'torneios': tournaments, 'ano': selected_year,
        'torneio': selected_tournament, 'total_partidas': len(selected),
        'ganhadores': [], 'classificacao': [], 'premios': None, 'jogadores': [],
        'criterio': criterio,
    }
    if not selected:
        return response
    records = []
    for match in selected:
        for player in match['participantes']:
            team, nickname = player['time_nick'].split(' / ', 1)
            records.append({'ID Partida': match['match_id_externo'], 'time': team, 'jogador': nickname,
                            'Minutos': player['minutos'], 'Kills': player['kills'],
                            'Venceu?': 'Sim' if player['venceu'] else 'Não'})
    if not records:
        return response
    data = pd.DataFrame(records)
    service = TournamentService()
    ranking = service.classificar_times(data)
    prizes = service.calcular_rateio_premios(data, criterio=criterio)
    team_prizes = {row['time']: row for row in prizes['premios_times']}
    response['classificacao'] = [{**row,
                                  'percentual': team_prizes.get(row['time'], {}).get('percentual', 0),
                                  'premio_rs': team_prizes.get(row['time'], {}).get('premio_rs', 0)}
                                 for row in ranking]
    response['ganhadores'] = [row for row in response['classificacao'] if row['posicao'] == 1 and row['vitorias'] > 0]
    prizes['premio_jogadores'].sort(key=lambda row: (-row['premio_rs'], row['time'], row['jogador']))
    awards = {(row['time'], row['jogador']): row['premio_rs'] for row in prizes['premio_jogadores']}
    for (team, nickname), stats in data.groupby(['time', 'jogador'], sort=True):
        response['jogadores'].append({
            'time': team, 'jogador': nickname,
            'minutos': int(stats['Minutos'].sum()), 'kills': int(stats['Kills'].sum()),
            'partidas': int(stats['ID Partida'].nunique()),
            'premio_rs': awards.get((team, nickname), 0),
        })
    response['jogadores'].sort(key=lambda row: (-row['premio_rs'], row['time'], row['jogador']))
    response['premios'] = prizes
    return response

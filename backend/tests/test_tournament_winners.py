import unittest
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException

from src.repositories.match_repository import BancoIndisponivel
from src.routers.partidas import ganhadores_torneios
from src.services.tournament_service import TournamentService
from src.services.tournament_winners_service import consultar_ganhadores


def match(identifier, year=2026, tournament='T1', winner='Beta'):
    return {'match_id_externo': identifier, 'data_partida': f'{year}-10-01T14:00:00Z',
            'tournamentId': tournament, 'rodada': 1, 'confronto': 'Alpha vs Beta',
            'participantes': [
                {'time_nick': 'Alpha / A', 'minutos': 30, 'kills': 5, 'venceu': winner == 'Alpha'},
                {'time_nick': 'Beta / B', 'minutos': 20, 'kills': 10, 'venceu': winner == 'Beta'},
            ]}


def dataset(scores):
    return pd.DataFrame([
        {'ID Partida': f'{team}-{index}', 'time': team, 'jogador': team,
         'Minutos': 20, 'Kills': kills, 'Venceu?': 'Sim'}
        for team, wins, kills in scores for index in range(wins)
    ])


class TournamentRankingTests(unittest.TestCase):
    def test_tiebreak_uses_all_kills_including_lost_matches(self):
        data = pd.DataFrame([
            {'ID Partida': '1', 'time': 'Alpha', 'jogador': 'A', 'Minutos': 10, 'Kills': 12, 'Venceu?': 'Sim'},
            {'ID Partida': '2', 'time': 'Alpha', 'jogador': 'A', 'Minutos': 10, 'Kills': 1, 'Venceu?': 'Não'},
            {'ID Partida': '1', 'time': 'Beta', 'jogador': 'B', 'Minutos': 10, 'Kills': 20, 'Venceu?': 'Não'},
            {'ID Partida': '2', 'time': 'Beta', 'jogador': 'B', 'Minutos': 10, 'Kills': 1, 'Venceu?': 'Sim'},
        ])
        service = TournamentService()
        ranking = service.classificar_times(data)
        self.assertEqual([(row['time'], row['vitorias'], row['kills']) for row in ranking],
                         [('Beta', 1, 21), ('Alpha', 1, 13)])
        self.assertEqual(service.calcular_vitorias_por_time(data)[0]['time'], 'Beta')
        self.assertEqual(service.calcular_rateio_premios(data)['premios_times'][0]['premio_rs'], 5000)

    def test_victories_take_priority_over_kills(self):
        ranking = TournamentService().classificar_times(dataset([('Alpha', 2, 1), ('Beta', 1, 100)]))
        self.assertEqual(ranking[0]['time'], 'Alpha')

    def test_equal_first_places_share_first_and_second_prizes(self):
        result = TournamentService().calcular_rateio_premios(
            dataset([('Alpha', 3, 10), ('Beta', 3, 10), ('Gamma', 2, 5)]))
        prizes = {row['time']: row for row in result['premios_times']}
        self.assertEqual([prizes[t]['posicao'] for t in ['Alpha', 'Beta', 'Gamma']], [1, 1, 3])
        self.assertEqual([prizes[t]['premio_rs'] for t in ['Alpha', 'Beta', 'Gamma']], [4000, 4000, 2000])

    def test_tie_at_third_place_shares_prize_with_fourth(self):
        result = TournamentService().calcular_rateio_premios(
            dataset([('Alpha', 4, 10), ('Beta', 3, 10), ('Gamma', 2, 5), ('Delta', 2, 5)]))
        prizes = {row['time']: row['premio_rs'] for row in result['premios_times']}
        self.assertEqual(prizes, {'Alpha': 5000, 'Beta': 3000, 'Delta': 1000, 'Gamma': 1000})
        self.assertEqual(sum(prizes.values()), 10000)

    def test_criterion_changes_player_prizes_without_changing_team_ranking(self):
        data = pd.DataFrame([
            {'ID Partida': '1', 'time': 'Alpha', 'jogador': 'A', 'Minutos': 30, 'Kills': 1, 'Venceu?': 'Sim'},
            {'ID Partida': '1', 'time': 'Alpha', 'jogador': 'B', 'Minutos': 10, 'Kills': 3, 'Venceu?': 'Sim'},
        ])
        service = TournamentService()
        minutes = service.calcular_rateio_premios(data)
        kills = service.calcular_rateio_premios(data, criterio='kills')
        self.assertEqual(minutes['premios_times'], kills['premios_times'])
        self.assertEqual(minutes['premio_jogadores'][0]['premio_rs'], 3750)
        self.assertEqual(kills['premio_jogadores'][0]['premio_rs'], 1250)


class TournamentWinnersTests(unittest.TestCase):
    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios')
    def test_defaults_to_latest_year_and_keeps_tournaments_separate(self, saved):
        saved.return_value = [match('old', 2025), match('a', 2026, 'T1'), match('b', 2026, 'T2', 'Alpha')]
        result = consultar_ganhadores()
        self.assertEqual(result['anos'], [2026, 2025])
        self.assertEqual(result['torneios'], ['T1', 'T2'])
        self.assertEqual(result['ano'], 2026)
        self.assertEqual(result['total_partidas'], 1)
        self.assertEqual(result['ganhadores'][0]['time'], 'Beta')
        self.assertEqual(consultar_ganhadores(2026, 'T2')['ganhadores'][0]['time'], 'Alpha')
        self.assertEqual(consultar_ganhadores(2025, 'T1')['ano'], 2025)

    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios')
    def test_deduplicates_matches_and_counts_every_team(self, saved):
        saved.return_value = [match('1'), match('1'), match('2', winner='Alpha')]
        result = consultar_ganhadores(2026, 'T1', 'kills')
        self.assertEqual(result['total_partidas'], 2)
        self.assertEqual(result['ganhadores'][0]['time'], 'Beta')
        self.assertEqual(result['ganhadores'][0]['vitorias'], 1)
        self.assertEqual(result['ganhadores'][0]['kills'], 20)
        self.assertEqual(len(result['classificacao']), 2)
        self.assertEqual(result['premios']['criterio_utilizado'], 'kills')

    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios')
    def test_returns_both_winners_when_victories_and_kills_tie(self, saved):
        first = match('1')
        second = match('2', winner='Alpha')
        for game in [first, second]:
            game['participantes'][0]['kills'] = 10
        saved.return_value = [first, second]
        result = consultar_ganhadores()
        self.assertEqual([row['time'] for row in result['ganhadores']], ['Alpha', 'Beta'])
        self.assertEqual([row['premio_rs'] for row in result['ganhadores']], [4000, 4000])

    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios', return_value=[])
    def test_empty_database_has_no_invented_year_or_winner(self, saved):
        result = consultar_ganhadores()
        self.assertEqual(result['anos'], [])
        self.assertIsNone(result['ano'])
        self.assertEqual(result['ganhadores'], [])
        self.assertIsNone(result['premios'])

    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios')
    def test_missing_year_does_not_fall_back_to_other_tournaments(self, saved):
        saved.return_value = [match('1')]
        result = consultar_ganhadores(2024)
        self.assertEqual(result['total_partidas'], 0)
        self.assertEqual(result['torneios'], [])
        self.assertEqual(result['ganhadores'], [])

    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios')
    @patch('src.simulator.official_api_client.OfficialApiClient.consultar_partida')
    def test_route_uses_saved_data_without_consulting_api(self, api, saved):
        saved.return_value = [match('1')]
        result = ganhadores_torneios(ano=2026, torneio='T1', criterio='minutos')
        self.assertEqual(result['total_partidas'], 1)
        api.assert_not_called()

    @patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios', side_effect=BancoIndisponivel('offline'))
    def test_database_error_returns_503(self, saved):
        with self.assertRaises(HTTPException) as error:
            ganhadores_torneios(ano=2026, torneio='T1', criterio='minutos')
        self.assertEqual(error.exception.status_code, 503)

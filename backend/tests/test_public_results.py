import os
import unittest
from unittest.mock import patch

from src.repositories.match_repository import BancoIndisponivel
from src.services.tournament_winners_service import consultar_ganhadores
from test_auth import http


def match(identifier='1', year=2026, tournament='T1'):
    return {'match_id_externo': identifier, 'data_partida': f'{year}-10-01', 'tournamentId': tournament,
            'participantes': [
                {'time_nick': 'Alpha / Ana', 'minutos': 30, 'kills': 1, 'venceu': True},
                {'time_nick': 'Alpha / Bia', 'minutos': 10, 'kills': 3, 'venceu': True},
                {'time_nick': 'Beta / Caio', 'minutos': 20, 'kills': 8, 'venceu': False},
            ]}


class PublicResultsTests(unittest.TestCase):
    def setUp(self):
        saved = patch('src.services.tournament_winners_service.buscar_partidas_dos_torneios')
        self.saved = saved.start()
        self.saved.return_value = [match()]
        self.addCleanup(saved.stop)
        config = patch.dict(os.environ, {'PUBLIC_PRIZE_CRITERION': 'minutos'})
        config.start()
        self.addCleanup(config.stop)

    @patch('src.routers.auth.repository.buscar_sessao')
    @patch('src.repositories.match_repository.salvar_partida')
    def test_public_get_needs_no_login_and_never_writes(self, save, session):
        status, _, body = http('GET', '/api/publico/resultados')
        self.assertEqual(status, 200)
        self.assertEqual(body['status'], 'parcial')
        self.assertEqual(body['criterio'], 'minutos')
        self.assertEqual(body['premio_base_rs'], 10000)
        self.assertEqual(len(body['jogadores']), 3)
        awards = {row['jogador']: row['premio_rs'] for row in body['jogadores']}
        self.assertEqual(awards, {'Ana': 3750, 'Bia': 1250, 'Caio': 0})
        session.assert_not_called()
        save.assert_not_called()

    def test_public_and_admin_awards_match_and_duplicate_matches_do_not_count(self):
        self.saved.return_value = [match(), match()]
        _, _, public = http('GET', '/api/publico/resultados')
        admin = consultar_ganhadores()
        self.assertEqual(public['total_partidas'], 1)
        self.assertEqual(public['jogadores'], admin['jogadores'])
        ana = next(row for row in public['jogadores'] if row['jogador'] == 'Ana')
        self.assertEqual((ana['minutos'], ana['kills'], ana['partidas']), (30, 1, 1))

    def test_filters_and_empty_selection(self):
        self.saved.return_value = [match(), match('old', 2025, 'T2')]
        status, _, body = http('GET', '/api/publico/resultados?ano=2025&torneio=T2')
        self.assertEqual(status, 200)
        self.assertEqual((body['ano'], body['torneio']), (2025, 'T2'))
        self.assertEqual(body['anos'], [2026, 2025])
        self.assertEqual(body['torneios'], ['T2'])
        status, _, body = http('GET', '/api/publico/resultados?ano=2024&torneio=missing')
        self.assertEqual(status, 200)
        self.assertEqual(body['jogadores'], [])
        self.assertEqual(body['total_partidas'], 0)
        self.assertEqual(body['classificacao'], [])

    def test_empty_database_does_not_fabricate_results(self):
        self.saved.return_value = []
        status, _, body = http('GET', '/api/publico/resultados')
        self.assertEqual(status, 200)
        self.assertIsNone(body['ano'])
        self.assertEqual(body['jogadores'], [])

    @patch.dict(os.environ, {'PUBLIC_PRIZE_CRITERION': 'kills'})
    def test_criterion_is_configured_on_server(self):
        _, _, body = http('GET', '/api/publico/resultados?criterio=minutos')
        self.assertEqual(body['criterio'], 'kills')
        self.assertEqual(next(row for row in body['jogadores'] if row['jogador'] == 'Ana')['premio_rs'], 1250)

    def test_invalid_filters_and_write_attempts(self):
        self.assertEqual(http('GET', '/api/publico/resultados?ano=1800')[0], 422)
        self.assertEqual(http('GET', '/api/publico/resultados?torneio=')[0], 422)
        self.assertEqual(http('POST', '/api/publico/resultados')[0], 405)
        self.assertEqual(http('GET', '/api/historico')[0], 401)

    def test_database_failure_is_handled_without_private_details(self):
        self.saved.side_effect = BancoIndisponivel('internal password')
        status, _, body = http('GET', '/api/publico/resultados')
        self.assertEqual(status, 503)
        self.assertNotIn('internal password', str(body))

    @patch('src.routers.publico.consultar_ganhadores')
    def test_public_response_only_contains_allowed_fields(self, winners):
        result = consultar_ganhadores()
        result['senha_hash'] = 'secret'
        result['classificacao'][0]['empresa'] = 'private'
        result['jogadores'][0]['login'] = 'private'
        winners.return_value = result
        _, _, body = http('GET', '/api/publico/resultados')
        self.assertNotIn('senha_hash', body)
        self.assertNotIn('empresa', body['classificacao'][0])
        self.assertNotIn('login', body['jogadores'][0])
        self.assertNotIn('premios', body)

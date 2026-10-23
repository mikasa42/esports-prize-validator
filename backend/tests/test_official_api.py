import copy
import datetime
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests
from fastapi import HTTPException

from src.simulator import official_api_server
from src.simulator.official_api_client import (APIOficialIndisponivel, OfficialApiClient,
                                        PartidaNaoEncontrada)
from src.services.verification_service import comparar_partida, verificar_grupo


OFFICIAL = {
    'match_id_externo': 'FN-1', 'data_partida': '2026-10-01', 'rodada': 1,
    'confronto': 'Alpha vs Beta', 'tentativas_realizadas': 1,
    'participantes': [
        {'time_nick': 'Alpha / A', 'minutos': 20, 'kills': 4, 'venceu': True},
        {'time_nick': 'Beta / B', 'minutos': 10, 'kills': 2, 'venceu': False},
    ],
}


def imported():
    return pd.DataFrame([
        {'Data': datetime.date(2026, 10, 1), 'Rodada': 1, 'Partida': 'Alpha vs Beta',
         'time': p['time_nick'].split(' / ')[0], 'jogador': p['time_nick'].split(' / ')[1],
         'Minutos': p['minutos'], 'Kills': p['kills'], 'venceu': p['venceu']}
        for p in OFFICIAL['participantes']
    ])


class ComparisonTests(unittest.TestCase):
    def test_equal_results(self):
        self.assertEqual(comparar_partida(imported(), OFFICIAL), [])

    def test_metadata_player_and_statistics_differences(self):
        data = imported()
        data.loc[0, 'Kills'] = 9
        data.loc[0, 'venceu'] = False
        data.loc[0, 'Minutos'] = 1
        data.loc[:, 'Rodada'] = 2
        differences = comparar_partida(data, OFFICIAL)
        self.assertEqual({d['campo'] for d in differences}, {'rodada', 'kills', 'venceu', 'minutos'})
        self.assertEqual(comparar_partida(data.iloc[:1], OFFICIAL)[-1]['campo'], 'participante')
        extra = copy.deepcopy(OFFICIAL)
        extra['participantes'] = extra['participantes'][:1]
        self.assertTrue(any(d['oficial'] == 'ausente' for d in comparar_partida(imported(), extra)))

    def test_missing_and_unavailable_are_distinct(self):
        for exception, status in ((PartidaNaoEncontrada('ausente'), 'divergente'),
                                  (APIOficialIndisponivel('offline'), 'erro_api')):
            with self.subTest(status=status), patch.object(OfficialApiClient, 'consultar_partida', side_effect=exception):
                result = verificar_grupo(('FN-1', imported()))
                self.assertFalse(result['verificado'])
                self.assertEqual(result['status'], status)

    @patch.object(OfficialApiClient, 'consultar_partida', return_value=OFFICIAL)
    def test_incomplete_csv_returns_full_official_roster(self, consult):
        result = verificar_grupo((' fn–1 ', imported().iloc[:1]))
        consult.assert_called_once_with('FN-1')
        self.assertEqual(result['status'], 'divergente')
        self.assertEqual(len(result['participantes_oficiais']), 2)
        self.assertEqual(result['jogadores_ausentes_csv'], ['Beta / B'])
        self.assertFalse(result['participantes_oficiais'][1]['presente_no_csv'])


class ClientTests(unittest.TestCase):
    @patch('src.simulator.official_api_client.requests.get')
    @patch.dict('os.environ', {'OFFICIAL_API_URL': 'http://official.test'})
    def test_success_uses_one_request_with_timeout(self, get):
        response = Mock(status_code=200)
        response.json.return_value = copy.deepcopy(OFFICIAL)
        get.return_value = response
        self.assertEqual(OfficialApiClient.consultar_partida('FN-1')['tentativas_realizadas'], 1)
        get.assert_called_once_with('http://official.test/api/partidas/FN-1', timeout=(5, 30))

    @patch('src.simulator.official_api_client.requests.get')
    def test_missing_match_is_not_retried(self, get):
        get.return_value.status_code = 404
        with self.assertRaises(PartidaNaoEncontrada):
            OfficialApiClient.consultar_partida('FN-1')
        get.assert_called_once()

    @patch('src.simulator.official_api_client.requests.get')
    def test_request_errors_are_not_retried(self, get):
        for error in (requests.Timeout(), requests.ConnectionError(), requests.HTTPError(),
                      requests.exceptions.JSONDecodeError('invalid', '{', 1)):
            with self.subTest(error=type(error).__name__):
                get.reset_mock()
                get.side_effect = error
                with self.assertRaises(APIOficialIndisponivel):
                    OfficialApiClient.consultar_partida('FN-1')
                get.assert_called_once()

    @patch('src.simulator.official_api_client.requests.get')
    def test_normalizes_id_for_http_request_and_response(self, get):
        response = Mock(status_code=200)
        response.json.return_value = copy.deepcopy(OFFICIAL)
        get.return_value = response
        self.assertEqual(OfficialApiClient.consultar_partida(' fn–1 ')['match_id_externo'], 'FN-1')
        self.assertTrue(get.call_args.args[0].endswith('/api/partidas/FN-1'))


class OfficialJsonTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'partidas.json'
        self.data = [{
            'matchId': 'match-1001', 'round': 1, 'tournamentId': 'tournament-55',
            'matchDate': '2026-10-01T14:00:00Z',
            'teamA': {'name': 'Alpha', 'players': [
                {'nickname': 'A', 'kills': 4, 'deaths': 2, 'assists': 3, 'minutesPlayed': 20}]},
            'teamB': {'name': 'Beta', 'players': [
                {'nickname': 'B', 'kills': 2, 'deaths': 4, 'assists': 1, 'minutesPlayed': 10}]},
            'winnerTeam': 'Alpha',
        }]
        self.write_data()
        self.data_patch = patch.object(official_api_server, 'DATA_PATH', self.path)
        self.data_patch.start()
        self.addCleanup(self.data_patch.stop)

    def write_data(self):
        self.path.write_text(json.dumps(self.data), encoding='utf-8')

    def test_reads_json_and_normalizes_match_id(self):
        result = official_api_server.obter_partida(' match–1001 ')
        self.assertEqual(result['match_id_externo'], 'MATCH-1001')
        self.assertEqual(result['confronto'], 'Alpha vs Beta')
        self.assertEqual(result['rodada'], 1)
        self.assertEqual(result['tournamentId'], 'tournament-55')
        self.assertEqual(result['data_partida'], '2026-10-01T14:00:00Z')
        self.assertEqual(result['participantes'], [
            {'time_nick': 'Alpha / A', 'minutos': 20, 'kills': 4,
             'deaths': 2, 'assists': 3, 'venceu': True},
            {'time_nick': 'Beta / B', 'minutos': 10, 'kills': 2,
             'deaths': 4, 'assists': 1, 'venceu': False},
        ])
        with self.assertRaises(HTTPException) as err:
            official_api_server.obter_partida('MATCH-9999')
        self.assertEqual(err.exception.status_code, 404)

    def test_listing_pagination_and_file_reload(self):
        self.assertEqual(official_api_server.health(), {'status': 'ok'})
        self.assertEqual(official_api_server.listar_partidas(1, 0)['partidas'][0]['participantes'], 2)
        self.assertEqual(official_api_server.listar_partidas(1, 1)['partidas'], [])
        self.data.append({**self.data[0], 'matchId': 'match-1002'})
        self.write_data()
        self.assertEqual(official_api_server.listar_partidas(1, 1)['partidas'][0]['id_partida'], 'MATCH-1002')

    def test_invalid_missing_and_duplicate_json_return_503(self):
        for content in ('{invalid', '{}', '[{}]', json.dumps(self.data * 2)):
            with self.subTest(content=content):
                self.path.write_text(content, encoding='utf-8')
                with self.assertRaises(HTTPException) as err:
                    official_api_server.health()
                self.assertEqual(err.exception.status_code, 503)
        self.path.unlink()
        with self.assertRaises(HTTPException) as err:
            official_api_server.health()
        self.assertEqual(err.exception.status_code, 503)

    @patch('src.simulator.official_api_server.perf_counter', side_effect=[10.0, 10.125])
    def test_reports_actual_processing_time(self, clock):
        result = official_api_server.obter_partida('MATCH-1001')
        self.assertEqual(result['tempo_resposta_segundos'], 0.125)

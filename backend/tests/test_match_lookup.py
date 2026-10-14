import copy
import os
import io
import threading
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi import UploadFile, HTTPException
from src.main import app
from src.routers.partidas import MAX_CSV_BYTES, consultar_partidas_csv
from src.services.match_lookup_service import consultar_csv, ler_ids
from src.simulator.official_api_client import OfficialApiClient, APIOficialIndisponivel, PartidaNaoEncontrada

OFFICIAL = {'match_id_externo': 'MATCH-202', 'data_partida': '2026-09-02', 'rodada': 2,
            'confronto': 'Beta vs Alpha', 'tentativas_realizadas': 1,
            'participantes': [{'time_nick': 'Beta / B', 'minutos': 20, 'kills': 4, 'venceu': True}]}


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.saved = {}
        if os.environ.get('MYSQL_TEST_DATABASE'):
            env = patch.dict(os.environ, {'MYSQL_DATABASE': os.environ['MYSQL_TEST_DATABASE']})
            env.start()
            self.addCleanup(env.stop)
            from src.repositories.match_repository import conectar
            from src.database.initialization import inicializar_banco
            inicializar_banco()
            connection = conectar()
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM partidas')
            connection.commit()
            connection.close()
        else:
            lookup = patch('src.services.match_lookup_service.buscar_partida',
                           side_effect=lambda match_id: copy.deepcopy(self.saved.get(match_id)))
            save = patch('src.services.match_lookup_service.salvar_partida',
                         side_effect=lambda match: self.saved.setdefault(match['match_id_externo'], copy.deepcopy(match)))
            lookup.start()
            save.start()
            self.addCleanup(lookup.stop)
            self.addCleanup(save.stop)

    def test_ids_normalized_without_removing_repeated_rows(self):
        self.assertEqual(ler_ids(b'id_partida\n match-101 \nMATCH-101\nMATCH-202\n'), ['MATCH-101', 'MATCH-101', 'MATCH-202'])
        for content in (b'id_partida\n""\n', b'foo\nbar\n', b'ID Partida\n'):
            with self.assertRaises(ValueError):
                ler_ids(content)

    @patch.object(OfficialApiClient, 'consultar_partida', return_value=OFFICIAL)
    def test_repeated_upload_uses_persistent_database(self, api):
        result = consultar_csv(b'id_partida\nMATCH-202\nMATCH-202\n', 'kills')
        self.assertEqual(api.call_count, 1)
        self.assertTrue(all(call.args == ('MATCH-202',) for call in api.call_args_list))
        self.assertEqual(result['total_solicitado'], 2)
        self.assertEqual(result['partidas'][0]['origem'], 'api')
        self.assertEqual(result['falhas'], [])
        self.assertEqual(result['premios']['criterio_utilizado'], 'kills')
        self.assertEqual(result['premios']['premio_jogadores'][0]['total_kills'], 4)
        api.side_effect = APIOficialIndisponivel('Offline')
        again = consultar_csv(b'ID Partida\nMATCH-202\n', 'minutos')
        self.assertEqual(result['partidas'][1]['origem'], 'banco')
        api.side_effect = APIOficialIndisponivel('Offline')
        self.assertEqual(again['partidas'][0]['origem'], 'banco')
        self.assertEqual(api.call_count, 1)

    @patch.object(OfficialApiClient, 'consultar_partida', return_value=OFFICIAL)
    def test_saved_match_is_available_in_new_process_without_api(self, api):
        if not os.environ.get('MYSQL_TEST_DATABASE'):
            self.skipTest('Configure MYSQL_TEST_DATABASE para testar com MySQL real.')
        from src.routers.partidas import consultar_partida
        self.assertEqual(consultar_partida('match-202')['origem'], 'api')
        script = """
from unittest.mock import patch
from src.routers.partidas import consultar_partida
from src.simulator.official_api_client import OfficialApiClient
with patch.object(OfficialApiClient, 'consultar_partida', side_effect=AssertionError('API chamada')):
    result = consultar_partida('match-202')
    assert result['origem'] == 'banco'
    assert result['participantes'][0]['kills'] == 4
"""
        subprocess.run([sys.executable, '-c', script], check=True)
        api.assert_called_once_with('MATCH-202')

    @patch.object(OfficialApiClient, 'consultar_partida')
    def test_mixed_ids_returns_only_requested_matches_and_ignores_csv_statistics(self, api):
        def lookup(match_id):
            result = copy.deepcopy(OFFICIAL)
            result['match_id_externo'] = match_id
            return result
        api.side_effect = lookup
        result = consultar_csv(b'id_partida,Kills\nMATCH-101,999\nMATCH-202,999\n', 'kills')
        self.assertEqual([r['match_id_externo'] for r in result['partidas']], ['MATCH-101', 'MATCH-202'])
        self.assertEqual(api.call_count, 2)
        self.assertEqual(result['premios']['premio_jogadores'][0]['total_kills'], 8)
        self.assertEqual(result['classificacao'], [{'time': 'Beta', 'vitorias': 2}])

    @patch.object(OfficialApiClient, 'consultar_partida')
    def test_partial_errors_keep_available_matches(self, api):
        def lookup(match_id):
            if match_id == 'MATCH-404':
                raise APIOficialIndisponivel('Offline')
            if match_id == 'MATCH-405':
                raise PartidaNaoEncontrada('Ausente')
            return copy.deepcopy(OFFICIAL)
        api.side_effect = lookup
        result = consultar_csv(b'id_partida\nMATCH-202\nMATCH-404\nMATCH-405\n', 'minutos')
        self.assertEqual(len(result['partidas']), 1)
        self.assertEqual([f['status'] for f in result['falhas']], ['erro_api', 'nao_encontrada'])
        self.assertIsNone(result['premios'])

    @patch.object(OfficialApiClient, 'consultar_partida')
    def test_invalid_api_payload_is_reported_per_match(self, api):
        for players in ([], [{'time_nick': 'invalid'}],
                        [{'time_nick': 'Team / Nick', 'minutos': -1, 'kills': 1, 'venceu': True}]):
            with self.subTest(players=players):
                api.return_value = {**OFFICIAL, 'participantes': players}
                result = consultar_csv(b'id_partida\nMATCH-202\n', 'minutos')
                self.assertEqual(result['partidas'], [])
                self.assertEqual(result['falhas'][0]['status'], 'erro_api')

    @patch.object(OfficialApiClient, 'consultar_partida', return_value=OFFICIAL)
    def test_upload_returns_api_data_and_closes_file(self, api):
        file = io.BytesIO(b'id_partida\nMATCH-202\n')
        result = consultar_partidas_csv(UploadFile(file=file, filename='matches.csv'), 'minutos')
        self.assertTrue(file.closed)
        self.assertEqual(result['partidas'][0]['participantes'], OFFICIAL['participantes'])

    @patch.object(OfficialApiClient, 'consultar_partida')
    def test_upload_validation_without_api_calls(self, api):
        cases = [(b'', 'x.csv', 400), (b'id_partida\nMATCH-1', 'x.txt', 400),
                 (b'\xff', 'x.csv', 400), (b'x' * (MAX_CSV_BYTES + 1), 'x.csv', 413)]
        for content, filename, status in cases:
            with self.assertRaises(HTTPException) as err:
                consultar_partidas_csv(UploadFile(file=io.BytesIO(content), filename=filename), 'minutos')
            self.assertEqual(err.exception.status_code, status)
        api.assert_not_called()

    @patch.object(OfficialApiClient, 'consultar_partida')
    def test_requests_run_sequentially_in_csv_row_order(self, api):
        caller = threading.get_ident()
        completed = []
        def lookup(match_id):
            self.assertEqual(threading.get_ident(), caller)
            completed.append(match_id)
            return {**copy.deepcopy(OFFICIAL), 'match_id_externo': match_id}
        api.side_effect = lookup
        result = consultar_csv(b'id_partida\nID-1\nID-1\nID-2\n', 'minutos')
        self.assertEqual(completed, ['ID-1', 'ID-2'])
        self.assertEqual(result['falhas'], [])
        self.assertEqual(result['total_solicitado'], 3)
        self.assertEqual(len(result['partidas']), 3)
        self.assertEqual(result['premios']['premio_jogadores'][0]['total_minutos'], 40)

    def test_lookup_routes_are_available(self):
        paths = {route.path for route in app.routes}
        self.assertIn('/api/partidas/{match_id}', paths)
        self.assertNotIn('/api/importar-csv', paths)
        self.assertNotIn('/api/verificar-partidas', paths)

    def test_database_failure_returns_503(self):
        from src.routers.partidas import consultar_partida
        from src.repositories.match_repository import BancoIndisponivel
        with patch('src.services.match_lookup_service.buscar_partida', side_effect=BancoIndisponivel('Offline')):
            with self.assertRaises(HTTPException) as error:
                consultar_partida('MATCH-202')
            self.assertEqual(error.exception.status_code, 503)
            with self.assertRaises(HTTPException) as error:
                consultar_partidas_csv(UploadFile(file=io.BytesIO(b'id_partida\nMATCH-202\n'), filename='x.csv'), 'minutos')
            self.assertEqual(error.exception.status_code, 503)

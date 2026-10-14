import json
import unittest
from unittest.mock import patch

import pymysql
from fastapi import HTTPException

from src.repositories.match_repository import BancoIndisponivel, listar_partidas_salvas
from src.routers.partidas import consultar_historico


class HistoryTests(unittest.TestCase):
    @patch('src.repositories.match_repository.conectar')
    def test_reads_saved_responses_with_server_pagination(self, connect):
        connection = connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {'total': 12}
        cursor.fetchall.return_value = [{'resposta': json.dumps({'match_id_externo': 'MATCH-1001', 'participantes': []})}]
        result = listar_partidas_salvas(limit=5, offset=10)
        self.assertEqual(result['total'], 12)
        self.assertEqual(result['offset'], 10)
        self.assertEqual(result['partidas'][0]['origem'], 'banco')
        query, params = cursor.execute.call_args.args
        self.assertIn('ORDER BY p.id DESC', query)
        self.assertIn('LIMIT %s OFFSET %s', query)
        self.assertEqual(params, (5, 10))
        connection.close.assert_called_once()

    @patch('src.repositories.match_repository.conectar')
    def test_search_values_are_bound_as_parameters(self, connect):
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {'total': 0}
        cursor.fetchall.return_value = []
        term = "Alpha' OR 1=1 --"
        result = listar_partidas_salvas(limit=10, offset=0, busca=term)
        self.assertEqual(result['partidas'], [])
        for call in cursor.execute.call_args_list:
            query, params = call.args
            self.assertNotIn(term, query)
            self.assertEqual(params[:2], (f'%{term}%', f'%{term}%'))

    @patch('src.repositories.match_repository.conectar')
    def test_database_error_closes_connection(self, connect):
        cursor = connect.return_value.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = pymysql.OperationalError('offline')
        with self.assertRaises(BancoIndisponivel):
            listar_partidas_salvas()
        connect.return_value.close.assert_called_once()

    @patch('src.routers.partidas.listar_partidas_salvas')
    @patch('src.simulator.official_api_client.OfficialApiClient.consultar_partida')
    def test_history_route_does_not_consult_api(self, api, saved):
        saved.return_value = {'partidas': [], 'total': 0, 'limit': 5, 'offset': 0}
        result = consultar_historico(limit=5, offset=0, busca=' Alpha ')
        saved.assert_called_once_with(limit=5, offset=0, busca='Alpha')
        api.assert_not_called()
        self.assertEqual(result['total'], 0)

    @patch('src.routers.partidas.listar_partidas_salvas', side_effect=BancoIndisponivel('offline'))
    def test_history_route_reports_database_unavailability(self, saved):
        with self.assertRaises(HTTPException) as error:
            consultar_historico(limit=5, offset=0, busca='')
        self.assertEqual(error.exception.status_code, 503)

import copy
import unittest
from unittest.mock import patch

from src.services.csv_comparison_service import ler_csv, comparar_csv
from src.services.match_lookup_service import consultar_csv

OFFICIAL = {'match_id_externo': 'MATCH-1001', 'data_partida': '2026-10-01T14:00:00Z',
            'rodada': 1, 'confronto': 'Alpha vs Beta', 'tournamentId': 'T1', 'origem': 'banco',
            'participantes': [
                {'time_nick': 'Alpha / Ana', 'minutos': 30, 'kills': 12, 'deaths': 2, 'assists': 5, 'venceu': True},
                {'time_nick': 'Beta / Bia', 'minutos': 20, 'kills': 7, 'deaths': 5, 'assists': 1, 'venceu': False},
            ]}


def compare(text, official=OFFICIAL):
    columns, rows = ler_csv(text.encode('utf-8'))
    return comparar_csv(columns, rows, [official])


def cells(result, row=0):
    return {cell['coluna']: cell for cell in result['linhas'][row]['campos']}


class CsvComparisonTests(unittest.TestCase):
    def test_every_supplied_field_is_compared_and_unknowns_are_preserved(self):
        result = compare('id_partida,time,jogador,Minutos,Kills,Rodada,Data,Partida,torneio,Deaths,Assists,Venceu?,winnerTeam,Nota\nmatch-1001,Alpha,Ana,30,12,1,01/10/2026,Alpha vs Beta,T1,2,5,Sim,Alpha,Minha nota\n')
        values = cells(result)
        self.assertTrue(all(cell['status'] == 'conferente' for name, cell in values.items() if name != 'Nota'))
        self.assertEqual(values['Nota']['status'], 'nao_comparavel')
        self.assertEqual(values['Nota']['csv'], 'Minha nota')
        self.assertEqual(result['linhas'][0]['origem'], 'banco')
        self.assertEqual(result['linhas'][0]['status'], 'parcial')

    def test_different_kills_minutes_and_round_are_exposed_per_row(self):
        result = compare('id_partida,time,jogador,Kills,Minutos,Rodada\nMATCH-1001,Alpha,Ana,99,7,3\nMATCH-1001,Beta,Bia,7,20,1\n')
        values = cells(result)
        self.assertEqual([(values[key]['csv'], values[key]['oficial'], values[key]['status']) for key in ['Kills', 'Minutos', 'Rodada']], [('99', 12, 'divergente'), ('7', 30, 'divergente'), ('3', 1, 'divergente')])
        self.assertEqual(result['resumo']['linhas_divergentes'], 1)
        self.assertEqual(result['linhas'][1]['status'], 'conferente')

    def test_inconsistent_metadata_is_checked_on_every_row(self):
        result = compare('id_partida,Rodada\nMATCH-1001,1\nMATCH-1001,2\n')
        self.assertEqual(cells(result, 0)['Rodada']['status'], 'conferente')
        self.assertEqual(cells(result, 1)['Rodada']['status'], 'divergente')

    def test_invalid_numeric_boolean_and_missing_values(self):
        result = compare('id_partida,time,jogador,Kills,Minutos,Venceu?,Deaths,Data\nMATCH-1001,Alpha,Ana,NaN,-1,talvez,,31/02/2026\n')
        values = cells(result)
        for field in ['Kills', 'Minutos', 'Venceu?', 'Data']:
            self.assertEqual(values[field]['status'], 'invalido_csv')
        self.assertEqual(values['Deaths']['status'], 'ausente_csv')
        self.assertEqual(values['Deaths']['oficial'], 2)
        self.assertEqual(result['resumo']['linhas_divergentes'], 1)

    def test_time_and_case_normalization_and_separate_time_comparison(self):
        result = compare('id_partida,time,jogador,Minutos,Kills,Data,Venceu?\nMATCH-1001, alpha , ana ,30.0,12,2026-10-01T11:00:00-03:00,true\n')
        self.assertTrue(all(cell['status'] == 'conferente' for cell in result['linhas'][0]['campos']))
        different = compare('id_partida,Data\nMATCH-1001,2026-10-01T15:00:00Z\n')
        self.assertEqual(cells(different)['Data']['status'], 'divergente')

    def test_missing_identity_never_compares_statistics_with_arbitrary_player(self):
        result = compare('id_partida,Kills,Minutos\nMATCH-1001,12,30\n')
        self.assertEqual(cells(result)['Kills']['status'], 'nao_comparavel')
        self.assertEqual(result['linhas'][0]['status'], 'parcial')

    def test_invalid_statistic_is_reported_even_without_player_identity(self):
        result = compare('id_partida,Kills\nMATCH-1001,abc\n')
        self.assertEqual(cells(result)['Kills']['status'], 'invalido_csv')

    def test_ambiguous_nickname_is_not_guessed_and_unknown_player_is_flagged(self):
        official = copy.deepcopy(OFFICIAL)
        official['participantes'][1]['time_nick'] = 'Beta / Ana'
        result = compare('id_partida,jogador,Kills\nMATCH-1001,Ana,12\n', official)
        self.assertEqual(cells(result)['Kills']['status'], 'nao_comparavel')
        result = compare('id_partida,time,jogador,Kills\nMATCH-1001,Alpha,Desconhecido,12\n')
        self.assertEqual(cells(result)['jogador']['status'], 'divergente')
        self.assertEqual(cells(result)['Kills']['status'], 'nao_comparavel')

    def test_unavailable_api_preserves_csv_without_false_comparison(self):
        result = compare('id_partida,Kills,Nota\nMATCH-1001,99,Detalhe\n', {'match_id_externo': 'MATCH-1001', 'erro': 'API indisponível'})
        self.assertEqual(cells(result)['Kills']['csv'], '99')
        self.assertEqual(cells(result)['Kills']['status'], 'sem_referencia')
        self.assertEqual(cells(result)['Nota']['status'], 'nao_comparavel')
        self.assertEqual(result['linhas'][0]['status'], 'sem_referencia')

    def test_missing_optional_official_field_is_not_invented(self):
        official = copy.deepcopy(OFFICIAL)
        del official['participantes'][0]['deaths']
        result = compare('id_partida,time,jogador,Deaths\nMATCH-1001,Alpha,Ana,2\n', official)
        self.assertEqual(cells(result)['Deaths']['status'], 'nao_comparavel')
        self.assertIsNone(cells(result)['Deaths']['oficial'])

    def test_duplicate_rows_keep_csv_line_numbers_and_each_value(self):
        result = compare('id_partida,Kills\n\nMATCH-1001,12\nMATCH-1001,12\nMATCH-1001,20\n')
        self.assertEqual([row['linha'] for row in result['linhas']], [3, 4, 5])
        self.assertEqual(result['linhas'][1]['duplicada_de'], 3)
        self.assertIsNone(result['linhas'][2]['duplicada_de'])
        self.assertEqual(result['resumo']['linhas_duplicadas'], 1)

    def test_parser_preserves_quoted_delimiters_na_nicknames_and_bom(self):
        content = '\ufeffid_partida;time;jogador;Nota;Minutos\nMATCH-1001;Alpha;NA;"texto;com separador";"30,0"\n'
        columns, rows = ler_csv(content.encode())
        self.assertEqual(rows[0]['valores']['jogador'], 'NA')
        self.assertEqual(rows[0]['valores']['Nota'], 'texto;com separador')
        self.assertEqual(rows[0]['valores']['Minutos'], '30,0')
        self.assertEqual(columns[0], 'id_partida')

    def test_bad_headers_and_malformed_records_are_rejected(self):
        for text in ['id_partida,Kills,Kills\nMATCH-1001,1,2', 'id_partida,ID Partida\nMATCH-1001,MATCH-1002', 'id_partida,Kills\nMATCH-1001,1,extra', 'id_partida,Kills\nMATCH-1001', 'id_partida,Kills\n,1', 'id_partida,\nMATCH-1001,2', 'id_partida,Nota\nMATCH-1001,"aberto']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                ler_csv(text.encode())

    def test_id_only_csv_has_explicit_scope(self):
        self.assertTrue(compare('id_partida\nMATCH-1001\n')['somente_ids'])

    @patch('src.services.match_lookup_service.buscar_partida', return_value=OFFICIAL)
    @patch('src.services.match_lookup_service.salvar_partida')
    @patch('src.services.match_lookup_service.OfficialApiClient.consultar_partida')
    def test_comparison_does_not_change_prizes_or_fetch_duplicate_ids(self, api, save, database):
        result = consultar_csv(b'id_partida,time,jogador,Kills\nMATCH-1001,Alpha,Ana,999\nMATCH-1001,Alpha,Ana,999\n', 'kills')
        self.assertEqual(result['total_solicitado'], 1)
        self.assertEqual(result['comparacao_csv']['resumo']['linhas_divergentes'], 2)
        self.assertEqual(result['comparacao_csv']['resumo']['linhas_duplicadas'], 1)
        self.assertEqual(result['premios']['premio_jogadores'][0]['total_kills'], 12)
        self.assertEqual(result['partidas'][0]['participantes'][0]['kills'], 12)
        database.assert_called_once_with('MATCH-1001')
        api.assert_not_called()
        save.assert_not_called()

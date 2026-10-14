import unittest

import pandas as pd

from src.services.rateio_criteria import CriterioRateio
from src.services.tournament_service import TournamentService


class RateioIgualitario(CriterioRateio):
    def calcular_totais(self, dados):
        return pd.Series(1, index=sorted(dados['jogador'].unique()))


class PrizeDistributionTests(unittest.TestCase):
    def setUp(self):
        self.dados = pd.DataFrame([
            {'ID Partida': 'M1', 'time': 'Alpha', 'jogador': 'Ana',
             'Minutos': 30, 'Kills': 2, 'Venceu?': 'Sim'},
            {'ID Partida': 'M1', 'time': 'Alpha', 'jogador': 'Bia',
             'Minutos': 20, 'Kills': 6, 'Venceu?': 'Sim'},
            {'ID Partida': 'M2', 'time': 'Alpha', 'jogador': 'Ana',
             'Minutos': 10, 'Kills': 1, 'Venceu?': 'Sim'},
            {'ID Partida': 'M2', 'time': 'Alpha', 'jogador': 'Bia',
             'Minutos': 0, 'Kills': 3, 'Venceu?': 'Sim'},
        ])

    def test_minutes_accumulate_matches_and_distribute_proportionally(self):
        result = TournamentService().calcular_rateio_premios(self.dados, premio_total=12000)
        self.assertEqual(result['criterio_utilizado'], 'minutos')
        self.assertEqual(result['classificacao_times'], [{'time': 'Alpha', 'vitorias': 2}])
        self.assertEqual(result['premio_jogadores'], [
            {'time': 'Alpha', 'jogador': 'Ana', 'total_minutos': 40, 'premio_rs': 4000.0},
            {'time': 'Alpha', 'jogador': 'Bia', 'total_minutos': 20, 'premio_rs': 2000.0},
        ])

    def test_kills_use_different_weights(self):
        result = TournamentService().calcular_rateio_premios(self.dados, criterio='kills')
        self.assertEqual(result['premio_jogadores'], [
            {'time': 'Alpha', 'jogador': 'Ana', 'total_kills': 3, 'premio_rs': 1250.0},
            {'time': 'Alpha', 'jogador': 'Bia', 'total_kills': 9, 'premio_rs': 3750.0},
        ])

    def test_new_strategy_can_be_injected_without_changing_calculation(self):
        service = TournamentService(criterios={'igualitario': RateioIgualitario()})
        result = service.calcular_rateio_premios(self.dados, criterio='igualitario')
        self.assertEqual(result['criterio_utilizado'], 'igualitario')
        self.assertEqual([p['premio_rs'] for p in result['premio_jogadores']], [2500.0, 2500.0])
        self.assertEqual([p['total_igualitario'] for p in result['premio_jogadores']], [1, 1])
        # A extensão pertence à instância que a recebeu.
        with self.assertRaises(ValueError):
            TournamentService().calcular_rateio_premios(self.dados, criterio='igualitario')

    def test_zero_weights_do_not_divide_by_zero(self):
        self.dados['Kills'] = 0
        result = TournamentService().calcular_rateio_premios(self.dados, criterio='kills')
        self.assertEqual([p['premio_rs'] for p in result['premio_jogadores']], [0, 0])

    def test_unknown_criterion_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Critério de rateio desconhecido'):
            TournamentService().calcular_rateio_premios(self.dados, criterio='invalido')

    def test_podium_percentages_are_preserved(self):
        rows = []
        for team, wins in [('Alpha', 4), ('Beta', 3), ('Gamma', 2), ('Delta', 1)]:
            for match in range(wins):
                rows.append({'ID Partida': f'{team}-{match}', 'time': team, 'jogador': team,
                             'Minutos': 20, 'Kills': 5, 'Venceu?': 'Sim'})
        result = TournamentService().calcular_rateio_premios(pd.DataFrame(rows))
        self.assertEqual({p['time']: p['premio_rs'] for p in result['premio_jogadores']},
                         {'Alpha': 5000.0, 'Beta': 3000.0, 'Gamma': 2000.0})

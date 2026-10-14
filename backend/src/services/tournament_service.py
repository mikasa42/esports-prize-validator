"""Classificação e rateio calculados em memória com os dados retornados pela API."""
from itertools import groupby
from typing import Mapping, Optional

from src.services.rateio_criteria import CRITERIOS_PADRAO, CriterioRateio


class TournamentService:
    def __init__(self, criterios: Optional[Mapping[str, CriterioRateio]] = None):
        self._criterios = {**CRITERIOS_PADRAO, **(criterios or {})}

    def classificar_times(self, dados) -> list:
        """Vitórias por partida, depois abates totais; empate completo divide a posição."""
        kills = dados.groupby('time')['Kills'].sum().rename('kills')
        wins = dados[dados['Venceu?'].str.strip().str.lower() == 'sim'].groupby('time')['ID Partida'].nunique().rename('vitorias')
        ranking = kills.to_frame().join(wins).fillna({'vitorias': 0}).reset_index()
        ranking['vitorias'] = ranking['vitorias'].astype(int)
        ranking = ranking.sort_values(['vitorias', 'kills', 'time'], ascending=[False, False, True])
        records = ranking.to_dict(orient='records')
        position = 0
        previous = None
        for index, row in enumerate(records):
            score = (row['vitorias'], row['kills'])
            if score != previous:
                position = index + 1
            row['posicao'] = position
            previous = score
        return records

    def calcular_vitorias_por_time(self, dados) -> list:
        return [{'time': row['time'], 'vitorias': row['vitorias']}
                for row in self.classificar_times(dados) if row['vitorias'] > 0]

    def calcular_rateio_premios(self, dados, premio_total: float = 10000.00, criterio: str = 'minutos') -> dict:
        """Divide 50%, 30% e 20% entre o pódio, e rateia por estratégia dentro do time.

        Times empatados em vitórias e kills dividem os valores das posições ocupadas.
        Se o empate alcançar uma posição sem prêmio, sua parcela é zero.
        """
        try:
            estrategia = self._criterios[criterio]
        except KeyError:
            raise ValueError(f'Critério de rateio desconhecido: {criterio}') from None

        ranking = [row for row in self.classificar_times(dados) if row['vitorias'] > 0]
        percentuais = [0.50, 0.30, 0.20]
        premios_times = []
        index = 0
        for _, group in groupby(ranking, key=lambda row: (row['vitorias'], row['kills'])):
            tied = list(group)
            percentual = sum(percentuais[index:index + len(tied)]) / len(tied)
            for row in tied:
                premios_times.append({**row, 'percentual': percentual,
                                      'premio_rs': round(premio_total * percentual, 2)})
            index += len(tied)

        resultados_jogadores = []
        for team in premios_times:
            # Mantém precisão no cálculo; arredonda somente os valores de exibição.
            premio_time = premio_total * team['percentual']
            if premio_time == 0:
                continue
            df_time = dados[dados['time'] == team['time']]
            totais_jogador = estrategia.calcular_totais(df_time)
            total = totais_jogador.sum()
            for jogador, pontos in totais_jogador.items():
                proporcao = pontos / total if total > 0 else 0
                resultados_jogadores.append({
                    'time': team['time'], 'jogador': jogador,
                    f'total_{criterio}': int(pontos),
                    'premio_rs': round(premio_time * proporcao, 2),
                })

        return {
            'criterio_utilizado': criterio,
            'classificacao_times': [{'time': row['time'], 'vitorias': row['vitorias']} for row in ranking],
            'premios_times': premios_times,
            'premio_jogadores': resultados_jogadores,
        }

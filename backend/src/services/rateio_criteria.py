"""Estratégias para calcular o peso de cada jogador no rateio do prêmio."""
from abc import ABC, abstractmethod

import pandas as pd


class CriterioRateio(ABC):
    @abstractmethod
    def calcular_totais(self, dados: pd.DataFrame) -> pd.Series:
        """Retorna os pesos por jogador, com o nome do jogador como índice."""
        raise NotImplementedError


class RateioPorMinutos(CriterioRateio):
    def calcular_totais(self, dados: pd.DataFrame) -> pd.Series:
        return dados.groupby('jogador')['Minutos'].sum()


class RateioPorKills(CriterioRateio):
    def calcular_totais(self, dados: pd.DataFrame) -> pd.Series:
        return dados.groupby('jogador')['Kills'].sum()


CRITERIOS_PADRAO = {
    'minutos': RateioPorMinutos(),
    'kills': RateioPorKills(),
}

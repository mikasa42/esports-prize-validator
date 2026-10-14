"""Cliente HTTP da API oficial simulada; não acessa seu banco diretamente."""
import logging
import os
import time
from urllib.parse import quote

import requests
from src.match_ids import normalizar_id_partida

logger = logging.getLogger(__name__)


class PartidaNaoEncontrada(Exception):
    pass


class APIOficialIndisponivel(Exception):
    pass


class OfficialApiClient:
    @staticmethod
    def consultar_partida(match_id_externo: str, max_tentativas: int = 3):
        match_id_externo = normalizar_id_partida(match_id_externo)
        if max_tentativas < 1:
            raise ValueError('É necessário pelo menos uma tentativa.')
        base = os.environ.get('OFFICIAL_API_URL', 'http://127.0.0.1:8001').rstrip('/')
        url = f'{base}/api/partidas/{quote(str(match_id_externo), safe="")}'
        for tentativa in range(1, max_tentativas + 1):
            try:
                response = requests.get(url, timeout=(3, 15))
                if response.status_code == 404:
                    raise PartidaNaoEncontrada('Partida não encontrada no banco oficial.')
                response.raise_for_status()
                result = response.json()
                if (not isinstance(result, dict) or normalizar_id_partida(result.get('match_id_externo', '')) != match_id_externo
                        or not isinstance(result.get('participantes'), list)
                        or not all(key in result for key in ('data_partida', 'rodada', 'confronto'))):
                    raise APIOficialIndisponivel('Resposta inválida da API oficial.')
                result['match_id_externo'] = match_id_externo
                result['tentativas_realizadas'] = tentativa
                return result
            except requests.RequestException as err:
                if tentativa == max_tentativas:
                    raise APIOficialIndisponivel(
                        f'API oficial indisponível após {max_tentativas} tentativas.'
                    ) from err
                logger.warning('Falha na consulta da partida %s; tentativa %s.', match_id_externo, tentativa)
                time.sleep(tentativa)
        raise APIOficialIndisponivel('Não foi possível consultar a API oficial.')

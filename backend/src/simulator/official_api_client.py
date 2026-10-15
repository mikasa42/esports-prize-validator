"""Cliente HTTP da API oficial simulada; não acessa seu banco diretamente."""
import os
from urllib.parse import quote

import requests
from src.match_ids import normalizar_id_partida

class PartidaNaoEncontrada(Exception):
    pass


class APIOficialIndisponivel(Exception):
    pass


class OfficialApiClient:
    @staticmethod
    def consultar_partida(match_id_externo: str):
        match_id_externo = normalizar_id_partida(match_id_externo)
        base = os.environ.get('OFFICIAL_API_URL', 'http://127.0.0.1:8001').rstrip('/')
        url = f'{base}/api/partidas/{quote(str(match_id_externo), safe="")}'
        try:
            response = requests.get(url)
            if response.status_code == 404:
                raise PartidaNaoEncontrada('Partida não encontrada no banco oficial.')
            response.raise_for_status()
            result = response.json()
            if (not isinstance(result, dict) or normalizar_id_partida(result.get('match_id_externo', '')) != match_id_externo
                    or not isinstance(result.get('participantes'), list)
                    or not all(key in result for key in ('data_partida', 'rodada', 'confronto'))):
                raise APIOficialIndisponivel('Resposta inválida da API oficial.')
            result['match_id_externo'] = match_id_externo
            result['tentativas_realizadas'] = 1
            return result
        except requests.RequestException as err:
            raise APIOficialIndisponivel('API oficial indisponível.') from err

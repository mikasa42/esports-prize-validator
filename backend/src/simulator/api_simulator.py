import random
import time
import logging

logger = logging.getLogger(__name__)

class OficialApiSimulator:
    @staticmethod
    def consultar_partida(match_id_externo: str, max_tentativas: int = 3):
        """
        Simula a consulta ao site oficial do jogo por ID de partida.
        - Leva de 2 a 10 segundos por tentativa.
        - Possui falhas simuladas (15% de chance de erro).
        - Inclui política de retry para resiliência.
        """
        tentativa = 0
        
        while tentativa < max_tentativas:
            tentativa += 1
            # Simula o tempo de resposta entre 2 e 10 segundos exigido pelo desafio
            delay = random.randint(2, 10)
            time.sleep(delay)
            
            # Simula 15% de chance de o site oficial cair ou não responder
            if random.random() < 0.15:
                if tentativa < max_tentativas:
                    logger.warning(f"Tentativa {tentativa} falhou para a partida {match_id_externo}. Tentando novamente...")
                    continue
                else:
                    raise ConnectionError(f"Erro crítico: O site oficial falhou após {max_tentativas} tentativas para a partida {match_id_externo}.")
            
            # Retorna o resultado simulado com sucesso
            return {
                "match_id_externo": match_id_externo,
                "status": "sucesso",
                "tentativas_realizadas": tentativa,
                "tempo_resposta_segundos": delay,
                "verificado": True,
                "mensagem": "Dados da partida conferidos com o site oficial com sucesso."
            }
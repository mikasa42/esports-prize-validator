import random
import time

class OficialApiSimulator:
    @staticmethod
    def consultar_partida(match_id_externo: str):
        # Simula o tempo de resposta entre 2 e 10 segundos
        delay = random.randint(2, 10)
        time.sleep(delay)
        
        # Simula uma chance de 15% de erro/instabilidade (fora do ar)
        if random.random() < 0.15:
            raise ConnectionError("O site oficial está instável ou fora do ar no momento.")
        
        # Retorna dados simulados conferidos com sucesso
        return {
            "match_id_externo": match_id_externo,
            "status": "sucesso",
            "tempo_resposta_segundos": delay,
            "verificado": True
        }
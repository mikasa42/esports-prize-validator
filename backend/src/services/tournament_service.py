"""Classificação e rateio calculados em memória com os dados retornados pela API."""

class TournamentService:
    def calcular_vitorias_por_time(self, dados) -> dict:
        """Calcula o total de vitórias por time para definir a colocação."""
        df = dados
        
        # Filtra apenas linhas onde o time venceu ('Sim')
        # Agrupa por time e conta partidas únicas ou ocorrências
        vitorias = df[df['Venceu?'].str.strip().str.lower() == 'sim'].groupby('time')['ID Partida'].nunique().reset_index()
        vitorias.columns = ['time', 'vitorias']
        
        # Ordena da maior para a menor quantidade de vitórias
        vitorias = vitorias.sort_values(by='vitorias', ascending=False)
        return vitorias.to_dict(orient='records')

    def calcular_rateio_premios(self, dados, premio_total: float = 10000.00, criterio: str = 'minutos') -> dict:
        """
        Calcula a distribuição do prêmio total (ex: R$ 10.000,00) seguindo a regra:
        - 1º lugar: 50%
        - 2º lugar: 30%
        - 3º lugar: 20%
        E dentro do time, divide proporcionalmente por 'minutos' ou 'kills'.
        """
        df = dados
        
        # Separa a coluna 'Time / Nick' em 'time' e 'jogador'
        
        # 1. Calcula vitórias por time para definir o pódio
        vitorias_por_time = df[df['Venceu?'].str.strip().str.lower() == 'sim'].groupby('time')['ID Partida'].nunique().reset_index()
        vitorias_por_time.columns = ['time', 'vitorias']
        vitorias_por_time = vitorias_por_time.sort_values(by='vitorias', ascending=False).reset_index(drop=True)
        
        # Atribuição das porcentagens do prêmio por colocação
        # 1º = 50%, 2º = 30%, 3º = 20% (ajustando se houver menos times)
        percentuais = [0.50, 0.30, 0.20]
        premio_por_time = {}
        
        for index, row in vitorias_por_time.iterrows():
            if index < len(percentuais):
                premio_por_time[row['time']] = premio_total * percentuais[index]
            else:
                premio_por_time[row['time']] = 0.0  # Demais posições não levam prêmio principal

        resultados_jogadores = []
        
        # 2. Rateio interno do prêmio do time para cada jogador
        for time_nome, premio_time in premio_por_time.items():
            if premio_time == 0:
                continue
                
            df_time = df[df['time'] == time_nome]
            
            # Agrupa os dados do jogador no time (soma de minutos ou kills)
            coluna_criterio = 'Minutos' if criterio == 'minutos' else 'Kills'
            totais_jogador = df_time.groupby('jogador')[coluna_criterio].sum().reset_index()
            
            total_geral_criterio = totais_jogador[coluna_criterio].sum()
            
            for _, j_row in totais_jogador.iterrows():
                jogador = j_row['jogador']
                pontos = j_row[coluna_criterio]
                
                # Evita divisão por zero
                proporcao = (pontos / total_geral_criterio) if total_geral_criterio > 0 else 0
                valor_receber = premio_time * proporcao
                
                resultados_jogadores.append({
                    "time": time_nome,
                    "jogador": jogador,
                    f"total_{criterio}": int(pontos),
                    "premio_rs": round(valor_receber, 2)
                })
                
        return {
            "criterio_utilizado": criterio,
            "classificacao_times": vitorias_por_time.to_dict(orient='records'),
            "premio_jogadores": resultados_jogadores
        }
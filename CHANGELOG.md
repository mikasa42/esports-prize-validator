# Notas de versão

## 1.0.0 — em preparação

### Comparação CSV × API oficial

- A tela **Nova consulta** apresenta a conferência dos valores do CSV ao lado dos dados oficiais, com identificação da linha, partida e jogador.
- Comparação de abates, minutos jogados, rodada, data, confronto, torneio, equipe, jogador, mortes, assistências, resultado e time vencedor, quando os campos forem enviados e houver referência oficial.
- Destaques para divergências, valores inválidos, campos vazios, colunas não comparáveis e respostas oficiais indisponíveis.
- Busca, filtros de conferência e paginação; apresentação responsiva para desktop e celular.
- Leitura de CSV em UTF-8 com vírgula, ponto e vírgula ou tabulação; preservação dos valores e das linhas repetidas para conferência.
- CSV de exemplo atualizado com informações de jogadores e estatísticas.
- O upload retorna `comparacao_csv`, mantendo os resultados anteriores e a compatibilidade com arquivos contendo apenas IDs.

### Regras preservadas

- Cada ID é consultado uma única vez por envio, mesmo quando aparece em várias linhas.
- Classificação e premiações continuam usando exclusivamente os dados oficiais.
- Respostas oficiais já salvas são reutilizadas e identificadas na tela; não representam uma nova consulta à API.
- Campos sem equivalente ou sem identificação suficiente do jogador não são considerados conferidos.
- O arquivo CSV e a conferência não são persistidos como histórico de auditoria.

### Validação da funcionalidade

- Suíte do backend: 100 testes, com 2 testes opcionais ignorados.
- Suíte do painel: 36 testes aprovados.
- Build de produção concluído.
- Upload real autenticado conferido no navegador, incluindo divergências de minutos, abates e rodada e visualização em desktop e celular.

A versão permanece em preparação na branch `release/1.0.0`. A publicação na
`master` e a criação da tag de versão são etapas posteriores.

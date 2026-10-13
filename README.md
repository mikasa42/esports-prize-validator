# PowerRev Tech Challenge — Consulta de Partidas e Premiações

O painel lê os IDs de um CSV, consulta a API oficial e mostra as partidas,
seus jogadores, a classificação por vitórias e o rateio de R$ 10.000,00
por minutos jogados ou abates. O backend não usa banco de dados, não salva
uploads ou respostas e não mantém cache. Cada envio faz novas consultas à API.

## Executar com Docker

```bash
docker compose up -d --build
```

- Painel: http://localhost:3000
- Backend: http://localhost:8000/docs
- API oficial simulada: http://localhost:8001/docs

O Compose inicia o backend, o frontend e o simulador oficial. Apenas o
simulador tem um MySQL próprio (`official-db`), que fornece os dados já
existentes da API externa. O backend acessa esse serviço por HTTP e não
possui conexão ou dependência desse banco. As consultas não gravam dados.

## Consultar um CSV

Selecione um CSV UTF-8 de até 10 MB, escolha o critério de rateio e clique
em **Consultar partidas**. O arquivo precisa conter `id_partida` ou `ID Partida`;
as demais colunas são opcionais e não são usadas como fonte das estatísticas.
Não há vínculo com um torneio. Você pode misturar quaisquer IDs no arquivo.

```csv
id_partida
FN-2026-R1-M1001
FN-2026-R1-M1002
```

Os IDs são normalizados. Cada linha gera uma consulta sequencial, inclusive IDs repetidos. Hífens, espaços,
maiúsculas e zeros extras são normalizados: `fn–2026–r01–m01002` corresponde a
`FN-2026-R1-M1002`. A tela mostra todos os jogadores retornados pela API.

O endpoint é `POST /api/consultar-csv`, com os campos multipart `arquivo` e
`criterio` (`minutos` ou `kills`). Ele retorna `partidas`, `falhas`,
`total_solicitado`, `classificacao` e `premios`. Todos os cálculos usam somente
os dados oficiais dos IDs solicitados e são feitos em memória.
Se alguns IDs não forem encontrados ou a API falhar, as partidas disponíveis
continuam visíveis. Classificação e premiações ficam vazias até todos os IDs
serem encontrados. Cada falha identifica a partida afetada.

## Desenvolvimento local

Pré-requisitos: Python 3.10 a 3.12, Node.js 18+, npm 9+ e Bash.

```bash
npm run setup
# Inicia o simulador externo usado pelo backend local:
docker compose up -d official-db official-api
npm run dev
```

O setup instala `requirements.txt` na `.venv` e as dependências do frontend.
O backend usa `http://127.0.0.1:8001` como API oficial por padrão. Configure
`OFFICIAL_API_URL` para usar outra API compatível. `CORS_ORIGINS` aceita
origens separadas por vírgulas. O frontend consulta `/api` na mesma origem,
encaminhada ao backend pelo proxy React ou pelo Nginx nos containers.

```bash
npm run dev:backend
npm run dev:frontend
npm run check:backend
npm run build:frontend
```

## Simulador externo

Os arquivos em `backend/src/simulator` separam as duas responsabilidades:

- `official_api_client.py`: cliente HTTP usado pelo backend para consultar partidas, validar respostas e repetir chamadas após falhas de comunicação.
- `official_api_server.py`: servidor FastAPI que simula a API oficial, consulta o MySQL e aplica os atrasos e falhas configurados.

O serviço `official-api` usa `requirements-official.txt`, que adiciona as
bibliotecas de banco somente à imagem do simulador. `OFFICIAL_DATABASE_URL`
configura sua conexão ao MySQL. O SQL
`backend/src/simulator/Partidas_Oficiais_Fortnite.sql` inicializa 400
participações de jogadores em 50 partidas no primeiro uso do volume
`official_mysql_data`. Reiniciar os containers não reinsere os registros.

- Lista: `GET http://localhost:8001/api/partidas` (paginação por `limit` e `offset`).
- Partida: `GET http://localhost:8001/api/partidas/FN-2026-R1-M1001`.

A simulação tem latência de 2 a 10 segundos e 5% de falhas temporárias.
O backend tenta até três vezes por linha, com timeout. As consultas são sequenciais,
na ordem do CSV, sem paralelismo. IDs `MATCH-*` do CSV antigo não existem nesse
simulador; use os IDs `FN-2026-*` para obter resultados.

Para testar sem atrasos ou falhas simuladas:

```bash
OFFICIAL_MIN_DELAY=0 OFFICIAL_MAX_DELAY=0 OFFICIAL_FAILURE_RATE=0 docker compose up -d official-api
```

## Comparar desempenho

Para testar com o atraso simulado de 2 a 10 segundos e uma consulta por linha:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build
```

Essa configuração mantém a taxa de falhas simuladas de 5%. Novas tentativas
podem aumentar o tempo. Repetições de IDs geram novas consultas, mas os cálculos
de classificação e premiações consideram cada partida uma única vez.

## Testes

Para incluir os testes do simulador, instale também suas dependências:

```bash
.venv/bin/python -m pip install -r requirements-official.txt
cd backend
../.venv/bin/python -m unittest discover -s tests
```

Os testes da consulta confirmam o funcionamento sem SQLAlchemy ou PyMySQL,
o uso da API em cada upload, as consultas sequenciais por linha e os resultados parciais.

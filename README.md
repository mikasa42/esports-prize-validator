# PowerRev Tech Challenge — Consulta de Partidas e Premiações

O painel lê os IDs de um CSV, consulta a API oficial e mostra as partidas,
seus jogadores, a classificação por vitórias e o rateio de R$ 10.000,00
por minutos jogados ou abates. O backend salva partidas válidas em MySQL.
Consultas posteriores reutilizam esses dados, mesmo com a API oficial offline.

## Executar com Docker

```bash
docker compose up -d --build
```

- Painel: http://localhost:3000
- Backend: http://localhost:8000/docs
- API oficial simulada: http://localhost:8001/docs

O Compose inicia o backend, o frontend e o simulador oficial. O simulador tem
um MySQL próprio (`official-db`). O backend consulta a API por HTTP e salva
as respostas validadas em seu MySQL, no volume `backend_mysql_data`.
O volume conserva as partidas após recriar containers.

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

Os IDs são normalizados. Cada linha é resolvida sequencialmente. IDs já salvos não consultam a API. Hífens, espaços,
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
docker compose up -d backend-db official-db official-api
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
SQLAlchemy à imagem do simulador. PyMySQL também é usado pelo backend. `OFFICIAL_DATABASE_URL`
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
podem aumentar o tempo na primeira consulta. Repetições usam o banco; os cálculos
de classificação e premiações consideram cada partida uma única vez.

## Testes

Para incluir os testes do simulador, instale também suas dependências:

```bash
.venv/bin/python -m pip install -r requirements-official.txt
cd backend
../.venv/bin/python -m unittest discover -s tests
```

Os testes da consulta verificam
a reutilização das partidas persistidas, as consultas sequenciais e os resultados parciais.

## Persistência e consulta por ID

`GET /api/partidas/FN-2026-R1-M1001` retorna uma partida. Se ela ainda não
estiver salva, o backend consulta a API, valida e persiste sua resposta.
O mesmo fluxo é usado pelo upload CSV. O campo `origem` indica `api` na
primeira consulta e `banco` nas seguintes. Erros e partidas inválidas não
são salvos, permitindo novas tentativas.

O backend usa um MySQL próprio, separado do banco do simulador. A tabela
`partidas` é definida em `backend/src/database/schema.sql` e criada automaticamente
na primeira consulta. Ela guarda o ID, a resposta oficial em JSON e a data de gravação.

Em desenvolvimento local, execute `docker compose up -d backend-db`.
A conexão padrão é `127.0.0.1:3306`, banco `esports_backend`, usuário
`backend_user` e senha `backend_password`. Configure `MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_DATABASE`, `MYSQL_USER` e `MYSQL_PASSWORD` para usar outro servidor.
No Compose, as credenciais podem ser alteradas por `BACKEND_MYSQL_DATABASE`,
`BACKEND_MYSQL_USER`, `BACKEND_MYSQL_PASSWORD` e `BACKEND_MYSQL_ROOT_PASSWORD`.

As partidas não expiram automaticamente; o banco representa a primeira resposta
válida obtida para cada ID normalizado. O histórico é compartilhado, pois o projeto
ainda não possui login por usuário. Falhas de banco retornam HTTP 503.
Arquivos SQLite antigos não são importados automaticamente.

Os testes comuns usam um repositório simulado. Para executar também a persistência
real entre processos, crie um banco MySQL exclusivo de testes e execute:

```bash
cd backend
MYSQL_TEST_DATABASE=esports_backend_test ../.venv/bin/python -m unittest discover -s tests
```

Esse modo limpa a tabela `partidas` no banco indicado antes de cada teste;
use apenas um banco dedicado a testes e conceda acesso ao usuário configurado.

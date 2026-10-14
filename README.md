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

O Compose inicia o backend, o frontend e o simulador oficial. O simulador lê o arquivo `backend/src/simulator/Partidas_oficiais.json`. O backend consulta a API por HTTP e salva
as respostas validadas em seu MySQL, no volume `backend_mysql_data`.
O volume conserva as partidas após recriar containers.

## Consultar um CSV

Selecione um CSV UTF-8 de até 10 MB, escolha o critério de rateio e clique
em **Consultar partidas**. O arquivo precisa conter `id_partida` ou `ID Partida`;
as demais colunas são opcionais e não são usadas como fonte das estatísticas.
Não há vínculo com um torneio. Você pode misturar quaisquer IDs no arquivo.

```csv
id_partida
MATCH-1001
MATCH-1002
```

Os IDs são normalizados. Cada linha é resolvida sequencialmente. IDs já salvos não consultam a API. Hífens, espaços,
maiúsculas e zeros extras são normalizados: `match–1002` corresponde a
`MATCH-1002`. A tela mostra todos os jogadores retornados pela API.

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
docker compose up -d backend-db official-api
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
- `official_api_server.py`: servidor FastAPI que simula a API oficial, lê o JSON e responde sem atrasos ou falhas artificiais.

O serviço `official-api` lê `backend/src/simulator/Partidas_oficiais.json`,
montado no container em modo somente leitura. `OFFICIAL_DATA_PATH` permite
configurar outro caminho. O arquivo é relido a cada consulta.
Os campos `matchId`, `round`, `teamA`, `teamB` e `winnerTeam` são convertidos
para a resposta da API; `tournamentId`, mortes e assistências também são retornados.
A data da partida vem de `matchDate` e os minutos de cada jogador vêm de
`minutesPlayed`, retornados como `data_partida` e `minutos` na API.

- Lista: `GET http://localhost:8001/api/partidas` (paginação por `limit` e `offset`).
- Partida: `GET http://localhost:8001/api/partidas/MATCH-1001`.

A API responde sem atrasos ou falhas artificiais. O campo
`tempo_resposta_segundos` mede o processamento real da consulta.
O backend tenta até três vezes em caso de falhas de comunicação.
As consultas são sequenciais, na ordem do CSV. Use os IDs `MATCH-*`
presentes no campo `matchId` do JSON. Consultas posteriores usam o banco.

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

`GET /api/partidas/MATCH-1001` retorna uma partida. Se ela ainda não
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

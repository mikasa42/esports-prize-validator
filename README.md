# PowerRev Tech Challenge — Sistema de Gestão e Conferência de Torneios

Este repositório contém a solução desenvolvida para o **desafio técnico de Product Engineer** da **PowerRev**. 

## 🎯 Objetivo do Software
Maria Clara organiza torneios amadores de e-sports (jogos em equipes 5x5) e gerencia tudo manualmente através de planilhas e conferências manuais demoradas no site oficial do jogo, o que gera erros, lentidão e insatisfação dos jogadores na hora de distribuir as premiações[cite: 1, 2].

O **Tournament Hub** automatiza esse fluxo ponta a ponta:
1. **Upload e Leitura de Dados:** Processa o arquivo CSV exportado do Excel com os dados das partidas da competição.
2. **Conferência Resiliente:** Valida cada ID de partida contra o site oficial utilizando um simulador que reproduz latência realista (2 a 10 segundos) e falhas temporárias com política de *retries*.
3. **Cálculo Preciso de Premiações:** Organiza a classificação dos times por número de vitórias e realiza o rateio proporcional do prêmio em dinheiro entre os jogadores (permitindo alternar dinamicamente entre o critério atual de **minutos jogados** e a nova proposta de **kills/abates**).
4. **Interface Intuitiva:** Um painel centralizado para a operadora visualizar o status de tudo em tempo real.

---

## 🛠️ Tecnologias Utilizadas
* **Backend:** Python com **FastAPI** (validação de dados robusta e alta performance assíncrona).
* **Processamento de Dados:** **Pandas** (manipulação ágil do dataset CSV e cálculos estatísticos/financeiros).
* **Banco de Dados:** **MySQL 8.0** (orquestrado via Docker).
* **Frontend:** **React** e Axios para comunicação com a API.
* **Infraestrutura:** Docker e Docker Compose.

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos

* Python 3.10 a 3.12, com suporte a `venv`.
* Node.js 18+ e npm 9+.
* Bash para os scripts de desenvolvimento.
* Docker e Docker Compose para o MySQL opcional.

### Ambiente de desenvolvimento unificado

Na raiz do projeto, instale todas as dependências:

```bash
npm run setup
docker compose up -d db
npm run import:csv
source .venv/bin/activate
npm run dev
```

O setup cria a `.venv` na raiz e instala as bibliotecas de
`requirements.txt`. Também instala as dependências do frontend com
`npm ci`, usando `frontend/package-lock.json` e a opção `--legacy-peer-deps`
utilizada pelo projeto. Python e Node mantêm suas dependências em diretórios
próprios (`.venv/` e `frontend/node_modules/`), com comandos centralizados na
raiz. A antiga `backend/.venv` não é utilizada por esses comandos.

`npm run dev` inicia a API em `http://localhost:8000` e o frontend em
`http://localhost:3000`. Use Ctrl+C para encerrar os processos. A ativação da
`.venv` é útil para comandos Python manuais; os scripts já usam seu interpretador
explicitamente. No editor, selecione `.venv/bin/python` como interpretador.

Também é possível executar cada serviço em um terminal separado:

```bash
npm run dev:backend
npm run dev:frontend
```

Para conferir dependências Python ou gerar o build do frontend:

```bash
npm run check:backend
npm run build:frontend
```

O NumPy está fixado na série 1.26 para compatibilidade com Pandas 2.2.1.
Ao adicionar bibliotecas, atualize `requirements.txt` ou o manifesto e
lockfile do frontend, conforme a linguagem, e execute novamente o setup.

Para iniciar apenas o banco de dados:

```bash
docker compose up -d db
```

O painel permite enviar o CSV pela seção **Dados e conferência do torneio**.
Informe o nome do torneio, selecione o arquivo, escolha o critério de rateio
e clique em **Salvar**. A conferência no site oficial é iniciada automaticamente
após a carga, e o resultado aparece na mesma seção.
O backend valida e transforma o conteúdo antes de salvar no MySQL; o painel
atualiza automaticamente a classificação e as premiações após a importação.
O arquivo deve ser UTF-8, ter até 10 MB e conter as colunas `Data`, `Rodada`,
`ID Partida`, `Partida`, `Time / Nick`, `Minutos`, `Kills` e `Venceu?`.
Use datas `AAAA-MM-DD`, números inteiros não negativos, `Time / Jogador` e
resultados `Sim` ou `Não`. O endpoint é `POST /api/importar-csv`, com os campos
multipart `arquivo`, `nome` e `criterio` (`minutos` ou `kills`). Recarregar o mesmo nome substitui seus dados e
verificações; arquivos inválidos preservam os dados anteriores.

Também é possível fazer a carga pelo terminal.

O CSV é colocado manualmente em `database/torneio-setembro.csv`. Execute
`npm run import:csv` para validar e carregar os dados no MySQL. Para outro arquivo:

```bash
npm run import:csv -- /caminho/arquivo.csv --nome "Meu torneio"
```

A recarga substitui as partidas, participantes e verificações do torneio com o
mesmo nome, sem duplicar registros. A operação é transacional: se falhar,
os dados anteriores são preservados. IDs externos de partidas são únicos no banco.
O comando informa o ID do torneio importado; os endpoints aceitam `torneio_id`
(o painel começa no torneio 1 e passa a usar o torneio retornado pelo upload).

O fluxo é: upload ou CSV manual → importador Python (validação e transformação) → MySQL →
API → frontend. Classificação, premiações e conferência consultam o banco;
as requisições não releem o CSV. Após alterar o arquivo, execute a carga novamente.

A conexão padrão usa o MySQL local configurado no Compose. Para outro ambiente,
defina `DATABASE_URL` (formato `mysql+pymysql://usuario:senha@host:3306/banco`).
O frontend consulta `/api` na mesma origem. Em desenvolvimento, o proxy do
React encaminha para `127.0.0.1:8000`; em containers, o Nginx encaminha para
`backend:8000` pela rede do Compose.
Origens permitidas pela API podem ser definidas em `CORS_ORIGINS`, separadas por vírgulas.

### Executar todos os serviços em containers

```bash
docker compose up -d --build
docker compose exec backend python -m src.import_csv
```

Acesse o painel em `http://localhost:3000` e a documentação da API em
`http://localhost:8000/docs`. De outro dispositivo na rede, substitua
`localhost` pelo IP da máquina que executa o Docker. O navegador consulta
`/api` pelo painel na porta 3000; não precisa conhecer o IP dos containers.
O CSV local está montado no backend; após alterá-lo, repita o comando de carga.

### Site oficial simulado com MySQL separado

O Compose também inicia `official-db` (MySQL próprio, banco `fortnite_oficial`)
e `official-api` (FastAPI). O SQL
`backend/src/simulator/Partidas_Oficiais_Fortnite.sql` é executado automaticamente
na primeira inicialização do volume `official_mysql_data`, carregando 400
participações de jogadores e 50 partidas. O banco principal dos torneios continua
em `db`, com seu volume `mysql_data`; os uploads não alteram os dados oficiais.

- Documentação da API oficial: `http://localhost:8001/docs`.
- Lista de partidas: `GET http://localhost:8001/api/partidas` (paginação por `limit` e `offset`).
- Dados de uma partida: `GET http://localhost:8001/api/partidas/FN-2026-R1-M1001`.
- MySQL oficial: `127.0.0.1:3307`, banco `fortnite_oficial`, usuário `official_user`, senha `official_password`.

O backend consulta `http://official-api:8001` pela rede Docker. Fora dos
containers, usa `http://127.0.0.1:8001`, configurável por `OFFICIAL_API_URL`.
A API oficial usa `OFFICIAL_DATABASE_URL` para sua própria conexão.

Ao conferir partidas, o backend compara data, rodada, confronto, participantes,
minutos, abates e vitória com os dados oficiais. Os resultados são persistidos
como `verificado`, `divergente` ou `erro_api`. Um ID inexistente no site oficial
é uma divergência; falhas de conexão e indisponibilidade são erros de API.
O CSV de exemplo antigo contém IDs `MATCH-*`, ausentes no SQL Fortnite; para
uma conferência positiva, importe um CSV com os IDs `FN-2026-*` e os dados correspondentes.

A simulação mantém latência de 2 a 10 segundos e 15% de falhas temporárias.
O cliente faz até três tentativas, com timeout e até cinco partidas em paralelo.
Para um ambiente de teste sem atraso ou falhas:

```bash
OFFICIAL_MIN_DELAY=0 OFFICIAL_MAX_DELAY=0 OFFICIAL_FAILURE_RATE=0 docker compose up -d official-api
```

Para restaurar os padrões, execute `docker compose up -d official-api` sem
essas variáveis. A inicialização do SQL ocorre somente com um volume novo;
reiniciar os containers não reinsere os registros. Alterar o SQL após a primeira
carga não atualiza automaticamente o banco existente.

Ao reenviar um CSV com conteúdo idêntico ao conjunto completo de dados de um
torneio já cadastrado, mesmo usando outro nome, o sistema reutiliza seu ID,
aplica o critério escolhido e exibe a classificação e as premiações. Não cria
outro torneio nem duplica as partidas. Conteúdos diferentes ou parciais com IDs
de outro torneio exigem o nome original para atualizar os dados.

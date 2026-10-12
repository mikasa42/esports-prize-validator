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

O painel permite enviar o CSV pela seção **Importar dados do torneio**.
Informe o nome do torneio, selecione o arquivo e clique em **Importar CSV**.
O backend valida e transforma o conteúdo antes de salvar no MySQL; o painel
atualiza automaticamente a classificação e as premiações após a importação.
O arquivo deve ser UTF-8, ter até 10 MB e conter as colunas `Data`, `Rodada`,
`ID Partida`, `Partida`, `Time / Nick`, `Minutos`, `Kills` e `Venceu?`.
Use datas `AAAA-MM-DD`, números inteiros não negativos, `Time / Jogador` e
resultados `Sim` ou `Não`. O endpoint é `POST /api/importar-csv`, com os campos
multipart `arquivo` e `nome`. Recarregar o mesmo nome substitui seus dados e
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

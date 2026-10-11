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
source .venv/bin/activate
npm run dev
```

O setup cria a `.venv` na raiz e instala as bibliotecas de
`backend/requirements.txt`. Também instala as dependências do frontend com
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
Ao adicionar bibliotecas, atualize `backend/requirements.txt` ou o manifesto e
lockfile do frontend, conforme a linguagem, e execute novamente o setup.

Para iniciar apenas o banco de dados:

```bash
docker compose up -d db
```

O backend atual lê o CSV em `database/torneio-setembro.csv` e ainda não usa o
MySQL. A comunicação do painel com a API ainda depende de ajustar o endereço
fixo em `frontend/src/App.js` e configurar CORS no backend.

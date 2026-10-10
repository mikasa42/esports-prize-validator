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
* Docker e Docker Compose instalados na máquina.
* Python 3.10+
* Node.js

### Passo a Passo

1. **Subir o Banco de Dados (MySQL):**
   Na raiz do repositório, execute:
   ```bash
   docker compose up -d´´´
2. **Configurar e Executar o Backend (FastAPI):**
Na pasta backend, execute:
    ```bash
    cd backend
    python -m venv .venv
    source .venv/bin/activate  # No Windows (PowerShell): .venv\Scripts\Activate.ps1 | No Git Bash: source .venv/Scripts/activate
    pip install -r requirements.txt
    uvicorn src.main:app --reload ´´´
3. **Configurar e Executar o Frontend (React):**
Em um novo terminal, na pasta frontend, execute:
    ```bash
    cd frontend
    npm install
    npm start ´´´
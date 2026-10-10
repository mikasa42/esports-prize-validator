from fastapi import FastAPI, HTTPException
import pandas as pd
import os
from src.simulator.api_simulator import OficialApiSimulator

app = FastAPI(title="PowerRev Tournament API", version="1.0")

# Caminho simulado para o CSV que a Maria Clara mandou
CSV_PATH = os.path.join("..", "database", "torneio-setembro.csv")

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API de Gestão de Torneios da PowerRev!"}

@app.post("/api/verificar-partidas")
def verificar_partidas():
    """
    Simula a leitura do CSV da Maria Clara e a conferência no site oficial.
    """
    # Aqui faremos a leitura do CSV e a aplicação das regras
    return {"status": "Processo de verificação iniciado"}
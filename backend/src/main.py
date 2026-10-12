import os
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from src.services.match_lookup_service import consultar_csv

app = FastAPI(title="PowerRev Match API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API de consulta de partidas operando com sucesso!"}

MAX_CSV_BYTES = 10 * 1024 * 1024


@app.post('/api/consultar-csv')
def consultar_partidas_csv(
    arquivo: UploadFile = File(...),
    criterio: Literal['minutos', 'kills'] = Form('minutos'),
):
    try:
        if not arquivo.filename or not arquivo.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail='Selecione um arquivo .csv.')
        content = arquivo.file.read(MAX_CSV_BYTES + 1)
        if len(content) > MAX_CSV_BYTES:
            raise HTTPException(status_code=413, detail='O CSV deve ter no máximo 10 MB.')
        if not content.strip():
            raise HTTPException(status_code=400, detail='O arquivo CSV está vazio.')
        return consultar_csv(content, criterio)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail='Salve o CSV com codificação UTF-8.')
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        arquivo.file.close()

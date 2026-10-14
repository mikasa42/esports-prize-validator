import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.partidas import router as partidas_router

app = FastAPI(title="PowerRev Match API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(partidas_router)


@app.get("/")
def read_root():
    return {"message": "API de consulta de partidas operando com sucesso!"}

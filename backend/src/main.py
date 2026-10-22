import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.routers.auth import router as auth_router
from src.repositories.match_repository import BancoIndisponivel
from src.routers.partidas import router as partidas_router
from src.routers.publico import router as publico_router
from src.database.initialization import inicializar_banco

@asynccontextmanager
async def lifespan(app):
    inicializar_banco()
    yield


app = FastAPI(title="PowerRev Match API", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth_router)
app.include_router(partidas_router)
app.include_router(publico_router)


@app.middleware('http')
async def nao_armazenar_autenticacao(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/auth/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(RequestValidationError)
async def dados_invalidos(request, exc):
    # Não devolver valores enviados, especialmente senhas, nos erros 422.
    errors = [{'loc': error['loc'], 'msg': error['msg'], 'type': error['type']} for error in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': errors})


@app.exception_handler(BancoIndisponivel)
async def banco_indisponivel(request, exc):
    return JSONResponse(status_code=503, content={'detail': 'Banco de dados indisponível. Tente novamente.'})


@app.get("/")
def read_root():
    return {"message": "API de consulta de partidas operando com sucesso!"}

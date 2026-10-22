"""Autenticação por cookie HttpOnly e sessão revogável no servidor."""
import os
import re
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from src.repositories import auth_repository as repository
from src.services.auth_security import (
    COOKIE_NAME, DUMMY_HASH, SESSION_SECONDS, hash_senha, hash_token, verificar_senha,
)


def validar_requisicao(request: Request, x_requested_with: str | None = Header(None, alias='X-Requested-With')):
    if request.method in {'GET', 'HEAD', 'OPTIONS'}:
        return
    # Um site externo não pode enviar esse cabeçalho sem passar pelo CORS.
    if x_requested_with != 'TournamentHub':
        raise HTTPException(403, 'Cabeçalho de proteção da requisição ausente.')
    origin = request.headers.get('origin')
    allowed = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    if origin and origin not in [item.strip() for item in allowed]:
        raise HTTPException(403, 'Origem da requisição não permitida.')


router = APIRouter(prefix='/api/auth', tags=['Autenticação'], dependencies=[Depends(validar_requisicao)])


class Credenciais(BaseModel):
    login: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=128)

    @field_validator('login')
    @classmethod
    def normalizar_login(cls, value):
        return value.strip().lower()


class InformacoesUsuario(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    login: str = Field(min_length=3, max_length=100)
    empresa: str = Field(min_length=1, max_length=150)

    @field_validator('nome', 'empresa')
    @classmethod
    def validar_texto(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Preencha este campo.')
        return value

    @field_validator('login')
    @classmethod
    def validar_login(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9][a-z0-9._@+\-]{2,99}', value):
            raise ValueError('Use de 3 a 100 caracteres: letras, números, ponto, _, @, + ou hífen.')
        return value


class Cadastro(InformacoesUsuario):
    senha: str = Field(min_length=12, max_length=128)


class TrocaSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=12, max_length=128)


class UsuarioPublico(BaseModel):
    id: int
    nome: str
    login: str
    empresa: str


def limitar_tentativas(request: Request):
    # Não confiar em X-Forwarded-For fornecido pelo cliente.
    address = request.client.host if request.client else 'unknown'
    if not repository.registrar_tentativa(hash_token(address)):
        raise HTTPException(429, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.', headers={'Retry-After': '900'})


def usuario_atual(request: Request):
    token = request.cookies.get(COOKIE_NAME, '')
    if not token or len(token) > 128:
        raise HTTPException(401, 'Entre na sua conta para continuar.')
    usuario = repository.buscar_sessao(hash_token(token))
    if not usuario:
        raise HTTPException(401, 'Sua sessão expirou. Entre novamente.')
    return usuario


def iniciar_sessao(usuario, request, response):
    token = secrets.token_urlsafe(32)
    anterior = request.cookies.get(COOKIE_NAME)
    repository.criar_sessao(usuario['id'], hash_token(token), hash_token(anterior) if anterior else None)
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=os.environ.get('AUTH_COOKIE_SECURE', 'false').lower() == 'true',
                        samesite='lax', path='/api')
    response.headers['Cache-Control'] = 'no-store'
    return usuario


@router.post('/cadastro', status_code=201, response_model=UsuarioPublico, dependencies=[Depends(limitar_tentativas)])
def cadastrar(dados: Cadastro, request: Request, response: Response):
    try:
        usuario = repository.criar_usuario(dados.nome, dados.login, hash_senha(dados.senha), dados.empresa)
    except repository.LoginEmUso:
        raise HTTPException(409, 'Este login já está em uso.')
    return iniciar_sessao(usuario, request, response)


@router.post('/login', response_model=UsuarioPublico, dependencies=[Depends(limitar_tentativas)])
def entrar(dados: Credenciais, request: Request, response: Response):
    usuario = repository.buscar_usuario(dados.login)
    valido = verificar_senha(dados.senha, usuario['senha_hash'] if usuario else DUMMY_HASH)
    if not usuario or not valido:
        raise HTTPException(401, 'Login ou senha inválidos.')
    return iniciar_sessao(usuario, request, response)


@router.get('/me', response_model=UsuarioPublico)
def minha_conta(response: Response, usuario=Depends(usuario_atual)):
    response.headers['Cache-Control'] = 'no-store'
    return usuario


@router.post('/logout', status_code=204)
def sair(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        repository.remover_sessao(hash_token(token))
    response.delete_cookie(COOKIE_NAME, path='/api', httponly=True,
                           secure=os.environ.get('AUTH_COOKIE_SECURE', 'false').lower() == 'true', samesite='lax')
    response.headers['Cache-Control'] = 'no-store'


@router.post('/perfil', response_model=UsuarioPublico)
def editar_perfil(dados: InformacoesUsuario, usuario=Depends(usuario_atual)):
    try:
        return repository.atualizar_usuario(usuario['id'], dados.nome, dados.login, dados.empresa)
    except repository.LoginEmUso:
        raise HTTPException(409, 'Este login já está em uso.')


@router.post('/senha', status_code=204, dependencies=[Depends(limitar_tentativas)])
def alterar_senha(dados: TrocaSenha, request: Request, usuario=Depends(usuario_atual)):
    conta = repository.buscar_usuario(usuario['login'])
    if not conta or not verificar_senha(dados.senha_atual, conta['senha_hash']):
        raise HTTPException(400, 'A senha atual está incorreta.')
    if dados.senha_atual == dados.nova_senha:
        raise HTTPException(400, 'Escolha uma senha diferente da atual.')
    alterada = repository.trocar_senha(usuario['id'], conta['senha_hash'], hash_senha(dados.nova_senha),
                                     hash_token(request.cookies[COOKIE_NAME]))
    if not alterada:
        raise HTTPException(409, 'A senha foi alterada em outra sessão. Entre novamente.')

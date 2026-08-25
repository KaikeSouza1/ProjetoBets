"""Ponto de entrada da API. O Streamlit deixou de ser a interface principal — o frontend
React fala só com estas rotas, nunca com o banco ou com o engine diretamente."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import backtests, dashboard, health, leads, leagues, matches, teams
from app.core import db
from app.core.errors import InsufficientDataError, NotFoundError


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    db.bootstrap()
    yield


app = FastAPI(title="Motor de Análise de Apostas — API", version="1.0", lifespan=_lifespan)

_allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
def handle_not_found(_request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InsufficientDataError)
def handle_insufficient_data(_request: Request, exc: InsufficientDataError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ValueError)
def handle_value_error(_request: Request, exc: ValueError):
    # o engine levanta ValueError para 'dados insuficientes' — nunca vira 500 genérico
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router)
app.include_router(matches.router)
app.include_router(leagues.router)
app.include_router(teams.router)
app.include_router(backtests.router)
app.include_router(leads.router)

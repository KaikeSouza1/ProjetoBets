"""Testes de integração deste projeto sempre dependem de Postgres — não existe camada
de mock pro banco em nenhuma parte do código (ver engine/*, services/*). Aqui só garante
que o schema mais recente já foi aplicado antes de rodar qualquer teste."""
import pytest

from app.core import db


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_schema():
    db.bootstrap()

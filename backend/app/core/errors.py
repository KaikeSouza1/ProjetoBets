"""Erros padronizados — a API nunca deixa uma exceção crua (traceback, SQL, etc.) chegar
ao frontend. Toda rota que pode falhar por 'não encontrado' ou 'dado insuficiente'
levanta uma dessas, mapeadas para HTTP pelo handler em main.py."""


class NotFoundError(Exception):
    pass


class InsufficientDataError(Exception):
    pass

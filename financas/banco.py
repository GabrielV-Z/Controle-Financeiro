import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    valor INTEGER NOT NULL CHECK (valor > 0),
    categoria TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes (data);
CREATE INDEX IF NOT EXISTS idx_transacoes_categoria ON transacoes (categoria);

CREATE TABLE IF NOT EXISTS orcamentos (
    categoria TEXT PRIMARY KEY,
    limite INTEGER NOT NULL CHECK (limite > 0)
);
"""


def conectar(caminho):
    if str(caminho) != ":memory:":
        caminho = Path(caminho).expanduser()
        caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(caminho))
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con

import csv
from dataclasses import dataclass, replace
from datetime import date

from .modelos import (
    ErroValidacao,
    Transacao,
    parse_data,
    parse_valor,
    valor_decimal,
)

CABECALHO_CSV = ["tipo", "valor", "categoria", "descricao", "data"]


@dataclass(frozen=True)
class Resumo:
    receitas: int
    despesas: int
    por_categoria: list

    @property
    def saldo(self):
        return self.receitas - self.despesas


@dataclass(frozen=True)
class SituacaoOrcamento:
    categoria: str
    limite: int
    gasto: int

    @property
    def estourado(self):
        return self.gasto > self.limite

    @property
    def percentual(self):
        return self.gasto * 100 / self.limite


def _chave_mes(mes):
    return "%04d-%02d" % mes


def _para_transacao(linha):
    return Transacao(
        id=linha["id"],
        tipo=linha["tipo"],
        valor=linha["valor"],
        categoria=linha["categoria"],
        descricao=linha["descricao"],
        data=date.fromisoformat(linha["data"]),
    )


class Financas:
    def __init__(self, con):
        self.con = con

    def adicionar(self, transacao):
        with self.con:
            cur = self.con.execute(
                "INSERT INTO transacoes (tipo, valor, categoria, descricao, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    transacao.tipo,
                    transacao.valor,
                    transacao.categoria,
                    transacao.descricao,
                    transacao.data.isoformat(),
                ),
            )
        return replace(transacao, id=cur.lastrowid)

    def remover(self, id_transacao):
        with self.con:
            cur = self.con.execute("DELETE FROM transacoes WHERE id = ?", (id_transacao,))
        return cur.rowcount > 0

    def listar(self, tipo=None, categoria=None, mes=None, limite=None):
        sql = "SELECT * FROM transacoes"
        condicoes, params = [], []
        if tipo:
            condicoes.append("tipo = ?")
            params.append(tipo)
        if categoria:
            condicoes.append("categoria = ?")
            params.append(categoria.strip().lower())
        if mes:
            condicoes.append("substr(data, 1, 7) = ?")
            params.append(_chave_mes(mes))
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        sql += " ORDER BY data DESC, id DESC"
        if limite:
            sql += " LIMIT ?"
            params.append(limite)
        return [_para_transacao(l) for l in self.con.execute(sql, params)]

    def saldo(self):
        linha = self.con.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor ELSE -valor END), 0) "
            "FROM transacoes"
        ).fetchone()
        return linha[0]

    def resumo_mensal(self, mes):
        chave = _chave_mes(mes)
        totais = {"receita": 0, "despesa": 0}
        for linha in self.con.execute(
            "SELECT tipo, SUM(valor) AS total FROM transacoes "
            "WHERE substr(data, 1, 7) = ? GROUP BY tipo",
            (chave,),
        ):
            totais[linha["tipo"]] = linha["total"]
        por_categoria = [
            (l["categoria"], l["total"])
            for l in self.con.execute(
                "SELECT categoria, SUM(valor) AS total FROM transacoes "
                "WHERE tipo = 'despesa' AND substr(data, 1, 7) = ? "
                "GROUP BY categoria ORDER BY total DESC, categoria",
                (chave,),
            )
        ]
        return Resumo(totais["receita"], totais["despesa"], por_categoria)

    def definir_orcamento(self, categoria, limite):
        categoria = categoria.strip().lower()
        if not categoria:
            raise ErroValidacao("a categoria nao pode ser vazia")
        if limite <= 0:
            raise ErroValidacao("o limite deve ser maior que zero")
        with self.con:
            self.con.execute(
                "INSERT INTO orcamentos (categoria, limite) VALUES (?, ?) "
                "ON CONFLICT(categoria) DO UPDATE SET limite = excluded.limite",
                (categoria, limite),
            )

    def remover_orcamento(self, categoria):
        with self.con:
            cur = self.con.execute(
                "DELETE FROM orcamentos WHERE categoria = ?", (categoria.strip().lower(),)
            )
        return cur.rowcount > 0

    def situacao_orcamentos(self, mes):
        chave = _chave_mes(mes)
        linhas = self.con.execute(
            "SELECT o.categoria, o.limite, COALESCE(SUM(t.valor), 0) AS gasto "
            "FROM orcamentos o "
            "LEFT JOIN transacoes t ON t.categoria = o.categoria "
            "AND t.tipo = 'despesa' AND substr(t.data, 1, 7) = ? "
            "GROUP BY o.categoria, o.limite ORDER BY o.categoria",
            (chave,),
        )
        return [SituacaoOrcamento(l["categoria"], l["limite"], l["gasto"]) for l in linhas]

    def exportar_csv(self, caminho):
        transacoes = self.listar()
        with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(CABECALHO_CSV)
            for t in reversed(transacoes):
                escritor.writerow(
                    [t.tipo, valor_decimal(t.valor), t.categoria, t.descricao, t.data.isoformat()]
                )
        return len(transacoes)

    def importar_csv(self, caminho):
        novas = []
        with open(caminho, newline="", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo)
            if leitor.fieldnames is None or set(CABECALHO_CSV) - set(leitor.fieldnames):
                raise ErroValidacao("cabecalho esperado: " + ",".join(CABECALHO_CSV))
            for numero, linha in enumerate(leitor, start=2):
                try:
                    novas.append(
                        Transacao(
                            tipo=linha["tipo"].strip().lower(),
                            valor=parse_valor(linha["valor"]),
                            categoria=linha["categoria"],
                            descricao=linha["descricao"] or "",
                            data=parse_data(linha["data"]),
                        )
                    )
                except (ErroValidacao, AttributeError, TypeError) as erro:
                    raise ErroValidacao("linha %d: %s" % (numero, erro))
        with self.con:
            self.con.executemany(
                "INSERT INTO transacoes (tipo, valor, categoria, descricao, data) "
                "VALUES (?, ?, ?, ?, ?)",
                [(t.tipo, t.valor, t.categoria, t.descricao, t.data.isoformat()) for t in novas],
            )
        return len(novas)

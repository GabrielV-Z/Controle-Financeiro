import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .banco import conectar
from .modelos import (
    ErroValidacao,
    TIPOS,
    Transacao,
    formatar_valor,
    parse_data,
    parse_mes,
    parse_valor,
)
from .relatorio import tabela_transacoes, texto_resumo
from .servico import Financas


def caminho_padrao():
    return os.environ.get("FINANCAS_DB") or str(Path.home() / ".financas" / "dados.db")


def mes_atual():
    hoje = date.today()
    return hoje.year, hoje.month


def criar_parser():
    parser = argparse.ArgumentParser(
        prog="financas", description="Controle financeiro pessoal pelo terminal."
    )
    parser.add_argument("--db", default=None, help="caminho do banco de dados")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("add", help="registra uma receita ou despesa")
    p.add_argument("tipo", choices=TIPOS)
    p.add_argument("valor")
    p.add_argument("categoria")
    p.add_argument("-d", "--descricao", default="")
    p.add_argument("--data", default=None, help="AAAA-MM-DD ou DD/MM/AAAA (padrao: hoje)")

    p = sub.add_parser("listar", help="lista transacoes")
    p.add_argument("--tipo", choices=TIPOS)
    p.add_argument("--categoria")
    p.add_argument("--mes", help="AAAA-MM")
    p.add_argument("-n", "--limite", type=int)

    p = sub.add_parser("remover", help="remove uma transacao pelo id")
    p.add_argument("id", type=int)

    p = sub.add_parser("resumo", help="resumo mensal com orcamentos")
    p.add_argument("--mes", help="AAAA-MM (padrao: mes atual)")

    sub.add_parser("saldo", help="saldo geral")

    p = sub.add_parser("orcamento", help="gerencia limites mensais por categoria")
    acoes = p.add_subparsers(dest="acao", required=True)
    a = acoes.add_parser("definir")
    a.add_argument("categoria")
    a.add_argument("limite")
    a = acoes.add_parser("remover")
    a.add_argument("categoria")

    p = sub.add_parser("exportar", help="exporta tudo para CSV")
    p.add_argument("arquivo")

    p = sub.add_parser("importar", help="importa transacoes de um CSV")
    p.add_argument("arquivo")

    return parser


def executar(args, financas):
    if args.comando == "add":
        data = parse_data(args.data) if args.data else date.today()
        t = financas.adicionar(
            Transacao(
                tipo=args.tipo,
                valor=parse_valor(args.valor),
                categoria=args.categoria,
                descricao=args.descricao,
                data=data,
            )
        )
        print("Registrado #%d: %s de %s em %s" % (t.id, t.tipo, formatar_valor(t.valor), t.categoria))

    elif args.comando == "listar":
        mes = parse_mes(args.mes) if args.mes else None
        print(tabela_transacoes(financas.listar(args.tipo, args.categoria, mes, args.limite)))

    elif args.comando == "remover":
        if financas.remover(args.id):
            print("Transacao #%d removida." % args.id)
        else:
            raise ErroValidacao("nao existe transacao com id %d" % args.id)

    elif args.comando == "resumo":
        mes = parse_mes(args.mes) if args.mes else mes_atual()
        rotulo = "%02d/%04d" % (mes[1], mes[0])
        print(texto_resumo(financas.resumo_mensal(mes), rotulo, financas.situacao_orcamentos(mes)))

    elif args.comando == "saldo":
        print("Saldo geral: %s" % formatar_valor(financas.saldo()))

    elif args.comando == "orcamento":
        if args.acao == "definir":
            financas.definir_orcamento(args.categoria, parse_valor(args.limite))
            print("Orcamento de %s definido." % args.categoria.strip().lower())
        else:
            if financas.remover_orcamento(args.categoria):
                print("Orcamento removido.")
            else:
                raise ErroValidacao("nao existe orcamento para %r" % args.categoria)

    elif args.comando == "exportar":
        print("%d transacoes exportadas para %s" % (financas.exportar_csv(args.arquivo), args.arquivo))

    elif args.comando == "importar":
        print("%d transacoes importadas." % financas.importar_csv(args.arquivo))


def main(argv=None):
    args = criar_parser().parse_args(argv)
    con = conectar(args.db or caminho_padrao())
    try:
        executar(args, Financas(con))
    except ErroValidacao as erro:
        print("erro: %s" % erro, file=sys.stderr)
        return 1
    except OSError as erro:
        print("erro: %s" % erro, file=sys.stderr)
        return 1
    finally:
        con.close()
    return 0

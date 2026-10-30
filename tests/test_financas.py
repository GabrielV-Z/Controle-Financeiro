import os
import tempfile
import unittest
from datetime import date

from financas.banco import conectar
from financas.modelos import (
    ErroValidacao,
    Transacao,
    formatar_valor,
    parse_data,
    parse_mes,
    parse_valor,
)
from financas.servico import Financas


def nova(tipo="despesa", valor=1000, categoria="mercado", descricao="", data=date(2026, 10, 5)):
    return Transacao(tipo=tipo, valor=valor, categoria=categoria, descricao=descricao, data=data)


class TestModelos(unittest.TestCase):
    def test_parse_valor(self):
        self.assertEqual(parse_valor("12,50"), 1250)
        self.assertEqual(parse_valor("12.50"), 1250)
        self.assertEqual(parse_valor("R$ 1.234,56"), 123456)
        self.assertEqual(parse_valor("10"), 1000)
        self.assertEqual(parse_valor("0,005"), 1)

    def test_parse_valor_invalido(self):
        for texto in ("abc", "", "nan", "inf"):
            with self.assertRaises(ErroValidacao):
                parse_valor(texto)

    def test_formatar_valor(self):
        self.assertEqual(formatar_valor(123456), "R$ 1.234,56")
        self.assertEqual(formatar_valor(5), "R$ 0,05")
        self.assertEqual(formatar_valor(-2500), "-R$ 25,00")

    def test_parse_data_e_mes(self):
        self.assertEqual(parse_data("2026-10-05"), date(2026, 10, 5))
        self.assertEqual(parse_data("05/10/2026"), date(2026, 10, 5))
        self.assertEqual(parse_mes("2026-10"), (2026, 10))
        with self.assertRaises(ErroValidacao):
            parse_data("ontem")
        with self.assertRaises(ErroValidacao):
            parse_mes("2026-13")

    def test_validacao_transacao(self):
        with self.assertRaises(ErroValidacao):
            nova(tipo="outro")
        with self.assertRaises(ErroValidacao):
            nova(valor=0)
        with self.assertRaises(ErroValidacao):
            nova(categoria="   ")
        self.assertEqual(nova(categoria="  Mercado ").categoria, "mercado")


class TestServico(unittest.TestCase):
    def setUp(self):
        self.con = conectar(":memory:")
        self.f = Financas(self.con)

    def tearDown(self):
        self.con.close()

    def test_adicionar_listar_remover(self):
        t = self.f.adicionar(nova(descricao="feira"))
        self.assertIsNotNone(t.id)
        self.assertEqual(len(self.f.listar()), 1)
        self.assertTrue(self.f.remover(t.id))
        self.assertFalse(self.f.remover(t.id))
        self.assertEqual(self.f.listar(), [])

    def test_filtros(self):
        self.f.adicionar(nova(categoria="mercado", data=date(2026, 10, 1)))
        self.f.adicionar(nova(categoria="lazer", data=date(2026, 10, 2)))
        self.f.adicionar(nova(tipo="receita", categoria="salario", data=date(2026, 9, 30)))
        self.assertEqual(len(self.f.listar(categoria="Lazer")), 1)
        self.assertEqual(len(self.f.listar(mes=(2026, 10))), 2)
        self.assertEqual(len(self.f.listar(tipo="receita")), 1)
        self.assertEqual(len(self.f.listar(limite=2)), 2)

    def test_saldo(self):
        self.f.adicionar(nova(tipo="receita", valor=500000, categoria="salario"))
        self.f.adicionar(nova(valor=12000))
        self.assertEqual(self.f.saldo(), 488000)

    def test_resumo_mensal(self):
        self.f.adicionar(nova(tipo="receita", valor=300000, categoria="salario"))
        self.f.adicionar(nova(valor=20000, categoria="mercado"))
        self.f.adicionar(nova(valor=5000, categoria="mercado"))
        self.f.adicionar(nova(valor=8000, categoria="lazer"))
        self.f.adicionar(nova(valor=99999, categoria="outro", data=date(2026, 9, 1)))
        r = self.f.resumo_mensal((2026, 10))
        self.assertEqual(r.receitas, 300000)
        self.assertEqual(r.despesas, 33000)
        self.assertEqual(r.saldo, 267000)
        self.assertEqual(r.por_categoria, [("mercado", 25000), ("lazer", 8000)])

    def test_resumo_mes_vazio(self):
        r = self.f.resumo_mensal((2020, 1))
        self.assertEqual((r.receitas, r.despesas, r.por_categoria), (0, 0, []))

    def test_orcamentos(self):
        self.f.definir_orcamento("Mercado", 30000)
        self.f.definir_orcamento("lazer", 10000)
        self.f.adicionar(nova(valor=35000, categoria="mercado"))
        self.f.adicionar(nova(valor=2000, categoria="lazer"))
        situacao = {s.categoria: s for s in self.f.situacao_orcamentos((2026, 10))}
        self.assertTrue(situacao["mercado"].estourado)
        self.assertFalse(situacao["lazer"].estourado)
        self.assertAlmostEqual(situacao["lazer"].percentual, 20.0)
        self.f.definir_orcamento("mercado", 50000)
        situacao = {s.categoria: s for s in self.f.situacao_orcamentos((2026, 10))}
        self.assertFalse(situacao["mercado"].estourado)
        self.assertTrue(self.f.remover_orcamento("lazer"))
        self.assertFalse(self.f.remover_orcamento("lazer"))

    def test_orcamento_invalido(self):
        with self.assertRaises(ErroValidacao):
            self.f.definir_orcamento("mercado", 0)

    def test_csv_ida_e_volta(self):
        self.f.adicionar(nova(valor=1250, categoria="mercado", descricao="pao, leite"))
        self.f.adicionar(nova(tipo="receita", valor=100000, categoria="salario"))
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "dados.csv")
            self.assertEqual(self.f.exportar_csv(caminho), 2)
            outro = Financas(conectar(":memory:"))
            self.assertEqual(outro.importar_csv(caminho), 2)
            self.assertEqual(outro.saldo(), self.f.saldo())
            descricoes = {t.descricao for t in outro.listar()}
            self.assertIn("pao, leite", descricoes)

    def test_importar_csv_invalido_nao_grava_nada(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "ruim.csv")
            with open(caminho, "w", encoding="utf-8") as a:
                a.write("tipo,valor,categoria,descricao,data\n")
                a.write("despesa,10.00,mercado,ok,2026-10-01\n")
                a.write("despesa,xx,mercado,erro,2026-10-02\n")
            with self.assertRaises(ErroValidacao) as ctx:
                self.f.importar_csv(caminho)
            self.assertIn("linha 3", str(ctx.exception))
            self.assertEqual(self.f.listar(), [])


if __name__ == "__main__":
    unittest.main()

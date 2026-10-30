from .modelos import formatar_valor


def _montar(cabecalho, linhas, direita=()):
    larguras = [len(c) for c in cabecalho]
    for linha in linhas:
        for i, celula in enumerate(linha):
            larguras[i] = max(larguras[i], len(celula))

    def formatar(linha):
        partes = []
        for i, celula in enumerate(linha):
            partes.append(celula.rjust(larguras[i]) if i in direita else celula.ljust(larguras[i]))
        return "  ".join(partes).rstrip()

    separador = "  ".join("-" * l for l in larguras)
    return "\n".join([formatar(cabecalho), separador] + [formatar(l) for l in linhas])


def tabela_transacoes(transacoes):
    if not transacoes:
        return "Nenhuma transacao encontrada."
    linhas = []
    for t in transacoes:
        sinal = "+" if t.tipo == "receita" else "-"
        linhas.append(
            (
                str(t.id),
                t.data.strftime("%d/%m/%Y"),
                t.tipo,
                t.categoria,
                "%s %s" % (sinal, formatar_valor(t.valor)),
                t.descricao,
            )
        )
    cabecalho = ("ID", "Data", "Tipo", "Categoria", "Valor", "Descricao")
    return _montar(cabecalho, linhas, direita={0, 4})


def texto_resumo(resumo, rotulo, orcamentos):
    partes = [
        "Resumo de %s" % rotulo,
        "",
        "Receitas: %s" % formatar_valor(resumo.receitas),
        "Despesas: %s" % formatar_valor(resumo.despesas),
        "Saldo:    %s" % formatar_valor(resumo.saldo),
    ]
    if resumo.por_categoria:
        partes += ["", "Despesas por categoria"]
        linhas = []
        for categoria, total in resumo.por_categoria:
            parte = total * 100 / resumo.despesas
            linhas.append((categoria, formatar_valor(total), "%.1f%%" % parte))
        partes.append(_montar(("Categoria", "Total", "Parte"), linhas, direita={1, 2}))
    if orcamentos:
        partes += ["", "Orcamentos"]
        linhas = []
        for o in orcamentos:
            situacao = "ESTOURADO" if o.estourado else "ok"
            linhas.append(
                (
                    o.categoria,
                    formatar_valor(o.gasto),
                    formatar_valor(o.limite),
                    "%.0f%%" % o.percentual,
                    situacao,
                )
            )
        partes.append(
            _montar(("Categoria", "Gasto", "Limite", "Uso", "Situacao"), linhas, direita={1, 2, 3})
        )
    return "\n".join(partes)

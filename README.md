# Controle Financeiro

Aplicativo de terminal para controle de gastos pessoais. Registra receitas e despesas,
mostra o resumo do mes, acompanha orcamentos por categoria e importa/exporta CSV.
Usa apenas a biblioteca padrao do Python (3.9 ou superior) e guarda os dados em SQLite.

## Uso

Os comandos rodam a partir da pasta do projeto:

    python -m financas add receita 3500 salario -d "pagamento de outubro"
    python -m financas add despesa 89,90 mercado -d "feira da semana"
    python -m financas add despesa 45 lazer --data 28/10/2026
    python -m financas listar --mes 2026-10
    python -m financas resumo
    python -m financas saldo
    python -m financas remover 3

### Orcamentos

    python -m financas orcamento definir mercado 600
    python -m financas orcamento remover mercado
    python -m financas resumo --mes 2026-10

O resumo mostra quanto de cada limite ja foi usado e marca as categorias estouradas.

### CSV

    python -m financas exportar backup.csv
    python -m financas importar backup.csv

O arquivo deve ter o cabecalho `tipo,valor,categoria,descricao,data`. Se alguma linha for
invalida, nada e importado e o erro aponta o numero da linha.

## Onde ficam os dados

Por padrao em `~/.financas/dados.db`. Para usar outro arquivo, passe `--db caminho.db`
antes do comando ou defina a variavel de ambiente `FINANCAS_DB`.

## Valores

Aceita `12,50`, `12.50` e `1.234,56`. Internamente tudo e guardado em centavos (inteiros),
o que evita erros de arredondamento de ponto flutuante.

## Estrutura

    financas/
        modelos.py     validacao e conversao de valores, datas e meses
        banco.py       conexao e esquema do SQLite
        servico.py     regras: transacoes, resumo, orcamentos, CSV
        relatorio.py   formatacao das tabelas de saida
        cli.py         argumentos de linha de comando
    tests/
        test_financas.py

## Testes

    python -m unittest discover -s tests -t .

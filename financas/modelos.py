from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

TIPOS = ("receita", "despesa")
FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


class ErroValidacao(ValueError):
    pass


@dataclass(frozen=True)
class Transacao:
    tipo: str
    valor: int
    categoria: str
    descricao: str
    data: date
    id: Optional[int] = None

    def __post_init__(self):
        if self.tipo not in TIPOS:
            raise ErroValidacao("tipo deve ser 'receita' ou 'despesa'")
        if self.valor <= 0:
            raise ErroValidacao("o valor deve ser maior que zero")
        categoria = self.categoria.strip().lower()
        if not categoria:
            raise ErroValidacao("a categoria nao pode ser vazia")
        object.__setattr__(self, "categoria", categoria)
        object.__setattr__(self, "descricao", self.descricao.strip())


def parse_valor(texto):
    limpo = texto.strip().replace("R$", "").replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise ErroValidacao("valor invalido: %r" % texto)
    if not valor.is_finite():
        raise ErroValidacao("valor invalido: %r" % texto)
    centavos = (valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(centavos)


def formatar_valor(centavos):
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    milhar = "{:,}".format(reais).replace(",", ".")
    return "%sR$ %s,%02d" % (sinal, milhar, resto)


def valor_decimal(centavos):
    reais, resto = divmod(centavos, 100)
    return "%d.%02d" % (reais, resto)


def parse_data(texto):
    texto = texto.strip()
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErroValidacao("data invalida: %r (use AAAA-MM-DD ou DD/MM/AAAA)" % texto)


def parse_mes(texto):
    try:
        ano, mes = texto.strip().split("-")
        ano, mes = int(ano), int(mes)
    except ValueError:
        raise ErroValidacao("mes invalido: %r (use AAAA-MM)" % texto)
    if not 1 <= mes <= 12 or ano < 1:
        raise ErroValidacao("mes invalido: %r (use AAAA-MM)" % texto)
    return ano, mes

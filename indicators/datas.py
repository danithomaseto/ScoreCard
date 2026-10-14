"""Datas do export em formato brasileiro (dia/mes) ou americano (mes/dia).

O Summary nao entrega a data sempre do mesmo jeito: conforme o servidor
da operacao, a semana vem como celula de data de verdade, como texto
"06/09/2026" (dia/mes) ou como texto americano "9/6/26" (mes/dia). Lido
sempre como dia/mes, o "9/6/26" (6 de setembro) virava 9 de junho, o
"10/4/26" virava 10 de abril e o "9/13/26" nao virava nada — a semana
sumia do calculo.

Uma data sozinha como "9/6/26" nao diz qual e a ordem. Por isso a ordem
e decidida pela **coluna inteira**, que sai sempre do mesmo servidor:

1. Uma data que so existe numa das ordens ("9/13/26": nao ha mes 13)
   mostra a ordem do arquivo.
2. Sem nenhuma assim, vale a ordem em que as datas fazem sentido para o
   que a coluna e: na semana, todas no mesmo dia da semana que as datas
   ja certas da coluna (domingo ou segunda, que e onde o Summary comeca
   a semana); nos dias de pico, dentro do mes extraido.
3. Empate ainda: ano com 4 digitos e o formato brasileiro do portal
   ("06/09/2026"); com 2 digitos, o americano ("9/6/26").

Celula de data de verdade e data ISO ("2026-09-06") nao tem ambiguidade
e entram como vieram.
"""

import datetime
import re

DOMINGO, SEGUNDA = 6, 0
INICIOS_DE_SEMANA = (DOMINGO, SEGUNDA)

# dia/mes/ano ou mes/dia/ano (separador /, - ou .), com hora opcional
# depois ("9/6/26 00:00"); ou ano-mes-dia.
_DATA = re.compile(r"^\s*(\d{1,4})[/.\-](\d{1,2})[/.\-](\d{1,4})(?:[ T].*)?$")


def _montar(ano, mes, dia):
    try:
        return datetime.date(ano, mes, dia)
    except ValueError:
        return None


def _ano(texto):
    return int(texto) + 2000 if len(texto) <= 2 else int(texto)


def leituras(valor):
    """As formas de ler um valor: {"dmy": data, "mdy": data}.

    Quando so existe uma (ou as duas dao o mesmo dia), as duas chaves
    trazem a mesma data. Valor que nao e data devolve {}.
    """
    if isinstance(valor, datetime.datetime):
        return {"dmy": valor.date(), "mdy": valor.date()}
    if isinstance(valor, datetime.date):
        return {"dmy": valor, "mdy": valor}
    if valor is None or isinstance(valor, (int, float)):
        return {}
    achado = _DATA.match(str(valor))
    if not achado:
        return {}
    a, b, c = achado.groups()
    if len(a) == 4:  # ISO: ano-mes-dia
        data = _montar(int(a), int(b), int(c))
        return {"dmy": data, "mdy": data} if data else {}
    if len(c) not in (2, 4):
        return {}
    dmy = _montar(_ano(c), int(b), int(a))
    mdy = _montar(_ano(c), int(a), int(b))
    if dmy and mdy:
        return {"dmy": dmy, "mdy": mdy}
    if dmy or mdy:
        so = dmy or mdy
        return {"dmy": so, "mdy": so, "so": "dmy" if dmy else "mdy"}
    return {}


def e_data(valor):
    """O valor e uma data em alguma das formas?"""
    return bool(leituras(valor))


def _ambigua(lida):
    return lida and "so" not in lida and lida["dmy"] != lida["mdy"]


def _ano_curto(valor):
    achado = _DATA.match(str(valor)) if isinstance(valor, str) else None
    return bool(achado) and len(achado.group(1)) != 4 and len(achado.group(3)) == 2


def ordem(valores, nota):
    """"dmy" ou "mdy": a ordem das datas em texto de uma coluna.

    nota(datas, certas) da a pontuacao de uma leitura: datas sao as
    ambiguas lidas naquela ordem, certas as que nao tem duvida.
    """
    lidas = [(v, leituras(v)) for v in valores]
    pistas = {lida["so"] for _, lida in lidas if lida and "so" in lida}
    if len(pistas) == 1:
        return pistas.pop()

    ambiguas = [lida for _, lida in lidas if _ambigua(lida)]
    certas = [lida["dmy"] for _, lida in lidas if lida and not _ambigua(lida)]
    if ambiguas:
        dmy = nota([lida["dmy"] for lida in ambiguas], certas)
        mdy = nota([lida["mdy"] for lida in ambiguas], certas)
        if dmy != mdy:
            return "dmy" if dmy > mdy else "mdy"

    curtas = sum(_ano_curto(v) for v, lida in lidas if _ambigua(lida))
    return "mdy" if curtas * 2 > len(ambiguas) and ambiguas else "dmy"


def _converter(valores, nota):
    escolhida = ordem(valores, nota)
    convertidas = {}
    for valor in valores:
        lida = leituras(valor)
        if lida:
            convertidas[chave(valor)] = lida[escolhida]
    return convertidas


def chave(valor):
    """A chave de um valor nos dicionarios de semanas() e dias_do_mes()."""
    return valor if isinstance(valor, (datetime.date, str)) else repr(valor)


def _nota_de_semana(hoje):
    limite = hoje + datetime.timedelta(days=7)

    def nota(datas, certas):
        # O dia em que a semana comeca: o das datas certas da coluna, ou
        # domingo/segunda quando todas sao ambiguas.
        dias = {d.weekday() for d in certas} or set(INICIOS_DE_SEMANA)
        pontos = sum(2 for d in datas if d.weekday() in dias)
        pontos += sum(1 for d in datas if d.weekday() in INICIOS_DE_SEMANA)
        # Semana que ainda nao comecou nao pode estar no export.
        pontos -= sum(3 for d in datas if d > limite)
        return pontos

    return nota


def semanas(valores, hoje=None):
    """{valor: data ISO} da coluna de semana. Valor que nao e data fica
    de fora (a linha fica sem semana, como antes)."""
    nota = _nota_de_semana(hoje or datetime.date.today())
    return {chave: data.isoformat() for chave, data in _converter(list(valores), nota).items()}


def dias_do_mes(valores, mes):
    """{valor: date} de uma coluna de dias (Report Date), com o mes
    extraido ("2026-09") de pista: vale a ordem que poe os dias nele."""
    def nota(datas, certas):
        return sum(1 for d in datas if f"{d.year:04d}-{d.month:02d}" == mes)

    return _converter(list(valores), nota)


def mes_predominante(valores):
    """O mes ("2026-09") em que cai a maior parte de uma coluna de dias,
    na ordem (dia/mes ou mes/dia) que mais concentra as datas num mes so.
    Serve para o arquivo de Dias de Pico antigo, sem o periodo no nome."""
    melhor = (0, None)
    for ordem_ in ("dmy", "mdy"):
        contagem = {}
        for valor in valores:
            lida = leituras(valor)
            if lida:
                mes = lida[ordem_].strftime("%Y-%m")
                contagem[mes] = contagem.get(mes, 0) + 1
        if contagem:
            mes, quantos = max(contagem.items(), key=lambda item: (item[1], item[0]))
            if quantos > melhor[0]:
                melhor = (quantos, mes)
    return melhor[1]

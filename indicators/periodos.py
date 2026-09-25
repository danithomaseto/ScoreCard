"""Rotulos e contas de calendario dos periodos.

A semana **comeca no domingo**, que e o fechamento do Summary: a data
que vem no "Medium Level Group" e sempre um domingo. O numero da semana
serve so de rotulo e nao entra em calculo nenhum.
"""

from datetime import date, timedelta

MESES = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def numero_da_semana(data_iso):
    """Mesmo numero que o WEEKNUM do Excel no modo padrao, em que a
    semana comeca no domingo. Conferido: 30/08/2026 -> 36."""
    dia = date.fromisoformat(data_iso)
    primeiro_de_janeiro = date(dia.year, 1, 1)
    # weekday() do Python e segunda=0; aqui domingo precisa ser 0.
    domingo_base = (primeiro_de_janeiro.weekday() + 1) % 7
    dia_do_ano = (dia - primeiro_de_janeiro).days + 1
    return (dia_do_ano - 1 + domingo_base) // 7 + 1


def rotulo_semana(data_iso):
    """("Week 36", "30/08 a 05/09")."""
    inicio = date.fromisoformat(data_iso)
    fim = inicio + timedelta(days=6)
    return (
        f"Week {numero_da_semana(data_iso)}",
        f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')}",
    )


def rotulo_mes(chave, de=None, ate=None):
    """("Setembro", "01 a 19/09"). O subtitulo mostra o intervalo real
    extraido, porque o mes quase nunca vai ate o ultimo dia: a
    convencao e do dia 1 ate o ultimo sabado fechado."""
    ano, mes = chave.split("-")
    titulo = f"{MESES[int(mes) - 1]}"
    if int(ano) != date.today().year:
        titulo += f"/{ano}"

    if de and ate:
        inicio = date.fromisoformat(de)
        fim = date.fromisoformat(ate)
        return titulo, f"{inicio.strftime('%d')} a {fim.strftime('%d/%m')}"
    return titulo, ""


def semana_parcial(data_iso, de, ate):
    """A semana cabe inteira dentro do intervalo extraido?

    So da pra saber quando o intervalo foi digitado. Com o "Last Week"
    do relatorio, quem fecha a semana e ele, entao nao ha o que
    verificar.
    """
    if not de or not ate:
        return False
    inicio = date.fromisoformat(data_iso)
    fim = inicio + timedelta(days=6)
    return inicio < date.fromisoformat(de) or fim > date.fromisoformat(ate)


def mes_parcial(chave, de, ate):
    """O intervalo extraido para antes do fim do mes? So da pra saber com
    datas digitadas; o "Last Month" do relatorio ja e o mes fechado."""
    if not de or not ate:
        return False
    ano, mes = (int(p) for p in chave.split("-"))
    proximo = date(ano + (mes == 12), mes % 12 + 1, 1)
    return date.fromisoformat(ate) < proximo - timedelta(days=1)

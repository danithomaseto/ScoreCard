"""Presenteismo: periodos, roteamento das faltas e a formula.

Sao dois calendarios diferentes, de proposito:

- **Semanal** usa as semanas do mes vigente, de segunda a domingo,
  cortadas na virada do mes. A primeira e a ultima costumam ter menos
  dias uteis, e e isso que faz o denominador mudar de semana pra
  semana.
- **Resultado do mes** usa o ciclo da folha ponto, do dia 13 ao dia 12
  do mes seguinte. Nao e o mes do calendario.

Uma falta e roteada pela **data** para os dois ao mesmo tempo: o mesmo
arquivo alimenta a semana e o ciclo sem ser importado duas vezes.
"""

import calendar
import datetime

META_PADRAO = 0.98
HORAS_DIA_PADRAO = 8.0

MESES = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

DIA_DE_CORTE = 13  # a folha ponto vira no dia 13


def dias_uteis(inicio, fim):
    """Segunda a sexta entre as duas datas, inclusive."""
    if fim < inicio:
        return 0
    total = 0
    dia = inicio
    while dia <= fim:
        if dia.weekday() < 5:
            total += 1
        dia += datetime.timedelta(days=1)
    return total


def semanas_do_mes(ano, mes, hoje=None):
    """As semanas do mes, de segunda a domingo, cortadas na virada.

    Setembro/2026 sai assim: 01-06 (4 dias uteis), 07-13 (5), 14-20 (5),
    21-27 (5) e 28-30 (3) — o mes comeca numa terca e acaba numa quarta.
    """
    hoje = hoje or datetime.date.today()
    primeiro = datetime.date(ano, mes, 1)
    ultimo = datetime.date(ano, mes, calendar.monthrange(ano, mes)[1])

    semanas = []
    inicio = primeiro
    numero = 1
    while inicio <= ultimo:
        # domingo da semana em que "inicio" cai
        fim_semana = inicio + datetime.timedelta(days=6 - inicio.weekday())
        fim = min(fim_semana, ultimo)
        semanas.append({
            "id": f"{ano:04d}-{mes:02d}-S{numero}",
            "numero": numero,
            "rotulo": f"S{numero} · {inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')}",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "dias_uteis": dias_uteis(inicio, fim),
            "em_aberto": inicio <= hoje <= fim,
        })
        inicio = fim + datetime.timedelta(days=1)
        numero += 1
    return semanas


def _inicio_do_ciclo(dia):
    """O ciclo 13->12 a que uma data pertence comeca no dia 13 deste mes
    ou do mes anterior."""
    if dia.day >= DIA_DE_CORTE:
        return datetime.date(dia.year, dia.month, DIA_DE_CORTE)
    anterior = datetime.date(dia.year, dia.month, 1) - datetime.timedelta(days=1)
    return datetime.date(anterior.year, anterior.month, DIA_DE_CORTE)


def _somar_mes(dia, meses):
    ano = dia.year + (dia.month - 1 + meses) // 12
    mes = (dia.month - 1 + meses) % 12 + 1
    return datetime.date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def ciclo_de(data_iso):
    """Identificador do ciclo de folha ponto de uma data."""
    return _inicio_do_ciclo(datetime.date.fromisoformat(data_iso)).isoformat()


def ciclos_folha(hoje=None, anteriores=3):
    """Os ciclos 13->12, do mais recente pro mais antigo.

    O ciclo em andamento entra como "Em aberto" e conta **so os dias
    uteis ja decorridos** — senao o presenteismo de um ciclo que mal
    comecou apareceria despencando, porque as faltas ja aconteceram e os
    dias ainda nao.

    Passado o dia 12, o proximo ciclo ja aparece na lista, pronto pra
    receber lancamentos.
    """
    hoje = hoje or datetime.date.today()
    atual = _inicio_do_ciclo(hoje)

    inicios = [_somar_mes(atual, 1)]  # o proximo, ainda por abrir
    inicios += [_somar_mes(atual, -n) for n in range(0, anteriores + 1)]

    ciclos = []
    for inicio in inicios:
        fim = _somar_mes(inicio, 1) - datetime.timedelta(days=1)
        if hoje < inicio:
            status, uteis = f"Aberto em {inicio.strftime('%d/%m')}", 0
        elif hoje > fim:
            status, uteis = "Fechado", dias_uteis(inicio, fim)
        else:
            status, uteis = "Em aberto", dias_uteis(inicio, hoje)
        ciclos.append({
            "id": inicio.isoformat(),
            "rotulo": f"{inicio.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}",
            # O ano do inicio e sempre o do fim ou o anterior; repetir
            # os dois estourava a largura do seletor.
            "rotulo_curto": f"{inicio.strftime('%d/%m')} → {fim.strftime('%d/%m/%Y')}",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "status": status,
            "dias_uteis": uteis,
            "mes_referencia": f"{inicio.year:04d}-{inicio.month:02d}",
        })
    return ciclos


def semana_de(data_iso, hoje=None):
    """Identificador da semana do mes a que uma data pertence."""
    dia = datetime.date.fromisoformat(data_iso)
    for semana in semanas_do_mes(dia.year, dia.month, hoje=hoje):
        if semana["inicio"] <= data_iso <= semana["fim"]:
            return semana["id"]
    return None


def calcular(hc, dias, horas_dia, faltas):
    """Presenteismo = 1 - (faltas x horas/dia) / (hc x dias x horas/dia).

    As horas por dia se cancelam na conta, mas ficam na formula porque e
    assim que ela e conferida na reuniao: horas perdidas sobre horas
    disponiveis.
    """
    hc = hc or 0
    dias = dias or 0
    horas_dia = horas_dia or 0
    disponiveis = hc * dias * horas_dia
    if disponiveis <= 0:
        return None
    perdidas = (faltas or 0) * horas_dia
    return round(1 - (perdidas / disponiveis), 6)


def memoria(hc, dias, horas_dia, faltas):
    """Os numeros que a tela mostra ao lado da formula."""
    disponiveis = (hc or 0) * (dias or 0) * (horas_dia or 0)
    perdidas = (faltas or 0) * (horas_dia or 0)
    return {
        "horas_disponiveis": round(disponiveis, 2),
        "horas_perdidas": round(perdidas, 2),
        "horas_efetivas": round(disponiveis - perdidas, 2),
        "presenteismo": calcular(hc, dias, horas_dia, faltas),
    }


def contar_faltas(lancamentos, gestor=None, inicio=None, fim=None):
    """Dias de ausencia de um gestor dentro de um intervalo."""
    total = 0
    for item in lancamentos:
        if gestor and item["gestor"] != gestor:
            continue
        if inicio and item["data"] < inicio:
            continue
        if fim and item["data"] > fim:
            continue
        total += item.get("dias", 1)
    return total

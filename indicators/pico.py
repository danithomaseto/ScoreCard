"""Hora direta de pico: os 5 dias de maior hora direta do mes.

Vem da extracao "Dias de Pico": o Summary do mes com Group By 1 =
Report Date, uma linha por dia. A conta segue a planilha de referencia
(Calculo_ScoreCard.xlsx, aba Summary):

1. A hora direta de cada dia, com a mesma formula de sempre:
   (Measured Direct + Signon Direct + Insert Direct) / (Total - PD Brk).
2. Os 5 dias com a maior hora direta.
3. A hora direta de pico e **agregada**: soma as horas dos 5 dias e
   divide uma vez so — nao e a media das 5 porcentagens. Assim um dia
   com poucas horas (um sabado com meia duzia de pessoas) pesa pelo
   tamanho dele, e nao igual a um dia cheio.

Entram so os dias de trabalho da escala: segunda a sexta e, nas
operacoes de escala espanhola, os dois ultimos sabados do mes. Sabado
fora da escala e domingo ficam de fora mesmo com horas — e hora extra,
e hora extra nao entra. Tambem so contam os dias do mes da extracao.

Efetividade, dispersao e presenteismo do pico sao os do mes; so a hora
direta muda, e com ela o cubo.
"""

import datetime

from . import presenteismo

QUANTIDADE = 5


def _data(valor):
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    texto = str(valor or "").strip()
    # O portal exporta dd/mm/aaaa (e o formato da semana no export
    # semanal); os outros ficam de reserva.
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    return None


def calcular(linhas, mes, escala_espanhola=False, quantidade=QUANTIDADE):
    """linhas sao as do reader (a data vem em "detalhe"); mes e a chave
    "2026-09" do mes extraido.

    Devolve {"hora_direta", "dias", "dias_validos", "ignorados"}, com
    hora_direta None se nenhum dia valido tiver horas.
    """
    por_dia = {}
    ignorados = []
    for linha in linhas:
        dia = _data(linha.get("detalhe"))
        if dia is None:
            continue
        motivo = None
        if f"{dia.year:04d}-{dia.month:02d}" != mes:
            motivo = "fora do mes"
        elif not presenteismo.dia_util(dia, escala_espanhola):
            motivo = "domingo" if dia.weekday() == 6 else "sabado fora da escala"
        if motivo:
            ignorados.append({"data": dia.isoformat(), "motivo": motivo})
            continue

        soma = por_dia.setdefault(dia, {"diretas": 0.0, "base": 0.0})
        soma["diretas"] += sum(linha.get(c) or 0.0
                               for c in ("measured_direct", "signon_direct", "insert_direct"))
        soma["base"] += (linha.get("total") or 0.0) - (linha.get("pd_brk") or 0.0)

    dias = [
        {"data": dia.isoformat(), "hora_direta": s["diretas"] / s["base"],
         "horas_diretas": s["diretas"], "horas": s["base"]}
        for dia, s in por_dia.items() if s["base"] > 0
    ]
    # Maior hora direta primeiro; no empate, o dia mais cedo, para o
    # resultado nao depender da ordem das linhas no arquivo.
    dias.sort(key=lambda d: (-d["hora_direta"], d["data"]))
    escolhidos = dias[:quantidade]

    base = sum(d["horas"] for d in escolhidos)
    hora_direta = (sum(d["horas_diretas"] for d in escolhidos) / base) if base > 0 else None
    return {
        "hora_direta": round(hora_direta, 6) if hora_direta is not None else None,
        "dias": [{**d, "hora_direta": round(d["hora_direta"], 6)} for d in escolhidos],
        "dias_validos": len(dias),
        "ignorados": sorted(ignorados, key=lambda d: d["data"]),
    }

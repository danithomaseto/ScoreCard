"""A conta de cada indicador, para a dica ao passar o mouse na celula
(aba Inicio, Resultado Gestor e Resultado Turno).

Cada indicador e uma divisao (ou produto) de somas que ja estao
guardadas com o periodo: as horas do Summary (weekly.totais), as
pessoas dentro e fora da tolerancia, as horas disponiveis e perdidas do
presenteismo e as parcelas do coverage. Aqui elas viram texto em
portugues, com os numeros daquele periodo:

    {"formula": "Goal ÷ Measured Direct",
     "conta": "1.234,5 h ÷ 1.200,0 h = 102,88%"}

Sem as parcelas (extracao antiga, que nao guardava as somas), fica so a
formula.
"""

from indicators import limits

FORMULAS = {
    "efetividade": "Goal ÷ Measured Direct",
    "hora_direta": "(Measured Direct + Signon Direct + Insert Direct) ÷ (Total − PD Brk)",
    "hora_direta_pico": "Horas diretas ÷ horas trabalhadas nos dias de pico",
    "dispersao": "Pessoas com Var entre −10 e +10 ÷ pessoas com Goal e Measured Direct",
    "presenteismo": "1 − (Faltas × Horas/dia) ÷ (HC × Dias úteis × Horas/dia)",
    "cubo": "Efetividade × Hora direta × Presenteísmo",
    "coverage": "(Horas LMS − Diretas sem meta) ÷ (Horas Metrics + Sinergia recebida − Sinergia cedida)",
}


def horas(valor):
    """1234.5 -> "1.234,5 h"."""
    texto = f"{valor:,.1f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{texto} h"


def _numeros(entrada, *campos):
    valores = [entrada.get(c) for c in campos]
    return None if any(v is None for v in valores) else valores


def explicar(indicador, entrada, periodo="week"):
    """{"formula", "conta"} da celula, ou None sem numero."""
    entrada = entrada or {}
    valor = entrada.get(indicador)
    if valor is None:
        return None
    resultado = limits.formatar(valor)
    chave = "hora_direta_pico" if indicador == "hora_direta" and periodo == "peak" else indicador
    dica = {"formula": FORMULAS[chave], "conta": ""}

    if indicador == "efetividade":
        n = _numeros(entrada, "soma_goal", "soma_measured_direct")
        if n:
            dica["conta"] = f"{horas(n[0])} ÷ {horas(n[1])} = {resultado}"
    elif indicador == "hora_direta" and periodo == "peak":
        dias = entrada.get("_dias_pico") or []
        if dias and all("horas_diretas" in d and "horas" in d for d in dias):
            diretas = sum(d["horas_diretas"] for d in dias)
            base = sum(d["horas"] for d in dias)
            dica["conta"] = f"{horas(diretas)} ÷ {horas(base)} em {len(dias)} dias = {resultado}"
    elif indicador == "hora_direta":
        n = _numeros(entrada, "soma_measured_direct", "soma_signon_direct", "soma_insert_direct",
                     "soma_total", "soma_pd_brk")
        if n:
            diretas = n[0] + n[1] + n[2]
            dica["conta"] = f"{horas(diretas)} diretas ÷ {horas(n[3] - n[4])} = {resultado}"
    elif indicador == "dispersao":
        n = _numeros(entrada, "dentro", "fora")
        if n:
            total = n[0] + n[1]
            dica["conta"] = f"{n[0]} de {total} pessoas = {resultado}"
    elif indicador == "presenteismo":
        partes = entrada.get("_presenteismo_partes") or {}
        n = _numeros(partes, "horas_perdidas", "horas_disponiveis")
        if n:
            dica["conta"] = f"1 − {horas(n[0])} perdidas ÷ {horas(n[1])} disponíveis = {resultado}"
    elif indicador == "cubo":
        n = _numeros(entrada, "efetividade", "hora_direta", "presenteismo")
        if n:
            dica["conta"] = " × ".join(limits.formatar(v) for v in n) + f" = {resultado}"
    elif indicador == "coverage":
        partes = entrada.get("_coverage_partes") or {}
        n = _numeros(partes, "lms", "diretas_sem_meta", "metrics", "recebida", "cedida")
        if n:
            # Sinergia so aparece na conta quando ha.
            base = horas(n[2])
            if n[3]:
                base += f" + {horas(n[3])} recebida"
            if n[4]:
                base += f" − {horas(n[4])} cedida"
            if n[3] or n[4]:
                base = f"({base})"
            dica["conta"] = f"({horas(n[0])} − {horas(n[1])}) ÷ {base} = {resultado}"
    return dica

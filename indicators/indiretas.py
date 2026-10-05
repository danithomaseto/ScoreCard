"""Horas indiretas por semana, a partir do export Week + Job Code.

Reproduz a planilha de referencia (Indicadores Score, aba HD). As
colunas da planilha sao as mesmas letras do export:

    H = Unmeasured Signon Indirect  ("HORAS LOGADAS")
    K = PD Brk                      ("BRIEFING")
    L = Total
    M = UnPd Brk                    ("REFEICAO")

- Atividade (Job Code) e **indireta** quando H, K ou M e diferente de
  zero.
- Horas da atividade indireta = H + K + M.
- Horas totais da semana = soma de L + M de todas as atividades (a
  refeicao nao entra no Total do relatorio; sem somar o M, as horas de
  LUNCH ficariam fora do total).
- % = horas / horas totais da semana.

Conferido com a planilha, semana de 06/09/2026: 715,26 h totais, 135,88
h indiretas, 19,00%.

Nada de I/O aqui: entram as linhas do reader, sai o resultado.
"""

from .limits import LIMITE_INDIRETAS


def _horas(linha, campo):
    return linha.get(campo) or 0.0


def e_indireta(linha):
    return any(_horas(linha, campo) != 0 for campo in ("signon_indirect", "pd_brk", "unpd_brk"))


def horas_indiretas(linha):
    return _horas(linha, "signon_indirect") + _horas(linha, "pd_brk") + _horas(linha, "unpd_brk")


def horas_totais(linha):
    return _horas(linha, "total") + _horas(linha, "unpd_brk")


def _dividir(parte, todo):
    return round(parte / todo, 6) if todo else None


def da_semana(linhas):
    """{"horas_totais", "horas_indiretas", "percentual", "atividades"} de um
    conjunto de linhas (uma semana). atividades vem da maior para a
    menor, cada uma com horas, % do total e % das indiretas."""
    total = sum(horas_totais(l) for l in linhas)
    por_atividade = {}
    for linha in linhas:
        if not e_indireta(linha):
            continue
        atividade = (linha.get("detalhe") or "").strip() or "(sem código)"
        por_atividade[atividade] = por_atividade.get(atividade, 0.0) + horas_indiretas(linha)
    indiretas = sum(por_atividade.values())
    atividades = [{
        "atividade": atividade,
        "horas": round(horas, 2),
        "percentual": _dividir(horas, total),
        "percentual_indiretas": _dividir(horas, indiretas),
    } for atividade, horas in sorted(por_atividade.items(), key=lambda item: (-item[1], item[0]))]
    return {
        "horas_totais": round(total, 2),
        "horas_indiretas": round(indiretas, 2),
        "percentual": _dividir(indiretas, total),
        "atividades": atividades,
    }


def por_semana(linhas):
    """{"2026-09-06": da_semana(...)}, uma entrada por semana do export.
    Linha sem semana fica de fora."""
    grupos = {}
    for linha in linhas:
        if linha.get("semana"):
            grupos.setdefault(linha["semana"], []).append(linha)
    return {semana: da_semana(grupo) for semana, grupo in sorted(grupos.items())}


def cor(percentual):
    """Verde ate o limite (15%); acima dele ja e ruim: vermelho."""
    if percentual is None:
        return None
    return "vermelho" if percentual > LIMITE_INDIRETAS else "verde"

"""Indicadores por gestor ou por turno (abas Resultado Gestor e
Resultado Turno).

As mesmas contas da operacao (weekly.totais), so que feitas para as
linhas de cada gestor ou turno: o export traz um nivel a mais de
agrupamento (Week > Supervisor > User ID, ou Supervisor > User ID no
mes) e o "grupo" de cada linha e o nome que veio na coluna B, igual a
planilha.

Nenhum I/O aqui: entram as linhas do reader e sai o resultado.
"""

from . import coverage, weekly

# Rotulo do grupo sem nome: gente sem supervisor ("," no export) ou sem
# turno (celula vazia).
SEM_NOME = {"gestor": "Sem supervisor", "turno": "Sem turno"}


def sem_nome(nome):
    return not (nome or "").replace(",", "").strip()


def rotulo(nome, dimensao):
    """O nome como veio da planilha; o grupo vazio ganha um rotulo."""
    return SEM_NOME.get(dimensao, "Sem grupo") if sem_nome(nome) else nome


def por_grupo(linhas):
    """{grupo: totais do grupo + "cobertura"} de um conjunto de linhas.

    "cobertura" sao as horas (LMS e diretas sem meta) dos usuarios que
    ficam nesse grupo para o coverage: cada usuario num grupo so, o que
    tem mais horas dele (coverage.grupo_principal), com todas as horas
    dele no periodo.
    """
    grupos = {}
    for linha in linhas:
        grupos.setdefault(linha.get("grupo") or "", []).append(linha)
    principal = coverage.grupo_principal(linhas)
    horas = coverage.por_usuario(linhas)
    resultado = {}
    for nome, do_grupo in grupos.items():
        totais = weekly.totais(do_grupo, nivel_detalhe="User ID")
        totais["cobertura"] = {
            usuario: {k: v for k, v in h.items() if k != "gestor"}
            for usuario, h in horas.items() if principal.get(usuario, "") == nome
        }
        resultado[nome] = totais
    return resultado


def por_semana_e_grupo(linhas):
    """{semana: {grupo: ...}} do export com Week no primeiro nivel."""
    semanas = {}
    for linha in linhas:
        if linha.get("semana"):
            semanas.setdefault(linha["semana"], []).append(linha)
    return {semana: por_grupo(grupo) for semana, grupo in sorted(semanas.items())}

"""Coverage por usuario: quanto das horas que a pessoa deveria trabalhar
aparece no LMS.

    Coverage = (Horas LMS - Diretas sem meta)
               / (Horas Metrics + Sinergia recebida - Sinergia cedida)

- Horas LMS: a coluna "Total" do export (K no mensal, L no semanal).
- Diretas sem meta: "Unmeasured Signon Direct" (F no mensal, G no
  semanal). As colunas sao achadas pelo titulo, como no resto do app.
- Horas Metrics: o que a pessoa deveria ter trabalhado = dias x horas.
  Os dias vem dos dias uteis do periodo e as horas de HORAS_PADRAO
  (8,75); os dois podem ser trocados por usuario na tela.
- Sinergia cedida e recebida: horas digitadas na tela.

O total usa as somas das colunas, nunca a media dos percentuais.
Conferido com a planilha de referencia (Indicadores Score, aba
COVERAGE W): ESANTOS 43,40 / 43,75 = 99,2%.
"""

HORAS_PADRAO = 8.75

CAMPOS_MANUAIS = ("dias", "horas", "cedida", "recebida")


def por_usuario(linhas):
    """{usuario: {"lms", "diretas_sem_meta"}} de um conjunto de linhas do
    reader (a coluna do usuario e o "detalhe": o segundo nivel no
    semanal, o primeiro no mensal)."""
    usuarios = {}
    for linha in linhas:
        usuario = (linha.get("detalhe") or "").strip()
        if not usuario:
            continue
        soma = usuarios.setdefault(usuario, {"lms": 0.0, "diretas_sem_meta": 0.0})
        soma["lms"] += linha.get("total") or 0.0
        soma["diretas_sem_meta"] += linha.get("signon_direct") or 0.0
    return {u: {k: round(v, 4) for k, v in s.items()} for u, s in usuarios.items()}


def por_semana_e_usuario(linhas):
    """{semana: {usuario: {...}}} do export semanal."""
    semanas = {}
    for linha in linhas:
        if linha.get("semana"):
            semanas.setdefault(linha["semana"], []).append(linha)
    return {semana: por_usuario(grupo) for semana, grupo in semanas.items()}


def _dividir(numerador, denominador):
    if not denominador or denominador <= 0:
        return None
    return round(numerador / denominador, 6)


def calcular(lms, diretas_sem_meta, metrics, cedida=0.0, recebida=0.0):
    return _dividir(lms - diretas_sem_meta, metrics + (recebida or 0.0) - (cedida or 0.0))


def linha(usuario, horas_lms, manuais, dias_padrao, horas_padrao=HORAS_PADRAO):
    """Uma linha da tela: o que veio do export, o que foi digitado e o
    coverage. manuais e {"dias", "horas", "cedida", "recebida"} com so o
    que foi digitado para esse usuario."""
    manuais = manuais or {}
    dias = manuais.get("dias", dias_padrao)
    horas = manuais.get("horas", horas_padrao)
    cedida = manuais.get("cedida", 0.0)
    recebida = manuais.get("recebida", 0.0)
    metrics = round(dias * horas, 4)
    return {
        "usuario": usuario,
        "lms": horas_lms["lms"],
        "diretas_sem_meta": horas_lms["diretas_sem_meta"],
        "dias": dias,
        "dias_origem": "digitado" if "dias" in manuais else "calendario",
        "horas": horas,
        "horas_origem": "digitado" if "horas" in manuais else "padrao",
        "metrics": metrics,
        "cedida": cedida,
        "recebida": recebida,
        "coverage": calcular(horas_lms["lms"], horas_lms["diretas_sem_meta"], metrics, cedida, recebida),
    }


def total(linhas, sinergia_operacao=None):
    """A linha de total: soma das colunas de horas e o coverage delas.

    A sinergia e, em geral, conhecida so por operacao (horas cedidas a
    outra operacao ou recebidas dela), nao por pessoa: sinergia_operacao
    ({"cedida", "recebida"}) entra aqui, somada ao que tiver sido
    digitado por usuario."""
    soma = {campo: round(sum(l[campo] for l in linhas), 4)
            for campo in ("lms", "diretas_sem_meta", "metrics", "cedida", "recebida")}
    sinergia_operacao = sinergia_operacao or {}
    soma["cedida_usuarios"], soma["recebida_usuarios"] = soma["cedida"], soma["recebida"]
    soma["cedida_operacao"] = round(sinergia_operacao.get("cedida", 0.0), 4)
    soma["recebida_operacao"] = round(sinergia_operacao.get("recebida", 0.0), 4)
    soma["cedida"] = round(soma["cedida"] + soma["cedida_operacao"], 4)
    soma["recebida"] = round(soma["recebida"] + soma["recebida_operacao"], 4)
    soma["usuarios"] = len(linhas)
    soma["coverage"] = calcular(soma["lms"], soma["diretas_sem_meta"], soma["metrics"],
                                soma["cedida"], soma["recebida"])
    return soma

"""Monta as abas Resultado Gestor e Resultado Turno.

Igual a aba Inicio, so que uma tabela por gestor (ou turno): os seis
indicadores nas linhas, as semanas do mes nas colunas e o mes no fim.
As semanas vem da extracao Gestor · Week (ou Turno · Week) e o mes da
Gestor · Month (ou Turno · Month).

- EFETIVIDADE, HORA DIRETA e DISPERSAO: as linhas do grupo no export,
  com as mesmas contas da operacao.
- PRESENTEISMO (so gestor): o do Headcount, quando o nome do gestor no
  Headcount e o mesmo da planilha. Nome diferente nao puxa nada.
- CUBO: EFETIVIDADE x HORA DIRETA x PRESENTEISMO.
- COVERAGE: as horas dos usuarios do grupo sobre dias x horas de cada
  um, com os dias e horas digitados na aba Coverage (sem a sinergia, que
  e da operacao inteira).

Turno nao tem presenteismo (o Headcount e por gestor), entao o
presenteismo e o cubo nao se aplicam a ele.
"""

import datetime

import coverage_store
import coverage_tela
import grupos_store
import headcount
import settings_store
from config.operations import OPERATIONS
from indicators import coverage, grupos, limits, periodos
from indicators.weekly import calcular_cubo

TITULOS = {"gestor": "Resultado Gestor", "turno": "Resultado Turno"}
SINGULAR = {"gestor": "gestor", "turno": "turno"}


def _operacao_padrao(dimensao):
    """A primeira operacao com alguma extracao desta aba; senao a
    primeira da lista."""
    dados = grupos_store.ler()[dimensao]
    return next((op for op in OPERATIONS if dados.get(op)), next(iter(OPERATIONS)))


def _meses(guardado, hoje):
    meses = {hoje.strftime("%Y-%m")}
    for chave_guardada in guardado:
        tipo, chave_periodo = chave_guardada.split(":", 1)
        meses |= periodos.meses_das_semanas(chave_periodo) if tipo == "week" else {chave_periodo}
    return sorted(meses, reverse=True)


def _colunas(guardado, mes):
    """As semanas que tem algum dia no mes e o mes, como na aba Inicio."""
    colunas = []
    semanas = sorted(c.split(":", 1)[1] for c in guardado
                     if c.startswith("week:") and periodos.semana_no_mes(c.split(":", 1)[1], mes))
    for chave in semanas:
        entrada = guardado[grupos_store.chave("week", chave)]
        titulo, subtitulo = periodos.rotulo_semana(chave)
        colunas.append({"chave": chave, "periodo": "week", "titulo": titulo, "subtitulo": subtitulo,
                        "parcial": bool(entrada.get("parcial")), "_entrada": entrada})
    entrada_mes = guardado.get(grupos_store.chave("month", mes))
    if entrada_mes:
        titulo, subtitulo = periodos.rotulo_mes(mes, entrada_mes.get("de"), entrada_mes.get("ate"))
        colunas.append({"chave": mes, "periodo": "month", "titulo": titulo, "subtitulo": subtitulo,
                        "parcial": False, "_entrada": entrada_mes})
    return colunas


def _coverage(operacao, coluna, cobertura):
    """Coverage do grupo no periodo: as horas dos usuarios dele sobre dias
    x horas de cada um (digitados na aba Coverage, ou o calendario)."""
    if not cobertura:
        return None
    entrada = coluna["_entrada"]
    dias = coverage_tela._dias_uteis(operacao, coluna["periodo"], coluna["chave"],
                                     entrada.get("de"), entrada.get("ate"))
    digitados = coverage_store.manuais(operacao, coverage_store.chave(coluna["periodo"], coluna["chave"]))
    linhas = [coverage.linha(usuario, horas, digitados.get(usuario), dias)
              for usuario, horas in cobertura.items()]
    return coverage.total(linhas)["coverage"]


def _celula(indicador, valor, nao_se_aplica=False):
    if nao_se_aplica:
        # A copia guarda a posicao vazia: o valor de baixo nao sobe.
        return {"texto": "", "cor": "", "nao_se_aplica": True, "copia_vazia": True}
    return {"texto": limits.formatar(valor), "cor": limits.cor(indicador, valor)}


def _tabela(dimensao, operacao, nome, colunas, presenteismo):
    linhas = []
    valores_por_coluna = []
    for coluna in colunas:
        totais = coluna["_entrada"]["grupos"].get(nome)
        if totais is None:
            valores_por_coluna.append(None)
            continue
        pres = None
        if presenteismo is not None:
            vivo = presenteismo[coluna["periodo"]].get(coluna["chave"])
            pres = vivo["presenteismo"] if vivo else None
        valores_por_coluna.append({
            "efetividade": totais.get("efetividade"),
            "hora_direta": totais.get("hora_direta"),
            "dispersao": totais.get("dispersao"),
            "presenteismo": pres,
            "cubo": calcular_cubo(totais.get("efetividade"), totais.get("hora_direta"), pres),
            "coverage": _coverage(operacao, coluna, totais.get("cobertura")),
            "usuarios": totais.get("linhas", 0),
        })
    sem_presenteismo = dimensao == "turno"
    for indicador in limits.ORDEM:
        celulas = []
        for valores in valores_por_coluna:
            fora = sem_presenteismo and indicador in ("presenteismo", "cubo")
            celulas.append(_celula(indicador, (valores or {}).get(indicador), fora))
        linhas.append({
            "chave": indicador,
            "rotulo": limits.ROTULOS[indicador],
            "meta": "não se aplica ao turno" if sem_presenteismo and indicador in ("presenteismo", "cubo")
            else limits.METAS[indicador],
            "celulas": celulas,
        })
    return linhas, [v["usuarios"] if v else None for v in valores_por_coluna]


def montar(dimensao, operacao=None, mes=None, hoje=None):
    if dimensao not in grupos_store.DIMENSOES:
        raise ValueError("Dimensão inválida.")
    hoje = hoje or datetime.date.today()
    operacao = operacao if operacao in OPERATIONS else _operacao_padrao(dimensao)
    guardado = grupos_store.da_operacao(dimensao, operacao)
    meses = _meses(guardado, hoje)
    mes = mes if mes in meses else hoje.strftime("%Y-%m")

    colunas = _colunas(guardado, mes)
    nomes = sorted({nome for c in colunas for nome in c["_entrada"]["grupos"]},
                   key=lambda n: (grupos.sem_nome(n), grupos.rotulo(n, dimensao).casefold()))
    ocultos = set(settings_store.get_grupos_ocultos(dimensao, operacao))

    lista = []
    tabelas = []
    for nome in nomes:
        vinculado = (dimensao == "gestor"
                     and bool(headcount.gestores_do_headcount(operacao, nome)))
        visivel = nome not in ocultos
        lista.append({"id": nome, "rotulo": grupos.rotulo(nome, dimensao),
                      "visivel": visivel, "vinculado": vinculado})
        if not visivel:
            continue
        presenteismo = None
        if dimensao == "gestor":
            presenteismo = headcount.presenteismo_do_gestor(
                operacao, nome, hoje=hoje,
                semanas=[c["chave"] for c in colunas if c["periodo"] == "week"],
                meses=[c["chave"] for c in colunas if c["periodo"] == "month"])
        linhas, usuarios = _tabela(dimensao, operacao, nome, colunas, presenteismo)
        tabelas.append({
            "id": nome,
            "rotulo": grupos.rotulo(nome, dimensao),
            "vinculado": vinculado,
            "usuarios": usuarios,
            "linhas": linhas,
        })

    quando = max((c["_entrada"].get("extraido_em") or "" for c in colunas), default="")
    for coluna in colunas:
        coluna.pop("_entrada")
    return {
        "dimensao": dimensao,
        "titulo": TITULOS[dimensao],
        "singular": SINGULAR[dimensao],
        "operacoes": [{"key": k, "label": v["label"]} for k, v in OPERATIONS.items()],
        "operacao": operacao,
        "operacao_rotulo": OPERATIONS[operacao]["label"],
        "meses": [{"id": m, "rotulo": periodos.rotulo_mes_ano(m)} for m in meses],
        "mes": mes,
        "mes_rotulo": periodos.rotulo_mes_ano(mes),
        "colunas": colunas,
        "grupos": lista,
        "tabelas": tabelas,
        "ultima_extracao": (datetime.datetime.fromisoformat(quando).strftime("Extração de %d/%m %H:%M")
                            if quando else None),
    }


def definir_visiveis(dimensao, operacao, da_tela, visiveis):
    """Guarda quem a pessoa escondeu entre os grupos da tela (da_tela):
    os que nao estao em visiveis. Quem foi escondido em outro mes e nao
    aparece nesta tela continua como estava."""
    if dimensao not in grupos_store.DIMENSOES:
        raise ValueError("Dimensão inválida.")
    if operacao not in OPERATIONS:
        raise ValueError("Operação inválida.")
    da_tela = set(da_tela or [])
    visiveis = set(visiveis or []) & da_tela
    ocultos = (set(settings_store.get_grupos_ocultos(dimensao, operacao)) - da_tela) | (da_tela - visiveis)
    settings_store.set_grupos_ocultos(dimensao, operacao, ocultos)

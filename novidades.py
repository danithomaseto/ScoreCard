"""O que ha de novo em cada versao e o tour do primeiro uso.

Ao abrir o app, a tela pergunta o estado():

- quem nunca usou (sem tour visto, sem novidades vistas e sem nenhuma
  extracao no historico) ganha o tour curto da aba Inicio;
- quem ja usava e abre uma versao nova ve a janela "O que ha de novo"
  daquela versao, uma vez so.

O que foi visto fica no settings.json desta maquina ("vistos"). Os dois
reabrem em Configuracoes > Ajuda, quantas vezes a pessoa quiser.

Para uma versao nova: acrescente a entrada dela no topo de NOVIDADES,
com o mesmo numero do arquivo VERSAO.
"""

import history_store
import settings_store
import versao

# Versao -> lista de (titulo, texto). Curto: a janela mostra tudo de uma vez.
NOVIDADES = {
    "V.01.1": [
        ("Visual novo",
         "Filtros com a lista no visual do app (com ponto verde nas operações que têm dados no mês), "
         "login e abertura redesenhados, ícone em cada página e Configurações organizadas por seção."),
        ("Resumo no topo da Início",
         "Quantos indicadores estão na meta no mês, o melhor, o pior e a comparação com o mês anterior."),
        ("Seu nome na barra amarela",
         "Clique nele para abrir Configurações, os atalhos, as novidades e o Sair — que saíram do menu lateral."),
        ("Arquivos do SharePoint para todo mundo",
         "A Início mostra o relatório que já está na pasta do SharePoint, mesmo que você não "
         "tenha extraído, com a data do arquivo mais novo ao lado da última extração."),
        ("Headcount e Coverage compartilhados",
         "Quadro, faltas e lançamentos do Coverage vão para a pasta do SharePoint e aparecem "
         "para os outros gestores da operação."),
        ("A conta de cada indicador",
         "Pare o mouse (ou o foco do teclado) num número da tabela: aparece a fórmula e a "
         "conta com os números daquele período."),
        ("Procurar com Ctrl+K",
         "Digite \"hughes setembro\", \"coverage\" ou \"tema\" e vá direto para a tela ou a "
         "ação, sem passar pelo menu."),
        ("Tabela como imagem",
         "O botão Imagem na Início copia a tabela dos indicadores como figura, pronta para "
         "colar no PowerPoint."),
        ("Mais leve",
         "A extração usa o Edge do Windows, as telas já montadas ficam guardadas até os "
         "dados mudarem e há o modo leve em Configurações > Aparência."),
        ("Telas pequenas e TV",
         "Tabelas com cabeçalho e primeira coluna fixos, e o modo apresentação se ajusta à "
         "altura da tela: enche a TV e cabe no notebook com o Windows em 125%."),
    ],
}


def da_versao(numero):
    """[{"titulo", "texto"}] da versao (lista vazia se nao houver)."""
    return [{"titulo": titulo, "texto": texto} for titulo, texto in NOVIDADES.get(numero, [])]


def _ja_usava():
    """Ja extraiu alguma vez nesta maquina (ou ja configurou a pasta)."""
    return bool(history_store.get_history()) or bool(settings_store.get_sharepoint_folder())


def estado():
    """O que mostrar ao abrir o app:
    {"versao", "itens", "mostrar": None | "tour" | "novidades", "tour_visto"}."""
    numero = versao.info()["versao"]
    itens = da_versao(numero)
    vistos = settings_store.get_vistos()
    mostrar = None
    if not vistos["tour"] and not vistos["novidades"] and not _ja_usava():
        mostrar = "tour"
    elif itens and vistos["novidades"] != numero:
        mostrar = "novidades"
    return {"versao": numero, "itens": itens, "mostrar": mostrar, "tour_visto": vistos["tour"]}


def marcar(o_que):
    """Marca como visto: "novidades" (as da versao atual) ou "tour"."""
    if o_que == "novidades":
        settings_store.marcar_visto("novidades", versao.info()["versao"])
    elif o_que == "tour":
        settings_store.marcar_visto("tour", True)
        # Quem acabou de fazer o tour ja conhece a versao atual.
        settings_store.marcar_visto("novidades", versao.info()["versao"])
    else:
        raise ValueError("Marca inválida.")
    return estado()

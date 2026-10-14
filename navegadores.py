"""Qual navegador a automacao usa.

O .exe levava um Chromium embutido (o chromium-headless-shell), que era
mais da metade do tamanho dele. Todo Windows 10/11 ja tem o Microsoft
Edge, que e um Chromium: a automacao passa a usar o Edge da maquina, e o
.exe fica bem menor e abre mais rapido na primeira vez de cada versao.

Ordem de tentativa (o primeiro que abrir e usado ate o app fechar):

1. Microsoft Edge da maquina;
2. Google Chrome da maquina, se o Edge nao abrir;
3. o Chromium embutido, so na versao completa do .exe
   (SCORECARD_BUILD_COM_CHROMIUM=1 no build) ou rodando do codigo-fonte
   com "playwright install chromium".

O Playwright abre o navegador com um perfil temporario proprio: nao mexe
no perfil, nos favoritos nem nas senhas de quem usa o computador.

SCORECARD_NAVEGADOR=edge|chrome|chromium forca um deles (diagnostico e
testes). PLAYWRIGHT_CHROMIUM_EXECUTABLE aponta um executavel especifico.
"""

import logging
import os
import sys
import threading

log = logging.getLogger("scorecard.navegadores")

# (chave, nome na tela, canal do Playwright)
NAVEGADORES = (
    ("edge", "Microsoft Edge", "msedge"),
    ("chrome", "Google Chrome", "chrome"),
    ("chromium", "Chromium embutido", None),
)
NOMES = {chave: nome for chave, nome, _ in NAVEGADORES}

# Nomes do executavel dentro da pasta de cada Chromium do Playwright
# ("chrome-win", "chrome-headless-shell-win64"...), que mudam conforme a
# versao.
EXECUTAVEIS_DO_CHROMIUM = (
    "chrome.exe", "headless_shell.exe", "chrome-headless-shell.exe",
    "chrome", "headless_shell", "chrome-headless-shell",
)

MENSAGEM_SEM_NAVEGADOR = (
    "Não encontrei um navegador para a automação: o Score Card usa o Microsoft Edge "
    "(ou o Google Chrome) deste computador. Peça à TI para instalar ou reparar o Edge, "
    "ou use a versão completa do Score Card, que leva o próprio navegador."
)

_escolhido = None  # chave do que abriu da ultima vez
_trava = threading.Lock()


class SemNavegador(RuntimeError):
    pass


# ---------------- Onde estao ----------------

def _caminhos_do_windows(*partes):
    raizes = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    return [os.path.join(raiz, *partes) for raiz in raizes if raiz]


def _instalado(chave):
    """Caminho do Edge/Chrome desta maquina, ou None. Fora do Windows nao
    procura (o Playwright acha sozinho ao tentar abrir)."""
    if os.name != "nt":
        return None
    partes = {
        "edge": ("Microsoft", "Edge", "Application", "msedge.exe"),
        "chrome": ("Google", "Chrome", "Application", "chrome.exe"),
    }[chave]
    return next((c for c in _caminhos_do_windows(*partes) if os.path.isfile(c)), None)


def chromium_embutido():
    """Ha um Chromium do Playwright no pacote (versao completa) ou baixado
    por "playwright install chromium"? So olha o disco."""
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        return os.path.isfile(os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"])
    raizes = []
    if hasattr(sys, "_MEIPASS"):
        raizes.append(os.path.join(sys._MEIPASS, "playwright", "driver", "package", ".local-browsers"))
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        raizes.append(os.environ["PLAYWRIGHT_BROWSERS_PATH"])
    if os.environ.get("LOCALAPPDATA"):
        raizes.append(os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright"))
    for raiz in raizes:
        if not os.path.isdir(raiz):
            continue
        for nome in os.listdir(raiz):
            if not nome.startswith(("chromium-", "chromium_headless_shell-")):
                continue
            pasta = os.path.join(raiz, nome)
            for sub in os.listdir(pasta):
                caminho = os.path.join(pasta, sub)
                if os.path.isdir(caminho) and any(
                        os.path.isfile(os.path.join(caminho, exe)) for exe in EXECUTAVEIS_DO_CHROMIUM):
                    return True
    return False


def ordem():
    """As chaves na ordem em que serao tentadas."""
    forcado = (os.environ.get("SCORECARD_NAVEGADOR") or "").strip().lower()
    if forcado in NOMES:
        return [forcado]
    chaves = [chave for chave, _, _ in NAVEGADORES]
    if _escolhido in chaves:
        chaves.remove(_escolhido)
        chaves.insert(0, _escolhido)
    return chaves


def disponiveis():
    """[{"chave", "nome", "caminho"}] do que existe nesta maquina, na ordem
    de tentativa. No Windows confere o disco; fora dele, Edge e Chrome
    entram sem caminho (so abrindo para saber)."""
    achados = []
    for chave in ordem():
        if chave == "chromium":
            if chromium_embutido():
                achados.append({"chave": chave, "nome": NOMES[chave], "caminho": ""})
            continue
        caminho = _instalado(chave)
        if caminho or os.name != "nt":
            achados.append({"chave": chave, "nome": NOMES[chave], "caminho": caminho or ""})
    return achados


def descricao():
    """Para a saude do sistema e o diagnostico: o navegador que sera
    usado ({"chave", "nome", "caminho"}) ou None."""
    achados = disponiveis()
    return achados[0] if achados else None


def nome_do_escolhido():
    return NOMES.get(_escolhido, "")


# ---------------- Abrir ----------------

def _abrir(playwright, chave, headless):
    if chave == "chromium":
        if headless:
            try:
                return playwright.chromium.launch(headless=True)
            except Exception as exc:  # noqa: BLE001
                if "Executable doesn't exist" not in str(exc):
                    raise
        return playwright.chromium.launch(headless=headless, channel="chromium")
    canal = next(c for k, _, c in NAVEGADORES if k == chave)
    return playwright.chromium.launch(headless=headless, channel=canal)


def lancar(playwright, headless=True):
    """Abre o primeiro navegador da ordem que funcionar e lembra dele.
    Sem nenhum, levanta SemNavegador com a mensagem para a tela."""
    global _escolhido
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        return playwright.chromium.launch(headless=headless,
                                          executable_path=os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"])
    falhas = []
    for chave in ordem():
        if os.name == "nt" and chave in ("edge", "chrome") and not _instalado(chave):
            continue
        if chave == "chromium" and not chromium_embutido() and getattr(sys, "frozen", False):
            continue
        try:
            navegador = _abrir(playwright, chave, headless)
        except Exception as exc:  # noqa: BLE001 - tenta o proximo
            falhas.append(f"{NOMES[chave]}: {str(exc).splitlines()[0][:160]}")
            continue
        with _trava:
            if _escolhido != chave:
                log.info("navegador da automação: %s", NOMES[chave])
            _escolhido = chave
        return navegador
    for falha in falhas:
        log.warning("navegador não abriu - %s", falha)
    raise SemNavegador(MENSAGEM_SEM_NAVEGADOR)

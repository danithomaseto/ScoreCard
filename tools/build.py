"""Gera o dist\\ScoreCard.exe. Chamado pelo build.bat, com o Python do venv.

Cada passo para o build no primeiro erro e diz a causa provavel e o que
fazer; tudo o que aparece na tela vai tambem para build.log, que e o
arquivo para mandar a quem da suporte.

O PyInstaller gera numa pasta a parte (dist_novo) e so no fim ela vira o
dist: um build que falha nao apaga o .exe que ja estava la.

    python tools\\build.py                 instala as dependencias e gera
    python tools\\build.py --sem-instalar  so gera (dependencias ja instaladas)

O .exe padrao usa o Edge da maquina na automacao (navegadores.py). Com
SCORECARD_BUILD_COM_CHROMIUM=1 sai a versao completa, com um Chromium
embutido de reserva (maior).
"""

import datetime
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(RAIZ, "build.log")
DIST = os.path.join(RAIZ, "dist")
NOVO = os.path.join(RAIZ, "dist_novo")
TRABALHO = os.path.join(RAIZ, "build")
EXECUTAVEL = "ScoreCard.exe" if os.name == "nt" else "ScoreCard"

# Versoes testadas. O pywebview usa o pythonnet no Windows, que ainda nao
# tem versao para Python mais novo que o 3.13.
PYTHON_MINIMO = (3, 10)
PYTHON_MAXIMO = (3, 13)

# (trecho da mensagem de erro, causa provavel e o que fazer). A primeira
# que aparecer na saida do passo que falhou e a mostrada.
DICAS = [
    ("autoteste falhou",
     "O app gerado nao passou no autoteste (falta um modulo ou arquivo da tela no pacote). Se alguem "
     "mexeu na lista EXCLUIDOS do build.spec, tire de la o modulo citado acima; senao apague a pasta "
     "venv e rode de novo."),
    ("pythonnet",
     "O pywebview (a janela do app) precisa do pythonnet, que nao instala nesta versao do Python. "
     "Instale o Python 3.12 (python.org, marcando \"Add python.exe to PATH\"), apague a pasta venv "
     "e rode o build.bat de novo."),
    ("tkinter",
     "O Python foi instalado sem o Tcl/Tk, que o PyInstaller usa na tela de abertura do .exe. "
     "Abra o instalador do Python > Modify > marque \"tcl/tk and IDLE\" > Next > Install, e rode "
     "o build.bat de novo."),
    ("nao encontrei chromium_headless_shell",
     "O Chromium do Playwright nao foi baixado. Confira a internet (ou o proxy da empresa) e rode "
     "o build.bat de novo; ele tenta baixar outra vez."),
    ("could not find a version that satisfies",
     "O pip nao achou o pacote: sem internet, proxy bloqueando o PyPI ou versao do Python sem "
     "suporte. Teste abrir https://pypi.org no navegador; na rede da empresa, rode fora da VPN ou "
     "peca a liberacao do proxy."),
    ("ssl",
     "Falha de certificado/SSL ao baixar (proxy da empresa inspecionando o trafego). Rode fora da "
     "VPN ou em outra rede."),
    ("winerror 32",
     "Um arquivo esta preso por outro programa. Feche o ScoreCard.exe (e janelas do Explorer na "
     "pasta dist), espere o OneDrive/antivirus terminar e rode de novo."),
    ("permissionerror",
     "Sem permissao para gravar um arquivo. Feche o ScoreCard.exe e janelas do Explorer na pasta "
     "dist; se a pasta do projeto estiver no OneDrive, pause a sincronizacao durante o build."),
    ("access is denied",
     "Sem permissao para gravar um arquivo. Feche o ScoreCard.exe e janelas do Explorer na pasta "
     "dist; se o antivirus bloqueou, peca a TI para liberar a pasta do projeto."),
    ("acesso negado",
     "Sem permissao para gravar um arquivo. Feche o ScoreCard.exe e janelas do Explorer na pasta "
     "dist; se o antivirus bloqueou, peca a TI para liberar a pasta do projeto."),
    ("no space left",
     "Disco cheio. O build precisa de uns 2 GB livres."),
    ("espaco insuficiente",
     "Disco cheio. O build precisa de uns 2 GB livres."),
    ("no module named",
     "Falta um pacote no ambiente. Apague a pasta venv e rode o build.bat de novo (ele reinstala tudo)."),
]


class BuildFalhou(Exception):
    pass


def dica_para(saida):
    """A causa provavel de um erro, pelo texto que o passo mostrou."""
    minusculo = saida.lower()
    return next((dica for trecho, dica in DICAS if trecho in minusculo), None)


def registrar(texto=""):
    print(texto, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(texto + "\n")


def falhar(passo, saida=""):
    registrar("")
    registrar("=" * 64)
    registrar(f" O BUILD PAROU EM: {passo}")
    registrar("=" * 64)
    dica = dica_para(saida)
    registrar(dica or "Causa nao reconhecida: veja as ultimas linhas acima.")
    registrar(f"Registro completo: {LOG}")
    if os.path.isfile(os.path.join(DIST, EXECUTAVEL)):
        registrar("O dist\\ScoreCard.exe anterior continua la, sem mudanca.")
    raise BuildFalhou(passo)


def rodar(passo, comando):
    """Roda um passo mostrando a saida na tela e no build.log. Erro para o build."""
    registrar("")
    registrar(f"--- {passo} ---")
    saida = []
    try:
        processo = subprocess.Popen(comando, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        falhar(passo, str(exc))
    with processo, open(LOG, "a", encoding="utf-8") as fh:
        for linha in processo.stdout:
            sys.stdout.write(linha)
            sys.stdout.flush()
            fh.write(linha)
            saida.append(linha)
    if processo.returncode != 0:
        falhar(passo, "".join(saida[-80:]))
    return "".join(saida)


def com_chromium():
    return "1" in (os.environ.get("SCORECARD_BUILD_COM_CHROMIUM"), os.environ.get("SCORECARD_BUILD_FULL_CHROMIUM"))


def conferir_python():
    versao = sys.version_info[:2]
    registrar(f"Python {sys.version.split()[0]} em {sys.executable}")
    if not PYTHON_MINIMO <= versao <= PYTHON_MAXIMO:
        registrar(f"AVISO: o build foi testado com o Python {PYTHON_MINIMO[0]}.{PYTHON_MINIMO[1]} a "
                  f"{PYTHON_MAXIMO[0]}.{PYTHON_MAXIMO[1]}; com o {versao[0]}.{versao[1]} pode faltar pacote. "
                  "Se der erro, instale o Python 3.12.")
    try:
        import tkinter  # noqa: F401 - so confere se existe (tela de abertura do .exe)
    except ImportError as exc:
        falhar("conferir o Python", f"tkinter: {exc}")


def remover(pasta, passo):
    if not os.path.exists(pasta):
        return
    try:
        shutil.rmtree(pasta)
    except OSError as exc:
        falhar(passo, f"{type(exc).__name__}: {exc}")


def trocar_o_dist():
    """dist_novo vira dist. O antigo so sai depois que o novo esta pronto."""
    antigo = DIST + "_antigo"
    remover(antigo, "trocar o dist")
    try:
        if os.path.exists(DIST):
            os.replace(DIST, antigo)
        os.replace(NOVO, DIST)
    except OSError as exc:
        if not os.path.exists(DIST) and os.path.exists(antigo):
            os.replace(antigo, DIST)
        falhar("trocar o dist", f"{type(exc).__name__}: {exc} (o .exe novo ficou em dist_novo)")
    remover(antigo, "apagar o dist antigo")


def main(argumentos):
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write(f"Build do Score Card - {datetime.datetime.now():%d/%m/%Y %H:%M:%S}\n")
    registrar(f"Pasta do projeto: {RAIZ}")
    registrar("Versao: " + ("completa, com Chromium embutido" if com_chromium()
                            else "leve, usa o Edge da maquina (SCORECARD_BUILD_COM_CHROMIUM=1 gera a completa)"))
    conferir_python()

    if "--sem-instalar" not in argumentos:
        rodar("Instalando as dependencias (pip)",
              [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"])
        if com_chromium():
            rodar("Baixando o Chromium de reserva (Playwright)",
                  [sys.executable, "-m", "playwright", "install", "chromium"])

    remover(NOVO, "limpar o build anterior")
    remover(TRABALHO, "limpar o build anterior")
    rodar("Gerando o executavel (PyInstaller: app + lancador)",
          [sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm",
           "--distpath", NOVO, "--workpath", TRABALHO])

    gerado = os.path.join(NOVO, EXECUTAVEL)
    if not os.path.isfile(gerado):
        falhar("conferir o executavel gerado", f"O PyInstaller terminou sem criar {gerado}.")
    trocar_o_dist()

    final = os.path.join(DIST, EXECUTAVEL)
    registrar("")
    registrar("=" * 64)
    registrar(f" Pronto: {final}")
    registrar(f" {os.path.getsize(final) / 1024 / 1024:.0f} MB. Esse arquivo sozinho e o que se distribui.")
    registrar("=" * 64)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BuildFalhou:
        sys.exit(1)
    except KeyboardInterrupt:
        registrar("Build interrompido.")
        sys.exit(1)

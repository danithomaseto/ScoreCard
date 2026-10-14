"""Gera o dist\\ScoreCard.exe. Chamado pelo build.bat, com o Python do venv.

Cada passo para o build no primeiro erro e diz a causa provavel e o que
fazer; tudo o que aparece na tela vai tambem para build.log, que e o
arquivo para mandar a quem da suporte.

O PyInstaller trabalha numa pasta temporaria, fora da pasta do projeto
(que costuma estar no OneDrive: sincronizar milhares de arquivos do app
em pasta deixava arquivo preso e sobra no dist). Dali, so o
ScoreCard.exe vai para o dist, e o que mais estiver no dist (a pasta
ScoreCardApp com o _internal de um build antigo, por exemplo) e apagado:
no fim o dist tem um arquivo so. Um build que falha nao mexe no .exe que
ja estava la.

    python tools\\build.py                 instala as dependencias e gera
    python tools\\build.py --sem-instalar  so gera (dependencias ja instaladas)

O .exe padrao usa o Edge da maquina na automacao (navegadores.py). Com
SCORECARD_BUILD_COM_CHROMIUM=1 sai a versao completa, com um Chromium
embutido de reserva (maior).
"""

import datetime
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(RAIZ, "build.log")
DIST = os.path.join(RAIZ, "dist")
EXECUTAVEL = "ScoreCard.exe" if os.name == "nt" else "ScoreCard"
# Fora do projeto (e do OneDrive). SCORECARD_BUILD_TEMP troca o lugar, se o
# disco do TEMP estiver cheio.
TEMPORARIA = os.environ.get("SCORECARD_BUILD_TEMP") or os.path.join(tempfile.gettempdir(), "ScoreCard_build")
TRABALHO = os.path.join(TEMPORARIA, "trabalho")
SAIDA = os.path.join(TEMPORARIA, "saida")
# Sobras de builds antigos dentro do projeto, que eram geradas ali.
SOBRAS_ANTIGAS = [os.path.join(RAIZ, nome) for nome in ("build", "dist_novo", "dist_antigo")]

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


def _tirar_somente_leitura(funcao, caminho, _erro):
    """Arquivo marcado como somente leitura nao se apaga no Windows."""
    os.chmod(caminho, stat.S_IWRITE)
    funcao(caminho)


def _com_paciencia(acao, tentativas=8, espera=0.5):
    """O OneDrive e o antivirus seguram por um instante o arquivo recem-
    criado: tenta de novo algumas vezes antes de desistir."""
    for tentativa in range(tentativas):
        try:
            return acao()
        except OSError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(espera * (tentativa + 1))


def apagar(caminho):
    """Apaga arquivo ou pasta, com paciencia. Erro so se nao der mesmo."""
    if os.path.isdir(caminho) and not os.path.islink(caminho):
        if sys.version_info >= (3, 12):
            _com_paciencia(lambda: shutil.rmtree(caminho, onexc=_tirar_somente_leitura))
        else:
            _com_paciencia(lambda: shutil.rmtree(caminho, onerror=_tirar_somente_leitura))
    elif os.path.lexists(caminho):
        def _arquivo():
            try:
                os.remove(caminho)
            except PermissionError:
                os.chmod(caminho, stat.S_IWRITE)
                os.remove(caminho)
        _com_paciencia(_arquivo)


def remover(pasta, passo):
    if not os.path.lexists(pasta):
        return
    try:
        apagar(pasta)
    except OSError as exc:
        falhar(passo, f"{type(exc).__name__}: {exc}")


def colocar_no_dist(gerado):
    """Deixa no dist so o .exe novo. Ele e copiado ao lado do antigo e so
    entao toma o lugar dele (troca de um arquivo so, sem janela em que o
    dist fica vazio); depois sai tudo o que nao for ele. Devolve o que
    nao deu para apagar."""
    os.makedirs(DIST, exist_ok=True)
    final = os.path.join(DIST, EXECUTAVEL)
    temporario = final + ".novo"
    try:
        apagar(temporario)
        shutil.copy2(gerado, temporario)
        _com_paciencia(lambda: os.replace(temporario, final))
    except OSError as exc:
        try:
            apagar(temporario)
        except OSError:
            pass
        falhar("colocar o .exe no dist", f"{type(exc).__name__}: {exc}")
    sobras = []
    for nome in sorted(os.listdir(DIST)):
        if nome == EXECUTAVEL:
            continue
        try:
            apagar(os.path.join(DIST, nome))
        except OSError:
            sobras.append(nome)
    return sobras


def limpar_sobras_antigas():
    """build, dist_novo e dist_antigo na pasta do projeto, de builds de
    antes. Se algum estiver preso, fica para o proximo build."""
    for caminho in SOBRAS_ANTIGAS:
        try:
            apagar(caminho)
        except OSError as exc:
            registrar(f"Aviso: nao consegui apagar {caminho} ({exc}); fica para o proximo build.")


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

    limpar_sobras_antigas()
    registrar(f"Pasta de trabalho (temporaria): {TEMPORARIA}")
    remover(TEMPORARIA, "limpar o build anterior")
    rodar("Gerando o executavel (PyInstaller: app + lancador)",
          [sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm",
           "--distpath", SAIDA, "--workpath", TRABALHO])

    gerado = os.path.join(SAIDA, EXECUTAVEL)
    if not os.path.isfile(gerado):
        falhar("conferir o executavel gerado", f"O PyInstaller terminou sem criar {gerado}.")
    sobras = colocar_no_dist(gerado)
    try:
        apagar(TEMPORARIA)  # ~1 GB do app em pasta, que ja esta dentro do .exe
    except OSError:
        pass

    final = os.path.join(DIST, EXECUTAVEL)
    registrar("")
    registrar("=" * 64)
    registrar(f" Pronto: {final}")
    registrar(f" {os.path.getsize(final) / 1024 / 1024:.0f} MB, um arquivo so, sem mais nada junto:")
    registrar(" e esse arquivo sozinho que se distribui.")
    if sobras:
        registrar("")
        registrar(f" ATENCAO: sobrou no dist {', '.join(sobras)}, que o OneDrive ou o antivirus")
        registrar(" esta segurando. Nao faz parte do app: feche o Explorer nessa pasta e apague,")
        registrar(" ou rode o build de novo.")
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

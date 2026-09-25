"""Lancador do ScoreCard.exe: descompacta o app uma vez so.

O ScoreCard.exe que se distribui e este lancador, pequeno, com o app
inteiro (Python, interface, Playwright e Chromium) guardado dentro dele
num zip. Na primeira abertura de cada versao, o zip e descompactado em
%LOCALAPPDATA%\\ScoreCard\\app-<versao>; da segunda em diante, o
lancador ve que a pasta ja esta pronta e so abre o app.

Antes, no "arquivo unico" puro do PyInstaller, TODO o conteudo era
descompactado numa pasta temporaria a cada abertura e apagado ao
fechar — era isso que fazia o programa demorar pra abrir.

Onde o zip fica: entre o executavel do lancador e o pacote do
PyInstaller, que tem que ser a ultima coisa do arquivo (o PyInstaller
acha o proprio pacote lendo o final do arquivo, e o Windows ignora o
que vem depois do executavel propriamente dito). Logo antes do pacote
vai um rodape fixo com o tamanho do zip e a versao. Quem monta isso e
tools/empacotar.py, no fim do build.

Seguranca contra falhas: o zip e descompactado numa pasta temporaria
e so renomeado para a pasta final depois de completo, com um arquivo
".pronto" dentro. Se a descompactacao for interrompida (PC desligou,
disco cheio), a proxima abertura refaz do zero.
"""

import io
import logging
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile

MARCA = b"SCAPP001"
# marca, tamanho do zip, versao (12 caracteres + preenchimento)
RODAPE = struct.Struct("<8sQ16s")
# Rodape do pacote do PyInstaller: magic, tamanho do pacote, posicao e
# tamanho do indice, versao do Python, nome da DLL do Python.
COOKIE_PYINSTALLER = struct.Struct("!8sIIII64s")
NOME_DO_APP = "ScoreCardApp.exe" if os.name == "nt" else "ScoreCardApp"
PRONTO = ".pronto"

log = logging.getLogger("scorecard.lancador")


def _magic_pyinstaller():
    # Montado em tempo de execucao, e nao escrito por extenso, pelo mesmo
    # motivo que o PyInstaller faz assim: o padrao escrito no codigo
    # poderia ser encontrado por engano ao procurar o pacote no arquivo.
    return b"MEI" + bytes((0x0C, 0x0B, 0x0A, 0x0B, 0x0E))


def inicio_do_pacote_pyinstaller(fh):
    """Posicao, no arquivo, onde comeca o pacote do PyInstaller."""
    fh.seek(0, os.SEEK_END)
    tamanho = fh.tell()
    janela = min(tamanho, 1024 * 1024)
    fh.seek(tamanho - janela)
    fim = fh.read(janela)
    posicao = fim.rfind(_magic_pyinstaller())
    if posicao < 0:
        raise ValueError("Pacote do PyInstaller nao encontrado no executavel.")
    campos = COOKIE_PYINSTALLER.unpack(fim[posicao:posicao + COOKIE_PYINSTALLER.size])
    tamanho_do_pacote = campos[1]
    return tamanho - janela + posicao + COOKIE_PYINSTALLER.size - tamanho_do_pacote


def localizar_app(caminho_exe):
    """(inicio do zip, tamanho do zip, versao) dentro do executavel."""
    with open(caminho_exe, "rb") as fh:
        inicio_pacote = inicio_do_pacote_pyinstaller(fh)
        fh.seek(inicio_pacote - RODAPE.size)
        marca, tamanho, versao = RODAPE.unpack(fh.read(RODAPE.size))
    if marca != MARCA:
        raise ValueError("Este executavel nao traz o app dentro.")
    return inicio_pacote - RODAPE.size - tamanho, tamanho, versao.rstrip(b"\0").decode("ascii")


class _Trecho(io.RawIOBase):
    """Um pedaco de um arquivo visto como se fosse um arquivo inteiro:
    e assim que o zipfile le o zip que esta no meio do executavel."""

    def __init__(self, fh, inicio, tamanho):
        super().__init__()
        self._fh, self._inicio, self._tamanho, self._pos = fh, inicio, tamanho, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self._pos

    def seek(self, deslocamento, de_onde=os.SEEK_SET):
        base = {os.SEEK_SET: 0, os.SEEK_CUR: self._pos, os.SEEK_END: self._tamanho}[de_onde]
        self._pos = max(0, min(self._tamanho, base + deslocamento))
        return self._pos

    def readinto(self, destino):
        quanto = min(len(destino), self._tamanho - self._pos)
        if quanto <= 0:
            return 0
        self._fh.seek(self._inicio + self._pos)
        lido = self._fh.readinto(memoryview(destino)[:quanto])
        self._pos += lido
        return lido


def pasta_base():
    raiz = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(raiz, "ScoreCard")


def pasta_da_versao(versao):
    return os.path.join(pasta_base(), f"app-{versao}")


def esta_pronta(pasta):
    return os.path.isfile(os.path.join(pasta, PRONTO))


def preparar(caminho_exe, avisar=lambda pct: None):
    """Garante a pasta do app desta versao e devolve o caminho dela."""
    inicio, tamanho, versao = localizar_app(caminho_exe)
    destino = pasta_da_versao(versao)
    if esta_pronta(destino):
        return destino

    log.info("primeira abertura da versao %s: descompactando em %s", versao, destino)
    os.makedirs(pasta_base(), exist_ok=True)
    temporaria = f"{destino}.tmp-{os.getpid()}"
    shutil.rmtree(temporaria, ignore_errors=True)
    inicio_relogio = time.monotonic()

    with open(caminho_exe, "rb") as fh, zipfile.ZipFile(_Trecho(fh, inicio, tamanho)) as zipado:
        itens = zipado.infolist()
        total = sum(item.file_size for item in itens) or 1
        feito, ultimo = 0, -1
        for item in itens:
            caminho = zipado.extract(item, temporaria)
            modo = (item.external_attr >> 16) & 0o777
            if modo and os.name != "nt":
                os.chmod(caminho, modo)  # o zipfile nao restaura o "executavel"
            feito += item.file_size
            pct = feito * 100 // total
            if pct != ultimo:
                avisar(pct)
                ultimo = pct

    with open(os.path.join(temporaria, PRONTO), "w", encoding="utf-8") as fh:
        fh.write(versao)

    # Sem ".pronto", o que houver no destino e sobra de uma tentativa
    # interrompida.
    if os.path.isdir(destino) and not esta_pronta(destino):
        shutil.rmtree(destino, ignore_errors=True)
    try:
        os.replace(temporaria, destino)
    except OSError:
        # Outra abertura ao mesmo tempo terminou antes; vale a dela.
        shutil.rmtree(temporaria, ignore_errors=True)
        if not esta_pronta(destino):
            raise

    log.info("versao %s pronta em %.1fs", versao, time.monotonic() - inicio_relogio)
    limpar_versoes_antigas(versao)
    return destino


def limpar_versoes_antigas(versao_atual):
    """Apaga as pastas de versoes anteriores, para nao acumular algumas
    centenas de MB a cada atualizacao. Uma pasta em uso (app antigo
    ainda aberto) fica para a proxima vez."""
    atual = os.path.basename(pasta_da_versao(versao_atual))
    try:
        nomes = os.listdir(pasta_base())
    except OSError:
        return
    for nome in nomes:
        if not nome.startswith("app-") or nome == atual:
            continue
        caminho = os.path.join(pasta_base(), nome)
        if ".tmp-" in nome and time.time() - os.path.getmtime(caminho) < 3600:
            continue  # pode ser outra abertura descompactando agora
        shutil.rmtree(caminho, ignore_errors=True)


def abrir_app(pasta, argumentos=()):
    """Abre o app e devolve (processo, arquivo de sinal).

    O app cria o arquivo de sinal quando a janela termina de carregar
    (main.py); ate la o lancador mantem a tela de abertura na frente.
    """
    sinal = os.path.join(tempfile.gettempdir(), f"scorecard-pronto-{os.getpid()}")
    ambiente = dict(os.environ)
    # O app tambem e um executavel do PyInstaller: sem isto ele herdaria
    # o ambiente do lancador e tentaria usar a pasta temporaria dele.
    ambiente["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    ambiente["SCORECARD_SINAL_PRONTO"] = sinal
    opcoes = {}
    if os.name == "nt":
        opcoes["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    processo = subprocess.Popen(
        [os.path.join(pasta, NOME_DO_APP), *argumentos],
        cwd=pasta,
        env=ambiente,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **opcoes,
    )
    return processo, sinal


def esperar_janela(processo, sinal, limite=120):
    """True quando a janela do app carregou; False se o app fechou antes."""
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if os.path.exists(sinal):
            try:
                os.remove(sinal)
            except OSError:
                pass
            return True
        if processo.poll() is not None:
            return processo.returncode == 0
        time.sleep(0.1)
    return True  # demorou demais; deixa o app seguir sozinho


def _splash(texto=None, fechar=False):
    if "_PYI_SPLASH_IPC" not in os.environ:
        return  # sem tela de abertura (rodando do codigo, ou ja fechada)
    try:
        import pyi_splash  # so existe dentro do .exe com tela de abertura
    except ImportError:
        return
    try:
        if fechar:
            pyi_splash.close()
        elif texto is not None:
            pyi_splash.update_text(texto)
    except Exception:
        pass


def _mensagem(texto):
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, texto, "Score Card", 0x10)
            return
        except Exception:
            pass
    saida = sys.stderr or sys.__stderr__
    if saida is not None:  # no .exe sem console nao ha onde escrever
        print(texto, file=saida)


def main():
    import registro

    registro.configurar()
    caminho_exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
    try:
        pasta = preparar(
            caminho_exe,
            avisar=lambda pct: _splash(f"Preparando a primeira abertura desta versao... {pct}%"),
        )
        processo, sinal = abrir_app(pasta, sys.argv[1:])
    except Exception as exc:  # noqa: BLE001 - qualquer falha vira mensagem
        log.exception("o lancador nao conseguiu abrir o app")
        _splash(fechar=True)
        _mensagem(
            "Nao foi possivel abrir o Score Card.\n\n"
            f"{exc}\n\n"
            f"Detalhes em {os.path.join(registro.pasta(), 'scorecard.log')}"
        )
        return 1

    abriu = esperar_janela(processo, sinal)
    _splash(fechar=True)
    if not abriu:
        log.error("o app fechou antes de abrir a janela (codigo %s)", processo.returncode)
        _mensagem(
            "O Score Card fechou ao abrir.\n\n"
            f"Detalhes em {os.path.join(registro.pasta(), 'scorecard.log')}"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

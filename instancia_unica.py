"""Uma janela so do Score Card por usuario do Windows.

Duas janelas abertas gravam nos mesmos arquivos de dados (headcount,
coverage, indicadores): o que uma salva, a outra sobrescreve com a copia
antiga que tinha na memoria. Entao a segunda abertura nao abre nada — so
traz para a frente a janela que ja esta aberta.

Quem marca "tem um aberto" e um mutex nomeado do Windows, criado pelo
app e liberado pelo proprio Windows quando o processo termina (mesmo se
ele travar ou for encerrado a forca: nao sobra trava perdida, como
sobraria com um arquivo). "Local\\" deixa um por sessao, para duas pessoas
no mesmo servidor de terminal poderem usar cada uma o seu.

Fora do Windows (testes, desenvolvimento) nada disso se aplica.
"""

import logging
import os

log = logging.getLogger("scorecard.instancia")

NOME_DO_MUTEX = "Local\\ScoreCard-DHL-janela-unica"
TITULO_DA_JANELA = "Score Card"
# Processos que podem ser dono da janela: o app empacotado ou o Python,
# rodando do codigo-fonte. Uma pasta do Explorer chamada "Score Card"
# tem o mesmo titulo e nao pode ser confundida com o app.
PROCESSOS_DO_APP = ("scorecardapp.exe", "python.exe", "pythonw.exe")

ERRO_JA_EXISTE = 183  # ERROR_ALREADY_EXISTS
SYNCHRONIZE = 0x00100000
CONSULTA_LIMITADA = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
SW_RESTORE = 9

_mutex = None  # fica aberto ate o processo terminar


def _windows():
    return os.name == "nt"


def _kernel32():
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.OpenMutexW.restype = wintypes.HANDLE
    kernel32.OpenMutexW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    return kernel32


def _ultimo_erro():
    import ctypes

    return ctypes.get_last_error()


def ja_aberto():
    """True se o app ja esta aberto nesta sessao. So consulta: quem
    segura a marca e o app (segurar), nao o lancador."""
    if not _windows():
        return False
    try:
        kernel32 = _kernel32()
        handle = kernel32.OpenMutexW(SYNCHRONIZE, False, NOME_DO_MUTEX)
        if handle:
            kernel32.CloseHandle(handle)
            return True
    except Exception:  # noqa: BLE001 - na duvida, deixa abrir
        log.exception("nao consegui consultar se o app ja esta aberto")
    return False


def segurar():
    """Marca este processo como a janela do Score Card. False se outro
    ja estava marcado (este deve fechar)."""
    global _mutex
    if not _windows():
        return True
    try:
        kernel32 = _kernel32()
        handle = kernel32.CreateMutexW(None, False, NOME_DO_MUTEX)
        if handle and _ultimo_erro() == ERRO_JA_EXISTE:
            kernel32.CloseHandle(handle)
            return False
        _mutex = handle
    except Exception:  # noqa: BLE001 - na duvida, deixa abrir
        log.exception("nao consegui marcar a janela unica")
    return True


def _nome_do_processo(user32, kernel32, hwnd):
    import ctypes
    from ctypes import wintypes

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    processo = kernel32.OpenProcess(CONSULTA_LIMITADA, False, pid.value)
    if not processo:
        return ""
    try:
        tamanho = wintypes.DWORD(1024)
        caminho = ctypes.create_unicode_buffer(tamanho.value)
        if not kernel32.QueryFullProcessImageNameW(processo, 0, caminho, ctypes.byref(tamanho)):
            return ""
        return os.path.basename(caminho.value).lower()
    finally:
        kernel32.CloseHandle(processo)


def _janela_do_app():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32")
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.OpenProcess.restype = wintypes.HANDLE
    encontrada = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def olhar(hwnd, _):
        tamanho = user32.GetWindowTextLengthW(hwnd)
        if tamanho != len(TITULO_DA_JANELA) or not user32.IsWindowVisible(hwnd):
            return True
        titulo = ctypes.create_unicode_buffer(tamanho + 1)
        user32.GetWindowTextW(hwnd, titulo, tamanho + 1)
        if titulo.value == TITULO_DA_JANELA and \
                _nome_do_processo(user32, kernel32, hwnd) in PROCESSOS_DO_APP:
            encontrada.append(hwnd)
            return False
        return True

    user32.EnumWindows(olhar, 0)
    return (user32, encontrada[0]) if encontrada else (user32, None)


def trazer_para_frente():
    """Mostra a janela ja aberta: desminimiza e poe na frente. True se
    achou a janela."""
    if not _windows():
        return False
    try:
        user32, hwnd = _janela_do_app()
        if not hwnd:
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:  # noqa: BLE001 - nao achar a janela nao e erro grave
        log.exception("nao consegui trazer a janela aberta para a frente")
        return False

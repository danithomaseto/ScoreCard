"""Avisa quando algo muda na pasta do SharePoint.

Antes a tela varria a pasta inteira (12 operacoes x 9 subpastas) a cada
minuto, mudasse ou nao. Agora o app espera o aviso:

- no Windows, o proprio sistema avisa (FindFirstChangeNotification na
  pasta e subpastas): relatorio novo, lancamento de outra pessoa que o
  OneDrive baixou, arquivo apagado;
- fora do Windows, ou se o aviso nao funcionar (pasta de rede antiga),
  uma conferencia barata a cada INTERVALO segundos: so nomes, tamanhos e
  datas, sem abrir arquivo nenhum.

Uma rajada de mudancas (o OneDrive baixando varios arquivos) vira um
aviso so, ESPERA segundos depois da ultima.
"""

import logging
import os
import threading
import time

log = logging.getLogger("scorecard.observador")

ESPERA = 2.5      # segundos de calmaria antes de avisar
INTERVALO = 15.0  # conferencia por assinatura (sem o aviso do Windows)


def assinatura(base):
    """Nomes, tamanhos e datas de tudo ate dois niveis abaixo de cada
    pasta de operacao (<op>\\Week, <op>\\Gestor\\Week, <op>\\Lancamentos)."""
    itens = []

    def varrer(pasta, profundidade):
        try:
            with os.scandir(pasta) as entradas:
                for entrada in entradas:
                    if entrada.name.startswith((".", "~$")):
                        continue
                    try:
                        if entrada.is_dir(follow_symlinks=False):
                            if profundidade:
                                varrer(entrada.path, profundidade - 1)
                        else:
                            estado = entrada.stat()
                            itens.append((entrada.path, estado.st_size, estado.st_mtime_ns))
                    except OSError:
                        continue
        except OSError:
            pass

    varrer(base, 3)
    return hash(tuple(sorted(itens)))


class Observador:
    """Thread que chama ao_mudar() quando a pasta muda. parar() encerra."""

    def __init__(self, base, ao_mudar, espera=ESPERA, intervalo=INTERVALO):
        self.base = base
        self.ao_mudar = ao_mudar
        self.espera = espera
        self.intervalo = intervalo
        self.modo = None
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, name="observador-sharepoint", daemon=True)

    def iniciar(self):
        self._thread.start()
        return self

    def parar(self):
        self._parar.set()

    @property
    def ativo(self):
        return self._thread.is_alive() and not self._parar.is_set()

    def _avisar(self):
        try:
            self.ao_mudar()
        except Exception:  # noqa: BLE001 - o observador nao pode morrer por causa da tela
            log.exception("falha ao avisar mudança na pasta")

    def _rodar(self):
        if os.name == "nt":
            try:
                self._rodar_windows()
                return
            except Exception:  # noqa: BLE001 - cai na conferencia por assinatura
                log.exception("aviso de mudança do Windows não funcionou; conferindo de tempos em tempos")
        self._rodar_por_assinatura()

    def _rodar_por_assinatura(self):
        self.modo = "conferencia"
        anterior = assinatura(self.base)
        while not self._parar.wait(self.intervalo):
            atual = assinatura(self.base)
            if atual != anterior:
                # Espera a rajada acabar antes de avisar.
                while not self._parar.wait(self.espera):
                    depois = assinatura(self.base)
                    if depois == atual:
                        break
                    atual = depois
                anterior = atual
                if not self._parar.is_set():
                    self._avisar()

    def _rodar_windows(self):
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.FindFirstChangeNotificationW.restype = wintypes.HANDLE
        kernel32.FindFirstChangeNotificationW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL, wintypes.DWORD]
        kernel32.FindNextChangeNotification.argtypes = [wintypes.HANDLE]
        kernel32.FindCloseChangeNotification.argtypes = [wintypes.HANDLE]
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        filtro = 0x1 | 0x2 | 0x8 | 0x10  # nome de arquivo, nome de pasta, tamanho, ultima gravacao
        invalido = wintypes.HANDLE(-1).value
        alca = kernel32.FindFirstChangeNotificationW(self.base, True, filtro)
        if not alca or alca == invalido:
            raise OSError(ctypes.get_last_error(), "FindFirstChangeNotificationW")
        self.modo = "windows"
        ESPERANDO, SINALIZADO = 0x102, 0x0
        try:
            while not self._parar.is_set():
                resultado = kernel32.WaitForSingleObject(alca, 1000)
                if resultado == ESPERANDO:
                    continue
                if resultado != SINALIZADO:
                    raise OSError(ctypes.get_last_error(), "WaitForSingleObject")
                # Junta a rajada: espera ESPERA segundos sem novo aviso.
                ultimo = time.monotonic()
                kernel32.FindNextChangeNotification(alca)
                while not self._parar.is_set() and time.monotonic() - ultimo < self.espera:
                    if kernel32.WaitForSingleObject(alca, 250) == SINALIZADO:
                        ultimo = time.monotonic()
                        kernel32.FindNextChangeNotification(alca)
                if not self._parar.is_set():
                    self._avisar()
        finally:
            kernel32.FindCloseChangeNotification(alca)

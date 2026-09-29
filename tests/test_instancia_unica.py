"""Janela unica: a segunda abertura so traz a primeira para a frente.

O mutex e do Windows; aqui o kernel32 e trocado por um falso que imita
o comportamento dele (o mesmo nome devolve "ja existe")."""

import pytest

import instancia_unica


class Kernel32Falso:
    def __init__(self):
        self.mutexes = set()
        self.ultimo_erro = 0
        self.fechados = []

    def CreateMutexW(self, _seguranca, _dono, nome):
        self.ultimo_erro = instancia_unica.ERRO_JA_EXISTE if nome in self.mutexes else 0
        self.mutexes.add(nome)
        return 1

    def OpenMutexW(self, _acesso, _herdar, nome):
        return 7 if nome in self.mutexes else None

    def CloseHandle(self, handle):
        self.fechados.append(handle)


@pytest.fixture
def windows(monkeypatch):
    kernel32 = Kernel32Falso()
    monkeypatch.setattr(instancia_unica, "_windows", lambda: True)
    monkeypatch.setattr(instancia_unica, "_kernel32", lambda: kernel32)
    monkeypatch.setattr(instancia_unica, "_ultimo_erro", lambda: kernel32.ultimo_erro)
    monkeypatch.setattr(instancia_unica, "_mutex", None)
    return kernel32


def test_primeira_abertura_segura_a_marca(windows):
    assert not instancia_unica.ja_aberto()
    assert instancia_unica.segurar() is True
    assert instancia_unica.ja_aberto()


def test_segunda_abertura_nao_abre(windows):
    assert instancia_unica.segurar() is True
    assert instancia_unica.segurar() is False
    assert windows.fechados == [1], "a segunda solta o handle que recebeu"


def test_falha_do_windows_deixa_abrir(monkeypatch):
    def quebrado():
        raise OSError("sem kernel32")

    monkeypatch.setattr(instancia_unica, "_windows", lambda: True)
    monkeypatch.setattr(instancia_unica, "_kernel32", quebrado)
    assert instancia_unica.segurar() is True
    assert instancia_unica.ja_aberto() is False


def test_fora_do_windows_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(instancia_unica, "_windows", lambda: False)
    assert instancia_unica.segurar() is True
    assert instancia_unica.ja_aberto() is False
    assert instancia_unica.trazer_para_frente() is False


def test_lancador_com_app_aberto_so_traz_a_janela(monkeypatch):
    import lancador

    chamadas = []
    monkeypatch.setattr(instancia_unica, "ja_aberto", lambda: True)
    monkeypatch.setattr(instancia_unica, "trazer_para_frente", lambda: chamadas.append("frente"))
    monkeypatch.setattr(lancador, "preparar", lambda *a, **k: pytest.fail("nao deveria preparar"))
    assert lancador.main() == 0
    assert chamadas == ["frente"]

"""Celular, tablet e computador: tamanho da tela e da legenda no vídeo."""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ux"))


@pytest.mark.parametrize(
    ("dispositivo", "largura", "altura", "toque"),
    [("celular", 390, 844, True), ("tablet", 820, 1180, True), ("desktop", 1280, 800, False)],
)
def test_tamanho_da_tela(monkeypatch, dispositivo, largura, altura, toque):
    monkeypatch.setenv("TELA_DISPOSITIVO", dispositivo)
    sys.modules.pop("tela", None)
    tela = importlib.import_module("tela")
    assert (tela.LARGURA, tela.ALTURA, tela.TOQUE) == (largura, altura, toque)


@pytest.mark.parametrize(
    ("largura", "altura", "colunas", "trecho"),
    [(390, 844, 34, "x=(w-tw)/2"), (820, 1180, 60, "x=(w-tw)/2"), (1280, 800, 52, "x=32")],
)
def test_legenda_cabe_na_tela(largura, altura, colunas, trecho):
    import montar_video

    corpo, cols, onde = montar_video.estilo_legenda(largura, altura)
    assert cols == colunas and trecho in onde
    assert cols * corpo * 0.5 < largura  # a linha inteira cabe na largura

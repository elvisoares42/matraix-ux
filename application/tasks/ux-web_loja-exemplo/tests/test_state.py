"""Confere se a persona fez o relato do teste de usabilidade e se a sessão foi gravada."""
from __future__ import annotations

import json
from pathlib import Path

SAIDA = Path("/app/output")
RESULTADOS = {"concluiu", "concluiu_com_dificuldade", "desistiu", "travou"}
TAREFAS = {"escolher_produto", "preencher_entrega", "escolher_pagamento", "revisar_pedido", "pagar_pix", "ler_conclusao"}


def _relato() -> dict:
    arq = SAIDA / "resultado_teste.json"
    assert arq.exists(), "falta /app/output/resultado_teste.json"
    return json.loads(arq.read_text(encoding="utf-8"))


def test_relato_valido():
    r = _relato()
    assert r.get("resultado") in RESULTADOS
    assert isinstance(r.get("passos"), list) and r["passos"], "passos vazios"
    assert isinstance(r.get("relato"), str) and r["relato"].strip()


def test_avaliacao_por_tarefa():
    for a in _relato().get("avaliacao_tarefas", []):
        assert a.get("tarefa") in TAREFAS
        for nota in ("dificuldade", "clareza", "suficiencia"):
            assert isinstance(a.get(nota), int) and 1 <= a[nota] <= 7, f"{nota} fora de 1 a 7"


def test_pensou_em_voz_alta_e_gravou():
    falas = SAIDA / "fala_em_voz_alta.jsonl"
    assert falas.exists() and falas.read_text(encoding="utf-8").strip(), "a persona não pensou em voz alta"
    assert list((SAIDA / "video").glob("seg_*.webm")), "a sessão não foi gravada"

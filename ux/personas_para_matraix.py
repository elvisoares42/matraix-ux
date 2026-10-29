"""Converte personas da base Personas Sintéticas UX num grupo de personas (dataset) do MatrAIx.

Entrada: personas.jsonl da base (gerada pelo projeto personas-sinteticas ou baixada do Hugging Face).
Saída: persona/datasets/<nome>/persona_NNNNNN.yaml + manifest.json, prontos para o Playground e para `matraix run`.

Uso (na raiz do MatrAIx):
  .venv/bin/python ux/personas_para_matraix.py personas.jsonl --nome brasil-quali --amostra 7 --estratos geracao
  .venv/bin/python ux/personas_para_matraix.py personas.jsonl --nome brasil-quanti --amostra 400 --filtro regiao=Nordeste

Só entram personas testáveis (18+), a não ser com --incluir-menores. A amostra é estratificada e determinística (--seed).
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FAIXAS = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 200)]
GENERO = {"cisgênero": None, "mulher trans": "Woman", "homem trans": "Man", "pessoa não binária": "Non-binary"}


def faixa_idade(idade: int) -> str:
    for a, b in FAIXAS:
        if a <= idade <= b:
            return f"{a}+" if b == 200 else f"{a}-{b}"
    return "under-18"


def dimensoes(p: dict) -> dict:
    """Dimensões no padrão do MatrAIx (para filtros e relatórios) + todos os campos da base."""
    genero = GENERO.get(p.get("identidade_genero")) or ("Woman" if p["sexo"] == "Mulher" else "Man")
    padrao = {"age_bracket": faixa_idade(int(p["idade"])), "gender_identity": genero, "region": "Brazil",
              "primary_language": "Portuguese", "lang_portuguese": "Native"}
    proprias = {k: v for k, v in p.items() if k not in ("persona_id", "nome", "sobrenome", "ficha")}
    return {**padrao, **proprias}


def amostrar(pessoas: list[dict], n: int, estratos: list[str], seed: int) -> list[dict]:
    """Amostra proporcional por estrato (ex.: geração), com pelo menos uma persona por estrato quando couber."""
    rng = random.Random(seed)
    if not estratos or n >= len(pessoas):
        return rng.sample(pessoas, min(n, len(pessoas)))
    grupos = defaultdict(list)
    for p in pessoas:
        grupos[tuple(p.get(e, "") for e in estratos)].append(p)
    cotas = {g: max(1, round(n * len(v) / len(pessoas))) for g, v in grupos.items()}
    while sum(cotas.values()) > n:  # ajusta o arredondamento tirando dos maiores
        g = max(cotas, key=lambda k: (cotas[k], len(grupos[k])))
        cotas[g] -= 1
    escolhidas = []
    for g in sorted(grupos):
        escolhidas += rng.sample(grupos[g], min(cotas[g], len(grupos[g])))
    return sorted(escolhidas, key=lambda p: p["persona_id"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personas", type=Path, help="personas.jsonl da base")
    ap.add_argument("--nome", required=True, help="nome do grupo (vira persona/datasets/<nome>)")
    ap.add_argument("--amostra", type=int, default=7, help="quantas personas (padrão: 7, um teste qualitativo)")
    ap.add_argument("--estratos", default="geracao", help="campos para estratificar, separados por vírgula ('' = sem)")
    ap.add_argument("--filtro", action="append", default=[], help="campo=valor (pode repetir)")
    ap.add_argument("--seed", type=int, default=20261029)
    ap.add_argument("--incluir-menores", action="store_true")
    a = ap.parse_args()

    pessoas = [json.loads(l) for l in a.personas.open(encoding="utf-8") if l.strip()]
    if not a.incluir_menores:
        pessoas = [p for p in pessoas if p.get("testavel") == "sim"]
    for f in a.filtro:
        campo, valor = f.split("=", 1)
        pessoas = [p for p in pessoas if str(p.get(campo)) == valor]
    escolhidas = amostrar(pessoas, a.amostra, [e for e in a.estratos.split(",") if e], a.seed)
    if not escolhidas:
        raise SystemExit("Nenhuma persona atende aos filtros.")

    pasta = RAIZ / "persona" / "datasets" / a.nome
    pasta.mkdir(parents=True, exist_ok=True)
    for f in pasta.glob("persona_*.yaml"):
        f.unlink()
    manifest = []
    for p in escolhidas:
        dims = dimensoes(p)
        doc = {"persona_id": p["persona_id"], "version": "1.0", "source": "personas-sinteticas-ux",
               "display_name": f"{p['nome']} {p['sobrenome']}", "dimensions": dims, "system_prompt": p["ficha"],
               "provenance": {"base": "Personas Sintéticas UX (IBGE: Censo 2022, PNAD TIC 2025, PNS 2019)",
                              "aviso": "persona sintética: padrões agregados, nenhum dado de pessoa real"}}
        rel = f"persona/datasets/{a.nome}/persona_{p['persona_id']}.yaml"
        (RAIZ / rel).write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        manifest.append({"persona_id": p["persona_id"], "path": rel, "source": "personas-sinteticas-ux",
                         "display_name": doc["display_name"],
                         "dimensions": {k: dims[k] for k in ("age_bracket", "gender_identity", "regiao", "geracao")}})
    (pasta / "manifest.json").write_text(json.dumps({
        "kind": a.nome, "count": len(escolhidas), "seed": a.seed, "schema_version": "1.0",
        "smoke_persona_id": escolhidas[0]["persona_id"], "dimension_count": len(dims), "dimension_ids": list(dims),
        "source_counts": {"personas-sinteticas-ux": len(escolhidas)}, "personas": manifest}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"{len(escolhidas)} personas em {pasta}")
    for p in escolhidas[:10]:
        print(f"  {p['persona_id']} {p['nome']} {p['sobrenome']}, {p['idade']} anos, {p['uf']}, {p['geracao']}")


if __name__ == "__main__":
    main()

#!/bin/bash
# Resposta de referência (sem IA), só para testar o ambiente: notas neutras e a primeira opção.
set -euo pipefail
mkdir -p /app/output
python3 <<'PY'
import json
from pathlib import Path
import yaml
q = yaml.safe_load(Path("/app/input/questionnaire.yaml").read_text(encoding="utf-8"))
respostas = []
for p in q["questions"]:
    if p["type"] == "likert":
        v = (p["minValue"] + p["maxValue"]) // 2
    elif p["type"] == "single_choice":
        v = p["options"][0]["id"]
    else:
        v = "Mostraria o frete e o formato do CEP antes."
    respostas.append({"questionId": p["id"], "value": v})
Path("/app/output/survey_result.json").write_text(json.dumps({"answers": respostas}, ensure_ascii=False, indent=2))
PY

#!/bin/zsh
# Barra o envio se aparecer chave de API ou termo proibido nos arquivos e commits do fork (não no conteúdo do MatrAIx original).
# Termos proibidos: .termos-proibidos (uma expressão por linha, fora do git), se existir.
cd "$(dirname "$0")/.." || exit 1
CHAVES='sk-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AccountKey=[A-Za-z0-9+/=]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}'
falhou=0
# só o que o fork acrescentou ou mudou em relação ao MatrAIx original (o resto é deles)
ARQS=$( { git diff --name-only upstream/main; git ls-files -o --exclude-standard; } | sort -u | while read -r f; do [[ -f "$f" ]] && echo "$f"; done)
achou=$(echo "$ARQS" | tr '\n' '\0' | xargs -0 grep -IlE "$CHAVES" 2>/dev/null)
hist=$(git log -p upstream/main..HEAD 2>/dev/null | grep -E '^\+[^+]' | grep -E "$CHAVES")
if [[ -n "$achou$hist" ]]; then echo "❌ Possível chave de API:"; echo "$achou"; echo "$hist" | cut -c1-80; falhou=1; fi
if [[ -s .termos-proibidos ]]; then
  TERMOS=$(grep -v '^\s*$' .termos-proibidos | paste -sd '|' -)
  t1=$(echo "$ARQS" | grep -v '^.termos-proibidos$' | tr '\n' '\0' | xargs -0 grep -IinE "$TERMOS" 2>/dev/null)
  t2=$(git log -p upstream/main..HEAD 2>/dev/null | grep -E '^\+[^+]' | grep -iE "$TERMOS")
  if [[ -n "$t1$t2" ]]; then echo "❌ Termos proibidos:"; echo "$t1" | head -20; echo "$t2" | head -20; falhou=1; fi
fi
[[ $falhou == 0 ]] && echo "✅ Sem chaves e sem termos proibidos."
exit $falhou

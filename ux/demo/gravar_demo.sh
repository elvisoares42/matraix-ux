#!/bin/zsh
# Grava o vídeo de demonstração do README: sessão roteirizada na Elvis Design (loja fictícia) + voz + legenda + cortes.
# A voz usa a OpenAI: rode com a chave só no ambiente do terminal (nunca em arquivo do repositório):
#   export OPENAI_API_KEY=...   (digite você mesmo)
#   ux/demo/gravar_demo.sh                 (voz melhorada, ~US$ 0,45)
#   UX_VOZ=basica ux/demo/gravar_demo.sh   (voz básica, centavos)
# Precisa de: pip install playwright imageio-ffmpeg httpx pyyaml && python -m playwright install chromium
set -e
# chave opcional num arquivo fora do repositório (nunca dentro do projeto)
[[ -z "${OPENAI_API_KEY:-}" && -f ~/.config/matraix-ux/chave.env ]] && source ~/.config/matraix-ux/chave.env
[[ -n "${OPENAI_API_KEY:-}" ]] && echo "Chave da OpenAI encontrada: o vídeo sai com voz." || echo "Sem chave da OpenAI: o vídeo sai só com legenda."
cd "$(dirname "$0")/../.."
PY=${PYTHON:-python3}
TRAB=$(mktemp -d)
mkdir -p "$TRAB/083265"
TELA_PORTA=${TELA_PORTA:-8812} TELA_SAIDA="$TRAB/083265" "$PY" ux/demo/sessao_demo.py
"$PY" ux/montar_video.py "$TRAB" --personas persona/datasets/brasil-quali-exemplo --voz "${UX_VOZ:-melhorada}"
mkdir -p docs/ux
cp "$TRAB"/videos/083265_*.mp4 docs/ux/demo-loja-exemplo.mp4
echo "Vídeo: docs/ux/demo-loja-exemplo.mp4"

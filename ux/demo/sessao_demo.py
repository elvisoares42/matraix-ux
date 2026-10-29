"""Sessão roteirizada (sem IA) na Elvis Design (loja fictícia), para o vídeo de demonstração do README.

As falas imitam um pensar em voz alta real; a tela, os toques e os erros são de verdade.
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TAREFA = RAIZ / "application/tasks/ux-web_loja-exemplo/input"
sys.path.insert(0, str(TAREFA))
from tela import Tela  # noqa: E402

t = Tela()
t.abrir(f"file://{TAREFA}/site/index.html")
t.ver()
t.falar("Oi! Bom, abriu a loja. Tá escrito fones de ouvido, e tem três opções.")
t.falar("O leve é cento e vinte e nove, o esportivo cento e oitenta e nove, e o headphone passa de trezentos.")
t.falar("Eu quero um pra usar no ônibus, então acho que o leve resolve. Vou ver os detalhes dele.")
t.tocar("Ver detalhes do Fone Leve")
t.ver()
t.falar("Bateria de vinte horas, estojo de carga, garantia de um ano. Gostei. Vou comprar.")
t.tocar("Comprar")
t.ver()
t.falar("Agora os dados de entrega. Nome completo...")
t.digitar("Nome completo", "Teste da Silva")
t.falar("E-mail...")
t.digitar("E-mail", "teste@exemplo.com")
t.falar("CEP, do jeito que eu sempre escrevo, com tracinho.")
t.digitar("CEP", "01310-100")
t.digitar("Celular", "(11) 91234-5678")
t.ver()
t.falar("Hmm, esse botão Continuar tá meio apagado. Será que eu esqueci alguma coisa? Vou tentar assim mesmo.")
t.tocar("Continuar")
t.ver()
t.falar("Ué. Dado inválido, embaixo do CEP. Mas não diz o que tá errado.")
t.falar("Vou tentar sem o tracinho, só os números.")
t.digitar("CEP", "01310100")
t.tocar("Continuar")
t.ver()
t.falar("Agora foi. Como você quer pagar? Pix ou na entrega. Pix aprova na hora, vou de Pix.")
t.tocar("Pix")
t.ver()
t.tocar("Ir para a revisão")
t.ver()
t.falar("Revise o pedido... Opa, frete de vinte e quatro e noventa? Isso não apareceu antes.")
t.falar("O total ficou cento e cinquenta e quatro e oitenta. Eu queria ter sabido disso lá no começo.")
t.rolar()
t.ver()
t.falar("Tá, o resto é aquele texto pequeno de sempre. Vou finalizar.")
t.tocar("Finalizar pedido")
t.ver()
t.falar("Pague com Pix. Tem o QR Code e um código pra copiar. Vou copiar o código.")
t.tocar("Copiar código Pix")
t.ver()
t.falar("Hmm... copiou? Não apareceu nenhum aviso. Vou confiar e dizer que já paguei.")
t.tocar("Já fiz o pagamento")
t.ver()
t.falar("Pedido recebido, com o número. Mas não fala quando chega. Eu ia ficar ansiosa esperando.")
t.falar("No geral foi fácil escolher, mas o erro do CEP e o frete surpresa me deixaram insegura.")
t.encerrar()

saida = Path(os.environ.get("TELA_SAIDA", "/app/output"))
(saida / "persona_meta.json").write_text(json.dumps({"persona_id": "083265"}), encoding="utf-8")
print("sessão gravada em", saida)

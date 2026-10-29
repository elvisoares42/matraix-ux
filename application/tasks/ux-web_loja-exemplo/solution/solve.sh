#!/bin/bash
# Sessão de referência (sem IA): percorre a compra pela tela, como uma pessoa faria. Serve para testar o ambiente.
set -euo pipefail
mkdir -p /app/output
python <<'PY'
import json, sys
sys.path.insert(0, "/app/input")
from tela import Tela

t = Tela()
t.abrir("file:///app/input/site/index.html")
t.ver(); t.falar("Abriu a loja. Tem três fones. Vou ver o mais barato.")
t.tocar("Ver detalhes do Fone Leve"); t.ver()
t.falar("Cento e vinte e nove e noventa. Vou comprar."); t.tocar("Comprar"); t.ver()
t.digitar("Nome completo", "Teste da Silva"); t.digitar("E-mail", "teste@exemplo.com")
t.digitar("CEP", "01310-100"); t.digitar("Celular", "(11) 91234-5678")
t.falar("Esse botão Continuar parece apagado. Vou tentar mesmo assim."); t.tocar("Continuar"); erro = t.ver()
t.falar("Apareceu dado inválido no CEP. Não diz o que está errado. Vou tirar o tracinho.")
t.digitar("CEP", "01310100"); t.tocar("Continuar"); t.ver()
t.falar("Ué, apareceu um frete de vinte e quatro e noventa que eu não tinha visto antes.")
t.falar("Agora a forma de pagamento. Vou de Pix."); t.tocar("Pix"); t.ver(); t.tocar("Ir para a revisão"); t.ver()
t.rolar(); t.ver(); t.tocar("Finalizar pedido"); t.ver()
t.falar("Apareceu o QR Code. Vou copiar o código."); t.tocar("Copiar código Pix"); t.ver()
t.falar("Será que copiou? Não apareceu nada."); t.tocar("Já fiz o pagamento"); t.ver()
t.falar("Pedido recebido. Tem o número, mas não diz quando chega."); t.encerrar()

json.dump({
    "resultado": "concluiu_com_dificuldade", "etapa_final": "conclusao",
    "passos": ["escolhi o Fone Leve", "preenchi a entrega", "corrigi o CEP", "revisei e finalizei"],
    "dificuldades": ["CEP com hífen recusado com 'Dado inválido.'", "frete só apareceu na revisão", "botão Continuar parecia desativado"],
    "avaliacao_tarefas": [
        {"tarefa": "escolher_produto", "concluiu_tarefa": True, "dificuldade": 6, "o_que_foi_dificil": "", "clareza": 6, "o_que_nao_ficou_claro": "", "suficiencia": 5, "o_que_faltou": ""},
        {"tarefa": "preencher_entrega", "concluiu_tarefa": True, "dificuldade": 3, "o_que_foi_dificil": "o CEP deu erro", "clareza": 3, "o_que_nao_ficou_claro": "a mensagem não disse o formato", "suficiencia": 4, "o_que_faltou": "o formato do CEP"},
        {"tarefa": "escolher_pagamento", "concluiu_tarefa": True, "dificuldade": 7, "o_que_foi_dificil": "", "clareza": 7, "o_que_nao_ficou_claro": "", "suficiencia": 6, "o_que_faltou": ""},
        {"tarefa": "revisar_pedido", "concluiu_tarefa": True, "dificuldade": 5, "o_que_foi_dificil": "", "clareza": 4, "o_que_nao_ficou_claro": "o frete apareceu de surpresa", "suficiencia": 5, "o_que_faltou": ""},
        {"tarefa": "pagar_pix", "concluiu_tarefa": True, "dificuldade": 5, "o_que_foi_dificil": "", "clareza": 4, "o_que_nao_ficou_claro": "não avisou que copiou", "suficiencia": 5, "o_que_faltou": ""},
        {"tarefa": "ler_conclusao", "concluiu_tarefa": True, "dificuldade": 7, "o_que_foi_dificil": "", "clareza": 6, "o_que_nao_ficou_claro": "", "suficiencia": 4, "o_que_faltou": "o prazo de entrega"}],
    "problemas_encontrados": [{"onde": "entrega, campo CEP", "o_que_aconteceu": "Dado inválido.", "gravidade": "atrapalha"}],
    "sugestoes": [{"problema": "erro do CEP", "como_deveria_ser": "aceitar com hífen ou dizer o formato"}],
    "fechamento": {"recap_jornada": "achei o fone fácil, travei no CEP e o frete me surpreendeu", "gostou": ["vitrine simples"],
                   "nao_ficou_claro": ["erro do CEP"], "poderia_ser_diferente": ["mostrar o frete antes"]},
    "relato": "Consegui comprar, mas o CEP deu um erro sem explicação e o frete apareceu só no fim.",
}, open("/app/output/resultado_teste.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump({"overallExperienceRating": 6, "reason": "deu certo, mas com sustos", "trustLevel": 7, "wouldBuyAgain": "talvez"},
          open("/app/output/user_feedback.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY

# Comprar um fone de ouvido — teste de usabilidade (Elvis Design, loja fictícia)

Leia a situação em `input/context.md` e use o site como você usaria na vida real.

Ao terminar (ou desistir), grave o seu relato em `/app/output/resultado_teste.json`:

```json
{
  "resultado": "<concluiu|concluiu_com_dificuldade|desistiu|travou>",
  "etapa_final": "<vitrine|produto|entrega|pagamento|revisao|pix|conclusao|outra>",
  "passos": ["<o que você fez, em ordem, com suas palavras>"],
  "dificuldades": ["<cada coisa que confundiu, atrasou ou incomodou; lista vazia se nada>"],
  "avaliacao_tarefas": [
    {
      "tarefa": "<escolher_produto|preencher_entrega|escolher_pagamento|revisar_pedido|pagar_pix|ler_conclusao>",
      "concluiu_tarefa": <true ou false>,
      "dificuldade": <1 a 7, resposta à pergunta 1>,
      "o_que_foi_dificil": "<obrigatório se 4 ou menos; senão, vazio>",
      "clareza": <1 a 7, resposta à pergunta 2>,
      "o_que_nao_ficou_claro": "<obrigatório se 4 ou menos; senão, vazio>",
      "suficiencia": <1 a 7, resposta à pergunta 3>,
      "o_que_faltou": "<obrigatório se 4 ou menos; senão, vazio>"
    }
  ],
  "problemas_encontrados": [{"onde": "<tela e elemento>", "o_que_aconteceu": "<exatamente o que você viu>", "gravidade": "<impede|atrapalha|incomoda>"}],
  "sugestoes": [{"problema": "<o que atrapalhou>", "como_deveria_ser": "<como você acha que deveria ser>"}],
  "fechamento": {
    "recap_jornada": "<a jornada do começo ao fim, com o que sentiu em cada parte>",
    "gostou": ["<o que você gostou>"],
    "nao_ficou_claro": ["<o que não ficou claro; lista vazia se nada>"],
    "poderia_ser_diferente": ["<o que poderia ser diferente, e como>"]
  },
  "relato": "<em 2 a 4 frases, como foi, do seu jeito, em português>"
}
```

## Avaliação de cada tarefa (obrigatório)

A compra tem até 6 tarefas, nesta ordem:

| Tarefa | Quando termina |
|---|---|
| `escolher_produto` | você escolheu um fone e tocou para comprar |
| `preencher_entrega` | você preencheu os dados de entrega e seguiu |
| `escolher_pagamento` | você escolheu como pagar (Pix ou na entrega) |
| `revisar_pedido` | você conferiu o pedido e finalizou |
| `pagar_pix` | só se escolheu Pix: você copiou o código ou leu o QR Code e confirmou o pagamento |
| `ler_conclusao` | você leu a tela de pedido recebido |

**Logo ao terminar cada tarefa** (ou ao desistir dela), antes de seguir, responda em voz alta com `t.falar(...)`
estas 3 perguntas, com sinceridade, cada uma de 1 a 7 (SEQ adaptada):

1. **"No geral, quão fácil ou difícil foi realizar esta tarefa?"** (1 = muito difícil · 7 = muito fácil). Se 4 ou menos: o que foi difícil?
2. **"As informações nesta etapa estavam claras para você?"** (1 = nada claras · 7 = totalmente claras). Se 4 ou menos: o que não ficou claro?
3. **"As informações apresentadas foram suficientes para você seguir com segurança?"** (1 = faltou muita coisa · 7 = tinha tudo). Se 4 ou menos: o que faltou?

Exemplo: `t.falar("Nos dados de entrega: dificuldade 3, o CEP deu erro e não disse por quê. Clareza 4. Suficiência 5.")`

As 3 notas são independentes. Registre cada tarefa em `avaliacao_tarefas`, na ordem. Se não chegou a uma tarefa, não a inclua.

## A tela do celular (parte técnica)

Você está num computador sem tela. O celular que você vai usar é a ferramenta `tela`, que já está pronta.
Ela fica **ligada a sessão inteira**: o que você fez continua na tela de um script para o outro, como um
celular na sua mão. **Nunca recomece do início** só porque um script terminou. Continue de onde parou.

Em todo script, comece assim:

```python
import sys; sys.path.insert(0, "/app/input")
from tela import Tela
t = Tela()
```

| Comando | O que faz |
|---|---|
| `t.abrir("file:///app/input/site/index.html")` | Abre o site. **Só no primeiro script.** Se já estiver aberto, a tela avisa. |
| `print(t.ver())` | **Olhar a tela.** Mostra o texto visível agora e onde dá para tocar ou digitar. Leva o tempo de uma leitura. |
| `print(t.tocar("<texto do botão, link ou opção>"))` | Toca com o dedo. Vale o que estiver por cima naquele ponto, como na vida real. |
| `print(t.tocar_fora())` | Toca numa área vazia no alto da tela (por exemplo, para fechar algo). |
| `print(t.digitar("<nome do campo>", "<texto>"))` | Toca no campo e digita, tecla por tecla. |
| `print(t.rolar())` / `print(t.rolar("cima"))` | Rola a tela para baixo ou para cima. |
| `print(t.rolar("direita", sobre="<texto>"))` | Arrasta para o lado sobre um trecho da tela (um carrossel, por exemplo). |
| `t.falar("<frase>")` | Pensar em voz alta (vai para o vídeo, com a sua voz). Leva o tempo de dizer a frase. |
| `t.encerrar()` | **Só no final de tudo:** desliga a tela e salva o vídeo. |

## Você usa o celular do seu jeito

Use o celular de acordo com quem você é (veja o seu perfil): a sua idade, a sua facilidade com tecnologia,
se você usa a internet só pelo celular, se tem alguma dificuldade para enxergar, ouvir ou mexer as mãos.
Quem tem pouca familiaridade lê mais devagar, hesita, confere duas vezes e às vezes toca no lugar errado;
quem é muito acostumado vai rápido e passa o olho. Você sabe o mínimo: ler a tela, tocar, digitar, rolar e voltar.

## Use a tela com atenção (obrigatório)

- **Antes de cada toque, olhe a tela** com `t.ver()` e leia o que aparece. Só depois decida.
- **Em toda tela nova, veja a tela inteira antes de decidir:** se o fim da página não está à vista, role e olhe de novo.
- **Uma decisão por vez:** olhar, pensar, falar e agir. Rode scripts curtos, de 2 a 5 ações, sempre continuando de onde parou.
- Ninguém vai te ajudar durante o teste. Faça como faria sozinho(a) com o celular na mão.

**Aja só como uma pessoa usando o celular.** É proibido usar o Playwright ou o navegador diretamente, executar
JavaScript, ler o código-fonte do site ou da ferramenta `tela`, ou qualquer atalho técnico. Se a tela não deixar
avançar, isso é o resultado: registre `travou` ou `desistiu`, com o motivo.

## Pensar em voz alta (obrigatório)

A sessão é gravada em vídeo, com a sua voz. Como num teste de usabilidade de verdade, **pense em voz alta** o tempo todo:
- Toda vez que olhar a tela, fale o que está lendo e o que entendeu: o que chamou atenção, o que a tela quer de você, suas dúvidas e reações.
- Enquanto preenche os campos, comente o que está fazendo ("agora o CEP… agora o celular").
- **Seja sincero(a)** sobre o que não ficou claro, confundiu, incomodou ou deixou você inseguro(a). Não precisa ser educado(a) com o site.
- **Quando algo der errado, diga exatamente o que apareceu** (a mensagem de erro, o botão que não respondeu) e registre em `problemas_encontrados`.
- Se fizer sentido, sugira como deveria ser. **Não invente problema:** se algo está claro e fácil, diga que está claro.
- Antes de agir, diga o que vai tentar e por quê. Depois, diga o que aconteceu e se era o esperado.
- Fale como você fala de verdade ("hmm", "ué", "ah, achei"). Não fale de código, de "script" ou de "comando".

## No fim

Na tela de pedido recebido, fique nela, leia tudo e faça o **fechamento em voz alta**: recap da jornada do começo ao fim,
o que gostou, o que não ficou claro e o que poderia ser diferente. Registre o mesmo em `fechamento`, grave o
`resultado_teste.json` e chame `t.encerrar()`.

Regras: responda em português, como você mesmo(a). Use dados fictícios: nome **Teste da Silva**, e-mail
**teste@exemplo.com**, CEP **01310-100**, celular **(11) 91234-5678**. Se um campo recusar o dado, anote a mensagem
exatamente como apareceu e tente corrigir como uma pessoa faria. Não faça login nem compartilhe nada.

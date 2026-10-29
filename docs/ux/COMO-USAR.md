# Como usar: testes de usabilidade e formulários com personas sintéticas

Guia prático para designers. Você pode seguir os comandos à mão ou **pedir para uma IA de código fazer por você**
(Claude Code, GitHub Copilot no VS Code, Cursor, OpenAI Codex, Gemini CLI...). Os prompts prontos estão na seção 7.

> Personas sintéticas são triagem, não prova. Use para achar problemas cedo e chegar mais afiado ao teste com pessoas reais.

## 1. Preparar (uma vez)

1. Siga a instalação do MatrAIx no [README principal](../../README.md) (Python, `uv`, Docker para tarefas web).
2. Instale o que o fork UX usa para gravar e montar vídeos:
   ```bash
   uv pip install playwright imageio-ffmpeg httpx pyyaml && uv run python -m playwright install chromium
   ```
3. Chave do modelo **só no ambiente do terminal**, nunca em arquivo do repositório:
   ```bash
   export OPENAI_API_KEY=...      # ou ANTHROPIC_API_KEY=...
   ```
4. Baixe a base **Personas Sintéticas UX** (100 mil personas brasileiras, `personas.jsonl`) do Hugging Face
   ou gere com o projeto [personas-sinteticas](https://github.com/elvisoares42/personas-sinteticas).

## 2. Escolher as personas (o "grupo" do teste)

O grupo de personas é quem participa do teste. O conversor sorteia da base, na proporção do Brasil:

```bash
# teste qualitativo: 5 personas, uma mistura de gerações
uv run python ux/personas_para_matraix.py personas.jsonl --nome meu-quali --amostra 5

# formulário: 400 personas; dá para filtrar (repita --filtro para combinar)
uv run python ux/personas_para_matraix.py personas.jsonl --nome meu-quanti --amostra 400 --filtro regiao=Nordeste
uv run python ux/personas_para_matraix.py personas.jsonl --nome pcd --amostra 7 --filtro deficiencia=sim
```

Campos úteis para filtro: `uf`, `regiao`, `geracao`, `sexo`, `cor_raca`, `negra`, `renda_per_capita`, `instrucao`,
`deficiencia`, `usa_internet`, `internet_so_celular`, `situacao_domicilio`, `orientacao_sexual`, `identidade_genero`.

## 3. Teste de usabilidade (qualitativo, com vídeo)

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/ux-web_loja-exemplo \
  --execution-mode auto --dataset persona/datasets/meu-quali --sample-size 5 \
  --model-name openai/gpt-5.4
uv run matraix run -c configs/jobs/application-task-job-recipe/<arquivo-que-o-comando-mostrar>.yaml

# vídeo de cada persona: tela + voz + legenda, sem os trechos parados
uv run python ux/montar_video.py jobs/<job> --personas persona/datasets/meu-quali                # voz melhorada
uv run python ux/montar_video.py jobs/<job> --personas persona/datasets/meu-quali --voz basica   # voz básica, mais barata
```

Cada persona olha a tela, toca, digita, rola e **pensa em voz alta**. Ao fim de cada etapa responde à **SEQ adaptada**
(dificuldade, clareza e suficiência, de 1 a 7), aponta os **problemas encontrados** com gravidade e faz um fechamento.
Os vídeos saem em `jobs/<job>/videos/`. Sem chave da OpenAI (ou com `--sem-voz`), saem só com legenda.

### Testar o seu protótipo

1. Copie a tarefa: `cp -R application/tasks/ux-web_loja-exemplo application/tasks/ux-web_meu-produto`.
2. Troque `input/site/` pelo HTML do seu protótipo **ou** aponte `t.abrir(...)` em `instruction.md` para a URL publicada.
3. Reescreva `input/context.md` (a situação da persona), a lista de tarefas e os dados fictícios em `instruction.md`.
4. Atualize o `README.md` da tarefa com o seu **gabarito** (os problemas que você já conhece), para comparar depois.

> A persona "enxerga" pelo texto e pelos elementos da página (DOM). Protótipos em HTML (Figma Sites, Framer, Webflow,
> código) funcionam bem. O visualizador de protótipos do Figma desenha tudo numa imagem e a persona não consegue ler:
> publique como site antes.

## 4. Formulário (quantitativo)

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/ux-survey_formulario-exemplo \
  --execution-mode auto --dataset persona/datasets/meu-quanti --sample-size 400 \
  --model-name openai/gpt-5.4-mini
uv run matraix run -c configs/jobs/application-task-job-recipe/<arquivo>.yaml
```

O exemplo traz o **SUS** (10 itens), **NPS**, a pergunta "o que mais atrapalhou" e um comentário aberto.
Para o seu formulário, edite `input/questionnaire.yaml` (tipos: `likert`, `single_choice`, `multi_choice`, `free_text`)
e `input/context.md`.

## 5. Quanto custa (valores médios medidos)

Medido em rodadas reais de um protótipo de checkout no celular, em outubro de 2026, com **5 personas por rodada**
(3 rodadas de usabilidade com o gpt-5.4). O custo muda com o modelo, o tamanho do protótipo e quanto a persona fala.

| Teste com 5 personas | Sessões (gpt-5.4) | Voz do vídeo | **Total por teste** |
|---|---|---|---|
| **Usabilidade + vídeo com voz básica** (`--voz basica`, gpt-4o-mini-tts) | US$ 2,20 a 2,75 | centavos | **~US$ 2,20** |
| **Usabilidade + vídeo com voz melhorada** (padrão, gpt-audio-1.5) | US$ 2,20 a 2,75 | US$ 1,70 a 2,70 | **~US$ 4,50** |
| Usabilidade sem voz (vídeo só com legenda, `--sem-voz`) | US$ 2,20 a 2,75 | — | ~US$ 2,20 |
| **Formulário com 400 personas** (gpt-4o-mini) | — | — | **US$ 0,15 a 0,40** |

- Por persona, a sessão de usabilidade custa em média **US$ 0,50** (de 0,36 a 0,85, em 22 sessões).
- A voz melhorada é mais natural e expressiva, boa para apresentar a stakeholders. A básica serve para o dia a dia da equipe.
- **Modelo barato na usabilidade** (gpt-5.4-mini, ~US$ 0,14 por persona): não recomendado. Nas nossas rodadas, personas
  "trapacearam" (rodaram JavaScript, leram o código da página).
- **Formulário**: modelos pequenos tendem a dar notas parecidas para todo mundo (o "meio-termo seguro"). Para notas mais
  diferenciadas, use um modelo maior: o custo sobe, mas fica bem abaixo de uma pesquisa de campo.
- Dá para pôr um teto em qualquer rodada: `matraix run -c <arquivo>.yaml --max-cost-usd 10`.

## 6. Ler os resultados

- **Vídeos** (`jobs/<job>/videos/`): assista primeiro; é o highlight reel.
- **Relatos** (`resultado_teste.json` de cada persona): passos, dificuldades, problemas encontrados, sugestões, SEQ por etapa.
- **Compare com o gabarito** do README da tarefa: quais problemas as personas acharam sozinhas, quais ninguém achou.
- **Desconfie** de persona que concluiu fácil demais, e de qualquer relato que fale de código: ela pode ter usado um atalho técnico. Descarte essas sessões.

## 7. Prompts prontos para IAs de código

Abra a pasta do fork na ferramenta e cole o prompt. Funciona em qualquer agente que lê arquivos e roda comandos no terminal.

| Ferramenta | Onde colar |
|---|---|
| **Claude Code** | no terminal (`claude`), no app desktop ou na extensão do VS Code/JetBrains |
| **GitHub Copilot** | VS Code, painel do Copilot Chat em **modo Agent** |
| **Cursor** | painel do agente (Agent) |
| **OpenAI Codex** | `codex` no terminal ou a extensão do VS Code |
| **Gemini CLI / outros agentes** | no terminal, na pasta do projeto |

**Preparar o ambiente**
```text
Leia docs/ux/COMO-USAR.md e prepare este projeto para rodar testes de usabilidade com personas sintéticas:
instale as dependências, confira se o Docker está ligado e rode a sessão de referência da tarefa
application/tasks/ux-web_loja-exemplo sem IA (solution/solve.sh) para testar o ambiente.
Não grave nenhuma chave em arquivo; se precisar de chave, me peça para eu definir no terminal.
```

**Criar um teste de usabilidade do meu protótipo**
```text
Crie uma tarefa de teste de usabilidade copiando application/tasks/ux-web_loja-exemplo.
Protótipo: <URL publicada ou pasta com o HTML>.
Situação da persona: <ex.: "você quer renovar o seguro do carro pelo celular">.
Tarefas do teste, em ordem: <ex.: entrar, simular, escolher o plano, pagar, ler a confirmação>.
Dados fictícios: <ex.: nome Teste da Silva, CPF 000.000.000-00>.
Mantenha o protocolo de pensar em voz alta, a SEQ adaptada por tarefa e as regras da tela.
Escreva no README da tarefa um gabarito com os problemas que você já vê no protótipo.
```

**Rodar o teste qualitativo com vídeo**
```text
Monte um grupo de 5 personas da base personas.jsonl (ux/personas_para_matraix.py, estratificado por geração),
rode a tarefa application/tasks/<minha-tarefa> com o modelo openai/gpt-5.4 e um teto de US$ 10,
e depois monte os vídeos com ux/montar_video.py (voz básica; use a melhorada só se eu pedir). No fim, me mostre uma tabela por persona com resultado,
SEQ de cada etapa e os problemas encontrados, e compare com o gabarito do README da tarefa.
```

**Rodar um formulário com 400 personas**
```text
Crie um formulário a partir de application/tasks/ux-survey_formulario-exemplo com estas perguntas: <cole aqui>.
Monte um grupo de 400 personas (proporcional por geração) e rode com openai/gpt-5.4-mini, teto de US$ 5.
Me entregue: SUS médio, NPS, distribuição de cada pergunta por geração, região e renda,
e um resumo dos comentários abertos agrupados por tema.
```

**Analisar uma rodada que já terminou**
```text
Leia os resultados em jobs/<job>/ (resultado_teste.json, user_feedback.json e eventos.jsonl de cada persona).
Liste os problemas de usabilidade ordenados por quantas personas tiveram e pela gravidade, com uma citação
de fala de cada um (fala_em_voz_alta.jsonl), a heurística de Nielsen relacionada e uma sugestão de correção.
Separe as sessões suspeitas (persona que usou atalho técnico ou concluiu sem olhar a tela).
```

## 8. Cuidados

- **Chaves**: só no ambiente do terminal. O `.gitignore` já ignora `.env`; mesmo assim, nunca cole chave em arquivo do projeto.
- **Dados reais**: use protótipos e dados fictícios. Não aponte a persona para sistemas com dados de clientes nem para contas reais.
- **Acessibilidade**: personas com deficiência sintéticas ajudam a lembrar desses públicos, mas não substituem teste com pessoas com deficiência e tecnologia assistiva real.
- **Vídeos**: todo vídeo sai com a faixa "SIMULAÇÃO – persona sintética", para nunca ser confundido com gravação de pessoa real.

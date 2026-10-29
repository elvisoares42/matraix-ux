"""Tela do celular para testes de usabilidade com personas sintéticas (fork UX do MatrAIx).

Um serviço local mantém UM navegador aberto durante a sessão inteira e grava UM vídeo contínuo.
Os scripts da persona só mandam comandos, como um dedo e um par de olhos:

    import sys; sys.path.insert(0, "/app/input")
    from tela import Tela
    t = Tela()                       # liga a tela (ou reconecta, se já estiver ligada)
    t.abrir("http://...")            # só na primeira vez
    print(t.ver())                   # olha a tela: o que está visível agora e o que dá para tocar
    t.falar("Tô vendo três produtos. Vou tocar no primeiro.")
    print(t.tocar("Ver detalhes"))
    print(t.digitar("Seu e-mail", "maria@exemplo.com"))
    print(t.rolar())                 # rola para baixo ("cima", "direita", "esquerda"; sobre="texto" para um carrossel)
    t.encerrar()                     # no fim da sessão: fecha e salva o vídeo

Saída em TELA_SAIDA (padrão /app/output): video/seg_NN.webm (um por sessão da tela), fala_em_voz_alta.jsonl
({"segmento", "segundos", "fala"}) e eventos.jsonl (cada ação com início e fim), que ux/montar_video.py junta
num vídeo com voz e legenda, cortando os trechos em que a persona não fala nem mexe na tela.
Precisa do Playwright com Chromium (o ambiente application/shared-web-playwright do MatrAIx já tem).

Regras que imitam a vida real:
- Toque errado não quebra nada: o toque cai no que estiver por cima, no ponto tocado.
- Só dá para tocar no que está visível na tela agora.
- É preciso olhar a tela (ver) antes de tocar ou rolar de novo; ver espera o tempo de leitura.
- A tela NÃO dá dicas (moderador não ajuda durante o teste): só descreve o que se vê e o que se fez.
- O que a página faz entre um script e outro continua lá: nada recomeça sozinho.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORTA = int(os.environ.get("TELA_PORTA", "8799"))  # troque se outra tela já estiver usando a porta
SAIDA = Path(os.environ.get("TELA_SAIDA", "/app/output"))
LARGURA, ALTURA = 390, 844
OCIOSO_MAX = 600  # s sem comandos: fecha e salva o vídeo sozinho


# ---------------------------------------------------------------- cliente (scripts da persona)
class Tela:
    def __init__(self) -> None:
        if not self._ping():
            SAIDA.mkdir(parents=True, exist_ok=True)
            log = open(SAIDA / "tela_servidor.log", "a")
            subprocess.Popen([sys.executable, __file__, "servidor"], stdout=log, stderr=log,
                             start_new_session=True)
            for _ in range(120):
                time.sleep(0.5)
                if self._ping():
                    break
            else:
                raise RuntimeError("A tela não ligou. Veja /app/output/tela_servidor.log")

    def _ping(self) -> bool:
        try:
            return self._cmd("ping", _timeout=2) == "ok"
        except Exception:  # noqa: BLE001
            return False

    def _cmd(self, acao: str, _timeout: float = 120, **dados) -> str:
        req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/", method="POST",
                                     data=json.dumps({"acao": acao, **dados}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=_timeout) as r:
            return json.loads(r.read())["resposta"]

    def abrir(self, url: str) -> str: return self._cmd("abrir", url=url)
    def ver(self) -> str: return self._cmd("ver")
    def tocar(self, nome: str) -> str: return self._cmd("tocar", nome=nome)
    def tocar_fora(self) -> str: return self._cmd("tocar_fora")
    def digitar(self, campo: str, texto: str) -> str: return self._cmd("digitar", campo=campo, texto=texto)
    def rolar(self, direcao: str = "baixo", sobre: str = "") -> str:
        """direcao: baixo, cima, direita ou esquerda; sobre: texto visível onde o dedo arrasta (ex.: um carrossel)."""
        return self._cmd("rolar", direcao=direcao, sobre=sobre)
    def falar(self, texto: str) -> str: return self._cmd("falar", texto=texto)
    def esperar(self, segundos: float = 2) -> str: return self._cmd("esperar", segundos=segundos)
    def encerrar(self) -> str: return self._cmd("encerrar")


# ---------------------------------------------------------------- servidor (dono do navegador)
LER_TELA_JS = r"""
() => {
  const W = innerWidth, H = innerHeight;
  const topo = (el) => { const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom <= 0 || r.top >= H || r.right <= 0 || r.left >= W) return false;
    const x = Math.min(Math.max(r.left + r.width / 2, 1), W - 1), y = Math.min(Math.max(r.top + r.height / 2, 1), H - 1);
    const t = document.elementFromPoint(x, y); return !!t && (t === el || el.contains(t) || t.contains(el)); };
  const visivel = (el) => { const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.05; };
  const nomeDe = (el) => {
    let n = el.getAttribute('aria-label') || '';
    if (!n && el.id) { const l = document.querySelector(`label[for="${el.id}"]`); if (l) n = l.innerText; }
    if (!n && el.closest('label')) n = el.closest('label').innerText;
    if (!n) n = (el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('alt') || '').trim();
    return n.replace(/\s+/g, ' ').trim();
  };
  // barras fixas na parte de baixo (rodapé com total e botão, avisos): a pessoa vê como um bloco à parte
  const fixos = [...document.querySelectorAll('body *')].filter(e => { const p = getComputedStyle(e).position; const r = e.getBoundingClientRect(); return (p === 'fixed' || p === 'sticky') && r.top > H * 0.5 && r.height > 30 && r.height < H * 0.6 && visivel(e); });
  const naBarra = (el) => fixos.some(f => f.contains(el));
  // texto visível, na ordem de leitura, só o que não está coberto por outra coisa
  const linhas = [], linhasBarra = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode, s = n.textContent.replace(/\s+/g, ' ').trim(); if (!s) continue;
    const el = n.parentElement; if (!el || !visivel(el)) continue;
    const g = document.createRange(); g.selectNodeContents(n); const r = g.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= H || r.width < 1) continue;
    const x = Math.min(Math.max(r.left + Math.min(r.width, 20) / 2, 1), W - 1), y = Math.min(Math.max(r.top + r.height / 2, 1), H - 1);
    const t = document.elementFromPoint(x, y); if (!t || !(t === el || el.contains(t) || t.contains(el))) continue;
    (naBarra(el) ? linhasBarra : linhas).push({ y: Math.round(r.top), x: Math.round(r.left), s }); }
  const juntar = (ls) => { ls.sort((a, b) => a.y - b.y || a.x - b.x); const out = []; let ultY = -99;
    for (const l of ls) { if (Math.abs(l.y - ultY) <= 4 && out.length) out[out.length - 1] += '  ' + l.s; else out.push(l.s); ultY = l.y; } return out; };
  const texto = juntar(linhas), textoBarra = juntar(linhasBarra);
  // o que aparece pela metade na borda da tela (o que passa por trás da barra fixa não conta: a pessoa sabe que continua)
  const blocos = 'section,article,li,[class*=rounded],h2,h3,p';
  let cortado = '';
  if (!fixos.length) for (const el of document.querySelectorAll(blocos)) {
    const r = el.getBoundingClientRect(); if (r.height < 16 || r.width < 40) continue;
    if (r.top < H - 12 && r.bottom > H + 4) { const t = (el.innerText || '').replace(/\s+/g, ' ').trim(); if (t) { cortado = t.slice(0, 70); break; } } }
  let cortadoCima = '';
  for (const el of document.querySelectorAll(blocos)) { const r = el.getBoundingClientRect();
    if (r.height >= 16 && r.width >= 40 && r.top < -4 && r.bottom > 12) { const t = (el.innerText || '').replace(/\s+/g, ' ').trim(); if (t) { cortadoCima = t.slice(0, 70); break; } } }
  // o que dá para tocar
  const sel = 'button,a[href],input,textarea,select,[role=button],[role=switch],[role=radio],[role=checkbox],[role=link],[tabindex="0"]';
  const itens = [], itensBarra = []; const vistos = new Set();
  for (const el of document.querySelectorAll(sel)) {
    if (vistos.has(el) || !visivel(el) || !topo(el)) continue; vistos.add(el);
    const nome = nomeDe(el); if (!nome) continue;
    const tag = el.tagName.toLowerCase(), role = el.getAttribute('role');
    let tipo = (tag === 'input' || tag === 'textarea') ? 'campo' : role === 'switch' ? 'chave' : role === 'radio' ? 'opção' : role === 'checkbox' ? 'caixa' : tag === 'a' ? 'link' : 'botão';
    const est = [];
    const op = +getComputedStyle(el).opacity;
    if (el.disabled || el.getAttribute('aria-disabled') === 'true' || op < 0.6) est.push('parece desativado');
    if (role === 'switch' || role === 'radio' || role === 'checkbox') est.push(el.getAttribute('aria-checked') === 'true' ? 'ligado' : 'desligado');
    if (tipo === 'campo') est.push(el.value ? `preenchido: "${el.value}"` : 'vazio');
    (naBarra(el) ? itensBarra : itens).push(`- ${tipo} "${nome.slice(0, 80)}"${est.length ? ' (' + est.join(', ') + ')' : ''}`);
  }
  const mais = document.scrollingElement.scrollTop + H < document.scrollingElement.scrollHeight - 8;
  const acima = document.scrollingElement.scrollTop > 8;
  return { texto, itens, mais, acima, cortado, cortadoCima, textoBarra, itensBarra };
}
"""

ALVOS_JS = r"""
([nome, soCampos]) => {
  const W = innerWidth, H = innerHeight, alvo = nome.replace(/\s+/g, ' ').trim().toLowerCase();
  const nomeDe = (el) => { let n = el.getAttribute('aria-label') || '';
    if (!n && el.id) { const l = document.querySelector(`label[for="${el.id}"]`); if (l) n = l.innerText; }
    if (!n) n = (el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('alt') || '');
    return n.replace(/\s+/g, ' ').trim().toLowerCase(); };
  const sel = soCampos ? 'input,textarea,select' : 'button,a[href],input,textarea,select,[role=button],[role=switch],[role=radio],[role=checkbox],[role=link],[tabindex="0"],p,span,h1,h2,h3,li,label,div';
  const cand = [];
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const n = nomeDe(el); if (!n) continue;
    const exato = n === alvo, contem = n.includes(alvo) && n.length <= alvo.length * 3 + 20;
    if (!exato && !contem) continue;
    const naTela = r.bottom > 0 && r.top < H && r.right > 0 && r.left < W;
    const interativo = el.matches('button,a[href],input,textarea,select,[role=button],[role=switch],[role=radio],[role=checkbox],[role=link],[tabindex="0"]');
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    const t = naTela ? document.elementFromPoint(Math.min(Math.max(x, 1), W - 1), Math.min(Math.max(y, 1), H - 1)) : null;
    const descoberto = !!t && (t === el || el.contains(t) || t.contains(el));
    cand.push({ x, y, exato, interativo, naTela, descoberto, area: r.width * r.height });
  }
  cand.sort((a, b) => (b.naTela - a.naTela) || (b.descoberto - a.descoberto) || (b.exato - a.exato) || (b.interativo - a.interativo) || (a.area - b.area) || (a.y - b.y));
  return cand[0] || null;
}
"""


def servidor() -> None:
    from playwright.sync_api import sync_playwright

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "video").mkdir(exist_ok=True)
    pw = sync_playwright().start()
    nav = pw.chromium.launch(headless=True)
    estado = {"ctx": None, "page": None, "inicio": time.time(), "olhou": False, "ultimo": time.time(),
              "seg": len(list((SAIDA / "video").glob("seg_*.webm"))) + 1}

    def contexto():
        if estado["page"] is None:
            estado["ctx"] = nav.new_context(viewport={"width": LARGURA, "height": ALTURA}, has_touch=True,
                                            record_video_dir=str(SAIDA / "video" / "_bruto"),
                                            record_video_size={"width": LARGURA, "height": ALTURA}, locale="pt-BR")
            estado["page"] = estado["ctx"].new_page()
            estado["inicio"] = time.time()
        return estado["page"]

    def assinatura(page) -> str:
        try:
            return page.evaluate("() => location.href + '|' + document.body.innerText.length + '|' + document.body.innerText.slice(0, 400)")
        except Exception:  # noqa: BLE001
            return ""

    def salvar_video():
        if estado["page"] is None:
            return "Não havia tela aberta."
        v = estado["page"].video
        estado["ctx"].close()
        destino = SAIDA / "video" / f"seg_{estado['seg']:02d}.webm"
        try:
            Path(v.path()).rename(destino)
        except Exception:  # noqa: BLE001
            pass
        estado.update(page=None, ctx=None, seg=estado["seg"] + 1)
        return f"Sessão encerrada. Vídeo salvo em {destino}."

    def executar(d: dict) -> str:
        acao = d.get("acao")
        estado["ultimo"] = time.time()
        if acao == "ping":
            return "ok"
        if acao == "encerrar":
            return salvar_video()
        page = contexto()
        if acao == "falar":
            with open(SAIDA / "fala_em_voz_alta.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"segmento": estado["seg"], "segundos": round(time.time() - estado["inicio"], 1),
                                    "fala": d.get("texto", "")}, ensure_ascii=False) + "\n")
            palavras = len(str(d.get("texto", "")).split())
            page.wait_for_timeout(int(max(1.2, palavras / 2.4 + 0.4) * 1000))  # o tempo de dizer a frase
            return "ok"
        if acao == "esperar":
            page.wait_for_timeout(min(float(d.get("segundos", 2)), 15) * 1000)
            return "Esperou."
        if acao == "abrir":
            if page.url not in ("about:blank", "") and not d.get("de_novo"):
                return "O site já está aberto no celular."
            page.goto(d["url"], wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            estado["olhou"] = False
            return "O site abriu."
        if acao == "ver":
            v = page.evaluate(LER_TELA_JS)
            palavras = sum(len(l.split()) for l in v["texto"])
            page.wait_for_timeout(int(min(9, max(2.5, palavras / 4)) * 1000))  # tempo de leitura (~240 palavras/min)
            estado["olhou"] = True
            partes = ["[O que está na tela agora, de cima para baixo]",
                      *([f'(no alto, aparece cortado pela borda: "{v["cortadoCima"]}…")'] if v.get("cortadoCima") else []),
                      *(v["texto"] or ["(tela vazia)"]),
                      *([f'(embaixo, aparece cortado pela borda: "{v["cortado"]}…")'] if v.get("cortado") else []),
                      *(["(o fim da página está à vista)"] if not v["mais"] and not v.get("cortado") else []),
                      "", "[Onde dá para tocar ou digitar nesta parte da tela]", *(v["itens"] or ["(nada)"])]
            if v.get("textoBarra") or v.get("itensBarra"):
                partes += ["", "[Barra fixa na parte de baixo da tela, que fica sempre no lugar]",
                           *v.get("textoBarra", []), *v.get("itensBarra", [])]
            return "\n".join(partes)
        if acao in ("tocar", "tocar_fora", "rolar") and not estado["olhou"]:
            return "Primeiro olhe a tela (t.ver())."
        antes = assinatura(page)
        if acao == "rolar":
            x, y = LARGURA / 2, ALTURA / 2
            if d.get("sobre"):
                alvo = page.evaluate(ALVOS_JS, [d["sobre"], False])
                if not alvo or not alvo["naTela"]:
                    return f'Você não está vendo "{d["sobre"]}" na tela.'
                x, y = alvo["x"], alvo["y"]
            dx, dy = {"cima": (0, -500), "direita": (300, 0), "esquerda": (-300, 0)}.get(d.get("direcao"), (0, 500))
            pos = "() => [scrollX, scrollY, ...[...document.querySelectorAll('*')].filter(e => e.scrollHeight > e.clientHeight + 4 || e.scrollWidth > e.clientWidth + 4).map(e => e.scrollTop + ':' + e.scrollLeft)].join('|')"
            antes_pos = page.evaluate(pos)
            page.mouse.move(x, y)
            page.mouse.wheel(dx, dy)
            page.wait_for_timeout(900)
            estado["olhou"] = False
            return "Você rolou a tela." if page.evaluate(pos) != antes_pos else "Você tentou rolar, mas a tela não se moveu."
        if acao == "tocar_fora":
            page.mouse.click(LARGURA / 2, 40)
            page.wait_for_timeout(1200)
            estado["olhou"] = False
            return "Você tocou numa área vazia no alto da tela."
        if acao == "tocar":
            alvo = page.evaluate(ALVOS_JS, [d.get("nome", ""), False])
            if not alvo:
                return f'Você não está vendo "{d.get("nome")}" na tela.'
            if not alvo["naTela"]:
                return f'Você não está vendo "{d.get("nome")}" na tela.'
            page.mouse.click(alvo["x"], alvo["y"])  # um toque de dedo: vale o que estiver por cima naquele ponto
            page.wait_for_timeout(1500)
            estado["olhou"] = False
            return f'Você tocou em "{d.get("nome")}".'
        if acao == "digitar":
            alvo = page.evaluate(ALVOS_JS, [d.get("campo", ""), True])
            if not alvo or not alvo["naTela"]:
                return f'Você não está vendo o campo "{d.get("campo")}" na tela.'
            page.mouse.click(alvo["x"], alvo["y"])
            page.wait_for_timeout(300)
            # apaga o que já estava no campo tecla por tecla (Ctrl+A não seleciona tudo no macOS)
            atual = page.evaluate("() => document.activeElement && 'value' in document.activeElement ? document.activeElement.value.length : 0")
            if atual:
                page.keyboard.press("End")
                for _ in range(atual):
                    page.keyboard.press("Backspace")
            page.keyboard.type(str(d.get("texto", "")), delay=70)
            page.wait_for_timeout(500)
            valor = page.evaluate("() => document.activeElement && 'value' in document.activeElement ? document.activeElement.value : ''")
            return f'Você digitou no campo "{d.get("campo")}". Agora ele mostra: "{valor}".'
        return f"Não conheço a ação {acao}."

    def registrar(d: dict) -> str:
        """Executa e anota o intervalo da ação (eventos.jsonl), para o vídeo cortar os trechos parados."""
        acao = d.get("acao")
        if acao == "ping":
            return executar(d)
        if acao != "encerrar":
            contexto()  # o relógio do vídeo começa quando a tela liga
        seg, ini = estado["seg"], round(time.time() - estado["inicio"], 2)
        resp = executar(d)
        fim = ini if acao == "encerrar" else round(time.time() - estado["inicio"], 2)
        with open(SAIDA / "eventos.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"segmento": seg, "acao": acao, "inicio": ini, "fim": fim}) + "\n")
        return resp

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                resp = registrar(d)
            except Exception as e:  # noqa: BLE001  (nunca derruba a tela)
                resp = "O celular não respondeu a esse gesto."
            body = json.dumps({"resposta": resp}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # silencioso
            pass

    srv = HTTPServer(("127.0.0.1", PORTA), Handler)
    srv.timeout = 5
    while True:
        srv.handle_request()
        if estado["page"] is not None and time.time() - estado["ultimo"] > OCIOSO_MAX:
            salvar_video()


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "servidor":
    servidor()

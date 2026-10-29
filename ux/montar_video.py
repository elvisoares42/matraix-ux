"""Monta o vídeo da sessão de cada persona: tela gravada + voz (pensar em voz alta) + legenda.

Entrada, por tentativa do job (artifacts/app/output/):
  video/seg_XX.webm            gravação da tela, um arquivo por script da persona
  fala_em_voz_alta.jsonl       {"segmento": n, "segundos": t, "fala": "..."}

Saída: resultados/videos/<job>/<persona>.mp4, com o aviso "SIMULAÇÃO – persona sintética"
o tempo todo (para nunca ser confundido com gravação de cliente real).

A voz é gerada pela OpenAI, em português do Brasil, com uma voz compatível com o gênero e um tom compatível
com a idade e a facilidade com tecnologia. Dois níveis (--voz):
  melhorada (padrão): gpt-audio-1.5, mais natural e expressiva; ~US$ 0,40 por persona
  basica: gpt-4o-mini-tts, mais simples e bem mais barata; centavos por persona
Sem OPENAI_API_KEY (ou com --sem-voz), o vídeo sai só com legenda.

Uso (na raiz do MatrAIx, com a chave no ambiente, nunca em arquivo versionado):
  .venv/bin/python ux/montar_video.py jobs/<job> [--personas persona/datasets/<grupo>] [--voz basica|melhorada]
                                       [--sem-voz] [--sem-corte] [persona_id ...]
Por padrão corta os trechos em que a persona não fala nem mexe na tela (ex.: enquanto a IA pensa).
Saída: <job>/videos/<persona>.mp4 e <job>/videos/custo_voz.json
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import httpx
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _fonte(*nomes: str) -> str:
    """Primeira fonte que existir (macOS, Linux)."""
    for n in nomes:
        if Path(n).exists():
            return n
    return nomes[-1]


FONTE = _fonte("/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONTE_BOLD = _fonte("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
VOZ_NIVEL = sys.argv[sys.argv.index("--voz") + 1] if "--voz" in sys.argv else os.environ.get("UX_VOZ", "melhorada")
# vozes por gênero em cada nível (a voz básica usa as vozes do modelo de TTS)
VOZES = {"melhorada": {"Woman": ["marin"], "Man": ["cedar"]}, "basica": {"Woman": ["coral"], "Man": ["ash"]}}[VOZ_NIVEL]
VOZES.update({"Mulher": VOZES["Woman"], "Homem": VOZES["Man"], "Non-binary": VOZES["Woman"]})
SEM_VOZ = "--sem-voz" in sys.argv or not os.environ.get("OPENAI_API_KEY")
TOM_TECNOLOGIA = {
    "Digital native": "fala rápido e com segurança, um pouco impaciente",
    "Comfortable": "fala tranquila e prática",
    "Cautious adopter": "fala devagar, conferindo as coisas, com um pouco de desconfiança",
    "Reluctant": "fala hesitante, insegura com tecnologia, às vezes perdida",
    "Avoidant": "fala bem devagar, desconfortável e confusa com o celular",
}
LARG, ALT = 390, 844
# Corte de trechos parados: mantém fala e ações (com folga para ver o resultado) e encurta o resto.
SEM_CORTE = "--sem-corte" in sys.argv
PAUSA_MAX = 0.8          # s de tela parada mantidos entre dois trechos úteis
OLHAR_MAX = 1.5          # s mantidos de cada "ver" (a leitura em silêncio é encurtada)
FOLGA_ACAO = (0.3, 0.8)  # s antes e depois de um toque, digitação ou rolagem
USO_CORTE = {"antes_s": 0.0, "depois_s": 0.0}


def intervalos_uteis(eventos: list[dict], pistas: list, total: float) -> list[tuple[float, float]]:
    """Trechos com fala ou ação, unidos quando a pausa entre eles é curta."""
    blocos = [(max(0.0, ini - 0.2), ini + dur + 0.3) for _, ini, dur, _ in pistas]
    for e in eventos:
        a, b = float(e.get("inicio", 0)), float(e.get("fim", 0))
        if e.get("acao") == "falar":
            continue  # a fala já entra pelas pistas, na posição real do áudio
        if e.get("acao") in ("ver", "esperar"):
            blocos.append((a, min(b, a + OLHAR_MAX)))
        else:
            blocos.append((max(0.0, a - FOLGA_ACAO[0]), b + FOLGA_ACAO[1]))
    blocos = sorted((max(0.0, a), min(total, b)) for a, b in blocos if b > a)
    juntos: list[list[float]] = []
    for a, b in blocos:
        if juntos and a - juntos[-1][1] <= PAUSA_MAX:
            juntos[-1][1] = max(juntos[-1][1], b)
        else:
            juntos.append([a, b])
    # cada corte deixa PAUSA_MAX de respiro, para a edição não ficar seca
    return [(max(0.0, a - PAUSA_MAX / 2), min(total, b + PAUSA_MAX / 2)) for a, b in juntos]


def cortar_parados(arquivo: Path, intervalos: list[tuple[float, float]], total: float) -> Path:
    """Remove do trecho montado o que ficou fora dos intervalos úteis (vídeo, voz e legenda juntos)."""
    mantido = sum(b - a for a, b in intervalos)
    if not intervalos or mantido >= total - 0.5:
        return arquivo
    cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in intervalos)
    saida = arquivo.with_name(arquivo.stem + "_cortado.mp4")
    r = ffmpeg("-i", str(arquivo), "-vf", f"select='{cond}',setpts=N/FRAME_RATE/TB",
               "-af", f"aselect='{cond}',asetpts=N/SR/TB", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
               "-c:a", "aac", "-ar", "44100", "-ac", "1", str(saida))
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    USO_CORTE["antes_s"] += total
    USO_CORTE["depois_s"] += mantido
    return saida


def ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([FFMPEG, "-hide_banner", "-y", *args], capture_output=True, text=True)


def duracao(arquivo: Path) -> float:
    saida = subprocess.run([FFMPEG, "-hide_banner", "-i", str(arquivo)],
                           capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", saida)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


MODELO_VOZ = os.environ.get("UX_MODELO_VOZ") or {"melhorada": "gpt-audio-1.5", "basica": "gpt-4o-mini-tts"}[VOZ_NIVEL]
USO_VOZ = {"audio_tokens": 0, "text_tokens_saida": 0, "tokens_entrada": 0, "falas": 0, "segundos_audio": 0.0}


def _post(url: str, corpo: dict) -> httpx.Response:
    """Chamada à OpenAI com novas tentativas quando a API demora ou recusa por excesso de pedidos."""
    import time
    for tentativa in range(4):
        try:
            r = httpx.post(url, headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}, json=corpo, timeout=300)
            if r.status_code in (429, 500, 502, 503, 504) and tentativa < 3:
                time.sleep(5 * (tentativa + 1))
                continue
            r.raise_for_status()
            return r
        except (httpx.TimeoutException, httpx.TransportError):
            if tentativa == 3:
                raise
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError("a OpenAI não respondeu")


def gerar_voz(texto: str, voz: str, instrucoes: str, destino: Path) -> None:
    """Fala da persona em áudio, lida palavra por palavra (sem inventar nada)."""
    if destino.exists() or SEM_VOZ:
        return
    if VOZ_NIVEL == "basica":
        r = _post("https://api.openai.com/v1/audio/speech",
                  {"model": MODELO_VOZ, "voice": voz, "input": texto, "instructions": instrucoes, "response_format": "mp3"})
        destino.write_bytes(r.content)
        USO_VOZ["falas"] += 1
        USO_VOZ["segundos_audio"] += duracao(destino)
        return
    import base64
    corpo = {
        "model": MODELO_VOZ, "modalities": ["text", "audio"], "audio": {"voice": voz, "format": "mp3"},
        "messages": [
            {"role": "system", "content": instrucoes + " Você é uma pessoa dublando a própria fala: leia EXATAMENTE "
             "o texto do usuário, palavra por palavra, sem acrescentar, tirar ou responder nada."},
            {"role": "user", "content": texto},
        ],
    }
    for _ in range(2):
        r = _post("https://api.openai.com/v1/chat/completions", corpo)
        d = r.json()
        audio = d["choices"][0]["message"]["audio"]
        u = d.get("usage", {})
        USO_VOZ["audio_tokens"] += u.get("completion_tokens_details", {}).get("audio_tokens", 0)
        USO_VOZ["text_tokens_saida"] += u.get("completion_tokens_details", {}).get("text_tokens", 0)
        USO_VOZ["tokens_entrada"] += u.get("prompt_tokens", 0)
        USO_VOZ["falas"] += 1
        # confere se leu o texto como está (tolerando pontuação); senão, tenta mais uma vez
        limpo = lambda s: re.sub(r"[^\w]+", " ", s.lower()).strip()  # noqa: E731
        if limpo(audio.get("transcript", "")) == limpo(texto):
            break
    destino.write_bytes(base64.b64decode(audio["data"]))


def legenda(texto: str, pasta: Path, n: int) -> Path:
    arq = pasta / f"legenda_{n:03d}.txt"
    arq.write_text("\n".join(textwrap.wrap(texto, 34)), encoding="utf-8")
    return arq


def montar_segmento(video: Path, falas: list[dict], perfil: dict, voz: str, trab: Path,
                    seg: int, eventos: list[dict] | None = None) -> Path:
    """Um trecho: vídeo + falas posicionadas no tempo, sem sobreposição."""
    idade = perfil.get("age_bracket") or perfil.get("idade", "")
    instrucoes = (f"Fale em português do Brasil, com sotaque brasileiro natural, como uma pessoa "
                  f"de {idade} anos pensando em voz alta enquanto usa um site no celular. "
                  f"{TOM_TECNOLOGIA.get(perfil.get('tech_savviness', ''), '')}. Natural, sem tom de locutor.")
    cursor, pistas = 0.0, []
    for i, f in enumerate(falas):
        mp3 = trab / f"voz_{seg:02d}_{i:03d}.mp3"
        gerar_voz(f["fala"], voz, instrucoes, mp3)
        ini = max(float(f.get("segundos", 0)), cursor)
        # sem voz: a legenda fica o tempo de ler a frase
        dur = duracao(mp3) if mp3.exists() else max(1.5, len(f["fala"].split()) / 2.4)
        pistas.append((mp3 if mp3.exists() else None, ini, dur, f["fala"]))
        cursor = ini + dur + 0.3
    dur_video = duracao(video)
    total = max(dur_video, cursor + 0.5)

    entradas = ["-i", str(video)]
    for mp3, *_ in pistas:
        if mp3:
            entradas += ["-i", str(mp3)]
    filtros = [f"[0:v]scale={LARG}:{ALT},tpad=stop_mode=clone:stop_duration={max(0.0, total - dur_video):.2f}"]
    texto_aviso = trab / "aviso.txt"
    texto_aviso.write_text("SIMULAÇÃO – persona sintética", encoding="utf-8")
    nome = trab / "nome.txt"
    nome.write_text(f"{perfil.get('nome', '')} · {idade}", encoding="utf-8")
    filtros[0] += (f",drawbox=x=0:y=0:w=iw:h=54:color=black@0.65:t=fill"
                   f",drawtext=fontfile='{FONTE_BOLD}':textfile='{texto_aviso}':fontcolor=yellow:fontsize=17:x=(w-tw)/2:y=8"
                   f",drawtext=fontfile='{FONTE}':textfile='{nome}':fontcolor=white:fontsize=14:x=(w-tw)/2:y=32")
    for i, (_, ini, dur, fala) in enumerate(pistas):
        arq = legenda(fala, trab, seg * 1000 + i)
        filtros[0] += (f",drawtext=fontfile='{FONTE}':textfile='{arq}':fontcolor=white:fontsize=17"
                       f":line_spacing=4:box=1:boxcolor=black@0.7:boxborderw=10"
                       f":x=(w-tw)/2:y=h-th-40:enable='between(t,{ini:.2f},{ini + dur:.2f})'")
    filtros[0] += "[v]"
    com_audio = [(ini, mp3) for mp3, ini, _, _ in pistas if mp3]
    if com_audio:
        for i, (ini, _) in enumerate(com_audio, start=1):
            filtros.append(f"[{i}:a]adelay={int(ini * 1000)}:all=1[a{i}]")
        filtros.append("".join(f"[a{i}]" for i in range(1, len(com_audio) + 1))
                       + f"amix=inputs={len(com_audio)}:normalize=0,apad=whole_dur={total:.2f}[a]")
    else:
        filtros.append(f"anullsrc=r=44100:cl=mono,atrim=duration={total:.2f}[a]")
    saida = trab / f"trecho_{seg:02d}.mp4"
    r = ffmpeg(*entradas, "-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
               "-t", f"{total:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
               "-c:a", "aac", "-ar", "44100", "-ac", "1", str(saida))
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    if eventos and not SEM_CORTE:  # gravações antigas, sem eventos.jsonl, saem sem corte
        return cortar_parados(saida, intervalos_uteis(eventos, pistas, total), total)
    return saida


def montar_persona(saida_app: Path, perfil: dict, destino: Path) -> Path | None:
    videos = sorted((saida_app / "video").glob("*.webm"), key=lambda p: (not p.name.startswith("seg_"), p.name))
    # pula gravações corrompidas (script da persona que não fechou o navegador)
    videos = [v for v in videos if duracao(v) > 0]
    if not videos:
        return None
    falas = []
    arq_falas = saida_app / "fala_em_voz_alta.jsonl"
    if arq_falas.exists():
        for linha in arq_falas.read_text(encoding="utf-8").splitlines():
            try:
                falas.append(json.loads(linha))
            except json.JSONDecodeError:
                pass
    eventos = []
    arq_ev = saida_app / "eventos.jsonl"
    if arq_ev.exists():
        for linha in arq_ev.read_text(encoding="utf-8").splitlines():
            try:
                eventos.append(json.loads(linha))
            except json.JSONDecodeError:
                pass
    voz_lista = VOZES.get(perfil.get("gender_identity") or perfil.get("sexo", ""), VOZES["Woman"])
    voz = voz_lista[sum(map(ord, perfil.get("persona_id", "0"))) % len(voz_lista)]
    trab = destino.parent / f".trabalho_{destino.stem}"
    trab.mkdir(parents=True, exist_ok=True)
    trechos = []
    for ordem, video in enumerate(videos, start=1):
        m = re.match(r"seg_(\d+)", video.name)
        seg = int(m[1]) if m else ordem
        trechos.append(montar_segmento(video, [f for f in falas if int(f.get("segmento", 0)) == seg],
                                       perfil, voz, trab, seg, [e for e in eventos if int(e.get("segmento", 0)) == seg]))
    lista = trab / "lista.txt"
    lista.write_text("".join(f"file '{t}'\n" for t in trechos), encoding="utf-8")
    r = ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(destino))
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return destino


def carregar_perfis(pasta: Path | None) -> dict:
    """Perfis das personas a partir de um dataset do MatrAIx (persona_*.yaml) ou de um CSV/JSONL."""
    perfis = {}
    if not pasta:
        return perfis
    if pasta.is_file() and pasta.suffix == ".csv":
        return {r["persona_id"]: r for r in csv.DictReader(open(pasta, encoding="utf-8"))}
    if pasta.is_file() and pasta.suffix == ".jsonl":
        return {(d := json.loads(l))["persona_id"]: d for l in open(pasta, encoding="utf-8") if l.strip()}
    import yaml
    for arq in sorted(pasta.glob("persona_*.yaml")):
        doc = yaml.safe_load(arq.read_text(encoding="utf-8"))
        perfis[str(doc["persona_id"])] = {**doc.get("dimensions", {}), "nome": doc.get("display_name", "")}
    return perfis


def main() -> None:
    """Pula vídeos já montados; monta 4 personas em paralelo."""
    from concurrent.futures import ThreadPoolExecutor

    args = [a for a in sys.argv[1:] if a not in ("--sem-voz", "--sem-corte")]
    if "--voz" in args:
        i = args.index("--voz")
        del args[i:i + 2]
    personas = None
    if "--personas" in args:
        i = args.index("--personas")
        personas = Path(args[i + 1])
        del args[i:i + 2]
    raiz, so = Path(args[0]), set(args[1:])
    perfis = carregar_perfis(personas)
    pasta = raiz / "videos"
    pasta.mkdir(parents=True, exist_ok=True)

    def uma(trial: Path) -> None:
        meta = trial / "persona_meta.json"
        pid = str(json.loads(meta.read_text()).get("persona_id")) if meta.exists() else trial.name
        if so and pid not in so:
            return
        perfil = {**perfis.get(pid, {}), "persona_id": pid}
        saida_app = next(trial.rglob("app/output"), None) or trial
        nome = re.sub(r"[^A-Za-z0-9]+", "-", perfil.get("nome", pid)).strip("-")
        destino = pasta / f"{pid}_{nome}.mp4"
        if destino.exists() and not so:
            print(f"{pid}: já montado"); return
        try:
            v = montar_persona(saida_app, perfil, destino)
            print(f"{pid} {perfil.get('nome', '')}: {v if v else 'sem vídeo gravado'}"
                  + (f"  ({duracao(v):.0f}s)" if v else ""), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{pid}: erro ao montar — {str(e)[-400:]}", flush=True)

    tentativas = sorted(p for p in raiz.iterdir() if p.is_dir() and p.name != "videos")
    if (raiz / "video").exists():  # uma pasta de saída solta (ex.: teste local da tela)
        tentativas = [raiz]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(uma, tentativas))
    # custo da voz: melhorada pelos tokens medidos (áudio estimado em US$ 64–80 por milhão de tokens);
    # básica pelos minutos de áudio (gpt-4o-mini-tts, estimado em ~US$ 0,015 por minuto)
    if USO_CORTE["antes_s"]:
        print(f"cortes: {USO_CORTE['antes_s']:.0f}s → {USO_CORTE['depois_s']:.0f}s de vídeo")
    uso = dict(USO_VOZ, modelo=MODELO_VOZ, sem_voz=SEM_VOZ,
               custo_estimado_usd=([round(USO_VOZ["segundos_audio"] / 60 * 0.015, 3)] * 2 if VOZ_NIVEL == "basica" else
                                   [round(USO_VOZ["audio_tokens"] * p / 1e6 + USO_VOZ["tokens_entrada"] * 2.5 / 1e6, 3)
                                    for p in (64, 80)]))
    (pasta / "custo_voz.json").write_text(json.dumps(uso, ensure_ascii=False, indent=1), encoding="utf-8")
    print("voz:", uso)


if __name__ == "__main__":
    main()

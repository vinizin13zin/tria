"""Recorta a tomada única da narração (saida/narracao/tomada.mp3) em falas
e sincroniza cada uma com a legenda correspondente de timeline.js.

- Divide pelas 19 maiores pausas (o roteiro usa [long pause] entre falas)
- Se uma fala não cabe no espaço até a próxima, acelera até 1.18x
- Atualiza t0/t1/cps das legendas para o texto "digitar" no ritmo da voz
- Gera saida/narracao/vo_XX.wav e tempos.json (lidos por audio.py)
"""
import json, os, re, subprocess, wave
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "saida", "narracao")
TLP = os.path.join(HERE, "timeline.js")
tl = json.loads(re.sub(r"^[^=]*=", "", open(TLP, encoding="utf8").read()).strip().rstrip(";"))
subs = tl["subs"]
n_lines = len(subs)

LINHAS = os.path.join(D, "linhas")
segs = []
if os.path.isdir(LINHAS):
    # uma fala por arquivo (voz_kokoro.py)
    for k in range(n_lines):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(LINHAS, f"{k:02d}.wav"), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                           capture_output=True, check=True).stdout
        y = np.frombuffer(r, "<i2").astype(np.float64) / 32768.0
        e = np.abs(y) > 0.01
        a0, b0 = np.argmax(e), len(y) - np.argmax(e[::-1])
        segs.append(y[max(0, a0 - 1500): b0 + 3000])
else:
    # tomada única (ElevenLabs): divide pelas maiores pausas
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(D, "tomada.mp3"), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float64) / 32768.0
    hop = SR // 100
    nf = len(x) // hop
    rms = np.sqrt((x[: nf * hop].reshape(nf, hop) ** 2).mean(1) + 1e-12)
    voiced = 20 * np.log10(rms / rms.max()) > -38
    runs, i = [], 0
    while i < nf:
        if not voiced[i]:
            j = i
            while j < nf and not voiced[j]: j += 1
            if i > 0 and j < nf: runs.append((i, j))
            i = j
        else: i += 1
    runs.sort(key=lambda r: r[1] - r[0], reverse=True)
    prev = 0
    for a, b in sorted(runs[: n_lines - 1]) + [(nf, nf)]:
        idx = np.where(voiced[prev:a])[0]
        s0, s1 = prev + idx[0], prev + idx[-1] + 1
        segs.append(x[max(0, s0 * hop - 2205): min(len(x), s1 * hop + 4410)])
        prev = b

tempos = []
for k, seg in enumerate(segs):
    dur = len(seg) / SR
    s = subs[k]
    start = 0.15 if k == 0 else s["t0"]
    nxt = subs[k + 1]["t0"] if k + 1 < n_lines else tl["duration"]
    room = nxt - start - 0.2
    if k == 0: room = subs[1]["t0"] - start - 0.1 if n_lines > 1 else room
    tempo = 1.0
    if dur > room: tempo = min(1.18, dur / room)
    out = os.path.join(D, f"vo_{k:02d}.wav")
    tmp = out + ".raw"
    (seg * 32767).astype("<i2").tofile(tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", tmp,
                    "-af", f"atempo={tempo:.3f}", out], check=True)
    os.remove(tmp)
    with wave.open(out) as w: dur = w.getnframes() / SR
    tempos.append({"file": os.path.basename(out), "start": round(start, 3), "dur": round(dur, 3), "tempo": round(tempo, 3)})
    # legenda acompanha a voz
    s["t0"] = round(start, 2)
    s["t1"] = round(min(max(s["t1"], start + dur + 0.35), nxt - 0.08), 2)
    s["cps"] = round(len(s["text"]) / max(0.6, dur * 0.92), 1)
    print(f"{k:02d} {start:6.2f}s  {dur:5.2f}s  x{tempo:.2f}  {s['text']}")


json.dump(tempos, open(os.path.join(D, "tempos.json"), "w"), indent=1)
open(TLP, "w", encoding="utf8").write("window.TL = " + json.dumps(tl, ensure_ascii=False, indent=2) + ";\n")
print("ok", len(tempos), "falas")

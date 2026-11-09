"""Ajusta cada legenda de timeline.js à duração real da fala (saida/falas/XX.wav):
o texto é "digitado" no ritmo da voz e some logo depois que ela termina."""
import json, os, re, wave
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "timeline.js")
tl = json.loads(re.sub(r"^[^=]*=", "", open(P, encoding="utf8").read()).strip().rstrip(";"))
subs = tl["subs"]
for i, s in enumerate(subs):
    with wave.open(os.path.join(HERE, "saida", "falas", f"{i:02d}.wav")) as w:
        dur = w.getnframes() / w.getframerate()
    nxt = subs[i + 1]["t0"] if i + 1 < len(subs) else tl["duration"]
    s["dur"] = round(dur, 3)
    s["t1"] = round(min(max(s["t1"], s["t0"] + dur + 0.4), nxt - 0.08), 2)
    s["cps"] = round(len(s["text"]) / max(0.5, dur * 0.9), 1)
    if s["t0"] + dur > nxt: print("AVISO: fala", i, "invade a próxima")
open(P, "w", encoding="utf8").write("window.TL = " + json.dumps(tl, ensure_ascii=False, indent=1) + ";\n")
print("ok", len(subs))

"""Gera as falas da narração offline com Kokoro-82M v1.0 (vozes masculinas pt-BR).

Modelo e vozes vêm de pacotes npm: kokoro-q8-shards (model_quantized.onnx em
6 partes) e expo-kokoro (build/voices/pm_*.bin). Requer: pip install kokoro-onnx
Uso: python3 voz.py <pasta com kokoro.onnx e voices.npz>
Lê timeline.js (campos say/voice/speed/fx) e grava saida/falas/XX.wav (44.1 kHz).
"""
import json, os, re, subprocess, sys, wave
import numpy as np
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.loads(re.sub(r"^[^=]*=", "", open(os.path.join(HERE, "timeline.js"), encoding="utf8").read()).strip().rstrip(";"))
OUT = os.path.join(HERE, "saida", "falas"); os.makedirs(OUT, exist_ok=True)
k = Kokoro(os.path.join(sys.argv[1], "kokoro.onnx"), os.path.join(sys.argv[1], "voices.npz"))

FX = {
    # narrador: 2 semitons mais grave, comprimido
    "": "asetrate={sr}*0.89090,aresample=44100,atempo=1.12246,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80",
    # voz no telefone: banda estreita, saturada e trêmula (choro)
    # rádio de emergência: banda estreita, saturado, com zumbido
    "radio": "asetrate={sr}*0.94387,aresample=44100,atempo=1.05946,highpass=f=420,lowpass=f=2800,acrusher=bits=8:mix=0.25,"
             "acompressor=threshold=-24dB:ratio=8:attack=2:release=50,volume=2.2,alimiter=limit=0.6",
    # voz atrás da porta: abafada, e cada vez mais grave (a imitação "escorrega")
    "door": "asetrate={sr}*0.97,aresample=44100,atempo=1.03,lowpass=f=1300,highpass=f=120,aecho=0.8:0.6:35|70:0.3|0.2,"
            "vibrato=f=5:d=0.08,acompressor=threshold=-20dB:ratio=4,volume=1.6",
    # multidão: sussurrada (sem graves), com eco de rua
    "crowd": "highpass=f=380,lowpass=f=7000,aecho=0.8:0.7:60|140|260:0.35|0.25|0.15,acompressor=threshold=-26dB:ratio=6,volume=1.4",
    "phone": "asetrate={sr}*0.94387,aresample=44100,atempo=1.05946,highpass=f=350,lowpass=f=3200,tremolo=f=7:d=0.25,"
             "acompressor=threshold=-24dB:ratio=6:attack=2:release=50,volume=2.5,alimiter=limit=0.6",
}
def crowd(text, speed):
    """multidão sussurrando junta: 3 vozes, tons e atrasos diferentes"""
    parts = []
    for v, sh, dl in [("pm_alex", 1.0, 0.0), ("pm_santa", 0.94, 0.045), ("pf_dora", 1.06, 0.09), ("pm_alex", 0.88, 0.13)]:
        a, sr_ = k.create(text, voice=v, speed=speed * sh, lang="pt-br")
        a = np.concatenate([np.zeros(int(dl * sr_)), a / (np.abs(a).max() + 1e-9)])
        parts.append(a)
    n = max(len(p) for p in parts)
    return sum(np.pad(p, (0, n - len(p))) for p in parts) / 3.0, sr_


for i, s in enumerate(TL["subs"]):
    if s["fx"] == "crowd": audio, sr = crowd(s["say"], s["speed"])
    else: audio, sr = k.create(s["say"], voice=s["voice"], speed=s["speed"], lang="pt-br")
    tmp = os.path.join(OUT, f"{i:02d}_raw.wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(audio / (np.abs(audio).max() + 1e-9) * 0.9, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", FX[s["fx"]].format(sr=sr) + ",loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", os.path.join(OUT, f"{i:02d}.wav")], check=True)
    os.remove(tmp)
    print(f"{i:02d} {len(audio)/sr:5.2f}s  [{s['voice']}{'/'+s['fx'] if s['fx'] else ''}] {s['say']}")

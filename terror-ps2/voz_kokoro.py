"""Narração offline com Kokoro-82M v1.0 (voz masculina pt-BR "pm_alex").

O modelo e as vozes vêm de pacotes npm (registry liberado neste ambiente):
  - kokoro-q8-shards  -> model_quantized.onnx em 6 partes
  - expo-kokoro       -> build/voices/pm_alex.bin
Requer: pip install kokoro-onnx
Uso: python3 voz_kokoro.py <pasta_com_kokoro.onnx_e_voices.npz>
Gera saida/narracao/linhas/XX.wav (44.1 kHz), uma por legenda de timeline.js.
"""
import json, os, re, subprocess, sys, wave
import numpy as np
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
MD = sys.argv[1]
OUT = os.path.join(HERE, "saida", "narracao", "linhas")
os.makedirs(OUT, exist_ok=True)

# texto falado de cada legenda (mesma ordem de timeline.js) e velocidade
FALAS = [
    ("Se você estivesse sozinho em casa...", 0.82),
    ("e um jogo soubesse onde você mora?", 0.84),
    ("Dois mil e quatro. A locadora do seu bairro ia fechar.", 0.92),
    ("O dono te deu um jogo de graça. Sem nome.", 0.9),
    ("Na capa preta, só um aviso: não jogue sozinho.", 0.88),
    ("Você jogou sozinho.", 0.85),
    ("O jogo começava na frente de uma casa.", 0.9),
    ("Era a sua casa.", 0.8),
    ("O seu personagem entrou no seu quarto.", 0.9),
    ("Tinha um menino jogando. De costas.", 0.86),
    ("E atrás dele... tinha uma coisa.", 0.8),
    ("Você sentiu um bafo gelado na nuca.", 0.86),
    ("Você virou.", 0.8),
    ("Nada.", 0.75),
    ("No jogo, o monstro tinha sumido.", 0.88),
    ("E o menino da tela... olhou pra você.", 0.82),
    ("Ele nunca esteve dentro do jogo.", 0.85),
    ("Ele estava jogando.", 0.78),
    ("Jogador dois... conectado.", 0.78),
    ("Se você está ouvindo isso... ele já sabe onde você mora.", 0.84),
]

k = Kokoro(os.path.join(MD, "kokoro.onnx"), os.path.join(MD, "voices.npz"))
for i, (txt, spd) in enumerate(FALAS):
    s, sr = k.create(txt, voice="pm_alex", speed=spd, lang="pt-br")
    tmp = os.path.join(OUT, f"{i:02d}_raw.wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(s / (np.abs(s).max() + 1e-9) * 0.9, -1, 1) * 32767).astype("<i2").tobytes())
    # 2 semitons mais grave (voz mais pesada), mantendo a duração
    f = 2 ** (-2 / 12)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    f"asetrate={sr}*{f:.5f},aresample=44100,atempo={1/f:.5f},highpass=f=70,"
                    "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", os.path.join(OUT, f"{i:02d}.wav")], check=True)
    os.remove(tmp)
    print(f"{i:02d} {len(s)/sr:5.2f}s  {txt}")

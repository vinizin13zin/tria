#!/usr/bin/env bash
# Gera o vídeo completo: quadros (Chromium headless) + áudio (numpy) -> saida/o_jogador.mp4
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
node render.js saida/frames "${WORKERS:-4}"
ffmpeg -y -loglevel error -framerate 30 -i saida/frames/f_%05d.jpg -i saida/audio.wav \
  -c:v libx264 -preset medium -b:v 2000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p \
  -c:a aac -b:a 160k -shortest -movflags +faststart saida/o_jogador.mp4
echo "pronto: saida/o_jogador.mp4"

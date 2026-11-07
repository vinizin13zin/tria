#!/usr/bin/env bash
# Gera o curta "03:33": falas (Kokoro) -> legendas sincronizadas -> trilha -> quadros -> mp4
# Uso: ./build.sh <pasta com kokoro.onnx e voices.npz>   (ver voz.py)
set -euo pipefail
cd "$(dirname "$0")"
python3 voz.py "$1"
python3 sincroniza.py
python3 audio.py
node render.js saida/frames "${WORKERS:-4}"
ffmpeg -y -loglevel error -framerate 30 -i saida/frames/f_%05d.jpg -i saida/audio.wav \
  -c:v libx264 -preset medium -b:v 2000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p \
  -c:a aac -b:a 160k -shortest -movflags +faststart saida/0333.mp4
echo "pronto: saida/0333.mp4"

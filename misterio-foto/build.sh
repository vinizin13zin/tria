#!/usr/bin/env bash
# Gera o curta "A Foto": falas (Kokoro) -> legendas sincronizadas -> trilha -> quadros -> mp4
# Uso: ./build.sh <pasta com kokoro.onnx e voices.npz>   (ver voz.py)
set -euo pipefail
cd "$(dirname "$0")"
python3 voz.py "$1"
python3 sincroniza.py
python3 audio.py
node render.js saida/frames "${WORKERS:-4}"
ffmpeg -y -loglevel error -framerate 30 -i saida/frames/f_%05d.jpg -i saida/audio.wav \
  -c:v libx264 -preset medium -b:v 3500k -maxrate 5000k -bufsize 10000k -pix_fmt yuv420p \
  -c:a aac -b:a 160k -shortest -movflags +faststart saida/a_foto.mp4
echo "pronto: saida/a_foto.mp4"

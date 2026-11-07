# O JOGADOR — curta de terror estilo PS2 (1min30, vertical 9:16)

Vídeo final: [`saida/o_jogador.mp4`](saida/o_jogador.mp4) — 720×1280, 30 fps, 93 s, narrado, pronto para TikTok / Reels / Shorts.

Narração em segunda pessoa, voz masculina neural (Kokoro-82M, voz `pm_alex`, gerada offline por `voz_kokoro.py`), sincronizada com as legendas por `narracao.py`.

## A história

> **"ESSE JOGO NUNCA FOI LANÇADO. ...MAS ALGUÉM ESTÁ JOGANDO."**

2004. A locadora do bairro vai fechar e o dono dá ao Caio um jogo sem nome, numa capa preta
com um único aviso: **NÃO JOGUE SOZINHO**. Ele joga sozinho. O jogo começa na frente de uma
casa — a casa *dele*. O personagem entra no quarto dele e encontra um menino jogando, de costas.
Atrás do menino, **uma coisa**. Caio sente um bafo gelado na nuca, vira... nada. A TV pergunta
`SALVAR PROGRESSO? ▶SIM SIM`. Na tela, o menino vira a cabeça 180° e olha pra ele — e o monstro
desce do teto, atravessando o forro.

**Reviravolta:** "CARREGANDO... SLOT 2". A câmera recua de uma TV que mostra o Caio, parado,
encarando a tela... e quem segura o controle é o monstro. *Ele nunca esteve dentro do jogo.
Ele estava JOGANDO.* Final: **JOGADOR 2 CONECTADO.** — o espectador é o próximo.

### O monstro — "O Jogador"
2,5 m, magro demais, braços que arrastam no chão com dedos de 30 cm. A cabeça é **de cabeça pra
baixo**: um sorriso gigante cheio de dentes no topo, olhos humanos pequenos e injetados embaixo,
cada um olhando pra um lado, lágrimas escorrendo *pra cima* e um terceiro olho vertical no queixo.
Tem uma boca vertical no peito, costelas e vértebras saltadas, se mexe "travado" a 8 fps e solta
fragmentos de polígonos rasgados como um bug de PS2.

## Visual PS2
- Render interno em **240×426** ampliado 3× por vizinho mais próximo
- **Tremor de vértices** (snap em espaço de tela no vertex shader)
- Cores de 15 bits com **dithering Bayer 4×4**, granulação e scanlines
- Texturas procedurais de baixa resolução sem filtragem, neblina densa, low-poly
- Cenas "dentro do jogo" ainda mais tremidas, com HUD e lanterna

## Como gerar de novo
Requisitos: Node + Playwright (Chromium), Python 3 + numpy, ffmpeg.

```bash
./build.sh                        # áudio + 2700 quadros + mp4
node render.js --at 41.6,71.7     # prévia de instantes específicos (saida/previa)
```
`index.html` também roda direto no navegador (botão ▶ ASSISTIR) para prévia em tempo real.

| Arquivo | O quê |
|---|---|
| `timeline.js` | roteiro: cenas, legendas e marcas de tempo (compartilhado por vídeo e áudio) |
| `index.html` | cenas 3D (three.js), personagens, monstro, pós-processamento PS2 e legendas |
| `render.js` | captura quadro a quadro no Chromium headless (paralelo) |
| `audio.py` | trilha 100% sintetizada: drone, chuva, passos, cantiga de caixinha de música, batimentos, ossos estalando, grito |
| `voz_kokoro.py` | gera as 20 falas da narração (pt-BR, masculina) |
| `narracao.py` | encaixa cada fala na cena e ajusta o ritmo das legendas |
| `build.sh` | junta tudo em `saida/o_jogador.mp4` |

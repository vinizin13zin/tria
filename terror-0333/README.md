# 03:33 — curta de terror estilo PS2 (1min32, vertical 9:16, narrado)

Vídeo: [`saida/0333.mp4`](saida/0333.mp4)

> **"Se você recebesse uma ligação do seu próprio número... você atenderia?"**

3:33 da manhã. O seu celular toca — no visor, o SEU número. Do outro lado, a sua voz, chorando:
*"Por favor... não abre a porta. Você não é eu."* A voz vem também de trás da porta. Pelo olho
mágico: você, do lado de fora, chorando de medo. *"Olha as suas mãos."* Elas não são mãos de gente.
No espelho, você está sorrindo de orelha a orelha. Ele não tinha medo de um monstro — tinha medo
de VOCÊ. E você abre a porta.
Final: *"Se o seu número te ligar hoje às 3:33... NÃO ATENDE. Pode ser o verdadeiro você... tentando te avisar."*

- Narração em segunda pessoa, voz masculina neural offline (Kokoro, `pm_alex`); a voz no telefone
  usa outra voz masculina (`pm_santa`) com filtro de linha telefônica e tremor de choro.
- Mesmo motor visual PS2 de `../terror-ps2` (baixa resolução, tremor de vértices, dithering), com
  espelho com reflexo real, visão de olho mágico (olho de peixe) e zoom de impacto nos sustos.

| Arquivo | O quê |
|---|---|
| `timeline.js` | roteiro: cenas, marcas de tempo, legendas e texto falado |
| `voz.py` / `sincroniza.py` | gera as falas e ajusta as legendas ao ritmo da voz |
| `audio.py` | trilha sintetizada + mixagem com a narração (-14 LUFS) |
| `index.html` / `render.js` | cenas 3D e captura quadro a quadro |
| `build.sh` | tudo de uma vez |

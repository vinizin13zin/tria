"""Trilha sonora sintetizada do curta "O Jogador" (só numpy).

Lê os tempos de timeline.js para que legendas, cortes e sustos fiquem
sincronizados com o vídeo. Gera saida/audio.wav (44.1 kHz, estéreo).
"""
import json, os, re, wave
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.loads(re.sub(r"^[^=]*=", "", open(os.path.join(HERE, "timeline.js"), encoding="utf8").read()).strip().rstrip(";"))
M = TL["marks"]
DUR = TL["duration"]
N = int(DUR * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(13)


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def noise(sec):
    return rng.standard_normal(int(sec * SR))


def filt(x, lo=None, hi=None, order=4):
    """filtro passa-banda suave via FFT"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR) + 1e-9
    g = np.ones_like(f)
    if hi: g *= 1 / (1 + (f / hi) ** order)
    if lo: g *= 1 / (1 + (lo / f) ** order)
    return np.fft.irfft(X * g, len(x))


def env(n, a=0.005, r=None, sec=None):
    sec = sec or n / SR
    tt = np.arange(n) / SR
    e = np.clip(tt / max(a, 1e-4), 0, 1)
    if r: e *= np.exp(-tt / r)
    return e


def add(start, sig, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def crush(x, bits=8, down=4):
    x = np.repeat(x[::down], down)[: len(x)]
    q = 2 ** (bits - 1)
    return np.round(x * q) / q


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)


# ---------------- camadas contínuas ----------------
def drone():
    tt = np.arange(N) / SR
    d = (np.sin(2 * np.pi * 41 * tt) + 0.8 * np.sin(2 * np.pi * 41.6 * tt)
         + 0.5 * np.sin(2 * np.pi * 55.2 * tt + np.sin(tt * 0.3)) + 0.3 * np.sin(2 * np.pi * 82.7 * tt))
    d = d / 2.6 + 0.6 * norm(filt(rng.standard_normal(N), 30, 180))
    lvl = np.zeros(N)
    pts = [(0, .55), (5.5, .2), (18, .25), (31, .4), (40, .5), (47, .45), (60, .5), (68.5, .7), (73, 0), (74, .25),
           (77, .55), (86, .8), (88.5, 0), (90, 0)]
    xs, ys = zip(*pts)
    lvl = np.interp(tt, xs, ys)
    lvl[(tt >= M["black"]) & (tt < 74)] = 0
    add(0, d * lvl, 0.5)


def rain():
    n = noise(18 - 5.5)
    r = norm(filt(n, 500, 6000)) * 0.6 + norm(filt(n, 80, 500)) * 0.3
    fade = np.clip(t_(12.5) / 0.6, 0, 1) * np.clip((12.5 - t_(12.5)) / 0.4, 0, 1)
    add(5.5, r * fade, 0.34, -0.2)
    add(5.5, np.roll(r, 3000) * fade, 0.34, 0.2)
    # chuva abafada pela janela no quarto
    n2 = noise(13)
    add(18, norm(filt(n2, 60, 500)) * np.clip((13 - t_(13)) / 1, 0, 1), 0.08)
    # pingos
    for k in range(260):
        st = 5.5 + rng.random() * 12.3
        c = noise(0.02) * env(int(0.02 * SR), 0.0005, 0.004)
        add(st, filt(c, 1500, 7000), 0.25, rng.uniform(-0.8, 0.8))


def neon_buzz():
    tt = t_(12.5)
    b = np.sign(np.sin(2 * np.pi * 120 * tt)) * 0.5 + np.sin(2 * np.pi * 240 * tt) * 0.3
    b = filt(b, 80, 1500)
    gate = np.ones_like(tt)
    for k in range(int(12.5 * 9)):
        if k % 13 == 0: gate[int(k / 9 * SR):int((k + 1) / 9 * SR)] = 0.1
    add(5.5, b * gate, 0.025)


def tv_hum():
    tt = t_(74 - 18)
    h = np.sin(2 * np.pi * 60 * tt) + 0.5 * np.sin(2 * np.pi * 120 * tt) + 0.2 * np.sin(2 * np.pi * 15734 * tt)
    h += 0.25 * norm(filt(rng.standard_normal(len(tt)), 2000, 9000))
    add(18, h, 0.03)
    tt = t_(88.5 - 77)
    h = np.sin(2 * np.pi * 60 * tt) + 0.6 * norm(filt(rng.standard_normal(len(tt)), 1500, 8000))
    add(77, h, 0.03)


# ---------------- eventos ----------------
def footstep_wet(st, g=0.5):
    n = noise(0.09) * env(int(0.09 * SR), 0.002, 0.025)
    add(st, filt(n, 200, 2500), g, rng.uniform(-0.2, 0.2))


def footstep_wood(st, g=0.5):
    tt = t_(0.18)
    s = np.sin(2 * np.pi * (95 - 40 * tt) * tt) * np.exp(-tt / 0.05) + filt(noise(0.18), 800, 4000) * np.exp(-tt / 0.01) * 0.4
    add(st, crush(s, 6, 3), g)


def blips():
    for s in TL["subs"]:
        cps = 22 if s["kind"] == "big" else 30
        freq = 520 if s["kind"] == "big" else 1250
        txt = s["text"]
        for i, ch in enumerate(txt):
            st = s["t0"] + i / cps
            if st > s["t1"] or ch == " " or i % 2: continue
            tt = t_(0.014)
            b = np.sign(np.sin(2 * np.pi * freq * tt)) * env(len(tt), 0.001, 0.006)
            add(st, b, 0.06 if s["kind"] != "big" else 0.09)


def music_box(start, end, g=0.2):
    # cantiga de ninar menor, levemente desafinada
    notes = [69, 72, 76, 74, 72, 71, 72, 69, 64, 69, 71, 72, 71, 69, 68, 69]
    st, k = start, 0
    while st < end:
        m = notes[k % len(notes)]
        f = 440 * 2 ** ((m - 69) / 12) * (1 + 0.006 * np.sin(k))
        tt = t_(1.4)
        s = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.01 * tt) + 0.15 * np.sin(2 * np.pi * f * 3.98 * tt)) * np.exp(-tt / 0.45)
        fade = 1 if st < end - 3 else max(0.0, (end - st) / 3)
        add(st, crush(s, 7, 2), g * fade, 0.3 * np.sin(k))
        st += 0.42 if k % 4 != 3 else 0.84
        k += 1


def boom(st, g=0.9, f0=70):
    tt = t_(2.2)
    s = np.sin(2 * np.pi * (f0 * np.exp(-tt * 0.8)) * tt) * np.exp(-tt / 0.6)
    s += norm(filt(noise(2.2), 20, 200)) * np.exp(-tt / 0.3) * 0.6
    add(st, np.tanh(2 * s), g)


def cluster(st, dur=2.5, g=0.35):
    tt = t_(dur)
    s = np.zeros_like(tt)
    for f in [311, 329.6, 349, 466, 493.9, 987, 1046]:
        ph = 2 * np.pi * f * tt * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * tt + f))
        s += (2 * ((ph / (2 * np.pi)) % 1) - 1)
    s = filt(s / 7, 150, 5000) * np.clip(tt / 0.02, 0, 1) * np.exp(-tt / (dur * 0.45))
    add(st, s, g, -0.3); add(st + 0.01, s, g, 0.3)


def glitch(st, dur=0.5, g=0.35):
    tt = t_(dur)
    s = np.zeros_like(tt)
    i = 0
    while i < len(tt):
        ln = int(rng.uniform(0.01, 0.06) * SR)
        kind = rng.integers(3)
        seg = tt[i:i + ln]
        if kind == 0: s[i:i + ln] = rng.standard_normal(len(seg))
        elif kind == 1: s[i:i + ln] = np.sign(np.sin(2 * np.pi * rng.uniform(200, 3000) * seg))
        i += ln
    add(st, crush(s, 4, 6), g, rng.uniform(-0.5, 0.5))


def static_burst(st, dur=0.4, g=0.4):
    add(st, crush(noise(dur), 5, 2) * np.clip((dur - t_(dur)) / 0.05, 0, 1), g)


def crack(st, g=0.45):
    tt = t_(0.08)
    s = filt(noise(0.08), 1000, 9000) * np.exp(-tt / 0.006) + np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.02) * 0.6
    add(st, np.tanh(3 * s), g, rng.uniform(-0.3, 0.3))


def heartbeat(start, end):
    st = start
    while st < end:
        k = (st - start) / (end - start)
        for off, a in [(0, 1), (0.16, 0.7)]:
            tt = t_(0.25)
            s = np.sin(2 * np.pi * 52 * tt) * np.exp(-tt / 0.07) * np.clip(tt / 0.005, 0, 1)
            add(st + off, s, 0.85 * a * (0.6 + 0.4 * k))
        st += lerp(1.0, 0.45, k)


def lerp(a, b, k):
    return a + (b - a) * k


def beep_save(st):
    for i, f in enumerate([880, 1320]):
        tt = t_(0.12)
        add(st + i * 0.13, np.sign(np.sin(2 * np.pi * f * tt)) * env(len(tt), 0.002, 0.08), 0.1)


def creak(st, dur=1.5, g=0.25):
    tt = t_(dur)
    f = 260 + 140 * np.sin(2 * np.pi * 0.7 * tt) + 40 * rng.standard_normal(len(tt)).cumsum() / SR
    ph = np.cumsum(2 * np.pi * f / SR)
    s = (2 * ((ph / (2 * np.pi)) % 1) - 1) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 23 * tt)))
    add(st, filt(s, 200, 3000) * np.sin(np.pi * tt / dur), g, 0.6)


def grind(st, dur, g=0.25):
    tt = t_(dur)
    s = norm(filt(noise(dur), 40, 400)) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * tt) ** 2) * np.clip(tt / 0.3, 0, 1)
    add(st, s, g)


def scream(st, dur=1.5, g=0.85):
    tt = t_(dur)
    f = (900 * np.exp(-tt * 0.6) + 300) * (1 + 0.03 * np.sin(2 * np.pi * 11 * tt))
    ph = np.cumsum(2 * np.pi * f / SR)
    src = (2 * ((ph / (2 * np.pi)) % 1) - 1) + 0.8 * rng.standard_normal(len(tt))
    s = filt(src, 600, 1100, 2) * 1.2 + filt(src, 2200, 3200, 2) + filt(src, 3500, 6000, 2) * 0.6
    s = np.tanh(4 * norm(s)) * np.clip(tt / 0.01, 0, 1) * np.clip((dur - tt) / 0.3, 0, 1)
    add(st, s, g, -0.15); add(st + 0.012, s, g, 0.15)


def growl(st, dur=2.4, g=0.5):
    tt = t_(dur)
    f = 55 + 8 * np.sin(2 * np.pi * 3 * tt)
    ph = np.cumsum(2 * np.pi * f / SR)
    s = (2 * ((ph / (2 * np.pi)) % 1) - 1) * (0.6 + 0.4 * rng.standard_normal(len(tt)))
    s = filt(s, 40, 900) * np.sin(np.pi * np.clip(tt / dur, 0, 1))
    add(st, np.tanh(2 * norm(s)), g)


def memcard_ticks(start, end):
    st = start
    while st < end:
        tt = t_(0.05)
        add(st, np.sin(2 * np.pi * 1760 * tt) * np.exp(-tt / 0.01), 0.06)
        st += 1 / 3


# ---------------- montagem ----------------
drone(); rain(); neon_buzz(); tv_hum(); blips()
static_burst(0.0, 0.42, 0.45)
for k in range(5): glitch(0.4 + k * 0.567, 0.12, 0.18)
boom(M["hookFlash"], 0.8); cluster(M["hookFlash"], 1.0, 0.3); glitch(M["hookFlash"], 0.45, 0.4)
glitch(5.35, 0.2, 0.3)
for k in range(16): footstep_wet(5.6 + k * 0.48)
glitch(17.4, 0.6, 0.35)
music_box(22.2, 40)
glitch(30.5, 0.8, 0.4)
for k in range(9): footstep_wood(31.1 + k * 0.46)
cluster(M["reveal"], 3.0, 0.4); boom(M["reveal"], 0.9, 60)
for k in range(3): crack(M["snap"] + k * 0.083, 0.55)
glitch(M["snap"], 0.6, 0.45); cluster(M["snap"], 2.0, 0.25)
heartbeat(47.2, 58)
beep_save(M["save"])
glitch(59.8, 0.25, 0.4)
for k in range(10): crack(M["headTurn"] + 0.4 + k * 0.26, 0.35)
creak(M["creak"], 1.6, 0.3)
grind(69.0, 2.3, 0.22)
for k in range(12): crack(69.0 + k * 0.19, 0.18)
scream(M["scare"], 1.5, 0.9); boom(M["scare"], 0.95, 50); glitch(M["scare"], 1.4, 0.35)
memcard_ticks(74.2, 76.9)
glitch(76.9, 0.2, 0.3)
for k in range(8): crack(M["monsterTurn"] + 0.3 + k * 0.375, 0.35)
glitch(85.5, 0.5, 0.3)
boom(M["connected"], 0.9, 45); glitch(M["connected"], 0.5, 0.45); growl(M["connected"], 2.4, 0.45)
static_burst(89.85, 0.15, 0.3)

# corte seco para o silêncio após o susto e no fim
tt = np.arange(N) / SR
mute = ((tt >= M["black"]) & (tt < 74.0)) | ((tt >= M["end"]) & (tt < 89.85))
L[mute] *= 0.0; R[mute] *= 0.0

mix = np.stack([L, R], 1)
mix = np.tanh(1.3 * mix / (np.percentile(np.abs(mix), 99.95) + 1e-9)) * 0.95  # compressão suave dos picos
os.makedirs(os.path.join(HERE, "saida"), exist_ok=True)
out = os.path.join(HERE, "saida", "audio.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok", out)

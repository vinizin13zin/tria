"""Trilha sonora sintetizada do curta "03:33" (só numpy) + narração.

Lê os tempos de timeline.js para que legendas, cortes e sustos fiquem
sincronizados com o vídeo. Gera saida/audio.wav (44.1 kHz, estéreo).
"""
import json, os, re, subprocess, wave
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
        cps = s.get("cps") or (22 if s["kind"] == "big" else 30)
        freq = 520 if s["kind"] == "big" else 1250
        txt = s["text"]
        for i, ch in enumerate(txt):
            st = s["t0"] + i / cps
            if st > s["t1"] or ch == " " or i % 2: continue
            tt = t_(0.014)
            b = np.sign(np.sin(2 * np.pi * freq * tt)) * env(len(tt), 0.001, 0.006)
            add(st, b, 0.03 if s["kind"] != "big" else 0.05)


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



# ---------------- camadas novas ----------------
def drone():
    tt = np.arange(N) / SR
    d = (np.sin(2 * np.pi * 43 * tt) + 0.8 * np.sin(2 * np.pi * 43.7 * tt) + 0.5 * np.sin(2 * np.pi * 64.5 * tt + np.sin(tt * 0.4)))
    d = d / 2.3 + 0.6 * norm(filt(rng.standard_normal(N), 30, 200))
    pts = [(0, .5), (5.5, .25), (17, .35), (30.6, .45), (38.4, .55), (50.2, .6), (57.8, .8), (66.1, .6), (75.5, .9), (M["black"], 0),
           (80.4, .4), (85.5, .9), (M["end"], 0), (DUR, 0)]
    xs, ys = zip(*pts)
    add(0, d * np.interp(tt, xs, ys), 0.5)


def city_hum(start, end, g=0.06):
    n = noise(end - start)
    s = norm(filt(n, 40, 300)) + 0.3 * np.sin(2 * np.pi * 0.1 * t_(end - start)) * norm(filt(n, 300, 900))
    add(start, s * np.clip(t_(end - start) / 1.0, 0, 1) * np.clip((end - start - t_(end - start)) / 0.6, 0, 1), g)


def vibrate(start, end, g=0.35):
    """celular vibrando na madeira do criado-mudo: rajadas de ~0.9 s"""
    st = start
    while st < end:
        tt = t_(0.9)
        s = np.sign(np.sin(2 * np.pi * 155 * tt)) * 0.6 + np.sin(2 * np.pi * 310 * tt) * 0.4
        s = filt(s, 80, 1800) * np.clip(tt / 0.02, 0, 1) * np.clip((0.9 - tt) / 0.03, 0, 1)
        add(st, s, g)
        st += 1.36


def ringtone(start, end, g=0.12):
    """toque polifônico de celular antigo, levemente desafinado"""
    mel = [76, 79, 83, 79, 76, 72, 76, 79]
    st, i = start, 0
    while st < end:
        f = 440 * 2 ** ((mel[i % len(mel)] - 69) / 12) * (1 - 0.01 * (i % 3))
        tt = t_(0.16)
        s = (np.sign(np.sin(2 * np.pi * f * tt)) * 0.5 + np.sin(2 * np.pi * f * 2 * tt) * 0.3) * np.exp(-tt / 0.1)
        add(st, crush(s, 6, 2), g, 0.15)
        st += 0.17 if i % 8 != 7 else 0.65
        i += 1


def bulb_buzz(start, end, g=0.04):
    tt = t_(end - start)
    s = np.sign(np.sin(2 * np.pi * 120 * tt)) * 0.4 + np.sin(2 * np.pi * 360 * tt) * 0.3
    gate = (np.sin(2 * np.pi * 9 * tt) > -0.6).astype(float)
    add(start, filt(s, 100, 2000) * gate, g)


def fluo(start, end, g=0.05):
    tt = t_(end - start)
    s = np.sin(2 * np.pi * 120 * tt) + 0.5 * np.sin(2 * np.pi * 240 * tt) + 0.3 * norm(filt(rng.standard_normal(len(tt)), 2000, 6000))
    add(start, s, g)


def click(st, g=0.4):
    tt = t_(0.05)
    add(st, filt(noise(0.05), 800, 6000) * np.exp(-tt / 0.004), g)


def knock_lock(st, g=0.5):  # trinco da porta
    for d in (0, 0.09):
        tt = t_(0.08)
        s = filt(noise(0.08), 400, 5000) * np.exp(-tt / 0.01) + np.sin(2 * np.pi * 900 * tt) * np.exp(-tt / 0.02) * 0.4
        add(st + d, s, g)


def whoosh(st, dur=0.6, g=0.4):
    tt = t_(dur)
    s = norm(filt(noise(dur), 300, 4000)) * np.sin(np.pi * tt / dur) ** 2
    add(st, s, g)


def sub_drop(st, g=0.8):
    tt = t_(1.6)
    add(st, np.sin(2 * np.pi * (90 * np.exp(-tt * 2) + 30) * tt) * np.exp(-tt / 0.7), g)


def reverse_swell(end_t, dur=1.4, g=0.35):
    tt = t_(dur)
    s = 0
    for f in [220, 233, 311, 466]:
        s = s + np.sin(2 * np.pi * f * tt)
    s = (s / 4 + 0.5 * norm(filt(noise(dur), 500, 5000))) * (tt / dur) ** 3
    add(end_t - dur, s, g)


def digital_crunch(start, end, g=0.25):
    st = start
    while st < end:
        glitch(st, rng.uniform(0.05, 0.25), g * rng.uniform(0.5, 1))
        st += rng.uniform(0.15, 0.6)


def beep_missed(st):
    for i, f in enumerate([660, 660, 440]):
        tt = t_(0.11)
        add(st + i * 0.15, np.sign(np.sin(2 * np.pi * f * tt)) * env(len(tt), 0.002, 0.07), 0.12)


def blips():
    for s in TL["subs"]:
        cps = s.get("cps") or 30
        freq = 520 if s["kind"] == "big" else (900 if s["kind"] == "phone" else 1250)
        for i, ch in enumerate(s["text"]):
            st = s["t0"] + i / cps
            if st > s["t1"] or ch == " " or i % 2: continue
            tt = t_(0.012)
            add(st, np.sign(np.sin(2 * np.pi * freq * tt)) * env(len(tt), 0.001, 0.005), 0.025)


# ---------------- montagem ----------------
drone(); blips()
static_burst(0.0, 0.25, 0.4); whoosh(0.0, 0.4, 0.3)
vibrate(0.1, M["pickup"]); ringtone(5.6, M["pickup"])
city_hum(5.5, 30.6)
glitch(M["flash"], 0.35, 0.5); boom(M["flash"], 0.7, 60); scream(M["flash"], 0.35, 0.5)
whoosh(M["close"] - 0.2, 0.4, 0.25)
click(M["pickup"] + 1.2, 0.35)                       # flip abrindo
add(17.0, norm(filt(noise(13), 300, 3400)) * 0.5, 0.03)  # chiado da linha
sub_drop(M["punch"], 0.6); glitch(M["punch"], 0.25, 0.35)
cluster(M["turnDoor"], 3.0, 0.25)
bulb_buzz(26.4, 50.2)
for k in range(9): footstep_wood(31.0 + k * 0.6, 0.45)
heartbeat(37.0, 50.0)
fluo(38.4, 41.5)
click(M["lightsOff"], 0.5)
click(M["face"] - 0.02, 0.5); boom(M["face"], 0.95, 55); scream(M["face"], 1.1, 0.8); glitch(M["face"], 0.6, 0.45)
fluo(M["face"], 50.2, 0.04)
whoosh(M["stepBack"], 0.5, 0.3)
digital_crunch(M["hands"] + 0.5, M["mirror"] - 0.2, 0.3)
reverse_swell(M["mirror"] + 0.7, 1.6, 0.4)
cluster(M["mirror"], 3.5, 0.3)
for k in range(3): crack(M["smileMax"] + k * 0.13, 0.5)
glitch(M["smileMax"], 0.4, 0.4); sub_drop(M["smileMax"], 0.6)
fluo(66.1, M["black"], 0.04)
knock_lock(M["unlock"], 0.5)
creak(M["doorOpen"], 2.6, 0.35)
for k in range(4): crack(M["tilt"] + k * 0.125, 0.45)
scream(M["lunge"], 1.6, 0.95); boom(M["lunge"], 0.95, 50); glitch(M["lunge"], 1.6, 0.4)
beep_missed(M["missed"] + 0.2)
fluo(80.4, M["end"], 0.035)
boom(M["naoAtende"], 0.9, 45); glitch(M["naoAtende"], 0.5, 0.45); growl(M["naoAtende"], 2.0, 0.35)
static_burst(DUR - 0.15, 0.15, 0.3)

tt = np.arange(N) / SR
mute = ((tt >= M["black"]) & (tt < M["missed"])) | ((tt >= M["end"]) & (tt < DUR - 0.15))
L[mute] *= 0.0; R[mute] *= 0.0

# ---------------- narração com "ducking" da trilha ----------------
V = np.zeros(N)
for i, s in enumerate(TL["subs"]):
    with wave.open(os.path.join(HERE, "saida", "falas", f"{i:02d}.wav")) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32768.0
    a = int(s["t0"] * SR); v = v[: max(0, N - a)]
    V[a:a + len(v)] += v * (0.85 if s["fx"] == "phone" else 1.0)
wet = np.zeros(N)
for d, g in [(0.029, 0.16), (0.043, 0.12), (0.071, 0.09), (0.113, 0.05)]:
    k = int(d * SR); wet[k:] += V[:-k] * g
V = V + filt(wet, 200, 4000)
lvl = np.convolve(np.abs(V), np.ones(4410) / 4410, "same")
duck = 1 - 0.55 * np.clip(lvl / (np.percentile(lvl[lvl > 1e-4], 50) + 1e-9), 0, 1)
music = np.stack([L * duck, R * duck], 1)
music /= (np.percentile(np.abs(music), 99.95) + 1e-9)
V = V / (np.max(np.abs(V)) + 1e-9) * 0.95
mix = music * 0.75 + np.stack([V, V], 1)
mix = np.tanh(mix / (np.percentile(np.abs(mix), 99.99) + 1e-9))
mix *= 0.89 / (np.max(np.abs(mix)) + 1e-9)
os.makedirs(os.path.join(HERE, "saida"), exist_ok=True)
out = os.path.join(HERE, "saida", "audio.wav")
def write(x):
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
write(mix)
meas = subprocess.run(["ffmpeg", "-nostats", "-i", out, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", meas)[-1])
g = min(10 ** ((-14 - lufs) / 20), 0.89 / (np.max(np.abs(mix)) + 1e-9))
write(mix * g)
print("ok", out, "loudness %.1f LUFS -> ganho %.2f" % (lufs, g))

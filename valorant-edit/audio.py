"""Synthesised phonk beat + sound effects for the edit. Everything is generated
from oscillators and noise, so there is no licensing question on the audio."""
import json
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
BPM = 140
BEAT = 60 / BPM
STEP = BEAT / 4
BAR = BEAT * 4
rng = np.random.default_rng(42)


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def env(dur, decay, attack=0.002):
    t = t_(dur)
    return np.minimum(t / attack, 1) * np.exp(-t / decay)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def svf_sweep(x, f0, f1, q=4.0, curve=1.0):
    """Resonant band-pass whose centre sweeps f0→f1 (log), for risers/whooshes."""
    n = len(x)
    u = (np.arange(n) / max(n - 1, 1)) ** curve
    f = f0 * (f1 / f0) ** u
    g = 2 * np.sin(np.pi * f / SR)
    lo = bd = 0.0
    out = np.empty(n)
    damp = 1 / q
    for i in range(n):
        hi_ = x[i] - lo - damp * bd
        bd += g[i] * hi_
        lo += g[i] * bd
        out[i] = bd
    return out


def reverb(x, seconds=1.2, mix=0.25):
    ir = noise(seconds) * np.exp(-t_(seconds) / (seconds / 5))
    ir = lp(ir, 6000)
    wet = fftconvolve(x, ir)[: len(x)]
    wet /= np.max(np.abs(wet)) + 1e-9
    return x * (1 - mix) + wet * mix * np.max(np.abs(x))


def norm(x, peak=0.98):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


# ── instruments ─────────────────────────────────────────────
def kick(hard=1.0):
    t = t_(0.45)
    f = 45 + 160 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    k = np.sin(ph) * np.exp(-t / 0.22)
    k[: int(0.004 * SR)] += noise(0.004) * 0.6
    return np.tanh(k * (2.2 * hard))


def clap():
    n = noise(0.25)
    e = np.zeros_like(n)
    for off in (0, 0.009, 0.018):
        i = int(off * SR)
        seg = env(0.25, 0.012 if off < 0.018 else 0.09)[: len(e) - i]
        e[i:i + len(seg)] += seg
    c = bp(n, 900, 5000) * e
    c += np.sin(2 * np.pi * 190 * t_(0.25)) * env(0.25, 0.03) * 0.5
    return np.tanh(c * 2.5) * 0.8


def hat(open_=False):
    d = 0.18 if open_ else 0.05
    return hp(noise(d), 7000, 4) * env(d, 0.06 if open_ else 0.012) * 0.55


def bass808(freq, dur, glide_from=None):
    t = t_(dur)
    f = np.full_like(t, freq)
    if glide_from:
        f = freq + (glide_from - freq) * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    b = np.sin(ph) * np.minimum(t / 0.004, 1) * np.exp(-t / 0.55)
    b *= np.minimum((dur - t) / 0.025, 1)  # release, avoids a click on cut-off
    return np.tanh(b * 2.6) * 0.75


def cowbell(freq, dur=0.32):
    t = t_(dur)
    sq = lambda f: np.sign(np.sin(2 * np.pi * f * t))
    c = (sq(freq) + sq(freq * 1.4836)) * 0.5
    c = bp(c, freq * 0.9, freq * 4.0) * env(dur, 0.09, 0.001)
    return c * 0.9


def note(n):  # semitone offset from F#4
    return 369.99 * 2 ** (n / 12)


def place(buf, sig, at, gain=1.0):
    i = int(round(at * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


# ── sound effects ───────────────────────────────────────────
def sfx_gunshot():
    d = 0.6
    t = t_(d)
    crack = hp(noise(d), 1500) * env(d, 0.012, 0.0005)
    body = bp(noise(d), 180, 2500) * env(d, 0.07, 0.0005)
    thump = np.sin(2 * np.pi * (55 + 90 * np.exp(-t / 0.02)) * t) * env(d, 0.09)
    g = np.tanh((crack * 1.4 + body * 1.2 + thump * 1.3) * 3)
    return norm(reverb(g, 0.5, 0.18), 0.95)


def sfx_headshot():
    d = 0.7
    t = t_(d)
    partials = [(2093, 1.0), (3140, 0.6), (4710, 0.35), (6280, 0.2)]
    s = sum(a * np.sin(2 * np.pi * f * t) for f, a in partials) * env(d, 0.16, 0.001)
    s += hp(noise(d), 5000) * env(d, 0.01) * 0.4
    return norm(reverb(s, 0.8, 0.25), 0.7)


def sfx_whoosh(d=0.42):
    w = svf_sweep(noise(d), 250, 4500, q=3, curve=0.8)
    e = np.sin(np.pi * np.linspace(0, 1, len(w))) ** 2
    return norm(w * e, 0.6)


def sfx_impact():
    d = 1.6
    t = t_(d)
    boom = np.sin(2 * np.pi * (38 + 70 * np.exp(-t / 0.06)) * t) * env(d, 0.45)
    hit = lp(noise(d), 2500) * env(d, 0.08, 0.0005)
    return norm(reverb(np.tanh((boom * 1.5 + hit) * 2), 1.4, 0.35), 0.95)


def sfx_riser(d):
    r = svf_sweep(noise(d), 200, 9000, q=6, curve=2.2)
    t = t_(d)
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (3 * (t / d) ** 2)) / SR) * 0.25
    e = (t / d) ** 2.2
    return norm((r + tone) * e, 0.55)


def sfx_reverse_cymbal(d=0.9):
    s = hp(noise(d), 4000) * env(d, 0.25)
    return norm(s[::-1], 0.4)


# ── arrangement ─────────────────────────────────────────────
INTRO_BARS, DROP_BARS = 2, 8
DROP_AT = INTRO_BARS * BAR
END_AT = (INTRO_BARS + DROP_BARS) * BAR
TOTAL = END_AT + 1.1

MELODY = [  # (step, semitone) over 2 bars = 32 sixteenths
    (0, 0), (3, 0), (6, 3), (8, 0), (10, -2), (12, 0), (14, 3),
    (16, 5), (19, 3), (22, 0), (24, -2), (26, 0), (28, 3), (30, -4),
]
BASS = [0, 0, -4, -2]  # root per bar (relative to F#1)


def build_music():
    drums = np.zeros(int(TOTAL * SR) + SR)
    bass = np.zeros_like(drums)
    bell = np.zeros_like(drums)
    fx = np.zeros_like(drums)
    kicks = []

    # intro: filtered cowbell + sub drone + riser
    for bar in range(INTRO_BARS):
        for s, n in MELODY[:7] if bar % 2 == 0 else MELODY[7:]:
            place(bell, cowbell(note(n)), bar * BAR + (s % 16) * STEP, 0.7)
    bell_intro_end = int(DROP_AT * SR)
    bell[:bell_intro_end] = lp(bell[:bell_intro_end], 900)
    place(fx, sfx_riser(DROP_AT), 0, 0.9)
    place(fx, sfx_reverse_cymbal(BEAT * 2), DROP_AT - BEAT * 2, 1.0)

    # drop
    for b in range(DROP_BARS):
        t0 = DROP_AT + b * BAR
        brk = b == 5  # one-bar break / beat switch
        mel = MELODY[:7] if b % 2 == 0 else MELODY[7:]
        for s, n in mel:
            place(bell, cowbell(note(n + (12 if b >= 6 and s % 4 == 0 else 0))), t0 + (s % 16) * STEP, 0.85)
        if brk:
            place(fx, sfx_reverse_cymbal(BAR * 0.75), t0 + BAR * 0.25, 1.2)
            place(drums, hat(), t0 + 14 * STEP, 0.8)
            continue
        ksteps = [0, 6, 10] if b % 2 == 0 else [0, 7, 10, 13]
        for s in ksteps:
            place(drums, kick(), t0 + s * STEP)
            kicks.append(t0 + s * STEP)
            root = 46.25 * 2 ** (BASS[b % 4] / 12)
            place(bass, bass808(root, STEP * 4, glide_from=root * 1.5 if s == 0 else None), t0 + s * STEP)
        for s in (4, 12):
            place(drums, clap(), t0 + s * STEP)
        for s in range(0, 16, 2):
            place(drums, hat(open_=(s == 14 and b % 2 == 1)), t0 + s * STEP, 0.9 if s % 4 == 0 else 0.6)
        if b % 2 == 1:  # triplet hat roll on the last beat
            for k in range(6):
                place(drums, hat(), t0 + 3 * BEAT + k * BEAT / 6, 0.5 + k * 0.06)
    place(drums, kick(1.4), END_AT)
    place(bass, bass808(46.25, 1.0, glide_from=92.5), END_AT, 1.0)
    place(fx, sfx_impact(), END_AT, 0.8)
    place(fx, sfx_impact(), DROP_AT, 0.9)

    # sidechain duck on kicks
    duck = np.ones_like(drums)
    for k in kicks:
        i = int(k * SR)
        n = int(0.18 * SR)
        duck[i:i + n] = np.minimum(duck[i:i + n], 1 - 0.6 * np.exp(-np.arange(n) / SR / 0.06)[: len(duck[i:i + n])])
    bell = reverb(bell, 1.0, 0.22)
    mix = drums * 0.9 + bass * 0.85 * duck + bell * 0.55 * duck + fx * 0.7
    mix = np.tanh(mix * 1.3)
    mix = mix[: int(TOTAL * SR)]
    fade = int(0.6 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return norm(mix, 0.89), sorted(kicks + [END_AT])


def write(path, x):
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


if __name__ == "__main__":
    import os
    os.makedirs("audio", exist_ok=True)
    music, kicks = build_music()
    write("audio/music.wav", music)
    for name, fn in [("gunshot", sfx_gunshot), ("headshot", sfx_headshot), ("whoosh", sfx_whoosh), ("impact", sfx_impact)]:
        write(f"audio/{name}.wav", fn())
    json.dump({"bpm": BPM, "beat": BEAT, "drop": DROP_AT, "end": END_AT, "total": TOTAL, "kicks": [round(k, 4) for k in kicks]}, open("audio/timing.json", "w"), indent=1)
    print(f"music {TOTAL:.2f}s, drop at {DROP_AT:.3f}s, end hit {END_AT:.3f}s")

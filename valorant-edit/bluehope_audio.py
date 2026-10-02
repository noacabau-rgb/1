"""Music + SFX arranged for the Blue Hope edit (40 beats @ 140 BPM).

  B0-B4    intro: filtered cowbell opening up, riser, logo shimmer
  B4       DROP (first kill)
  B4-B28   6 bars of phonk, build-up gap on B22-B24 before the clutch kill
  B28      tape stop -> near silence so the caster's scream carries the clip
  B32-B36  riser back in
  B36-B40  final bar under the logo outro, last hit on B40 + tail
"""
import json
import numpy as np
from scipy.signal import fftconvolve
import audio as A
from audio import SR, BEAT, STEP, BAR, place, kick, clap, hat, bass808, cowbell, note, lp, hp, bp, noise, env, t_, norm, reverb

TOTAL_BEATS = 40
TAIL = 0.65
TOTAL = TOTAL_BEATS * BEAT + TAIL
B = lambda n: n * BEAT
rng = np.random.default_rng(9)


def tape_stop(x, dur):
    """Playback rate falls 1 -> 0 over `dur` (classic DJ tape stop)."""
    n = int(dur * SR)
    rate = np.linspace(1, 0, n) ** 1.6
    pos = np.cumsum(rate)
    pos = pos[pos < len(x) - 1]
    out = np.interp(pos, np.arange(len(x)), x)
    out *= np.linspace(1, 0, len(out)) ** 0.5
    return out


def sfx_shimmer():
    out = np.zeros(int(1.6 * SR))
    for i, f in enumerate([1480, 1760, 2217, 2960, 3520]):
        d = 1.6 - i * 0.05
        tone = (np.sin(2 * np.pi * f * t_(d)) + 0.3 * np.sin(2 * np.pi * f * 2.01 * t_(d))) * env(d, 0.35, 0.002)
        place(out, tone, i * 0.05, 0.5)
    return norm(reverb(out, 1.4, 0.45), 0.6)


def sfx_glitch(d=0.28):
    x = np.zeros(int(d * SR))
    sl = int(0.022 * SR)
    for i in range(0, len(x), sl):
        if rng.random() < 0.7:
            f = rng.choice([180, 440, 900, 1800, 3600])
            seg = np.sign(np.sin(2 * np.pi * f * np.arange(sl) / SR)) * 0.6 + noise(sl / SR) * 0.4
            x[i:i + sl] = seg[: len(x[i:i + sl])] * rng.uniform(0.4, 1)
    x = np.round(x * 6) / 6  # bitcrush
    return norm(bp(x, 150, 8000), 0.5)


def sfx_swoosh_rev(d=0.6):
    return A.sfx_whoosh(d)[::-1] * np.linspace(0.3, 1, int(d * SR))


def drum_bar(drums, bass, t0, b, kicks, gap_from_step=None, full_end=False):
    ksteps = [0, 6, 10] if b % 2 == 0 else [0, 7, 10, 13]
    roots = [0, 0, -4, -2]
    for s in ksteps:
        if gap_from_step is not None and s >= gap_from_step:
            continue
        place(drums, kick(), t0 + s * STEP)
        kicks.append(t0 + s * STEP)
        root = 46.25 * 2 ** (roots[b % 4] / 12)
        place(bass, bass808(root, STEP * 4, glide_from=root * 1.5 if s == 0 else None), t0 + s * STEP)
    for s in (4, 12):
        if gap_from_step is None or s < gap_from_step:
            place(drums, clap(), t0 + s * STEP)
    for s in range(0, 16, 2):
        if gap_from_step is None or s < gap_from_step:
            place(drums, hat(open_=(s == 14 and b % 2 == 1)), t0 + s * STEP, 0.9 if s % 4 == 0 else 0.6)
    if b % 2 == 1 and gap_from_step is None:
        for k in range(6):
            place(drums, hat(), t0 + 3 * BEAT + k * BEAT / 6, 0.5 + k * 0.06)
    if gap_from_step is not None:  # snare roll build into the next downbeat
        n = 16 - gap_from_step
        for k in range(n * 2):
            place(drums, clap(), t0 + gap_from_step * STEP + k * STEP / 2, 0.25 + 0.6 * k / (n * 2))


def melody_bar(bell, t0, b, gain=0.85, octave=False):
    mel = A.MELODY[:7] if b % 2 == 0 else A.MELODY[7:]
    for s, n in mel:
        place(bell, cowbell(note(n + (12 if octave and s % 4 == 0 else 0))), t0 + (s % 16) * STEP, gain)


def build():
    N = int(TOTAL * SR) + SR
    drums, bass, bell, fx, pad = (np.zeros(N) for _ in range(5))
    kicks, impacts = [], []

    # ── intro B0-B4: filter opening on the cowbell, sub drone, riser
    intro = np.zeros(N)
    for b in range(1):
        melody_bar(intro, B(0), 0, 0.8)
    melody_bar(intro, B(2), 1, 0.8)  # second half-phrase keeps it moving
    ie = int(B(4) * SR)
    seg = intro[:ie]
    r = np.linspace(0, 1, ie) ** 1.5
    bell[:ie] += lp(seg, 450) * (1 - r) + lp(seg, 3200) * r
    drone = np.sin(2 * np.pi * 46.25 * t_(B(4))) * np.minimum(t_(B(4)) / 0.4, 1) * 0.35
    place(pad, np.tanh(drone * 2), 0)
    place(fx, A.sfx_riser(B(4)), 0, 0.8)
    place(fx, A.sfx_reverse_cymbal(B(2)), B(2), 1.0)

    # ── drop B4-B28
    for i in range(6):
        t0 = B(4 + 4 * i)
        gap = 8 if i == 4 else None  # B22-B24: drums out, snare roll build
        drum_bar(drums, bass, t0, i, kicks, gap_from_step=gap)
        melody_bar(bell, t0, i, 0.85, octave=(i == 5))
    impacts += [B(4), B(24)]

    # ── tape stop at B28, then a hollow break for the caster
    pre = np.zeros(int(BAR * SR) + SR)
    drum_bar(pre, pre, 0, 0, [])
    melody_bar(pre, 0, 0, 0.6)
    place(fx, tape_stop(np.tanh(pre * 1.2), 0.75) * 0.8, B(28))
    brk = np.zeros(N)
    for b in range(2):
        melody_bar(brk, B(28 + 4 * b) + 0.4 * (b == 0), b, 0.6)
    s0, s1 = int(B(28) * SR), int(B(36) * SR)
    bell[s0:s1] += lp(brk[s0:s1], 380) * 0.35
    sub = np.sin(2 * np.pi * 46.25 * t_(B(8))) * 0.18
    place(pad, sub * np.minimum(t_(B(8)) / 1.0, 1), B(28))
    place(fx, A.sfx_riser(B(4)), B(32), 0.45)
    place(fx, A.sfx_reverse_cymbal(B(2)), B(34), 1.0)

    # ── outro B36-B40 + final hit
    drum_bar(drums, bass, B(36), 0, kicks)
    melody_bar(bell, B(36), 0, 0.9, octave=True)
    place(drums, kick(1.4), B(40))
    kicks.append(B(40))
    place(bass, bass808(46.25, 1.2, glide_from=92.5), B(40), 1.0)
    impacts += [B(36), B(40)]
    for t in impacts:
        place(fx, A.sfx_impact(), t, 0.8 if t != B(40) else 0.6)

    # sidechain
    duck = np.ones(N)
    for k in kicks:
        i, n = int(k * SR), int(0.18 * SR)
        seg = duck[i:i + n]
        duck[i:i + n] = np.minimum(seg, 1 - 0.6 * np.exp(-np.arange(len(seg)) / SR / 0.06))
    bell = reverb(bell, 1.0, 0.22)
    mix = drums * 0.9 + bass * 0.85 * duck + bell * 0.55 * duck + fx * 0.7 + pad * 0.3
    mix = np.tanh(mix * 1.3)[: int(TOTAL * SR)]
    fade = int(0.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return norm(mix, 0.89), sorted(kicks)


if __name__ == "__main__":
    import os
    os.makedirs("audio", exist_ok=True)
    music, kicks = build()
    A.write("audio/bh_music.wav", music)
    for name, fn in [("shimmer", sfx_shimmer), ("glitch", sfx_glitch), ("swoosh_rev", sfx_swoosh_rev)]:
        A.write(f"audio/{name}.wav", fn())
    json.dump({"bpm": A.BPM, "beat": BEAT, "total": TOTAL, "kicks": [round(k, 4) for k in kicks]},
              open("audio/bh_timing.json", "w"), indent=1)
    print(f"music {TOTAL:.2f}s, {len(kicks)} kicks")

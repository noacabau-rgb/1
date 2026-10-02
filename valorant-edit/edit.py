"""Beat-synced vertical (9:16) edit engine.

Reads edit.json (segments of gameplay clips laid on the beat grid of
audio/music.wav), applies TikTok-style effects (speed ramps, zoom punches,
screen shake, whip transitions, flashes, RGB split, grade) and mixes the
music, the clip's own game audio and layered SFX.

    python3 edit.py edit.json out.mp4
"""
import json
import subprocess
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, find_peaks

OW, OH, FPS, SR = 1080, 1920, 60, 44100
TIMING = json.load(open("audio/timing.json"))
BEAT = TIMING["beat"]


def ease_out(u):
    return 1 - (1 - np.clip(u, 0, 1)) ** 3


def pulse(dt, decay):
    """1 at the event, exponential decay after it, 0 before it."""
    return np.exp(-dt / decay) if dt >= 0 else 0.0


# ── sources ─────────────────────────────────────────────────
def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out.strip())


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


class FrameStream:
    """Sequential decoder at 60 fps, 1920x1080; serves monotonic time requests."""

    def __init__(self, path, start, dur):
        self.start = max(0.0, start)
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", f"{self.start:.3f}", "-i", path, "-t", f"{dur + 0.5:.3f}",
             "-vf", "fps=60,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
             "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
        self.idx, self.frame, self.prev = -1, None, None

    def at(self, t):
        want = max(0, int(round((t - self.start) * FPS)))
        while self.idx < want:
            buf = self.p.stdout.read(1920 * 1080 * 3)
            if len(buf) < 1920 * 1080 * 3:
                break  # past the end: hold the last frame
            self.prev, self.frame = self.frame, np.frombuffer(buf, np.uint8).reshape(1080, 1920, 3)
            self.idx += 1
        return self.frame

    def close(self):
        self.p.stdout.close()
        self.p.kill()


def detect_shots(audio, t0, t1):
    """Gunshot-like transients in the clip's own audio, in source seconds."""
    a = audio[int(t0 * SR):int(t1 * SR)]
    if len(a) < SR // 10:
        return []
    hpf = sosfilt(butter(2, 1500, "high", fs=SR, output="sos"), a)
    hop = SR // 200
    e = np.sqrt(np.convolve(hpf ** 2, np.ones(hop) / hop, "same"))[::hop]
    flux = np.maximum(np.diff(e, prepend=e[0]), 0)
    if flux.max() <= 0:
        return []
    peaks, _ = find_peaks(flux, height=flux.max() * 0.35, distance=int(0.09 * 200))
    return [t0 + p / 200 for p in peaks]


# ── timeline ────────────────────────────────────────────────
class Segment:
    def __init__(self, cfg, t_out0, clip_audio):
        self.cfg = cfg
        self.t0 = t_out0
        self.dur = cfg["beats"] * BEAT
        self.t1 = self.t0 + self.dur
        ramp = cfg.get("ramp") or [[0, cfg.get("speed", 1.0)], [1, cfg.get("speed", 1.0)]]
        n = int(np.ceil(self.dur * FPS * 8)) + 2
        p = np.linspace(0, 1, n)
        speed = np.interp(p, [k[0] for k in ramp], [k[1] for k in ramp])
        self.cum = np.concatenate([[0], np.cumsum((speed[1:] + speed[:-1]) / 2 * self.dur / (n - 1))])
        self.p = p
        if "kill" in cfg:  # place the kill exactly on a beat of this segment
            kb = cfg.get("kill_beat", cfg["beats"] / 2)
            self.src_in = cfg["kill"] - np.interp(kb / cfg["beats"], p, self.cum)
        else:
            self.src_in = cfg.get("in", 0.0)
        self.file = cfg["file"]
        self.focus = cfg.get("focus", [0.5, 0.5])
        src_end = self.src_at(self.t1)
        shots = cfg.get("shots", "auto")
        if shots == "auto":
            shots = detect_shots(clip_audio, max(self.src_in, 0), src_end)
        self.shots_src = [s for s in shots if self.src_in <= s <= src_end]
        self.shots = [self.out_at(s) for s in self.shots_src]
        self.kills = [self.out_at(cfg["kill"])] if "kill" in cfg else []

    def src_at(self, t):
        return self.src_in + np.interp((t - self.t0) / self.dur, self.p, self.cum)

    def out_at(self, s):
        return self.t0 + np.interp(s - self.src_in, self.cum, self.p) * self.dur


def build_segments(cfg, audios):
    segs, t = [], cfg.get("start", 0.0)
    for c in cfg["segments"]:
        s = Segment(c, t, audios[c["file"]])
        segs.append(s)
        t = s.t1
    return segs


# ── text overlays ───────────────────────────────────────────
def text_layer(text, size, color=(255, 255, 255), stroke=0):
    font = ImageFont.truetype("fonts/Anton.ttf", size)
    l, t, r, b = font.getbbox(text, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 40, b - t + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20 - l, 20 - t), text, font=font, fill=color + (255,),
                            stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return np.array(im)


def overlay(img, layer, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    lay = cv2.resize(layer, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = lay.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, OW), min(y0 + h, OH)
    if xb <= xa or yb <= ya:
        return
    sub = lay[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = sub[..., 3:4] / 255 * alpha
    roi = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = (roi * (1 - a) + sub[..., 2::-1] * a).astype(np.uint8)


# ── look ────────────────────────────────────────────────────
_curve = np.clip(255 * (0.5 + 0.5 * np.tanh((np.arange(256) / 255 - 0.5) * 2.6) / np.tanh(1.3)), 0, 255).astype(np.uint8)
_yy, _xx = np.mgrid[0:OH, 0:OW]
VIGNETTE = (1 - 0.42 * (((_xx - OW / 2) / (OW / 2)) ** 2 + ((_yy - OH / 2) / (OH / 2)) ** 2) ** 1.4 * 0.5)[..., None].astype(np.float32)
VIGNETTE = np.clip(VIGNETTE, 0.45, 1)


def grade(img, sat=1.3):
    img = cv2.LUT(img, _curve)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return (img.astype(np.float32) * VIGNETTE).astype(np.uint8)


def rgb_split(img, px):
    if px < 1:
        return img
    px = int(px)
    out = img.copy()
    out[:, px:, 2] = img[:, :-px, 2]
    out[:, :-px, 0] = img[:, px:, 0]
    return out


def h_motion_blur(img, k):
    k = int(k)
    if k < 3:
        return img
    kern = np.zeros((1, k), np.float32)
    kern[0, :] = 1 / k
    return cv2.filter2D(img, -1, kern)


# ── render ──────────────────────────────────────────────────
def render(cfg_path, out_path):
    cfg = json.load(open(cfg_path))
    files = sorted({s["file"] for s in cfg["segments"]})
    audios = {f: load_audio(f) for f in files}
    segs = build_segments(cfg, audios)
    total = segs[-1].t1 + cfg.get("outro", 0.0)
    cuts = [s.t0 for s in segs[1:]]
    kicks = [k for k in TIMING["kicks"] if k < total]
    drop = TIMING["drop"]
    texts = [(t, text_layer(t["text"], t.get("size", 150), tuple(t.get("color", [255, 255, 255])), 6)) for t in cfg.get("texts", [])]
    rng = np.random.default_rng(1)
    shake_noise = rng.standard_normal((int(total * FPS) + 10, 3))
    shake_noise = cv2.GaussianBlur(shake_noise, (1, 5), 0)

    events = {"shots": [t for s in segs for t in s.shots], "kills": [t for s in segs for t in s.kills]}
    print(f"{len(segs)} segments, {total:.2f}s, shots {len(events['shots'])}, kills {len(events['kills'])}")

    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", "/tmp/_edit_video.mp4"], stdin=subprocess.PIPE)
    streams = {}
    nframes = int(round(total * FPS))
    for f in range(nframes):
        t = f / FPS
        seg = next((s for s in segs if s.t0 <= t < s.t1), segs[-1])
        if seg not in streams:
            for s in list(streams):
                streams.pop(s).close()
            streams[seg] = FrameStream(seg.file, seg.src_in - 0.05, seg.src_at(seg.t1) - seg.src_in + 0.2)
        frozen = t >= segs[-1].t1  # outro: freeze on last frame
        src = streams[seg].at(seg.src_at(min(t, seg.t1 - 1e-3)))

        # camera: base zoom drift + punches + shake + whip offset
        u = (t - seg.t0) / seg.dur
        zoom = seg.cfg.get("zoom", 1.08) + 0.06 * u
        for k in kicks:
            zoom += 0.035 * pulse(t - k, 0.09) if t >= drop else 0
        for c in cuts:
            zoom += 0.14 * pulse(t - c, 0.12)
        for k in events["kills"]:
            zoom += 0.22 * pulse(t - k, 0.16)
        zoom += 0.25 * pulse(t - drop, 0.25)
        if frozen:
            zoom += 0.08 * ease_out((t - segs[-1].t1) / 0.8)
        sh = 0.0
        for s_ in events["shots"]:
            sh += pulse(t - s_, 0.07)
        for k in events["kills"]:
            sh += 1.6 * pulse(t - k, 0.12)
        sh += 2.0 * pulse(t - drop, 0.18)
        sh = min(sh, 2.5)
        n = shake_noise[f]
        dx, dy, rot = n[0] * 22 * sh, n[1] * 22 * sh, n[2] * 0.9 * sh

        whip, blur = 0.0, 0.0
        for c in cuts:
            d = t - c
            if -0.07 <= d < 0:
                e = (d + 0.07) / 0.07
                whip, blur = -OW * 0.55 * e ** 2, 90 * e
            elif 0 <= d < 0.09:
                e = 1 - d / 0.09
                whip, blur = OW * 0.55 * e ** 2, 90 * e

        # one affine: output pixel → source pixel (9:16 window around focus point)
        crop_h = 1080 / zoom
        scale = OH / crop_h
        fx, fy = seg.focus[0] * 1920, seg.focus[1] * 1080
        M = cv2.getRotationMatrix2D((fx, fy), rot, scale)
        M[0, 2] += OW / 2 - fx + dx + whip
        M[1, 2] += OH / 2 - fy + dy
        img = cv2.warpAffine(src, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = h_motion_blur(img, blur)
        img = grade(img, seg.cfg.get("sat", 1.3))

        split = 0.0
        for k in events["kills"]:
            split += 18 * pulse(t - k, 0.12)
        for c in cuts:
            split += 10 * pulse(t - c, 0.06)
        split += 24 * pulse(t - drop, 0.2)
        img = rgb_split(img, min(split, 30))

        flash = 0.0
        for k in events["kills"]:
            flash += 0.45 * pulse(t - k, 0.07)
        flash += 0.85 * pulse(t - drop, 0.12)
        flash += 0.7 * pulse(t - TIMING["end"], 0.15) if TIMING["end"] < total else 0
        if seg.cfg.get("dim_before_drop") and t < drop:
            img = (img * (0.55 + 0.45 * ease_out(u))).astype(np.uint8)
        if flash > 0.01:
            img = cv2.addWeighted(img, 1 - min(flash, 0.9), np.full_like(img, 255), min(flash, 0.9), 0)

        for tc, lay in texts:
            d = t - tc["t"]
            if 0 <= d < tc["dur"]:
                pop = 1 + 0.35 * np.exp(-d / 0.06) * np.cos(d * 40)
                fade = min(1, (tc["dur"] - d) / 0.12)
                overlay(img, lay, OW / 2, tc.get("y", 0.5) * OH, pop * tc.get("scale", 1), fade)

        enc.stdin.write(img.tobytes())
        if f % 120 == 0:
            print(f"frame {f}/{nframes}")
    enc.stdin.close()
    enc.wait()
    for s in streams.values():
        s.close()

    mix_audio(cfg, segs, audios, events, cuts, total)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "/tmp/_edit_video.mp4", "-i", "/tmp/_edit_audio.wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out_path], check=True)
    print("wrote", out_path)


def mix_audio(cfg, segs, audios, events, cuts, total):
    n = int(total * SR)
    rd = lambda p: wavfile.read(p)[1].astype(np.float32) / 32768
    music = rd("audio/music.wav")[:n]
    music = np.pad(music, (0, max(0, n - len(music))))
    sfx = {k: rd(f"audio/{k}.wav") for k in ("gunshot", "headshot", "whoosh", "impact")}

    # game audio follows the same time map as the picture (slow-mo pitches down)
    game = np.zeros(n, np.float32)
    t = np.arange(n) / SR
    for s in segs:
        m = (t >= s.t0) & (t < s.t1)
        st = s.src_at(t[m])
        a = audios[s.file]
        game[m] = np.interp(st * SR, np.arange(len(a)), a, left=0, right=0)
    game = game / (np.max(np.abs(game)) + 1e-9)

    fx = np.zeros(n, np.float32)

    def place(sig, at, g):
        i = int(at * SR)
        if 0 <= i < n:
            j = min(n, i + len(sig))
            fx[i:j] += sig[: j - i] * g

    for s_ in events["shots"]:
        place(sfx["gunshot"], s_, 0.35)
    for k in events["kills"]:
        place(sfx["headshot"], k, 0.6)
        place(sfx["gunshot"], k, 0.5)
    for c in cuts:
        place(sfx["whoosh"], c - 0.3, 0.5)
    mix = music * cfg.get("music_gain", 0.8) + game * cfg.get("game_gain", 0.45) + fx
    mix = np.tanh(mix * 1.1)
    fade = int(0.3 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.95
    wavfile.write("/tmp/_edit_audio.wav", SR, (mix * 32767).astype(np.int16))


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "edit.json", sys.argv[2] if len(sys.argv) > 2 else "edit.mp4")

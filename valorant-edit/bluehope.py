"""BLUE HOPE — Valorant TikTok edit (1080x1920, 60 fps, ~17.8 s).

    python3 bluehope_audio.py          # music + sfx
    python3 bluehope.py                # full render -> bluehope_edit.mp4
    python3 bluehope.py --stills 0.5 1.8 ...   # preview frames -> work/
"""
import json
import os
import subprocess
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile

OW, OH, FPS, SR = 1080, 1920, 60, 44100
TM = json.load(open("audio/bh_timing.json"))
BEAT, TOTAL, KICKS = TM["beat"], TM["total"], TM["kicks"]
B = lambda n: n * BEAT
DROP, OUTRO = B(4), B(36)
CAM_IN = 12.62          # output time the caster-cam split screen comes in

# brand colours (BGR)
BLUE = np.array([246, 158, 6], np.float32)      # #069EF6
LIGHT = np.array([255, 205, 120], np.float32)   # #78CDFF
NAVY = np.array([48, 22, 8], np.float32)        # #081630

CLIPS = {k: f"clips/{k}.mp4" for k in ("c1", "c2", "c3", "c4")}

# kill / shot times are in SOURCE seconds, read frame-by-frame from the clips
SEGMENTS = [
    dict(clip="c4", beats=6, kill=6.716, kill_beat=4, shots=[6.716], zoom=1.06, game=0.25,
         ramp=[[0, .45], [.64, .45], [.667, 1.0], [1, 1.0]], text=("ONE TAP", 0.0, 0.85)),
    dict(clip="c1", beats=4, kill=1.30, kill_beat=2, shots=[1.233, 1.30, 1.433, 1.533], zoom=1.08, trans="whip",
         ramp=[[0, 1.25], [.4, 1.1], [.5, .3], [.78, .3], [.9, 1.0], [1, 1.0]]),
    dict(clip="c3", beats=4, src_in=4.38, speed=1.0, shots=[4.466, 4.733, 4.933, 5.20, 5.466, 5.75], zoom=1.24, trans="glitch"),
    dict(clip="c1", beats=4, kill=8.466, kill_beat=2, shots=[8.466], zoom=1.06, trans="zoom",
         ramp=[[0, 1.2], [.42, 1.0], [.5, .28], [.8, .28], [.92, 1.0], [1, 1.0]]),
    dict(clip="c2", beats=4, src_in=5.22, speed=0.78, shots=[5.333, 5.533, 5.80, 6.00, 6.20, 6.30], zoom=1.26, trans="wipe"),
    dict(clip="c4", beats=6, kill=9.80, kill_beat=2, shots=[9.633, 9.80], zoom=1.06, trans="whip",
         ramp=[[0, 1.1], [.3, 1.0], [.333, .35], [.68, .35], [.8, 1.0], [1, 1.0]], text=("CLUTCH", 0.05, 0.95)),
    dict(clip="c1", beats=8, kill=12.0, kill_beat=1, shots=[11.966, 12.0], zoom=1.04, trans="zoom", game=0.72, speed=1.0),
]


# ── small maths ─────────────────────────────────────────────
def clamp(x, a=0.0, b=1.0):
    return min(b, max(a, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a))


def out_cubic(u): return 1 - (1 - u) ** 3
def in_cubic(u): return u ** 3
def out_expo(u): return 1 if u >= 1 else 1 - 2 ** (-10 * u)
def in_expo(u): return 0 if u <= 0 else 2 ** (10 * u - 10)
def in_out_cubic(u): return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def out_back(u, s=1.70158): return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2
def pulse(dt, decay): return float(np.exp(-dt / decay)) if dt >= 0 else 0.0


# ── sources ─────────────────────────────────────────────────
def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


class SRSource:
    """Real-ESRGAN x4 frames pre-computed by prepare_sr.py (60 fps indices)."""

    def __init__(self, name):
        self.dir = f"cache/sr/{name}"
        self.frames = {}

    def get(self, i):
        if i not in self.frames:
            if not os.path.exists(f"{self.dir}/{i:05d}.jpg"):  # should not happen: fall back to nearest
                i = min((int(f[:5]) for f in os.listdir(self.dir)), key=lambda k: abs(k - i))
            if len(self.frames) > 6:
                self.frames.pop(next(iter(self.frames)))
            self.frames[i] = cv2.imread(f"{self.dir}/{i:05d}.jpg")
        return self.frames[i]


DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
_flow_cache = {}
_grid_cache = {}


def interpolated(stream, fpos):
    """Optical-flow frame interpolation (smooth 'twixtor' slow motion)."""
    i0 = int(np.floor(fpos))
    a = float(fpos - i0)
    f0 = stream.get(i0)
    if a < 0.05:
        return f0
    f1 = stream.get(i0 + 1)
    if a > 0.95:
        return f1
    key = (id(stream), i0)
    if key not in _flow_cache:
        _flow_cache.clear()
        g0 = cv2.cvtColor(cv2.resize(f0, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        g1 = cv2.cvtColor(cv2.resize(f1, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        up = lambda f: cv2.resize(f, (f0.shape[1], f0.shape[0])) * 4
        _flow_cache[key] = (up(DIS.calc(g0, g1, None)), up(DIS.calc(g1, g0, None)))
    f01, f10 = _flow_cache[key]
    h, w = f0.shape[:2]
    if (w, h) not in _grid_cache:
        gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        _grid_cache[(w, h)] = (gx, gy)
    gx, gy = _grid_cache[(w, h)]
    w0 = cv2.remap(f0, gx - a * f01[..., 0], gy - a * f01[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.remap(f1, gx - (1 - a) * f10[..., 0], gy - (1 - a) * f10[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(w0, 1 - a, w1, a, 0)


# ── timeline ────────────────────────────────────────────────
class Segment:
    def __init__(self, cfg, t0):
        self.cfg, self.clip, self.t0 = cfg, cfg["clip"], t0
        self.dur = cfg["beats"] * BEAT
        self.t1 = t0 + self.dur
        sp = cfg.get("speed", 1.0)
        ramp = cfg.get("ramp") or [[0, sp], [1, sp]]
        n = 4000
        self.p = np.linspace(0, 1, n)
        speed = np.interp(self.p, [k[0] for k in ramp], [k[1] for k in ramp])
        self.speed = speed
        self.cum = np.concatenate([[0], np.cumsum((speed[1:] + speed[:-1]) / 2 * self.dur / (n - 1))])
        if "kill" in cfg:
            self.src_in = cfg["kill"] - np.interp(cfg["kill_beat"] / cfg["beats"], self.p, self.cum)
        else:
            self.src_in = cfg["src_in"]
        self.src_out = self.src_in + self.cum[-1]
        self.shots = [self.out_at(s) for s in cfg.get("shots", []) if self.src_in <= s <= self.src_out]
        self.kills = [self.out_at(cfg["kill"])] if "kill" in cfg else []

    def src_at(self, t):
        return self.src_in + np.interp((t - self.t0) / self.dur, self.p, self.cum)

    def speed_at(self, t):
        return float(np.interp((t - self.t0) / self.dur, self.p, self.speed))

    def out_at(self, s):
        return self.t0 + float(np.interp(s - self.src_in, self.cum, self.p)) * self.dur


SEGS = []
_t = 0.0
for c in SEGMENTS:
    SEGS.append(Segment(c, _t))
    _t = SEGS[-1].t1
assert abs(SEGS[-1].t1 - OUTRO) < 1e-6, SEGS[-1].t1
CUTS = [(s.t0, s.cfg.get("trans", "whip")) for s in SEGS[1:]] + [(OUTRO, "flash")]
KILLS = [k for s in SEGS for k in s.kills]
SHOTS = [k for s in SEGS for k in s.shots]


# ── graphics assets ─────────────────────────────────────────
def pil_text(text, font, size, fill=(255, 255, 255), stroke=0, stroke_fill=(8, 22, 48), spacing=0):
    f = ImageFont.truetype(font, size)
    widths = [f.getlength(ch) + spacing for ch in text]
    asc, desc = f.getmetrics()
    W = int(sum(widths) + 2 * stroke + 20)
    im = Image.new("RGBA", (W, asc + desc + 2 * stroke + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 10 + stroke
    for ch, w in zip(text, widths):
        d.text((x, 10 + stroke), ch, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=stroke_fill + (255,))
        x += w
    a = np.array(im)
    ys, xs = np.nonzero(a[..., 3])
    return rgba_to_layer(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def rgba_to_layer(a):
    """RGBA uint8 (PIL order) -> (BGR float32, alpha float32 0..1)."""
    return a[..., 2::-1].astype(np.float32), a[..., 3].astype(np.float32) / 255


def load_logo(width):
    im = Image.open("logo.png").convert("RGBA")
    im = im.crop(im.getbbox())
    im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    return rgba_to_layer(np.array(im))


ANTON, CHAKRA = "fonts/Anton.ttf", "fonts/ChakraPetch-SemiBold.ttf"
LOGO_BIG = load_logo(700)
LOGO_SMALL = load_logo(96)
WM_TEXT = pil_text("BLUE HOPE", ANTON, 46, spacing=3)
TITLE_LETTERS = [pil_text(ch, ANTON, 190, fill=(255, 255, 255) if i < 4 else (6, 158, 246)) if ch != " " else None
                 for i, ch in enumerate("BLUE HOPE")]
TAG = pil_text("E S P O R T", CHAKRA, 62, fill=(120, 205, 255))
POPS = {s.cfg["text"][0]: pil_text(s.cfg["text"][0], ANTON, 210, stroke=10, stroke_fill=(8, 22, 48), spacing=4)
        for s in SEGS if "text" in s.cfg}


def glow_of(layer, sigma, color):
    bgr, a = layer
    pad = int(sigma * 3)
    ap = cv2.copyMakeBorder(a, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    g = cv2.GaussianBlur(ap, (0, 0), sigma)
    g = g / (g.max() + 1e-6)
    return (np.ones(g.shape + (3,), np.float32) * color, g)


LOGO_GLOW = glow_of(LOGO_BIG, 28, LIGHT)
POP_GLOWS = {w: glow_of(l, 18, BLUE) for w, l in POPS.items()}
TITLE_W = sum((l[0].shape[1] if l else 60) + 12 for l in TITLE_LETTERS) - 12


def blit(img, layer, cx, cy, scale=1.0, alpha=1.0, add=False, mask_fn=None):
    """Composite a (bgr, alpha) layer centred at (cx, cy). img is float32 BGR."""
    if alpha <= 0.004 or scale <= 0.01:
        return
    bgr, a = layer
    if abs(scale - 1) > 1e-3:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        a = cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = a.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, OW), min(y0 + h, OH)
    if xb <= xa or yb <= ya:
        return
    sa = a[ya - y0:yb - y0, xa - x0:xb - x0] * alpha
    if mask_fn is not None:
        sa = sa * mask_fn(np.arange(xa, xb)[None, :] - cx, np.arange(ya, yb)[:, None] - cy, w, h)
    sb = bgr[ya - y0:yb - y0, xa - x0:xb - x0]
    roi = img[ya:yb, xa:xb]
    if add:
        roi += sb * sa[..., None]
    else:
        roi *= (1 - sa[..., None])
        roi += sb * sa[..., None]


# ── look ────────────────────────────────────────────────────
_x = np.arange(256) / 255
_lift = _x ** 0.78                                                    # brighter shadows & mids
CURVE = np.clip(255 * 1.03 * (0.5 + 0.5 * np.tanh((_lift - 0.5) * 2.3) / np.tanh(1.15)), 0, 255).astype(np.uint8)
_yy, _xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
VIGN = np.clip(1 - 0.3 * ((((_xx - OW / 2) / (OW * .62)) ** 2 + ((_yy - OH / 2) / (OH * .62)) ** 2) ** 1.5), .5, 1)[..., None]
RADIAL = (np.clip(1 - ((_xx - OW / 2) ** 2 + (_yy - OH * 0.40) ** 2) ** 0.5 / 900, 0, 1) ** 2)[..., None]
GRAIN = [np.random.default_rng(i).normal(0, 2.2, (OH, OW, 1)).astype(np.float32) for i in range(6)]


def grade(img_u8, sat=1.38):
    h, w = img_u8.shape[:2]
    blur = cv2.GaussianBlur(img_u8, (0, 0), 1.2)
    img = cv2.addWeighted(img_u8, 1.22, blur, -0.22, 0)                   # light crispening
    img = cv2.LUT(img, CURVE)                                             # lift + contrast
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv[..., 1] = cv2.multiply(hsv[..., 1], sat)
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR).astype(np.float32)
    lum = img.mean(axis=2, keepdims=True) / 255
    img += (BLUE - img) * 0.07 * (1 - lum) ** 2                           # team-blue shadows
    small = cv2.resize(img, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    bright = np.clip(small - 172, 0, None)
    bloom = cv2.resize(cv2.GaussianBlur(bright, (0, 0), 7), (w, h))
    return img + bloom * 0.7


def radial_blur(img, amount, n=6):
    h, w = img.shape[:2]
    acc = img.copy()
    for k in range(1, n):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, 1 + amount * k / n)
        acc += cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return acc / n


def h_blur(img, k):
    k = int(k)
    if k < 3:
        return img
    return cv2.blur(img, (k, 1))


def rgb_split(img, px):
    px = int(px)
    if px < 1:
        return img
    out = img.copy()
    out[:, px:, 2] = img[:, :-px, 2]
    out[:, :-px, 0] = img[:, px:, 0]
    return out


def glitch(img, strength, seed):
    r = np.random.default_rng(seed)
    out = img.copy()
    for _ in range(int(10 * strength) + 2):
        y = r.integers(0, OH - 40)
        h = int(r.integers(12, 140))
        dx = int(r.normal(0, 90 * strength))
        out[y:y + h] = np.roll(img[y:y + h], dx, axis=1)
        if r.random() < 0.25 * strength:
            out[y:y + h] = out[y:y + h] * 0.4 + BLUE * 0.6
    return rgb_split(out, 26 * strength)


def wipe_band(img, p, t):
    """Brand-coloured skewed band; fully covers the frame at p = 0.5."""
    e = in_out_cubic(clamp(p))
    L = -2.35 * OW + e * 3.7 * OW
    R = L + 2.0 * OW
    sk = 0.35 * OW
    poly = lambda l, r: np.array([[l + sk, 0], [r + sk, 0], [r - sk, OH], [l - sk, OH]], np.int32)
    over = np.zeros((OH, OW), np.uint8)
    cv2.fillPoly(over, [poly(L, R)], 255)
    m = over.astype(np.float32)[..., None] / 255
    img[:] = img * (1 - m) + NAVY * m
    for edge, col, wdt in ((L, BLUE, 70), (R - 70, BLUE, 70), (L + 70, LIGHT, 8), (R - 78, LIGHT, 8)):
        over[:] = 0
        cv2.fillPoly(over, [poly(edge, edge + wdt)], 255)
        m = over.astype(np.float32)[..., None] / 255
        img[:] = img * (1 - m) + col * m
    if 0.3 < p < 0.7:
        blit(img, LOGO_SMALL, OW / 2 + (L + R) / 2 - OW / 2, OH / 2, 2.6, 1.0)


# ── motion graphics ─────────────────────────────────────────
def title_block(img, t, t0, cx, cy, scale=1.0, alpha=1.0):
    """'BLUE HOPE' letters slam in one by one, then underline + ESPORT tag."""
    x = cx - TITLE_W * scale / 2
    for i, lay in enumerate(TITLE_LETTERS):
        w = (lay[0].shape[1] if lay else 60)
        if lay:
            u = prog(t, t0 + i * 0.035, t0 + i * 0.035 + 0.2)
            if u > 0:
                s = scale * (1 + 1.3 * (1 - out_cubic(u)))
                blit(img, lay, x + w * scale / 2, cy, s, alpha * min(1, u * 3))
        x += (w + 12) * scale
    u = out_expo(prog(t, t0 + 0.35, t0 + 0.75))
    if u > 0:
        bw = TITLE_W * scale * u
        y = int(cy + 112 * scale)
        img[y:y + int(12 * scale), int(cx - bw / 2):int(cx + bw / 2)] = \
            img[y:y + int(12 * scale), int(cx - bw / 2):int(cx + bw / 2)] * (1 - alpha) + BLUE * alpha
    ta = prog(t, t0 + 0.5, t0 + 0.8) * alpha
    blit(img, TAG, cx, cy + 170 * scale, scale, ta)


def logo_block(img, t, t0, cx, cy, scale=1.0, alpha=1.0, shine_at=(0.45,)):
    """Logo: wings spread from the centre (mask), glow, then a shine sweep."""
    u = out_expo(prog(t, t0, t0 + 0.55))
    if u <= 0:
        return
    rise = (1 - u) * 50
    lw = LOGO_BIG[1].shape[1] * scale
    half = u * lw / 2 + 2

    def wings(dx, dy, w, h):
        return np.clip((half - np.abs(dx)) / 25, 0, 1)

    glow_a = alpha * (0.55 + 0.45 * pulse(t - t0 - 0.35, 0.4)) * u
    blit(img, LOGO_GLOW, cx, cy + rise, scale, glow_a * 0.85, add=True, mask_fn=wings)
    blit(img, LOGO_BIG, cx, cy + rise, scale * (0.92 + 0.08 * u), alpha, mask_fn=wings)
    for so in shine_at:
        shine_pass(img, prog(t, t0 + so, t0 + so + 0.5), cx, cy + rise, scale * (0.92 + 0.08 * u), lw, alpha)


def shine_pass(img, sh, cx, cy, scale, lw, alpha):
    if 0 < sh < 1:
        pos = (-0.7 + 1.4 * sh) * lw

        def shine(dx, dy, w, h):
            return np.clip(1 - np.abs(dx + dy * 0.5 - pos) / 45, 0, 1)

        white = (np.full_like(LOGO_BIG[0], 255), LOGO_BIG[1])
        blit(img, white, cx, cy, scale, alpha * 0.8, add=False, mask_fn=shine)


def streaks(img, t, t0, color=LIGHT):
    for k, (off, wdt, a) in enumerate(((0, 10, .9), (.08, 4, .6), (.15, 22, .35))):
        u = prog(t, t0 + off, t0 + off + 0.45)
        if not 0 < u < 1:
            continue
        x = -OW + in_out_cubic(u) * 3 * OW
        over = np.zeros((OH, OW), np.uint8)
        poly = np.array([[x, 0], [x + wdt, 0], [x + wdt - OW * .9, OH], [x - OW * .9, OH]], np.int32)
        cv2.fillPoly(over, [poly], 255)
        img += (over.astype(np.float32)[..., None] / 255) * color * a * np.sin(np.pi * u)


def ring(img, t, t0, cx, cy, maxr=620, color=BLUE):
    u = prog(t, t0, t0 + 0.7)
    if 0 < u < 1:
        over = np.zeros((OH, OW), np.uint8)
        cv2.circle(over, (int(cx), int(cy)), int(60 + out_cubic(u) * maxr), 255, max(1, int(14 * (1 - u))), cv2.LINE_AA)
        img += (over.astype(np.float32)[..., None] / 255) * color * (1 - u)


def sparks(img, t, t0, cx, cy, n=36, seed=3):
    u = prog(t, t0, t0 + 0.7)
    if not 0 < u < 1:
        return
    r = np.random.default_rng(seed)
    over = np.zeros((OH, OW), np.uint8)
    for _ in range(n):
        ang, sp, ln = r.uniform(0, 2 * np.pi), r.uniform(300, 900), r.uniform(30, 90)
        d0 = 80 + out_cubic(u) * sp
        p0 = (int(cx + np.cos(ang) * d0), int(cy + np.sin(ang) * d0))
        p1 = (int(cx + np.cos(ang) * (d0 + ln * (1 - u))), int(cy + np.sin(ang) * (d0 + ln * (1 - u))))
        cv2.line(over, p0, p1, 255, 4, cv2.LINE_AA)
    img += (over.astype(np.float32)[..., None] / 255) * LIGHT * (1 - u)


MOTES = np.random.default_rng(5).uniform(0, 1, (70, 4))


def motes(img, t, d):
    """Soft particles drifting up behind the end card."""
    a = prog(d, 0.1, 0.6)
    for x, y0, sp, sz in MOTES:
        y = (y0 * OH - d * (80 + 220 * sp)) % OH
        r = int(2 + 5 * sz)
        cx, cy = int(x * OW), int(y)
        roi = img[max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1]
        roi += LIGHT * 0.35 * a * (0.4 + 0.6 * sz)


def corners(img, t, a):
    if a <= 0:
        return
    k = 1 + sum(0.15 * pulse(t - kk, 0.12) for kk in KICKS)
    m, s, th = 38, int(64 * k), 6
    over = np.zeros((OH, OW), np.uint8)
    for (x, y, dx, dy) in ((m, m + 140, 1, 1), (OW - m, m + 140, -1, 1), (m, OH - m - 260, 1, -1), (OW - m, OH - m - 260, -1, -1)):
        cv2.line(over, (x, y), (x + dx * s, y), 255, th)
        cv2.line(over, (x, y), (x, y + dy * s), 255, th)
    img[:] = img * (1 - over[..., None] / 255 * a * .8) + BLUE * (over[..., None] / 255 * a * .8)


def watermark(img, t):
    a = prog(t, DROP + 0.25, DROP + 0.55) * (1 - prog(t, CAM_IN, CAM_IN + 0.2))
    if a <= 0:
        return
    slide = (1 - out_cubic(prog(t, DROP + 0.25, DROP + 0.6))) * -120
    blit(img, LOGO_SMALL, 52 + 48 + slide, 200, 1.0, a)
    blit(img, WM_TEXT, 52 + 104 + WM_TEXT[1].shape[1] / 2 + slide, 202, 1.0, a * 0.95)
    corners(img, t, a * 0.85 * (1 - prog(t, CAM_IN, CAM_IN + 0.2)))


def text_pops(img, t):
    for s in SEGS:
        if "text" not in s.cfg:
            continue
        word, off, dur = s.cfg["text"]
        t0 = s.kills[0] + off
        d = t - t0
        if 0 <= d < dur:
            sc = 1 + 0.5 * np.exp(-d / 0.05) * np.cos(d * 45)
            a = min(1, d / 0.03) * min(1, (dur - d) / 0.15)
            sh = np.random.default_rng(int(t * 60)).normal(0, 8 * pulse(d, 0.12), 2)
            lay = POPS[word]
            blit(img, POP_GLOWS[word], OW / 2 + sh[0], OH * 0.34 + sh[1], sc, a * 0.9, add=True)
            blit(img, lay, OW / 2 + sh[0], OH * 0.34 + sh[1], sc, a)


# ── per-frame render ────────────────────────────────────────
def rounded_mask(w, h, r):
    r = int(max(0, min(r, w // 2, h // 2)))
    m = np.zeros((h, w), np.uint8)
    if r == 0:
        m[:] = 255
    else:
        cv2.rectangle(m, (r, 0), (w - r - 1, h - 1), 255, -1)
        cv2.rectangle(m, (0, r), (w - 1, h - r - 1), 255, -1)
        for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
            cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


def pill(text, fill=(6, 158, 246)):
    tl = pil_text(text, CHAKRA, 40, fill=(255, 255, 255))
    th, tw = tl[1].shape
    w, h = tw + 96, th + 30
    bgr = np.empty((h, w, 3), np.float32)
    bgr[:] = np.array(fill[::-1], np.float32)
    a = rounded_mask(w, h, h // 2)
    cv2.circle(bgr, (34, h // 2), 11, (40, 40, 235), -1, cv2.LINE_AA)
    bgr[15:15 + th, 62:62 + tw] = bgr[15:15 + th, 62:62 + tw] * (1 - tl[1][..., None]) + tl[0] * tl[1][..., None]
    return bgr, a


CAM_PANEL = (40, 272, 1000, 750)    # x, y, w, h  (caster cam, top)
GAME_PANEL = (40, 1056, 1000, 700)  # gameplay, bottom
CASTER_PILL = pill("CASTER")
SCREAM = pil_text("OUI ! OUI !", ANTON, 150, stroke=9, stroke_fill=(8, 22, 48), spacing=3)
SCREAM_GLOW = glow_of(SCREAM, 16, BLUE)


class Renderer:
    def __init__(self):
        from scipy.signal import butter, sosfilt
        self.src = {c: SRSource(c) for c in CLIPS}
        self.cam = SRSource("cam")
        self.freeze = None
        # caster voice envelope (per 60 fps source frame) drives the cam panel's reactions
        a = load_audio(CLIPS[SEGS[-1].clip])
        v = sosfilt(butter(2, [300, 3000], "band", fs=SR, output="sos"), a)
        hop = SR // FPS
        r = np.sqrt(np.add.reduceat(v[: len(v) // hop * hop] ** 2, np.arange(0, len(v) // hop * hop, hop)) / hop)
        env = np.zeros_like(r)
        for i in range(len(r)):
            env[i] = max(r[i], env[i - 1] * 0.86 if i else 0)
        ref = np.percentile(env[int(12 * FPS):int(15 * FPS)], 92)
        self.voice = np.clip(env / (ref + 1e-9), 0, 1.25)

    def source_image(self, seg, t):
        src = self.src[seg.clip]
        fpos = seg.src_at(t) * FPS
        if seg.speed_at(t) < 0.9:
            return interpolated(src, fpos)
        return src.get(int(round(fpos)))

    def camera(self, t, seg):
        u = (t - seg.t0) / seg.dur
        zoom = seg.cfg.get("zoom", 1.1) * (1 + 0.05 * u)
        if t >= DROP:
            zoom += sum(0.03 * pulse(t - k, 0.09) for k in KICKS)
        zoom += sum(0.13 * pulse(t - c, 0.12) for c, _ in CUTS)
        zoom += sum(0.16 * pulse(t - k, 0.16) for k in KILLS)
        zoom += sum(0.025 * pulse(t - k, 0.06) for k in SHOTS)
        sh = sum(pulse(t - s, 0.07) for s in SHOTS) + sum(1.5 * pulse(t - k, 0.12) for k in KILLS)
        sh += 2.0 * pulse(t - DROP, 0.18)
        if t < DROP:
            sh += 0.25 * prog(t, B(2), DROP)
        return zoom, min(sh, 2.6)

    def game_frame(self, t, f, seg, size=(OW, OH), panel=0.0):
        frame = self.source_image(seg, t)
        zoom, sh = self.camera(t, seg)
        n = np.random.default_rng(f).normal(0, 1, 3)
        dx, dy, rot = n[0] * 20 * sh, n[1] * 20 * sh, n[2] * 0.8 * sh
        whip = blur = rz = 0.0
        for c, kind in CUTS:
            d = t - c
            if kind == "whip":
                if -0.07 <= d < 0:
                    e = (d + 0.07) / 0.07
                    whip, blur = -OW * 0.6 * e ** 2, 110 * e
                elif 0 <= d < 0.09:
                    e = 1 - d / 0.09
                    whip, blur = OW * 0.6 * e ** 2, 110 * e
            elif kind == "zoom" and -0.1 <= d < 0.12:
                e = 1 - abs(d) / (0.1 if d < 0 else 0.12)
                zoom *= 1 + (0.55 if d < 0 else 0.35) * e ** 2
                rz = 0.28 * e
        pw, ph = size
        H, W = frame.shape[:2]
        ch_full = H / zoom
        ch_panel = (H * 5 / 9) / (zoom / seg.cfg.get("zoom", 1.1))   # wider framing inside the bottom panel
        ch = ch_full + (ch_panel - ch_full) * panel
        scale = ph / ch
        pre = min(1.0, scale * 1.15)                 # area-downscale the 4x frame first: no aliasing
        if pre < 0.98:
            frame = cv2.resize(frame, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA)
        H, W = frame.shape[:2]
        fx, fy = W / 2, H / 2 + H * 0.055 * panel
        M = cv2.getRotationMatrix2D((fx, fy), rot, scale / pre)
        M[0, 2] += pw / 2 - fx + dx + whip
        M[1, 2] += ph / 2 - fy + dy
        img = cv2.warpAffine(frame, M, (pw, ph), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        img = grade(img)
        if blur:
            img = h_blur(img, blur)
        if rz > 0.01:
            img = radial_blur(img, rz)
        return img

    def finale(self, t, f, seg):
        """Split screen: the caster's webcam flies in on top, gameplay shrinks to the bottom."""
        e = out_expo(prog(t, CAM_IN, CAM_IN + 0.42))
        lerp = lambda a, b, u: a + (b - a) * u
        gx, gy, gw, gh = (lerp(a, b, e) for a, b in zip((0, 0, OW, OH), GAME_PANEL))
        gw, gh = int(round(gw)), int(round(gh))
        game = self.game_frame(t, f, seg, (gw, gh), e)
        if e <= 0.001:
            return game
        bg = cv2.resize(cv2.GaussianBlur(cv2.resize(game, (gw // 8, gh // 8)), (0, 0), 3), (OW, OH))
        img = bg * 0.3 + NAVY * 0.62
        m = rounded_mask(gw, gh, 30 * e)[..., None]
        x0, y0 = int(round(gx)), int(round(gy))
        img[y0:y0 + gh, x0:x0 + gw] = img[y0:y0 + gh, x0:x0 + gw] * (1 - m) + game * m

        sidx = int(round(seg.src_at(t) * FPS))
        voice = float(self.voice[min(sidx, len(self.voice) - 1)])
        ec = prog(t, CAM_IN + 0.04, CAM_IN + 0.5)
        if ec > 0:
            s, ep = out_back(ec, 1.4), out_expo(ec)
            cxp, cyp, cwp, chp = CAM_PANEL
            cw = max(40, int(lerp(280, cwp, s) * (1 + 0.035 * voice)))
            chh = max(30, int(lerp(210, chp, s) * (1 + 0.035 * voice)))
            ccx, ccy = lerp(150, cxp + cwp / 2, ep), lerp(190, cyp + chp / 2, ep)
            jit = np.random.default_rng(f + 7).normal(0, 1, 3)
            rot = -10 * (1 - out_cubic(ec)) + 0.9 * voice * jit[2]
            cam = cv2.resize(self.cam.get(sidx), (cw, chh), interpolation=cv2.INTER_AREA)
            cam = grade(cam, sat=1.15)
            pad, bw = 40, 8
            L = np.zeros((chh + 2 * pad, cw + 2 * pad, 3), np.float32)
            A = np.zeros(L.shape[:2], np.float32)
            rm = rounded_mask(cw, chh, 30)
            L[pad:pad + chh, pad:pad + cw] = cam
            A[pad:pad + chh, pad:pad + cw] = rm
            ring_m = rounded_mask(cw + 2 * bw, chh + 2 * bw, 30 + bw)
            ring_m[bw:bw + chh, bw:bw + cw] *= (1 - rm)
            R = np.zeros_like(A)
            R[pad - bw:pad + chh + bw, pad - bw:pad + cw + bw] = ring_m
            L = L * (1 - R[..., None]) + BLUE * R[..., None]
            A = np.maximum(A, R)
            if abs(rot) > 0.05:
                Mr = cv2.getRotationMatrix2D((L.shape[1] / 2, L.shape[0] / 2), rot, 1.0)
                L = cv2.warpAffine(L, Mr, (L.shape[1], L.shape[0]), flags=cv2.INTER_LINEAR)
                A = cv2.warpAffine(A, Mr, (A.shape[1], A.shape[0]), flags=cv2.INTER_LINEAR)
                R = cv2.warpAffine(R, Mr, (R.shape[1], R.shape[0]), flags=cv2.INTER_LINEAR)
            glow = cv2.GaussianBlur(R, (0, 0), 14)
            glow = glow / (glow.max() + 1e-6)
            px, py = ccx + jit[0] * 9 * voice, ccy + jit[1] * 9 * voice
            blit(img, (np.ones_like(L) * LIGHT, glow), px, py, 1.0, (0.45 + 0.55 * min(voice, 1)) * min(1, ec * 2), add=True)
            blit(img, (L, A), px, py, 1.0, 1.0)
            blit(img, CASTER_PILL, px - cw / 2 + CASTER_PILL[1].shape[1] / 2 + 24, py - chh / 2, 1.0, prog(ec, 0.5, 1.0))
        d = t - (CAM_IN + 0.3)
        if d >= 0:
            sc = (1 + 0.45 * np.exp(-d / 0.05) * np.cos(d * 45)) * (1 + 0.1 * voice)
            a = min(1, d / 0.03) * (1 - prog(t, OUTRO - 0.12, OUTRO))
            blit(img, SCREAM_GLOW, OW / 2, 1040, sc, a * 0.9, add=True)
            blit(img, SCREAM, OW / 2, 1040, sc, a)
        return img

    def frame(self, f):
        t = f / FPS
        if t < OUTRO:
            seg = next(s for s in SEGS if s.t0 <= t < s.t1)
            img = self.finale(t, f, seg) if seg is SEGS[-1] and t >= CAM_IN else self.game_frame(t, f, seg)
            if t >= OUTRO - 1.5 / FPS:
                self.freeze = img.copy()
        else:
            img = self.freeze.copy() if self.freeze is not None else np.zeros((OH, OW, 3), np.float32)

        # cut-specific effects
        for c, kind in CUTS:
            d = t - c
            if kind == "glitch" and -0.05 <= d < 0.11:
                img = glitch(img, 1 - abs(d) / 0.11, f)
            if kind == "wipe" and -0.13 <= d < 0.13:
                wipe_band(img, (d + 0.13) / 0.26, t)

        if t < DROP + 0.05:
            self.intro(img, t)
        if t >= OUTRO:
            img = self.outro(img, t)

        split = sum(16 * pulse(t - k, 0.12) for k in KILLS) + sum(8 * pulse(t - c, 0.06) for c, _ in CUTS)
        split += 26 * pulse(t - DROP, 0.2) + 20 * pulse(t - OUTRO, 0.2)
        img = rgb_split(img, min(split, 32))

        watermark(img, t)
        text_pops(img, t)

        flash = sum(0.4 * pulse(t - k, 0.07) for k in KILLS if abs(k - DROP) > 0.01)
        flash += 0.9 * pulse(t - DROP, 0.12) + 0.9 * pulse(t - OUTRO, 0.13) + 0.45 * pulse(t - B(40), 0.12)
        if flash > 0.01:
            fl = min(flash, 0.92)
            img = img * (1 - fl) + 255 * fl
        img = img * VIGN + GRAIN[f % len(GRAIN)]
        return np.clip(img, 0, 255).astype(np.uint8)

    def intro(self, img, t):
        g = 1 - in_cubic(prog(t, B(3.4), DROP))
        if g > 0:
            dark = cv2.GaussianBlur(img, (0, 0), 1 + 9 * g)
            img[:] = dark * (1 - 0.62 * g) + NAVY * 0.5 * g
        cx, cy = OW / 2, OH * 0.40
        ex = in_expo(prog(t, B(3.45), DROP))
        sc = 1 + 3.2 * ex
        a = 1 - ex
        vib = np.random.default_rng(int(t * 60)).normal(0, 7 * prog(t, B(1.8), B(3.45)) * (1 - ex), 2)
        streaks(img, t, 0.0)
        ring(img, t, 0.12, cx, cy)
        logo_block(img, t, 0.08, cx + vib[0], cy - 70 * sc + vib[1], 0.95 * sc, a)
        title_block(img, t, 0.5, cx + vib[0] * .6, cy + 340 * sc, 0.8 * sc, a)

    def outro(self, img, t):
        d = t - OUTRO
        bg = cv2.GaussianBlur(img, (0, 0), 3 + 22 * out_cubic(prog(d, 0, 0.35)))
        k = 0.78 * out_cubic(prog(d, 0, 0.3))
        img = bg * (1 - k) + NAVY * k
        # radial blue light behind the logo, pumping with the kicks
        cx, cy = OW / 2, OH * 0.40
        pump = 1 + sum(0.35 * pulse(t - kk, 0.15) for kk in KICKS)
        img += RADIAL * BLUE * 0.55 * pump
        streaks(img, t, OUTRO + 0.02)
        ring(img, t, OUTRO, cx, cy, 760, LIGHT)
        sparks(img, t, OUTRO, cx, cy)
        n = np.random.default_rng(int(t * 60)).normal(0, 1, 2) * 18 * (pulse(d, 0.15) + 0.6 * pulse(t - B(40), 0.12))
        s = out_back(prog(d, 0, 0.32))
        motes(img, t, d)
        breathe = 1 + 0.012 * np.sin(d * 3) + 0.05 * pulse(t - B(40), 0.2)
        logo_block(img, t, OUTRO - 0.02, cx + n[0], cy - 70 + n[1] + 6 * np.sin(d * 3), 0.95 * max(s, 0.01) * breathe, 1.0,
                   shine_at=(0.45, 1.45))
        title_block(img, t, OUTRO + 0.12, cx + n[0] * .5, cy + 340 + 6 * np.sin(d * 3), 0.8, 1.0)
        return img


# ── audio ───────────────────────────────────────────────────
def mix_audio(path, audios):
    n = int(TOTAL * SR)
    rd = lambda p: wavfile.read(p)[1].astype(np.float32) / 32768
    music = rd("audio/bh_music.wav")[:n]
    music = np.pad(music, (0, n - len(music)))
    sfx = {k: rd(f"audio/{k}.wav") for k in ("gunshot", "headshot", "whoosh", "shimmer", "glitch", "swoosh_rev")}
    t = np.arange(n) / SR
    game = np.zeros(n, np.float32)
    gain = np.zeros(n, np.float32)
    for s in SEGS:
        m = (t >= s.t0) & (t < s.t1)
        a = audios[s.clip]
        game[m] = np.interp(s.src_at(t[m]) * SR, np.arange(len(a)), a, left=0, right=0)
        gain[m] = s.cfg.get("game", 0.42)
    # let the last clip's audio (the caster) ring on under the outro
    last = SEGS[-1]
    m = t >= OUTRO
    a = audios[last.clip]
    game[m] = np.interp((last.src_out + (t[m] - OUTRO)) * SR, np.arange(len(a)), a, left=0, right=0)
    gain[m] = 0.6 * np.clip(1 - (t[m] - OUTRO) / 1.6, 0, 1)
    gain = np.convolve(gain, np.ones(2205) / 2205, "same")  # 50 ms smoothing between segments
    game = game / (np.percentile(np.abs(game), 99.9) + 1e-9) * gain

    fx = np.zeros(n, np.float32)

    def place(sig, at, g):
        i = int(at * SR)
        if i < 0:
            sig, i = sig[-i:], 0
        if i < n:
            j = min(n, i + len(sig))
            fx[i:j] += sig[: j - i] * g

    for s in SHOTS:
        place(sfx["gunshot"], s, 0.22)
    for k in KILLS:
        place(sfx["headshot"], k, 0.32)
        place(sfx["gunshot"], k, 0.4)
    for c, kind in CUTS:
        if kind == "flash":
            continue
        place(sfx["whoosh"], c - 0.24, 0.55)
        if kind == "glitch":
            place(sfx["glitch"], c - 0.05, 0.6)
    place(sfx["shimmer"], 0.1, 0.55)
    place(sfx["swoosh_rev"], DROP - 0.6, 0.6)
    place(sfx["shimmer"], OUTRO + 0.05, 0.5)
    place(sfx["whoosh"], CAM_IN - 0.2, 0.6)

    mus_gain = np.ones(n, np.float32) * 0.74
    mix = music * mus_gain + game + fx
    mix = np.tanh(mix)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.78
    wavfile.write(path, SR, (mix * 32767).astype(np.int16))


def main():
    args = sys.argv[1:]
    r = Renderer()
    if args and args[0] == "--stills":
        times = sorted(float(x) for x in args[1:])
        for tt in times:
            f = int(round(tt * FPS))
            # warm up the freeze frame for outro stills
            if tt >= OUTRO and r.freeze is None:
                r.frame(int(OUTRO * FPS) - 1)
            cv2.imwrite(f"work/still_{tt:.2f}.png", r.frame(f))
        return
    for s in SEGS:
        print(f"{s.clip}: out {s.t0:5.2f}-{s.t1:5.2f}  src {s.src_in:6.3f}-{s.src_out:6.3f}  kills {[round(k, 3) for k in s.kills]}")
    audios = {c: load_audio(p) for c, p in CLIPS.items()}
    mix_audio("work/bh_audio.wav", audios)
    nf = int(round(TOTAL * FPS))
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
                            "-r", str(FPS), "-i", "-", "-i", "work/bh_audio.wav", "-c:v", "libx264", "-preset", "slow",
                            "-crf", "17", "-maxrate", "30M", "-bufsize", "60M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
                            "-movflags", "+faststart", "bluehope_edit.mp4"], stdin=subprocess.PIPE)
    for f in range(nf):
        enc.stdin.write(r.frame(f).tobytes())
        if f % 120 == 0:
            print(f"frame {f}/{nf}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote bluehope_edit.mp4")


if __name__ == "__main__":
    main()

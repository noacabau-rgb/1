"""Pre-computes Real-ESRGAN x4 versions of every source frame the edit uses.

Gameplay: each clip is brought to 720p, a centred strip (REGION_W wide) is
upscaled to 4x -> cache/sr/<clip>/<frame>.jpg  (frame = 60 fps index).
Caster cam (c1 only): the webcam box at native 1080p -> cache/sr/cam/<frame>.jpg
Resumable: existing files are skipped.
"""
import os
import subprocess
import sys
import time
import numpy as np
import cv2
from sr import Upscaler

REGION_W = {"c1": 560, "c2": 480, "c3": 480, "c4": 480}
CAM_BOX = (62, 0, 432, 276)  # x0, y0, x1, y1 in c1's native 1920x1080
FPS = 60


def needed_frames():
    import bluehope as bh
    need = {c: set() for c in bh.CLIPS}
    cam = set()
    for f in range(int(round(bh.OUTRO * FPS)) + 2):
        t = min(f / FPS, bh.OUTRO - 1e-4)
        seg = next(s for s in bh.SEGS if s.t0 <= t < s.t1)
        fpos = seg.src_at(t) * FPS
        if seg.speed_at(t) < 0.9:
            need[seg.clip] |= {int(np.floor(fpos)), int(np.floor(fpos)) + 1}
        else:
            need[seg.clip].add(int(round(fpos)))
        if seg is bh.SEGS[-1] and t >= bh.CAM_IN - 0.2:
            cam.add(int(round(fpos)))
    return need, cam


def region(frame, clip):
    if frame.shape[0] != 720:
        frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
    w = REGION_W[clip]
    x0 = 640 - w // 2
    return frame[:, x0:x0 + w]


def main():
    need, cam = needed_frames()
    total = sum(len(v) for v in need.values()) + len(cam)
    print(f"frames to upscale: {total} ({ {k: len(v) for k, v in need.items()} }, cam {len(cam)})", flush=True)
    up = Upscaler(denoise=0.5)
    done, t0 = 0, time.time()
    for clip, idxs in need.items():
        path = f"clips/{clip}.mp4"
        out_dir = f"cache/sr/{clip}"
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs("cache/sr/cam", exist_ok=True)
        want = set(idxs) | (cam if clip == "c1" else set())
        todo = {i for i in idxs if not os.path.exists(f"{out_dir}/{i:05d}.jpg")}
        cam_todo = {i for i in cam if not os.path.exists(f"cache/sr/cam/{i:05d}.jpg")} if clip == "c1" else set()
        done += len(want) - len(todo) - len(cam_todo)
        if not todo and not cam_todo:
            continue
        w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                        "stream=width,height", "-of", "csv=p=0", path],
                                       capture_output=True, text=True).stdout.strip().split(","))
        last = max(todo | cam_todo)
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=60", "-frames:v", str(last + 1),
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
        for i in range(last + 1):
            buf = p.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            if i not in todo and i not in cam_todo:
                continue
            fr = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            if i in todo:
                cv2.imwrite(f"{out_dir}/{i:05d}.jpg", up(region(fr, clip)), [cv2.IMWRITE_JPEG_QUALITY, 95])
                done += 1
            if i in cam_todo:
                x0, y0, x1, y1 = CAM_BOX
                cv2.imwrite(f"cache/sr/cam/{i:05d}.jpg", up(fr[y0:y1, x0:x1]), [cv2.IMWRITE_JPEG_QUALITY, 95])
                done += 1
            el = time.time() - t0
            print(f"{clip} {i:5d}  {done}/{total}  {el / 60:.1f} min", flush=True)
        p.stdout.close()
        p.kill()
    print("SR done", flush=True)


if __name__ == "__main__":
    main()

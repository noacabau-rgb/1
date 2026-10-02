# Edit Valorant — 9:16, 18 s, synchronisé au beat

- `audio.py` — génère la musique phonk (140 BPM) et les bruitages (tir, headshot, whoosh, impact). Tout est synthétisé : aucun droit d'auteur sur l'audio.
- `edit.py` — moteur de montage : rampes de vitesse, zoom sur chaque kick, tremblement sur chaque tir (détecté dans le son du clip), transitions « whip » avec flou de mouvement, flash + RGB split sur les kills et sur le drop, étalonnage, textes.
- `edit.json` — la timeline : chaque segment = un clip, une durée en temps (`beats`), et l'instant du kill (`kill`, en secondes dans le clip) qui sera calé pile sur un temps de la musique (`kill_beat`).

```
python3 audio.py                 # musique + sfx → audio/
python3 edit.py edit.json edit.mp4
```

Dépendances : `pip install numpy scipy opencv-python-headless pillow` + ffmpeg.

## Edit BLUE HOPE (`bluehope_edit.mp4`)

17,8 s · 1080×1920 · 60 fps · beat phonk 140 BPM synthétisé.

| Temps | Contenu |
|---|---|
| 0 – 1,7 s | Intro motion design : logo qui déploie ses ailes, reflet, « BLUE HOPE / ESPORT » lettre par lettre, sur le pré-kill de Jetax ralenti et assombri |
| 1,7 s | DROP : one tap (c4) + flash, « ONE TAP » |
| 2,6 – 12 s | Kills calés sur les temps forts (ralentis fluides par interpolation optique), multi-kills Sheriff et Vandal, clutch violet + « CLUTCH » |
| 12 – 15,4 s | La musique se coupe (tape stop) : kill final, puis écran partagé avec la cam du caster qui crie « OUI ! OUI ! » |
| 15,4 – 17,8 s | Outro : logo BLUE HOPE sur le dernier temps fort |

### Qualité d'image : upscaling IA

Les clips Twitch (720p pour 3 d'entre eux, très compressés) sont agrandis ×4 avec
**Real-ESRGAN** (`realesr-general-x4v3`, débruitage 0,5) avant le recadrage vertical.
`sr.py` lit les poids officiels `.pth` sans PyTorch, reconstruit le réseau en ONNX et
l'exécute sur CPU avec onnxruntime.

```
mkdir -p models && cd models
for f in realesr-general-x4v3.pth realesr-general-wdn-x4v3.pth; do
  curl -LO https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/$f
done
```

### Rendu

```
pip install numpy scipy opencv-python-headless pillow onnx onnxruntime
python3 bluehope_audio.py   # musique + sfx
python3 prepare_sr.py       # upscaling IA des images utilisées -> cache/sr/ (~45 min CPU, reprise possible)
python3 bluehope.py         # rendu -> bluehope_edit.mp4 (clips sources dans clips/c1..c4.mp4)
python3 bluehope.py --stills 1.0 3.5   # aperçus dans work/
```

Final (12,6 – 15,4 s) : écran partagé, la cam du caster (zone 62–432 × 0–276 px du clip c1)
arrive en haut et réagit au volume de sa voix, le gameplay passe en bas.

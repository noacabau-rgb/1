# Edit Valorant — 9:16, 18 s, synchronisé au beat

- `audio.py` — génère la musique phonk (140 BPM) et les bruitages (tir, headshot, whoosh, impact). Tout est synthétisé : aucun droit d'auteur sur l'audio.
- `edit.py` — moteur de montage : rampes de vitesse, zoom sur chaque kick, tremblement sur chaque tir (détecté dans le son du clip), transitions « whip » avec flou de mouvement, flash + RGB split sur les kills et sur le drop, étalonnage, textes.
- `edit.json` — la timeline : chaque segment = un clip, une durée en temps (`beats`), et l'instant du kill (`kill`, en secondes dans le clip) qui sera calé pile sur un temps de la musique (`kill_beat`).

```
python3 audio.py                 # musique + sfx → audio/
python3 edit.py edit.json edit.mp4
```

Dépendances : `pip install numpy scipy opencv-python-headless pillow` + ffmpeg.

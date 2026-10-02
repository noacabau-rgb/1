# Claude — Motion Reel (15 s)

Vidéo motion design de 15 secondes (1920×1080, 60 fps), entièrement générée par du code (Canvas 2D), sans aucun logiciel d'animation.

- `claude-motion-reel.mp4` — la vidéo finale
- `index.html` — l'animation (ouvrable dans un navigateur pour la voir en direct)
- `render.mjs` — rendu image par image (Chromium headless → ffmpeg), avec motion blur 4 sous-images / obturateur 180°

Re-générer : `node render.mjs` (nécessite Playwright + ffmpeg).

# Blue Hope — site web

Site one-page de l'équipe esport Valorant **Blue Hope** : aigle 3D (WebGL) en fond qui se déplace,
tourne et s'éclate en couches au fil du scroll, défilement fluide, motion design.

## Ouvrir
Double-clique sur `index.html`, ou lance un petit serveur local :
```
python3 -m http.server 8000   # puis http://localhost:8000
```
Les bibliothèques (Three.js 0.147, GSAP 3.12 + ScrollTrigger, Lenis 1.1) et les polices Google
sont chargées depuis leurs CDN : il faut une connexion internet.

## Modifier le contenu
En haut du script principal de `index.html`, l'objet `CONFIG` :
- `roster` : remplace `"À annoncer"` par les pseudos (et le rôle si besoin) ;
- `links` : remplace les `"#"` par les liens Discord, TikTok, Twitch, X, YouTube.

La vidéo des highlights est `assets/highlights.mp4` (l'edit Blue Hope en 720×1280).

## Comment c'est fait
- **Logo 3D** : le logo PNG a été vectorisé couche par couche (silhouette + 4 bleus + œil,
  `assets/logo3d.json`, intégré dans la page) puis chaque couche est extrudée en 3D avec
  `THREE.ExtrudeGeometry`, matériaux physiques vernis et reflets d'environnement.
- **Scroll** : chaque section définit une « pose » de l'aigle (position, rotation, écartement des
  couches, intensité du glow) ; GSAP ScrollTrigger interpole entre les poses, la scène lisse le tout.
- **Rendu** : bloom (UnrealBloomPass) + passe finale maison (tone mapping ACES, aberration
  chromatique, vignette, grain).
- Section « Notre jeu » épinglée en scroll horizontal, cartes roster en 3D au survol, lecteur de
  highlights avec moments cliquables, formulaire de candidature (copie le texte pour Discord),
  curseur custom, boutons magnétiques, texte « scramble » dans le menu.
- Respecte `prefers-reduced-motion` ; si WebGL est indisponible, le logo s'affiche en image.

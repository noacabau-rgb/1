# cn-web

Site de présentation pour cn-web, activité de création de sites web.

Ouvrez `index.html` dans un navigateur : tout tient dans un seul fichier (HTML, CSS et JavaScript).
Seules la police Archivo (Google Fonts) et la bibliothèque three.js (cdnjs) sont chargées depuis Internet.

## Ce que contient la page

- **En-tête 3D** (three.js) : une page web éclatée en quatre calques (navigateur, structure, contenu, interactions) qui pivote avec la souris ou au doigt.
- **Titre réactif** : les lettres s'élargissent sous le pointeur grâce à l'axe de largeur de la police variable Archivo.
- **Méthode en stop motion** : 104 images à 8 images par seconde, dessinées sur un canvas comme du papier découpé. Lecture, pause, curseur image par image et accès direct à chaque étape.
- **Configurateur de devis** : prix, délai et arborescence du site recalculés à chaque clic, puis envoyés dans le formulaire de contact.
- **Démo responsive** : une poignée à faire glisser pour passer de l'affichage téléphone à l'affichage ordinateur (container queries).
- **Maquettes en relief** : trois exemples de styles qui s'inclinent en 3D au survol.
- **Jauges Lighthouse** et seuils Core Web Vitals, FAQ, formulaire de contact, thème clair et sombre.

Le site respecte `prefers-reduced-motion` et reste lisible au clavier.

## À personnaliser avant la mise en ligne

- Les **prix** (offres et configurateur, objets `TYPES` et `OPTS` dans le script).
- L'adresse **contact@cn-web.fr**.
- Le **formulaire de contact** n'envoie rien pour l'instant. Pour le brancher, mettez `action="https://formspree.io/f/VOTRE_ID" method="POST"` sur le `<form id="c-form">` et retirez le `preventDefault()` du script, ou utilisez les formulaires Netlify.
- Les trois maquettes d'exemple sont fictives : remplacez-les par vos vraies réalisations dès que vous en avez.

## Modifier le code

La source est `src/page.html`. Après une modification, lancez `./build.sh` pour régénérer `index.html`.

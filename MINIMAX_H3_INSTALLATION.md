# MiniMax H3 : installer le modèle vidéo gratuit en local

MiniMax H3 (aussi appelé « Hailuo 3 ») est un modèle de génération vidéo **à poids ouverts** publié par MiniMax début août 2026. Il produit des clips de **4 à 15 secondes**, à **24 images/s**, **avec un son stéréo** (32 kHz) généré en même temps que l'image. Il accepte des formats du 21:9 au 9:16 et peut faire parler des personnages dans 11 langues.

Trois modes existent :

| Mode | Ce qu'il fait | Modèle utilisé |
|---|---|---|
| **Texte → vidéo (T2V)** | un prompt donne une vidéo avec son | FL2VA |
| **Image → vidéo (I2V)** | une première image (et, si on veut, une dernière) donne une vidéo avec son | FL2VA |
| **Référence → vidéo (R2V / Omni)** | jusqu'à 9 images, 3 clips vidéo et 3 clips audio servent de références | Ref2VA |

> ⚠️ Je n'ai pas pu ouvrir la page guides.0xloucash.xyz : elle est bloquée depuis mon environnement. Ce guide reprend ce que disent les sources publiques (dépôts GitHub officiels et communautaires, documentation ComfyUI, Hugging Face), listées à la fin. Les besoins en VRAM viennent de **tests de la communauté**. MiniMax n'a publié aucun chiffre officiel.

---

## 0. Avant de commencer

### 0.1 Licence (à lire avant d'installer)

Les poids sont sous la **MiniMax H3 Community License**, et non sous une licence open source classique. D'après plusieurs sources :

- La « zone d'application » de la licence **exclurait les États-Unis, l'Union européenne, le Royaume-Uni et la Corée du Sud**. Dans ces pays, un usage local demanderait une autorisation séparée de MiniMax. **Si tu es en France ou ailleurs dans l'UE, lis le texte officiel de la licence** sur la page Hugging Face `MiniMaxAI/MiniMax-H3` avant de te lancer.
- L'usage commercial serait gratuit, avec attribution, pour les structures qui font **moins de 20 M$ de chiffre d'affaires annuel**. Au-delà, il faut une autorisation écrite.
- Le module **2K (H3‑Regenerate‑2K)** et le modèle d'enrichissement de prompt (**H3‑Context‑IR**) **ne sont pas publiés**. En local, tu n'as donc pas la sortie 2K du site officiel.

### 0.2 Matériel

| Élément | Minimum réaliste | Confortable |
|---|---|---|
| **GPU** | NVIDIA (CUDA). Les poids quantifiés et les kernels sont spécifiques à CUDA | RTX 4090 / 5090 |
| **VRAM** | 8 Go (voie NF4 DiffSynth, très lent) · 12‑16 Go (GGUF Q4) | 24‑32 Go |
| **RAM système** | 32 Go | 64‑96 Go (le délestage vers la RAM est fréquent) |
| **Disque (SSD)** | ~45 Go (un seul mode, quantifié) | ~75‑100 Go (tous les modes) |
| **OS** | Windows 10/11 ou Linux | — |

Ordres de grandeur de temps de génération rapportés par la communauté :
- RTX 5090, 1080p, INT8, clip de 5 s avec SageAttention : **~8 min**
- RTX 5090, clip de 10 s : **~23 min** avec SageAttention, **~58 min** sans
- RTX 5060 Ti 16 Go, 736p, 8 s, 20 steps : **~35‑40 min**

> 💡 **Sur Mac (Apple Silicon)**, il existe un portage natif Metal : [antirez/h3.c](https://github.com/antirez/h3.c). Il n'est pas couvert ici.
>
> 💡 **Sans GPU adapté**, le hub officiel MiniMax / Hailuo offre quelques générations gratuites en ligne.

### 0.3 Quelle méthode choisir ?

| Méthode | Difficulté | Pour qui |
|---|---|---|
| **A. Pinokio + launcher MiniMax H3** | ⭐ (1 clic) | débutants avec 24‑32 Go de VRAM |
| **B. Pinokio + Maestro** | ⭐ | débutants, toutes cartes à partir de ~6‑8 Go, réglages automatiques |
| **C. ComfyUI manuel** | ⭐⭐⭐ | utilisateurs qui veulent choisir chaque fichier |

---

## 1. Installer Pinokio (méthodes A et B)

Pinokio est un « navigateur d'applications IA » qui installe tout (Python, CUDA, dépendances) sans ligne de commande.

1. Va sur **https://pinokio.computer** et télécharge la version pour ton OS.
2. **Windows** : lance l'installateur `.exe`. Si SmartScreen bloque, clique sur *Informations complémentaires → Exécuter quand même*.
   **Linux** : installe le `.deb` ou le `.AppImage` (pour l'AppImage : `chmod +x Pinokio*.AppImage && ./Pinokio*.AppImage`).
3. Au premier lancement, Pinokio demande un **dossier de travail**. Choisis un SSD avec **au moins 100 Go libres**, dans un chemin **sans espaces ni accents** (par exemple `D:\pinokio`).
4. Laisse Pinokio installer ses outils de base (Git, Conda, etc.). Cela prend quelques minutes.
5. Mets à jour le pilote NVIDIA vers une version récente (les kernels cu130 demandent un pilote compatible CUDA 13).

---

## 2. Méthode A : launcher Pinokio « MiniMax H3 » (ComfyUI préconfiguré)

Ce launcher ([ThomasEricB/minimax-h3-pinokio](https://github.com/ThomasEricB/minimax-h3-pinokio)) installe ComfyUI, PyTorch cu130, tous les poids et trois workflows prêts à l'emploi.

### 2.1 Installation

1. Dans Pinokio, clique sur **Discover**, puis **Download from URL**.
2. Colle `https://github.com/ThomasEricB/minimax-h3-pinokio` et valide.
3. Clique sur **Install**. Le launcher :
   - clone ComfyUI et installe ses dépendances, plus torch cu130 ;
   - télécharge les poids (**~63 Go**) ;
   - installe les workflows.

   Avec ComfyUI et son environnement (~10 Go), compte **~75 Go** au total.

   | Composant | Taille |
   |---|---|
   | H3‑Encoder (Qwen3‑VL‑32B, NVFP4 AWQ) | 15,7 Go |
   | H3‑VisualVAE | 5,2 Go |
   | H3‑AudioVAE | 0,6 Go |
   | H3‑Base‑FL2VA (INT8) — texte/image → vidéo | 21,0 Go |
   | H3‑Base‑Ref2VA (INT8) — référence → vidéo | 21,0 Go |

4. **Optionnel, RTX série 50 uniquement** : *Install SageAttention 3*. Cela divise environ par deux le temps de génération. Prévois 15‑25 minutes de compilation et ~4,9 Go pour le toolkit CUDA 13.

### 2.2 Lancement

1. Clique sur **Start**. Quand le serveur est prêt, le menu affiche **Open Web UI**.
2. Ouvre l'onglet **Workflows** et choisis :
   - **Text to Video (sage3)** pour du texte → vidéo + audio ;
   - **Image to Video (stock)** pour une première/dernière image → vidéo + audio ;
   - **Reference to Video (sage3)** pour des références → vidéo + audio.
3. Les modèles sont déjà sélectionnés. Écris ton prompt, puis clique sur **Queue / Run**.
4. La vidéo (avec son) apparaît dans le nœud de sortie et est enregistrée dans `ComfyUI/output/`.

> Si ta carte n'est pas une RTX 50, mets le nœud **Patch Sage Attention KJ** sur `disabled` dans les workflows « sage3 ».

### 2.3 Menu utile

- **Download Models** télécharge un modèle manquant.
- **Manage Disk Space** supprime un des deux transformers (21 Go chacun) si tu n'utilises qu'un mode.
- **Update** met à jour ComfyUI et ses dépendances.
- **Reset** supprime ComfyUI sans toucher aux poids.
- **Reinstall Workflows** restaure les trois workflows d'origine.

---

## 3. Méthode B : Pinokio + Maestro (le plus simple sur petite carte)

[Maestro](https://github.com/Blizaine/Maestro) est un studio vidéo/image/musique 100 % local, construit sur WanGP, qui intègre MiniMax H3. Il ajuste lui‑même les réglages selon ta VRAM et ta RAM.

Configuration indiquée : GPU NVIDIA avec **6 Go de VRAM minimum** (24 Go+ recommandés) et **16 Go de RAM**. Les modèles (50‑100 Go selon ce que tu utilises) se téléchargent **à la première utilisation**.

1. Dans Pinokio, ouvre **Discover** et cherche **Maestro**, ou utilise *Download from URL* avec `https://github.com/Blizaine/Maestro`.
2. Clique sur **Download**, puis **Install**. Le launcher crée un environnement Python adapté à ta carte (par exemple PyTorch 2.10 + CUDA 13 pour les RTX 50).
3. Clique sur **Start**, puis ouvre l'interface web.
4. Au premier lancement, **Performance Auto‑Tune** choisit un profil selon ta VRAM et ta RAM. Tu peux le modifier dans *Settings → Show advanced settings*.
5. Va dans **Studio → Video** et choisis un workflow H3 :
   - **First & Last** : texte ou image(s) → vidéo ;
   - **Omni** : références → vidéo.
6. Choisis la variante de modèle :
   - **Pruned 20B** (recommandé) ou **Full 33B** ;
   - la quantification qui correspond à ta VRAM : NVFP4‑AWQ, GGUF Q2/Q4, INT8 ou BF16.
7. Optionnel : ouvre le panneau **H3 Optimizations** (Turbo LoRA, Sol Engine sur RTX 40/50, First Block Cache).
8. Écris ton prompt et lance la génération. Le premier lancement télécharge les poids nécessaires.

Pas besoin de compte Hugging Face. L'action **Connect Hugging Face (Optional)** sert seulement à lever des limites de téléchargement.

**En cas de saturation de la VRAM (OOM)** : Maestro affiche une bannière qui propose de baisser la marge VRAM en un clic. Tu peux aussi réduire la résolution ou la durée.

---

## 4. Méthode C : installation manuelle dans ComfyUI

### 4.1 Installer ou mettre à jour ComfyUI

H3 est pris en charge **nativement** par les versions récentes de ComfyUI (≥ 0.30.0 selon les guides, 0.31.0 pour certains packs de nœuds).

- **Windows (portable)** : télécharge la dernière version portable sur https://github.com/comfyanonymous/ComfyUI/releases, décompresse‑la, puis lance `run_nvidia_gpu.bat`. Si tu l'avais déjà, lance `update/update_comfyui.bat`.
- **Linux** :

  ```bash
  git clone https://github.com/comfyanonymous/ComfyUI.git
  cd ComfyUI
  python3 -m venv venv && source venv/bin/activate
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
  pip install -r requirements.txt
  python main.py
  ```

  Pour une installation existante : `git pull && pip install -r requirements.txt`.

Ouvre ensuite **http://127.0.0.1:8188**.

### 4.2 Télécharger les modèles

Dépôt Hugging Face : **https://huggingface.co/Comfy-Org/MiniMax-H3**

Télécharge **un** fichier par catégorie, selon ta VRAM, et place‑le dans le bon dossier :

**① Modèle de diffusion → `ComfyUI/models/diffusion_models/`**

| Fichier | Taille | Usage |
|---|---|---|
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 19,5 Go | ✅ conseillé pour T2V/I2V (24 Go de VRAM) |
| `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` | 19,5 Go | alternative FP8 |
| `minimax_h3_fl2va_pruned_bf16.safetensors` | 37,5 Go | qualité max, élagué |
| `minimax_h3_fl2va_bf16.safetensors` | 61,7 Go | complet, cartes 80 Go |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 19,5 Go | ✅ pour le mode Référence → vidéo |

(Les versions « ref2va » existent dans les mêmes déclinaisons que les « fl2va ».)

**② Encodeur de texte → `ComfyUI/models/text_encoders/`**

| Fichier | Taille |
|---|---|
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 14,6 Go ✅ conseillé |
| `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` | 25,3 Go |
| `qwen3vl_32b_minimax_h3_bf16.safetensors` | 48 Go |

**③ VAE → `ComfyUI/models/vae/`**

| Fichier | Taille |
|---|---|
| `minimax_h3_video_vae_fp16.safetensors` | 4,85 Go (obligatoire) |
| `minimax_h3_audio_vae_fp32.safetensors` | 577 Mo (obligatoire) |

Arborescence finale :

```
ComfyUI/
└── models/
    ├── diffusion_models/
    │   └── minimax_h3_fl2va_pruned_int8_convrot.safetensors
    ├── text_encoders/
    │   └── qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
    └── vae/
        ├── minimax_h3_video_vae_fp16.safetensors
        └── minimax_h3_audio_vae_fp32.safetensors
```

Téléchargement en ligne de commande (optionnel) :

```bash
pip install -U "huggingface_hub[cli]"
cd ComfyUI/models
huggingface-cli download Comfy-Org/MiniMax-H3 --include "*fl2va_pruned_int8_convrot*" --local-dir ./_h3
huggingface-cli download Comfy-Org/MiniMax-H3 --include "*nvfp4_awq*" --local-dir ./_h3
huggingface-cli download Comfy-Org/MiniMax-H3 --include "*vae*" --local-dir ./_h3
# puis déplace chaque fichier de ./_h3/<sous-dossier>/ vers diffusion_models/, text_encoders/ et vae/
```

> Vérifie les noms exacts sur la page Hugging Face : le dépôt peut évoluer.

### 4.3 Cartes 12‑16 Go : versions GGUF

1. Installe le nœud **ComfyUI‑GGUF** : *Manager → Custom Nodes Manager → « ComfyUI-GGUF » → Install*, puis redémarre.
2. Télécharge un modèle de diffusion élagué en **Q4_K_M** (~10,6 Go) et un encodeur de texte en **Q2_K** (~7,9 Go) depuis un dépôt GGUF communautaire, par exemple :
   - `unsloth/MiniMax-H3-GGUF`
   - `Abiray/MiniMax-H3-Pruned-GGUF`
   - `vantagewithai/MiniMax-H3-comfyUI-GGUF`
3. Place le `.gguf` du modèle de diffusion dans `models/unet/` (ou `models/diffusion_models/`) et l'encodeur dans `models/text_encoders/`.
4. Dans le workflow, remplace le nœud *Load Diffusion Model* par **Unet Loader (GGUF)**, et le chargeur d'encodeur par sa version GGUF.
5. Sur 12‑16 Go, on peut aussi utiliser la VAE vidéo `fp8mix` (~2,6 Go) avec la VAE audio bf16 (~289 Mo). Ces fichiers sont dans les dépôts communautaires.

> Les fichiers GGUF sont des conversions **non officielles**. La qualité baisse à mesure que la quantification descend (Q2 < Q4 < Q5 < Q8).

### 4.4 Charger un workflow

1. Dans ComfyUI : **Workflow → Browse Templates → Video**, puis choisis **MiniMax H3** (Text to Video, Image to Video ou Reference to Video).
2. Vérifie que chaque nœud de chargement pointe vers les fichiers que tu as téléchargés.
3. Écris ton prompt, puis **Run**.

---

## 5. Réglages et prompts

- **Résolution** : 1344×768 (16:9) par défaut. 1080p est possible mais demande beaucoup plus de VRAM et de RAM. Commence en 768p.
- **Durée** : 4 à 15 s. Commence par **5 s** pour tester.
- **Steps** : **15** suffisent généralement. À 10, l'audio se dégrade nettement. 20 donne la qualité maximale.
- **Prompt** : le site officiel enrichit les prompts avec un modèle fermé. En local, écris un prompt **structuré et détaillé** : sujet, action, décor, lumière, mouvement de caméra, ambiance sonore.
- **Dialogues** : utilise les balises `<d>`, par exemple :
  `Une femme regarde la caméra et dit <d>[French] Bonjour, bienvenue dans ma cuisine.</d>`
- **Mode Référence** : jusqu'à 9 images, 3 vidéos et 3 audios (12 fichiers maximum, 15 s cumulées). L'audio seul ne suffit pas.

---

## 6. Dépannage

| Problème | Solution |
|---|---|
| **Out of memory / CUDA OOM** | baisse la résolution ou la durée, passe à un modèle plus quantifié (INT8 → GGUF Q4), ferme les autres applis qui utilisent le GPU, lance ComfyUI avec `--lowvram` |
| **Génération extrêmement lente** | normal si la VRAM déborde vers la RAM. Ajoute de la RAM, réduis la résolution, active SageAttention (RTX 50) |
| **Interface vide dans Pinokio** (mais OK dans un navigateur) | installe Caddy : `conda install -y -n base -c conda-forge caddy`, puis redémarre Pinokio |
| **Nœuds rouges / manquants** | mets ComfyUI à jour, puis *Manager → Install Missing Custom Nodes* |
| **Modèle introuvable dans la liste** | fichier dans le mauvais dossier. Vérifie la section 4.2, puis appuie sur `R` dans ComfyUI pour rafraîchir |
| **Téléchargement interrompu** | relance-le : Hugging Face reprend là où il s'était arrêté |
| **Vérifier que ComfyUI tourne** | ouvre `http://127.0.0.1:8188` |

---

## Sources

- [ThomasEricB/minimax-h3-pinokio (launcher Pinokio 1 clic)](https://github.com/ThomasEricB/minimax-h3-pinokio)
- [Blizaine/Maestro](https://github.com/Blizaine/Maestro) · [Maestro sur Pinokio](https://pinokio.co/apps/github-com-blizaine-maestro)
- [MiniMax-AI/awesome-minimax-h3-integration](https://github.com/MiniMax-AI/awesome-minimax-h3-integration)
- [Comfy-Org/MiniMax-H3 (Hugging Face)](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/README.md)
- [Tutoriel officiel ComfyUI MiniMax H3](https://docs.comfy.org/tutorials/video/minimax/minimax-h3-native)
- [ComfyUI Wiki : workflows T2V, I2V et R2V](https://comfyui-wiki.com/en/tutorial/advanced/video/minimax/minimax-h3)
- [Tuto Maestro Pinokio (paradoxetemporel.fr)](https://paradoxetemporel.fr/71174-tuto-maestro-pinokio-generer-des-videos-minimax-h3-en-local.html)
- [Guide VRAM MindStudio](https://www.mindstudio.ai/blog/minimax-h3-run-locally-guide) · [Guide matériel Kingy](https://kingy.ai/ai/ai-guides/minimax-h3-local-installation-hardware-guide/)
- [Licence et matériel (runaihome)](https://runaihome.com/blog/minimax-h3-open-weights-local-ai-hardware-guide-2026/)
- [Abiray/MiniMax-H3-Pruned-GGUF](https://huggingface.co/Abiray/MiniMax-H3-Pruned-GGUF)

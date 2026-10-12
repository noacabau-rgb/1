# MiniMax H3 : le modèle vidéo gratuit

**Il génère en une seule fois la vidéo, la voix, le lip-sync et la musique.**

MiniMax H3 est un modèle chinois de génération vidéo, gratuit et téléchargeable. En une seule génération, il produit la vidéo, une voix réaliste, un lip-sync synchronisé avec cette voix et une musique adaptée à la scène. Les clips durent de **4 à 15 secondes**, à **24 images/s**, avec un **son stéréo en 32 kHz**. Formats disponibles : 21:9, 16:9, 4:3, 1:1, 3:4 et 9:16.

> Ce guide suit le guide « MiniMax H3 – le modèle vidéo gratuit » de guides.0xloucash.xyz. J'y ai ajouté les commandes et précisions techniques des dépôts officiels (MiniMax-AI, Comfy-Org) et de Wan2GP. Les sources sont listées à la fin.

---

## ⚠️ À lire en premier : restriction territoriale

**La licence de MiniMax H3 (MiniMax H3 Community License) exclut l'installation locale en France, dans l'UE, au Royaume-Uni, en Corée du Sud et aux États-Unis.**

| Tu es… | Ce que tu peux faire |
|---|---|
| 🇫🇷 en France / UE / UK / Corée / US | ➜ **ÉTAPE 3** : espaces Hugging Face en ligne, ou API hébergée par MiniMax. 100 % légal. |
| 🌍 ailleurs | ➜ ÉTAPES 1, 2 ou 3, selon ta machine |

Un VPN contourne techniquement la restriction, mais **c'est une violation de licence**, sous ta seule responsabilité. C'est fortement déconseillé pour un usage commercial.

**Usage commercial** : il est autorisé, sauf pour les entreprises qui font **plus de 20 M$ de chiffre d'affaires par an**. Celles-ci ont besoin d'une autorisation écrite de MiniMax.

---

## 🧠 « Open-weight », pas « open-source »

On lit souvent que MiniMax H3 est « open source ». C'est faux : il est **open-weight** (poids ouverts).

| | Public | Fermé |
|---|---|---|
| **Poids du modèle** | ✅ H3-Base, checkpoints **FL2VA** et **Ref2VA** | — |
| **Code d'inférence** | ✅ SGLang, vLLM, Diffusers, ComfyUI | — |
| **Préprocessing des prompts** | — | ❌ *Context-IR*, hébergé chez MiniMax |
| **Upscaling 2K** | — | ❌ *Regenerate-2K*, hébergé uniquement |
| **Entraînement** | — | ❌ ni données ni recette |
| **Fine-tuning** | — | ❌ aucun workflow LoRA ou fine-tuning officiel |

Concrètement :
- Tu peux **inspecter et faire tourner** le modèle, là où la licence l'autorise.
- Tu **ne peux pas** voir comment il a été entraîné, ni le ré-entraîner.
- **Le 2K n'est pas dans les poids.** En local, tu es limité par défaut à **768 pixels de côté court** (c'est bien du « 768p », pas du 720p).
- Comme Context-IR est fermé, ton prompt n'est pas enrichi en local. Écris des prompts **détaillés et structurés** (voir la section « Bien écrire ses prompts »).

> En résumé : tu as le plat (les poids), mais pas la recette.

---

## 📋 La fiche

| | |
|---|---|
| **Repo officiel** | [github.com/MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) (~7 900 ⭐) |
| **Poids officiels** | [huggingface.co/MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) (5 M+ téléchargements) |
| **Licence** | Community License : usage local exclu dans l'UE, au UK, en Corée et aux US |
| **Statut** | Open-weight, pas open-source |
| **Résolution locale** | 768p (côté court) par défaut |
| **Résolution 2K** | via Regenerate-2K, hébergé uniquement |
| **Sortie** | vidéo + voix + lip-sync + musique, en une seule génération |
| **Usage commercial** | autorisé, sauf entreprises > 20 M$/an (autorisation écrite) |

**Les deux checkpoints :**
- **FL2VA** (*First/Last frame to Video+Audio*) : texte → vidéo, ou image de début et/ou de fin → vidéo.
- **Ref2VA** (*Reference to Video+Audio*) : jusqu'à 9 images, 3 vidéos et 3 audios de référence (12 fichiers maximum, 15 s cumulées).

---

## 🛡️ Méfie-toi des faux « installeurs » MiniMax H3

En cherchant H3, tu croiseras des **repos GitHub tout neufs** (quelques semaines, peu d'étoiles) qui proposent un **`.exe` Windows ou un `.dmg` macOS « prêt à l'emploi »**. **C'est un signal d'alarme.** Un vrai modèle d'IA se distribue sous forme de **poids et de code d'inférence**, jamais comme une application à double-cliquer. Ce format est une technique classique pour piéger les gens qui cherchent des outils d'IA « gratuits ».

**Pour vérifier qu'un repo est officiel (valable pour n'importe quel modèle) :**
1. Regarde le **nom de l'organisation GitHub**, pas seulement le nom du repo. Ici, ce doit être **`MiniMax-AI`**.
2. Compare avec le lien donné sur la **page Hugging Face officielle** (`MiniMaxAI/MiniMax-H3`), qui pointe vers le vrai code.
3. Méfie-toi d'une **organisation récente**, avec **un seul repo** et **peu d'étoiles**.

---

## 🪜 ÉTAPE 1 : installation locale officielle (hors UE/UK/Corée/US uniquement)

> **Rappel : si tu es en France, passe directement à l'ÉTAPE 3.**

L'installation officielle vise surtout des **serveurs multi-GPU** : les exemples officiels utilisent 4 GPU. Les poids d'origine pèsent environ **460 Go**, car chaque transformer fait ~62 Go en BF16. Sur un PC perso, préfère l'**ÉTAPE 2** (Wan2GP) ou ComfyUI (voir l'encadré plus bas).

### 1.1 Récupérer le code

```bash
git clone https://github.com/MiniMax-AI/MiniMax-H3.git
cd MiniMax-H3
```

Suis ensuite le README pour les dépendances Python et l'environnement : Python, PyTorch avec CUDA, et SGLang ou vLLM selon le moteur choisi.

### 1.2 Télécharger les poids depuis Hugging Face

```bash
pip install -U "huggingface_hub[cli]"

# Les deux familles (FL2VA + Ref2VA)
hf download MiniMaxAI/MiniMax-H3 --include "model_index.json" "FL2VA/*" "Ref2VA/*" --local-dir MiniMax-H3

# Ou une seule famille, par exemple texte/image → vidéo
hf download MiniMaxAI/MiniMax-H3 --include "model_index.json" "FL2VA/*" --local-dir MiniMax-H3
```

### 1.3 Lancer le serveur d'inférence (SGLang)

**FL2VA** (texte, image de début et/ou de fin) :

```bash
sglang serve \
  --model-path MiniMaxAI/MiniMax-H3 \
  --num-gpus 4 \
  --ulysses-degree 4 \
  --performance-mode speed \
  --host 0.0.0.0 \
  --port 30010 \
  --model-variant fl2va
```

**Ref2VA** (références multimodales) : même commande avec `--port 30011 --model-variant ref2va`.

Des exemples de requêtes se trouvent dans `scripts/readme/` du repo.

**Diffusers** : `ModularPipeline.from_pretrained("MiniMaxAI/MiniMax-H3")`.

**Optionnel**, une « skill » officielle d'aide à l'écriture de prompts :

```bash
npx skills add https://github.com/MiniMax-AI/MiniMax-H3 --skill h3-prompt-writing
```

> 💡 **Alternative ComfyUI (une seule carte graphique)** : Comfy-Org publie des versions reconditionnées et quantifiées sur [huggingface.co/Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3). Pour 24 Go de VRAM, une combinaison qui fonctionne bien :
> - `models/diffusion_models/` → `minimax_h3_fl2va_pruned_int8_convrot.safetensors` (19,5 Go)
> - `models/text_encoders/` → `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (14,6 Go)
> - `models/vae/` → `minimax_h3_video_vae_fp16.safetensors` (4,85 Go) et `minimax_h3_audio_vae_fp32.safetensors` (577 Mo)
>
> Ensuite, mets ComfyUI à jour et ouvre *Workflow → Browse Templates → Video → MiniMax H3*.

---

## 🪜 ÉTAPE 2 : la version légère pour les machines moins puissantes (Wan2GP)

> Même restriction territoriale qu'à l'ÉTAPE 1 : c'est aussi une installation locale.

**Wan2GP** est une interface optimisée pour les machines « GPU poor ». Elle prend en charge MiniMax H3.
👉 **[pinokio.co/apps/github-com-6morpheus6-wan2gp](https://pinokio.co/apps/github-com-6morpheus6-wan2gp)** (code source : [github.com/deepbeepmeep/Wan2GP](https://github.com/deepbeepmeep/Wan2GP))

Ce n'est **pas** une version « distillée » de H3 : aucun checkpoint distillé n'existe à ce jour. Wan2GP utilise des **formats quantifiés** (int8, fp8, gguf, NV FP4, Nunchaku) qui réduisent fortement la mémoire nécessaire :

| Vidéo | VRAM nécessaire |
|---|---|
| 5 secondes (124 images) | **5-6 Go** |
| 15 secondes en 832×480 | **8-9 Go** |

**Matériel compatible** : GPU NVIDIA de la GTX 10xx à la RTX 50xx, ou AMD RDNA 2 à 4 (script `wan2gp-amd`). Windows ou Linux.

### 2.1 Installation via Pinokio (recommandée, en un clic)

1. Télécharge et installe **Pinokio** depuis **[pinokio.computer](https://pinokio.computer)**.
2. Au premier lancement, choisis un dossier de travail sur un **SSD avec beaucoup de place libre** (compte plusieurs dizaines de Go), dans un chemin **sans espaces ni accents**, par exemple `D:\pinokio`.
3. Ouvre **[pinokio.co/apps/github-com-6morpheus6-wan2gp](https://pinokio.co/apps/github-com-6morpheus6-wan2gp)** (ou cherche « Wan2GP » dans l'onglet **Discover** de Pinokio), puis clique sur **Download**.
4. Clique sur **Install**. Pinokio installe Python, PyTorch, Triton et toutes les dépendances.
5. Clique sur **Start**, puis ouvre l'interface web.
6. Dans la liste des modèles vidéo, choisis **MiniMax H3**, en version **pruned 20B** (plus légère) ou **33B**, et en mode **FL2VA** ou **Ref2VA**.
7. Écris ton prompt et lance la génération. Le premier lancement télécharge les poids, ce qui prend du temps.

### 2.2 Installation manuelle (alternative)

```bash
git clone https://github.com/deepbeepmeep/Wan2GP.git
cd Wan2GP
conda create -n wan2gp python=3.11.14 -y
conda activate wan2gp
pip install torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
# Windows uniquement (RTX 30xx–50xx) :
python -m pip install -U "triton-windows>=3.6,<3.7"
python wgp.py
```

Des scripts tout prêts existent aussi : `scripts\install.bat` puis `scripts\run.bat` sous Windows, ou `scripts/install.sh` puis `scripts/run.sh` sous Linux.

### 2.3 Astuces pour économiser la VRAM dans Wan2GP

- **Profile 4** : jusqu'à 50 % de VRAM en moins sur les longues vidéos.
- **Attention Head Split → Medium** : environ 20 % de VRAM en moins, au prix d'environ 10 % de vitesse.
- **SageAttention** : accélère sur les RTX 30xx et plus récentes.
- **VAE INT8 ConvRot** : deux fois plus rapide, téléchargé automatiquement quand tu choisis INT8.

---

## 🪜 ÉTAPE 3 : tester en ligne, sans rien installer (accessible partout, y compris en France)

**C'est la voie recommandée en UE, au UK, en Corée et aux US.** Aucune question de licence : tout tourne sur les serveurs de Hugging Face, pas sur ta machine.

Deux espaces sont disponibles :
- 👉 **[huggingface.co/spaces/multimodalart/minimax-h3](https://huggingface.co/spaces/multimodalart/minimax-h3)** (version standard)
- 👉 **[huggingface.co/spaces/mrfakename/minimax-h3-ultra-fast](https://huggingface.co/spaces/mrfakename/minimax-h3-ultra-fast)** (optimisée pour la vitesse)

**Mode d'emploi :**
1. Ouvre l'espace dans ton navigateur. Un ordinateur, un Mac ou un téléphone font l'affaire.
2. *(Conseillé)* Connecte-toi à un compte Hugging Face gratuit : le quota GPU est plus élevé qu'en anonyme.
3. Donne un **texte**, une **image** ou une **vidéo de référence**, selon ce que propose l'interface.
4. Lance la génération. Il peut y avoir une file d'attente si l'espace est très utilisé.
5. Télécharge ta vidéo, avec l'audio synchronisé.

L'autre option légale partout est l'**API hébergée par MiniMax**, payante ou à crédits. C'est aussi la seule façon d'obtenir la **2K**, via Regenerate-2K.

---

## ✍️ Bien écrire ses prompts

- Décris dans l'ordre : **sujet → action → décor → lumière → mouvement de caméra → ambiance sonore/musique**.
- **Dialogues avec lip-sync** : utilise les balises `<d>`, par exemple :
  `Une femme sourit face caméra dans une cuisine lumineuse et dit <d>[French] Bonjour, bienvenue chez moi !</d> Musique acoustique douce en fond.`
- Commence par des clips de **5 s** pour tester, puis allonge jusqu'à 15 s.

---

## 🎬 Ce qui rend ce modèle différent

Le vrai argument n'est pas la gratuité : Seedance et Kling ont aussi des offres gratuites. C'est que **H3 génère tout en une seule passe** :
- la **vidéo**, à partir d'un texte, d'une image ou d'une référence ;
- une **voix réaliste** ;
- le **lip-sync** synchronisé avec cette voix ;
- une **musique** qui colle à l'ambiance de la scène.

D'habitude, il faut générer la vidéo, synthétiser la voix ailleurs, chercher une musique et tout recaler au montage. H3 sort le tout assemblé.

---

## ❓ FAQ express

**C'est vraiment gratuit ?**
Oui, pour l'usage personnel et la plupart des usages commerciaux. Seules les entreprises qui font plus de 20 M$ par an ont besoin d'une autorisation écrite.

**Je suis en France, je peux l'installer en local ?**
Non, la licence l'exclut explicitement. Utilise les espaces Hugging Face (ÉTAPE 3) ou l'API hébergée.

**Un VPN pour contourner, ça marche ?**
Techniquement oui, légalement non : c'est une violation de licence, sous ta seule responsabilité. À éviter absolument pour du commercial.

**C'est open source ?**
Non, c'est open-weight. Les poids et le code d'inférence sont publics. Le préprocessing (Context-IR), l'upscaling 2K (Regenerate-2K) et l'entraînement restent fermés.

**Quelle résolution en local ?**
768p par défaut (côté court). La 2K passe uniquement par le module hébergé.

**J'ai une petite carte graphique, c'est jouable ?**
Oui, avec Wan2GP : 5-6 Go de VRAM pour 5 secondes, 8-9 Go pour 15 secondes en 832×480.

**Ça marche sur Mac ?**
Selon le guide d'origine, le repo officiel propose un installeur pour Apple Silicon. Je ne l'ai pas trouvé dans la partie du README que j'ai pu consulter. Il existe aussi un portage communautaire natif Metal : [antirez/h3.c](https://github.com/antirez/h3.c). Les espaces Hugging Face, eux, fonctionnent sur n'importe quel appareil avec un navigateur.

---

## 🔗 Tous les liens

- Repo officiel : [github.com/MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)
- Poids officiels : [huggingface.co/MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3)
- Espace HF (standard) : [huggingface.co/spaces/multimodalart/minimax-h3](https://huggingface.co/spaces/multimodalart/minimax-h3)
- Espace HF (ultra rapide) : [huggingface.co/spaces/mrfakename/minimax-h3-ultra-fast](https://huggingface.co/spaces/mrfakename/minimax-h3-ultra-fast)
- Wan2GP (version légère) : [pinokio.co/apps/github-com-6morpheus6-wan2gp](https://pinokio.co/apps/github-com-6morpheus6-wan2gp) · [code source](https://github.com/deepbeepmeep/Wan2GP)
- Pinokio : [pinokio.computer](https://pinokio.computer)
- Poids reconditionnés pour ComfyUI : [huggingface.co/Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
- Liste officielle des intégrations : [github.com/MiniMax-AI/awesome-minimax-h3-integration](https://github.com/MiniMax-AI/awesome-minimax-h3-integration)
- Guide d'origine : [guides.0xloucash.xyz – MiniMax H3](https://guides.0xloucash.xyz/Cr%C3%A9ation+de+Contenu/Guides+DM/MiniMax+H3+-+le+modele+video+gratuit)

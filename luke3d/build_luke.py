"""Génère un modèle 3D stylisé de Luke (tenue de Tatooine) à partir de primitives.

Sorties : luke.glb (couleurs), luke.obj, luke.stl (impression 3D).
Unités : mètres, Y vers le haut, le personnage regarde vers +Z.
"""
import numpy as np
import trimesh
from trimesh.creation import cylinder, icosphere, box, revolve

SKIN = [232, 190, 160, 255]
HAIR = [120, 85, 50, 255]
TUNIC = [236, 228, 210, 255]
PANTS = [215, 205, 180, 255]
BOOT = [205, 192, 170, 255]
BOOT_BAND = [180, 165, 140, 255]
SOLE = [70, 60, 50, 255]
LEATHER = [110, 70, 40, 255]
SILVER = [200, 200, 205, 255]
BLACK = [30, 30, 30, 255]
EYE = [40, 30, 25, 255]
TEETH = [250, 250, 245, 255]

parts = []


def add(mesh, color, name):
    mesh.visual.face_colors = color
    mesh.metadata["name"] = name
    parts.append((name, mesh))
    return mesh


def tube(p1, p2, r, sections=24):
    return cylinder(radius=r, segment=[p1, p2], sections=sections)


def ball(c, r, scale=(1, 1, 1), sub=3):
    s = icosphere(subdivisions=sub, radius=r)
    s.apply_scale(scale)
    s.apply_translation(c)
    return s


def limb(p1, p2, r1, r2=None, sections=24):
    """Tronc de cône arrondi entre deux points (articulations sphériques)."""
    r2 = r1 if r2 is None else r2
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    h = np.linalg.norm(p2 - p1)
    prof = [[0, 0], [r1, 0], [r2, h], [0, h]]
    m = revolve(prof, sections=sections)  # axe Z
    z = np.array([0, 0, 1.0])
    d = (p2 - p1) / h
    m.apply_transform(trimesh.geometry.align_vectors(z, d))
    m.apply_translation(p1)
    return trimesh.util.concatenate([m, ball(p1, r1, sub=2), ball(p2, r2, sub=2)])


def lathe(profile, depth=0.75, y0=0.0, sections=48):
    """Révolution autour de Y d'un profil [(rayon, y)], aplatie en profondeur."""
    m = revolve([[r, y] for r, y in profile], sections=sections)  # axe Z
    m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    m.apply_scale([1, 1, depth])
    m.apply_translation([0, y0, 0])
    return m


# --- Bottes -------------------------------------------------------------
for sx, side in ((1, "G"), (-1, "D")):
    x = 0.17 * sx
    add(limb([x, 0.08, 0], [x, 0.50, 0.0], 0.068, 0.072), BOOT, f"botte_{side}")
    for i, y in enumerate(np.arange(0.18, 0.49, 0.035)):
        add(tube([x, y, 0], [x, y + 0.012, 0], 0.075 + 0.002 * (i % 2)), BOOT_BAND, f"bande_{side}_{i}")
    foot = box(extents=[0.11, 0.09, 0.24])
    foot.apply_translation([x, 0.05, 0.05])
    add(foot, BOOT, f"pied_{side}")
    toe = ball([x, 0.045, 0.16], 0.055, scale=(1, 0.8, 1))
    add(toe, BOOT, f"pointe_{side}")
    sole = box(extents=[0.12, 0.02, 0.27])
    sole.apply_translation([x, 0.01, 0.06])
    add(sole, SOLE, f"semelle_{side}")

    # --- Jambes (pantalon) ---------------------------------------------
    add(limb([x * 0.95, 0.50, 0], [x * 0.6, 0.97, 0], 0.075, 0.095), PANTS, f"jambe_{side}")

# --- Tunique -------------------------------------------------------------
tunic = lathe([(0.0, 0.0), (0.27, 0.0), (0.25, 0.12), (0.21, 0.30),
               (0.21, 0.45), (0.23, 0.58), (0.20, 0.64), (0.07, 0.68), (0.0, 0.68)],
              depth=0.62, y0=0.80)
add(tunic, TUNIC, "tunique")
# Col en V : peau visible sur la poitrine
v = ball([0, 1.40, 0.10], 0.06, scale=(0.8, 1.6, 0.4))
add(v, SKIN, "poitrine")

# --- Ceinture -------------------------------------------------------------
belt = lathe([(0.0, 0.0), (0.225, 0.0), (0.225, 0.06), (0.0, 0.06)], depth=0.66, y0=0.97)
add(belt, LEATHER, "ceinture")
buckle = box(extents=[0.11, 0.07, 0.02])
buckle.apply_translation([0.02, 1.0, 0.152])
add(buckle, SILVER, "boucle")

# Étui + blaster (côté droit du personnage)
holster = box(extents=[0.07, 0.12, 0.05])
holster.apply_translation([-0.17, 0.95, 0.12])
add(holster, LEATHER, "etui")
add(tube([-0.21, 0.93, 0.15], [-0.25, 0.87, 0.20], 0.025), BLACK, "blaster_corps")
add(tube([-0.205, 0.94, 0.145], [-0.215, 0.925, 0.155], 0.03), SILVER, "blaster_bout")

# Sabre laser accroché à gauche
sx_, sz_ = 0.205, 0.11
add(tube([sx_, 0.99, sz_], [sx_, 0.95, sz_], 0.008), SILVER, "sabre_crochet")
add(tube([sx_, 0.95, sz_], [sx_, 0.90, sz_], 0.019), SILVER, "sabre_emetteur")
add(tube([sx_, 0.90, sz_], [sx_, 0.82, sz_], 0.017), BLACK, "sabre_poignee")
add(tube([sx_, 0.82, sz_], [sx_, 0.73, sz_], 0.017), SILVER, "sabre_pommeau")
for i, y in enumerate((0.89, 0.865, 0.84)):
    add(tube([sx_, y, sz_], [sx_, y - 0.008, sz_], 0.019), SILVER, f"sabre_bague_{i}")

# --- Bras croisés ------------------------------------------------------------
shoulder = {1: [0.21, 1.40, 0.0], -1: [-0.21, 1.40, 0.0]}
elbow = {1: [0.25, 1.18, 0.07], -1: [-0.25, 1.18, 0.07]}
# Avant-bras qui se croisent devant la poitrine
wrist = {1: [-0.13, 1.25, 0.17], -1: [0.13, 1.21, 0.19]}
for s, side in ((1, "G"), (-1, "D")):
    add(limb(shoulder[s], elbow[s], 0.07, 0.075), TUNIC, f"bras_{side}")
    add(limb(elbow[s], wrist[s], 0.075, 0.068), TUNIC, f"avantbras_{side}")
    w = np.array(wrist[s])
    hand = ball(w + [-0.04 * s, 0.0, -0.03], 0.04, scale=(1.1, 0.8, 0.9))
    add(hand, SKIN, f"main_{side}")

# --- Cou et tête -------------------------------------------------------------
add(limb([0, 1.44, 0], [0, 1.52, 0], 0.045), SKIN, "cou")
head_c = np.array([0, 1.62, 0.01])
add(ball(head_c, 0.1, scale=(0.82, 1.0, 0.92), sub=4), SKIN, "tete")
add(ball(head_c + [0, -0.07, 0.035], 0.055, scale=(1.0, 0.7, 0.9)), SKIN, "menton")
add(ball(head_c + [0, 0.0, 0.09], 0.02, scale=(0.7, 1.0, 0.9)), SKIN, "nez")
for s in (1, -1):
    add(ball(head_c + [0.034 * s, 0.022, 0.078], 0.012), EYE, f"oeil_{s}")
    add(ball(head_c + [0.085 * s, 0.0, 0.0], 0.022, scale=(0.5, 1, 0.8)), SKIN, f"oreille_{s}")
smile = ball(head_c + [0, -0.045, 0.075], 0.032, scale=(1.2, 0.35, 0.5))
add(smile, TEETH, "sourire")
# Cheveux : calotte + mèche
hair = ball(head_c + [0, 0.03, -0.012], 0.108, scale=(0.88, 0.9, 0.96), sub=4)
keep = hair.vertices[hair.faces].mean(axis=1)
mask = (keep[:, 1] > head_c[1] + 0.02) | ((keep[:, 2] < head_c[2] - 0.02) & (keep[:, 1] > head_c[1] - 0.08))
hair.update_faces(mask)
hair.remove_unreferenced_vertices()
add(hair, HAIR, "cheveux")
add(ball(head_c + [-0.02, 0.085, 0.05], 0.05, scale=(1.3, 0.5, 0.8)), HAIR, "meche")

# --- Export ------------------------------------------------------------------
scene = trimesh.Scene()
for name, m in parts:
    scene.add_geometry(m, geom_name=name, node_name=name)
scene.export("luke.glb")
merged = trimesh.util.concatenate([m for _, m in parts])
merged.export("luke.obj")
merged.export("luke.stl")
print("parties:", len(parts), "triangles:", len(merged.faces),
      "hauteur: %.2f m" % merged.extents[1])

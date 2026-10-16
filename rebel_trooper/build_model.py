"""Génère un modèle 3D stylisé (low-poly) d'un soldat rebelle (Rebel fleet trooper).

Sortie : rebel_trooper.glb (couleurs, à privilégier), rebel_trooper.obj/.mtl, rebel_trooper.stl (impression 3D).
Usage : python3 build_model.py
"""
import os

import numpy as np
import trimesh
from trimesh.creation import box, capsule, cylinder, icosphere, torus
from trimesh.geometry import align_vectors

OUT = os.path.dirname(os.path.abspath(__file__))

COLORS = {
    "skin": (232, 190, 160),
    "shirt": (128, 168, 222),
    "vest": (30, 28, 30),
    "pants": (176, 176, 172),
    "boots": (18, 18, 20),
    "belt": (120, 50, 30),
    "holster": (176, 92, 42),
    "helmet": (238, 240, 242),
    "visor": (25, 30, 38),
    "strap": (20, 20, 20),
    "gun": (22, 22, 24),
    "metal": (170, 170, 175),
    "orange": (240, 110, 20),
    "eye": (40, 30, 25),
    "hair": (120, 80, 50),
}

parts = []  # (nom, couleur, mesh)


def add(name, color, mesh):
    parts.append((name, color, mesh))
    return mesh


def T(x=0.0, y=0.0, z=0.0):
    return trimesh.transformations.translation_matrix((x, y, z))


def limb(p1, p2, r, sections=16):
    """Capsule entre deux points."""
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    v = p2 - p1
    m = capsule(height=np.linalg.norm(v), radius=r, count=[sections, sections])
    # capsule centrée sur l'origine le long de Z
    m.apply_transform(align_vectors([0, 0, 1], v))
    m.apply_translation((p1 + p2) / 2)
    return m


def oriented_box(extents, center, direction):
    m = box(extents=extents)
    m.apply_transform(align_vectors([1, 0, 0], direction))
    m.apply_translation(center)
    return m


def oriented_cyl(r, length, center, direction, sections=20):
    m = cylinder(radius=r, height=length, sections=sections)
    m.apply_transform(align_vectors([0, 0, 1], direction))
    m.apply_translation(center)
    return m


def ellipsoid(center, radii, sub=3):
    m = icosphere(subdivisions=sub, radius=1.0)
    m.apply_scale(radii)
    m.apply_translation(center)
    return m


# Repère : Z vers le haut, personnage tourné vers -Y, son côté droit en -X. Unité : mètre.

# ---------------- Jambes / bottes ----------------
for side in (-1, 1):
    x = 0.095 * side
    add("boot", "boots", limb((x, 0.0, 0.07), (x, 0.0, 0.42), 0.068))
    foot = box(extents=(0.11, 0.27, 0.08))
    foot.apply_translation((x, -0.05, 0.04))
    add("boot_foot", "boots", foot)
    add("boot_toe", "boots", ellipsoid((x, -0.17, 0.045), (0.055, 0.06, 0.045)))
    buckle = box(extents=(0.02, 0.03, 0.03))
    buckle.apply_translation((x + 0.066 * side, 0.02, 0.38))
    add("boot_buckle", "metal", buckle)
    add("leg", "pants", limb((x, 0.0, 0.40), (x * 1.05, 0.0, 0.92), 0.075))
    add("knee", "pants", ellipsoid((x, -0.005, 0.62), (0.078, 0.08, 0.07)))
    pocket = box(extents=(0.03, 0.10, 0.12))
    pocket.apply_translation((x + 0.078 * side, -0.01, 0.73))
    add("cargo_pocket", "pants", pocket)

pelvis = ellipsoid((0, 0, 0.94), (0.19, 0.115, 0.09))
add("pelvis", "pants", pelvis)

# ---------------- Ceinture ----------------
belt = torus(major_radius=1.0, minor_radius=0.04, major_sections=48, minor_sections=8)
belt.apply_scale((0.185, 0.118, 0.45))
belt.apply_translation((0, 0, 0.995))
add("belt", "belt", belt)
buckle = box(extents=(0.06, 0.02, 0.04))
buckle.apply_translation((0, -0.125, 0.995))
add("belt_buckle", "metal", buckle)

# ---------------- Torse (chemise + gilet) ----------------
torso = ellipsoid((0, 0, 1.22), (0.175, 0.105, 0.27), sub=4)
add("torso", "shirt", torso)

vest = cylinder(radius=1.0, height=0.48, sections=40)
vest.apply_scale((0.19, 0.122, 1.0))
vest.apply_translation((0, 0, 1.17))
add("vest", "vest", vest)
for side in (-1, 1):
    add("vest_shoulder", "vest", ellipsoid((0.12 * side, 0.0, 1.405), (0.09, 0.11, 0.05)))
    # poches du gilet
    for z, h in ((1.30, 0.07), (1.05, 0.11)):
        p = box(extents=(0.10, 0.02, h))
        p.apply_translation((0.095 * side, -0.123, z))
        add("vest_pocket", "vest", p)
# ouverture du gilet : bande de chemise visible devant
strip = box(extents=(0.07, 0.02, 0.46))
strip.apply_translation((0, -0.118, 1.18))
add("shirt_front", "shirt", strip)
for i in range(4):
    b = cylinder(radius=0.006, height=0.004, sections=8)
    b.apply_transform(align_vectors([0, 0, 1], [0, -1, 0]))
    b.apply_translation((0, -0.129, 1.36 - i * 0.09))
    add("shirt_button", "shirt", b)

# col de chemise
for side in (-1, 1):
    c = box(extents=(0.07, 0.02, 0.06))
    c.apply_transform(trimesh.transformations.rotation_matrix(0.5 * side, [0, 1, 0]))
    c.apply_translation((0.04 * side, -0.07, 1.47))
    add("collar", "shirt", c)

# ---------------- Bras ----------------
r_sh, r_el, r_ha = (-0.215, 0.0, 1.40), (-0.255, -0.03, 1.14), (-0.17, -0.19, 1.035)
l_sh, l_el, l_ha = (0.215, 0.0, 1.40), (0.275, 0.0, 1.16), (0.07, -0.19, 1.235)
for sh, el, ha in ((r_sh, r_el, r_ha), (l_sh, l_el, l_ha)):
    add("upper_arm", "shirt", limb(sh, el, 0.052))
    add("forearm", "shirt", limb(el, ha, 0.045))
    add("hand", "skin", ellipsoid(ha, (0.045, 0.04, 0.05)))

# ---------------- Tête ----------------
add("neck", "skin", limb((0, 0, 1.44), (0, -0.01, 1.55), 0.056))
head = ellipsoid((0, -0.01, 1.64), (0.085, 0.095, 0.11), sub=4)
add("head", "skin", head)
add("hair", "hair", ellipsoid((0, 0.02, 1.68), (0.088, 0.09, 0.09)))
for side in (-1, 1):
    add("eye", "eye", ellipsoid((0.032 * side, -0.093, 1.655), (0.012, 0.006, 0.008), sub=2))
    add("ear", "skin", ellipsoid((0.087 * side, 0.0, 1.645), (0.012, 0.02, 0.03), sub=2))
add("nose", "skin", ellipsoid((0, -0.103, 1.625), (0.015, 0.015, 0.025), sub=2))

# ---------------- Casque ----------------
dome = icosphere(subdivisions=4, radius=1.0)
dome = dome.slice_plane([0, 0, 0], [0, 0, 1], cap=True)
dome.apply_scale((0.115, 0.125, 0.115))
dome.apply_translation((0, -0.01, 1.685))
add("helmet_dome", "helmet", dome)
brim = cylinder(radius=1.0, height=0.012, sections=48)
brim.apply_scale((0.15, 0.16, 1.0))
brim.apply_translation((0, -0.01, 1.685))
add("helmet_brim", "helmet", brim)
skirt = trimesh.creation.cone(radius=1.0, height=1.0, sections=48)
skirt = skirt.slice_plane([0, 0, 0.6], [0, 0, -1], cap=True)  # tronc de cône
skirt.apply_scale((0.165, 0.175, 0.09))
skirt.apply_translation((0, -0.01, 1.63))
add("helmet_skirt", "helmet", skirt)
visor = ellipsoid((0, -0.06, 1.75), (0.08, 0.08, 0.055))
visor = visor.slice_plane([0, -0.07, 0], [0, -1, 0], cap=True)
add("helmet_visor", "visor", visor)
for side in (-1, 1):
    ear = box(extents=(0.03, 0.06, 0.07))
    ear.apply_translation((0.13 * side, 0.02, 1.70))
    add("helmet_ear", "helmet", ear)
    add("chin_strap", "strap", limb((0.085 * side, -0.02, 1.62), (0.035 * side, -0.085, 1.55), 0.006))
chin = ellipsoid((0, -0.085, 1.54), (0.045, 0.025, 0.022), sub=2)
add("chin_cup", "helmet", chin)

# ---------------- Fusil (type A280 / StG) ----------------
hR, hL = np.array(r_ha), np.array(l_ha)
axis = (hL - hR) / np.linalg.norm(hL - hR)
up = np.cross([0, -1, 0], axis)
up /= np.linalg.norm(up)
fwd = np.cross(up, axis)


def P(t, u=0.0, f=0.0):
    """point sur le fusil : t le long du canon (0 = main droite), u vers le haut du fusil, f vers l'avant."""
    return hR + axis * t + up * u + fwd * f


def rbox(name, color, length, height, width, t, u=0.0, f=0.0):
    m = box(extents=(length, width, height))
    R = np.eye(4)
    R[:3, 0], R[:3, 1], R[:3, 2] = axis, fwd, up
    m.apply_transform(R)
    m.apply_translation(P(t, u, f) + [0, -0.02, 0])
    add(name, color, m)


rbox("rifle_receiver", "gun", 0.26, 0.06, 0.04, 0.17, 0.0)
rbox("rifle_stock", "gun", 0.20, 0.035, 0.03, 0.40, 0.0)
rbox("rifle_butt", "gun", 0.03, 0.10, 0.035, 0.51, -0.02)
rbox("rifle_grip", "gun", 0.03, 0.08, 0.03, 0.27, -0.06)
rbox("rifle_magazine", "gun", 0.04, 0.12, 0.025, 0.07, -0.08)
rbox("rifle_rail", "gun", 0.22, 0.012, 0.02, 0.15, 0.037)
add("rifle_barrel", "gun", oriented_cyl(0.016, 0.30, P(-0.12) + [0, -0.02, 0], axis))
add("rifle_shroud", "gun", oriented_cyl(0.024, 0.12, P(-0.02) + [0, -0.02, 0], axis))
add("rifle_muzzle", "orange", oriented_cyl(0.012, 0.03, P(-0.285) + [0, -0.02, 0], axis))
add("rifle_front_sight", "gun", oriented_box((0.015, 0.02, 0.05), P(-0.24, 0.03) + [0, -0.02, 0], axis))
add("rifle_scope", "gun", oriented_cyl(0.017, 0.22, P(0.06, 0.07) + [0, -0.02, 0], axis))
add("rifle_scope_lens", "metal", oriented_cyl(0.019, 0.02, P(-0.055, 0.07) + [0, -0.02, 0], axis))
rbox("rifle_scope_mount", "gun", 0.06, 0.04, 0.02, 0.06, 0.05)

# ---------------- Holster + blaster (hanche gauche) ----------------
holster = limb((0.215, -0.02, 0.92), (0.225, -0.035, 0.62), 0.03)
holster.apply_scale((1.0, 1.0, 1.0))
add("holster", "holster", holster)
add("holster_strap", "belt", limb((0.15, -0.10, 1.0), (0.215, -0.04, 0.92), 0.015))
add("holster_tie", "belt", limb((0.215, -0.04, 0.66), (0.10, -0.08, 0.64), 0.008))
add("pistol_grip", "gun", limb((0.21, -0.03, 0.93), (0.205, 0.03, 1.0), 0.02))
add("pistol_scope", "gun", oriented_cyl(0.012, 0.09, (0.245, -0.03, 0.88), (0.05, 0, -1)))
add("pistol_muzzle", "metal", oriented_cyl(0.022, 0.08, (0.228, -0.035, 0.58), (0, 0, 1)))
add("pistol_tip", "orange", oriented_cyl(0.012, 0.02, (0.228, -0.035, 0.535), (0, 0, 1)))


# ---------------- Export ----------------
def build_scene():
    scene = trimesh.Scene()
    by_color = {}
    for name, color, m in parts:
        by_color.setdefault(color, []).append(m)
    rot = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])  # Z-up -> Y-up (glTF), face vers +Z
    for color, meshes in by_color.items():
        m = trimesh.util.concatenate(meshes)
        m.apply_transform(rot)
        rgb = COLORS[color]
        mat = trimesh.visual.material.PBRMaterial(
            name=color,
            baseColorFactor=[c / 255 for c in rgb] + [1.0],
            metallicFactor=0.3 if color in ("gun", "metal", "visor") else 0.0,
            roughnessFactor=0.35 if color in ("helmet", "visor", "boots", "gun") else 0.8,
        )
        m.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(m, node_name=color, geom_name=color)
    return scene


scene = build_scene()
scene.export(os.path.join(OUT, "rebel_trooper.glb"))
scene.export(os.path.join(OUT, "rebel_trooper.obj"), mtl_name="rebel_trooper.mtl")

# STL : un seul solide, en millimètres (hauteur ~1/10 = 18 cm pour une figurine)
solid = trimesh.util.concatenate([m for _, _, m in parts])
solid.apply_scale(100.0)  # 1 m -> 100 mm  (figurine ~18 cm)
solid.export(os.path.join(OUT, "rebel_trooper_figurine_mm.stl"))

b = scene.bounds
print("parts:", len(parts), "height (m):", round(b[1][1] - b[0][1], 3), "faces:", sum(len(m.faces) for _, _, m in parts))

"""Génère un modèle 3D low-poly d'un clone trooper (style 501e légion).

Sorties : clone_trooper.glb (couleurs), clone_trooper.obj, clone_trooper.stl (impression 3D).
Unités : millimètres, hauteur totale ~300 mm.
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder, icosphere, capsule

WHITE = [235, 235, 230, 255]
BLUE = [25, 70, 190, 255]
BLACK = [25, 25, 28, 255]
GREY = [90, 90, 95, 255]

parts = []  # (nom, mesh, couleur)


def add(name, mesh, color):
    mesh.visual.face_colors = color
    parts.append((name, mesh, color))


def at(mesh, x, y, z):
    mesh.apply_translation([x, y, z])
    return mesh


def bx(name, size, pos, color):
    add(name, at(box(extents=size), *pos), color)


def ell(name, radii, pos, color, sub=3):
    m = icosphere(subdivisions=sub)
    m.apply_scale(radii)
    add(name, at(m, *pos), color)


def cyl(name, p0, p1, r, color, sections=32):
    add(name, cylinder(radius=r, segment=[p0, p1], sections=sections), color)


def taper(name, p0, p1, r0, r1, color, sections=32):
    """Cylindre conique entre deux points (z vertical)."""
    m = cylinder(radius=1.0, height=1.0, sections=sections)
    v = m.vertices
    t = v[:, 2] + 0.5  # 0 en bas, 1 en haut
    scale = r0 + (r1 - r0) * t
    v[:, 0] *= scale
    v[:, 1] *= scale
    m.vertices = v
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    m.apply_scale([1, 1, L])
    m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d / L))
    m.apply_translation((p0 + p1) / 2)
    add(name, m, color)


# Repère : z vers le haut, -y = avant du personnage. Hauteur ~172 unités, mise à l'échelle à la fin.
for s, side in ((1, "g"), (-1, "d")):
    x = 9 * s
    # Pieds / bottes
    bx(f"botte_{side}", [11, 20, 7], [x, -3, 3.5], WHITE)
    bx(f"semelle_{side}", [11.5, 20.5, 1.5], [x, -3, 0.75], GREY)
    # Tibias (avec marquage bleu de la 501e)
    taper(f"tibia_{side}", [x, 0, 6], [x, 0, 46], 5.5, 7.0, WHITE)
    taper(f"bande_tibia_{side}", [x, 0, 10], [x, 0, 14], 5.9, 6.2, BLUE)
    bx(f"marque_tibia_{side}", [5, 1.5, 9], [x, -6.3, 18], BLUE)
    # Genoux
    ell(f"genou_{side}", [6.5, 6.5, 5], [x, 0, 48], BLACK)
    bx(f"genouillere_{side}", [8, 3, 6], [x, -6, 49], WHITE)
    # Cuisses
    taper(f"cuisse_{side}", [x, 0, 50], [x * 1.05, 0, 86], 7.0, 8.5, WHITE)

# Bassin et ceinture
bx("entrejambe", [14, 14, 10], [0, 0, 86], BLACK)
ell("bassin", [17, 11, 7], [0, 0, 93], WHITE)
bx("ceinture", [34, 22, 6], [0, 0, 100], WHITE)
for i, px in enumerate(np.linspace(-13, 13, 6)):
    bx(f"poche_{i}", [4.2, 3, 5], [px, -11.5, 100], WHITE)
    bx(f"poche_trait_{i}", [4.4, 0.6, 0.6], [px, -13.1, 101.5], GREY)
bx("boucle", [6, 2, 4], [0, -11.8, 100], GREY)

# Abdomen (combinaison noire) et torse
cyl("abdomen", [0, 0, 103], [0, 0, 112], 14, BLACK)
ell("torse", [19, 12, 15], [0, 0, 125], WHITE)
bx("plastron", [30, 4, 20], [0, -9.5, 127], WHITE)
bx("bande_bleue_torse", [3.5, 1.5, 19], [0, -12, 125], BLUE)
bx("bande_bleue_col", [10, 1.5, 3], [0, -12, 135], BLUE)
bx("abdo_plaque", [16, 3, 6], [0, -12, 110], WHITE)
ell("dos", [17, 7, 13], [0, 7, 126], WHITE)

# Bras
for s, side in ((1, "g"), (-1, "d")):
    sx = 22 * s
    ell(f"epaule_{side}", [8, 9, 6], [sx, 0, 136], BLUE)       # épaulières bleues
    ell(f"articulation_epaule_{side}", [6, 6, 6], [sx * 0.95, 0, 132], BLACK)
    taper(f"biceps_{side}", [sx * 1.02, 0, 130], [sx * 1.08, 0, 113], 5.5, 5.0, WHITE)
    cyl(f"bande_biceps_{side}", [sx * 1.04, 0, 124], [sx * 1.05, 0, 121], 5.6, BLACK)
    ell(f"coude_{side}", [4.8, 4.8, 4.8], [sx * 1.08, 0, 112], BLACK)
    taper(f"avant_bras_{side}", [sx * 1.08, -1, 111], [sx * 1.1, -2, 92], 5.2, 4.3, WHITE)
    cyl(f"bande_poignet_{side}", [sx * 1.1, -2, 95], [sx * 1.1, -2, 93], 4.5, BLACK)
    ell(f"main_{side}", [3.8, 4.2, 6], [sx * 1.1, -2.5, 86], BLACK)  # gants noirs

# Cou et casque
cyl("cou", [0, 0, 138], [0, 0, 146], 6.5, BLACK)
ell("casque_dome", [11.5, 12.5, 12], [0, 0, 159], WHITE, sub=4)
bx("casque_machoire", [17, 12, 9], [0, -4, 149], WHITE)
bx("casque_menton", [8, 4, 5], [0, -10.5, 147], WHITE)
bx("visiere_horizontale", [17, 3, 3.6], [0, -10.6, 158], BLACK)
bx("visiere_verticale", [4, 3, 8], [0, -11.0, 153], BLACK)
bx("respirateur", [7, 1.5, 2], [0, -12.6, 148.5], GREY)
# Marquages bleus 501e sur le casque
bx("casque_bande_centrale", [3.5, 18, 2], [0, -1, 170.6], BLUE)
bx("casque_bande_front", [3.5, 2, 6], [0, -12.0, 165], BLUE)
for s, side in ((1, "g"), (-1, "d")):
    bx(f"casque_joue_{side}", [1.5, 6, 4], [8.6 * s, -6, 150], BLUE)
    ell(f"casque_oreille_{side}", [2, 4, 4], [11.2 * s, 0, 156], WHITE)

# Blaster DC-15 dans la main droite (pointé vers le bas)
hx = -22 * 1.1
bx("blaster_corps", [3.5, 30, 6], [hx, -6, 82], BLACK)
bx("blaster_crosse", [3, 10, 5], [hx, 10, 80], BLACK)
cyl("blaster_canon", [hx, -21, 83], [hx, -36, 83], 1.4, BLACK, sections=16)
bx("blaster_poignee", [3, 3, 8], [hx, -1, 77], BLACK)
bx("blaster_lunette", [2, 10, 2.5], [hx, -8, 86], GREY)

# Mise à l'échelle : 172 unités -> 300 mm
SCALE = 300.0 / 172.0

scene = trimesh.Scene()
for name, mesh, color in parts:
    mesh.apply_scale(SCALE)
    scene.add_geometry(mesh, node_name=name, geom_name=name)

combined = trimesh.util.concatenate([m for _, m, _ in parts])
print("Pièces :", len(parts), "| Triangles :", len(combined.faces))
print("Dimensions (mm) :", np.round(combined.extents, 1))

combined.export("clone_trooper.stl")
combined.export("clone_trooper.obj")


# glTF est en Y vers le haut : rotation -90° autour de X
gltf_scene = scene.copy()
gltf_scene.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
gltf_scene.export("clone_trooper.glb")
print("Exporté : clone_trooper.glb, clone_trooper.obj, clone_trooper.stl")

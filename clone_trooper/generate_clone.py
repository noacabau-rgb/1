"""Génère un modèle 3D low-poly d'un clone trooper du 212e bataillon (blanc / orange).

Usage :  python generate_clone.py
Sorties : clone_trooper_212.glb, clone_trooper_212.obj (+ .mtl), clone_trooper_212.stl
Unités : mètres, Y vers le haut, le personnage regarde vers +Z.
"""
import os

import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals

OUT = os.path.dirname(os.path.abspath(__file__))

COLORS = {
    "blanc": ([0.92, 0.91, 0.88, 1.0], 0.55),
    "orange": ([0.91, 0.58, 0.16, 1.0], 0.55),
    "noir": ([0.05, 0.05, 0.06, 1.0], 0.8),
    "gris": ([0.22, 0.22, 0.24, 1.0], 0.5),
    "metal": ([0.12, 0.12, 0.13, 1.0], 0.35),
    "visiere": ([0.02, 0.02, 0.03, 1.0], 0.15),
}

parts = []  # (name, mesh, color)


def add(name, mesh, color):
    parts.append((name, mesh, color))
    return mesh


def rot_x(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0])


def rot_y(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0])


def rot_z(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])


def place(mesh, center, rot=None):
    if rot is not None:
        mesh.apply_transform(rot)
    mesh.apply_translation(center)
    return mesh


def box(name, size, center, color, rot=None):
    return add(name, place(trimesh.creation.box(extents=size), center, rot), color)


def ellipsoid(name, radii, center, color, rot=None, sub=3):
    m = trimesh.creation.icosphere(subdivisions=sub, radius=1.0)
    m.apply_scale(radii)
    return add(name, place(m, center, rot), color)


def _align(mesh, p0, p1):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d / np.linalg.norm(d)))
    mesh.apply_translation((p0 + p1) / 2)
    return mesh


def segment_cyl(name, p0, p1, r, color, sections=24, scale_xy=(1, 1)):
    h = np.linalg.norm(np.subtract(p1, p0))
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    m.apply_scale([scale_xy[0], scale_xy[1], 1])
    return add(name, _align(m, p0, p1), color)


def segment_capsule(name, p0, p1, r, color):
    h = np.linalg.norm(np.subtract(p1, p0))
    m = trimesh.creation.capsule(height=h, radius=r, count=[24, 24])
    return add(name, _align(m, p0, p1), color)


def segment_plate(name, p0, p1, r0, r1, color, sections=28):
    """Plaque d'armure tronconique (cone tronqué) le long d'un segment."""
    h = np.linalg.norm(np.subtract(p1, p0))
    ang = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    ring0 = np.c_[r0 * np.cos(ang), r0 * np.sin(ang), np.full(sections, -h / 2)]
    ring1 = np.c_[r1 * np.cos(ang), r1 * np.sin(ang), np.full(sections, h / 2)]
    verts = np.vstack([ring0, ring1, [[0, 0, -h / 2], [0, 0, h / 2]]])
    faces = []
    n = sections
    for i in range(n):
        j = (i + 1) % n
        faces += [[i, j, n + j], [i, n + j, n + i], [2 * n, j, i], [2 * n + 1, n + i, n + j]]
    m = trimesh.Trimesh(verts, faces, process=True)
    return add(name, _align(m, p0, p1), color)


def lerp(a, b, t):
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


# ---------------------------------------------------------------- jambes
def leg(side, hip, knee, ankle, toe_dir):
    s = side
    segment_capsule(f"cuisse_combi_{s}", hip, knee, 0.068, "noir")
    segment_capsule(f"mollet_combi_{s}", knee, ankle, 0.055, "noir")
    # armure de cuisse + bande orange
    segment_plate(f"cuisse_armure_{s}", lerp(hip, knee, 0.05), lerp(hip, knee, 1.0), 0.088, 0.075, "blanc")
    segment_plate(f"cuisse_bande_{s}", lerp(hip, knee, 0.35), lerp(hip, knee, 0.55), 0.088, 0.083, "orange")
    # genouillere
    kd = np.subtract(ankle, hip)
    kd = kd / np.linalg.norm(kd)
    knee_c = np.asarray(knee) + np.array([0, 0.0, 0.075])
    box(f"genouillere_{s}", [0.1, 0.11, 0.035], knee_c, "orange", rot_x(-10))
    box(f"genouillere_bord_{s}", [0.11, 0.025, 0.04], knee_c + [0, 0.05, 0], "blanc", rot_x(-10))
    # tibia
    segment_plate(f"tibia_armure_{s}", lerp(knee, ankle, 0.0), lerp(knee, ankle, 0.92), 0.076, 0.06, "blanc")
    segment_plate(f"tibia_bande_{s}", lerp(knee, ankle, 0.2), lerp(knee, ankle, 0.42), 0.075, 0.07, "orange")
    # botte
    a = np.asarray(ankle, float)
    segment_cyl(f"cheville_{s}", a + [0, 0.04, 0], a - [0, 0.04, 0], 0.062, "blanc")
    foot = box(f"botte_{s}", [0.11, 0.08, 0.27], [0, 0, 0], "blanc")
    foot.apply_transform(rot_y(toe_dir))
    foot.apply_translation([a[0], 0.04, a[2] + 0.05])
    sole = box(f"semelle_{s}", [0.115, 0.025, 0.28], [0, 0, 0], "gris")
    sole.apply_transform(rot_y(toe_dir))
    sole.apply_translation([a[0], 0.0125, a[2] + 0.05])


leg("D", [-0.1, 0.95, 0.0], [-0.11, 0.53, 0.1], [-0.11, 0.1, 0.03], -4)
leg("G", [0.1, 0.95, 0.0], [0.11, 0.53, -0.04], [0.11, 0.1, -0.12], 6)

# ---------------------------------------------------------------- bassin / ceinture
ellipsoid("bassin_combi", [0.17, 0.12, 0.12], [0, 0.97, 0], "noir")
segment_plate("ceinture", [0, 1.0, 0], [0, 1.07, 0], 0.175, 0.175, "gris", sections=32)
box("boucle", [0.08, 0.06, 0.02], [0, 1.035, 0.17], "metal")
for i, x in enumerate([-0.15, -0.09, 0.09, 0.15]):
    box(f"poche_{i}", [0.05, 0.06, 0.04], [x, 1.03, 0.14 if abs(x) < 0.1 else 0.1], "blanc",
        rot_y(-30 if x < -0.12 else 30 if x > 0.12 else 0))
box("codpiece", [0.13, 0.11, 0.05], [0, 0.93, 0.11], "blanc", rot_x(8))
box("codpiece_bande", [0.13, 0.03, 0.052], [0, 0.95, 0.112], "orange", rot_x(8))
box("plaque_dos_bassin", [0.24, 0.1, 0.04], [0, 0.94, -0.12], "blanc")

# ---------------------------------------------------------------- torse
ellipsoid("torse_combi", [0.19, 0.27, 0.13], [0, 1.3, 0], "noir")
ellipsoid("abdomen", [0.16, 0.11, 0.12], [0, 1.15, 0.02], "blanc")
box("abdomen_bande", [0.22, 0.03, 0.02], [0, 1.15, 0.13], "orange", rot_x(-12))
chest = ellipsoid("plastron", [0.22, 0.15, 0.11], [0, 1.36, 0.02], "blanc")
# chevrons orange sur le plastron (motif 212e)
for sgn in (-1, 1):
    box(f"chevron_haut_{sgn}", [0.16, 0.035, 0.03], [0.08 * sgn, 1.40, 0.115], "orange", rot_z(-28 * sgn) @ rot_y(18 * sgn))
    box(f"chevron_bas_{sgn}", [0.12, 0.03, 0.03], [0.075 * sgn, 1.29, 0.11], "orange", rot_z(-28 * sgn) @ rot_y(22 * sgn))
ellipsoid("dossiere", [0.2, 0.17, 0.09], [0, 1.36, -0.07], "blanc")
box("sac_dos", [0.26, 0.24, 0.07], [0, 1.33, -0.15], "blanc")
box("sac_dos_bande", [0.265, 0.035, 0.072], [0, 1.38, -0.15], "orange")
box("col", [0.16, 0.035, 0.12], [0, 1.5, 0.01], "gris")

# ---------------------------------------------------------------- bras
def arm(side, shoulder, elbow, hand, hand_rot):
    s = side
    sh = np.asarray(shoulder, float)
    segment_capsule(f"bras_combi_{s}", sh, elbow, 0.052, "noir")
    segment_capsule(f"avantbras_combi_{s}", elbow, hand, 0.045, "noir")
    # epaulette
    sx = np.sign(sh[0])
    ellipsoid(f"epaulette_{s}", [0.095, 0.085, 0.1], sh + [0.025 * sx, 0.03, 0], "orange", rot_z(25 * sx))
    ellipsoid(f"epaulette_bord_{s}", [0.1, 0.05, 0.104], sh + [0.03 * sx, 0.0, 0], "blanc", rot_z(25 * sx))
    # biceps
    segment_plate(f"biceps_armure_{s}", lerp(sh, elbow, 0.15), lerp(sh, elbow, 1.0), 0.064, 0.058, "blanc")
    segment_plate(f"biceps_bande_{s}", lerp(sh, elbow, 0.5), lerp(sh, elbow, 0.65), 0.066, 0.064, "orange")
    # avant-bras
    segment_plate(f"avantbras_armure_{s}", lerp(elbow, hand, 0.0), lerp(elbow, hand, 0.82), 0.058, 0.05, "blanc")
    segment_plate(f"avantbras_bande_{s}", lerp(elbow, hand, 0.25), lerp(elbow, hand, 0.42), 0.058, 0.055, "orange")
    # main gantee
    g = box(f"main_{s}", [0.07, 0.09, 0.05], [0, 0, 0], "noir")
    g.apply_transform(hand_rot)
    g.apply_translation(hand)
    ellipsoid(f"coude_{s}", [0.062, 0.062, 0.062], elbow, "blanc")


arm("D", [-0.23, 1.46, 0.0], [-0.29, 1.21, -0.02], [-0.13, 1.12, 0.27], rot_z(20))
arm("G", [0.23, 1.46, 0.0], [0.31, 1.24, 0.08], [0.19, 1.15, 0.31], rot_z(-30))

# ---------------------------------------------------------------- tete / casque Phase II
segment_cyl("cou", [0, 1.5, 0], [0, 1.6, 0], 0.05, "noir")
ellipsoid("casque_dome", [0.13, 0.15, 0.145], [0, 1.72, -0.005], "blanc", sub=4)
ellipsoid("casque_crete", [0.035, 0.153, 0.148], [0, 1.72, -0.005], "orange", sub=4)
for sgn in (-1, 1):
    ellipsoid(f"casque_cote_{sgn}", [0.133, 0.035, 0.11], [0, 1.74, -0.02], "orange")
ellipsoid("casque_masque", [0.11, 0.09, 0.07], [0, 1.64, 0.08], "blanc")
segment_plate("casque_jupe", [0, 1.555, -0.01], [0, 1.64, -0.01], 0.15, 0.13, "blanc", sections=32)
# visiere en T
box("visiere_horiz", [0.2, 0.04, 0.03], [0, 1.715, 0.135], "visiere", rot_x(-6))
box("visiere_vert", [0.045, 0.07, 0.03], [0, 1.67, 0.14], "visiere")
box("sourcil_orange", [0.2, 0.025, 0.02], [0, 1.75, 0.13], "orange", rot_x(-12))
# respirateur
box("respirateur", [0.07, 0.04, 0.03], [0, 1.6, 0.14], "gris")
for sgn in (-1, 1):
    box(f"grille_{sgn}", [0.035, 0.04, 0.03], [0.055 * sgn, 1.61, 0.13], "gris", rot_y(25 * sgn))
    segment_cyl(f"antenne_{sgn}", [0.135 * sgn, 1.69, -0.02], [0.135 * sgn, 1.72, -0.02], 0.012, "gris")

# ---------------------------------------------------------------- fusil DC-15A
def rifle():
    start = np.array([-0.28, 1.1, 0.22])   # crosse
    end = np.array([0.55, 1.17, 0.36])     # bout du canon
    d = (end - start) / np.linalg.norm(end - start)
    R = trimesh.geometry.align_vectors([1, 0, 0], d)

    def rbox(name, size, local, color):
        m = trimesh.creation.box(extents=size)
        m.apply_translation(local)
        m.apply_transform(R)
        m.apply_translation(start)
        add(name, m, color)

    def rcyl(name, r, x0, x1, local_yz, color):
        m = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=16)
        m.apply_transform(rot_y(90))
        m.apply_translation([(x0 + x1) / 2, *local_yz])
        m.apply_transform(R)
        m.apply_translation(start)
        add(name, m, color)

    rbox("fusil_crosse", [0.2, 0.06, 0.035], [0.1, -0.01, 0], "metal")
    rbox("fusil_corps", [0.32, 0.075, 0.05], [0.36, 0.0, 0], "metal")
    rcyl("fusil_canon", 0.024, 0.5, 0.86, (0.01, 0), "metal")
    rcyl("fusil_bouche", 0.03, 0.82, 0.87, (0.01, 0), "gris")
    rbox("fusil_garde", [0.2, 0.03, 0.055], [0.62, -0.025, 0], "gris")
    rbox("fusil_poignee", [0.04, 0.09, 0.035], [0.27, -0.07, 0], "metal")
    rbox("fusil_chargeur", [0.035, 0.04, 0.08], [0.42, 0.0, -0.06], "gris")
    rcyl("fusil_viseur", 0.018, 0.28, 0.46, (0.065, 0), "gris")
    rbox("fusil_viseur_pied", [0.04, 0.03, 0.02], [0.37, 0.045, 0], "metal")


rifle()

# ---------------------------------------------------------------- export
scene = trimesh.Scene()
merged = {}
for name, mesh, color in parts:
    merged.setdefault(color, []).append(mesh)

materials = {}
for color, (rgba, rough) in COLORS.items():
    materials[color] = PBRMaterial(
        name=color, baseColorFactor=rgba, metallicFactor=0.1 if color != "metal" else 0.6,
        roughnessFactor=rough,
    )

for color, meshes in merged.items():
    m = trimesh.util.concatenate(meshes)
    m.visual = TextureVisuals(material=materials[color])
    scene.add_geometry(m, node_name=color, geom_name=color)

glb = os.path.join(OUT, "clone_trooper_212.glb")
scene.export(glb)

obj = os.path.join(OUT, "clone_trooper_212.obj")
# OBJ + MTL avec couleurs simples
with open(os.path.join(OUT, "clone_trooper_212.mtl"), "w") as f:
    for color, (rgba, rough) in COLORS.items():
        f.write(f"newmtl {color}\nKd {rgba[0]:.3f} {rgba[1]:.3f} {rgba[2]:.3f}\nKa 0 0 0\nKs 0.2 0.2 0.2\nNs 40\nd 1\n\n")
with open(obj, "w") as f:
    f.write("# Clone trooper 212e bataillon - modele low-poly genere\nmtllib clone_trooper_212.mtl\n")
    offset = 1
    for color, meshes in merged.items():
        m = trimesh.util.concatenate(meshes)
        f.write(f"o {color}\nusemtl {color}\n")
        for v in m.vertices:
            f.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
        for face in m.faces + offset:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        offset += len(m.vertices)

stl = os.path.join(OUT, "clone_trooper_212.stl")
trimesh.util.concatenate([p[1] for p in parts]).export(stl)

print(f"{len(parts)} pieces, {sum(len(p[1].faces) for p in parts)} triangles")
print(glb, obj, stl, sep="\n")

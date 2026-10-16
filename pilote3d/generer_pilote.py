"""Genere un modele 3D stylise du pilote rebelle (figurine ~95 mm).

Sorties : pilote.glb (couleurs), pilote.obj (+ .mtl), pilote.stl (impression 3D).
Usage : python3 generer_pilote.py
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder, icosphere, capsule

ORANGE = (196, 92, 62, 255)
BLANC = (236, 232, 220, 255)
GRIS = (72, 74, 78, 255)
NOIR = (28, 28, 30, 255)
ROUGE = (150, 34, 34, 255)
VISIERE = (222, 196, 64, 255)
PEAU = (226, 188, 158, 255)
METAL = (112, 112, 118, 255)
BLEU = (60, 120, 200, 255)

parts = []


def add(mesh, color):
    mesh.visual.face_colors = color
    parts.append(mesh)


def segment(p0, p1, r, color, sections=24):
    """Capsule entre deux points."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    h = np.linalg.norm(d)
    m = capsule(height=h, radius=r, count=[sections, sections])
    # capsule trimesh : axe Z, de z=0 a z=h
    m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], d / h))
    m.apply_translation(p0)
    add(m, color)


def tube(p0, p1, r, color, sections=24):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    m = cylinder(radius=r, segment=[p0, p1], sections=sections)
    add(m, color)


def ellipsoid(center, radii, color, sub=3):
    m = icosphere(subdivisions=sub)
    m.apply_scale(radii)
    m.apply_translation(center)
    add(m, color)


def bloc(center, size, color, rot=None):
    m = box(extents=size)
    if rot is not None:
        m.apply_transform(rot)
    m.apply_translation(center)
    add(m, color)


def anneau(center, rx, rz, h, color):
    m = cylinder(radius=1.0, height=h, sections=48)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_scale([rx, 1, rz])
    m.apply_translation(center)
    add(m, color)


# Repere : Y vers le haut, la figurine regarde vers +Z, unite = mm.
# --- Bottes ---
for s in (-1, 1):
    bloc([s * 6.5, 2.5, 2.0], [7.5, 5, 13], NOIR)
    ellipsoid([s * 6.5, 4.0, 7.5], [3.8, 2.6, 2.5], NOIR)
    tube([s * 6.3, 3, 0], [s * 6.3, 9, 0], 4.0, NOIR)

# --- Jambes (orange) ---
for s in (-1, 1):
    cheville, genou, hanche = [s * 6.3, 8, 0], [s * 6.6, 26, 1.2], [s * 6.0, 45, 0]
    segment(cheville, genou, 4.1, ORANGE)
    segment(genou, hanche, 5.0, ORANGE)
    ellipsoid([s * 6.6, 26, 3.4], [3.6, 3.4, 2.6], ORANGE)          # genouillere
    anneau([s * 6.5, 12, 0.2], 4.4, 4.4, 1.6, GRIS)                  # sangle mollet
    anneau([s * 6.3, 34, 0.6], 5.2, 5.2, 1.6, GRIS)                  # sangle cuisse
    segment([s * 9.6, 44, 3.0], [s * 10.3, 22, 3.0], 0.9, GRIS)      # sangle laterale
    bloc([s * 9.8, 30, 2.5], [2.0, 6, 5], ORANGE)                    # poche cuisse

# --- Bassin / torse ---
ellipsoid([0, 46, 0], [11.5, 7, 7], ORANGE)
segment([0, 48, 0], [0, 66, 0], 9.0, ORANGE)
ellipsoid([0, 62, 0], [10.6, 9.5, 7.2], ORANGE)
anneau([0, 49.5, 0], 11.0, 7.6, 3.2, GRIS)                           # ceinture
bloc([0, 49.5, 7.6], [6, 3.6, 1.6], GRIS)                            # boucle
bloc([11.6, 45.5, 1.0], [2.4, 8, 5], METAL)                          # etui hanche
segment([-5, 49, 7.0], [-6, 40, 6.5], 0.9, GRIS)                     # sangles harnais
segment([5, 49, 7.0], [6, 40, 6.5], 0.9, GRIS)

# --- Gilet blanc ---
ellipsoid([0, 64, 0.3], [11.2, 8.2, 8.0], BLANC)
ellipsoid([0, 67.5, -0.5], [11.6, 3.5, 7.8], BLANC)                  # col du gilet
bloc([-3.2, 64.5, 8.2], [5.5, 6.0, 2.2], BLANC)                      # boitier poitrine
bloc([-4.4, 66.0, 9.4], [1.4, 1.4, 0.6], BLEU)
bloc([-2.4, 66.0, 9.4], [1.4, 1.4, 0.6], NOIR)
bloc([-3.2, 63.0, 9.4], [3.6, 1.0, 0.6], GRIS)
cyl = cylinder(radius=1.4, height=0.6, sections=32)                  # insigne
cyl.apply_transform(trimesh.transformations.rotation_matrix(0.25, [0, 1, 0]))
cyl.apply_translation([5.0, 66.0, 7.6])
add(cyl, NOIR)
bloc([7.5, 61.5, 6.6], [2.2, 2.2, 0.8], ORANGE)                      # patch epaule

# --- Tuyau respiratoire (boitier -> hanche droite -> cuisse) ---
pts = [[-3.2, 61.5, 9.0], [-4.5, 56, 9.5], [-6, 50, 9.0], [-5.5, 44, 8.2],
       [-3, 38, 7.5], [-1.5, 32, 7.0], [-3, 26, 6.8]]
for a, b in zip(pts[:-1], pts[1:]):
    segment(a, b, 0.9, NOIR, sections=12)

# --- Cou et tete ---
tube([0, 68, 0], [0, 73, 0], 3.4, ORANGE)                            # col montant
ellipsoid([0, 79, 0.6], [4.5, 5.6, 5.0], PEAU)

# --- Casque ---
casque = icosphere(subdivisions=4)
casque.apply_scale([5.9, 5.8, 6.3])
casque.apply_translation([0, 81.2, -0.3])
# on retire la partie avant-basse (visage)
keep = ~((casque.triangles_center[:, 2] > 1.5) & (casque.triangles_center[:, 1] < 81.5))
casque.update_faces(keep)
casque.remove_unreferenced_vertices()
add(casque, NOIR)
ellipsoid([0, 85.6, -0.3], [1.2, 1.6, 6.4], ROUGE)                   # bande rouge
for s in (-1, 1):
    tube([s * 5.6, 79.5, 0.3], [s * 6.6, 79.5, 0.3], 2.4, NOIR)     # oreillettes
    ellipsoid([s * 3.4, 84.4, -0.3], [2.2, 2.7, 6.25], ROUGE, sub=4)
    segment([s * 5.2, 77.5, 1.5], [s * 3.0, 75.2, 4.0], 0.7, NOIR, 10)  # jugulaire
bloc([0, 81.3, 4.6], [8.6, 2.6, 1.2], VISIERE,
     rot=trimesh.transformations.rotation_matrix(-0.15, [1, 0, 0]))
segment([-4.4, 82.6, 4.2], [4.4, 82.6, 4.2], 0.6, NOIR, 10)         # bord visiere

# --- Bras droit (tendu, tient le blaster) ---
epD, coudeD, poignetD = [-11.2, 66.5, 0], [-16.5, 57, 4.5], [-21.5, 54, 13]
ellipsoid(epD, [4.6, 4.4, 4.6], ORANGE)
segment(epD, coudeD, 3.6, ORANGE)
segment(coudeD, poignetD, 3.3, ORANGE)
segment([-20.2, 54.5, 10.8], [-22.4, 53.8, 14.5], 3.8, NOIR)         # gant (manchette)
ellipsoid([-23.0, 53.2, 16.3], [3.0, 3.2, 3.0], NOIR)                # poing

# Blaster
bloc([-23.2, 55.2, 21.0], [2.6, 3.6, 9.5], METAL)
tube([-23.2, 56.0, 25.5], [-23.2, 56.0, 30.0], 1.0, METAL)
bloc([-23.2, 51.8, 17.2], [2.2, 5.0, 2.6], METAL,
     rot=trimesh.transformations.rotation_matrix(0.3, [1, 0, 0]))
bloc([-23.2, 57.6, 20.0], [1.4, 1.2, 4.0], GRIS)

# --- Bras gauche (le long du corps) ---
epG, coudeG, poignetG = [11.2, 66.5, 0], [13.5, 54, -0.5], [14.6, 43.5, 1.5]
ellipsoid(epG, [4.6, 4.4, 4.6], ORANGE)
segment(epG, coudeG, 3.6, ORANGE)
segment(coudeG, poignetG, 3.3, ORANGE)
segment([14.4, 45.5, 1.1], [14.8, 41.5, 1.9], 3.8, NOIR)
ellipsoid([15.0, 38.5, 2.2], [3.0, 3.6, 3.0], NOIR)

# --- Export ---
modele = trimesh.util.concatenate(parts)
modele.merge_vertices()
print("Triangles :", len(modele.faces), " Dimensions (mm) :", np.round(modele.extents, 1))

modele.export("pilote.glb")
modele.export("pilote.obj")
stl = modele.copy()
stl.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))  # Z vers le haut
stl.apply_translation([0, 0, -stl.bounds[0][2]])
stl.export("pilote.stl")

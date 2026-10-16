// Modèle 3D procédural d'un stormtrooper (armure impériale), inspiré de l'image de référence.
// Unités : mètres, Y vers le haut, le personnage regarde vers +Z, pieds à y = 0 (hauteur ≈ 1,83 m).
// Usage : import { buildStormtrooper } from './stormtrooper.js'; scene.add(buildStormtrooper(THREE));

export function buildStormtrooper(THREE) {
  const mats = {
    white: new THREE.MeshStandardMaterial({ name: 'armure_blanche', color: 0xf1f1ee, roughness: 0.32, metalness: 0.0, side: THREE.DoubleSide }),
    black: new THREE.MeshStandardMaterial({ name: 'combinaison_noire', color: 0x141414, roughness: 0.85, metalness: 0.0 }),
    grey: new THREE.MeshStandardMaterial({ name: 'details_gris', color: 0x8d9095, roughness: 0.5, metalness: 0.1 }),
    lens: new THREE.MeshStandardMaterial({ name: 'visiere', color: 0x0b120e, roughness: 0.08, metalness: 0.4 }),
    blue: new THREE.MeshStandardMaterial({ name: 'details_bleus', color: 0x3a4f8c, roughness: 0.5 }),
    gun: new THREE.MeshStandardMaterial({ name: 'blaster', color: 0x1d1e20, roughness: 0.45, metalness: 0.65 }),
    glove: new THREE.MeshStandardMaterial({ name: 'gants', color: 0x0e0e0e, roughness: 0.6 }),
  };

  const V = (x, y) => new THREE.Vector2(x, y);

  function add(parent, geo, mat, pos = [0, 0, 0], rot = [0, 0, 0], scl = [1, 1, 1], name) {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(...pos);
    m.rotation.set(...rot);
    m.scale.set(...scl);
    m.castShadow = true;
    m.receiveShadow = true;
    if (name) m.name = name;
    parent.add(m);
    return m;
  }

  function group(parent, pos = [0, 0, 0], rot = [0, 0, 0], name) {
    const g = new THREE.Group();
    g.position.set(...pos);
    g.rotation.set(...rot);
    if (name) g.name = name;
    parent.add(g);
    return g;
  }

  // Lathe à partir d'un profil [[rayon, y], ...]
  // (profil remis dans l'ordre y croissant pour que les normales pointent vers l'extérieur)
  const lathe = (pts, seg = 40, phiStart = 0, phiLength = Math.PI * 2) => {
    const p = pts[0][1] > pts[pts.length - 1][1] ? [...pts].reverse() : pts;
    return new THREE.LatheGeometry(p.map(([r, y]) => V(r, y)), seg, phiStart, phiLength);
  };

  // Boîte arrondie (extrusion biseautée d'un rectangle arrondi), centrée
  function roundBox(w, h, d, r = 0.01, bevel = 0.006) {
    const s = new THREE.Shape();
    const x = -w / 2 + bevel, y = -h / 2 + bevel, W = w - 2 * bevel, H = h - 2 * bevel;
    const rr = Math.min(r, W / 2, H / 2);
    s.moveTo(x + rr, y);
    s.lineTo(x + W - rr, y);
    s.quadraticCurveTo(x + W, y, x + W, y + rr);
    s.lineTo(x + W, y + H - rr);
    s.quadraticCurveTo(x + W, y + H, x + W - rr, y + H);
    s.lineTo(x + rr, y + H);
    s.quadraticCurveTo(x, y + H, x, y + H - rr);
    s.lineTo(x, y + rr);
    s.quadraticCurveTo(x, y, x + rr, y);
    const g = new THREE.ExtrudeGeometry(s, {
      depth: Math.max(d - 2 * bevel, 0.001), bevelEnabled: true, bevelThickness: bevel,
      bevelSize: bevel, bevelSegments: 3, curveSegments: 8,
    });
    g.translate(0, 0, -(d - 2 * bevel) / 2);
    g.computeVertexNormals();
    return g;
  }

  // Coque partielle de cylindre (plaques d'armure qui épousent le corps)
  function shell(rTop, rBot, h, arcStart, arc, seg = 32) {
    return new THREE.CylinderGeometry(rTop, rBot, h, seg, 1, false, arcStart, arc);
  }

  const root = new THREE.Group();
  root.name = 'Stormtrooper';

  // ───────────────────────────── Combinaison noire (sous l'armure)
  const suit = group(root, [0, 0, 0], [0, 0, 0], 'combinaison');
  add(suit, lathe([[0, 0.9], [0.15, 0.9], [0.16, 1.0], [0.17, 1.15], [0.18, 1.3], [0.16, 1.42], [0.07, 1.5], [0.055, 1.56], [0, 1.56]]), mats.black, [0, 0, 0], [0, 0, 0], [1, 1, 0.72], 'torse_noir');
  add(suit, new THREE.SphereGeometry(0.16, 24, 16), mats.black, [0, 0.9, 0], [0, 0, 0], [1, 0.6, 0.75], 'bassin_noir');

  // ───────────────────────────── Torse : plastron, dos, abdomen
  const torso = group(root, [0, 0, 0], [0, 0, 0], 'torse');

  // Plastron : coque avant
  add(torso, new THREE.LatheGeometry(
    [[0.15, 1.12], [0.175, 1.18], [0.188, 1.28], [0.183, 1.36], [0.162, 1.42], [0.11, 1.465]].map(([r, y]) => V(r, y)),
    40, -Math.PI * 0.36, Math.PI * 0.72,
  ), mats.white, [0, 0, 0.005], [0, 0, 0], [1.02, 1, 0.78], 'plastron');
  // Arête centrale du plastron (le "V" sculpté)
  add(torso, roundBox(0.05, 0.07, 0.02, 0.01, 0.006), mats.white, [0, 1.32, 0.147], [-0.2, 0, Math.PI / 4], [1, 1, 1], 'arete_plastron');
  add(torso, roundBox(0.03, 0.09, 0.016, 0.008, 0.005), mats.white, [-0.06, 1.27, 0.142], [-0.1, -0.35, -0.25], [1, 1, 1]);
  add(torso, roundBox(0.03, 0.09, 0.016, 0.008, 0.005), mats.white, [0.06, 1.27, 0.142], [-0.1, 0.35, 0.25], [1, 1, 1]);

  // Plaque dorsale
  add(torso, new THREE.LatheGeometry(
    [[0.15, 1.12], [0.17, 1.2], [0.18, 1.3], [0.175, 1.38], [0.15, 1.44], [0.1, 1.47]].map(([r, y]) => V(r, y)),
    40, Math.PI * 0.7, Math.PI * 0.6,
  ), mats.white, [0, 0, -0.005], [0, 0, 0], [1.02, 1, 0.8], 'dos');

  // Sangles d'épaules (pont entre plastron et dos)
  for (const s of [-1, 1]) {
    add(torso, roundBox(0.07, 0.025, 0.2, 0.01, 0.005), mats.white, [s * 0.1, 1.46, 0], [0, 0, s * -0.35], [1, 1, 1], 'sangle_epaule');
  }

  // Abdomen : plaque avec boutons
  add(torso, new THREE.CylinderGeometry(0.162, 0.155, 0.11, 40, 1, false, -Math.PI * 0.4, Math.PI * 0.8), mats.white, [0, 1.07, 0], [0, 0, 0], [1, 1, 0.78], 'abdomen');
  add(torso, new THREE.CylinderGeometry(0.16, 0.152, 0.1, 40, 1, false, Math.PI * 0.65, Math.PI * 0.7), mats.white, [0, 1.07, 0], [0, 0, 0], [1, 1, 0.8], 'abdomen_dos');
  // Panneau de contrôle (boutons)
  add(torso, roundBox(0.09, 0.05, 0.012, 0.006, 0.003), mats.white, [0.03, 1.08, 0.124], [0, 0.1, 0]);
  const btnCols = [mats.grey, mats.blue, mats.grey];
  for (let i = 0; i < 3; i++) {
    add(torso, new THREE.CylinderGeometry(0.006, 0.006, 0.006, 12), btnCols[i], [0.005 + i * 0.022, 1.08, 0.132], [Math.PI / 2, 0, 0]);
  }
  // Rainures horizontales de l'abdomen
  for (const y of [1.035, 1.12]) {
    add(torso, new THREE.TorusGeometry(0.157, 0.003, 6, 40, Math.PI * 0.8), mats.black, [0, y, 0], [Math.PI / 2, 0, Math.PI * 0.1], [1, 0.78, 1]);
  }

  // ───────────────────────────── Ceinture, détonateur thermique, coquille
  const belt = group(root, [0, 0, 0], [0, 0, 0], 'ceinture');
  add(belt, lathe([[0.165, 0.94], [0.172, 0.95], [0.172, 1.0], [0.165, 1.01]], 48), mats.white, [0, 0, 0], [0, 0, 0], [1, 1, 0.8], 'ceinturon');
  // Plaque de ceinture avec les cylindres de munitions (rangée de "dents")
  add(belt, roundBox(0.24, 0.06, 0.015, 0.006, 0.004), mats.white, [0, 0.972, 0.138], [0, 0, 0], [1, 1, 1], 'boucle');
  for (let i = -5; i <= 5; i++) {
    add(belt, new THREE.BoxGeometry(0.012, 0.04, 0.008), mats.grey, [i * 0.02, 0.972, 0.148]);
  }
  // Détonateur thermique au dos
  add(belt, new THREE.CylinderGeometry(0.022, 0.022, 0.16, 20), mats.grey, [0, 0.975, -0.15], [0, 0, Math.PI / 2], [1, 1, 1], 'detonateur');
  for (const x of [-0.08, 0.08]) {
    add(belt, new THREE.CylinderGeometry(0.024, 0.024, 0.012, 20), mats.white, [x, 0.975, -0.15], [0, 0, Math.PI / 2]);
  }
  // Coquille (pièce triangulaire bombée à l'entrejambe)
  const codShape = new THREE.Shape();
  codShape.moveTo(-0.1, 0);
  codShape.lineTo(0.1, 0);
  codShape.quadraticCurveTo(0.075, -0.1, 0.02, -0.16);
  codShape.lineTo(-0.02, -0.16);
  codShape.quadraticCurveTo(-0.075, -0.1, -0.1, 0);
  const cod = new THREE.ExtrudeGeometry(codShape, { depth: 0.02, bevelEnabled: true, bevelThickness: 0.015, bevelSize: 0.012, bevelSegments: 4 });
  add(belt, cod, mats.white, [0, 0.94, 0.1], [0.15, 0, 0], [1, 1, 1], 'coquille');
  // Plaque arrière (fessier)
  add(belt, cod, mats.white, [0, 0.94, -0.12], [-0.15, Math.PI, 0], [1.1, 0.9, 1], 'plaque_fessier');

  // ───────────────────────────── Jambes
  function buildLeg(side) {
    // side = -1 : jambe droite du personnage (côté gauche de l'image)
    const leg = group(root, [side * 0.095, 0.9, 0], [0, 0, side * -0.035], side < 0 ? 'jambe_droite' : 'jambe_gauche');
    // Cuisse noire et cuissard blanc
    add(leg, new THREE.CylinderGeometry(0.07, 0.058, 0.42, 20), mats.black, [0, -0.2, 0]);
    add(leg, lathe([[0.083, 0.0], [0.088, -0.05], [0.082, -0.2], [0.07, -0.33], [0.066, -0.36]], 32), mats.white, [0, -0.04, 0], [0, 0, 0], [1, 1, 1.05], 'cuissard');
    // Arêtes verticales des cuissards
    add(leg, new THREE.BoxGeometry(0.01, 0.3, 0.006), mats.white, [side * 0.05, -0.2, 0.068], [0.05, 0, 0]);
    add(leg, new THREE.BoxGeometry(0.004, 0.3, 0.004), mats.grey, [side * 0.073, -0.2, 0.0], [0, 0, 0]);

    // Genou (rotule noire)
    add(leg, new THREE.SphereGeometry(0.06, 20, 14), mats.black, [0, -0.42, 0.005]);

    // Tibia + jambière
    const shin = group(leg, [0, -0.42, 0], [0.02, 0, side * 0.035], 'tibia');
    add(shin, new THREE.CylinderGeometry(0.05, 0.04, 0.33, 20), mats.black, [0, -0.17, 0]);
    add(shin, lathe([[0.066, -0.03], [0.07, -0.08], [0.066, -0.2], [0.052, -0.31], [0.05, -0.34]], 32), mats.white, [0, 0, 0], [0, 0, 0], [1, 1, 1.12], 'jambiere');
    // Rebord avant de la jambière
    add(shin, roundBox(0.03, 0.3, 0.016, 0.01, 0.005), mats.white, [0, -0.18, 0.072], [0.04, 0, 0]);
    add(shin, new THREE.BoxGeometry(0.004, 0.27, 0.004), mats.grey, [side * 0.067, -0.18, 0.0]);

    // Botte blanche
    const boot = group(shin, [0, -0.36, 0.02], [0, 0, 0], 'botte');
    add(boot, lathe([[0.048, 0.02], [0.05, -0.02], [0.052, -0.05], [0, -0.05]], 24), mats.white, [0, 0, 0], [0, 0, 0], [1, 1, 1.15]);
    add(boot, roundBox(0.095, 0.05, 0.22, 0.03, 0.012), mats.white, [0, -0.04, 0.045], [0, 0, 0], [1, 1, 1], 'pied');
    add(boot, roundBox(0.1, 0.014, 0.23, 0.035, 0.004), mats.black, [0, -0.068, 0.045], [0, 0, 0], [1, 1, 1], 'semelle');
    return leg;
  }
  const rightLeg = buildLeg(-1);
  buildLeg(1);

  // Genouillère (sur le genou gauche du personnage, comme sur la photo)
  const kneePlate = new THREE.Shape();
  kneePlate.moveTo(-0.045, 0.04);
  kneePlate.lineTo(0.045, 0.04);
  kneePlate.lineTo(0.055, -0.01);
  kneePlate.lineTo(0.025, -0.055);
  kneePlate.lineTo(-0.025, -0.055);
  kneePlate.lineTo(-0.055, -0.01);
  kneePlate.closePath();
  add(root.getObjectByName('jambe_gauche'), new THREE.ExtrudeGeometry(kneePlate, { depth: 0.015, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.006, bevelSegments: 2 }), mats.white, [0, -0.43, 0.055], [-0.1, 0, 0], [1, 1, 1], 'genouillere');

  // Cartouchière de cuisse (anneau au-dessus du genou droit)
  add(rightLeg, new THREE.CylinderGeometry(0.074, 0.074, 0.05, 28, 1, true), mats.white, [0, -0.34, 0], [0, 0, 0], [1, 1, 1.05], 'cartouchiere');
  for (let i = 0; i < 4; i++) {
    add(rightLeg, roundBox(0.022, 0.045, 0.014, 0.004, 0.003), mats.white, [-0.033 + i * 0.022, -0.34, 0.077], [0, 0, 0]);
  }

  // ───────────────────────────── Bras (posture : tient le blaster devant soi)
  function buildArm(side, shoulderRot, elbowBend, wristRot) {
    const shoulder = group(root, [side * 0.205, 1.4, -0.005], shoulderRot, side < 0 ? 'bras_droit' : 'bras_gauche');
    // Épaulière (cloche)
    add(shoulder, new THREE.SphereGeometry(0.075, 28, 18, 0, Math.PI * 2, 0, Math.PI * 0.55), mats.white, [side * 0.01, 0.015, 0], [0, 0, side * -0.25], [1, 1, 1.05], 'epauliere');
    add(shoulder, new THREE.SphereGeometry(0.06, 20, 14), mats.black, [0, -0.01, 0]);
    // Biceps
    add(shoulder, new THREE.CylinderGeometry(0.048, 0.044, 0.26, 18), mats.black, [0, -0.14, 0]);
    add(shoulder, lathe([[0.058, -0.05], [0.062, -0.08], [0.058, -0.2], [0.054, -0.23]], 28), mats.white, [0, 0, 0], [0, 0, 0], [1, 1, 1], 'biceps');
    add(shoulder, new THREE.BoxGeometry(0.004, 0.15, 0.004), mats.grey, [side * 0.06, -0.14, 0]);
    // Coude
    const elbow = group(shoulder, [0, -0.28, 0], [elbowBend, 0, 0], 'coude');
    add(elbow, new THREE.SphereGeometry(0.047, 16, 12), mats.black);
    // Avant-bras (forme légèrement carrée comme sur la photo)
    add(elbow, new THREE.CylinderGeometry(0.044, 0.038, 0.24, 16), mats.black, [0, -0.13, 0]);
    add(elbow, roundBox(0.11, 0.2, 0.1, 0.035, 0.01), mats.white, [0, -0.13, 0], [0, 0, 0], [1, 1, 1], 'avant_bras');
    for (const z of [-0.015, 0.015]) {
      add(elbow, new THREE.BoxGeometry(0.004, 0.16, 0.012), mats.grey, [side * 0.055, -0.13, z]);
    }
    // Main gantée
    const wrist = group(elbow, [0, -0.26, 0], wristRot, 'poignet');
    add(wrist, roundBox(0.08, 0.09, 0.04, 0.018, 0.01), mats.glove, [0, -0.04, 0], [0, 0, 0], [1, 1, 1], 'main');
    add(wrist, roundBox(0.075, 0.035, 0.05, 0.015, 0.008), mats.glove, [0, -0.09, 0.012], [0.5, 0, 0], [1, 1, 1], 'doigts');
    add(wrist, roundBox(0.022, 0.05, 0.022, 0.009, 0.006), mats.glove, [side * -0.035, -0.04, 0.03], [0.6, 0, side * 0.4], [1, 1, 1], 'pouce');
    return { shoulder, elbow, wrist };
  }
  // Bras droit (côté gauche de l'image) : tient la poignée
  const rArm = buildArm(-1, [0, 0, 0], 0, [0, 1.3, 0]);
  // Bras gauche : soutient le canon
  const lArm = buildArm(1, [0, 0, 0], 0, [0, -1.3, 0]);

  // ───────────────────────────── Blaster E-11
  function buildBlaster() {
    const b = new THREE.Group();
    b.name = 'blaster_E11';
    // Canon principal (axe X)
    add(b, new THREE.CylinderGeometry(0.019, 0.019, 0.34, 20), mats.gun, [0.02, 0, 0], [0, 0, Math.PI / 2]);
    // Rainures de refroidissement
    for (let i = 0; i < 10; i++) {
      add(b, new THREE.BoxGeometry(0.012, 0.006, 0.041), mats.black, [-0.04 + i * 0.022, 0.012, 0]);
    }
    // Bouche du canon
    add(b, new THREE.CylinderGeometry(0.022, 0.022, 0.04, 20), mats.gun, [0.205, 0, 0], [0, 0, Math.PI / 2]);
    add(b, new THREE.CylinderGeometry(0.012, 0.012, 0.042, 16), mats.black, [0.207, 0, 0], [0, 0, Math.PI / 2]);
    // Lunette
    add(b, new THREE.CylinderGeometry(0.011, 0.011, 0.13, 16), mats.gun, [-0.02, 0.045, 0], [0, 0, Math.PI / 2]);
    add(b, new THREE.BoxGeometry(0.03, 0.025, 0.012), mats.gun, [-0.02, 0.028, 0]);
    add(b, new THREE.CylinderGeometry(0.014, 0.014, 0.02, 16), mats.gun, [0.045, 0.045, 0], [0, 0, Math.PI / 2]);
    // Boîtier / culasse
    add(b, new THREE.BoxGeometry(0.1, 0.03, 0.03), mats.gun, [-0.12, -0.005, 0]);
    // Poignée pistolet
    add(b, new THREE.BoxGeometry(0.03, 0.08, 0.026), mats.gun, [-0.13, -0.05, 0], [0, 0, 0.25]);
    // Pontet
    add(b, new THREE.TorusGeometry(0.018, 0.003, 6, 16, Math.PI), mats.gun, [-0.1, -0.022, 0], [Math.PI, 0, 0]);
    // Chargeur latéral
    add(b, new THREE.BoxGeometry(0.03, 0.02, 0.1), mats.gun, [-0.04, -0.005, -0.06]);
    // Rail du compteur et lame d'énergie
    add(b, new THREE.BoxGeometry(0.05, 0.012, 0.012), mats.grey, [0.08, -0.02, 0]);
    // Crosse repliée (sur le dessus)
    add(b, new THREE.BoxGeometry(0.2, 0.006, 0.008), mats.gun, [-0.04, 0.028, 0.022]);
    add(b, new THREE.BoxGeometry(0.2, 0.006, 0.008), mats.gun, [-0.04, 0.028, -0.022]);
    add(b, new THREE.BoxGeometry(0.01, 0.006, 0.05), mats.gun, [0.06, 0.028, 0]);
    // Éclats d'usure blancs (comme sur l'accessoire)
    add(b, new THREE.BoxGeometry(0.02, 0.004, 0.02), mats.grey, [-0.06, 0.018, 0.012]);
    return b;
  }
  const blaster = buildBlaster();
  root.add(blaster);

  // Pose : blaster tenu en travers du corps, canon vers l'avant-gauche et légèrement vers le bas
  const gunDir = new THREE.Vector3(1, -0.22, 0.5).normalize();
  const gunZ = new THREE.Vector3().crossVectors(gunDir, new THREE.Vector3(0, 1, 0)).normalize();
  const gunY = new THREE.Vector3().crossVectors(gunZ, gunDir);
  blaster.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(gunDir, gunY, gunZ));
  blaster.rotateX(-0.25); // léger roulis vers le haut, lunette visible
  const grip = new THREE.Vector3(-0.13, -0.05, 0);
  blaster.position.set(-0.085, 1.07, 0.22).sub(grip.clone().applyQuaternion(blaster.quaternion));
  blaster.updateMatrixWorld(true);

  // Cinématique inverse à deux segments : place la paume (main) sur une cible
  const UPPER = 0.28, FORE = 0.30;
  function reach(arm, target, poleOffset) {
    const S = arm.shoulder.position.clone();
    const toT = target.clone().sub(S);
    const d = Math.min(toT.length(), UPPER + FORE - 1e-3);
    const axis = toT.normalize();
    const a = (UPPER * UPPER + d * d - FORE * FORE) / (2 * d);
    const h = Math.sqrt(Math.max(UPPER * UPPER - a * a, 0));
    const pole = poleOffset.clone();
    pole.sub(axis.clone().multiplyScalar(pole.dot(axis))).normalize();
    const E = S.clone().add(axis.clone().multiplyScalar(a)).add(pole.multiplyScalar(h));
    const T = S.clone().add(axis.clone().multiplyScalar(d));
    // Repère de l'épaule : +Y du coude vers l'épaule, avant-bras plié dans le plan Y/Z (vers +Z)
    const y = S.clone().sub(E).normalize();
    const f = T.clone().sub(E).normalize();
    const z = f.clone().sub(y.clone().multiplyScalar(f.dot(y))).normalize();
    const x = new THREE.Vector3().crossVectors(y, z);
    arm.shoulder.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
    arm.elbow.rotation.set(-Math.acos(THREE.MathUtils.clamp(-y.dot(f), -1, 1)), 0, 0);
  }
  reach(rArm, new THREE.Vector3(-0.13, -0.045, 0).applyMatrix4(blaster.matrixWorld), new THREE.Vector3(-1, -0.6, -0.4));
  reach(lArm, new THREE.Vector3(0.1, -0.04, 0).applyMatrix4(blaster.matrixWorld), new THREE.Vector3(1, -0.7, -0.3));

  // ───────────────────────────── Casque
  const head = group(root, [0, 1.585, 0.01], [0.05, 0, 0], 'casque');
  // Cou noir
  add(head, new THREE.CylinderGeometry(0.055, 0.06, 0.08, 20), mats.black, [0, -0.04, -0.005]);

  // Dôme (profil tourné)
  add(head, lathe([
    [0.0, 0.215], [0.06, 0.205], [0.1, 0.18], [0.125, 0.14], [0.135, 0.1], [0.137, 0.075],
  ], 48), mats.white, [0, 0.02, 0], [0, 0, 0], [1, 1, 1.08], 'dome');
  // Jupe arrière évasée
  add(head, lathe([
    [0.137, 0.075], [0.14, 0.04], [0.146, 0.0], [0.153, -0.04], [0.158, -0.06],
  ], 32, Math.PI * 0.55, Math.PI * 0.9), mats.white, [0, 0.02, 0], [0, 0, 0], [1, 1, 1.08], 'jupe_arriere');
  // Masque : coque avant qui se resserre vers le menton
  add(head, lathe([
    [0.137, 0.075], [0.139, 0.04], [0.137, 0.0], [0.13, -0.04], [0.117, -0.075], [0.095, -0.1], [0.07, -0.11],
  ], 40, -Math.PI * 0.55, Math.PI * 1.1), mats.white, [0, 0.02, 0], [0, 0, 0], [1, 1, 1.15], 'visage');

  // Bandeau frontal gris
  add(head, new THREE.TorusGeometry(0.1375, 0.006, 8, 48, Math.PI * 1.1), mats.grey, [0, 0.095, 0], [Math.PI / 2, 0, Math.PI * -0.05 - Math.PI * 0.0], [1, 1.08, 1], 'bandeau');
  head.getObjectByName('bandeau').rotation.set(Math.PI / 2, 0, -Math.PI * 0.05);

  // Masque facial (partie avant plus plate et allongée vers le bas)
  const face = group(head, [0, 0.03, 0.075], [0, 0, 0], 'masque');

  // Lentilles des yeux (gouttes inclinées)
  for (const s of [-1, 1]) {
    const eye = add(face, new THREE.SphereGeometry(0.026, 24, 16), mats.lens, [s * 0.042, 0.04, 0.083], [0.1, s * 0.35, s * -0.3], [1.3, 0.72, 0.45], 'oeil');
    // Contour des yeux
    add(face, new THREE.TorusGeometry(0.026, 0.0035, 8, 32), mats.white, eye.position.toArray(), eye.rotation.toArray().slice(0, 3), [1.3, 0.72, 0.8]);
  }
  // Arête du nez
  add(face, roundBox(0.022, 0.06, 0.03, 0.008, 0.006), mats.white, [0, 0.01, 0.093], [-0.15, 0, 0], [1, 1, 1], 'nez');

  // Bouche en "frown" (bande noire en V inversé)
  for (const s of [-1, 1]) {
    add(face, roundBox(0.065, 0.014, 0.01, 0.005, 0.003), mats.black, [s * 0.038, -0.025, 0.09], [0, s * 0.45, s * -0.3], [1, 1, 1], 'bouche');
  }
  // Dents / grilles (petites lamelles grises)
  for (const s of [-1, 1]) {
    for (let i = 0; i < 4; i++) {
      add(face, new THREE.BoxGeometry(0.004, 0.012, 0.004), mats.grey, [s * (0.018 + i * 0.012), -0.033 + i * 0.0036 - 0.012, 0.094 - i * 0.004], [0, s * 0.45, s * -0.3]);
    }
  }

  // "Tubes" latéraux avec rayures bleues (sur les joues)
  for (const s of [-1, 1]) {
    const tubes = group(face, [s * 0.098, -0.015, 0.035], [0, s * 0.8, s * -0.15], 'tubes');
    add(tubes, roundBox(0.03, 0.055, 0.012, 0.006, 0.004), mats.white);
    for (let i = 0; i < 4; i++) {
      add(tubes, new THREE.BoxGeometry(0.003, 0.04, 0.004), mats.blue, [-0.009 + i * 0.006, 0, 0.007]);
    }
  }

  // Menton : grille centrale + deux évents ronds
  add(face, roundBox(0.03, 0.05, 0.02, 0.006, 0.004), mats.black, [0, -0.07, 0.072], [-0.3, 0, 0], [1, 1, 1], 'grille_menton');
  for (let i = 0; i < 6; i++) {
    add(face, new THREE.BoxGeometry(0.028, 0.003, 0.004), mats.grey, [0, -0.09 + i * 0.008, 0.083 - i * 0.0025], [-0.3, 0, 0]);
  }
  for (const s of [-1, 1]) {
    add(face, new THREE.CylinderGeometry(0.022, 0.022, 0.025, 24), mats.white, [s * 0.042, -0.075, 0.07], [Math.PI / 2 - 0.4, 0, 0], [1, 1, 1], 'event');
    add(face, new THREE.CylinderGeometry(0.016, 0.016, 0.027, 20), mats.grey, [s * 0.042, -0.075, 0.071], [Math.PI / 2 - 0.4, 0, 0]);
  }

  // Oreilles (disques latéraux avec bosses)
  for (const s of [-1, 1]) {
    add(head, new THREE.CylinderGeometry(0.035, 0.038, 0.012, 24), mats.white, [s * 0.142, 0.05, -0.005], [0, 0, Math.PI / 2], [1, 1, 1], 'oreille');
    add(head, new THREE.CylinderGeometry(0.012, 0.012, 0.01, 6), mats.grey, [s * 0.15, 0.05, -0.005], [0, 0, Math.PI / 2]);
    for (let i = 0; i < 4; i++) {
      add(head, new THREE.BoxGeometry(0.005, 0.03, 0.004), mats.grey, [s * 0.138, -0.01, 0.06 + i * 0.008], [0, s * 0.9, 0]);
    }
  }
  // Rayure arrière (bandes "hovi" à l'arrière du casque)
  add(head, new THREE.TorusGeometry(0.15, 0.004, 6, 40, Math.PI * 0.6), mats.grey, [0, -0.02, 0], [Math.PI / 2, 0, Math.PI * 1.2], [1, 1.08, 1], 'bande_arriere');

  return root;
}

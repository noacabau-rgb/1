// Génère stormtrooper.glb / .obj / .stl dans ./models à partir de stormtrooper.js
// Usage : npm install && npm run export
import fs from 'node:fs';
import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';
import { buildStormtrooper } from './stormtrooper.js';

// GLTFExporter utilise FileReader, absent de Node
globalThis.FileReader ??= class {
  readAsArrayBuffer(blob) { blob.arrayBuffer().then((r) => { this.result = r; this.onloadend?.(); }); }
  readAsDataURL(blob) {
    blob.arrayBuffer().then((r) => {
      this.result = `data:${blob.type};base64,${Buffer.from(r).toString('base64')}`;
      this.onloadend?.();
    });
  }
};

const trooper = buildStormtrooper(THREE);
trooper.updateMatrixWorld(true);
fs.mkdirSync('models', { recursive: true });

fs.writeFileSync('models/stormtrooper.obj', new OBJExporter().parse(trooper));
fs.writeFileSync('models/stormtrooper.stl', Buffer.from(new STLExporter().parse(trooper, { binary: true }).buffer));
const glb = await new GLTFExporter().parseAsync(trooper, { binary: true });
fs.writeFileSync('models/stormtrooper.glb', Buffer.from(glb));

for (const f of fs.readdirSync('models')) console.log(f, (fs.statSync(`models/${f}`).size / 1024).toFixed(0), 'Ko');

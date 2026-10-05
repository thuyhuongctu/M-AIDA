/**
 * The M-AIDA 3D logo (design handoff 03/10/2026, "M-AIDA Logo 3D embed.html"),
 * rebuilt as a module so three.js ships inside the app bundle instead of being
 * fetched from a CDN at run time (the CSP allows only 'self').
 *
 * Every letter has three stacked levels (ink, sand, amber) like the
 * three-level meta-analysis model; the hyphen is a forest-plot row; the map of
 * Vietnam stands between the A and the D with Hoang Sa and Truong Sa floating
 * as data points and Can Tho as the pooled diamond; Hương stands on a
 * pedestal at the left end, always turned to the camera. (The advisor's figure
 * at the right end was removed on 05/10/2026 at her request.)
 *
 * This module is loaded with a dynamic import() from Logo3D.tsx, so three.js
 * is a separate chunk that only the sign-in page and the logo dialog fetch.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export interface Logo3DOptions {
  /** CSS colour painted behind the scene. */
  background: string;
  /** Hương's cut-out figure (same-origin URL). */
  huongUrl: string;
  /** Turntable and floating islands; off under prefers-reduced-motion. */
  animate: boolean;
  /** Wheel zoom; off on the sign-in page so the wheel still scrolls the page. */
  zoom: boolean;
  /** Margin around the model when framing (1 = touching the edges). */
  framing?: number;
}

export interface Logo3DHandle {
  dispose(): void;
}

const V = (x: number, y: number) => new THREE.Vector2(x, y);
const poly = (pts: [number, number][]) => new THREE.Shape(pts.map(([x, y]) => V(x, y)));

// Vietnam outline and islands: the same geometry as the page watermark.
const VN =
  "108.9,25.2 148.2,39.0 145.3,52.5 158.2,69.0 186.7,80.1 166.7,96.0 158.2,99.0 148.2,102.0 138.2,120.0 126.8,129.0 120.3,156.0 125.4,177.0 142.5,189.0 159.6,210.0 174.4,231.0 192.4,243.0 202.9,258.0 210.9,273.0 216.6,291.0 222.3,312.0 223.7,336.0 220.9,357.0 218.0,378.0 198.1,396.0 183.8,405.0 159.6,415.5 152.5,417.0 146.8,429.0 141.1,441.0 119.7,456.0 95.5,468.0 94.6,454.5 93.5,439.5 101.2,427.5 96.3,415.5 84.1,413.4 101.2,399.0 124.0,397.5 124.8,378.0 140.2,374.4 145.3,363.0 172.4,348.0 169.6,321.0 169.6,294.0 172.4,284.4 173.8,270.0 169.6,249.0 153.9,240.0 134.0,219.0 116.8,198.0 104.0,174.0 72.7,147.0 85.5,137.4 88.3,121.5 81.2,113.4 44.2,99.0 39.9,86.4 18.2,83.4 18.5,54.0 31.3,43.5 52.7,50.4 61.3,42.0 81.2,43.2 95.8,38.4 105.5,32.4";
const HOANG_SA: [number, number][] = [[287.8, 219], [299.2, 225], [307.8, 220.5], [319.2, 231], [299.2, 237], [290.7, 229.5], [312.1, 240]];
const TRUONG_SA: [number, number][] = [[296.4, 384], [322, 402], [350.5, 393], [364.8, 414], [339.2, 432], [313.5, 438], [379, 429], [353.4, 462], [324.9, 474], [367.7, 489], [290.7, 420], [393.3, 447]];

/** True when a WebGL context can be created (probe only, released at once). */
export function webglAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (!gl) return false;
    (gl as WebGLRenderingContext).getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

export async function mountLogo3D(container: HTMLElement, opts: Logo3DOptions): Promise<Logo3DHandle> {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.setClearColor(new THREE.Color(opts.background), 1);
  renderer.domElement.setAttribute("aria-hidden", "true");
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 500);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enableZoom = opts.zoom;
  controls.enablePan = false;
  controls.autoRotate = opts.animate;
  controls.autoRotateSpeed = 1.2;
  controls.addEventListener("start", () => {
    controls.autoRotate = false;
  });

  // Studio light, as in the design's <three-d-stage>: sky/ground wash, a
  // shadow-casting key light and a dim fill so silhouettes never go black.
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d2c4, 1.0));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(4, 7, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.bias = -0.0002;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xfff4e6, 0.5);
  fill.position.set(-5, 3, -4);
  scene.add(fill);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({ opacity: 0.18 }));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // -- the model --------------------------------------------------------------
  const mat = (name: string, color: number, roughness: number, metalness = 0) =>
    new THREE.MeshStandardMaterial({ name, color, roughness, metalness });
  const ink = mat("ink", 0x1a1714, 0.38, 0.1);
  const sand = mat("sand", 0xc4b8a1, 0.7);
  const amber = mat("amber", 0xd39a3a, 0.28, 0.38);
  const pearl = mat("pearl", 0xfbf6ec, 0.25, 0.05);
  const red = mat("flag_red", 0xda251d, 0.5);
  const gold = mat("flag_star", 0xffce00, 0.4);

  const ext = (shape: THREE.Shape, depth: number, bevel = 0.01) =>
    new THREE.ExtrudeGeometry(shape, {
      depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel * 0.8, bevelSegments: 3, curveSegments: 48,
    });
  const g = new THREE.Group();
  g.name = "maida_logo";
  const add = (geo: THREE.BufferGeometry, m: THREE.Material, name: string, x = 0, y = 0, z = 0, parent: THREE.Object3D = g) => {
    const o = new THREE.Mesh(geo, m);
    o.name = name;
    o.position.set(x, y, z);
    o.castShadow = o.receiveShadow = true;
    parent.add(o);
    return o;
  };

  const M = () => poly([[0, 0], [0, 1], [0.2, 1], [0.475, 0.56], [0.75, 1], [0.95, 1], [0.95, 0], [0.75, 0], [0.75, 0.62], [0.52, 0.27], [0.43, 0.27], [0.2, 0.62], [0.2, 0]]);
  const A = () => {
    const s = poly([[0, 0], [0.36, 1], [0.56, 1], [0.92, 0], [0.71, 0], [0.63, 0.24], [0.29, 0.24], [0.21, 0]]);
    s.holes.push(new THREE.Path([V(0.35, 0.42), V(0.46, 0.75), V(0.57, 0.42)]));
    return s;
  };
  const D = () => {
    const s = new THREE.Shape();
    s.moveTo(0, 0); s.lineTo(0, 1); s.lineTo(0.45, 1); s.absarc(0.45, 0.5, 0.5, Math.PI / 2, -Math.PI / 2, true); s.lineTo(0, 0);
    const h = new THREE.Path();
    h.moveTo(0.2, 0.2); h.lineTo(0.45, 0.2); h.absarc(0.45, 0.5, 0.3, -Math.PI / 2, Math.PI / 2, false); h.lineTo(0.2, 0.8); h.lineTo(0.2, 0.2);
    s.holes.push(h);
    return s;
  };

  // three levels per letter: back amber, middle sand, front ink
  const L1 = 0.07;
  const letter = (mk: () => THREE.Shape, name: string, x: number) => {
    const grp = new THREE.Group();
    grp.name = name;
    grp.position.x = x;
    g.add(grp);
    add(ext(mk(), 0.06, 0.006), amber, `${name}_level3`, 2 * L1, -2 * L1 * 0.6 + 0.084, 0, grp);
    add(ext(mk(), 0.06, 0.006), sand, `${name}_level2`, L1, -L1 * 0.6 + 0.084, 0.09, grp);
    add(ext(mk(), 0.12, 0.012), ink, `${name}_level1`, 0, 0.084, 0.18, grp);
  };

  const s = 1.4 / 466;
  const base = 0.2;
  const mx = (a: number) => (a - 18) * s;
  const my = (b: number) => (492 - b) * s + base;

  let x = 0;
  const gap = 0.12;
  letter(M, "letter_M", x);
  x += 0.95 + gap;
  // hyphen as a forest-plot row: whisker, caps and the study square
  const hy = new THREE.Group();
  hy.position.set(x, 0.084 + 0.47, 0.24);
  g.add(hy);
  const rod = new THREE.CylinderGeometry(0.012, 0.012, 0.34, 16);
  rod.rotateZ(Math.PI / 2);
  add(rod, ink, "ci_whisker", 0.17, 0, 0, hy);
  const capGeo = new THREE.BoxGeometry(0.014, 0.09, 0.03);
  add(capGeo, ink, "ci_cap_lo", 0, 0, 0, hy);
  add(capGeo, ink, "ci_cap_hi", 0.34, 0, 0, hy);
  add(new THREE.BoxGeometry(0.11, 0.11, 0.11), amber, "ci_point", 0.19, 0, 0, hy);
  x += 0.34 + gap;
  letter(A, "letter_A1", x);
  x += 0.92 + gap;

  // the map, amber, taller than the letters
  const mapX = x;
  const outline = VN.split(" ").map((p) => {
    const [a, b] = p.split(",").map(Number);
    return [mx(a), my(b)] as [number, number];
  });
  add(ext(poly(outline), 0.2, 0.014), amber, "map_vietnam", mapX, 0, 0.1);
  const pooled = add(ext(poly([[0, 0.075], [0.055, 0], [0, -0.075], [-0.055, 0]]), 0.12, 0.01), pearl, "can_tho_pooled", mapX + mx(122), my(425), 0.27);
  const floaters: { o: THREE.Mesh; y: number; ph: number }[] = [];
  const sph = new THREE.SphereGeometry(0.024, 32, 16);
  const islands: [string, [number, number]][] = [
    ...HOANG_SA.map((p) => ["hoang_sa", p] as [string, [number, number]]),
    ...TRUONG_SA.map((p) => ["truong_sa", p] as [string, [number, number]]),
    ["phu_quoc", [71.2, 419.4]],
    ["con_dao", [145.3, 465.6]],
  ];
  islands.forEach(([n, [a, b]], i) => {
    const z = 0.2 + Math.sin(i * 2.3) * 0.18;
    const y = my(b);
    floaters.push({ o: add(sph, ink, `${n}_${i + 1}`, mapX + mx(a), y, z), y, ph: i * 0.7 });
  });
  // flag at Lung Cu
  const fx = mapX + mx(108.9);
  const fy = my(25.2);
  add(new THREE.CylinderGeometry(0.006, 0.006, 0.18, 12), ink, "flag_pole", fx, fy + 0.09, 0.2);
  add(new THREE.BoxGeometry(0.13, 0.085, 0.008), red, "flag", fx + 0.066, fy + 0.135, 0.2);
  const star = new THREE.Shape();
  for (let i = 0; i < 10; i++) {
    const r = i % 2 ? 0.012 : 0.031;
    const t = Math.PI / 2 + (i * Math.PI) / 5;
    if (i) star.lineTo(r * Math.cos(t), r * Math.sin(t));
    else star.moveTo(r * Math.cos(t), r * Math.sin(t));
  }
  add(new THREE.ShapeGeometry(star), gold, "flag_star", fx + 0.066, fy + 0.135, 0.2045);
  x = mapX + mx(393.3) + 0.04 + gap;

  letter(D, "letter_D", x);
  x += 0.95 + gap;
  letter(A, "letter_A2", x);
  x += 0.92 + 2 * L1;

  // Hương on a pedestal, a cut-out figure that always faces the camera
  const loader = new THREE.TextureLoader();
  const texH = await loader.loadAsync(opts.huongUrl);
  const figure = (tex: THREE.Texture, height: number, name: string, px: number) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    const img = tex.image as { width: number; height: number };
    const width = (height * img.width) / img.height;
    const material = new THREE.MeshStandardMaterial({ name, map: tex, alphaTest: 0.5, transparent: true, side: THREE.DoubleSide, roughness: 0.8 });
    const grp = new THREE.Group();
    grp.position.set(px, 0, 0.42);
    g.add(grp);
    const plane = new THREE.PlaneGeometry(width, height);
    plane.translate(0, height / 2 + 0.06, 0);
    const mesh = add(plane, material, `${name}_figure`, 0, 0, 0, grp);
    mesh.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: tex, alphaTest: 0.5 });
    add(new THREE.CylinderGeometry(0.22, 0.25, 0.04, 48), pearl, `${name}_pedestal`, 0, 0.03, 0, grp);
    return { grp, mesh };
  };
  const huong = figure(texH, 1.0, "huong", -0.5);

  // ground: forest-plot baseline, the pooled diamond lying flat, a pearl plinth.
  // The model runs from the left edge of Hương's pedestal to the last letter;
  // the plinth keeps the same 0.26 margin on each side as before.
  const left = -0.5 - 0.25;
  const plinthW = x - left + 0.52;
  const cx = (left + x) / 2;
  g.children.forEach((o) => {
    o.position.x -= cx;
  });
  add(new THREE.BoxGeometry(plinthW, 0.02, 0.02), ink, "axis_line", 0, 0.01, 0.62);
  const diamond = ext(poly([[0, 0.34], [0.62, 0], [0, -0.34], [-0.62, 0]]), 0.05, 0.012);
  diamond.rotateX(-Math.PI / 2);
  add(diamond, amber, "pooled_diamond", mapX - cx + mx(140), 0.0, 0.32);
  add(new THREE.BoxGeometry(plinthW, 0.06, 0.9), pearl, "plinth", 0, -0.03, 0.22);
  g.children.forEach((o) => {
    o.position.y += 0.06;
  });
  scene.add(g);

  // Frame the camera on the model. The logo is long and low, so a bounding
  // sphere (the design stage's rule) leaves most of the box empty. Instead the
  // distance is chosen so the model fits at every turntable angle: its
  // horizontal radius around the vertical axis must fit the horizontal field
  // of view, and its height plus the depth seen from the camera's elevation
  // must fit the vertical one. Recomputed on resize until the user drags.
  const box = new THREE.Box3().setFromObject(g);
  ground.position.y = box.min.y;
  const center = box.getCenter(new THREE.Vector3());
  const rxz = Math.max(
    ...[box.min.x, box.max.x].flatMap((bx) => [box.min.z, box.max.z].map((bz) => Math.hypot(bx - center.x, bz - center.z))),
  );
  const halfHeight = (box.max.y - box.min.y) / 2;
  const dir = new THREE.Vector3(1, 0.55, 1.25).normalize();
  const elevation = Math.asin(dir.y);
  const margin = opts.framing ?? 1.1;
  let userMoved = false;
  controls.addEventListener("start", () => {
    userMoved = true;
  });
  const frame = () => {
    const tanV = Math.tan((camera.fov * Math.PI) / 360);
    const tanH = tanV * camera.aspect;
    const needH = rxz / tanH;
    const needV = (halfHeight * Math.cos(elevation) + rxz * Math.sin(elevation)) / tanV;
    const dist = Math.max(needH, needV) * margin;
    camera.position.copy(center).addScaledVector(dir, dist);
    camera.near = Math.max(dist / 100, 0.01);
    camera.far = dist * 100;
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.minDistance = dist * 0.35;
    controls.maxDistance = dist * 2.5;
    controls.update();
  };
  const span = Math.max(rxz, halfHeight) * 1.5;
  Object.assign(key.shadow.camera, { left: -span, right: span, top: span, bottom: -span });
  key.shadow.camera.updateProjectionMatrix();

  const fit = () => {
    const w = container.clientWidth || 1;
    const h = container.clientHeight || 1;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (!userMoved) frame();
  };
  fit();
  const ro = new ResizeObserver(fit);
  ro.observe(container);

  const tmp = new THREE.Vector3();
  const face = (f: { grp: THREE.Group; mesh: THREE.Mesh }) => {
    f.grp.getWorldPosition(tmp);
    f.mesh.rotation.y = Math.atan2(camera.position.x - tmp.x, camera.position.z - tmp.z) - g.rotation.y;
  };
  const t0 = performance.now();
  renderer.setAnimationLoop(() => {
    if (opts.animate) {
      const t = (performance.now() - t0) / 1000;
      floaters.forEach((f) => {
        f.o.position.y = f.y + 0.06 + Math.sin(t * 1.4 + f.ph) * 0.025;
      });
      pooled.rotation.y = Math.sin(t * 0.9) * 0.6;
    }
    controls.update();
    face(huong);
    renderer.render(scene, camera);
  });

  return {
    dispose() {
      renderer.setAnimationLoop(null);
      ro.disconnect();
      controls.dispose();
      scene.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        const mats = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : [];
        mats.forEach((m) => m.dispose());
      });
      texH.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

/**
 * M-AIDA cosmos scene: the 3D background of the Cosmos look, ported from the
 * design package "M-AIDA Cloud Cosmos" (04/10/2026, `cosmos-scene.js`).
 *
 * A camera flies along one path through a spiral galaxy, past six planets
 * (one per workflow step, see planets.ts), past the Earth with a pin on Can
 * Tho, along nine golden streams (the Cuu Long) and into a constellation that
 * is a 3D forest plot. Each screen of the app is a "station" on that path;
 * changing screen flies the camera to the next station, and scrolling a
 * screen moves it a little further along.
 *
 * Changes from the design file (05/10/2026):
 * - three.js, d3-geo, topojson-client and the Natural Earth map (world-atlas)
 *   are bundled from npm, so nothing is fetched from unpkg or jsdelivr (the
 *   CSP allows only 'self'). This module is loaded with import() and only
 *   while the Cosmos look is on.
 * - The constellation shows the signed-in user's own records (r and n); a
 *   locked record is a gold star. The design drew the P6 sample.
 * - The author photos on the Can Tho pin are bundled with the app (photos sent
 *   by Do Thuy Huong on 05/10/2026), not read from the design's data file.
 * - three.js r184 is colour-managed: canvas textures are tagged sRGB, the
 *   glow shaders convert to the output colour space, light intensities are
 *   scaled from the legacy r149 units, and gradients are mixed in sRGB.
 * - Reduced motion: no animation loop; one still frame is drawn per change
 *   and the camera jumps instead of flying. The loop also stops while the
 *   tab is hidden, and runs at 30 frames a second on the working screens
 *   once the camera has arrived.
 */

import * as THREE from "three";
import { canvasTexture, planetRing, planetSurface } from "./planets";

const CYAN = "#7cc9d6";
const AMBER = "#f0b968";

export type CosmosPalette = "pastel" | "dark";

/** One record in the constellation. */
export interface CosmosEffect {
  r: number;
  n: number | null;
  /** Locked records shine as gold stars. */
  gold: boolean;
}

export interface CosmosOptions {
  palette: CosmosPalette;
  lang: "en" | "vi";
  /** Effect sizes of the signed-in user (empty on the sign-in page). */
  effects: CosmosEffect[];
  /** prefers-reduced-motion: still frames, no flight. */
  reduceMotion: boolean;
  /** Working screens: 30 fps once the camera has arrived. */
  calm: boolean;
  /** Same-origin photo URLs shown above the Can Tho pin, left to right. */
  authorPhotos?: string[];
}

interface Pal {
  pastel: boolean;
  fog: number;
  fogD: number;
  star?: number;
  bg: [string, string, string] | null;
  planets: number[];
  neb: string[];
  gIn: string;
  gMid: string;
  gOut: string;
  ocean: string;
  land: string;
  vn: string;
}

function palette(p: CosmosPalette): Pal {
  return p === "pastel"
    ? {
        pastel: true,
        fog: 0x3a3358,
        fogD: 0.0022,
        bg: ["#2b2748", "#5a4a78", "#b98aa6"],
        planets: [0xf6b8c8, 0xf8d1a8, 0xf3e6a0, 0xb8e6c9, 0xb6d8f2, 0xcdbaf0],
        neb: ["#f6b8c8", "#cdbaf0", "#b6d8f2", "#f8d1a8", "#b8e6c9"],
        gIn: "#ffe6c7",
        gMid: "#f6b8c8",
        gOut: "#b6d8f2",
        ocean: "#9fc9e6",
        land: "#f3dfe6",
        vn: "#ffd27a",
      }
    : {
        pastel: false,
        fog: 0x04060b,
        fogD: 0.0028,
        bg: null,
        planets: [0x54b6c6, 0x7cc9d6, 0x8fa8e8, 0xe0a24a, 0x5fbd8e, 0xf0b968],
        neb: ["#2e7f93", "#7a4fb0", "#c4823a", "#3a5fbf", "#2f9c7a"],
        gIn: AMBER,
        gMid: CYAN,
        gOut: "#3d7ccf",
        ocean: "#16344a",
        land: "#4f6b78",
        vn: "#ffd27a",
      };
}

const EARTH_AT = 0.76;
const FZ = -300; // depth of the constellation

/** Fractional part in [0, 1), also for negative numbers (curve parameters). */
function frac(x: number): number {
  const f = x - Math.floor(x);
  return Number.isFinite(f) ? Math.min(f, 0.999999) : 0;
}

/** sRGB components (0-1) of a CSS colour. */
function srgb(css: string): { r: number; g: number; b: number } {
  const t = { r: 0, g: 0, b: 0 };
  new THREE.Color(css).getRGB(t, THREE.SRGBColorSpace);
  return t;
}

/** Mix two CSS colours in sRGB (as r149 did) and return a linear THREE.Color. */
function mixSrgb(a: { r: number; g: number; b: number }, b: { r: number; g: number; b: number }, t: number): THREE.Color {
  return new THREE.Color().setRGB(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t, THREE.SRGBColorSpace);
}

function glowTex(inner: string, outer: string): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d")!;
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, inner);
  gr.addColorStop(0.25, outer);
  gr.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = gr;
  g.fillRect(0, 0, 128, 128);
  return canvasTexture(c);
}

function nebTex(col: string, seed: number): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d")!;
  let k = seed * 131 + 7;
  const rnd = () => (k = (k * 16807) % 2147483647) / 2147483647;
  const cc = srgb(col);
  for (let n = 0; n < 22; n++) {
    const x = 128 + (rnd() - 0.5) * 120;
    const y = 128 + (rnd() - 0.5) * 120;
    const r = 30 + rnd() * 70;
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    const a = 0.08 + rnd() * 0.12;
    gr.addColorStop(0, `rgba(${(cc.r * 255) | 0},${(cc.g * 255) | 0},${(cc.b * 255) | 0},${a})`);
    gr.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 256, 256);
  }
  return canvasTexture(c);
}

/** Fresnel glow around a sphere; converts to the output colour space. */
function atmosphere(radius: number, color: THREE.ColorRepresentation, k: number, gain: number, blending: THREE.Blending, seg: number) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(radius, seg, seg),
    new THREE.ShaderMaterial({
      uniforms: { c: { value: new THREE.Color(color) } },
      transparent: true,
      side: THREE.BackSide,
      blending,
      depthWrite: false,
      vertexShader:
        "varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }",
      fragmentShader: `uniform vec3 c; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(${k.toFixed(2)} - dot(vN, vV), 3.0); gl_FragColor = vec4(c, clamp(f,0.0,1.0)*${gain.toFixed(2)});
        #include <colorspace_fragment>
      }`,
    })
  );
}

function disposeObject(root: THREE.Object3D) {
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    m.geometry?.dispose?.();
    const mats = Array.isArray(m.material) ? m.material : m.material ? [m.material] : [];
    mats.forEach((mat) => {
      Object.values(mat).forEach((v) => {
        if (v instanceof THREE.Texture) v.dispose();
      });
      if ((mat as THREE.ShaderMaterial).uniforms) {
        Object.values((mat as THREE.ShaderMaterial).uniforms).forEach((u) => {
          if (u.value instanceof THREE.Texture) u.value.dispose();
        });
      }
      mat.dispose();
    });
  });
}

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

interface Planet {
  g: THREE.Group;
  m: THREE.Mesh;
  ring: THREE.Mesh;
  moon: THREE.Mesh;
  mr: number;
  mph: number;
}

export class CosmosScene {
  private host: HTMLElement;
  private opts: CosmosOptions;
  private mobile = false;
  private renderer: THREE.WebGLRenderer | null = null;
  private scene: THREE.Scene | null = null;
  private cam: THREE.PerspectiveCamera | null = null;
  private path: THREE.CatmullRomCurve3 | null = null;
  private target = 0;
  private cur = 0;
  private vs = 0;
  private mouse = { x: 0, y: 0 };
  private raf = 0;
  private last = 0;
  private elapsed = 0;
  private lastFrame = 0;
  private built = 0; // bumps on every rebuild, so a late Earth does not land in an old scene
  private look = new THREE.Vector3();
  private lk = new THREE.Vector3();
  private dot: THREE.CanvasTexture | null = null;
  private pal: Pal = palette("pastel");
  private BL: THREE.Blending = THREE.AdditiveBlending;
  private galaxy: THREE.Points | null = null;
  private stars: THREE.Points | null = null;
  private core: THREE.Sprite | null = null;
  private planets: Planet[] = [];
  private nebulae: { sp: THREE.Sprite; ph: number }[] = [];
  private pulse: { s: THREE.Sprite; base: number; ph: number }[] = [];
  private cons: THREE.Group | null = null;
  private earth: THREE.Group | null = null;
  private earthSpin: THREE.Group | null = null;
  private earthPulse: THREE.Mesh | null = null;
  private spinQ = new THREE.Quaternion();
  private flowRivers: (el: number) => void = () => {};
  private flowData: (el: number) => void = () => {};
  private updateWarp: (v: number, dt: number) => void = () => {};
  private updateComets: (el: number) => void = () => {};
  private disposed = false;

  constructor(host: HTMLElement, opts: CosmosOptions) {
    this.host = host;
    this.opts = { ...opts };
    addEventListener("pointermove", this.onMove);
    addEventListener("resize", this.onResize);
    document.addEventListener("visibilitychange", this.onVisibility);
    this.build(); // throws when WebGL is unavailable; the caller falls back to 2D
  }

  // ---- public API --------------------------------------------------------

  /** Fly (or jump, with reduced motion) to a point of the path, 0..1. */
  setProgress(p: number, jump = false) {
    this.target = Math.max(0, Math.min(0.999, p));
    if (jump || this.opts.reduceMotion) this.cur = this.target;
    this.kick();
  }

  update(next: Partial<CosmosOptions>) {
    const prev = this.opts;
    this.opts = { ...prev, ...next };
    const mobile = innerWidth < 720;
    if (prev.palette !== this.opts.palette || prev.lang !== this.opts.lang || mobile !== this.mobile) {
      this.teardown();
      this.build();
      return;
    }
    if (next.effects && next.effects !== prev.effects) this.buildConstellation();
    if (prev.reduceMotion !== this.opts.reduceMotion) {
      if (this.opts.reduceMotion) this.cur = this.target;
    }
    this.kick();
  }

  dispose() {
    this.disposed = true;
    removeEventListener("pointermove", this.onMove);
    removeEventListener("resize", this.onResize);
    document.removeEventListener("visibilitychange", this.onVisibility);
    this.teardown();
  }

  // ---- events ------------------------------------------------------------

  private onMove = (e: PointerEvent) => {
    this.mouse.x = e.clientX / innerWidth - 0.5;
    this.mouse.y = e.clientY / innerHeight - 0.5;
    if (!this.opts.reduceMotion) this.kick();
  };

  private onResize = () => {
    if (!this.renderer || !this.cam) return;
    if ((innerWidth < 720) !== this.mobile) {
      this.update({});
      return;
    }
    this.cam.aspect = innerWidth / innerHeight;
    this.cam.updateProjectionMatrix();
    this.renderer.setSize(innerWidth, innerHeight);
    this.kick();
  };

  private onVisibility = () => {
    if (document.hidden) {
      cancelAnimationFrame(this.raf);
      this.raf = 0;
    } else this.kick();
  };

  /** Start the loop (or draw one still frame with reduced motion). */
  private kick() {
    if (this.disposed || !this.renderer) return;
    if (this.opts.reduceMotion) {
      if (!this.raf) this.raf = requestAnimationFrame(() => {
        this.raf = 0;
        this.safeFrame(0);
      });
      return;
    }
    if (!this.raf && !document.hidden) {
      this.last = performance.now();
      this.raf = requestAnimationFrame(this.loop);
    }
  }

  private loop = (now: number) => {
    this.raf = 0;
    if (this.disposed || document.hidden || this.opts.reduceMotion) return;
    const settled = Math.abs(this.target - this.cur) < 1e-4 && this.vs < 1e-4;
    const minGap = this.opts.calm && settled ? 1000 / 30 : 0;
    if (now - this.lastFrame >= minGap - 1) {
      // The frame time can be a little earlier than the performance.now() taken
      // in kick(); never let the clock run backwards.
      const dt = Math.max(0, Math.min(0.1, (now - this.last) / 1000));
      this.last = now;
      this.lastFrame = now;
      this.safeFrame(dt);
    }
    this.raf = requestAnimationFrame(this.loop);
  };

  // ---- build -------------------------------------------------------------

  private teardown() {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
    if (this.scene) disposeObject(this.scene);
    this.dot?.dispose();
    if (this.renderer) {
      this.renderer.dispose();
      this.renderer.domElement.remove();
    }
    this.renderer = null;
    this.scene = null;
    this.cam = null;
    this.cons = null;
    this.earth = null;
    this.earthSpin = null;
    this.earthPulse = null;
    this.planets = [];
    this.nebulae = [];
    this.pulse = [];
  }

  private build() {
    const T = THREE;
    const MOB = (this.mobile = innerWidth < 720);
    const Q = MOB ? 0.45 : 1;
    const PAL = (this.pal = palette(this.opts.palette));
    this.BL = T.AdditiveBlending;
    const built = ++this.built;

    const renderer = new T.WebGLRenderer({ antialias: !MOB, alpha: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(devicePixelRatio, MOB ? 1.5 : 2));
    renderer.setSize(innerWidth, innerHeight);
    renderer.domElement.className = "cosmos-scene-canvas";
    renderer.domElement.setAttribute("aria-hidden", "true");
    this.host.appendChild(renderer.domElement);
    this.renderer = renderer;

    const scene = new T.Scene();
    scene.fog = new T.FogExp2(PAL.fog, PAL.fogD);
    this.scene = scene;
    if (PAL.bg) {
      const bc = document.createElement("canvas");
      bc.width = 4;
      bc.height = 256;
      const bg = bc.getContext("2d")!;
      const gr = bg.createLinearGradient(0, 0, 0, 256);
      gr.addColorStop(0, PAL.bg[0]);
      gr.addColorStop(0.55, PAL.bg[1]);
      gr.addColorStop(1, PAL.bg[2]);
      bg.fillStyle = gr;
      bg.fillRect(0, 0, 4, 256);
      scene.background = canvasTexture(bc);
    }
    const cam = new T.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 2000);
    this.cam = cam;
    const dot = (this.dot = glowTex("rgba(255,255,255,1)", "rgba(255,255,255,.35)"));

    // starfield
    const N = Math.round(7000 * Q);
    const sp = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const r = 300 + Math.random() * 700;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      sp.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th)], i * 3);
    }
    const sg = new T.BufferGeometry();
    sg.setAttribute("position", new T.BufferAttribute(sp, 3));
    const stars = new T.Points(sg, new T.PointsMaterial({ size: 2.2, map: dot, transparent: true, depthWrite: false, color: PAL.star ?? 0xcfd8e6, fog: false }));
    scene.add(stars);
    this.stars = stars;

    // spiral galaxy (colours mixed in sRGB, as in the design)
    const G = Math.round(16000 * Q);
    const gp = new Float32Array(G * 3);
    const gc = new Float32Array(G * 3);
    const ci = srgb(PAL.gIn);
    const co = srgb(PAL.gOut);
    const cm = srgb(PAL.gMid);
    for (let i = 0; i < G; i++) {
      const rad = Math.pow(Math.random(), 1.6) * 70;
      const arm = ((i % 4) / 4) * Math.PI * 2;
      const spin = rad * 0.09;
      const rx = (Math.random() - 0.5) * (2 + rad * 0.18);
      const ry = (Math.random() - 0.5) * (1 + 6 / (1 + rad * 0.2));
      const rz = (Math.random() - 0.5) * (2 + rad * 0.18);
      gp.set([Math.cos(arm + spin) * rad + rx, ry, Math.sin(arm + spin) * rad + rz], i * 3);
      const c = rad < 25 ? mixSrgb(ci, cm, rad / 25) : mixSrgb(cm, co, Math.min(1, (rad - 25) / 45));
      gc.set([c.r, c.g, c.b], i * 3);
    }
    const gg = new T.BufferGeometry();
    gg.setAttribute("position", new T.BufferAttribute(gp, 3));
    gg.setAttribute("color", new T.BufferAttribute(gc, 3));
    const galaxy = new T.Points(gg, new T.PointsMaterial({ size: 0.9, map: dot, vertexColors: true, transparent: true, depthWrite: false, blending: this.BL }));
    galaxy.rotation.x = 0.18;
    scene.add(galaxy);
    this.galaxy = galaxy;
    const core = new T.Sprite(new T.SpriteMaterial({ map: glowTex("rgba(255,240,215,1)", "rgba(240,185,104,.45)"), blending: this.BL, depthWrite: false }));
    core.scale.set(34, 34, 1);
    scene.add(core);
    this.core = core;

    // Lights, in r184 physical units (the design's r149 legacy units times pi;
    // the point light keeps no distance decay, as the legacy light nearly did).
    scene.add(new T.AmbientLight(0x3a4658, 0.8 * Math.PI));
    scene.add(new T.HemisphereLight(0x9fd6e0, 0x2a1a10, 0.5 * Math.PI));
    scene.add(new T.PointLight(0xffe2b8, 2.2 * Math.PI * 0.6, 400, 0));

    // camera path
    const path = new T.CatmullRomCurve3([
      new T.Vector3(0, 55, 150),
      new T.Vector3(60, 22, 70),
      new T.Vector3(30, 8, 10),
      new T.Vector3(-30, 6, -40),
      new T.Vector3(25, 4, -95),
      new T.Vector3(-20, 10, -150),
      new T.Vector3(0, 14, -200),
      new T.Vector3(0, 12, -255),
      new T.Vector3(0, 60, -300),
    ]);
    this.path = path;

    // six workflow planets
    const pcol = PAL.planets;
    this.planets = [];
    for (let i = 0; i < 6; i++) {
      const t = 0.25 + i * 0.075;
      const pt = path.getPointAt(t);
      const tan = path.getTangentAt(t);
      const side = new T.Vector3()
        .crossVectors(tan, new T.Vector3(0, 1, 0))
        .normalize()
        .multiplyScalar((i % 2 ? -1 : 1) * (MOB ? 5 : 11));
      const g = new T.Group();
      g.position.copy(pt).add(side).add(new T.Vector3(0, -2, 0));
      const pr = 2.6 + (i % 3) * 0.6;
      const m = new T.Mesh(
        new T.SphereGeometry(pr, 64, 64),
        new T.MeshStandardMaterial({ map: planetSurface(pcol[i], i, MOB), roughness: 0.95, metalness: 0, emissive: pcol[i], emissiveIntensity: 0.08 })
      );
      const atm = atmosphere(pr * 1.28, pcol[i], 0.75, 1.6, this.BL, 48);
      const moon = new T.Mesh(new T.SphereGeometry(0.45, 24, 24), new T.MeshStandardMaterial({ color: 0xd8cfc0, roughness: 1 }));
      const ring = planetRing(pcol[i], i, pr, MOB);
      ring.rotation.x = Math.PI / 2.4;
      const halo = new T.Sprite(new T.SpriteMaterial({ map: dot, color: pcol[i], transparent: true, opacity: 0.35, blending: this.BL, depthWrite: false }));
      halo.scale.set(14, 14, 1);
      g.add(m, atm, ring, halo, moon);
      scene.add(g);
      this.planets.push({ g, m, ring, moon, mr: pr * 2.7, mph: i * 1.3 });
    }

    // effect-size constellation: a 3D forest plot of the user's records
    this.buildConstellation();

    // Cuu Long: nine golden streams flowing into the constellation
    const RP = MOB ? 120 : 260;
    const rivers: { curve: THREE.CatmullRomCurve3; geo: THREE.BufferGeometry; seeds: Float32Array; v: number }[] = [];
    for (let k = 0; k < 9; k++) {
      const off = (k - 4) * 9;
      const curve = new T.CatmullRomCurve3([
        new T.Vector3(off * 0.25, -14, -150),
        new T.Vector3(off * 0.6, -16 + Math.sin(k) * 3, -200),
        new T.Vector3(off * 1.1, -12, -250),
        new T.Vector3(off * 0.35, -6, FZ + 4),
      ]);
      const pos = new Float32Array(RP * 3);
      const seeds = new Float32Array(RP);
      for (let j = 0; j < RP; j++) seeds[j] = Math.random();
      const geo = new T.BufferGeometry();
      geo.setAttribute("position", new T.BufferAttribute(pos, 3));
      const pts = new T.Points(geo, new T.PointsMaterial({ size: 0.9, map: dot, color: k % 2 ? 0xffd27a : 0xe0a24a, transparent: true, opacity: 0.85, depthWrite: false, blending: this.BL }));
      pts.frustumCulled = false;
      scene.add(pts);
      rivers.push({ curve, geo, seeds, v: 0.03 + Math.random() * 0.02 });
    }
    const tmpV = new T.Vector3();
    this.flowRivers = (el) =>
      rivers.forEach((rv) => {
        const a = rv.geo.attributes.position.array as Float32Array;
        for (let j = 0; j < RP; j++) {
          const u = frac(rv.seeds[j] + el * rv.v);
          rv.curve.getPointAt(u, tmpV);
          a[j * 3] = tmpV.x + Math.sin(j * 12.9) * 0.6;
          a[j * 3 + 1] = tmpV.y + Math.cos(j * 7.3) * 0.4;
          a[j * 3 + 2] = tmpV.z;
        }
        rv.geo.attributes.position.needsUpdate = true;
      });

    // nebulae along the flight path
    this.nebulae = [];
    for (let k = 0; k < (MOB ? 9 : 16); k++) {
      const t = 0.05 + k * 0.058;
      const pt = path.getPointAt(Math.min(0.98, t));
      const mat = new T.SpriteMaterial({ map: nebTex(PAL.neb[k % PAL.neb.length], k), transparent: true, opacity: 0.32, depthWrite: false, blending: this.BL, fog: false });
      const s = new T.Sprite(mat);
      const sc = 70 + (k % 4) * 30;
      s.scale.set(sc, sc, 1);
      s.position.copy(pt).add(new T.Vector3((k % 2 ? 1 : -1) * (40 + (k % 3) * 18), -10 + (k % 5) * 6, -30));
      scene.add(s);
      this.nebulae.push({ sp: s, ph: k });
    }

    // data stream threading the six planets
    const dcurve = new T.CatmullRomCurve3(this.planets.map((p) => p.g.position.clone()));
    const DN = MOB ? 350 : 900;
    const dpos = new Float32Array(DN * 3);
    const dseed = new Float32Array(DN);
    for (let j = 0; j < DN; j++) dseed[j] = Math.random();
    const dgeo = new T.BufferGeometry();
    dgeo.setAttribute("position", new T.BufferAttribute(dpos, 3));
    const dpts = new T.Points(dgeo, new T.PointsMaterial({ size: 0.55, map: dot, color: 0xbfeaf0, transparent: true, opacity: 0.9, depthWrite: false, blending: this.BL }));
    dpts.frustumCulled = false;
    scene.add(dpts);
    const dv = new T.Vector3();
    this.flowData = (el) => {
      const a = dgeo.attributes.position.array as Float32Array;
      for (let j = 0; j < DN; j++) {
        const u = frac(dseed[j] + el * 0.035);
        dcurve.getPointAt(u, dv);
        a[j * 3] = dv.x + Math.sin(j * 3.1 + el) * 0.5;
        a[j * 3 + 1] = dv.y + Math.cos(j * 1.7 + el) * 0.5;
        a[j * 3 + 2] = dv.z + Math.sin(j * 5.3) * 0.5;
      }
      dgeo.attributes.position.needsUpdate = true;
    };

    // warp streaks around the camera, stretched by the flight speed
    const WN = MOB ? 180 : 500;
    const wpos = new Float32Array(WN * 6);
    const wbase: number[][] = [];
    for (let j = 0; j < WN; j++) {
      const a = Math.random() * Math.PI * 2;
      const r = 6 + Math.random() * 30;
      wbase.push([Math.cos(a) * r, Math.sin(a) * r, -Math.random() * 160]);
    }
    const wgeo = new T.BufferGeometry();
    wgeo.setAttribute("position", new T.BufferAttribute(wpos, 3));
    const wmat = new T.LineBasicMaterial({ color: 0xcfe8ff, transparent: true, opacity: 0, depthWrite: false, blending: this.BL });
    const warp = new T.LineSegments(wgeo, wmat);
    warp.frustumCulled = false;
    cam.add(warp);
    scene.add(cam);
    this.updateWarp = (v, dt) => {
      const a = wgeo.attributes.position.array as Float32Array;
      const len = 0.5 + v * 260;
      wmat.opacity = Math.min(0.75, v * 40);
      for (let j = 0; j < WN; j++) {
        const b = wbase[j];
        b[2] += dt * (20 + v * 3000);
        if (b[2] > 0) b[2] -= 160;
        a[j * 6] = b[0];
        a[j * 6 + 1] = b[1];
        a[j * 6 + 2] = b[2];
        a[j * 6 + 3] = b[0];
        a[j * 6 + 4] = b[1];
        a[j * 6 + 5] = b[2] - len;
      }
      wgeo.attributes.position.needsUpdate = true;
    };

    // comets
    const comets: { head: THREE.Sprite; tg: THREE.BufferGeometry; TN: number; ph: number; r: number; y: number; z: number }[] = [];
    for (let k = 0; k < 3; k++) {
      const head = new T.Sprite(new T.SpriteMaterial({ map: dot, color: 0xfff2d8, transparent: true, depthWrite: false, blending: this.BL }));
      head.scale.set(2.2, 2.2, 1);
      const TN = 40;
      const tpos = new Float32Array(TN * 3);
      const tg = new T.BufferGeometry();
      tg.setAttribute("position", new T.BufferAttribute(tpos, 3));
      const tail = new T.Points(tg, new T.PointsMaterial({ size: 1.1, map: dot, color: 0xf0b968, transparent: true, opacity: 0.6, depthWrite: false, blending: this.BL }));
      tail.frustumCulled = false;
      scene.add(head, tail);
      comets.push({ head, tg, TN, ph: k * 2.1, r: 90 + k * 40, y: -10 + k * 18, z: -60 - k * 90 });
    }
    this.updateComets = (el) =>
      comets.forEach((c) => {
        const a = c.tg.attributes.position.array as Float32Array;
        for (let j = 0; j < c.TN; j++) {
          const t = el * 0.12 + c.ph - j * 0.006;
          a[j * 3] = Math.cos(t) * c.r;
          a[j * 3 + 1] = c.y + Math.sin(t * 2) * 6;
          a[j * 3 + 2] = c.z + Math.sin(t) * c.r * 0.4;
        }
        c.head.position.set(a[0], a[1], a[2]);
        c.tg.attributes.position.needsUpdate = true;
      });

    this.cur = this.target;
    this.look.set(0, 0, 0);
    this.lk.set(0, 0, 0);
    this.vs = 0;
    void this.buildEarth(built);
    this.kick();
  }

  /** (Re)build the constellation from opts.effects. */
  private buildConstellation() {
    const T = THREE;
    const scene = this.scene;
    const dot = this.dot;
    if (!scene || !dot) return;
    if (this.cons) {
      scene.remove(this.cons);
      // keep the shared dot texture alive
      this.cons.traverse((o) => {
        const m = o as THREE.Mesh;
        m.geometry?.dispose?.();
        const mat = m.material as THREE.Material & { map?: THREE.Texture | null };
        if (mat) {
          if (mat.map && mat.map !== dot) mat.map.dispose();
          mat.dispose();
        }
      });
    }
    this.pulse = [];
    const cons = new T.Group();
    cons.position.set(0, 12, FZ);
    cons.add(
      new T.Line(
        new T.BufferGeometry().setFromPoints([new T.Vector3(0, -24, 0), new T.Vector3(0, 24, 0)]),
        new T.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 })
      )
    );
    const EFFECTS = this.opts.effects.filter((e) => Number.isFinite(e.r));
    const NE = EFFECTS.length || 1;
    const xs = 32 / Math.max(0.05, ...EFFECTS.map((e) => Math.abs(e.r)));
    const yAt = (i: number) => 22 - (i + 0.5) * (46 / NE);
    EFFECTS.forEach((e, i) => {
      const y = yAt(i);
      const x = e.r * xs;
      const col = new T.Color(e.r < 0 ? AMBER : CYAN);
      const s = new T.Sprite(new T.SpriteMaterial({ map: dot, color: col, blending: this.BL, depthWrite: false, transparent: true }));
      const sz = 1.2 + Math.log10(Math.max(2, e.n || 2)) * 0.9;
      s.scale.set(sz, sz, 1);
      s.position.set(x, y, (Math.random() - 0.5) * 6);
      const ln = new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(0, y, 0), s.position.clone()]), new T.LineBasicMaterial({ color: col, transparent: true, opacity: 0.4 }));
      cons.add(s, ln);
      this.pulse.push({ s, base: sz, ph: i * 0.7 });
    });
    if (EFFECTS.length > 1) {
      cons.add(
        new T.Line(
          new T.BufferGeometry().setFromPoints(EFFECTS.map((e, i) => new T.Vector3(e.r * xs, yAt(i), 0))),
          new T.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.12 })
        )
      );
    }
    // gold stars: locked records
    if (EFFECTS.some((e) => e.gold)) {
      const c = document.createElement("canvas");
      c.width = c.height = 128;
      const g = c.getContext("2d")!;
      const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
      gr.addColorStop(0, "rgba(255,210,122,.55)");
      gr.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = gr;
      g.fillRect(0, 0, 128, 128);
      g.beginPath();
      for (let k = 0; k < 10; k++) {
        const a = -Math.PI / 2 + (k * Math.PI) / 5;
        const rr = k % 2 ? 15 : 38;
        g.lineTo(64 + Math.cos(a) * rr, 64 + Math.sin(a) * rr);
      }
      g.closePath();
      g.fillStyle = "#ffd27a";
      g.fill();
      const starTex = canvasTexture(c);
      EFFECTS.forEach((e, i) => {
        if (!e.gold) return;
        const s = new T.Sprite(new T.SpriteMaterial({ map: starTex, transparent: true, depthWrite: false, blending: this.BL }));
        s.scale.set(4.2, 4.2, 1);
        s.position.set(e.r * xs, yAt(i), 1);
        cons.add(s);
      });
    }
    scene.add(cons);
    this.cons = cons;
    this.kick();
  }

  /** The Earth with Vietnam lit and a pin on Can Tho (loaded lazily). */
  private async buildEarth(built: number) {
    try {
      const [geo, topo, world] = await Promise.all([
        import("d3-geo"),
        import("topojson-client"),
        import("world-atlas/countries-50m.json"),
      ]);
      try {
        await Promise.race([
          Promise.all([document.fonts?.load("600 54px 'Bricolage Grotesque'"), document.fonts?.load("400 30px 'Be Vietnam Pro'")]),
          new Promise((r) => setTimeout(r, 1500)),
        ]);
      } catch {
        /* the label falls back to a system face */
      }
      if (built !== this.built || !this.renderer || !this.scene || !this.path || !this.cam) return;
      const T = THREE;
      const PAL = this.pal;
      const scene = this.scene;
      const path = this.path;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const topology = (world as any).default ?? world;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const countries = (topo.feature(topology, topology.objects.countries) as any).features as any[];
      const W = Math.min(this.mobile ? 2048 : 4096, this.renderer.capabilities.maxTextureSize || 2048);
      const H = W / 2;
      const c = document.createElement("canvas");
      c.width = W;
      c.height = H;
      const g = c.getContext("2d")!;
      const proj = geo.geoEquirectangular().scale(W / (2 * Math.PI)).translate([W / 2, H / 2]);
      const gp = geo.geoPath(proj, g);
      g.fillStyle = PAL.ocean;
      g.fillRect(0, 0, W, H);
      g.strokeStyle = "rgba(255,255,255,.08)";
      g.lineWidth = 1.5;
      g.beginPath();
      gp(geo.geoGraticule10());
      g.stroke();
      countries.forEach((f) => {
        g.beginPath();
        gp(f);
        g.fillStyle = PAL.land;
        g.fill();
        g.strokeStyle = "rgba(255,255,255,.18)";
        g.lineWidth = 1;
        g.stroke();
      });
      const vn = countries.find((f) => String(f.id) === "704");
      if (vn) {
        g.save();
        g.shadowColor = PAL.vn;
        g.shadowBlur = 30;
        g.beginPath();
        gp(vn);
        g.fillStyle = PAL.vn;
        g.fill();
        g.restore();
        g.beginPath();
        gp(vn);
        g.strokeStyle = "#fff6dc";
        g.lineWidth = 4;
        g.stroke();
      }
      const tex = canvasTexture(c);
      tex.anisotropy = 8;
      const R = 9;
      const earth = new T.Group();
      const globe = new T.Mesh(
        new T.SphereGeometry(R, 96, 96),
        new T.MeshStandardMaterial({ map: tex, roughness: 0.9, metalness: 0, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: PAL.pastel ? 0.35 : 0.22 })
      );
      const atm = atmosphere(R * 1.18, PAL.pastel ? 0xcdbaf0 : 0x7cc9d6, 0.72, 1.8, this.BL, 64);
      const ll = (lat: number, lon: number, r: number) => {
        const phi = ((lon + 180) / 360) * Math.PI * 2;
        const th = ((90 - lat) / 180) * Math.PI;
        return new T.Vector3(-r * Math.cos(phi) * Math.sin(th), r * Math.cos(th), r * Math.sin(phi) * Math.sin(th));
      };
      const n = ll(10.03, 105.77, 1).normalize(); // Can Tho
      const pin = new T.Group();
      pin.position.copy(n.clone().multiplyScalar(R));
      pin.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), n);
      const beam = new T.Mesh(
        new T.CylinderGeometry(0.05, 0.12, 6, 12, 1, true),
        new T.MeshBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.7, blending: this.BL, depthWrite: false })
      );
      beam.position.y = 3;
      const head = new T.Mesh(new T.SphereGeometry(0.28, 24, 24), new T.MeshBasicMaterial({ color: 0xffe9b0 }));
      head.position.y = 6;
      const pulse = new T.Mesh(
        new T.RingGeometry(0.3, 0.42, 48),
        new T.MeshBasicMaterial({ color: 0xffd27a, transparent: true, side: T.DoubleSide, depthWrite: false })
      );
      pulse.rotation.x = -Math.PI / 2;
      pulse.position.y = 0.04;
      const lc = document.createElement("canvas");
      lc.width = 512;
      lc.height = 160;
      const lg = lc.getContext("2d")!;
      lg.fillStyle = "rgba(8,12,20,.78)";
      lg.beginPath();
      if (lg.roundRect) lg.roundRect(4, 4, 504, 152, 28);
      else lg.rect(4, 4, 504, 152);
      lg.fill();
      lg.strokeStyle = "rgba(255,210,122,.6)";
      lg.lineWidth = 3;
      lg.stroke();
      lg.fillStyle = "#ffd27a";
      lg.font = "600 54px 'Bricolage Grotesque', sans-serif";
      lg.fillText(this.opts.lang === "vi" ? "Cần Thơ" : "Can Tho", 34, 74);
      lg.fillStyle = "#e8edf3";
      lg.font = "400 30px 'Be Vietnam Pro', sans-serif";
      lg.fillText(this.opts.lang === "vi" ? "Nhóm tác giả M-AIDA" : "M-AIDA author team", 34, 124);
      const label = new T.Sprite(new T.SpriteMaterial({ map: canvasTexture(lc), transparent: true, depthTest: false }));
      label.scale.set(6.4, 2, 1);
      label.position.y = 8.2;
      pin.add(beam, head, pulse, label);
      // the two authors above the pin, each in a gold ring
      (this.opts.authorPhotos ?? []).slice(0, 2).forEach((src, i) => {
        const im = new Image();
        im.onload = () => {
          if (built !== this.built) return;
          const cc = document.createElement("canvas");
          cc.width = cc.height = 256;
          const cg = cc.getContext("2d")!;
          cg.save();
          cg.beginPath();
          cg.arc(128, 128, 116, 0, Math.PI * 2);
          cg.clip();
          cg.drawImage(im, 0, 0, 256, 256);
          cg.restore();
          cg.lineWidth = 10;
          cg.strokeStyle = "#ffd27a";
          cg.beginPath();
          cg.arc(128, 128, 118, 0, Math.PI * 2);
          cg.stroke();
          const sp = new T.Sprite(new T.SpriteMaterial({ map: canvasTexture(cc), transparent: true, depthTest: false }));
          sp.scale.set(2.6, 2.6, 1);
          sp.position.set(i ? 2.2 : -2.2, 11.4, 0);
          pin.add(sp);
          this.kick();
        };
        im.src = src;
      });
      const spin = new T.Group();
      spin.add(globe, pin);
      earth.add(spin, atm);
      const ep = EARTH_AT;
      const base = path.getPointAt(Math.min(0.99, ep + 0.02));
      const tan = path.getTangentAt(Math.min(0.99, ep + 0.02));
      const side = new T.Vector3().crossVectors(tan, new T.Vector3(0, 1, 0)).normalize();
      earth.position
        .copy(base)
        .add(side.multiplyScalar(this.mobile ? -6 : -16))
        .add(tan.clone().multiplyScalar(14))
        .add(new T.Vector3(0, -3, 0));
      const toCam = path.getPointAt(ep).clone().sub(earth.position).normalize();
      spin.quaternion.setFromUnitVectors(n, toCam);
      this.spinQ = spin.quaternion.clone();
      scene.add(earth);
      this.earth = earth;
      this.earthSpin = spin;
      this.earthPulse = pulse;
      this.kick();
    } catch (err) {
      console.warn("M-AIDA cosmos: Earth unavailable", err);
    }
  }

  // ---- frame -------------------------------------------------------------

  private warned = false;

  /** One frame; a failure is reported once and never stops the app. */
  private safeFrame(dt: number) {
    try {
      this.frame(dt);
    } catch (err) {
      if (!this.warned) console.warn("M-AIDA cosmos frame failed:", err);
      this.warned = true;
    }
  }

  private frame(dt: number) {
    const renderer = this.renderer;
    const scene = this.scene;
    const cam = this.cam;
    const path = this.path;
    if (!renderer || !scene || !cam || !path || !this.galaxy || !this.stars || !this.core) return;
    const still = this.opts.reduceMotion;
    const el = still ? 12 : (this.elapsed += dt);
    const prev = this.cur;
    if (still) this.cur = this.target;
    else this.cur += (this.target - this.cur) * Math.min(1, dt * 3);
    const vel = still ? 0 : (Math.abs(this.cur - prev) / Math.max(dt, 1e-3)) * 0.016;
    this.vs += (vel - this.vs) * Math.min(1, still ? 1 : dt * 6);
    const p = Math.min(0.999, this.cur);
    cam.position.copy(path.getPointAt(p));
    if (!still) {
      cam.position.x += this.mouse.x * 6;
      cam.position.y -= this.mouse.y * 4;
    }
    // look ahead along the path, towards the galaxy core early and the constellation late
    const lk = this.lk.copy(path.getPointAt(Math.min(0.999, p + 0.06)));
    const toCore = Math.max(0, 1 - p / 0.25);
    const toCons = Math.min(1, Math.max(0, (p - 0.72) / 0.14));
    lk.lerp(new THREE.Vector3(0, 0, 0), toCore * 0.85);
    lk.lerp(new THREE.Vector3(0, 12, FZ), toCons);
    if (this.earth && this.earthSpin && this.earthPulse) {
      const d = Math.abs(p - EARTH_AT);
      const w = Math.max(0, 1 - d / 0.07);
      const ww = w * w * (3 - 2 * w);
      lk.lerp(this.earth.position, ww * 0.9);
      this.earthSpin.quaternion.copy(this.spinQ);
      this.earthSpin.rotateY(Math.sin(el * 0.2) * 0.25 * (1 - ww));
      const k = (el * 0.8) % 1;
      this.earthPulse.scale.setScalar(1 + k * 6);
      (this.earthPulse.material as THREE.MeshBasicMaterial).opacity = 1 - k;
    }
    if (still) this.look.copy(lk);
    else this.look.lerp(lk, Math.min(1, dt * 4));
    cam.lookAt(this.look);
    if (!still) {
      cam.rotateZ(this.mouse.x * 0.08 + Math.sin(el * 0.3) * this.vs * 6);
      const fov = 55 + Math.min(18, this.vs * 900);
      if (Math.abs(cam.fov - fov) > 0.05) {
        cam.fov += (fov - cam.fov) * Math.min(1, dt * 5);
        cam.updateProjectionMatrix();
      }
    }
    this.updateWarp(still ? 0 : this.vs, dt);
    if (still) {
      this.galaxy.rotation.y = 0.4;
    } else {
      this.galaxy.rotation.y += dt * 0.04;
      this.stars.rotation.y += dt * 0.004;
    }
    (this.core.material as THREE.SpriteMaterial).opacity = 0.85 + Math.sin(el * 1.5) * 0.15;
    this.planets.forEach((pl, i) => {
      if (still) pl.m.rotation.y = i * 0.9;
      else {
        pl.m.rotation.y += dt * (0.2 + i * 0.05);
        pl.ring.rotation.z += dt * 0.1;
        pl.g.position.y += Math.sin(el + i) * 0.004;
      }
      const ma = el * 0.6 + pl.mph;
      pl.moon.position.set(Math.cos(ma) * pl.mr, Math.sin(ma * 0.7) * 0.8, Math.sin(ma) * pl.mr);
    });
    this.nebulae.forEach((n) => {
      const mat = n.sp.material as THREE.SpriteMaterial;
      if (!still) mat.rotation += dt * 0.01 * (n.ph % 2 ? 1 : -1);
      mat.opacity = 0.26 + Math.sin(el * 0.4 + n.ph) * 0.06;
    });
    this.pulse.forEach((q) => {
      const k = q.base * (1 + Math.sin(el * 2 + q.ph) * 0.18);
      q.s.scale.set(k, k, 1);
    });
    this.flowData(el);
    this.updateComets(el);
    if (this.cons) this.cons.rotation.y = Math.sin(el * 0.25) * 0.12;
    this.flowRivers(el);
    renderer.render(scene, cam);
  }
}

/**
 * M-AIDA signature planets (design package "M-AIDA Cloud Cosmos", 04/10/2026,
 * `maida-planets.js`), ported to a module for the Cosmos look of the app.
 *
 * Six planets, one per step of the workflow (Parse, Identify, Convert,
 * Evidence, Verify, Lock). Each surface carries the nine branches of the
 * Mekong (Cuu Long) and a band of the step's glyph; each ring carries Dong Son
 * drum motifs and the authors' signature. Every pattern comes from a seed
 * hashed from the authors' identifiers, so the planets look the same on every
 * screen. A hidden mark (low bit of the red channel) can be read back with
 * verifyMark(canvas).
 *
 * Changes from the design file (05/10/2026):
 * - No domain lock: M-AIDA is AGPL-3.0, and the internal trial runs on a new
 *   trycloudflare.com address every time, so the planets never turn grey.
 * - The visible ring text leaves out the Zenodo DOI until the archive record
 *   is checked (…516 in the design, …517 in earlier notes). The seed string is
 *   unchanged, so the patterns match the design exactly.
 * - Colours are worked out in sRGB, as three.js r149 did in the design, and
 *   every canvas texture is tagged sRGB for the colour-managed r184 renderer.
 */

import * as THREE from "three";

const ID =
  "M-AIDA|Do T.H.|Phan A.T.|ORCID 0000-0002-7711-2487|ORCID 0000-0003-0667-3137|DOI 10.5281/zenodo.21282516|Can Tho·Mekong Delta|2026";
export const STEPS = ["PARSE", "IDENTIFY", "CONVERT", "EVIDENCE", "VERIFY", "LOCK"] as const;
const SIGN = "M-AIDA · ĐỖ THÙY HƯƠNG & PHAN ANH TÚ · CẦN THƠ · MEKONG DELTA · ";

function hash(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}
const ROOT = hash(ID);

/** Deterministic RNG per planet (same constants as the design file). */
export function rng(seed: number): () => number {
  let a = (ROOT ^ Math.imul(seed + 1, 2654435761)) >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Shift a colour in sRGB HSL space and return a CSS hex string. */
export function shiftHex(base: THREE.Color, dh: number, ds: number, dl: number): string {
  const hsl = { h: 0, s: 0, l: 0 };
  base.getHSL(hsl, THREE.SRGBColorSpace);
  const c = new THREE.Color().setHSL(hsl.h + dh, hsl.s + ds, hsl.l + dl, THREE.SRGBColorSpace);
  return "#" + c.getHexString(THREE.SRGBColorSpace);
}

/** Canvas texture tagged sRGB (canvas pixels are sRGB). */
export function canvasTexture(c: HTMLCanvasElement): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function stamp(g: CanvasRenderingContext2D, w: number, h: number, seed: number) {
  const bytes = new TextEncoder().encode("MAIDA" + String.fromCharCode(seed + 48) + ID);
  const n = bytes.length;
  const bits: number[] = [];
  for (let k = 15; k >= 0; k--) bits.push((n >> k) & 1);
  bytes.forEach((b) => {
    for (let k = 7; k >= 0; k--) bits.push((b >> k) & 1);
  });
  const rows = Math.ceil(bits.length / w);
  const y0 = Math.floor(h * 0.62);
  const img = g.getImageData(0, y0, w, rows);
  const d = img.data;
  for (let i = 0; i < bits.length; i++) d[i * 4] = (d[i * 4] & 0xfe) | bits[i];
  g.putImageData(img, 0, y0);
}

/** Read the hidden mark back from a planet surface canvas (null when absent). */
export function verifyMark(canvas: HTMLCanvasElement): string | null {
  const g = canvas.getContext("2d");
  if (!g) return null;
  const w = canvas.width;
  const y0 = Math.floor(canvas.height * 0.62);
  const d = g.getImageData(0, y0, w, 8).data;
  const bit = (i: number) => d[i * 4] & 1;
  let n = 0;
  for (let i = 0; i < 16; i++) n = (n << 1) | bit(i);
  if (n <= 0 || n > 400) return null;
  const out = new Uint8Array(n);
  for (let j = 0; j < n; j++) {
    let b = 0;
    for (let k = 0; k < 8; k++) b = (b << 1) | bit(16 + j * 8 + k);
    out[j] = b;
  }
  const s = new TextDecoder().decode(out);
  return s.startsWith("MAIDA") ? s : null;
}

function glyph(g: CanvasRenderingContext2D, step: number, x: number, y: number, s: number, ink: string) {
  g.save();
  g.translate(x, y);
  g.strokeStyle = ink;
  g.fillStyle = ink;
  g.lineWidth = Math.max(1.4, s * 0.14);
  g.lineCap = "round";
  g.lineJoin = "round";
  g.beginPath();
  if (step === 0) {
    for (let k = 0; k < 4; k++) {
      g.moveTo(-s * 0.5, -s * 0.45 + k * s * 0.3);
      g.lineTo(s * (k === 3 ? 0.1 : 0.5), -s * 0.45 + k * s * 0.3);
    }
    g.stroke();
  } else if (step === 1) {
    g.arc(0, 0, s * 0.42, 0, 7);
    g.moveTo(-s * 0.7, 0);
    g.lineTo(-s * 0.2, 0);
    g.moveTo(s * 0.2, 0);
    g.lineTo(s * 0.7, 0);
    g.moveTo(0, -s * 0.7);
    g.lineTo(0, -s * 0.2);
    g.moveTo(0, s * 0.2);
    g.lineTo(0, s * 0.7);
    g.stroke();
  } else if (step === 2) {
    g.font = "italic 700 " + Math.round(s * 1.15) + "px Georgia, serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText("r", 0, 0);
  } else if (step === 3) {
    g.font = "700 " + Math.round(s * 1.4) + "px Georgia, serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText("“", 0, s * 0.25);
  } else if (step === 4) {
    g.moveTo(-s * 0.45, 0);
    g.lineTo(-s * 0.1, s * 0.38);
    g.lineTo(s * 0.5, -s * 0.4);
    g.stroke();
  } else {
    g.strokeRect(-s * 0.4, -s * 0.05, s * 0.8, s * 0.6);
    g.moveTo(-s * 0.24, -s * 0.05);
    g.arc(0, -s * 0.2, s * 0.24, Math.PI, 0);
    g.lineTo(s * 0.24, -s * 0.05);
    g.stroke();
  }
  g.restore();
}

/** Surface texture of planet i (one workflow step). */
export function planetSurface(hex: number, i: number, mobile: boolean): THREE.CanvasTexture {
  const W = mobile ? 512 : 1024;
  const H = W / 2;
  const k = W / 1024;
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const g = c.getContext("2d")!;
  const r = rng(i * 7 + 3);
  const base = new THREE.Color(hex);
  const col = (dh: number, ds: number, dl: number) => shiftHex(base, dh, ds, dl);
  g.fillStyle = col(0, 0, 0);
  g.fillRect(0, 0, W, H);
  for (let b = 0; b < 18; b++) {
    const y = r() * H;
    const h = (8 + r() * 46) * k;
    const l = (r() - 0.5) * 0.3;
    const f = (0.008 + r() * 0.02) / k;
    const ph = r() * 6;
    g.globalAlpha = 0.5;
    g.fillStyle = col((r() - 0.5) * 0.04, -0.05, l);
    g.beginPath();
    g.moveTo(0, y);
    for (let x = 0; x <= W; x += 16 * k) g.lineTo(x, y + Math.sin(x * f + ph) * 9 * k);
    g.lineTo(W, y + h);
    g.lineTo(0, y + h);
    g.fill();
  }
  // Cuu Long: nine river branches carved on the surface
  const sx = r() * W;
  const sy = H * (0.18 + r() * 0.2);
  for (let n = 0; n < 9; n++) {
    let x = sx;
    let y = sy;
    let a = Math.PI / 2 + (n - 4) * 0.16 + (r() - 0.5) * 0.08;
    const pts: [number, number][] = [[x, y]];
    for (let s = 0; s < 46; s++) {
      a += (r() - 0.5) * 0.22;
      x += Math.cos(a) * 7 * k;
      y += Math.sin(a) * 6 * k;
      pts.push([x, y]);
    }
    const strokes: [string, number, number][] = [
      [col(0, -0.1, -0.22), 4.2 * k, 0.45],
      [col(0.02, 0.05, 0.2), 1.3 * k, 0.55],
    ];
    strokes.forEach(([s, lw, al]) => {
      g.globalAlpha = al;
      g.strokeStyle = s;
      g.lineWidth = Math.max(0.8, lw);
      g.lineCap = "round";
      g.beginPath();
      pts.forEach(([px, py], j) => {
        const wx = ((px % W) + W) % W;
        if (j) g.lineTo(wx, py);
        else g.moveTo(wx, py);
      });
      g.stroke();
    });
  }
  // equator band: the glyph of this workflow step
  g.globalAlpha = 0.16;
  g.fillStyle = col(0, -0.1, -0.3);
  g.fillRect(0, H * 0.47, W, H * 0.09);
  g.globalAlpha = 0.7;
  const ink = col(0, -0.15, -0.38);
  for (let x = 32 * k; x < W; x += 64 * k) glyph(g, i, x, H * 0.515, 20 * k, ink);
  g.globalAlpha = 0.11;
  for (let n = 0; n < 5000 * k * k; n++) {
    g.fillStyle = r() > 0.5 ? "#fff" : "#000";
    g.fillRect(r() * W, r() * H, 1.5, 1.5);
  }
  g.globalAlpha = 1;
  stamp(g, W, H, i);
  const t = canvasTexture(c);
  t.wrapS = THREE.RepeatWrapping;
  t.userData = { maida: true, canvas: c };
  return t;
}

function ringTexture(hex: number, i: number, inner: number, outer: number, mobile: boolean): THREE.CanvasTexture {
  const S = mobile ? 512 : 1024;
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d")!;
  const base = new THREE.Color(hex);
  const ink = shiftHex(base, 0, 0, 0.12);
  const deep = shiftHex(base, 0, 0, -0.18);
  const C = S / 2;
  const R = (v: number) => (v / outer) * C;
  const r0 = R(inner);
  const r1 = R(outer) - 2;
  const bw = (r1 - r0) / 6;
  const rr = rng(i * 13 + 5);
  const lw = S / 1024;
  g.translate(C, C);
  g.strokeStyle = ink;
  g.fillStyle = ink;
  g.lineCap = "round";
  const circ = (rad: number, w: number, al: number) => {
    g.globalAlpha = al;
    g.lineWidth = w;
    g.beginPath();
    g.arc(0, 0, rad, 0, 7);
    g.stroke();
  };
  for (let k = 0; k <= 6; k++) circ(r0 + k * bw, (k % 3 ? 1.2 : 2.4) * lw, 0.85);
  g.globalAlpha = 0.18;
  g.fillStyle = deep;
  g.beginPath();
  g.arc(0, 0, r1, 0, 7);
  g.arc(0, 0, r0, 0, 7, true);
  g.fill();
  g.fillStyle = ink;
  // 1 · tangent circles (Dong Son)
  let m = r0 + bw * 0.5;
  let n = Math.round((2 * Math.PI * m) / (bw * 0.95));
  g.globalAlpha = 0.9;
  g.lineWidth = 1.4 * lw;
  for (let k = 0; k < n; k++) {
    const a = (k / n) * 2 * Math.PI;
    g.beginPath();
    g.arc(Math.cos(a) * m, Math.sin(a) * m, bw * 0.3, 0, 7);
    g.stroke();
    g.beginPath();
    g.arc(Math.cos(a) * m, Math.sin(a) * m, bw * 0.08, 0, 7);
    g.fill();
  }
  // 2 · saw teeth
  m = r0 + bw * 1.5;
  n = Math.round((2 * Math.PI * m) / (bw * 0.5));
  g.lineWidth = 1.6 * lw;
  g.beginPath();
  for (let k = 0; k <= n; k++) {
    const a = (k / n) * 2 * Math.PI;
    const rad = m + (k % 2 ? bw * 0.32 : -bw * 0.32);
    if (k) g.lineTo(Math.cos(a) * rad, Math.sin(a) * rad);
    else g.moveTo(Math.cos(a) * rad, Math.sin(a) * rad);
  }
  g.stroke();
  // 3 · step name and the authors' signature
  const text = STEPS[i] + " · " + SIGN;
  m = r0 + bw * 2.5;
  g.font = "600 " + Math.round(bw * 0.52) + "px 'JetBrains Mono', ui-monospace, monospace";
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.globalAlpha = 0.95;
  const chars = Array.from(text);
  const step = (bw * 0.42) / m;
  const reps = Math.max(1, Math.floor((2 * Math.PI) / (step * chars.length)));
  const list = Array.from(Array(reps).fill(text).join(""));
  const st = (2 * Math.PI) / list.length;
  list.forEach((ch, k) => {
    g.save();
    g.rotate(k * st);
    g.translate(0, -m);
    g.fillText(ch, 0, 0);
    g.restore();
  });
  // 4 · stylised Lac birds
  m = r0 + bw * 3.5;
  n = 10 + Math.floor(rr() * 6);
  g.lineWidth = 1.8 * lw;
  for (let k = 0; k < n; k++) {
    const a = (k / n) * 2 * Math.PI;
    g.save();
    g.rotate(a);
    g.translate(0, -m);
    g.beginPath();
    g.moveTo(-bw * 0.6, bw * 0.15);
    g.quadraticCurveTo(-bw * 0.1, -bw * 0.05, bw * 0.15, -bw * 0.05);
    g.lineTo(bw * 0.55, -bw * 0.32);
    g.moveTo(-bw * 0.25, bw * 0.08);
    g.lineTo(-bw * 0.05, -bw * 0.35);
    g.moveTo(bw * 0.15, -bw * 0.05);
    g.lineTo(bw * 0.05, bw * 0.3);
    g.stroke();
    g.restore();
  }
  // 5 · dotted ladder
  m = r0 + bw * 4.5;
  n = Math.round((2 * Math.PI * m) / (bw * 0.28));
  for (let k = 0; k < n; k++) {
    const a = (k / n) * 2 * Math.PI;
    g.beginPath();
    g.arc(Math.cos(a) * m, Math.sin(a) * m, bw * 0.07, 0, 7);
    g.fill();
  }
  // 6 · fourteen-point star rays moved out to the rim
  m = r0 + bw * 5.5;
  n = 14 * 4;
  g.lineWidth = 1.5 * lw;
  for (let k = 0; k < n; k++) {
    const a = (k / n) * 2 * Math.PI;
    const l = k % 4 === 0 ? bw * 0.42 : bw * 0.18;
    g.beginPath();
    g.moveTo(Math.cos(a) * (m - l), Math.sin(a) * (m - l));
    g.lineTo(Math.cos(a) * (m + l), Math.sin(a) * (m + l));
    g.stroke();
  }
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.globalAlpha = 1;
  const t = canvasTexture(c);
  t.anisotropy = 4;
  return t;
}

/** Ring of planet i with radius pr. */
export function planetRing(hex: number, i: number, pr: number, mobile: boolean): THREE.Mesh {
  const inner = pr * 1.45;
  const outer = pr * 2.3;
  return new THREE.Mesh(
    new THREE.RingGeometry(inner, outer, 160, 1),
    new THREE.MeshBasicMaterial({
      map: ringTexture(hex, i, inner, outer, mobile),
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.92,
      depthWrite: false,
    })
  );
}

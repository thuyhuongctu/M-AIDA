/**
 * Background music (8.0): the two M-AIDA songs by Đỗ Thùy Hương.
 *
 * The files ship with the app (frontend/public/audio/), so they come from the
 * same origin and the Content-Security-Policy needs no extra host. When the
 * songs are on the album site, `src` can point there instead (and Caddy's CSP
 * then needs `media-src 'self' https://thuyhuongctu.github.io`).
 *
 * Off by default: nothing is downloaded until the listener presses play, and
 * "playing" is never remembered, so a reload is always silent. Only the
 * volume is kept in this browser. One Audio object lives outside React, so
 * the music carries on from the sign-in page into the workspace.
 */

import { useSyncExternalStore } from "react";

export interface Track {
  id: string;
  title: string;
  src: string;
}

export const TRACKS: Track[] = [
  { id: "heartbeat", title: "The Heartbeat of M-AIDA", src: "/audio/heartbeat-of-maida.mp3" },
  { id: "preuves", title: "M-AIDA · Que les preuves décident", src: "/audio/maida-que-les-preuves-decident.mp3" },
];

export interface MusicState {
  playing: boolean;
  loading: boolean;
  failed: boolean;
  track: number;
  volume: number;
}

const VOLUME_KEY = "maida_music_volume";

function readVolume(): number {
  try {
    const v = Number(localStorage.getItem(VOLUME_KEY));
    return Number.isFinite(v) && v > 0 && v <= 1 ? v : 0.5;
  } catch {
    return 0.5;
  }
}

let state: MusicState = { playing: false, loading: false, failed: false, track: 0, volume: readVolume() };
let audio: HTMLAudioElement | null = null;
const listeners = new Set<() => void>();

function set(patch: Partial<MusicState>): void {
  state = { ...state, ...patch };
  listeners.forEach((fn) => fn());
}

function element(): HTMLAudioElement {
  if (audio) return audio;
  const a = new Audio();
  a.preload = "none";
  a.volume = state.volume;
  a.addEventListener("playing", () => set({ playing: true, loading: false, failed: false }));
  a.addEventListener("pause", () => set({ playing: false, loading: false }));
  a.addEventListener("waiting", () => set({ loading: true }));
  a.addEventListener("error", () => set({ playing: false, loading: false, failed: true }));
  // One song after the other, then round again.
  a.addEventListener("ended", () => choose((state.track + 1) % TRACKS.length, true));
  audio = a;
  return a;
}

export function play(): void {
  const a = element();
  if (!a.getAttribute("src")) a.src = TRACKS[state.track].src;
  set({ loading: true, failed: false });
  a.play().catch((err: unknown) => {
    // A newer play()/src change interrupted this one: not a failure.
    if (err instanceof DOMException && err.name === "AbortError") return;
    set({ playing: false, loading: false, failed: true });
  });
}

export function pause(): void {
  audio?.pause();
}

export function toggle(): void {
  if (state.playing || state.loading) pause();
  else play();
}

export function choose(index: number, autoplay = state.playing): void {
  const i = ((index % TRACKS.length) + TRACKS.length) % TRACKS.length;
  const a = element();
  a.src = TRACKS[i].src;
  set({ track: i, failed: false });
  if (autoplay) play();
}

export function setVolume(volume: number): void {
  const v = Math.min(1, Math.max(0, volume));
  if (audio) audio.volume = v;
  set({ volume: v });
  try {
    localStorage.setItem(VOLUME_KEY, String(v));
  } catch {
    /* storage unavailable: the volume lasts for this page only */
  }
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useMusic(): MusicState {
  return useSyncExternalStore(subscribe, () => state, () => state);
}

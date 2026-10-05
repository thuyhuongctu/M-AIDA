/**
 * Sign-in for M-AIDA 8.0.
 *
 * The backend tells the browser which identity mode it runs in
 * (GET /api/config). Three modes:
 *
 *   admin_key - 7.x single operator: no sign-in screen, the admin key typed in
 *               the header is sent as X-MAIDA-Admin-Key (see api.ts).
 *   supabase  - Supabase Auth in the browser (magic link or Google); the
 *               session's access token goes out as a bearer token.
 *   mock      - tests / e2e: POST /api/auth/mock-login mints a token.
 *
 * Nothing secret is stored here: the Supabase anon key is public by design
 * and the bearer token is the user's own session.
 */

import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { fetchConfig, mockLogin, registerAuth } from "./api";
import type { ClientConfig } from "./types";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}

export interface AuthState {
  mode: ClientConfig["auth_mode"];
  user: AuthUser | null;
  token: string | null;
  /** 8.0: the in-browser demo is running (demo.ts); no real account. */
  demo?: boolean;
}

type Listener = (state: AuthState) => void;

const MOCK_TOKEN_KEY = "maida_mock_token";
const MOCK_USER_KEY = "maida_mock_user";

let config: ClientConfig | null = null;
let supabase: SupabaseClient | null = null;
let state: AuthState = { mode: "admin_key", user: null, token: null };
const listeners = new Set<Listener>();

function emit(next: AuthState): void {
  state = next;
  listeners.forEach((fn) => fn(state));
}

export function getAuthState(): AuthState {
  return state;
}

export function getAccessToken(): string | null {
  return state.token;
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function userFromSession(session: Session | null): AuthUser | null {
  if (!session?.user) return null;
  const meta = (session.user.user_metadata ?? {}) as Record<string, unknown>;
  return {
    id: session.user.id,
    email: session.user.email ?? "",
    name: String(meta.full_name ?? meta.name ?? ""),
  };
}

// 8.0 demo: the sign-in state before the demo started, and what to undo when it ends.
let beforeDemo: AuthState | null = null;
let onDemoExit: (() => void) | null = null;

/** Start the in-browser demo as a signed-in visitor without an account (see demo.ts). */
export function enterDemo(user: AuthUser, onExit: () => void): void {
  if (!state.demo) beforeDemo = state;
  onDemoExit = onExit;
  emit({ mode: state.mode, user, token: null, demo: true });
}

/** End the demo: its workspace is dropped and the sign-in page comes back. */
export function leaveDemo(): void {
  if (!state.demo) return;
  const exit = onDemoExit;
  onDemoExit = null;
  exit?.();
  const back = beforeDemo ?? { mode: state.mode, user: null, token: null };
  beforeDemo = null;
  emit({ ...back, demo: false });
}

/** Load /api/config and restore any existing session. Call once at start-up. */
export async function initAuth(): Promise<ClientConfig> {
  registerAuth(getAccessToken, handleUnauthorized);
  config = await fetchConfig();
  if (config.auth_mode === "supabase") {
    const { createClient } = await import("@supabase/supabase-js");
    supabase = createClient(config.supabase_url, config.supabase_anon_key, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
    const { data } = await supabase.auth.getSession();
    emit({ mode: "supabase", user: userFromSession(data.session), token: data.session?.access_token ?? null });
    supabase.auth.onAuthStateChange((_event, session) => {
      const next: AuthState = { mode: "supabase", user: userFromSession(session), token: session?.access_token ?? null };
      if (state.demo) beforeDemo = next; // applied when the demo ends
      else emit(next);
    });
  } else if (config.auth_mode === "mock") {
    let token: string | null = null;
    let user: AuthUser | null = null;
    try {
      token = sessionStorage.getItem(MOCK_TOKEN_KEY);
      const raw = sessionStorage.getItem(MOCK_USER_KEY);
      user = raw ? (JSON.parse(raw) as AuthUser) : null;
    } catch {
      token = null;
    }
    emit({ mode: "mock", user: token ? user : null, token });
  } else {
    emit({ mode: "admin_key", user: null, token: null });
  }
  return config;
}

export async function signInWithEmail(email: string): Promise<void> {
  if (state.mode === "supabase" && supabase) {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) throw new Error(error.message);
    return;
  }
  if (state.mode === "mock") {
    const res = await mockLogin(email);
    const user: AuthUser = { id: res.user.id, email: res.user.email, name: res.user.name };
    try {
      sessionStorage.setItem(MOCK_TOKEN_KEY, res.access_token);
      sessionStorage.setItem(MOCK_USER_KEY, JSON.stringify(user));
    } catch {
      // session just won't survive a reload
    }
    emit({ mode: "mock", user, token: res.access_token });
    return;
  }
  throw new Error("Sign-in is not used in this deployment mode.");
}

export async function signInWithGoogle(): Promise<void> {
  if (state.mode !== "supabase" || !supabase) throw new Error("Google sign-in needs Supabase mode.");
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
  });
  if (error) throw new Error(error.message);
}

export async function signOut(): Promise<void> {
  if (state.demo) {
    leaveDemo();
    return;
  }
  if (state.mode === "supabase" && supabase) {
    await supabase.auth.signOut();
    emit({ mode: "supabase", user: null, token: null });
    return;
  }
  if (state.mode === "mock") {
    try {
      sessionStorage.removeItem(MOCK_TOKEN_KEY);
      sessionStorage.removeItem(MOCK_USER_KEY);
    } catch {
      // ignore
    }
    emit({ mode: "mock", user: null, token: null });
  }
}

/** Called by api.ts when the backend answers 401: the session is gone. */
export function handleUnauthorized(): void {
  if (state.mode === "mock" || state.mode === "supabase") {
    void signOut();
  }
}

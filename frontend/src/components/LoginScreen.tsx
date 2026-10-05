/**
 * LoginScreen - sign-in for the multi-user (cloud) modes.
 *
 * Supabase mode: magic link by e-mail or Google, or e-mail + password when the
 * operator issues the accounts (internal trial). Mock mode (tests): any
 * e-mail signs in at once. The screen is never shown in admin_key mode.
 * Two columns: the brand block (promise, illustration of the two authors,
 * contact) and the form. The illustration is the only character artwork on a
 * working route besides the contact avatars (decision 03/10/2026: characters
 * on the front, not at the workbench).
 */

import React, { useState } from "react";
import { isNotInvited } from "../api";
import { getLoginMethod, signInWithEmail, signInWithGoogle, signInWithPassword } from "../auth";
import { startDemo } from "../demo";
import { useI18n } from "../i18n";
import ContactDialog from "./ContactDialog";
import { Logo } from "./Logo";
import Logo3D from "./Logo3D";
import MusicPlayer from "./MusicPlayer";
import WorldClocks from "./WorldClocks";
import VnMark from "./VnMark";
import sceneLogin from "../assets/people/scene-login.webp";
import sceneMagnifier from "../assets/people/scene-magnifier.webp";
import sceneHuongMaida from "../assets/people/scene-huong-maida.webp";
import type { StringKey } from "../i18n";

/** Illustrations that take turns on the sign-in page (one per visit). */
const SCENES: { src: string; alt: StringKey }[] = [
  { src: sceneLogin, alt: "login_scene_alt" },
  { src: sceneMagnifier, alt: "login_scene_alt_magnifier" },
  { src: sceneHuongMaida, alt: "login_scene_alt_maida" },
];

interface LoginScreenProps {
  mode: "supabase" | "mock";
  version: string;
}

export default function LoginScreen({ mode, version }: LoginScreenProps) {
  const { t, lang, setLang } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Internal trial (login_method = "password"): accounts are made by the operator, no e-mail is sent.
  const usePassword = mode === "supabase" && getLoginMethod() === "password";
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const [scene] = useState(() => SCENES[Math.floor(Math.random() * SCENES.length)]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      if (usePassword) {
        await signInWithPassword(value, password);
      } else {
        await signInWithEmail(value);
        if (mode === "supabase") setSent(true);
      }
    } catch (err: unknown) {
      const bad = (err as { code?: string } | null)?.code === "bad_password";
      setError(
        bad ? t("login_bad_password")
          : isNotInvited(err) ? t("not_invited_login")
          : err instanceof Error ? err.message : t("error_generic"),
      );
    } finally {
      setBusy(false);
    }
  };

  const google = async () => {
    setBusy(true);
    setError(null);
    try {
      await signInWithGoogle();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
      setBusy(false);
    }
  };

  return (
    <div className="login" data-testid="login-card">
      <aside className="login-brand">
        <div className="login-brand-top">
          <Logo />
        </div>
        <div className="login-brand-mid">
          <Logo3D framing={1.12} className="logo3d-login" />
          <p className="login-claim">
            {lang === "vi"
              ? "Máy đề xuất kèm câu trích nguyên văn. Người kiểm chứng và khóa."
              : "The machine proposes, with the sentence it read. A person verifies and locks."}
          </p>
          <figure className="login-scene">
            <img src={scene.src} alt={t(scene.alt)} width={688} height={384} data-testid="login-scene" />
          </figure>
        </div>
        <p className="login-brand-foot">
          {t("project_line")} ·{" "}
          <button type="button" className="link-btn" onClick={() => setContactOpen(true)} data-testid="contact-open">
            {t("contact_open")}
          </button>
        </p>
        <ContactDialog open={contactOpen} onClose={() => setContactOpen(false)} />
      </aside>

      <section className="login-side">
        {/* the map moved behind the form when the illustration took the brand column */}
        <VnMark variant="hero" />
        <div className="login-topbar">
          <MusicPlayer />
          <button type="button" className={`seg ${lang === "en" ? "seg-on" : ""}`} onClick={() => setLang("en")}>EN</button>
          <button type="button" className={`seg ${lang === "vi" ? "seg-on" : ""}`} onClick={() => setLang("vi")}>VI</button>
        </div>
        <div className="login-form-wrap">
          <span className="eyebrow mono">M-AIDA {version} · closed beta</span>
          <h2 className="login-title">{t("login_title")}</h2>
          <p className="login-intro">{t("login_intro")}</p>

          {sent ? (
            <div className="note note-ok">
              <p>{t("login_link_sent")}</p>
            </div>
          ) : (
            <form onSubmit={submit} className="login-form">
              <label className="form-label" htmlFor="login-email">{t("login_email")}</label>
              <input
                id="login-email"
                className="form-input"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@university.edu"
              />
              {usePassword && (
                <>
                  <label className="form-label" htmlFor="login-password">{t("login_password")}</label>
                  <input
                    id="login-password"
                    className="form-input"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    data-testid="login-password"
                  />
                  <p className="hint-text">{t("login_password_hint")}</p>
                </>
              )}
              {mode === "mock" && <p className="hint-text">{t("login_mock_hint")}</p>}
              <button type="submit" className="btn btn-primary login-btn" disabled={busy}>
                {busy ? t("loading")
                  : mode === "mock" ? t("login_mock_button")
                  : usePassword ? t("login_password_button")
                  : t("login_send_link")}
              </button>
            </form>
          )}

          {mode === "supabase" && !sent && !usePassword && (
            <>
              <div className="login-divider"><span>{t("login_or")}</span></div>
              <button type="button" className="btn btn-ghost login-btn" onClick={google} disabled={busy}>
                <span className="g-mark" aria-hidden="true">G</span> {t("login_google")}
              </button>
            </>
          )}

          {error && <p className="error-message">{error}</p>}

          <div className="login-demo">
            <button type="button" className="btn btn-secondary login-btn" onClick={() => startDemo(version)} data-testid="demo-start">
              {t("demo_try")}
            </button>
            <p className="hint-text">{t("demo_try_hint")}</p>
          </div>

          <p className="login-legal">
            {t("login_legal_prefix")}{" "}
            <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer">{t("legal_terms")}</a>
            {" "}{t("login_legal_and")}{" "}
            <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer">{t("legal_privacy")}</a>.
            {" "}
            {usePassword
              ? lang === "vi"
                ? "Tài khoản do quản trị viên cấp cho đợt chạy thử nội bộ."
                : "Accounts are issued by the administrator for the internal trial."
              : lang === "vi"
                ? "Không cần mật khẩu; lần đăng nhập đầu tạo tài khoản với 10 tín dụng beta."
                : "No password. The first sign-in creates your account with 10 beta credits."}
          </p>
        </div>
        <WorldClocks variant="strip" />
      </section>
    </div>
  );
}

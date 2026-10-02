/**
 * LoginScreen - sign-in for the multi-user (cloud) modes.
 *
 * Supabase mode: magic link by e-mail or Google. Mock mode (tests): any
 * e-mail signs in at once. The screen is never shown in admin_key mode.
 */

import React, { useState } from "react";
import { signInWithEmail, signInWithGoogle } from "../auth";
import { useI18n } from "../i18n";

interface LoginScreenProps {
  mode: "supabase" | "mock";
  version: string;
}

export default function LoginScreen({ mode, version }: LoginScreenProps) {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      await signInWithEmail(value);
      if (mode === "supabase") setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
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
    <div className="login-wrap">
      <div className="login-card" data-testid="login-card">
        <h2 className="login-title">{t("login_title")}</h2>
        <p className="login-intro">{t("login_intro")}</p>

        {sent ? (
          <div className="alert alert-success">
            <p>{t("login_link_sent")}</p>
          </div>
        ) : (
          <form onSubmit={submit} className="login-form">
            <label className="form-label" htmlFor="login-email">
              {t("login_email")}
            </label>
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
            {mode === "mock" && <p className="hint-text">{t("login_mock_hint")}</p>}
            <button type="submit" className="btn btn-primary login-btn" disabled={busy}>
              {busy ? t("loading") : mode === "mock" ? t("login_mock_button") : t("login_send_link")}
            </button>
          </form>
        )}

        {mode === "supabase" && !sent && (
          <>
            <div className="login-divider">
              <span>{t("login_or")}</span>
            </div>
            <button type="button" className="btn btn-ghost login-btn" onClick={google} disabled={busy}>
              {t("login_google")}
            </button>
          </>
        )}

        {error && <p className="error-message">{error}</p>}
        <p className="login-legal">
          {t("login_legal_prefix")}{" "}
          <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer">{t("legal_terms")}</a>
          {" "}{t("login_legal_and")}{" "}
          <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer">{t("legal_privacy")}</a>.
        </p>
        <p className="login-foot">M-AIDA v{version} · Do Thuy Huong &amp; Phan Anh Tu · Can Tho University</p>
      </div>
    </div>
  );
}

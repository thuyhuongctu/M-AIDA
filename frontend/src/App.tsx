/**
 * M-AIDA - Root application component. The version shown in the header and
 * footer comes from /api/health (single source: backend APP_VERSION).
 *
 * 8.0 layout:
 *   - admin_key mode (single operator, 7.x behaviour): Extract | Verify & Lock
 *     tabs plus the admin-key field in the header.
 *   - supabase / mock modes (many users): sign-in screen, then
 *     Dashboard | Extract | Verify & Lock | Account.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { fetchHealth, getAdminKey, setAdminKey } from "./api";
import { AuthState, getAuthState, initAuth, subscribe } from "./auth";
import AccountPanel from "./components/AccountPanel";
import Dashboard from "./components/Dashboard";
import ExportPanel from "./components/ExportPanel";
import ExtractionPanel from "./components/ExtractionPanel";
import LoginScreen from "./components/LoginScreen";
import StatusBanner from "./components/StatusBanner";
import VerificationDashboard from "./components/VerificationDashboard";
import { I18nContext, Lang, readLang, storeLang, translate } from "./i18n";
import { ClientConfig, StudyDatabaseEntry } from "./types";
import "./index.css";

type Tab = "dashboard" | "extract" | "verify" | "account";

export default function App() {
  // Language (8.0): English by default, Vietnamese on request; remembered per browser.
  const [lang, setLangState] = useState<Lang>(readLang);
  const i18n = useMemo(
    () => ({
      lang,
      t: (key: Parameters<typeof translate>[1]) => translate(lang, key),
      setLang: (next: Lang) => {
        storeLang(next);
        setLangState(next);
      },
    }),
    [lang]
  );

  // Identity (8.0): resolved once from /api/config, then kept in sync with auth.ts.
  const [config, setConfig] = useState<ClientConfig | null>(null);
  const [auth, setAuth] = useState<AuthState>(getAuthState);
  const [bootError, setBootError] = useState<string | null>(null);
  useEffect(() => {
    const unsubscribe = subscribe(setAuth);
    initAuth()
      .then((cfg) => {
        setConfig(cfg);
        setAuth(getAuthState());
      })
      .catch((err: unknown) => setBootError(err instanceof Error ? err.message : String(err)));
    return unsubscribe;
  }, []);

  const cloud = config?.auth_mode === "supabase" || config?.auth_mode === "mock";

  // Count new extractions so the Verify tab can show an attention badge, and
  // bump a key so the dashboard/account panels reload after a change.
  const [extractionCount, setExtractionCount] = useState(0);

  const [activeTab, setActiveTab] = useState<Tab>("extract");
  // Every (re-)sign-in lands on the dashboard; the per-session counters reset too.
  const userId = auth.user?.id ?? null;
  useEffect(() => {
    if (cloud) {
      setActiveTab("dashboard");
      setExtractionCount(0);
    }
  }, [cloud, userId]);

  const [refreshKey, setRefreshKey] = useState(0);
  // Version label: read once from /api/health so the UI can never disagree
  // with the backend (7.2.1). Falls back to "?" while unreachable.
  const [version, setVersion] = useState<string>("?");
  useEffect(() => {
    fetchHealth()
      .then((h) => setVersion(h.version))
      .catch(() => setVersion("?"));
  }, []);

  // 7.2.2: the PI's admin key, kept only in this browser (see api.ts). Every
  // extract/verify/lock/Notion-sync call fails with 401 until this is set to
  // the value printed in the backend's startup log / MAIDA_ADMIN_KEY. Only
  // shown in admin_key mode.
  const [adminKey, setAdminKeyField] = useState<string>(getAdminKey);
  const handleAdminKeyChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setAdminKeyField(value);
      setAdminKey(value);
    },
    []
  );

  const handleExtracted = useCallback((_entry: StudyDatabaseEntry) => {
    setExtractionCount((c) => c + 1);
    setRefreshKey((k) => k + 1);
  }, []);

  const switchToVerify = useCallback(() => {
    setActiveTab("verify");
  }, []);

  const t = i18n.t;

  const header = (
    <header className="app-header">
      <div className="header-brand">
        <h1 className="app-title">M-AIDA</h1>
        <span className="app-version">v{version}</span>
      </div>
      <p className="app-subtitle">
        Meta-Analysis Intelligent Data Assistant - Internationalization &amp; Performance
      </p>
      <div className="header-right">
        {config?.auth_mode === "admin_key" && (
          <div className="admin-key-field">
            <label htmlFor="admin-key-input">Admin key</label>
            <input
              id="admin-key-input"
              type="password"
              autoComplete="off"
              placeholder="required to extract / verify / lock"
              value={adminKey}
              onChange={handleAdminKeyChange}
            />
          </div>
        )}
        {cloud && auth.user && (
          <span className="header-user" data-testid="header-user">
            {t("signed_in_as")} <strong>{auth.user.email}</strong>
          </span>
        )}
        <button
          type="button"
          className="lang-toggle"
          onClick={() => i18n.setLang(lang === "en" ? "vi" : "en")}
          aria-label="Switch language"
        >
          {t("lang_switch")}
        </button>
      </div>
    </header>
  );

  const footer = (
    <footer className="app-footer">
      <p>
        M-AIDA v{version} · PhD Dissertation Research Tool · Asia-Pacific I&rarr;P
        Meta-Analysis
      </p>
      <p>
        Do Thuy Huong &amp;{" "}
        <a href="https://patueconomics.com/" target="_blank" rel="noopener noreferrer">
          Phan Anh Tu
        </a>{" "}
        · School of Economics, Can Tho University
      </p>
      {cloud && (
        <p className="footer-legal">
          <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer">{t("legal_terms")}</a>
          {" · "}
          <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer">{t("legal_privacy")}</a>
          {" · "}
          <a href="https://github.com/thuyhuongctu/M-AIDA" target="_blank" rel="noopener noreferrer">AGPL-3.0</a>
        </p>
      )}
    </footer>
  );

  let body: React.ReactNode;
  if (bootError) {
    body = (
      <main className="app-main">
        <div className="alert alert-warn">
          <p>Cannot reach the M-AIDA backend: {bootError}</p>
        </div>
      </main>
    );
  } else if (!config) {
    body = (
      <main className="app-main">
        <p className="loading-text">{t("loading")}</p>
      </main>
    );
  } else if (cloud && !auth.user) {
    body = (
      <main className="app-main">
        <LoginScreen mode={config.auth_mode as "supabase" | "mock"} version={version} />
      </main>
    );
  } else {
    body = (
      <>
        <StatusBanner />
        <nav className="tab-nav" role="tablist">
          {cloud && (
            <button role="tab" aria-selected={activeTab === "dashboard"}
                    className={`tab-btn ${activeTab === "dashboard" ? "active" : ""}`}
                    onClick={() => setActiveTab("dashboard")} data-testid="tab-dashboard">
              {t("nav_dashboard")}
            </button>
          )}
          <button role="tab" aria-selected={activeTab === "extract"}
                  className={`tab-btn ${activeTab === "extract" ? "active" : ""}`}
                  onClick={() => setActiveTab("extract")} data-testid="tab-extract">
            {t("nav_extract")}
          </button>
          <button role="tab" aria-selected={activeTab === "verify"}
                  className={`tab-btn ${activeTab === "verify" ? "active" : ""}`}
                  onClick={() => setActiveTab("verify")} data-testid="tab-verify">
            {t("nav_verify")}
            {extractionCount > 0 && <span className="tab-badge">{extractionCount}</span>}
          </button>
          {cloud && (
            <button role="tab" aria-selected={activeTab === "account"}
                    className={`tab-btn ${activeTab === "account" ? "active" : ""}`}
                    onClick={() => setActiveTab("account")} data-testid="tab-account">
              {t("nav_account")}
            </button>
          )}
        </nav>

        <main className="app-main">
          {activeTab === "dashboard" && cloud && (
            <div className="tab-content">
              <Dashboard
                refreshKey={refreshKey}
                onNewExtraction={() => setActiveTab("extract")}
                onOpenStudy={() => setActiveTab("verify")}
              />
            </div>
          )}

          {activeTab === "extract" && (
            <div className="tab-content">
              <ExtractionPanel onExtracted={handleExtracted} cloud={cloud} />
              {extractionCount > 0 && (
                <div className="extraction-prompt">
                  <p>
                    {extractionCount} paper{extractionCount !== 1 ? "s" : ""} extracted
                    this session.
                  </p>
                  <button className="btn btn-link" onClick={switchToVerify}>
                    Go to Verify &amp; Lock
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === "verify" && (
            <div className="tab-content verify-tab">
              <VerificationDashboard />
              <ExportPanel />
            </div>
          )}

          {activeTab === "account" && cloud && (
            <div className="tab-content">
              <AccountPanel refreshKey={refreshKey} />
            </div>
          )}
        </main>
      </>
    );
  }

  return (
    <I18nContext.Provider value={i18n}>
      <div className="app">
        {header}
        {body}
        {footer}
      </div>
    </I18nContext.Provider>
  );
}

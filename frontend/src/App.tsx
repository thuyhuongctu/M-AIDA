/**
 * M-AIDA - Root application component. The version shown in the header and
 * footer comes from /api/health (single source: backend APP_VERSION).
 *
 * 8.0 layout:
 *   - admin_key mode (single operator, 7.x behaviour): Extract | Verify & Lock
 *     | Dataset, plus the admin-key field in the header.
 *   - supabase / mock modes (many users): sign-in screen, then
 *     Dashboard | Extract | Verify & Lock | Dataset | Account.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchHealth, fetchMe, getAdminKey, isNotInvited, setAdminKey } from "./api";
import { AuthState, getAuthState, initAuth, signOut, subscribe } from "./auth";
import AccountPanel from "./components/AccountPanel";
import BillingPanel, { readPaymentReturn, type PaymentReturn } from "./components/BillingPanel";
import ContactDialog from "./components/ContactDialog";
import Logo3DDialog from "./components/Logo3DDialog";
import Dashboard from "./components/Dashboard";
import DatasetPanel from "./components/DatasetPanel";
import ExtractionPanel from "./components/ExtractionPanel";
import LoginScreen from "./components/LoginScreen";
import { Logo } from "./components/Logo";
import VnMark from "./components/VnMark";
import ReviewScreen from "./components/ReviewScreen";
import StatusPill from "./components/StatusPill";
import Tour, { tourDone, type TourTab } from "./components/Tour";
import { I18nContext, Lang, readLang, storeLang, translate } from "./i18n";
import { ClientConfig, MeResponse, StudyDatabaseEntry } from "./types";
import "@fontsource/source-serif-4/400.css";
import "@fontsource/source-serif-4/400-italic.css";
import "@fontsource/source-serif-4/600.css";
import "@fontsource/source-serif-4/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./index.css";

type Tab = "dashboard" | "extract" | "verify" | "dataset" | "billing" | "account";

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
  const signedIn = !cloud || !!auth.user;

  // Count new extractions so the Verify tab can show an attention badge, and
  // bump a key so the dashboard/account panels reload after a change.
  const [extractionCount, setExtractionCount] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = useCallback(() => setRefreshKey((k) => k + 1), []);

  const [activeTab, setActiveTab] = useState<Tab>("extract");
  const [focusStudyId, setFocusStudyId] = useState<string | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const [logo3dOpen, setLogo3dOpen] = useState(false);
  // Back from a payment page (/?payment=return|cancel&order=…): open the
  // Billing tab once, where the order is settled and the address cleaned.
  const [paymentReturn, setPaymentReturn] = useState<PaymentReturn | null>(readPaymentReturn);
  const paymentTabPending = useRef(paymentReturn !== null);
  const paymentHandled = useCallback(() => {
    setPaymentReturn(null);
    setRefreshKey((k) => k + 1);
  }, []);

  // Every (re-)sign-in lands on the dashboard (or on Billing after a payment);
  // the per-session counters reset too.
  const userId = auth.user?.id ?? null;
  useEffect(() => {
    if (cloud) {
      const toAccount = paymentTabPending.current && userId !== null;
      if (toAccount) paymentTabPending.current = false;
      setActiveTab(toAccount ? "billing" : "dashboard");
      setExtractionCount(0);
    }
  }, [cloud, userId]);

  // Account summary for the header pills (credits) - cloud modes only.
  const [me, setMe] = useState<MeResponse | null>(null);
  // Closed beta: a signed-in address that is not on MAIDA_INVITED_EMAILS gets
  // 403 not_invited from every route; show one clear screen instead of a
  // workspace full of errors.
  const [notInvited, setNotInvited] = useState(false);
  useEffect(() => {
    setNotInvited(false);
    if (!cloud || !auth.user) {
      setMe(null);
      return;
    }
    fetchMe()
      .then(setMe)
      .catch((err: unknown) => {
        setMe(null);
        if (isNotInvited(err)) setNotInvited(true);
      });
  }, [cloud, auth.user, refreshKey]);

  // Version label: read once from /api/health so the UI can never disagree
  // with the backend (7.2.1). Falls back to "?" while unreachable.
  const [version, setVersion] = useState<string>("?");
  useEffect(() => {
    fetchHealth()
      .then((h) => setVersion(h.version))
      .catch(() => setVersion("?"));
  }, []);

  // 7.2.2: the PI's admin key, kept only in this browser (see api.ts). Only
  // shown in admin_key mode.
  const [adminKey, setAdminKeyField] = useState<string>(getAdminKey);
  const handleAdminKeyChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setAdminKeyField(value);
    setAdminKey(value);
  }, []);

  const handleExtracted = useCallback(
    (_entry: StudyDatabaseEntry) => {
      setExtractionCount((c) => c + 1);
      bump();
    },
    [bump]
  );

  const openStudy = useCallback((studyId: string) => {
    setFocusStudyId(studyId);
    setActiveTab("verify");
  }, []);

  // Guided tour (8.0): once per browser after the first sign-in, and on demand.
  const [tourOpen, setTourOpen] = useState(false);
  useEffect(() => {
    if (cloud && auth.user && !tourDone()) setTourOpen(true);
  }, [cloud, auth.user]);
  const tourTab = useCallback((tab: TourTab) => setActiveTab(tab), []);

  const t = i18n.t;

  const payments = !!config?.payments;
  const tabs: { id: Tab; label: string; badge?: number; cloudOnly?: boolean; paymentsOnly?: boolean }[] = [
    { id: "dashboard", label: t("nav_dashboard"), cloudOnly: true },
    { id: "extract", label: t("nav_extract") },
    { id: "verify", label: t("nav_verify"), badge: extractionCount },
    { id: "dataset", label: t("nav_dataset") },
    { id: "billing", label: t("nav_billing"), cloudOnly: true, paymentsOnly: true },
    { id: "account", label: t("nav_account"), cloudOnly: true },
  ];

  const initials = (auth.user?.name || auth.user?.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");

  const header = (
    <header className="shell-head">
      <div className="shell-head-left">
        <button
          type="button"
          className="logo-btn"
          onClick={() => setLogo3dOpen(true)}
          title={t("logo3d_open")}
          aria-label={t("logo3d_open")}
          data-testid="logo-3d-open"
        >
          <Logo />
        </button>
        <Logo3DDialog open={logo3dOpen} onClose={() => setLogo3dOpen(false)} />
        {signedIn && config && (
          <nav className="shell-nav" role="tablist">
            {tabs
              .filter((tab) => (!tab.cloudOnly || cloud) && (!tab.paymentsOnly || payments))
              .map((tab) => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  className={`nav-pill ${activeTab === tab.id ? "nav-pill-on" : ""}`}
                  onClick={() => setActiveTab(tab.id)}
                  data-testid={`tab-${tab.id}`}
                >
                  {tab.label}
                  {tab.badge ? <span className="nav-badge mono">{tab.badge}</span> : null}
                </button>
              ))}
          </nav>
        )}
      </div>
      <div className="shell-head-right">
        {signedIn && config && <StatusPill />}
        {cloud && me && me.credits !== null && (
          <span className="pill pill-credits mono" data-testid="credits-pill">
            <span className="glyph glyph-locked" aria-hidden="true">◆</span> {me.credits} {t("credits")}
          </span>
        )}
        {cloud && auth.user && (
          <span className="avatar" title={auth.user.email} data-testid="header-user">
            <span className="sr-only">{t("signed_in_as")} </span>
            <strong className="sr-only">{auth.user.email}</strong>
            <span aria-hidden="true">{initials}</span>
          </span>
        )}
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
        {signedIn && config && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setTourOpen(true)} data-testid="tour-open">
            {t("tour_btn")}
          </button>
        )}
        <div className="seg-group" role="group" aria-label="Language">
          <button type="button" className={`seg ${lang === "en" ? "seg-on" : ""}`} onClick={() => i18n.setLang("en")}>EN</button>
          <button type="button" className={`seg lang-toggle ${lang === "vi" ? "seg-on" : ""}`} onClick={() => i18n.setLang(lang === "vi" ? "en" : "vi")}>VI</button>
        </div>
      </div>
    </header>
  );

  const footer = (
    <footer className="shell-foot">
      <p>
        M-AIDA v{version} · {t("project_line")} ·{" "}
        <button type="button" className="link-btn" onClick={() => setContactOpen(true)} data-testid="contact-open">
          {t("contact_open")}
        </button>
      </p>
      <ContactDialog open={contactOpen} onClose={() => setContactOpen(false)} />
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
      <main className="shell-main">
        <div className="note note-warn"><p>Cannot reach the M-AIDA backend: {bootError}</p></div>
      </main>
    );
  } else if (!config) {
    body = (
      <main className="shell-main">
        <p className="loading-text">{t("loading")}</p>
      </main>
    );
  } else if (cloud && auth.user && notInvited) {
    body = (
      <main className="shell-main">
        <section className="not-invited" data-testid="not-invited">
          <h1 className="page-title">{t("not_invited_title")}</h1>
          <p className="mono">{auth.user.email}</p>
          <p>
            {t("not_invited_body")} <a href="mailto:thuyhuongctu@gmail.com">thuyhuongctu@gmail.com</a>.
          </p>
          <button type="button" className="btn btn-primary" onClick={() => void signOut()}>
            {t("not_invited_switch")}
          </button>
        </section>
      </main>
    );
  } else if (cloud && !auth.user) {
    return (
      <I18nContext.Provider value={i18n}>
        <LoginScreen mode={config.auth_mode as "supabase" | "mock"} version={version} />
      </I18nContext.Provider>
    );
  } else {
    body = (
      <main className={`shell-main ${activeTab === "verify" ? "shell-main-wide" : ""}`}>
        {activeTab === "dashboard" && cloud && (
          <Dashboard refreshKey={refreshKey} onNewExtraction={() => setActiveTab("extract")} onOpenStudy={openStudy} />
        )}
        {activeTab === "extract" && (
          <ExtractionPanel onExtracted={handleExtracted} cloud={cloud} credits={me?.credits ?? null} onOpenReview={openStudy} onSettled={bump} />
        )}
        {activeTab === "verify" && (
          <ReviewScreen initialStudyId={focusStudyId} refreshKey={refreshKey} onChanged={bump} />
        )}
        {activeTab === "dataset" && <DatasetPanel refreshKey={refreshKey} />}
        {activeTab === "billing" && cloud && (
          <BillingPanel refreshKey={refreshKey} paymentReturn={paymentReturn} onPaymentReturnHandled={paymentHandled} />
        )}
        {activeTab === "account" && cloud && <AccountPanel refreshKey={refreshKey} />}
      </main>
    );
  }

  return (
    <I18nContext.Provider value={i18n}>
      <div className="shell">
        <VnMark />
        {header}
        {body}
        {footer}
        <Tour open={tourOpen} onClose={() => setTourOpen(false)} onTab={tourTab} />
      </div>
    </I18nContext.Provider>
  );
}

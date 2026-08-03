/**
 * M-AIDA v7.1.1 - Root application component.
 *
 * Three-workspace layout:
 *   1. Extract       - PDF upload and LLM extraction (ExtractionPanel)
 *   2. Evidence Atlas - descriptive research intelligence (ResearchIntelligence)
 *   3. Verify & Lock - PI verification dashboard (VerificationDashboard + ExportPanel)
 */

import { App as CapacitorApp } from "@capacitor/app";
import { Share } from "@capacitor/share";
import { ExternalLink, Network, Share2 } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import ExportPanel from "./components/ExportPanel";
import ExtractionPanel from "./components/ExtractionPanel";
import ResearchIntelligence from "./components/ResearchIntelligence";
import StatusBanner from "./components/StatusBanner";
import { runtimeConfig } from "./config";
import VerificationDashboard from "./components/VerificationDashboard";
import { StudyDatabaseEntry } from "./types";
import "./index.css";

type Tab = "extract" | "verify" | "intelligence";

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("extract");
  // Count new extractions so the Verify tab can show an attention badge
  const [extractionCount, setExtractionCount] = useState(0);

  const handleExtracted = useCallback((_entry: StudyDatabaseEntry) => {
    setExtractionCount((c) => c + 1);
  }, []);

  const switchToVerify = useCallback(() => {
    setActiveTab("verify");
  }, []);

  const shareApp = useCallback(async () => {
    await Share.share({
      title: "M-AIDA Research",
      text: "M-AIDA supports human-verified data extraction for meta-analysis research.",
      url: runtimeConfig.supportUrl,
      dialogTitle: "Share M-AIDA",
    });
  }, []);

  useEffect(() => {
    if (!runtimeConfig.isNative || runtimeConfig.platform !== "android") return;
    let removeListener: (() => Promise<void>) | undefined;
    void CapacitorApp.addListener("backButton", ({ canGoBack }) => {
      if (activeTab !== "extract") setActiveTab("extract");
      else if (canGoBack) window.history.back();
      else void CapacitorApp.minimizeApp();
    }).then((handle) => {
      removeListener = () => handle.remove();
    });
    return () => {
      if (removeListener) void removeListener();
    };
  }, [activeTab]);

  const canShare =
    runtimeConfig.isNative ||
    (typeof navigator !== "undefined" && typeof navigator.share === "function");

  return (
    <div className="app">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      {/* Header */}
      <header className="app-header">
        <div>
          <div className="header-brand">
            <h1 className="app-title">M-AIDA</h1>
            <span className="app-version">v{runtimeConfig.appVersion}</span>
          </div>
          <p className="app-subtitle">
            Meta-Analysis Intelligent Data Assistant
          </p>
        </div>
        {canShare && (
          <button className="header-action" type="button" onClick={() => void shareApp()}>
            <Share2 size={17} aria-hidden="true" />
            Share
          </button>
        )}
      </header>

      {!runtimeConfig.storePublicationAllowed && (
        <aside className="release-gate" aria-label="Release status">
          <strong>Internal evaluation build.</strong> Store publication remains
          blocked until the CTU intellectual-property agreement and release
          checklist are approved.
        </aside>
      )}

      {/* Live status strip: backend, data, extraction mode, network */}
      <StatusBanner />

      {/* Tab navigation */}
      <nav className="tab-nav" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === "extract"}
          className={`tab-btn ${activeTab === "extract" ? "active" : ""}`}
          onClick={() => setActiveTab("extract")}
        >
          Extract
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "intelligence"}
          className={`tab-btn ${activeTab === "intelligence" ? "active" : ""}`}
          onClick={() => setActiveTab("intelligence")}
        >
          <Network size={16} aria-hidden="true" />
          Evidence Atlas
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "verify"}
          className={`tab-btn ${activeTab === "verify" ? "active" : ""}`}
          onClick={() => setActiveTab("verify")}
        >
          Verify &amp; Lock
          {extractionCount > 0 && (
            <span className="tab-badge">{extractionCount}</span>
          )}
        </button>
      </nav>

      {/* Tab content */}
      <main className="app-main" id="main-content">
        {activeTab === "extract" && (
          <div className="tab-content">
            <ExtractionPanel onExtracted={handleExtracted} />
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

        {activeTab === "intelligence" && <ResearchIntelligence />}
      </main>

      <footer className="app-footer">
        <p>
          M-AIDA v{runtimeConfig.appVersion} · Human verification required
        </p>
        <nav className="footer-links" aria-label="Legal and support">
          <a href={runtimeConfig.privacyPolicyUrl} target="_blank" rel="noreferrer">
            Privacy <ExternalLink size={12} aria-hidden="true" />
          </a>
          <a href={runtimeConfig.supportUrl} target="_blank" rel="noreferrer">
            Support <ExternalLink size={12} aria-hidden="true" />
          </a>
        </nav>
      </footer>
    </div>
  );
}

/**
 * M-AIDA v7.1.1 - Root application component.
 *
 * Two-tab layout:
 *   1. Extract       - PDF upload and LLM extraction (ExtractionPanel)
 *   2. Verify & Lock - PI verification dashboard (VerificationDashboard + ExportPanel)
 */

import React, { useCallback, useState } from "react";
import ExportPanel from "./components/ExportPanel";
import ExtractionPanel from "./components/ExtractionPanel";
import VerificationDashboard from "./components/VerificationDashboard";
import { StudyDatabaseEntry } from "./types";
import "./index.css";

type Tab = "extract" | "verify";

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

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <h1 className="app-title">M-AIDA</h1>
          <span className="app-version">v7.1.1</span>
        </div>
        <p className="app-subtitle">
          Meta-Analysis Intelligent Data Assistant - Internationalization &amp; Performance
        </p>
      </header>

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
      <main className="app-main">
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
      </main>

      <footer className="app-footer">
        <p>
          M-AIDA v7.1.1 · PhD Dissertation Research Tool · Asia-Pacific I&rarr;P
          Meta-Analysis
        </p>
      </footer>
    </div>
  );
}

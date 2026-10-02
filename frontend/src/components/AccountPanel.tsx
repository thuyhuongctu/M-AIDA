/**
 * AccountPanel - who is signed in, credit balance and history, data export,
 * and (for the operator) credit grants and model-usage totals.
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  adminGrantCredits,
  adminUsage,
  adminUsers,
  downloadAccountExport,
  fetchLedger,
  fetchMe,
} from "../api";
import { signOut } from "../auth";
import { useI18n } from "../i18n";
import type { AdminUsage, AdminUser, LedgerEntry, MeResponse } from "../types";

function fmtWhen(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function AccountPanel({ refreshKey }: { refreshKey: number }) {
  const { t } = useI18n();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // operator tools
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usage, setUsage] = useState<AdminUsage | null>(null);
  const [grantEmail, setGrantEmail] = useState("");
  const [grantAmount, setGrantAmount] = useState(10);
  const [grantResult, setGrantResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const m = await fetchMe();
      setMe(m);
      setLedger(m.credits === null ? [] : await fetchLedger(100));
      if (m.role === "admin" && m.auth_mode !== "admin_key") {
        const [u, g] = await Promise.all([adminUsers(), adminUsage(30)]);
        setUsers(u);
        setUsage(g);
      }
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const grant = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setGrantResult(null);
    try {
      const r = await adminGrantCredits(grantEmail.trim(), grantAmount);
      setGrantResult(`${grantEmail.trim()} → ${r.credits} ${t("credits")}`);
      await load();
    } catch (err: unknown) {
      setGrantResult(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setBusy(false);
    }
  };

  const reasonLabel = (reason: LedgerEntry["reason"]) => t(`reason_${reason}` as const);

  return (
    <div className="panel account-panel" data-testid="account-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("acc_title")}</h2>
        {me && me.auth_mode !== "admin_key" && (
          <button className="btn btn-ghost btn-sm" onClick={() => void signOut()} data-testid="sign-out">
            {t("sign_out")}
          </button>
        )}
      </div>
      {error && <p className="error-message">{error}</p>}

      {me && (
        <dl className="account-facts">
          <dt>{t("acc_email")}</dt>
          <dd>{me.email || "-"}</dd>
          <dt>{t("acc_role")}</dt>
          <dd>{me.role}</dd>
          <dt>{t("acc_balance")}</dt>
          <dd data-testid="account-credits">{me.credits === null ? "∞" : me.credits}</dd>
        </dl>
      )}

      <div className="action-row action-row-left">
        <button className="btn btn-secondary btn-sm" onClick={() => void downloadAccountExport()}>
          {t("acc_export")}
        </button>
      </div>

      {me && me.credits !== null && (
        <>
          <h3 className="panel-subtitle">{t("acc_ledger")}</h3>
          {ledger.length === 0 ? (
            <p className="empty-text">{t("acc_ledger_empty")}</p>
          ) : (
            <div className="table-container">
              <table className="studies-table ledger-table">
                <thead>
                  <tr>
                    <th>{t("job_when")}</th>
                    <th>{t("acc_ledger")}</th>
                    <th className="num">Δ</th>
                    <th className="num">{t("acc_balance")}</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.map((e) => (
                    <tr key={e.id}>
                      <td className="mono small">{fmtWhen(e.created_at)}</td>
                      <td>
                        {reasonLabel(e.reason)}
                        {e.note ? <span className="hint-inline"> · {e.note}</span> : null}
                      </td>
                      <td className={`num ${e.delta < 0 ? "neg" : "pos"}`}>{e.delta > 0 ? `+${e.delta}` : e.delta}</td>
                      <td className="num">{e.balance_after}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {me?.role === "admin" && me.auth_mode !== "admin_key" && (
        <div className="admin-tools" data-testid="admin-tools">
          <h3 className="panel-subtitle">{t("admin_title")}</h3>
          <form className="grant-form" onSubmit={grant}>
            <div className="form-row">
              <label className="form-label" htmlFor="grant-email">{t("admin_grant_email")}</label>
              <input id="grant-email" className="form-input" type="email" required value={grantEmail}
                     onChange={(e) => setGrantEmail(e.target.value)} />
            </div>
            <div className="form-row">
              <label className="form-label" htmlFor="grant-amount">{t("admin_grant_amount")}</label>
              <input id="grant-amount" className="form-input" type="number" min={1} max={10000} value={grantAmount}
                     onChange={(e) => setGrantAmount(Number(e.target.value))} />
            </div>
            <button className="btn btn-primary btn-sm" type="submit" disabled={busy}>{t("admin_grant_button")}</button>
            {grantResult && <p className="hint-text">{grantResult}</p>}
          </form>

          {usage && (
            <p className="usage-line">
              {t("admin_usage")}: <strong>{usage.calls}</strong> {t("admin_calls")} ·{" "}
              {usage.input_tokens.toLocaleString()} in / {usage.output_tokens.toLocaleString()} out ·{" "}
              {t("admin_cost")} <strong>${usage.estimated_cost_usd.toFixed(4)}</strong>
            </p>
          )}

          {users.length > 0 && (
            <div className="table-container">
              <table className="studies-table">
                <thead>
                  <tr>
                    <th>{t("admin_users")}</th>
                    <th>{t("acc_role")}</th>
                    <th className="num">{t("credits")}</th>
                    <th className="num">{t("dash_studies")}</th>
                    <th>{t("job_when")}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.email || u.id}</td>
                      <td>{u.role}</td>
                      <td className="num">{u.credits}</td>
                      <td className="num">{u.studies}</td>
                      <td className="mono small">{fmtWhen(u.last_seen_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

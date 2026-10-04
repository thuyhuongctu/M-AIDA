/**
 * AccountPanel - who is signed in, credit balance and history, credit packs
 * (when payments are on), data export, and (for the operator) credit grants,
 * model-usage totals and all payments.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  adminGrantCredits,
  adminOrders,
  adminUsage,
  adminUsers,
  apiUrl,
  cancelOrder,
  createOrder,
  downloadAccountExport,
  fetchLedger,
  fetchMe,
  fetchOrders,
  fetchPacks,
  syncOrder,
} from "../api";
import { signOut } from "../auth";
import { useI18n, type StringKey } from "../i18n";
import type {
  AdminOrders,
  AdminUsage,
  AdminUser,
  LedgerEntry,
  MeResponse,
  OrderStatus,
  PacksResponse,
  PaymentOrder,
} from "../types";

function fmtWhen(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** The buyer coming back from the payment page: /?payment=return|cancel&order=<code>. */
export interface PaymentReturn {
  kind: "return" | "cancel";
  order: string;
}

export function readPaymentReturn(): PaymentReturn | null {
  const params = new URLSearchParams(window.location.search);
  const kind = params.get("payment");
  const order = params.get("order") ?? "";
  if ((kind === "return" || kind === "cancel") && /^\d{1,20}$/.test(order)) return { kind, order };
  return null;
}

/** Drop ?payment=…&order=… from the address bar so a reload does not repeat it. */
function clearPaymentReturn(): void {
  const params = new URLSearchParams(window.location.search);
  params.delete("payment");
  params.delete("order");
  const query = params.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
}

const STATUS_CLASS: Record<OrderStatus, string> = {
  pending: "badge-medium",
  paid: "badge-success",
  cancelled: "badge-plain",
  expired: "badge-plain",
  failed: "badge-low",
};

const PACK_NAMES: Record<string, StringKey> = {
  thu: "pack_thu",
  tongquan: "pack_tongquan",
  nhom: "pack_nhom",
};

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

type Notice = { tone: "ok" | "info" | "warn"; text: string };

export default function AccountPanel({
  refreshKey,
  paymentReturn = null,
  onPaymentReturnHandled,
}: {
  refreshKey: number;
  paymentReturn?: PaymentReturn | null;
  onPaymentReturnHandled?: () => void;
}) {
  const { t, lang } = useI18n();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // credit packs
  const [packs, setPacks] = useState<PacksResponse | null>(null);
  const [orders, setOrders] = useState<PaymentOrder[]>([]);
  const [payBusy, setPayBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  // operator tools
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usage, setUsage] = useState<AdminUsage | null>(null);
  const [allOrders, setAllOrders] = useState<AdminOrders | null>(null);
  const [grantEmail, setGrantEmail] = useState("");
  const [grantAmount, setGrantAmount] = useState(10);
  const [grantResult, setGrantResult] = useState<string | null>(null);

  const vnd = useCallback(
    (amount: number) =>
      new Intl.NumberFormat(lang === "vi" ? "vi-VN" : "en-US", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
      }).format(amount),
    [lang]
  );
  const packName = (id: string) => (PACK_NAMES[id] ? t(PACK_NAMES[id]) : id);
  const errorText = useCallback(
    (err: unknown) => (err instanceof Error ? err.message : t("error_generic")),
    [t]
  );

  const load = useCallback(async () => {
    try {
      const m = await fetchMe();
      setMe(m);
      if (m.credits === null) {
        setLedger([]);
        setPacks(null);
        setOrders([]);
      } else {
        const [l, p, o] = await Promise.all([
          fetchLedger(100),
          fetchPacks().catch(() => null),
          fetchOrders(20).catch(() => [] as PaymentOrder[]),
        ]);
        setLedger(l);
        setPacks(p);
        setOrders(o);
      }
      if (m.role === "admin" && m.auth_mode !== "admin_key") {
        const [u, g, a] = await Promise.all([adminUsers(), adminUsage(30), adminOrders(100).catch(() => null)]);
        setUsers(u);
        setUsage(g);
        setAllOrders(a);
      }
      setError(null);
    } catch (err: unknown) {
      setError(errorText(err));
    }
  }, [errorText]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const describe = useCallback(
    (o: PaymentOrder, cancelled: boolean): Notice => {
      if (o.status === "paid") return { tone: "ok", text: t("pay_return_paid").replace("{n}", String(o.credits)) };
      if (cancelled || o.status === "cancelled") return { tone: "info", text: t("pay_return_cancel") };
      if (o.status === "expired") return { tone: "info", text: t("pay_return_expired") };
      if (o.payment_reference.startsWith("UNDERPAID")) return { tone: "warn", text: t("pay_underpaid") };
      return { tone: "warn", text: t("pay_return_pending") };
    },
    [t]
  );

  // Back from the payment page: settle the order once. payOS may notify the
  // server a few seconds after the redirect, so a pending order is checked
  // again twice before telling the buyer to wait.
  const handledReturn = useRef<string | null>(null);
  useEffect(() => {
    if (!paymentReturn) return;
    const key = `${paymentReturn.kind}:${paymentReturn.order}`;
    if (handledReturn.current === key) return;
    handledReturn.current = key;
    void (async () => {
      setNotice({ tone: "info", text: t("pay_checking") });
      try {
        let order: PaymentOrder;
        if (paymentReturn.kind === "cancel") {
          order = await cancelOrder(paymentReturn.order);
        } else {
          order = await syncOrder(paymentReturn.order);
          for (let attempt = 0; attempt < 2 && order.status === "pending"; attempt += 1) {
            await sleep(3000);
            order = await syncOrder(paymentReturn.order);
          }
        }
        setNotice(describe(order, paymentReturn.kind === "cancel"));
      } catch (err: unknown) {
        setNotice({ tone: "warn", text: errorText(err) });
      } finally {
        clearPaymentReturn();
        onPaymentReturnHandled?.();
        await load();
      }
    })();
  }, [paymentReturn, onPaymentReturnHandled, describe, errorText, load, t]);

  const buy = async (packId: string) => {
    setPayBusy(packId);
    setNotice({ tone: "info", text: t("pay_opening") });
    try {
      const order = await createOrder(packId);
      window.location.assign(apiUrl(order.checkout_url));
    } catch (err: unknown) {
      setNotice({ tone: "warn", text: errorText(err) });
      setPayBusy(null);
    }
  };

  const check = async (order: PaymentOrder) => {
    setPayBusy(order.id);
    try {
      const fresh = await syncOrder(order.id);
      setNotice(describe(fresh, false));
      await load();
    } catch (err: unknown) {
      setNotice({ tone: "warn", text: errorText(err) });
    } finally {
      setPayBusy(null);
    }
  };

  const grant = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setGrantResult(null);
    try {
      const r = await adminGrantCredits(grantEmail.trim(), grantAmount);
      setGrantResult(`${grantEmail.trim()} → ${r.credits} ${t("credits")}`);
      await load();
    } catch (err: unknown) {
      setGrantResult(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const reasonLabel = (reason: LedgerEntry["reason"]) => t(`reason_${reason}` as const);
  const statusPill = (status: OrderStatus) => (
    <span className={`badge ${STATUS_CLASS[status]}`} data-testid="order-status">
      {t(`pay_status_${status}` as const)}
    </span>
  );
  const shop = packs?.enabled ? packs : null;

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
      {notice && (
        <p className={`pay-notice pay-notice-${notice.tone}`} role="status" data-testid="pay-notice">
          {notice.text}
        </p>
      )}

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

      {shop && shop.packs.length > 0 && (
        <section className="pay-shop" data-testid="pay-shop">
          <h3 className="panel-subtitle">{t("pay_title")}</h3>
          <p className="hint-text pay-intro">{t("pay_intro")}</p>
          <div className="pack-grid">
            {shop.packs.map((p) => (
              <div className="pack-card" key={p.id} data-testid={`pack-${p.id}`}>
                <span className="pack-name">{packName(p.id)}</span>
                <span className="pack-credits">
                  {p.credits.toLocaleString(lang === "vi" ? "vi-VN" : "en-US")} <small>{t("credits")}</small>
                </span>
                <span className="pack-price">{vnd(p.price_vnd)}</span>
                <span className="pack-unit">
                  {vnd(Math.round(p.price_vnd / p.credits))} {t("pay_per_credit")}
                </span>
                <button
                  className="btn btn-primary btn-sm"
                  type="button"
                  disabled={payBusy !== null}
                  onClick={() => void buy(p.id)}
                  data-testid={`buy-${p.id}`}
                >
                  {t("pay_buy")}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {orders.length > 0 && (
        <>
          <h3 className="panel-subtitle">{t("pay_orders")}</h3>
          <div className="table-container">
            <table className="studies-table orders-table" data-testid="orders-table">
              <thead>
                <tr>
                  <th>{t("job_when")}</th>
                  <th>{t("pay_order")}</th>
                  <th>{t("pay_pack")}</th>
                  <th className="num">{t("pay_amount")}</th>
                  <th>{t("job_status")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id}>
                    <td className="mono small">{fmtWhen(o.created_at)}</td>
                    <td className="mono small">{o.order_code}</td>
                    <td>
                      {packName(o.pack_id)} <span className="hint-inline">· {o.credits} {t("credits")}</span>
                    </td>
                    <td className="num">{vnd(o.amount)}</td>
                    <td>
                      {statusPill(o.status)}
                      {o.status === "pending" && o.payment_reference.startsWith("UNDERPAID") && (
                        <span className="hint-inline"> {t("pay_underpaid")}</span>
                      )}
                    </td>
                    <td>
                      <div className="order-actions">
                        {o.status === "pending" && o.checkout_url && (
                          <a className="btn-link" href={apiUrl(o.checkout_url)}>
                            {t("pay_continue")}
                          </a>
                        )}
                        {(o.status === "pending" || o.status === "expired" || o.status === "cancelled") && (
                          <button
                            className="btn btn-ghost btn-sm"
                            type="button"
                            disabled={payBusy !== null}
                            onClick={() => void check(o)}
                          >
                            {t("pay_check")}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

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

          {allOrders && allOrders.orders.length > 0 && (
            <>
              <h3 className="panel-subtitle">{t("admin_orders")}</h3>
              <p className="paid-line" data-testid="admin-paid-total">
                <strong>{allOrders.paid_orders}</strong> {t("admin_paid")} · <strong>{vnd(allOrders.paid_amount_vnd)}</strong> ·{" "}
                <strong>{allOrders.paid_credits}</strong> {t("admin_paid_credits")}
              </p>
              <div className="table-container">
                <table className="studies-table orders-table">
                  <thead>
                    <tr>
                      <th>{t("job_when")}</th>
                      <th>{t("admin_users")}</th>
                      <th>{t("pay_order")}</th>
                      <th>{t("pay_pack")}</th>
                      <th className="num">{t("pay_amount")}</th>
                      <th>{t("job_status")}</th>
                      <th>Ref.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allOrders.orders.map((o) => (
                      <tr key={o.id}>
                        <td className="mono small">{fmtWhen(o.created_at)}</td>
                        <td>{o.email}</td>
                        <td className="mono small">{o.order_code}</td>
                        <td>{packName(o.pack_id)}</td>
                        <td className="num">{vnd(o.amount)}</td>
                        <td>{statusPill(o.status)}</td>
                        <td className="mono small">{o.payment_reference || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

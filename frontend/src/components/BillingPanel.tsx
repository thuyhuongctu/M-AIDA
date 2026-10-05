/**
 * BillingPanel - the "Billing" tab: credit packs on sale, the caller's
 * payments, and the return from the payment page.
 *
 * Shown only when the server has a payment provider (ClientConfig.payments).
 * Prices, packs and the payment link all come from the backend
 * (backend/payments.py); nothing here decides an amount.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { apiUrl, cancelOrder, createOrder, fetchMe, fetchOrders, fetchPacks, syncOrder } from "../api";
import { useI18n, type StringKey } from "../i18n";
import type { MeResponse, OrderStatus, PacksResponse, PaymentOrder } from "../types";

export function fmtWhen(iso: string | null): string {
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

/** Formatting shared by the Billing tab and the operator's payment list. */
export function useBillingFormat() {
  const { t, lang } = useI18n();
  const vnd = useCallback(
    (amount: number) =>
      new Intl.NumberFormat(lang === "vi" ? "vi-VN" : "en-US", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
      }).format(amount),
    [lang]
  );
  const packName = useCallback((id: string) => (PACK_NAMES[id] ? t(PACK_NAMES[id]) : id), [t]);
  const statusPill = (status: OrderStatus) => (
    <span className={`badge ${STATUS_CLASS[status]}`} data-testid="order-status">
      {t(`pay_status_${status}` as const)}
    </span>
  );
  return { vnd, packName, statusPill };
}

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

type Notice = { tone: "ok" | "info" | "warn"; text: string };

export default function BillingPanel({
  refreshKey,
  paymentReturn = null,
  onPaymentReturnHandled,
}: {
  refreshKey: number;
  paymentReturn?: PaymentReturn | null;
  onPaymentReturnHandled?: () => void;
}) {
  const { t, lang } = useI18n();
  const { vnd, packName, statusPill } = useBillingFormat();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [packs, setPacks] = useState<PacksResponse | null>(null);
  const [orders, setOrders] = useState<PaymentOrder[]>([]);
  const [payBusy, setPayBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [error, setError] = useState<string | null>(null);

  const errorText = useCallback((err: unknown) => (err instanceof Error ? err.message : t("error_generic")), [t]);

  const load = useCallback(async () => {
    try {
      const [m, p, o] = await Promise.all([fetchMe(), fetchPacks(), fetchOrders(20)]);
      setMe(m);
      setPacks(p);
      setOrders(o);
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

  const shop = packs?.enabled ? packs : null;

  return (
    <div className="panel account-panel billing-panel" data-testid="billing-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("pay_tab_title")}</h2>
        {me && me.credits !== null && (
          <span className="billing-balance mono" data-testid="billing-credits">
            {me.credits} {t("credits")}
          </span>
        )}
      </div>
      {error && <p className="error-message">{error}</p>}
      {notice && (
        <p className={`pay-notice pay-notice-${notice.tone}`} role="status" data-testid="pay-notice">
          {notice.text}
        </p>
      )}

      {shop && shop.packs.length > 0 ? (
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
      ) : (
        packs && <p className="hint-text">{t("pay_closed")}</p>
      )}

      <h3 className="panel-subtitle">{t("pay_orders")}</h3>
      {orders.length === 0 ? (
        <p className="empty-text">{t("pay_orders_empty")}</p>
      ) : (
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
      )}
    </div>
  );
}

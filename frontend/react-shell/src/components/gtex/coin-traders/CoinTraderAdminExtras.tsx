import React, { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Panel } from "@/components/gtex/ui";

export function CoinTraderAdminExtras() {
  const qc = useQueryClient();
  const [adminTab, setAdminTab] = useState<"adverts" | "orders" | "config" | "audits">("adverts");
  const [pauseReasons, setPauseReasons] = useState<Record<string, string>>({});
  const [orderStatusFilter, setOrderStatusFilter] = useState<"all" | "disputed" | "active">("all");
  const [resolveNote, setResolveNote] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const safeGet = async (url: string, fallback: any) => {
    try {
      const res = await api.get(url);
      return res?.data ?? fallback;
    } catch {
      return fallback;
    }
  };

  const { data: overview } = useQuery<any>({
    queryKey: ["admin", "coin-traders", "overview"],
    queryFn: () => safeGet("/admin/coin-traders/overview", null),
  });

  const { data: adverts = [] } = useQuery<any[]>({
    queryKey: ["admin", "coin-traders", "adverts"],
    queryFn: () => safeGet("/admin/coin-traders/adverts", []),
  });

  const { data: orders = [] } = useQuery<any[]>({
    queryKey: ["admin", "coin-traders", "orders"],
    queryFn: () => safeGet("/admin/coin-traders/orders", []),
  });

  const { data: config } = useQuery<any>({
    queryKey: ["admin", "coin-traders", "config"],
    queryFn: () => safeGet("/admin/coin-traders/config", null),
  });

  const { data: audits = [] } = useQuery<any[]>({
    queryKey: ["admin", "coin-traders", "audit-logs"],
    queryFn: () => safeGet("/admin/coin-traders/audit-logs", []),
  });

  const gtcRef = (config?.assets || []).find((a: any) => a.coin_unit === "coin");
  const fncRef = (config?.assets || []).find((a: any) => a.coin_unit === "credit");
  const [cfgDraft, setCfgDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!gtcRef && !fncRef) return;
    setCfgDraft({
      deposit_rate_value: String(gtcRef?.direct_buy_rate_fiat ?? ""),
      withdrawal_rate_value: String(gtcRef?.direct_sell_rate_fiat ?? ""),
      min_trader_buy_rate_fiat: String(gtcRef?.min_trader_buy_rate_fiat ?? ""),
      max_trader_buy_rate_fiat: String(gtcRef?.max_trader_buy_rate_fiat ?? ""),
      min_trader_sell_rate_fiat: String(gtcRef?.min_trader_sell_rate_fiat ?? ""),
      max_trader_sell_rate_fiat: String(gtcRef?.max_trader_sell_rate_fiat ?? ""),
      max_trader_spread_fiat: String(gtcRef?.max_trader_spread_fiat ?? ""),
      fan_coin_deposit_rate_value: String(fncRef?.direct_buy_rate_fiat ?? ""),
      trader_fan_coin_purchase_rate_value: String(fncRef?.trader_wholesale_rate_fiat ?? ""),
    });
  }, [config]);

  const refreshAll = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["admin", "coin-traders"] }),
      qc.invalidateQueries({ queryKey: ["coin-trader-marketplace"] }),
    ]);
  };

  const handlePauseAdvert = async (advertId: string) => {
    const reason = (pauseReasons[advertId] || "Flagged by compliance review").trim();
    setBusy(`pause:${advertId}`);
    try {
      await api.post(`/admin/coin-traders/adverts/${advertId}/pause`, { reason });
      toast.success("Advert paused by admin.");
      await refreshAll();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const handleResumeAdvert = async (advertId: string) => {
    setBusy(`resume:${advertId}`);
    try {
      await api.post(`/admin/coin-traders/adverts/${advertId}/resume`);
      toast.success("Advert resumed.");
      await refreshAll();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const handleResolveOrder = async (orderId: string, resolution: "release" | "refund") => {
    setBusy(`${resolution}:${orderId}`);
    try {
      await api.post(`/admin/coin-traders/orders/${orderId}/resolve`, {
        resolution,
        note: resolveNote[orderId] || `Admin ${resolution}`,
      });
      toast.success(`Order resolved (${resolution}).`);
      await refreshAll();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const handleSaveConfig = async () => {
    setBusy("save-config");
    try {
      const payload: Record<string, number> = {};
      for (const [k, v] of Object.entries(cfgDraft)) {
        if (v !== "" && Number.isFinite(Number(v))) payload[k] = Number(v);
      }
      await api.put("/admin/coin-traders/config", payload);
      toast.success("Marketplace rules updated.");
      await refreshAll();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const visibleOrders = orders.filter((o) => {
    if (orderStatusFilter === "disputed") return o.status === "disputed";
    if (orderStatusFilter === "active")
      return ["created", "payment_pending", "proof_submitted", "disputed"].includes(o.status);
    return true;
  });

  return (
    <div className="space-y-4">
      {overview && (
        <div
          className="grid gap-3 sm:grid-cols-2 md:grid-cols-5 rounded-xl border border-white/10 bg-black/30 p-3 text-xs"
          data-testid="admin-coin-trader-overview"
        >
          <div>
            <span className="text-slate-400">Traders (DIDit / Total)</span>
            <p className="text-base font-bold text-white">
              {overview.didit_verified_traders} / {overview.total_traders}
            </p>
          </div>
          <div>
            <span className="text-slate-400">Active Adverts</span>
            <p className="text-base font-bold text-emerald-400">{overview.active_adverts}</p>
          </div>
          <div>
            <span className="text-slate-400">Active / Disputed Orders</span>
            <p className="text-base font-bold text-amber-300">
              {overview.active_escrow_orders} /{" "}
              <span className="text-rose-400">{overview.disputed_orders}</span>
            </p>
          </div>
          <div>
            <span className="text-slate-400">Escrowed GTC / FNC</span>
            <p className="text-base font-bold text-white">
              {fmt(overview.total_escrowed_coin)} / {fmt(overview.total_escrowed_credit)}
            </p>
          </div>
          <div>
            <span className="text-slate-400">Completed Volume</span>
            <p className="text-base font-bold text-emerald-400">
              ₦{fmt(overview.completed_volume_fiat, 2)}
            </p>
          </div>
        </div>
      )}

      <Panel eyebrow="Marketplace Operations" title="Adverts, Disputes, Rules & Audit Logs">
        <div className="mb-4 flex flex-wrap gap-2 border-b border-white/10 pb-3">
          {[
            ["adverts", `Adverts (${adverts.length})`],
            ["orders", `Orders & Disputes (${orders.length})`],
            ["config", "Pricing & Rules"],
            ["audits", `Audit Logs (${audits.length})`],
          ].map(([k, lbl]) => (
            <button
              key={k}
              type="button"
              onClick={() => setAdminTab(k as any)}
              className={`gx-btn py-1 px-3 text-xs ${adminTab === k ? "gx-btn-primary" : "gx-btn-secondary"}`}
            >
              {lbl}
            </button>
          ))}
        </div>

        {adminTab === "adverts" && (
          <div className="space-y-2">
            {adverts.length === 0 ? (
              <p className="text-xs text-slate-400">No adverts published yet.</p>
            ) : (
              adverts.map((a) => (
                <div
                  key={a.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 p-2.5 text-xs"
                >
                  <div>
                    <Chip
                      tone={
                        a.status === "active"
                          ? "emerald"
                          : a.status === "admin_paused"
                            ? "red"
                            : "slate"
                      }
                    >
                      {label(a.status)}
                    </Chip>{" "}
                    <b className="text-white">
                      {a.side.toUpperCase()} {a.coin_unit === "coin" ? "GTC" : "FNC"}
                    </b>{" "}
                    @ ₦{fmt(a.effective_price_fiat, 2)} · Avail {fmt(a.available_coin)} · Trader{" "}
                    <span className="gx-mono text-slate-400">
                      {a.trader_profile_id.slice(0, 8)}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {a.status !== "admin_paused" ? (
                      <>
                        <input
                          className="gx-input py-1 text-xs max-w-[180px]"
                          placeholder="Pause reason"
                          value={pauseReasons[a.id] || ""}
                          onChange={(e) =>
                            setPauseReasons((p) => ({ ...p, [a.id]: e.target.value }))
                          }
                        />
                        <Btn
                          variant="danger"
                          disabled={busy !== null}
                          onClick={() => handlePauseAdvert(a.id)}
                          data-testid={`admin-pause-advert-${a.id}`}
                        >
                          Pause
                        </Btn>
                      </>
                    ) : (
                      <Btn disabled={busy !== null} onClick={() => handleResumeAdvert(a.id)}>
                        Resume
                      </Btn>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {adminTab === "orders" && (
          <div className="space-y-3">
            <div className="flex gap-2">
              {(["all", "disputed", "active"] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setOrderStatusFilter(f)}
                  className={`rounded px-2.5 py-1 text-xs ${orderStatusFilter === f ? "bg-white/15 text-white" : "text-slate-400"}`}
                >
                  {label(f)}
                </button>
              ))}
            </div>
            {visibleOrders.length === 0 ? (
              <p className="text-xs text-slate-400">No orders matching filter.</p>
            ) : (
              visibleOrders.map((o) => {
                const canResolve = ["payment_pending", "proof_submitted", "disputed"].includes(
                  o.status,
                );
                return (
                  <div
                    key={o.id}
                    className="rounded-lg border border-white/10 p-3 text-xs space-y-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span>
                        <b className="text-white">
                          {o.direction} · {fmt(o.coin_amount)}{" "}
                          {o.coin_unit === "coin" ? "GTC" : "FNC"}
                        </b>{" "}
                        (₦{fmt(o.fiat_total, 2)}) · Order{" "}
                        <span className="gx-mono">{o.id.slice(0, 8)}</span>
                      </span>
                      <Chip
                        tone={
                          o.status === "disputed"
                            ? "red"
                            : o.status === "released"
                              ? "emerald"
                              : "gold"
                        }
                      >
                        {label(o.status)}
                      </Chip>
                    </div>
                    {o.metadata_json?.dispute && (
                      <p className="text-rose-300">
                        Dispute reason: {o.metadata_json.dispute.reason}
                      </p>
                    )}
                    {o.proof?.proof_reference && (
                      <p className="text-slate-300">Proof Ref: {o.proof.proof_reference}</p>
                    )}
                    {canResolve && (
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          className="gx-input py-1 text-xs max-w-[220px]"
                          placeholder="Resolution note"
                          value={resolveNote[o.id] || ""}
                          onChange={(e) =>
                            setResolveNote((p) => ({ ...p, [o.id]: e.target.value }))
                          }
                        />
                        <Btn
                          disabled={busy !== null}
                          onClick={() => handleResolveOrder(o.id, "release")}
                        >
                          Release Escrow
                        </Btn>
                        <Btn
                          variant="danger"
                          disabled={busy !== null}
                          onClick={() => handleResolveOrder(o.id, "refund")}
                        >
                          Refund Escrow
                        </Btn>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {adminTab === "config" && (
          <div className="space-y-3 text-xs">
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              {Object.entries(cfgDraft).map(([k, val]) => (
                <label key={k} className="block">
                  <span className="gx-label">{label(k)}</span>
                  <input
                    className="gx-input mt-1 text-xs"
                    type="number"
                    step="0.01"
                    value={val}
                    onChange={(e) => setCfgDraft((p) => ({ ...p, [k]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
            <Btn disabled={busy !== null} onClick={handleSaveConfig}>
              {busy === "save-config" ? "Saving..." : "Save Marketplace Rules"}
            </Btn>
          </div>
        )}

        {adminTab === "audits" && (
          <div className="space-y-1.5 max-h-72 overflow-y-auto text-xs">
            {audits.length === 0 ? (
              <p className="text-slate-400">No audit entries yet.</p>
            ) : (
              audits.map((a) => (
                <div
                  key={a.id}
                  className="flex flex-wrap justify-between gap-2 rounded border border-white/10 p-2"
                >
                  <div>
                    <span className="gx-mono text-amber-300">{a.action_key}</span> ·{" "}
                    <span className="text-slate-200">{a.detail}</span>
                  </div>
                  <span className="text-slate-500">{new Date(a.created_at).toLocaleString()}</span>
                </div>
              ))
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}

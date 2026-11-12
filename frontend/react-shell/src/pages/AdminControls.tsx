import React, { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, label } from "@/lib/owner";
import { Btn, Chip, Empty, Loading, Panel, Stat } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";

/* ---------- helpers ---------- */
export function useAdminGet<T = any>(key: string, path: string, enabled = true) {
  return useQuery<T | null>({
    queryKey: ["admin", key, path],
    queryFn: async () => {
      try {
        return (await api.get(path)).data as T;
      } catch {
        return null;
      }
    },
    enabled,
  });
}

function useAct() {
  const qc = useQueryClient();
  return async (fn: () => Promise<any>, ok: string, invalidate: string[] = []) => {
    try {
      const res = await fn();
      toast.success(ok);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["admin"] }),
        qc.invalidateQueries({ queryKey: ["admin-god-mode-bootstrap"] }),
        ...invalidate.map((k) => qc.invalidateQueries({ queryKey: [k] })),
      ]);
      return res;
    } catch (e) {
      toast.error(errMsg(e));
      return null;
    }
  };
}

function Toggle({ on, onChange, text, testid }: { on: boolean; onChange: (v: boolean) => void; text: string; testid?: string }) {
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={() => onChange(!on)}
      className={`flex items-center justify-between gap-2 rounded-md border px-3 py-1.5 text-xs font-bold transition-colors ${
        on ? "border-emerald-400/50 bg-emerald-500/15 text-emerald-200" : "border-red-400/40 bg-red-500/10 text-red-200"
      }`}
    >
      <span>{text}</span>
      <span className="gx-mono">{on ? "ON" : "OFF"}</span>
    </button>
  );
}

function Field({ name, value, onChange, type = "text", testid }: { name: string; value: any; onChange: (v: string) => void; type?: string; testid?: string }) {
  return (
    <div>
      <label className="gx-label">{name}</label>
      <input className="gx-input" type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} />
    </div>
  );
}

const READONLY_KEYS = new Set(["id", "created_at", "updated_at", "updated_by", "updated_by_user_id", "active_bank_account", "reason"]);

export function GameClockPanel() {
  const act = useAct();
  const { data: clock, refetch } = useAdminGet<any>("world-clock", "/world/clock");
  const started = Boolean(clock?.officially_started);
  return (
    <Panel eyebrow="Game clock" title="Start the game clock" testid="admin-game-clock">
      <p className="mb-3 text-sm leading-relaxed text-slate-400">
        {started
          ? `The clock is running. Game date ${clock?.world_date || "—"}. One season is about 11 weeks. It cannot be paused or sped up.`
          : "The clock has not started. Press Start the clock once. After that it cannot be paused or sped up. One season is about 11 weeks."}
      </p>
      {started ? null : (
        <Btn
          variant="gold"
          data-testid="admin-start-clock-btn"
          onClick={() => act(() => api.post("/admin/world/clock/start"), "Game clock started").then(() => refetch())}
        >
          Start the clock
        </Btn>
      )}
    </Panel>
  );
}

export function NamedCupPrizePanel() {
  const act = useAct();
  const { data: cups, refetch } = useAdminGet<any[]>("named-cups", "/admin/national-team-engine/cups");
  const [cupId, setCupId] = useState("");
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [third, setThird] = useState("");
  const rows = cups || [];
  const selected = rows.find((row) => row.id === cupId);
  useEffect(() => {
    if (!cupId && rows[0]?.id) setCupId(rows[0].id);
  }, [cupId, cups]);
  useEffect(() => {
    if (!selected) return;
    setFirst(String(selected.first ?? ""));
    setSecond(String(selected.second ?? ""));
    setThird(String(selected.third ?? ""));
  }, [selected?.id]);
  return (
    <Panel eyebrow="Named cup" title="Put this prize into this cup" testid="admin-named-cup-prize">
      <p className="mb-3 text-sm leading-relaxed text-slate-400">
        Pick the cup, type what 1st, 2nd and 3rd win, then put that coin aside for this cup. Entry stays free. Players do not pay this. When the cup ends, the prize is paid from the coin held for it.
      </p>
      {rows.length === 0 ? (
        <Empty title="No cups yet" body="Create a GTEX competition on the admin desk, then come back and set its prize." />
      ) : (
        <>
          <label className="gx-label">Which cup</label>
          <select className="gx-input mb-3" value={cupId} onChange={(e) => setCupId(e.target.value)} data-testid="admin-cup-select">
            {rows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.title} · {row.season_label} · {row.held_coin} coin set aside
              </option>
            ))}
          </select>
          <div className="grid grid-cols-3 gap-2">
            <Field name="1st prize" type="number" value={first} onChange={setFirst} testid="admin-cup-first" />
            <Field name="2nd prize" type="number" value={second} onChange={setSecond} testid="admin-cup-second" />
            <Field name="3rd prize" type="number" value={third} onChange={setThird} testid="admin-cup-third" />
          </div>
          <Btn
            className="mt-3"
            variant="gold"
            data-testid="admin-save-cup-prize-btn"
            onClick={() =>
              act(
                () =>
                  api.put(`/admin/national-team-engine/cups/${cupId}/prize`, {
                    first: Number(first || 0),
                    second: Number(second || 0),
                    third: Number(third || 0),
                  }),
                "Prize saved for this cup",
              ).then(() => refetch())
            }
          >
            Put this prize into this cup
          </Btn>
        </>
      )}
    </Panel>
  );
}

/** Generic editor for flat settings objects (primitive fields only). Sends only changed fields. */
function SettingsEditor({ title, path, method = "put", extra = {}, wrap }: { title: string; path: string; method?: "put" | "post"; extra?: Record<string, any>; wrap?: (d: any) => any }) {
  const { data, isLoading } = useAdminGet("settings", path);
  const act = useAct();
  const [draft, setDraft] = useState<Record<string, any>>({});
  useEffect(() => setDraft({}), [data]);
  if (isLoading) return <Loading />;
  if (!data) return <p className="text-xs text-slate-500">{title}: unavailable for your role.</p>;
  const keys = Object.keys(data).filter((k) => !READONLY_KEYS.has(k) && ["string", "number", "boolean"].includes(typeof data[k]));
  const save = () => {
    const body: Record<string, any> = {};
    Object.entries(draft).forEach(([k, v]) => {
      body[k] = typeof data[k] === "number" ? Number(v) : v;
    });
    if (!Object.keys(body).length) return toast.info("No changes");
    return act(() => api[method](path, wrap ? wrap({ ...body, ...extra }) : { ...body, ...extra }), `${title} saved`);
  };
  return (
    <div className="space-y-3 rounded-xl border border-white/10 bg-slate-950/60 p-4">
      <p className="text-xs font-bold uppercase tracking-wider text-emerald-300">{title}</p>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        {keys.map((k) =>
          typeof data[k] === "boolean" ? (
            <Toggle key={k} text={label(k)} on={Boolean(draft[k] ?? data[k])} onChange={(v) => setDraft({ ...draft, [k]: v })} />
          ) : (
            <Field key={k} name={label(k)} type={typeof data[k] === "number" ? "number" : "text"} value={draft[k] ?? data[k]} onChange={(v) => setDraft({ ...draft, [k]: v })} />
          ),
        )}
      </div>
      <Btn onClick={save}>Save {title}</Btn>
    </div>
  );
}

/* ---------- Tab 1: rails ---------- */
export function RailsAndTreasuryTab() {
  const act = useAct();
  const { data: rails } = useAdminGet("rails", "/admin/god-mode/payment-rails");
  const { data: wc } = useAdminGet("wc", "/admin/god-mode/withdrawal-controls");
  const { data: td } = useAdminGet("td", "/admin/treasury/dashboard");
  const [railDraft, setRailDraft] = useState<any[]>([]);
  const [wcDraft, setWcDraft] = useState<any>(null);
  const [reason, setReason] = useState("Admin console adjustment");
  useEffect(() => setRailDraft(rails?.rails || []), [rails]);
  useEffect(() => setWcDraft(wc ? { ...wc } : null), [wc]);
  const [iv, setIv] = useState({ action: "buy_from_user", user_id: "", player_id: "", quantity: "1", unit_price_credits: "", confirmation_text: "" });
  const [wd, setWd] = useState<any>({ amount_credits: "", bank_name: "", account_number: "", account_name: "" });

  return (
    <div className="space-y-6" data-testid="admin-tab-rails">
      <Panel eyebrow="Money owed" title="What the platform may have to pay">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="People" value={fmt(td?.total_users ?? 0)} />
          <Stat label="Coin sitting in wallets" value={fmt(td?.wallet_liability ?? 0)} />
          <Stat label="Cash-outs still waiting" value={fmt(td?.pending_treasury_exposure ?? 0)} tone="warn" />
          <Stat label="Money in / cash-outs / ID checks" value={`${td?.pending_deposits ?? 0} / ${td?.pending_withdrawals ?? 0} / ${td?.pending_kyc ?? 0}`} />
        </div>
      </Panel>
      <Panel eyebrow="Banks" title="Turn pay-in and cash-out on or off">
        <input className="gx-input mb-3" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why you changed this (at least 4 letters)" />
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="space-y-2">
            {railDraft.length === 0 && <Empty title="No rails configured" />}
            {railDraft.map((r, i) => (
              <div key={r.provider} className="space-y-2 rounded-md border border-white/10 p-3">
                <p className="text-sm font-bold uppercase text-white">{r.provider}</p>
                <div className="grid grid-cols-3 gap-2">
                  {(["deposits_enabled", "withdrawals_enabled", "is_live"] as const).map((k) => (
                    <Toggle key={k} text={label(k)} on={Boolean(r[k])} onChange={(v) => setRailDraft(railDraft.map((x, j) => (j === i ? { ...x, [k]: v } : x)))} />
                  ))}
                </div>
                <input className="gx-input" placeholder="Maintenance message" value={r.maintenance_message ?? ""} onChange={(e) => setRailDraft(railDraft.map((x, j) => (j === i ? { ...x, maintenance_message: e.target.value } : x)))} />
              </div>
            ))}
            {railDraft.length > 0 && (
              <Btn onClick={() => act(() => api.put("/admin/god-mode/payment-rails", { reason, rails: railDraft.map(({ provider, deposits_enabled, withdrawals_enabled, is_live, maintenance_message }) => ({ provider, deposits_enabled, withdrawals_enabled, is_live, maintenance_message })) }), "Bank switches saved")}>Save bank switches</Btn>
            )}
          </div>
          {wcDraft && (
            <div className="space-y-2 rounded-md border border-white/10 p-3">
              <p className="text-xs font-bold uppercase text-emerald-300">Who can cash out</p>
              <select className="gx-input" value={wcDraft.processor_mode} onChange={(e) => setWcDraft({ ...wcDraft, processor_mode: e.target.value })}>
                <option value="manual_bank_transfer">Manual bank transfer</option>
                <option value="automatic_gateway">Automatic gateway</option>
              </select>
              {(["egame_withdrawals_enabled", "trade_withdrawals_enabled", "deposits_via_bank_transfer", "payouts_via_bank_transfer"] as const).map((k) => (
                <Toggle key={k} text={label(k)} on={Boolean(wcDraft[k])} onChange={(v) => setWcDraft({ ...wcDraft, [k]: v })} />
              ))}
              <Btn onClick={() => act(() => api.put("/admin/god-mode/withdrawal-controls", { egame_withdrawals_enabled: wcDraft.egame_withdrawals_enabled, trade_withdrawals_enabled: wcDraft.trade_withdrawals_enabled, processor_mode: wcDraft.processor_mode, deposits_via_bank_transfer: wcDraft.deposits_via_bank_transfer, payouts_via_bank_transfer: wcDraft.payouts_via_bank_transfer, reason }), "Cash-out rules saved")}>Save cash-out rules</Btn>
            </div>
          )}
        </div>
      </Panel>
      <Panel eyebrow="Exchange rate" title="Naira rate and trader limits">
        <SettingsEditor title="Treasury settings" path="/admin/treasury/settings" />
      </Panel>
      <BankAccounts />
      <Panel eyebrow="Market help" title="Buy a player share from someone, or sell one to them">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          <div>
            <label className="gx-label">Action</label>
            <select className="gx-input" value={iv.action} onChange={(e) => setIv({ ...iv, action: e.target.value })}>
              <option value="buy_from_user">Buy from user</option>
              <option value="sell_to_user">Sell to user</option>
            </select>
          </div>
          <Field name="User ID" value={iv.user_id} onChange={(v) => setIv({ ...iv, user_id: v })} />
          <Field name="Player ID" value={iv.player_id} onChange={(v) => setIv({ ...iv, player_id: v })} />
          <Field name="Quantity" type="number" value={iv.quantity} onChange={(v) => setIv({ ...iv, quantity: v })} />
          <Field name="Unit price (GTX)" type="number" value={iv.unit_price_credits} onChange={(v) => setIv({ ...iv, unit_price_credits: v })} />
          <Field name="Type CONFIRM-LIQUIDITY" value={iv.confirmation_text} onChange={(v) => setIv({ ...iv, confirmation_text: v })} />
        </div>
        <Btn className="mt-3" variant="danger" onClick={() => act(() => api.post("/admin/god-mode/liquidity/interventions", { ...iv, quantity: Number(iv.quantity), unit_price_credits: Number(iv.unit_price_credits), reason }), "Market trade done")}>Do this trade</Btn>
      </Panel>
      <Panel eyebrow="Platform cash-out" title="Send platform coin to a bank account">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.keys(wd).map((k) => (
            <Field key={k} name={label(k)} value={wd[k]} type={k.startsWith("amount") ? "number" : "text"} onChange={(v) => setWd({ ...wd, [k]: v })} />
          ))}
        </div>
        <Btn className="mt-3" variant="danger" onClick={() => act(() => api.post("/admin/god-mode/treasury/withdrawals", { ...wd, amount_credits: Number(wd.amount_credits), reason }), "Platform cash-out created")}>Send this to the bank</Btn>
      </Panel>
    </div>
  );
}

function BankAccounts() {
  const act = useAct();
  const { data } = useAdminGet("banks", "/admin/treasury/bank-accounts");
  const [f, setF] = useState({ bank_name: "", account_number: "", account_name: "", bank_code: "", currency_code: "NGN" });
  return (
    <Panel eyebrow="Deposits" title="Platform treasury bank accounts">
      <div className="space-y-2">
        {(data || []).map((a: any) => (
          <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-white/10 p-2 text-sm">
            <span>{a.bank_name} · {a.account_number} · {a.account_name} <Chip tone={a.is_active ? "emerald" : "slate"}>{a.is_active ? "active" : "inactive"}</Chip></span>
            <Btn variant="secondary" onClick={() => act(() => api.put(`/admin/treasury/bank-accounts/${a.id}`, { is_active: !a.is_active }), "Bank account updated")}>{a.is_active ? "Deactivate" : "Activate"}</Btn>
          </div>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">
        {Object.keys(f).map((k) => <Field key={k} name={label(k)} value={(f as any)[k]} onChange={(v) => setF({ ...f, [k]: v })} />)}
      </div>
      <Btn className="mt-3" onClick={() => act(() => api.post("/admin/treasury/bank-accounts", { ...f, bank_code: f.bank_code || null, is_active: true }), "Bank account added")}>Add bank account</Btn>
    </Panel>
  );
}

/* ---------- Tab 2: queues ---------- */
function Queue({ title, path, render }: { title: string; path: string; render: (item: any, act: ReturnType<typeof useAct>) => React.ReactNode }) {
  const { data } = useAdminGet("queue", path);
  const act = useAct();
  const items: any[] = data?.items || [];
  return (
    <Panel eyebrow="Queue" title={`${title} (${data?.total ?? items.length})`}>
      {items.length === 0 ? <Empty title="Queue clear" /> : items.map((it) => <div key={it.id} className="mb-2 flex flex-wrap items-center justify-between gap-3 rounded-md border border-white/10 p-3 text-sm">{render(it, act)}</div>)}
    </Panel>
  );
}

function CreatorApplicationsQueue() {
  const { data, refetch } = useAdminGet("creator-applications", "/admin/creator/applications");
  const act = useAct();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const items = Array.isArray(data) ? data : data?.items || [];

  const handleAction = async (appId: string, action: "approve" | "reject" | "request-verification" | "suspend") => {
    const review_notes = notes[appId] || "";
    await act(
      () => api.post(`/admin/creator/applications/${appId}/${action}`, { review_notes, reason: review_notes || action }),
      `Creator application ${action.replace("-", " ")} successful`
    );
    refetch();
  };

  return (
    <Panel eyebrow="Audience & Creator Verification" title={`Creator Applications (${items.length})`}>
      {items.length === 0 ? (
        <Empty title="No applications" body="Creator applications awaiting audience review will appear here." />
      ) : (
        <div className="space-y-4">
          {items.map((app: any) => (
            <div key={app.application_id} className="rounded-lg border border-white/10 bg-white/[0.02] p-4 text-sm" data-testid={`creator-app-${app.application_id}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-bold text-white">@{app.requested_handle}</span> ({app.display_name}) ·{" "}
                  <span className="capitalize text-pink-300">{app.platform}</span> ·{" "}
                  <b className="text-white">{fmt(app.follower_count)}</b> followers
                </div>
                <Chip tone={app.status === "approved" ? "emerald" : app.status === "rejected" ? "red" : app.status === "suspended" ? "amber" : "blue"}>
                  {label(app.status)}
                </Chip>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                {app.profile_url ? (
                  <a href={app.profile_url} target="_blank" rel="noopener noreferrer" className="text-pink-400 underline hover:text-pink-300">
                    Open Public Profile URL ↗
                  </a>
                ) : (
                  <span>No profile URL</span>
                )}
                {app.selfie_attachment_id && (
                  <span className="text-emerald-400">Live Selfie Attached</span>
                )}
                <span>Submitted: {new Date(app.created_at).toLocaleDateString()}</span>
              </div>

              {app.review_notes && (
                <p className="mt-2 text-xs text-slate-300 bg-slate-800/40 p-2 rounded">
                  Notes: {app.review_notes}
                </p>
              )}

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <input
                  className="gx-input flex-1 min-w-[200px] py-1 text-xs"
                  placeholder="Review notes / feedback..."
                  value={notes[app.application_id] || ""}
                  onChange={(e) => setNotes({ ...notes, [app.application_id]: e.target.value })}
                />
                <Btn onClick={() => handleAction(app.application_id, "approve")}>Approve</Btn>
                <Btn variant="secondary" onClick={() => handleAction(app.application_id, "request-verification")}>Request More Info</Btn>
                <Btn variant="danger" onClick={() => handleAction(app.application_id, "reject")}>Reject</Btn>
                {app.status === "approved" && (
                  <Btn variant="ghost" onClick={() => handleAction(app.application_id, "suspend")}>Suspend</Btn>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function CoinTraderDeskAdminQueue() {
  const { data, refetch } = useAdminGet("admin-coin-traders", "/api/coin-traders");
  const act = useAct();
  const traders = Array.isArray(data) ? data : data?.items || [];

  const handleTraderStatus = async (profileId: string, action: "suspend" | "reinstate") => {
    await act(
      () => api.post(`/api/admin/coin-traders/${profileId}/${action}`, { reason: `Admin ${action}` }),
      `Trader ${action} successful`
    );
    refetch();
  };

  return (
    <Panel eyebrow="Desk compliance" title={`Coin Traders & Verification (${traders.length})`}>
      {traders.length === 0 ? (
        <Empty title="No coin traders" />
      ) : (
        <div className="space-y-3">
          {traders.map((t: any) => {
            const isVerified = Boolean(t.verified_at);
            const isSuspended = Boolean(t.suspended_at) || t.status === "suspended";
            return (
              <div key={t.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 p-3 text-sm" data-testid={`admin-trader-${t.id}`}>
                <div>
                  <span className="font-bold text-white">{t.display_name}</span> · Tier: <span className="capitalize">{t.tier}</span> ·{" "}
                  <Chip tone={isVerified ? "emerald" : "gold"}>{isVerified ? `Verified (${t.verification_provider || "kyc"})` : "Unverified"}</Chip>{" "}
                  {isSuspended && <Chip tone="red">Suspended</Chip>}
                </div>
                <div className="flex gap-2">
                  {!isSuspended ? (
                    <Btn variant="danger" onClick={() => handleTraderStatus(t.id, "suspend")}>Suspend Desk</Btn>
                  ) : (
                    <Btn onClick={() => handleTraderStatus(t.id, "reinstate")}>Reinstate Desk</Btn>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
export function QueuesTab() {
  return (
    <div className="space-y-6" data-testid="admin-tab-queues">
      <CreatorApplicationsQueue />
      <CoinTraderDeskAdminQueue />
      <Queue title="Pending fiat deposits" path="/admin/treasury/deposits?status=payment_submitted" render={(d, act) => (
        <>
          <span>{d.user_email} · {fmt(d.amount_fiat)} {d.currency_code} → {fmt(d.amount_coin)} GTX · {d.payer_name || "—"} · ref {d.reference}</span>
          <div className="flex gap-2">
            <Btn onClick={() => act(() => api.post(`/admin/treasury/deposits/${d.id}/confirm`, {}), "Deposit confirmed & credited")}>Confirm</Btn>
            <Btn variant="danger" onClick={() => act(() => api.post(`/admin/treasury/deposits/${d.id}/reject`, {}), "Deposit rejected")}>Reject</Btn>
          </div>
        </>
      )} />
      <Queue title="Treasury withdrawals" path="/admin/treasury/withdrawals?status=pending_review" render={(w, act) => (
        <>
          <span>{w.user_email} · {fmt(w.amount_coin)} GTX → {w.bank_name} {w.bank_account_number} · {w.status}</span>
          <div className="flex gap-2">
            {["approved", "processing", "paid", "rejected"].map((s) => (
              <Btn key={s} variant={s === "rejected" ? "danger" : "secondary"} onClick={() => act(() => api.post(`/admin/treasury/withdrawals/${w.id}/status`, { status: s }), `Withdrawal ${s}`)}>{label(s)}</Btn>
            ))}
          </div>
        </>
      )} />
      <Queue title="KYC review" path="/admin/treasury/kyc?status=under_review" render={(k, act) => (
        <>
          <span>{k.user_email} · {k.user_full_name || "—"} · {k.country} · {k.status}</span>
          <div className="flex gap-2">
            <Btn onClick={() => act(() => api.post(`/admin/treasury/kyc/${k.id}/review`, { status: "approved" }), "KYC approved")}>Approve</Btn>
            <Btn variant="danger" onClick={() => act(() => api.post(`/admin/treasury/kyc/${k.id}/review`, { status: "rejected", rejection_reason: "Documents unclear" }), "KYC rejected")}>Reject</Btn>
          </div>
        </>
      )} />
      <Queue title="Open disputes" path="/admin/treasury/disputes" render={(d) => <span>{d.reference} · {d.subject} · {d.user_email} · <Chip>{label(d.status)}</Chip></span>} />
    </div>
  );
}

/* ---------- Tab 3: players ---------- */
export function PlayersTab() {
  const act = useAct();
  const [q, setQ] = useState("");
  const [tier, setTier] = useState("");
  const [sel, setSel] = useState<any>(null);
  const [edit, setEdit] = useState<Record<string, any>>({});
  const path = `/admin/players?limit=24${q ? `&search=${encodeURIComponent(q)}` : ""}${tier ? `&tier=${tier}` : ""}`;
  const { data, refetch } = useAdminGet("players", path);
  useEffect(() => setEdit({}), [sel?.player_id]);
  const val = (k: string) => edit[k] ?? sel?.[k] ?? "";
    const save = async () => {
    const body: Record<string, any> = {};
    ["overall", "potential", "age"].forEach((k) => edit[k] !== undefined && edit[k] !== "" && (body[k] = Number(edit[k])));
    if (edit.market_value_credits !== undefined && edit.market_value_credits !== "") body.market_value_credits = Number(edit.market_value_credits);
    ["real_player_tier", "real_world_club_name", "image_url"].forEach((k) => edit[k] !== undefined && (body[k] = edit[k]));
    if (edit.is_tradable !== undefined) body.is_tradable = edit.is_tradable;
    if (!Object.keys(body).length) return toast.info("No changes");
    const res = await act(() => api.patch(`/admin/players/${sel.player_id}`, { ...body, reason: "Admin console edit" }), "Player updated");
    if (res?.data?.player) setSel(res.data.player);
    refetch();
  };
  return (
    <div className="grid gap-6 lg:grid-cols-2" data-testid="admin-tab-players">
      <Panel eyebrow="Search" title="Legends, real players & regens">
        <div className="flex gap-2">
          <input className="gx-input flex-1" placeholder="Search name or player id" value={q} onChange={(e) => setQ(e.target.value)} />
          <select className="gx-input w-40" value={tier} onChange={(e) => setTier(e.target.value)}>
            <option value="">All tiers</option>
            {["legend", "marquee", "established", "wonderkid", "regen"].map((t) => <option key={t} value={t}>{label(t)}</option>)}
          </select>
        </div>
        <div className="mt-3 max-h-[520px] space-y-1 overflow-y-auto">
          {(data || []).map((p: any) => (
            <button key={p.player_id} onClick={() => setSel(p)} className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm ${sel?.player_id === p.player_id ? "border-emerald-400/60 bg-emerald-500/10" : "border-white/10 hover:border-white/30"}`}>
              <span className="truncate text-white">{p.full_name} <span className="text-slate-500">· {p.real_world_club_name || p.current_club_name || "—"}</span></span>
              <span className="gx-mono text-xs text-emerald-300">{p.overall ?? "–"} · {p.real_player_tier || (p.is_regen ? "regen" : "—")}</span>
            </button>
          ))}
          {data?.length === 0 && <Empty title="No players match" />}
        </div>
      </Panel>
      <Panel eyebrow="Editor" title={sel ? sel.full_name : "Select a player"}>
        {!sel ? <Empty title="Search a player, then edit age, GSI and cost" /> : (
          <div className="space-y-3">
            <div className="mx-auto w-48">
              <PlayerCard name={sel.full_name} rating={Number(val("overall")) || 60} position={sel.position} club={sel.real_world_club_name || sel.current_club_name} image={val("image_url") || null} regen={sel.is_regen} tier={sel.real_player_tier === "legend" ? "legendary" : undefined} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Field name="Age" type="number" value={val("age")} onChange={(v) => setEdit({ ...edit, age: v })} testid="admin-player-age" />
              <Field name="GSI" type="number" value={val("overall")} onChange={(v) => setEdit({ ...edit, overall: v })} testid="admin-player-gsi" />
              <Field name="Potential GSI" type="number" value={val("potential")} onChange={(v) => setEdit({ ...edit, potential: v })} />
              <div>
                <label className="gx-label">Tier</label>
                <select className="gx-input" value={val("real_player_tier")} onChange={(e) => setEdit({ ...edit, real_player_tier: e.target.value })}>
                  <option value="">None</option>
                  {["legend", "marquee", "established", "wonderkid"].map((t) => <option key={t} value={t}>{label(t)}</option>)}
                </select>
              </div>
              <Field name="Real-world club" value={val("real_world_club_name")} onChange={(v) => setEdit({ ...edit, real_world_club_name: v })} />
              <Field name="Cost (GTEX)" type="number" value={edit.market_value_credits ?? sel.current_value_credits ?? ""} onChange={(v) => setEdit({ ...edit, market_value_credits: v })} testid="admin-player-cost" />
              <Toggle text="Tradable" on={Boolean(edit.is_tradable ?? sel.is_tradable)} onChange={(v) => setEdit({ ...edit, is_tradable: v })} />
            </div>
            <Field name="Headshot URL (empty = clean silhouette)" value={val("image_url")} onChange={(v) => setEdit({ ...edit, image_url: v })} />
            <div className="flex gap-2">
              <Btn onClick={save}>Save player</Btn>
              <Btn variant="ghost" onClick={() => setEdit({ ...edit, image_url: "" })}>Clear portrait</Btn>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}

/* ---------- Tab 4: competitions / jackpot / kill-switch ---------- */
const JACKPOT_FIELDS: { key: string; name: string }[] = [
  { key: "threshold_amount", name: "Pay out when the pot reaches" },
  { key: "contribution_rate", name: "Share of fees that fill the pot" },
  { key: "distribution_mode", name: "How winners split the pot" },
  { key: "failsafe_hours", name: "Hours before a stuck round is paid anyway" },
  { key: "probability_limit", name: "Win-chance limit" },
  { key: "probability_cap", name: "Maximum win chance" },
  { key: "top_split_percent", name: "Percent for the top winners" },
  { key: "min_activity_score", name: "Minimum play needed to qualify" },
];

const PLAY_PRICES: { key: string; title: string; hint: string }[] = [
  { key: "tournament-entry", title: "User-hosted tournament", hint: "What a player pays to play a user-hosted tournament." },
  { key: "fast-match-entry", title: "Quick match", hint: "What a player pays to play a quick match after the free run." },
  { key: "competitive-match-entry", title: "Competitive match", hint: "What a player pays to play a competitive match." },
];

export function LaunchMatchPanel() {
  const act = useAct();
  const { data: flags, refetch: refetchFlags } = useAdminGet<any[]>("flags", "/admin/admin-engine/feature-flags");
  const { data: prices, refetch: refetchPrices } = useAdminGet<any[]>("play-prices", "/economy/service-pricing");
  const flag = (flags || []).find((item: any) => item.feature_key === "match_3d_gameplay");
  const threeD = Boolean(flag?.enabled);
  const [draft, setDraft] = useState<Record<string, { coin?: string; fan?: string }>>({});
  const ruleFor = (key: string) => (prices || []).find((item: any) => item.service_key === key);
  const shown = (key: string, field: "coin" | "fan") => {
    const edited = draft[key]?.[field];
    if (edited !== undefined) return edited;
    const rule = ruleFor(key);
    if (!rule) return "";
    return String(field === "coin" ? rule.price_coin : rule.price_fancoin_equivalent);
  };
  const setPrice = (key: string, field: "coin" | "fan", value: string) => {
    setDraft({ ...draft, [key]: { ...draft[key], [field]: value } });
  };
  const savePrice = (key: string) => {
    const meta = PLAY_PRICES.find((item) => item.key === key);
    const rule = ruleFor(key);
    return act(
      () =>
        api.post("/admin/economy/service-pricing", {
          service_key: key,
          title: rule?.title || meta?.title || key,
          description: meta?.hint || rule?.description || "",
          price_coin: shown(key, "coin") === "" ? "0" : shown(key, "coin"),
          price_fancoin_equivalent: shown(key, "fan") === "" ? "0" : shown(key, "fan"),
          active: true,
        }),
      "Play price saved"
    ).then(() => refetchPrices());
  };
  return (
    <Panel eyebrow="Launch" title="2D matches, 3D switch, and play prices" testid="admin-launch-match">
      <p className="mb-3 text-sm leading-relaxed text-slate-400">
        Public matches play on the 2D pitch. Turn 3D on only when that gameplay is ready. Official GTEX competitions stay free to enter. The prices below are what players pay to play a user-hosted tournament or a paid match. They start at 0.
      </p>
      <Toggle
        testid="admin-3d-gameplay-toggle"
        text={threeD ? "3D gameplay is on" : "3D gameplay is off. All matches are 2D"}
        on={threeD}
        onChange={() =>
          act(
            () =>
              api.post("/admin/admin-engine/feature-flags", {
                feature_key: "match_3d_gameplay",
                title: "3D gameplay",
                description: "Public matches stay on the 2D pitch until an admin turns 3D gameplay on.",
                enabled: !threeD,
                audience: "global",
              }),
            threeD ? "3D gameplay turned off" : "3D gameplay turned on"
          ).then(() => refetchFlags())
        }
      />
      <div className="mt-4 space-y-3">
        {PLAY_PRICES.map((item) => (
          <div key={item.key} className="rounded-md border border-white/10 p-3" data-testid={`admin-play-price-${item.key}`}>
            <p className="text-sm font-bold text-white">{item.title}</p>
            <p className="mb-2 text-xs text-slate-400">{item.hint}</p>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
              <Field name="GTEX" type="number" value={shown(item.key, "coin")} onChange={(v) => setPrice(item.key, "coin", v)} />
              <Field name="Fan Coin" type="number" value={shown(item.key, "fan")} onChange={(v) => setPrice(item.key, "fan", v)} />
              <div className="flex items-end">
                <Btn onClick={() => savePrice(item.key)}>Save price</Btn>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function CompetitionsTab({ children }: { children?: React.ReactNode }) {
  const act = useAct();
  const { data: rt } = useAdminGet("jackpot", "/admin/jackpot/runtime");
  const { data: ks } = useAdminGet("ks", "/admin/finance/match-kill-switches");
  const [jd, setJd] = useState<Record<string, any>>({});
  const [bal, setBal] = useState("");
  const [m, setM] = useState({ match_id: "", reason: "" });
  const src = useMemo(() => ({ ...(rt?.settings || {}), ...(rt || {}) }), [rt]);
  const jv = (k: string) => jd[k] ?? src[k] ?? "";
  return (
    <div className="space-y-6" data-testid="admin-tab-competitions">
      {children}
      <LaunchMatchPanel />
      <NamedCupPrizePanel />
      <Panel eyebrow="Jackpot" title="Fill the pot and choose when it pays">
        <p className="mb-3 text-sm leading-relaxed text-slate-400">
          Players cannot add money here. Type the new pot total and press &quot;Set the pot to this amount&quot;. That moves coin from the platform into the jackpot. A smaller number moves the difference back. Save the rules only when you change how it pays. Paying now sends the current pot to the winners.
        </p>
        <div className="mb-3 grid grid-cols-2 gap-4 md:grid-cols-3">
          <Stat label="Coin in the pot now" value={fmt(src.current_balance ?? src.balance ?? 0)} />
          <Stat label="Round" value={String(src.round_number ?? src.current_round ?? "—")} />
          <Stat label="Pays out at" value={fmt(src.threshold_amount ?? 0)} />
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {JACKPOT_FIELDS.map((f) => <Field key={f.key} name={f.name} value={jv(f.key)} onChange={(v) => setJd({ ...jd, [f.key]: v })} />)}
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <Btn onClick={() => {
            const body: any = {};
            Object.entries(jd).forEach(([k, v]) => (body[k] = k === "distribution_mode" ? v : Number(v)));
            return act(() => api.post("/admin/jackpot/runtime", body), "Jackpot rules saved");
          }}>Save jackpot rules</Btn>
          <input className="gx-input w-48" type="number" placeholder="New pot total" value={bal} onChange={(e) => setBal(e.target.value)} />
          <Btn variant="secondary" onClick={() => act(() => api.patch("/admin/jackpot/balance", { balance: Number(bal), reason: "Admin balance adjustment" }), "Jackpot amount set")}>Set the pot to this amount</Btn>
          <Btn variant="gold" onClick={() => window.confirm("Pay the current jackpot to the winners now?") && act(() => api.post("/admin/jackpot/trigger"), "Jackpot paid")}>Pay the jackpot now</Btn>
        </div>
      </Panel>
      <Panel eyebrow="Emergency" title="Stop a live match">
        <div className="flex flex-wrap gap-2">
          <input className="gx-input w-64" placeholder="Match ID" value={m.match_id} onChange={(e) => setM({ ...m, match_id: e.target.value })} />
          <input className="gx-input flex-1" placeholder="Reason" value={m.reason} onChange={(e) => setM({ ...m, reason: e.target.value })} />
          <Btn variant="danger" onClick={() => act(() => api.post("/admin/finance/match-kill-switches", { match_id: m.match_id, enabled: true, reason: m.reason || "Emergency stop" }), "Match halted")}>Stop this match</Btn>
        </div>
        <div className="mt-3 space-y-1">
          {(ks || []).map((k: any) => (
            <div key={k.match_id} className="flex items-center justify-between rounded-md border border-white/10 p-2 text-sm">
              <span>{k.match_id} · {k.reason || "—"} <Chip tone={k.enabled ? "red" : "slate"}>{k.enabled ? "halted" : "released"}</Chip></span>
              <Btn variant="secondary" onClick={() => act(() => api.post("/admin/finance/match-kill-switches", { match_id: k.match_id, enabled: !k.enabled, reason: k.reason }), "Match stop updated")}>{k.enabled ? "Let it play" : "Stop it again"}</Btn>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

/* ---------- Tab 5: economy ---------- */
export function EconomyTab() {
  const act = useAct();
  const { data: ct } = useAdminGet("ct", "/admin/finance/control-tower");
  const { data: wp } = useAdminGet("wp", "/admin/finance/wallet-protection");
  const { data: rec } = useAdminGet("rec", "/admin/finance/reconciliation");
  const { data: flags } = useAdminGet("flags", "/admin/admin-engine/feature-flags");
  const { data: rewards } = useAdminGet("rewards", "/admin/admin-engine/reward-rules");
  const [sim, setSim] = useState<any>({ daily_active_users: 100000, avg_matches_per_user: 5, fan_spend_per_match: 10, gtex_purchase_rate: 0.02, gtex_purchase_amount: 1 });
  const [simRes, setSimRes] = useState<any>(null);
  return (
    <div className="space-y-6" data-testid="admin-tab-economy">
      <LaunchMatchPanel />
      <Panel eyebrow="Coin" title="How much coin is out there">
        <p className="mb-3 text-sm leading-relaxed text-slate-400">This page watches the coin already created. It does not print new coin. Coin appears when GTEX pays a prize, a reward, or the jackpot.</p>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="GTEX coin in circulation" value={fmt(ct?.gtex_supply ?? 0)} />
          <Stat label="Fan coin in circulation" value={fmt(ct?.fan_supply ?? 0)} />
          <Stat label="Inflation risk" value={String(ct?.inflation_risk ?? "—")} tone={ct?.inflation_risk === "high" ? "bad" : "good"} />
          <Stat label="Liquidity" value={String(ct?.liquidity_status ?? "—")} />
          <Stat label="Frozen / banned" value={`${ct?.frozen_account_count ?? 0} / ${ct?.banned_account_count ?? 0}`} />
          <Stat label="Price overrides" value={String(ct?.manual_price_override_count ?? 0)} />
          <Stat label="Matches stopped" value={String(ct?.match_kill_switch_count ?? 0)} />
          <Stat label="Wallet locks" value={String(wp?.active_wallet_transaction_lock_count ?? 0)} />
        </div>
        {(ct?.alerts || []).map((a: any, i: number) => <p key={i} className="mt-2 text-xs text-amber-300">⚠ {a.title}: {a.message}</p>)}
        <p className="mt-3 text-xs text-slate-400">Reconciliation: {rec?.issues?.length ?? 0} open issues · {rec?.duplicate_provider_references ?? 0} duplicate refs · {rec?.confirmed_deposits_missing_ledger ?? 0} deposits missing ledger</p>
      </Panel>
      <Panel eyebrow="What-if" title="Guess the next 30 days of coin">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
          {Object.keys(sim).map((k) => <Field key={k} name={label(k)} type="number" value={sim[k]} onChange={(v) => setSim({ ...sim, [k]: Number(v) })} />)}
        </div>
        <Btn className="mt-3" onClick={async () => { const r = await act(() => api.post("/admin/finance/simulate", sim), "Guess finished"); if (r) setSimRes(r.data); }}>Run the 30-day guess</Btn>
        {simRes && <p className="mt-3 text-sm text-slate-200">Ending GTX supply {fmt(simRes.summary?.ending_gtex_supply)} · risk <b>{simRes.summary?.inflation_risk}</b> · {(simRes.summary?.recommendations || []).join(" ")}</p>}
      </Panel>
      <Panel eyebrow="Switches" title="Turn features on or off">
        {(flags || []).length === 0 && <Empty title="No flags" />}
        <div className="grid gap-2 md:grid-cols-2">
          {(flags || []).map((f: any) => (
            <Toggle key={f.id || f.feature_key} text={f.title || f.feature_key} on={Boolean(f.enabled)} onChange={(v) => act(() => api.post("/admin/admin-engine/feature-flags", { feature_key: f.feature_key, title: f.title || f.feature_key, description: f.description, enabled: v, audience: f.audience || "global" }), "Flag updated")} />
          ))}
        </div>
      </Panel>
      <Panel eyebrow="Fees" title="The fee rules that are live">
        {(rewards || []).map((r: any) => (
          <div key={r.id} className="mb-2 rounded-md border border-white/10 p-3 text-sm">
            <b className="text-white">{r.title}</b> <Chip tone={r.active ? "emerald" : "slate"}>{r.active ? "active" : "inactive"}</Chip>
            <p className="gx-mono text-xs text-slate-400">trade {r.trading_fee_bps} bps · gift rake {r.gift_platform_rake_bps} · withdrawal {r.withdrawal_fee_bps} · competition {r.competition_platform_fee_bps}</p>
          </div>
        ))}
      </Panel>
    </div>
  );
}

/* ---------- Tab 6: users / admins / audit ---------- */
export function UsersTab() {
  const act = useAct();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<any>(null);
  const [ctl, setCtl] = useState<any>({ freeze_login: false, freeze_wallet: false, freeze_matches: false, freeze_social: false, ban_account: false, reason: "" });
  const { data: users } = useAdminGet("users", `/admin/finance/users?search=${encodeURIComponent(q)}&limit=20`);
  const { data: admins } = useAdminGet("admins", "/admin/access");
  const { data: perms } = useAdminGet("perms", "/admin/access/permissions");
  const [auditQ, setAuditQ] = useState("");
  const { data: audit } = useAdminGet("audit", `/admin/god-mode/audit-events?limit=40${auditQ ? `&query=${encodeURIComponent(auditQ)}` : ""}`);
  const [na, setNa] = useState({ email: "", username: "", password: "" });
  return (
    <div className="space-y-6" data-testid="admin-tab-users">
      <Panel eyebrow="Accounts" title="Find user & apply controls">
        <input className="gx-input" placeholder="Search email, username or ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
          {(users || []).map((u: any) => (
            <button key={u.id} onClick={() => setSel(u)} className={`flex w-full justify-between rounded-md border px-3 py-1.5 text-left text-sm ${sel?.id === u.id ? "border-emerald-400/60" : "border-white/10"}`}>
              <span>{u.display_name || u.username} · {u.email}</span>
              <span className="text-xs text-slate-400">{u.role} · KYC {u.kyc_status || "—"} {!u.is_active && <Chip tone="red">banned</Chip>}</span>
            </button>
          ))}
        </div>
        {sel && (
          <div className="mt-3 space-y-2">
            <p className="text-sm text-white">Target: <b>{sel.email}</b> <span className="gx-mono text-xs text-slate-500">{sel.id}</span></p>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
              {(["freeze_login", "freeze_wallet", "freeze_matches", "freeze_social", "ban_account"] as const).map((k) => <Toggle key={k} text={label(k)} on={Boolean(ctl[k])} onChange={(v) => setCtl({ ...ctl, [k]: v })} />)}
            </div>
            <input className="gx-input" placeholder="Reason" value={ctl.reason} onChange={(e) => setCtl({ ...ctl, reason: e.target.value })} />
            <Btn variant="danger" onClick={() => act(() => api.post("/admin/finance/account-controls", { ...ctl, user_id: sel.id }), "Account controls applied")}>Apply controls</Btn>
          </div>
        )}
      </Panel>
      <Panel eyebrow="Admin roles" title="Scoped admin accounts">
        {(admins || []).map((a: any) => (
          <div key={a.id} className="mb-2 rounded-md border border-white/10 p-3 text-sm">
            <b className="text-white">{a.email}</b> · {a.admin_role_name} {a.role === "super_admin" && <Chip tone="gold">super</Chip>}
            <p className="gx-mono text-[11px] text-slate-400">{(a.permissions || []).join(", ")}</p>
          </div>
        ))}
        <div className="grid grid-cols-3 gap-2">
          {Object.keys(na).map((k) => <Field key={k} name={label(k)} type={k === "password" ? "password" : "text"} value={(na as any)[k]} onChange={(v) => setNa({ ...na, [k]: v })} />)}
        </div>
        <Btn className="mt-3" onClick={() => act(() => api.post("/admin/access", { ...na, permissions: (perms?.permissions || []).slice(0, 0) }), "Admin created (assign permissions after)")}>Create scoped admin</Btn>
      </Panel>
      <Panel eyebrow="Log" title="What admins changed">
        <input className="gx-input mb-2" placeholder="Search audit events" value={auditQ} onChange={(e) => setAuditQ(e.target.value)} />
        <div className="max-h-80 space-y-1 overflow-y-auto text-xs">
          {(audit || []).map((ev: any, i: number) => (
            <div key={ev.event_id || i} className="border-b border-white/5 pb-1">
              <span className="font-semibold text-emerald-300">{label(ev.event_type || ev.action_key || "event")}</span>
              <span className="ml-2 text-slate-400">{ev.summary || ev.reason || ev.detail || ""}</span>
            </div>
          ))}
          {(audit || []).length === 0 && <Empty title="No events" />}
        </div>
      </Panel>
    </div>
  );
}

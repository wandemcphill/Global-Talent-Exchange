import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";

function Balances({ w }: any) {
  const rows = [
    ["withdrawable", "Withdrawable", "good"], ["non_withdrawable", "Non-withdrawable", "default"], ["earned", "Earned", "default"],
    ["deposited", "Deposited", "default"], ["promotional", "Promotional", "warn"], ["pending_review", "Pending review", "warn"],
  ];
  return (
    <Panel eyebrow="Owner wallet · labelled balances" title="Balances" testid="balances-panel" className="lg:col-span-12">
      <div className="grid grid-cols-2 gap-6 md:grid-cols-4 lg:grid-cols-8">
        <Stat label="GTEX Coin total" value={<Coin amount={w.gtex_total} />} testid="balance-gtex-total" />
        <Stat label="Fan Coin" value={<Coin amount={w.fan_total} currency="FAN" />} testid="balance-fan-total" />
        {rows.map(([k, l, tone]) => <Stat key={k} label={l} value={fmt(w[k])} tone={tone} testid={`balance-${k}`} />)}
      </div>
      <p className="mt-4 text-xs text-slate-500">GTEX Coin powers the club economy. Fan Coin is for gifting and fan actions and is never withdrawable. Promotional grants can be spent but not withdrawn.</p>
    </Panel>
  );
}

function Deposit({ configured, rate, mode }: any) {
  const [amount, setAmount] = useState("5000");
  const go = async () => {
    try {
      const { data } = await api.post("/owner/deposits/init", { amount_ngn: Number(amount), callback_url: `${window.location.origin}/payment/callback` });
      window.location.href = data.authorization_url;
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Paystack · NGN" title="Deposit" testid="deposit-panel" className="lg:col-span-4">
      <label className="gx-label">Amount (₦)</label>
      <input data-testid="deposit-amount-input" className="gx-input" type="number" min={100} value={amount} onChange={(e) => setAmount(e.target.value)} />
      <p className="mt-2 text-xs text-slate-400" data-testid="deposit-preview">You receive <b className="text-white">{fmt(Number(amount || 0) / Number(rate || 100), 2)} GTX</b> at ₦{fmt(rate)} = 1 GTEX Coin {mode === "live" && <Chip tone="red">Live payments</Chip>}</p>
      <Btn className="mt-3 w-full" disabled={!configured} onClick={go} data-testid="deposit-button">Pay with Paystack</Btn>
      {!configured && <p className="mt-2 text-xs text-amber-300" data-testid="paystack-not-configured">Paystack keys are not connected yet, so Naira deposits are switched off.</p>}
      <p className="mt-2 text-xs text-slate-500">Deposits credit your wallet as "deposited" GTEX Coin after Paystack verification.</p>
    </Panel>
  );
}

function Withdraw({ rate }: any) {
  const refresh = useRefreshOwner();
  const [f, setF] = useState<any>({ amount_coin: "", bank_name: "", account_number: "", account_name: "" });
  const { data: elig } = useQuery({ queryKey: ["finance", "elig", f.amount_coin], queryFn: async () => (await api.get("/owner/withdrawals/eligibility", { params: { amount: Number(f.amount_coin) || 1 } })).data });
  const submit = async () => {
    try {
      await api.post("/owner/withdrawals", { ...f, amount_coin: Number(f.amount_coin) });
      toast.success("Withdrawal submitted for review");
      refresh();
    } catch (e: any) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Payout · reviewed" title="Withdraw" testid="withdraw-panel" className="lg:col-span-8">
      <div className="grid gap-3 md:grid-cols-4">
        <input data-testid="withdraw-amount-input" className="gx-input" placeholder="Amount (GTX)" value={f.amount_coin} onChange={(e) => setF({ ...f, amount_coin: e.target.value })} />
        <input data-testid="withdraw-bank-input" className="gx-input" placeholder="Bank" value={f.bank_name} onChange={(e) => setF({ ...f, bank_name: e.target.value })} />
        <input data-testid="withdraw-account-number-input" className="gx-input" placeholder="10-digit NUBAN" value={f.account_number} onChange={(e) => setF({ ...f, account_number: e.target.value })} />
        <input data-testid="withdraw-account-name-input" className="gx-input" placeholder="Account name" value={f.account_name} onChange={(e) => setF({ ...f, account_name: e.target.value })} />
      </div>
      {elig && (
        <div className="mt-4 flex flex-wrap gap-2" data-testid="withdraw-eligibility">
          {Object.entries(elig.checks).map(([k, v]: any) => <Chip key={k} tone={v ? "emerald" : "red"}>{label(k)}</Chip>)}
          <Chip tone="blue">Integrity {elig.integrity_score}</Chip>
          <Chip>KYC {elig.kyc_status} · required above {fmt(elig.kyc_threshold)}</Chip>
        </div>
      )}
      <Btn className="mt-4" disabled={!elig?.eligible || !f.amount_coin} onClick={submit} data-testid="withdraw-submit-button">Request withdrawal{f.amount_coin ? ` · ₦${fmt(Number(f.amount_coin) * Number(rate || 100))}` : ""}</Btn>
      <p className="mt-2 text-xs text-slate-500">Payouts follow the platform processor mode (manual bank transfer): an admin reviews every request, then pays it out to your bank account.</p>
      <p className="mt-2 text-xs text-slate-500">Every withdrawal goes to manual fraud review. Available in: {elig?.supported_countries?.join(", ")}. Only earned and deposited GTEX Coin is withdrawable.</p>
    </Panel>
  );
}

function SupportUnits({ data }: any) {
  const refresh = useRefreshOwner();
  const { data: world } = useQuery({ queryKey: ["world-clubs"], queryFn: async () => (await api.get("/owner/world/clubs")).data.clubs });
  const [club, setClub] = useState("");
  const [units, setUnits] = useState("1");
  const buy = async () => {
    try {
      const { data: r } = await api.post("/owner/support-units/buy", { club_id: club, units: Number(units) });
      toast.success(`You now hold ${r.units} units · ${r.tier}`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Secondary · supporter status" title="Club Support Units" testid="support-units-panel" className="lg:col-span-6">
      <div className="mb-4 flex gap-2 rounded-sm border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
        <ShieldAlert size={16} className="shrink-0" />
        Support Units are supporter memberships. They are not shares, not an investment, and carry no dividends, returns or ownership rights. Any reward pools are discretionary and follow published platform rules.
      </div>
      <div className="flex flex-wrap gap-2">
        <select data-testid="support-club-select" className="gx-input flex-1" value={club} onChange={(e) => setClub(e.target.value)}>
          <option value="">Choose a club</option>
          {(world || []).map((c: any) => <option key={c.club_id} value={c.club_id}>{c.club_name}{c.multi_club_group ? " (multi-club group)" : ""}</option>)}
        </select>
        <input data-testid="support-units-input" className="gx-input w-24" type="number" min={1} value={units} onChange={(e) => setUnits(e.target.value)} />
        <Btn variant="gold" disabled={!club} onClick={buy} data-testid="support-buy-button">Support · {fmt(Number(units) * data.support_unit_price)} GTX</Btn>
      </div>
      <div className="mt-4 space-y-2">
        {data.support_units.map((h: any) => (
          <div key={h.club_id} className="rounded-sm border border-white/5 p-3 text-sm">
            <p className="text-white">{h.club_name} · {h.units} units <Chip tone="gold">{h.tier}</Chip></p>
            <p className="text-xs text-slate-500">{h.benefits.join(" · ")}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function FanCoin({ data }: any) {
  const refresh = useRefreshOwner();
  const [amt, setAmt] = useState("100");
  const buy = async () => {
    try {
      const { data: r } = await api.post("/owner/fan-coin/buy", { amount: Number(amt) });
      toast.success(`+${fmt(r.fan_coin)} Fan Coin`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Secondary · fan rail" title="Fan Coin" testid="fan-coin-panel" className="lg:col-span-6">
      <p className="mb-3 text-sm text-slate-400">Convert GTEX Coin to Fan Coin at 1 : {data.fan_coin_per_gtex} for gifts and fan actions. Fan Coin is non-withdrawable.</p>
      <div className="flex gap-2">
        <input data-testid="fan-coin-amount-input" className="gx-input" type="number" min={1} value={amt} onChange={(e) => setAmt(e.target.value)} />
        <Btn variant="secondary" onClick={buy} data-testid="fan-coin-buy-button">Convert</Btn>
      </div>
    </Panel>
  );
}

function CoinTraders() {
  const { data } = useQuery({ queryKey: ["coin-traders"], queryFn: async () => (await api.get("/coin-traders")).data });
  return (
    <Panel eyebrow="Peer-to-peer · verified traders" title="Coin traders" testid="coin-traders-panel" className="lg:col-span-12">
      <p className="mb-3 text-sm text-slate-400">GTEX also lets you buy or sell GTEX Coin with verified coin traders, in addition to Paystack.</p>
      {(data || []).length === 0 ? <Empty title="No verified traders yet" body="Approved coin traders will appear here." /> : (
        <div className="grid gap-3 md:grid-cols-3">{data.map((t: any) => (
          <div key={t.id} className="rounded-sm border border-white/10 p-3 text-sm" data-testid={`coin-trader-${t.id}`}>
            <p className="text-white">{t.display_name} <Chip tone="emerald">{t.tier}</Chip></p>
            <p className="text-xs text-slate-500">Rating {t.rating} · completion {Math.round(Number(t.completion_rate) * 100)}% · ~{Math.round(t.average_release_minutes)} min release</p>
          </div>))}
        </div>
      )}
    </Panel>
  );
}

function LedgerTable({ rows }: any) {
  return (
    <Panel eyebrow="Single source of truth" title="Unified ledger" testid="ledger-panel" className="lg:col-span-12">
      {rows.length === 0 ? <Empty title="No ledger events yet" /> : (
        <div className="gx-scroll max-h-[520px] overflow-auto">
          <table className="gx-table w-full min-w-[980px]">
            <thead><tr><th>Time</th><th>Event</th><th>From → To</th><th>Cur</th><th>Gross</th><th>Fee</th><th>Net</th><th>Class</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map((e: any) => (
                <tr key={e.id} data-testid={`ledger-row-${e.id}`}>
                  <td className="gx-mono text-xs text-slate-500">{new Date(e.created_at).toLocaleString("en-NG")}</td>
                  <td className="capitalize text-white">{label(e.event_type)}<span className="block text-xs text-slate-500">{e.memo}</span></td>
                  <td className="gx-mono text-[11px] text-slate-400">{e.source_account.split(":")[0]} → {e.destination_account.split(":")[0]}</td>
                  <td><Chip tone={e.currency === "FAN_COIN" ? "gold" : "blue"}>{e.currency === "FAN_COIN" ? "FAN" : "GTX"}</Chip></td>
                  <td className="gx-mono">{fmt(e.gross_amount, 2)}</td>
                  <td className="gx-mono text-slate-500">{fmt(e.platform_fee, 2)}</td>
                  <td className="gx-mono text-white">{fmt(e.net_amount, 2)}</td>
                  <td className="text-xs capitalize">{label(e.balance_class)}</td>
                  <td><Chip tone={e.status === "completed" ? "emerald" : e.status === "reversed" ? "red" : "gold"}>{label(e.status)}</Chip></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function Finance() {
  const { data, isLoading } = useQuery({ queryKey: ["finance"], queryFn: async () => (await api.get("/owner/finance")).data });
  if (isLoading || !data) return <Loading label="Reading the ledger" />;
  return (
    <div data-testid="finance-page">
      <PageHeader eyebrow="Finance" title="Money, clearly labelled" sub="Every total on this page is derived from the unified ledger: gross, platform fee and net for every event." />
      <div className="grid gap-6 lg:grid-cols-12">
        <Balances w={data.wallet} />
        {data.clubs.map((c: any) => (
          <Panel key={c.club_id} eyebrow="Club treasury" title={c.club_name} className="lg:col-span-6" testid={`treasury-${c.club_id}`}>
            <div className="grid grid-cols-3 gap-4">
              <Stat label="Cash" value={<Coin amount={c.cash_gtex} />} />
              <Stat label="Distributable" value={<Coin amount={c.distributable} />} />
              <Stat label="Held payouts" value={<Coin amount={c.pending_payouts} />} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
              {Object.entries(c.earnings_sources).map(([k, v]: any) => <div key={k} className="flex justify-between"><span className="capitalize text-slate-400">{label(k)}</span><span className="gx-mono">{fmt(v)}</span></div>)}
            </div>
          </Panel>
        ))}
        <Deposit configured={data.paystack_configured} rate={data.ngn_per_gtex_coin} mode={data.paystack_mode} />
        <Withdraw rate={data.ngn_per_gtex_coin} />
        {data.withdrawals.length > 0 && (
          <Panel eyebrow="History" title="Withdrawals" className="lg:col-span-12" testid="withdrawals-history">
            {data.withdrawals.map((w: any) => <p key={w.id} className="text-sm text-slate-300">{fmt(w.amount_coin)} GTX → {w.bank_name} ****{w.account_last4} <Chip tone={w.status === "approved" ? "emerald" : w.status === "rejected" ? "red" : "gold"}>{label(w.status)}</Chip></p>)}
          </Panel>
        )}
        <LedgerTable rows={data.ledger} />
        <FanCoin data={data} />
        <SupportUnits data={data} />
        <CoinTraders />
      </div>
    </div>
  );
}

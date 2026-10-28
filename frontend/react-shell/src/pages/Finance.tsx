import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Flame, Megaphone, ShieldAlert, Sparkles, Tv, Trophy } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { publicUrl } from "@/lib/publicPath";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";
import { CoinTraderDesk } from "@/components/gtex/CoinTraderDesk";

function Balances({ w }: any) {
  const rows = [
    ["withdrawable", "Withdrawable", "good"], ["non_withdrawable", "Non-withdrawable", "default"], ["earned", "Earned", "default"],
    ["deposited", "Deposited", "default"], ["promotional", "Promotional", "warn"], ["pending_review", "Pending review", "warn"], ["exchange_activity", "Exchange & traders", "default"],
  ];
  return (
    <Panel eyebrow="Owner wallet · labelled balances" title="Balances" testid="balances-panel" className="lg:col-span-12">
      <div className="grid grid-cols-2 gap-6 md:grid-cols-4 lg:grid-cols-8">
        <Stat label="GTEX Coin total" value={<Coin amount={w.gtex_total} />} testid="balance-gtex-total" />
        <Stat label="Fan Coin" value={<Coin amount={w.fan_total} currency="FAN" />} testid="balance-fan-total" />
        {rows.map(([k, l, tone]) => <Stat key={k} label={l} value={fmt(w[k])} tone={tone} testid={`balance-${k}`} />)}
      </div>
      <p className="mt-4 text-xs text-slate-500">One wallet: this is the same GTEX wallet used by the exchange, coin traders and your clubs. GTEX Coin powers the club economy. Fan Coin is for gifting and fan actions and is never withdrawable. Promotional grants can be spent but not withdrawn.</p>
    </Panel>
  );
}

function Deposit({ configured, rates, mode }: any) {
  const [amount, setAmount] = useState("5000");
  const rate = Number(rates?.deposit_rate || 0);
  const coins = rates?.deposit_direction === "coin_per_fiat" ? Number(amount || 0) * rate : Number(amount || 0) / (rate || 1);
  const go = async () => {
    try {
      const { data } = await api.post("/owner/deposits/init", { amount_ngn: Number(amount), callback_url: `${window.location.origin}${publicUrl("/payment/callback")}` });
      window.location.href = data.authorization_url;
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Paystack · NGN" title="Deposit" testid="deposit-panel" className="lg:col-span-4">
      <label className="gx-label">Amount (₦)</label>
      <input data-testid="deposit-amount-input" className="gx-input" type="number" min={100} value={amount} onChange={(e) => setAmount(e.target.value)} />
      <p className="mt-2 text-xs text-slate-400" data-testid="deposit-preview">You receive <b className="text-white">{fmt(coins, 2)} GTX</b> at the treasury rate of ₦{fmt(rate)} per GTEX Coin {mode === "live" && <Chip tone="red">Live payments</Chip>}</p>
      <Btn className="mt-3 w-full" disabled={!configured} onClick={go} data-testid="deposit-button">Pay with Paystack</Btn>
      {!configured && <p className="mt-2 text-xs text-amber-300" data-testid="paystack-not-configured">Paystack keys are not connected yet, so Naira deposits are switched off.</p>}
      <p className="mt-2 text-xs text-slate-500">Deposits credit your wallet as "deposited" GTEX Coin after Paystack verification.</p>
    </Panel>
  );
}

function Withdraw({ rates }: any) {
  const wRate = Number(rates?.withdrawal_rate || 0);
  const toNgn = (c: number) => (rates?.withdrawal_direction === "coin_per_fiat" ? c / (wRate || 1) : c * wRate);
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
      <Btn className="mt-4" disabled={!elig?.eligible || !f.amount_coin} onClick={submit} data-testid="withdraw-submit-button">Request withdrawal{f.amount_coin ? ` · ₦${fmt(toNgn(Number(f.amount_coin)))}` : ""}</Btn>
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

function SponsorNegotiationDesk({ clubs }: { clubs: any[] }) {
  const [selectedClub, setSelectedClub] = useState("");
  const activeClubId = selectedClub || clubs?.[0]?.club_id || "";
  const refresh = useRefreshOwner();
  const [signingOfferId, setSigningOfferId] = useState<string | null>(null);

  const { data: sponsorData, isLoading, refetch } = useQuery({
    queryKey: ["sponsor-offers", activeClubId],
    queryFn: async () => (await api.get(`/owner/clubs/${activeClubId}/sponsors/offers`)).data,
    enabled: Boolean(activeClubId),
  });

  // Canonical Sponsorship Placement & Ads Feed integration
  const { data: stadiumPlacements } = useQuery({
    queryKey: ["sponsorship-placements", activeClubId],
    queryFn: async () => {
      try {
        const res = await api.post("/sponsorship/placements", {
          home_club_id: activeClubId,
          region_code: "NG",
        });
        return res.data?.placements || [];
      } catch {
        return [];
      }
    },
    enabled: Boolean(activeClubId),
  });

  const { data: sponsoredFeed } = useQuery({
    queryKey: ["sponsored-feed", activeClubId],
    queryFn: async () => {
      try {
        return (await api.get("/feed/sponsored", { params: { limit: 4 } })).data;
      } catch {
        return null;
      }
    },
    enabled: Boolean(activeClubId),
  });

  const handleSign = async (offer: any) => {
    if (!activeClubId) return;
    setSigningOfferId(offer.offer_id);
    try {
      const { data: r } = await api.post(`/owner/clubs/${activeClubId}/sponsors/sign`, { offer_id: offer.offer_id });
      toast.success(
        `Signed sponsorship with ${offer.sponsor_name}! +${fmt(r.upfront_signing_bonus_gtex || offer.upfront_signing_bonus_gtex)} GTX upfront bonus credited.`,
      );
      await refetch();
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSigningOfferId(null);
    }
  };

  if (!activeClubId) return null;

  return (
    <Panel
      eyebrow="Commercial Operations · Seasonal Revenue & Stadium Ad Surfaces"
      title="GM Sponsor Contract Negotiation & Stadium Ad Desk"
      testid="sponsor-negotiation-desk"
      className="lg:col-span-12"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div className="flex flex-wrap items-center gap-3">
          {clubs && clubs.length > 1 && (
            <select
              className="gx-input w-52"
              value={activeClubId}
              onChange={(e) => setSelectedClub(e.target.value)}
              data-testid="sponsor-club-select"
            >
              {clubs.map((c: any) => (
                <option key={c.club_id} value={c.club_id}>
                  {c.club_name}
                </option>
              ))}
            </select>
          )}
          {sponsorData && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400">
                General Manager: <b className="text-white">{sponsorData.gm_name}</b> (Negotiation {sponsorData.gm_negotiation}/20)
              </span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-400">
                Prestige: <b className="text-amber-300">{sponsorData.club_prestige} ({sponsorData.prestige_tier})</b>
              </span>
              {Boolean(sponsorData.active_win_bonus_clause_gtex) && (
                <>
                  <span className="text-slate-600">·</span>
                  <span className="text-emerald-400 font-semibold">
                    Active Win Bonus: +{fmt(sponsorData.active_win_bonus_clause_gtex)} GTX
                  </span>
                </>
              )}
            </div>
          )}
        </div>
        <p className="text-xs text-slate-400">
          Seasonal sponsorship packages negotiated by your General Manager + live stadium surface ad placements.
        </p>
      </div>

      {isLoading || !sponsorData ? (
        <Loading label="GM negotiating seasonal sponsor contracts" />
      ) : (
        <div className="mt-4 space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            {(sponsorData.offers || []).map((offer: any) => {
              const isLocked = Boolean(offer.locked);
              const isSigning = signingOfferId === offer.offer_id;
              return (
                <div
                  key={offer.offer_id}
                  data-testid={`sponsor-offer-card-${offer.offer_id}`}
                  className={`flex flex-col justify-between rounded-xl border p-4.5 transition ${
                    isLocked
                      ? "border-white/5 bg-slate-950/40 opacity-70"
                      : "border-sky-500/20 bg-gradient-to-b from-[#0b1a33]/60 via-[#0a1428]/40 to-black/60 hover:border-sky-400/50"
                  }`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-bold text-white">{offer.sponsor_name}</h4>
                        <p className="text-xs text-sky-300 font-semibold mt-0.5">{offer.slot}</p>
                      </div>
                      <Chip tone={isLocked ? "red" : "gold"}>
                        {offer.strategy_profile?.replace(/_/g, " ")}
                      </Chip>
                    </div>

                    <div className="grid grid-cols-2 gap-2 rounded-lg border border-white/5 bg-black/40 p-2.5 text-xs">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Upfront Bonus</span>
                        <span className="gx-mono text-xs font-black text-emerald-400">
                          +{fmt(offer.upfront_signing_bonus_gtex)} GTX
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Per Match Payout</span>
                        <span className="gx-mono text-xs font-black text-cyan-300">
                          {fmt(offer.per_match_gross_gtex)} GTX
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Win-Bonus Clause</span>
                        <span className="gx-mono text-xs font-black text-amber-300">
                          +{fmt(offer.win_bonus_clause_gtex)} GTX
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Duration / Gate</span>
                        <span className="gx-mono text-xs text-slate-300">
                          {offer.matches_duration} matches · P{offer.min_prestige_required}
                        </span>
                      </div>
                    </div>

                    <div className="rounded-md border border-white/5 bg-slate-900/50 p-2.5 text-[11px] text-slate-300 leading-relaxed italic">
                      <span className="font-semibold not-italic text-amber-300 block mb-0.5">GM Recommendation:</span>
                      "{offer.gm_recommendation}"
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-white/10">
                    {isLocked ? (
                      <button
                        type="button"
                        disabled
                        className="gx-btn w-full opacity-60 cursor-not-allowed text-xs text-rose-300 border-rose-500/30"
                      >
                        Locked · Requires Prestige {offer.min_prestige_required}
                      </button>
                    ) : (
                      <Btn
                        variant="primary"
                        className="w-full text-xs"
                        disabled={Boolean(signingOfferId)}
                        onClick={() => handleSign(offer)}
                        data-testid={`sign-sponsor-${offer.offer_id}`}
                      >
                        {isSigning ? "Signing Contract…" : "Sign Sponsor Deal"}
                      </Btn>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {sponsorData.active_deals && sponsorData.active_deals.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-black/30 p-4">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2.5">
                Active Sponsorship Contracts
              </h5>
              <div className="grid gap-2 sm:grid-cols-2">
                {sponsorData.active_deals.map((deal: any) => (
                  <div
                    key={deal.id}
                    className="flex items-center justify-between rounded-lg border border-white/5 bg-slate-900/40 p-2.5 text-xs"
                  >
                    <div>
                      <p className="font-semibold text-white">{deal.sponsor_name}</p>
                      <p className="text-[11px] text-slate-400">{deal.slot} · {fmt(deal.per_match_gross)} GTX / match</p>
                    </div>
                    <div className="text-right">
                      <Chip tone="emerald">{deal.status}</Chip>
                      <p className="text-[10px] text-slate-400 mt-1">{deal.matches_remaining} matches left</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Canonical Stadium Ad Surfaces & Sponsored Broadcast Feed */}
          <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3" data-testid="stadium-ad-placements">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                <Megaphone size={14} /> Canonical Stadium Surface Ad Placements (/sponsorship/placements)
              </span>
              <Chip tone="cyan">
                {stadiumPlacements?.length || 4} Active Stadium Surfaces
              </Chip>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-4 text-xs">
              {(stadiumPlacements && stadiumPlacements.length > 0
                ? stadiumPlacements
                : [
                    { surface: "perimeter_led", sponsor_name: sponsorData.active_deals?.[0]?.sponsor_name || "GTEX Exchange", campaign_code: "LED-MAIN", source: "club_contract" },
                    { surface: "tunnel_arch", sponsor_name: "Paystack Pro", campaign_code: "TUNNEL-VIP", source: "platform_network" },
                    { surface: "scoreboard_ribbon", sponsor_name: "Starlight Air", campaign_code: "RIBBON-HD", source: "broadcast_pool" },
                    { surface: "press_backdrop", sponsor_name: "Kora Emerald", campaign_code: "MEDIA-WALL", source: "club_contract" },
                  ]
              ).map((pl: any, idx: number) => (
                <div key={`${pl.surface}-${idx}`} className="rounded-lg border border-white/10 bg-black/40 p-2.5">
                  <p className="text-[10px] uppercase font-bold text-slate-400">{label(pl.surface)}</p>
                  <p className="font-bold text-white mt-0.5">{pl.sponsor_name}</p>
                  <p className="gx-mono text-[10px] text-emerald-300 mt-0.5">{pl.campaign_code} · {label(pl.source || "active")}</p>
                </div>
              ))}
            </div>
            {sponsoredFeed?.items?.length > 0 && (
              <p className="text-[11px] text-slate-400">
                Sponsored Broadcast Feed Active: {sponsoredFeed.items.length} promoted highlight clips generating matchday ad impressions.
              </p>
            )}
          </div>
        </div>
      )}
    </Panel>
  );
}

function ClubShareholderDesk({ clubs }: { clubs: any[] }) {
  const [selectedClub, setSelectedClub] = useState("");
  const activeClubId = selectedClub || clubs?.[0]?.club_id || "";
  const refresh = useRefreshOwner();
  const [dividendAmount, setDividendAmount] = useState("");
  const [takeoverUnits, setTakeoverUnits] = useState("10");
  const [distributing, setDistributing] = useState(false);
  const [bidding, setBidding] = useState(false);

  const { data: shData, isLoading, refetch } = useQuery({
    queryKey: ["club-shareholders", activeClubId],
    queryFn: async () => (await api.get(`/owner/clubs/${activeClubId}/shareholders`)).data,
    enabled: Boolean(activeClubId),
  });

  // Canonical Club Sale Market Valuation
  const { data: canonicalValuation } = useQuery({
    queryKey: ["club-sale-valuation", activeClubId],
    queryFn: async () => {
      try {
        return (await api.get(`/api/clubs/${activeClubId}/valuation`)).data;
      } catch {
        return null;
      }
    },
    enabled: Boolean(activeClubId),
  });

  const handleDistribute = async () => {
    if (!activeClubId) return;
    setDistributing(true);
    try {
      const body = dividendAmount ? { amount_gtex: Number(dividendAmount) } : {};
      const { data: res } = await api.post(`/owner/clubs/${activeClubId}/shareholders/distribute-dividend`, body);
      toast.success(
        `Distributed ${fmt(res.total_distributed_gtex)} GTX dividend across ${res.recipient_count} shareholders!`,
      );
      setDividendAmount("");
      await refetch();
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setDistributing(false);
    }
  };

  const handleTakeoverBid = async () => {
    if (!activeClubId) return;
    setBidding(true);
    try {
      const unitsNum = Number(takeoverUnits) || 10;
      const { data: res } = await api.post(`/owner/clubs/${activeClubId}/shareholders/takeover-bid`, {
        units: unitsNum,
      });
      toast.success(`Acquired ${res.units} units in ${res.club_name || shData?.club_name}! Tier: ${res.tier}`);
      await refetch();
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBidding(false);
    }
  };

  if (!activeClubId) return null;

  return (
    <Panel
      eyebrow="Governance, Equity & Dividends"
      title="Club Equity, Minority Share Dividends & Takeover Desk"
      testid="club-shareholder-dividend-desk"
      className="lg:col-span-12"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div className="flex flex-wrap items-center gap-3">
          {clubs && clubs.length > 1 && (
            <select
              className="gx-input w-52"
              value={activeClubId}
              onChange={(e) => setSelectedClub(e.target.value)}
              data-testid="shareholder-club-select"
            >
              {clubs.map((c: any) => (
                <option key={c.club_id} value={c.club_id}>
                  {c.club_name}
                </option>
              ))}
            </select>
          )}
          {shData && (
            <span className="text-xs text-slate-300">
              Valuation: <b className="text-white">{fmt(canonicalValuation?.estimated_valuation_coin ?? shData.valuation_gtex)} GTX</b> · Prestige {shData.prestige} ({shData.prestige_tier})
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400">
          Minority support units entitle fans and co-owners to seasonal TV/competition prize dividend pools.
        </p>
      </div>

      {isLoading || !shData ? (
        <Loading label="Reading club shareholder registry" />
      ) : (
        <div className="mt-4 space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label="Total Minority Units" value={`${fmt(shData.total_minority_units)} Units`} testid="sh-total-units" />
            <Stat
              label="Accrued Dividend Pool"
              value={<Coin amount={shData.accrued_dividend_pool_gtex} />}
              tone="good"
              testid="sh-accrued-pool"
            />
            <Stat label="Shareholder Count" value={fmt(shData.shareholder_count)} testid="sh-count" />
            <Stat
              label="Your Holding / Takeover Goal"
              value={`${fmt(shData.my_units)} / ${fmt(shData.minority_takeover_threshold_units)}`}
              tone={shData.my_units >= shData.minority_takeover_threshold_units ? "good" : "warn"}
              testid="sh-my-units"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3">
              <div>
                <h5 className="text-sm font-bold text-white">Distribute Seasonal Dividend</h5>
                <p className="text-xs text-slate-400 mt-0.5">
                  Distribute funds from the accrued TV rights and prize pool ({fmt(shData.accrued_dividend_pool_gtex)} GTX) proportionally to all minority shareholders.
                </p>
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  min={100}
                  max={25000}
                  className="gx-input flex-1"
                  placeholder={`Amount (defaults to ${fmt(shData.accrued_dividend_pool_gtex)} GTX)`}
                  value={dividendAmount}
                  onChange={(e) => setDividendAmount(e.target.value)}
                  data-testid="dividend-amount-input"
                />
                <Btn
                  variant="gold"
                  disabled={distributing}
                  onClick={handleDistribute}
                  data-testid="distribute-dividend-btn"
                >
                  {distributing ? "Distributing…" : "Distribute Seasonal Dividend"}
                </Btn>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3">
              <div>
                <h5 className="text-sm font-bold text-white">Acquire Minority Stake / Takeover Units</h5>
                <p className="text-xs text-slate-400 mt-0.5">
                  Purchase additional minority equity units to increase your dividend entitlement and work toward the {shData.minority_takeover_threshold_units}-unit co-chair takeover threshold.
                </p>
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  min={1}
                  max={500}
                  className="gx-input w-28"
                  value={takeoverUnits}
                  onChange={(e) => setTakeoverUnits(e.target.value)}
                  data-testid="takeover-units-input"
                />
                <Btn
                  variant="primary"
                  className="flex-1"
                  disabled={bidding}
                  onClick={handleTakeoverBid}
                  data-testid="takeover-bid-btn"
                >
                  {bidding ? "Acquiring…" : "Acquire Minority Stake / Takeover Units"}
                </Btn>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-black/40 p-4">
            <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3">
              Club Shareholder Registry ({shData.shareholders?.length || 0} Investors)
            </h5>
            {(!shData.shareholders || shData.shareholders.length === 0) ? (
              <p className="text-xs text-slate-400 py-3 text-center">No minority shareholders registered yet.</p>
            ) : (
              <div className="gx-scroll overflow-x-auto">
                <table className="gx-table w-full min-w-[640px]">
                  <thead>
                    <tr>
                      <th>Shareholder</th>
                      <th>Units Held</th>
                      <th>Share %</th>
                      <th>Tier</th>
                      <th>Est. Seasonal Dividend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shData.shareholders.map((sh: any) => (
                      <tr key={sh.user_id} data-testid={`shareholder-row-${sh.user_id}`}>
                        <td className="font-semibold text-white">{sh.username}</td>
                        <td className="gx-mono">{fmt(sh.units)}</td>
                        <td className="gx-mono text-cyan-300">{sh.share_pct}%</td>
                        <td>
                          {sh.tier ? <Chip tone="gold">{sh.tier}</Chip> : <span className="text-slate-500 text-xs">—</span>}
                        </td>
                        <td className="gx-mono text-emerald-300">
                          {fmt(sh.estimated_dividend_gtex)} GTX
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
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
        {data.ecosystem_waterfall && (
          <Panel
            eyebrow="Ecosystem Revenue Recycling · Giving Back to Club Owners"
            title="TV Broadcast, Competition Grants & Jackpot Waterfall"
            className="lg:col-span-12"
            testid="finance-ecosystem-waterfall"
          >
            <div className="grid gap-4 md:grid-cols-4">
              <Stat label="40% TV Broadcast Pool" value={<Coin amount={data.ecosystem_waterfall.tv_broadcast_pool_gtex ?? 0} />} />
              <Stat label="35% Competition Prize Pool" value={<Coin amount={data.ecosystem_waterfall.competition_prize_pool_gtex ?? 0} />} />
              <Stat label="25% Global Jackpot Pool" value={<Coin amount={data.ecosystem_waterfall.jackpot_ecosystem_pool_gtex ?? 0} />} />
              <Stat label="Your Club TV & Grant Earnings" value={<Coin amount={Number(data.ecosystem_waterfall.club_tv_revenue_gtex || 0) + Number(data.ecosystem_waterfall.club_competition_grants_gtex || 0)} />} tone="good" />
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
              <span>Platform fees from transfers, regen sales, and gifting rakes recycle back into TV rights, competition grants, and the GTEX Jackpot.</span>
              <Link to="/app/jackpot" className="text-amber-300 hover:underline font-semibold">Open Global Jackpot Hub →</Link>
            </div>
          </Panel>
        )}
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
        <SponsorNegotiationDesk clubs={data.clubs} />
        <ClubShareholderDesk clubs={data.clubs} />
        <Deposit configured={data.paystack_configured} rates={data.treasury_rates} mode={data.paystack_mode} />
        <Withdraw rates={data.treasury_rates} />
        {data.withdrawals.length > 0 && (
          <Panel eyebrow="History" title="Withdrawals" className="lg:col-span-12" testid="withdrawals-history">
            {data.withdrawals.map((w: any) => <p key={w.id} className="text-sm text-slate-300">{fmt(w.amount_coin)} GTX → {w.bank_name} ****{w.account_last4} <Chip tone={w.status === "approved" ? "emerald" : w.status === "rejected" ? "red" : "gold"}>{label(w.status)}</Chip></p>)}
          </Panel>
        )}
        <LedgerTable rows={data.ledger} />
        <FanCoin data={data} />
        <SupportUnits data={data} />
        <CoinTraderDesk />
      </div>
    </div>
  );
}

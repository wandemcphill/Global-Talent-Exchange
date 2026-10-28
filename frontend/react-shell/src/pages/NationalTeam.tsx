import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Award, CheckCircle2, Flag, Lock, Plus, ShieldCheck, ShoppingCart, Sparkles, Trophy, UserCheck, Wand2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, label, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";

const BASE = "/national-team-engine";
const COUNTRIES = [
  ["NG", "Nigeria"],
  ["GH", "Ghana"],
  ["SN", "Senegal"],
  ["CM", "Cameroon"],
  ["CI", "Côte d'Ivoire"],
  ["EG", "Egypt"],
  ["MA", "Morocco"],
  ["ZA", "South Africa"],
  ["BR", "Brazil"],
  ["AR", "Argentina"],
  ["FR", "France"],
  ["GB", "England"],
  ["ES", "Spain"],
  ["DE", "Germany"],
  ["PT", "Portugal"],
  ["JP", "Japan"],
  ["KR", "South Korea"],
];
const POSITIONS = ["", "goalkeeper", "defender", "midfielder", "forward"];

function EnterForm({ comp, onDone }: any) {
  const [code, setCode] = useState("NG");
  const enter = async () => {
    const name = COUNTRIES.find((c) => c[0] === code)?.[1];
    try {
      await api.post(`${BASE}/competitions/${comp.id}/rental-entry`, { country_code: code, country_name: name });
      toast.success(`You now manage ${name} in ${comp.title} (Free Entry via User ID)`);
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="space-y-3" data-testid="national-enter-form">
      <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-slate-300">
        <p className="font-semibold text-emerald-300">
          Free Entry · Open to All User IDs (0–3 Clubs Supported) · Pre-Qualifier Representative System
        </p>
        <p className="mt-1 text-slate-400">
          Joining any GTEX or User-Hosted National Team tournament is 100% free. You only rent players (real + regens at a fraction of club market value) and hire a tournament Manager in Fan Coin. If multiple users pick the same nation (e.g. 1,000 users pick England), an automatic single-elimination pre-qualifier crowns the #1 Country Representative who leads that nation through Qualifiers and keeps their exclusive spot in the World Cup Finals.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <p className="gx-label mb-1">Nation</p>
          <select
            data-testid="national-country-select"
            className="gx-input"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          >
            {COUNTRIES.map(([c, n]) => (
              <option key={c} value={c}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <Btn onClick={enter} data-testid="national-enter-button">
          <Flag size={14} />
          Take charge of the national team (Free Entry)
        </Btn>
      </div>
    </div>
  );
}

function RentCard({ p, entry, onRented, inBasket, onToggleBasket }: any) {
  const [busy, setBusy] = useState(false);
  const ok = p.eligibility?.eligible !== false;
  const rent = async () => {
    setBusy(true);
    try {
      await api.post(`${BASE}/entries/${entry.id}/rentals`, { player_id: p.player_id });
      toast.success(`${p.player_name} rented for the tournament`);
      onRented();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <PlayerCard
      testid={`rental-card-${p.player_id}`}
      name={p.player_name}
      rating={p.overall_rating}
      position={p.primary_position}
      age={p.age}
      nationality={p.nationality}
      club={p.current_club_name}
      image={p.image_url || p.portrait_url}
      regen={p.is_regen}
      badge={p.tier_label}
      stats={[
        { k: "Loan", v: fmt(p.loan_price_coin, 1) },
        { k: "GSI", v: p.gsi },
        { k: "Value", v: fmt(p.base_value_coin, 0) },
      ]}
      footer={
        <div className="flex flex-col gap-1.5 w-full">
          <Btn
            className="w-full justify-center"
            variant="secondary"
            disabled={busy || !ok}
            title={ok ? "" : (p.eligibility?.reasons || []).join(", ")}
            onClick={rent}
            data-testid={`rent-player-${p.player_id}`}
          >
            {!ok ? (
              label(p.eligibility?.reasons?.[0] || "not eligible")
            ) : busy ? (
              "Renting…"
            ) : (
              <>
                Rent · <Coin amount={p.loan_price_coin} />
              </>
            )}
          </Btn>
          {ok && onToggleBasket && (
            <button
              type="button"
              onClick={() => onToggleBasket(p)}
              data-testid={`shortlist-player-${p.player_id}`}
              className={`rounded border px-2 py-1 text-[11px] font-semibold transition-colors ${
                inBasket
                  ? "border-amber-400/50 bg-amber-500/20 text-amber-200"
                  : "border-white/10 bg-white/5 text-slate-300 hover:border-white/25"
              }`}
            >
              {inBasket ? "✓ In Shortlist Basket" : "+ Add to Shortlist Basket"}
            </button>
          )}
        </div>
      }
    />
  );
}

function RentalPool({ comp, entry, onRented, basket, onToggleBasket }: any) {
  const [position, setPosition] = useState("");
  const [nationOnly, setNationOnly] = useState(true);
  const [limit, setLimit] = useState(12);
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["rental-pool", comp.id, entry.id, position, nationOnly, limit],
    queryFn: async () =>
      (
        await api.get(`${BASE}/competitions/${comp.id}/rental-pool`, {
          params: {
            limit,
            entry_id: entry.id,
            ...(nationOnly ? { country_code: entry.country_code } : {}),
            ...(position ? { position } : {}),
          },
        })
      ).data,
    placeholderData: (prev: any) => prev,
  });
  const basketIds = new Set((basket || []).map((item: any) => item.player_id));
  return (
    <Panel
      eyebrow={`${fmt(data?.total)} players available (Real + Regens · Fractional Loan Pricing)`}
      title="Rental pool"
      testid="rental-pool-panel"
      action={
        <div className="flex flex-wrap gap-1">
          <button
            data-testid="rental-nation-toggle"
            onClick={() => setNationOnly(!nationOnly)}
            className={`gx-btn ${nationOnly ? "gx-btn-primary" : "gx-btn-secondary"}`}
          >
            {nationOnly ? `${entry.country_name} only` : "All nations"}
          </button>
          {POSITIONS.map((p) => (
            <button
              key={p || "all"}
              data-testid={`rental-filter-${p || "all"}`}
              onClick={() => setPosition(p)}
              className={`gx-btn capitalize ${position === p ? "gx-btn-primary" : "gx-btn-ghost"}`}
            >
              {p || "All"}
            </button>
          ))}
        </div>
      }
    >
      {isLoading ? (
        <Loading label="Calling up players" />
      ) : !data?.items?.length ? (
        <Empty title="No players in this pool" body="Try all nations or another position." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
          {data.items.map((p: any) => (
            <RentCard
              key={p.player_id}
              p={p}
              entry={entry}
              onRented={onRented}
              inBasket={basketIds.has(p.player_id)}
              onToggleBasket={onToggleBasket}
            />
          ))}
        </div>
      )}
      {data && data.total > data.items.length && (
        <div className="mt-5 text-center">
          <Btn
            variant="secondary"
            disabled={isFetching}
            onClick={() => setLimit(limit + 12)}
            data-testid="rental-load-more"
          >
            {isFetching ? "Scouting…" : "Load more players"}
          </Btn>
        </div>
      )}
    </Panel>
  );
}

function NationalManagerPanel({ entryId, refreshKey, onHired }: any) {
  const { data: managers } = useQuery({
    queryKey: ["national-managers-catalog"],
    queryFn: async () => (await api.get(`${BASE}/managers/catalog`)).data,
  });
  const { data: entryDetail } = useQuery({
    queryKey: ["national-entry", entryId, refreshKey],
    queryFn: async () => (await api.get(`${BASE}/entries/${entryId}`)).data,
  });
  const [hiringId, setHiringId] = useState<string | null>(null);
  const hiredManager = entryDetail?.metadata_json?.hired_manager;

  const hire = async (mgrId: string) => {
    setHiringId(mgrId);
    try {
      const { data } = await api.post(`${BASE}/entries/${entryId}/manager/hire`, { manager_id: mgrId });
      toast.success(
        `Hired ${data?.hired_manager?.display_name}! Paid ${fmt(data?.hired_manager?.fee_fan_coin, 0)} Fan Coin upfront.`
      );
      onHired(data?.hired_manager);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setHiringId(null);
    }
  };

  return (
    <Panel
      eyebrow="Tournament Head Coach Only (No GM / HOYD / Scout Needed · Paid Once Upfront in Fan Coin)"
      title="Hire National Team Manager"
      testid="national-manager-panel"
      action={
        hiredManager ? (
          <Chip tone="emerald">
            ✓ Hired: {hiredManager.display_name} ({hiredManager.preferred_formation} ·{" "}
            {String(hiredManager.tactical_style || "").replace(/_/g, " ")})
          </Chip>
        ) : (
          <Chip tone="gold">Step 1: Select Manager & Tactics</Chip>
        )
      }
    >
      <div className="grid gap-3 md:grid-cols-3">
        {(managers || []).map((m: any) => {
          const isCurrent = hiredManager?.manager_id === m.manager_id;
          return (
            <div
              key={m.manager_id}
              data-testid={`national-manager-card-${m.manager_id}`}
              className={`flex flex-col justify-between rounded border p-3.5 text-xs ${
                isCurrent
                  ? "border-emerald-500/50 bg-emerald-500/10"
                  : "border-white/10 bg-slate-950/60"
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-sm text-white">{m.display_name}</span>
                  <Chip tone="cyan">{m.preferred_formation}</Chip>
                </div>
                <p className="mt-1 text-emerald-300 font-semibold uppercase tracking-wider text-[10px]">
                  {String(m.tactical_style).replace(/_/g, " ")} · {m.tactical_rating} TAC
                </p>
                <p className="mt-1.5 text-slate-400">{m.specialty}</p>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-white/10 pt-2.5">
                <span className="gx-mono text-amber-300 font-semibold">
                  {fmt(m.fee_fan_coin, 0)} Fan Coin (Upfront)
                </span>
                <Btn
                  variant={isCurrent ? "ghost" : "secondary"}
                  disabled={!!hiringId || isCurrent}
                  onClick={() => hire(m.manager_id)}
                  data-testid={`hire-national-manager-${m.manager_id}`}
                >
                  {isCurrent ? "Active Coach ✓" : hiringId === m.manager_id ? "Hiring…" : "Hire Coach"}
                </Btn>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function AutoBuild({ comp, entry, onRented }: any) {
  const [budget, setBudget] = useState("500");
  const [tactic, setTactic] = useState("tiki_taka");
  const [squadSize, setSquadSize] = useState("18");
  const [plan, setPlan] = useState<any>(null);
  const [checkingOut, setCheckingOut] = useState(false);

  const run = async () => {
    try {
      setPlan(
        (
          await api.post(`${BASE}/competitions/${comp.id}/auto-build-squad`, {
            country_code: entry.country_code,
            budget_coin: Number(budget),
            tactic,
            squad_size: Number(squadSize) || 18,
          })
        ).data
      );
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const checkoutPlan = async () => {
    if (!plan?.players?.length) return;
    setCheckingOut(true);
    try {
      const playerIds = plan.players.map((p: any) => p.player_id);
      await api.post(`${BASE}/entries/${entry.id}/rentals/checkout`, {
        player_ids: playerIds,
        tactic: plan.tactic || tactic,
      });
      toast.success(`Checked out ${playerIds.length} auto-picked players for ${entry.country_name}!`);
      onRented();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setCheckingOut(false);
    }
  };

  return (
    <Panel eyebrow="AI Coach & Tactical Auto-Pick" title="Auto-build a squad" testid="auto-build-panel" className="lg:col-span-5">
      <div className="grid grid-cols-3 gap-2 mb-2">
        <div>
          <span className="text-[10px] uppercase text-slate-400">Budget (GTX)</span>
          <input
            data-testid="auto-build-budget"
            className="gx-input w-full mt-0.5"
            value={budget}
            onChange={(e) => setBudget(e.target.value.replace(/[^\d.]/g, ""))}
          />
        </div>
        <div>
          <span className="text-[10px] uppercase text-slate-400">Tactics</span>
          <select
            data-testid="auto-build-tactic"
            className="gx-input w-full mt-0.5"
            value={tactic}
            onChange={(e) => setTactic(e.target.value)}
          >
            <option value="tiki_taka">Tiki-Taka (4-3-3)</option>
            <option value="gegenpress">Gegenpress (4-2-3-1)</option>
            <option value="possession">Possession (4-3-3)</option>
            <option value="counter">Counter (4-2-3-1)</option>
            <option value="direct">Direct (4-4-2)</option>
            <option value="low_block">Low Block (5-4-1)</option>
          </select>
        </div>
        <div>
          <span className="text-[10px] uppercase text-slate-400">Size (18–30)</span>
          <input
            type="number"
            min={18}
            max={30}
            data-testid="auto-build-size"
            className="gx-input w-full mt-0.5"
            value={squadSize}
            onChange={(e) => setSquadSize(e.target.value)}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <Btn variant="secondary" onClick={run} data-testid="auto-build-button">
          <Wand2 size={14} />
          Suggest squad
        </Btn>
        {plan?.players?.length > 0 && (
          <Btn
            variant="primary"
            disabled={checkingOut}
            onClick={checkoutPlan}
            data-testid="auto-build-checkout-button"
          >
            <ShoppingCart size={14} />
            {checkingOut ? "Checking out…" : `Rent All ${plan.players.length} Players`}
          </Btn>
        )}
      </div>
      {plan && (
        <div className="mt-4 text-sm" data-testid="auto-build-result">
          <p className="text-slate-300">
            {plan.formation} ({String(plan.tactic).replace(/_/g, " ")}) · {plan.selected_count}/{plan.squad_size} picked · cost{" "}
            <Coin amount={plan.total_cost_coin} /> · left <Coin amount={plan.remaining_budget_coin} />
          </p>
          <ul className="gx-scroll mt-3 max-h-64 space-y-1 overflow-auto">
            {plan.players.map((p: any) => (
              <li key={p.player_id} className="flex justify-between border-b border-white/5 py-1 text-xs">
                <span className="text-white">
                  {p.assigned_slot} · {p.player_name}
                </span>
                <span className="gx-mono text-slate-400">
                  {p.overall_rating} · {fmt(p.loan_price_coin, 1)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

function EntryRoster({ comp, entryId, refreshKey, basket, onClearBasket, onRented }: any) {
  const { data: e, refetch } = useQuery({
    queryKey: ["national-entry", entryId, refreshKey],
    queryFn: async () => (await api.get(`${BASE}/entries/${entryId}`)).data,
  });
  const [submitting, setSubmitting] = useState(false);
  const [checkingOutBasket, setCheckingOutBasket] = useState(false);

  if (!e) return <Loading />;
  const roster = e.rental_squad_members || [];
  const minSize = e.minimum_squad_size || 18;
  const maxSize = e.maximum_squad_size || 30;

  const claim = async () => {
    try {
      await api.post(`${BASE}/entries/${entryId}/free-players/claim`);
      toast.success("Free players claimed");
      refetch();
      onRented();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const checkoutShortlist = async () => {
    if (!basket?.length) return;
    setCheckingOutBasket(true);
    try {
      await api.post(`${BASE}/entries/${entryId}/rentals/checkout`, {
        player_ids: basket.map((p: any) => p.player_id),
      });
      toast.success(`Checked out ${basket.length} shortlisted player(s)!`);
      onClearBasket();
      refetch();
      onRented();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setCheckingOutBasket(false);
    }
  };

  const submitTournamentSquad = async (isFinalsUpdate = false) => {
    if (roster.length === 0) {
      toast.error("Rent or claim players into your national squad before submitting.");
      return;
    }
    setSubmitting(true);
    try {
      const endpoint = isFinalsUpdate
        ? `${BASE}/competitions/${comp.id}/finals-squad`
        : `${BASE}/competitions/${comp.id}/entries`;
      await api.post(endpoint, {
        country_code: e.country_code,
        country_name: e.country_name,
        squad: roster.map((m: any) => ({
          player_id: m.player_id,
          player_name: m.player_name,
          overall_rating: m.overall_rating,
          position: m.primary_position || "CM",
          age: 24,
        })),
      });
      toast.success(
        isFinalsUpdate
          ? `Updated ${e.country_name} World Cup Finals squad while keeping your representative spot!`
          : `Submitted ${e.country_name} squad (${roster.length} players) to ${comp.title}!`
      );
      refetch();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSubmitting(false);
    }
  };

  const basketTotal = (basket || []).reduce((sum: number, p: any) => sum + Number(p.loan_price_coin || 0), 0);

  return (
    <Panel
      eyebrow={`${e.country_name} · ${roster.length}/${minSize} min (${maxSize} max) · Protected While Active`}
      title="Your national squad"
      testid="national-roster-panel"
      className="lg:col-span-7"
      action={
        <div className="flex flex-wrap gap-2">
          {e.free_players_remaining > 0 && (
            <Btn variant="gold" onClick={claim} data-testid="claim-free-players">
              Claim {e.free_players_remaining} free players
            </Btn>
          )}
          <Btn
            variant="primary"
            disabled={submitting || roster.length === 0}
            onClick={() => submitTournamentSquad(false)}
            data-testid="submit-national-entry-button"
          >
            <Lock size={13} />
            {submitting ? "Submitting…" : "Submit Squad to Qualifiers"}
          </Btn>
          <Btn
            variant="secondary"
            disabled={submitting || roster.length === 0}
            onClick={() => submitTournamentSquad(true)}
            data-testid="update-finals-squad-button"
            title="Qualified country representatives can update 1–2 players before World Cup Finals lock without re-renting their squad"
          >
            <ShieldCheck size={13} />
            Finals Squad Carryover Update
          </Btn>
        </div>
      }
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
        <span>
          Active Tournament Protection: Your rented pool never expires while {e.country_name} remains active. Once the tournament locks, rosters are locked (no injury replacements).
        </span>
      </div>
      <div className="mb-4 h-1.5 rounded-sm bg-white/5">
        <div
          className="h-1.5 rounded-sm bg-emerald-400 transition-[width] duration-700"
          style={{ width: `${Math.min(100, (roster.length / minSize) * 100)}%` }}
        />
      </div>

      {/* Shortlist / Basket Checkout Drawer */}
      {basket && basket.length > 0 && (
        <div
          className="mb-4 rounded border border-amber-400/30 bg-amber-500/10 p-3"
          data-testid="national-basket-panel"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs">
              <p className="font-bold text-amber-300">
                Shortlist Basket ({basket.length} player{basket.length === 1 ? "" : "s"}) · Total Loan Fee:{" "}
                {fmt(basketTotal, 1)} GTX
              </p>
              <p className="text-slate-300">
                {basket.map((p: any) => p.player_name).join(", ")}
              </p>
            </div>
            <div className="flex gap-2">
              <Btn variant="ghost" onClick={onClearBasket}>
                Clear
              </Btn>
              <Btn
                variant="gold"
                disabled={checkingOutBasket}
                onClick={checkoutShortlist}
                data-testid="checkout-basket-button"
              >
                <ShoppingCart size={13} />
                {checkingOutBasket ? "Checking out…" : `Checkout & Pay (${fmt(basketTotal, 1)} GTX)`}
              </Btn>
            </div>
          </div>
        </div>
      )}

      {roster.length === 0 ? (
        <Empty title="No players yet" body="Rent players from the pool below, shortlist a basket, or claim your free picks." />
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {roster.map((m: any) => (
            <div
              key={m.id}
              data-testid={`roster-${m.player_id}`}
              className="flex items-center justify-between rounded-sm border border-white/10 px-3 py-2 text-sm"
            >
              <span className="text-white">
                {m.shirt_number ? `#${m.shirt_number} ` : ""}
                {m.player_name}
              </span>
              <span className="flex items-center gap-2">
                <Chip tone={m.source_type === "free" ? "gold" : "cyan"}>{label(m.source_type)}</Chip>
                <span className="gx-mono text-emerald-300">{m.overall_rating}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function WorldCupPrizeMatrixPanel({ comp }: any) {
  const { data: breakdown } = useQuery({
    queryKey: ["national-reward-breakdown", comp.id],
    queryFn: async () => (await api.get(`${BASE}/competitions/${comp.id}/rewards/breakdown`)).data,
  });
  const rs = breakdown?.reward_structure || comp?.metadata_json?.reward_structure || {
    qualification_guaranteed_coin: "250.0000",
    per_match_coin: { win: "120.0000", draw: "60.0000", loss: "30.0000" },
    stage_progression_coin: {
      group_stage: "100.0000",
      round_of_16: "350.0000",
      quarterfinal: "600.0000",
      semifinal: "1000.0000",
      runner_up: "1500.0000",
      champion: "3000.0000",
    },
  };

  return (
    <Panel
      eyebrow="Guaranteed Qualification Payout + Every Match Win / Draw / Loss Payout + Stage Escalation"
      title={`${comp.title} Prize & Settlement Architecture`}
      testid="world-cup-prize-matrix-panel"
    >
      <div className="grid gap-3 md:grid-cols-4 text-xs">
        <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-3">
          <p className="text-[10px] uppercase tracking-wider text-emerald-300 font-bold">
            1. Finals Qualification Guarantee
          </p>
          <p className="gx-display mt-1 text-xl font-bold text-white">
            {fmt(rs.qualification_guaranteed_coin, 0)} GTX
          </p>
          <p className="mt-1 text-slate-300">
            Guaranteed minimum paid to every country representative that qualifies for the Finals.
          </p>
        </div>

        <div className="rounded border border-cyan-500/30 bg-cyan-500/10 p-3">
          <p className="text-[10px] uppercase tracking-wider text-cyan-300 font-bold">
            2. Every Match Played Pays Out
          </p>
          <div className="mt-1.5 space-y-1 text-slate-200">
            <div className="flex justify-between">
              <span>Match Win:</span>
              <b className="text-emerald-300">+{fmt(rs.per_match_coin?.win, 0)} GTX</b>
            </div>
            <div className="flex justify-between">
              <span>Match Draw:</span>
              <b className="text-amber-300">+{fmt(rs.per_match_coin?.draw, 0)} GTX</b>
            </div>
            <div className="flex justify-between">
              <span>Match Loss (Guaranteed):</span>
              <b className="text-cyan-300">+{fmt(rs.per_match_coin?.loss, 0)} GTX</b>
            </div>
          </div>
        </div>

        <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 md:col-span-2">
          <p className="text-[10px] uppercase tracking-wider text-amber-300 font-bold">
            3. Stage Progression Escalator (Cumulative)
          </p>
          <div className="mt-1.5 grid grid-cols-3 gap-2 text-slate-200">
            <div>
              <span className="text-slate-400 block text-[10px]">Group / R16</span>
              <b>
                +{fmt(rs.stage_progression_coin?.group_stage, 0)} / +
                {fmt(rs.stage_progression_coin?.round_of_16, 0)} GTX
              </b>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">QF / Semifinal</span>
              <b>
                +{fmt(rs.stage_progression_coin?.quarterfinal, 0)} / +
                {fmt(rs.stage_progression_coin?.semifinal, 0)} GTX
              </b>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Runner-Up / Champion</span>
              <b className="text-amber-300">
                +{fmt(rs.stage_progression_coin?.runner_up, 0)} / +
                {fmt(rs.stage_progression_coin?.champion, 0)} GTX
              </b>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}

export default function NationalTeam() {
  const { user } = useAuth();
  const isAdmin = ["admin", "super_admin"].includes(String(user?.role).toLowerCase());
  const [selected, setSelected] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [basket, setBasket] = useState<any[]>([]);
  const [showHostForm, setShowHostForm] = useState(false);
  const [hostTitle, setHostTitle] = useState("");
  const [hostFamily, setHostFamily] = useState("world_cup");
  const qc = useQueryClient();
  const refreshOwner = useRefreshOwner();

  const onRented = () => {
    setTick((t) => t + 1);
    refreshOwner();
    qc.invalidateQueries({ queryKey: ["rental-pool"] });
  };

  const toggleBasketPlayer = (p: any) => {
    setBasket((prev) =>
      prev.some((item) => item.player_id === p.player_id)
        ? prev.filter((item) => item.player_id !== p.player_id)
        : [...prev, p]
    );
  };

  const comps = useQuery({
    queryKey: ["national-comps", tick],
    queryFn: async () => (await api.get(`${BASE}/competitions`)).data,
  });
  const history = useQuery({
    queryKey: ["national-history", tick],
    queryFn: async () => (await api.get(`${BASE}/me/history`)).data,
  });
  const list: any[] = comps.data || [];
  const managed: any[] = history.data?.managed_entries || [];
  const comp =
    list.find((c) => c.id === selected) ||
    list.find((c) => managed.some((e) => e.competition_id === c.id)) ||
    list[0];
  const entry = managed.find((e: any) => e.competition_id === comp?.id);

  const seed = async () => {
    try {
      await api.post(`/admin${BASE}/competitions/seed-defaults`);
      toast.success("Default national tournaments seeded (World Cup, AFCON, Euros, Copa, Asian Cup)");
      comps.refetch();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const hostUserTournament = async () => {
    if (hostTitle.trim().length < 3) {
      toast.error("Enter a tournament title of at least 3 characters.");
      return;
    }
    try {
      const { data } = await api.post(`${BASE}/competitions/host`, {
        title: hostTitle.trim(),
        season_label: "2026",
        competition_family: hostFamily,
        region_type: hostFamily === "world_cup" ? "global" : hostFamily,
      });
      toast.success(`Hosted ${data.title}! Free entry is now open to all users.`);
      setHostTitle("");
      setShowHostForm(false);
      setSelected(data.id);
      setTick((t) => t + 1);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div data-testid="national-team-page" className="space-y-6">
      <PageHeader
        eyebrow="International duty · World Cup, AFCON, Euros, Copa America & Asian Cup"
        title="National team rentals"
        sub="Free entry for all users (0 to 3 clubs). Rent real players and regens for a fraction of club market value, hire your tournament Manager upfront in Fan Coin, win your country's Pre-Qualifier representative spot, and earn guaranteed World Cup match & stage prizes."
        action={
          <div className="flex flex-wrap gap-2">
            <Btn
              variant="secondary"
              onClick={() => setShowHostForm(!showHostForm)}
              data-testid="host-national-comp-button"
            >
              <Plus size={14} />
              Host National Tournament
            </Btn>
            {isAdmin && (
              <Btn variant="secondary" onClick={seed} data-testid="seed-national-competitions">
                Seed default tournaments
              </Btn>
            )}
          </div>
        }
      />

      {showHostForm && (
        <Panel
          eyebrow="User-Hosted National Team Competition (Free Entry · Rental Squads)"
          title="Host a Custom National Team Tournament"
          testid="host-national-comp-modal"
        >
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[220px]">
              <p className="gx-label mb-1">Tournament Name</p>
              <input
                className="gx-input w-full"
                placeholder="e.g. Lagos Invitational Nations Cup"
                value={hostTitle}
                onChange={(e) => setHostTitle(e.target.value)}
                data-testid="host-national-comp-title"
              />
            </div>
            <div>
              <p className="gx-label mb-1">Regional Template</p>
              <select
                className="gx-input"
                value={hostFamily}
                onChange={(e) => setHostFamily(e.target.value)}
                data-testid="host-national-comp-family"
              >
                <option value="world_cup">Global World Cup</option>
                <option value="afcon">AFCON (CAF)</option>
                <option value="euros">European Championship (UEFA)</option>
                <option value="copa">Copa America (CONMEBOL)</option>
                <option value="asian_cup">Asian Cup (AFC)</option>
              </select>
            </div>
            <Btn onClick={hostUserTournament} data-testid="host-national-comp-submit">
              Create Tournament
            </Btn>
          </div>
        </Panel>
      )}

      {comps.isLoading ? (
        <Loading />
      ) : list.length === 0 ? (
        <Empty
          testid="national-empty"
          title="No national tournaments open"
          body={
            isAdmin
              ? "Seed the default tournaments to open rentals."
              : "Click 'Host National Tournament' above or wait for an official GTEX World Cup cycle."
          }
        />
      ) : (
        <>
          <div className="gx-scroll flex gap-2 overflow-x-auto" data-testid="national-comp-tabs">
            {list.map((c) => (
              <button
                key={c.id}
                data-testid={`national-comp-${c.key}`}
                onClick={() => setSelected(c.id)}
                className={`gx-btn whitespace-nowrap ${
                  comp?.id === c.id ? "gx-btn-primary" : "gx-btn-secondary"
                }`}
              >
                {c.title}
                <span className="ml-1 text-[10px] opacity-70">{label(c.status)}</span>
              </button>
            ))}
          </div>

          {comp && <WorldCupPrizeMatrixPanel comp={comp} />}

          {comp && !entry && (
            <Panel
              eyebrow={`${comp.season_label} · ${label(comp.format_type)} · ${label(comp.age_band)} · Free Entry`}
              title={comp.title}
              testid="national-comp-panel"
            >
              <EnterForm comp={comp} onDone={() => setTick(tick + 1)} />
            </Panel>
          )}

          {comp && entry && (
            <>
              <NationalManagerPanel
                entryId={entry.id}
                refreshKey={tick}
                onHired={() => setTick((t) => t + 1)}
              />
              <div className="grid gap-6 lg:grid-cols-12">
                <EntryRoster
                  comp={comp}
                  entryId={entry.id}
                  refreshKey={tick}
                  basket={basket}
                  onClearBasket={() => setBasket([])}
                  onRented={onRented}
                />
                <AutoBuild comp={comp} entry={entry} onRented={onRented} />
              </div>
              <RentalPool
                comp={comp}
                entry={entry}
                onRented={onRented}
                basket={basket}
                onToggleBasket={toggleBasketPlayer}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}

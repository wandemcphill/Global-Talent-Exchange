import React, { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Dna,
  ShoppingCart,
  Sparkles,
  Sprout,
  Trash2,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { publicUrl } from "@/lib/publicPath";
import { clubCreateErrorMessage } from "./clubLocationCatalog";
import {
  buildClubDNA,
  buildCrestLibrary,
  buildKitSet,
  CREST_PAGE_SIZE,
  filterCrestLibrary,
  filterKitPresets,
  KIT_PAGE_SIZE,
  KIT_PRESETS,
  kitSwatchDataUri,
  preferredCrestIndex,
} from "./clubIdentityDefaults";
import { JerseyTurntable } from "./JerseyTurntable";
import {
  ClubLocationFields,
  clubLocationPayload,
  useClubLocation,
} from "@/components/gtex/ClubLocationFields";
import { useAuth } from "@/lib/auth";
import { fmt, useClub } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, Panel } from "@/components/gtex/ui";
import { MarketTable, marketLane } from "@/components/gtex/MarketTable";
import { posShort } from "@/components/gtex/PlayerCard";
import { GtexSceneViewport } from "@/lib/3d/GtexSceneViewport";
import { ClubCoinTraderFundingPanel } from "@/components/gtex/CoinTraderDesk";

const STEPS = [
  { key: "identity", label: "Club identity" },
  { key: "squad", label: "Sign starting squad" },
  { key: "manager", label: "Appoint manager" },
  { key: "academy", label: "Youth academy" },
  { key: "competition", label: "Open your club" },
];

function Stepper({ index }: any) {
  return (
    <ol className="mb-10 grid grid-cols-2 gap-2 md:grid-cols-5" data-testid="onboarding-stepper">
      {STEPS.map((s, i) => (
        <li
          key={s.key}
          className={`rounded-sm border p-3 ${
            i === index
              ? "border-emerald-500/50 bg-emerald-500/10"
              : i < index
                ? "border-white/10 bg-white/[0.02]"
                : "border-white/[0.05]"
          }`}
        >
          <p className="gx-mono text-[10px] text-slate-500">STEP {i + 1}</p>
          <p className="flex items-center gap-2 text-sm font-semibold text-white">
            {i < index && <Check size={14} className="text-emerald-400" />}
            {s.label}
          </p>
        </li>
      ))}
    </ol>
  );
}

function IdentityStep({ club, onboarding, onDone }: any) {
  const [busy, setBusy] = useState(false);
  const launchGrant = Number(onboarding?.launch_grant ?? 2500);
  const launchGrantLimit = Number(onboarding?.launch_grant_owner_limit ?? 500);
  const activate = async () => {
    setBusy(true);
    try {
      await api.post(`/owner/clubs/${club.club_id}/activate`);
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel eyebrow="Step 1" title={`Confirm ${club.club_name}`} testid="onboarding-identity-step">
      <div className="mb-5">
        <GtexSceneViewport
          sceneId="club_takeover"
          compact
          title={`3D Keys to the Club · ${club.club_name}`}
          subtitle="Official Founding Charter & Stadium Center-Circle Walkout"
          badgeText="3D OWNER TAKEOVER"
          clubName={club.club_name}
          subjectName={club.club_name}
          crestUrl={club?.crest_asset_ref || club?.crest_url || club?.identity?.crest_asset_ref}
          primaryColor={club?.primary_color || club?.identity?.primary_color}
          secondaryColor={club?.secondary_color || club?.identity?.secondary_color}
          quote="A new era begins under your executive stewardship."
          stats={[
            { label: "Founding Squad Grant", value: `${fmt(launchGrant)} GTX`, accent: "#00E676" },
            { label: "Fan Reserve", value: "1,000 FAN", accent: "#F5B83D" },
          ]}
        />
      </div>
      <p className="max-w-xl text-sm text-slate-300">
        Your club identity is registered. Activating it unlocks a{" "}
        <b className="text-white">{fmt(launchGrant)} GTX squad-signing grant</b> if you are among
        the first {fmt(launchGrantLimit)} eligible club owners, plus 1,000 FAN for gifting. The GTX
        grant is ring-fenced for eligible player signings.
      </p>
      <Btn
        className="mt-6"
        onClick={activate}
        disabled={busy}
        data-testid="onboarding-activate-button"
      >
        {busy ? "Activating…" : "Activate club"}
      </Btn>
    </Panel>
  );
}

function SquadFundingPanel({ clubId, club, onClubFunded, purpose = "squad", shortfall }: any) {
  const queryClient = useQueryClient();
  const [coinsToMove, setCoinsToMove] = useState("");
  const [nairaAmount, setNairaAmount] = useState("");
  const [provider, setProvider] = useState<"korapay" | "paystack">("korapay");
  const [providerTouched, setProviderTouched] = useState(false);
  const financeQuery = useQuery({
    queryKey: ["club-squad-funding-finance"],
    queryFn: async () => (await api.get("/owner/finance")).data,
  });
  const finance = financeQuery.data;
  useEffect(() => {
    if (providerTouched || !finance?.payment_providers) return;
    if (!finance.payment_providers.korapay && finance.payment_providers.paystack) {
      setProvider("paystack");
    } else if (!finance.payment_providers.paystack && finance.payment_providers.korapay) {
      setProvider("korapay");
    }
  }, [finance?.payment_providers, providerTouched]);
  const rates = finance?.treasury_rates || {};
  const rate = Number(rates.deposit_rate || 0);
  const walletCoins = Number(finance?.wallet?.gtex_total || 0);
  const clubCoins = Number(club?.economy?.cash_gtex || 0);
  const registeredPlayers = Number(
    club?.formation?.total_registered_players ?? club?.squad?.length ?? 0,
  );
  const playersRemaining = Math.max(0, 22 - registeredPlayers);
  const squadGap = Math.max(0, playersRemaining * 200 - clubCoins - walletCoins);
  const estimatedCoinsNeeded = shortfall != null ? Math.max(0, Number(shortfall) || 0) : squadGap;
  const wageMode = purpose === "wages";
  const suggestedNaira =
    rate > 0
      ? Math.max(
          100,
          Math.ceil(
            rates.deposit_direction === "fiat_per_coin"
              ? estimatedCoinsNeeded * rate
              : estimatedCoinsNeeded / rate,
          ),
        )
      : "";
  const parsedAmount = Number(nairaAmount || suggestedNaira || 0);
  const amountToPay = Number.isFinite(parsedAmount) ? parsedAmount : 0;
  const previewCoins =
    rate > 0
      ? rates.deposit_direction === "coin_per_fiat"
        ? amountToPay * rate
        : amountToPay / rate
      : 0;
  const platformReady = Boolean(finance?.payment_providers?.[provider]);

  const buyFromPlatform = async () => {
    const amount = Math.trunc(amountToPay);
    if (!Number.isFinite(amount) || amount < 100) {
      toast.error("Enter at least ₦100 to buy GTEX Coin.");
      return;
    }
    try {
      const { data } = await api.post("/owner/deposits/init", {
        amount_ngn: amount,
        provider,
        callback_url:
          window.location.origin +
          publicUrl(`/payment/callback?return_to=%2Fonboarding&provider=${provider}`),
      });
      window.location.href = data.authorization_url;
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  const moveToClub = async () => {
    const amount = Number(coinsToMove);
    if (!Number.isFinite(amount) || amount <= 0) {
      toast.error("Enter a valid GTX amount to add to the club treasury.");
      return;
    }
    if (amount > walletCoins) {
      toast.error("Your wallet does not have enough GTEX Coin for this top-up.");
      return;
    }
    try {
      await api.post("/owner/capital/inject", { club_id: clubId, amount });
      toast.success("GTEX Coin moved to your club treasury.");
      setCoinsToMove("");
      await queryClient.invalidateQueries({ queryKey: ["club-squad-funding-finance"] });
      await queryClient.invalidateQueries({ queryKey: ["finance"] });
      await onClubFunded?.();
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  return (
    <div
      className="mb-8 rounded-xl border border-emerald-500/25 bg-slate-950/70 p-4"
      data-testid="squad-funding-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="gx-eyebrow text-emerald-300">
            {wageMode ? "Staff contracts" : "Complete your 22-player squad"}
          </p>
          <h3 className="gx-display mt-1 text-xl font-bold uppercase text-white">
            {wageMode ? "Top up to pay salaries" : "Squad funding and top-up"}
          </h3>
          <p className="mt-2 max-w-3xl text-xs leading-relaxed text-slate-300">
            {wageMode
              ? `Named staff draw a salary the moment you agree the contract. That salary comes from topped-up or earned club coins, never from the 2,500 GTX welcome grant. The gap for the contracts you have selected is ${fmt(estimatedCoinsNeeded)} GTX. Pay with KoraPay, Paystack, or a Coin Trader, then move the coins into the club. If you would rather not pay, use the default staff member for that role.`
              : `Your club needs 22 registered players across the First Team, Reserves and Academy, including at least one goalkeeper. At a planning average of 200 GTX per player, use the current registered squad, club treasury and wallet balances to estimate any funding gap: ${fmt(estimatedCoinsNeeded)} GTX. The first-500 campaign grant is up to 2,500 GTX and is reserved for active players at GSI 74 and under. Legends, regens, and anyone at GSI 75 or above need topped-up GTX.`}
          </p>
          <p className="mt-1 max-w-3xl text-[11px] text-slate-400">
            The grant is for the first 500 eligible club owners. Some premium, regen, and legend
            player signings require deposited GTX under GTEX acquisition rules.
          </p>
        </div>
        <div className="rounded-lg border border-emerald-500/25 bg-black/25 px-4 py-3 text-right">
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Club treasury</p>
          <p className="gx-mono text-xl font-bold text-emerald-300">{fmt(clubCoins)} GTX</p>
          <p className="mt-1 text-[10px] text-slate-400">
            Squad grant remaining: {fmt(club?.economy?.squad_grant || 0)} GTX
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <p className="gx-label text-slate-300">Option 1 · Buy from GTEX</p>
          <p className="mt-1 text-xs text-slate-400">
            Pay through the platform. Verified payment credits your personal GTEX wallet first.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(["korapay", "paystack"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => {
                  setProviderTouched(true);
                  setProvider(item);
                }}
                className={
                  "gx-btn flex-1 py-1.5 text-xs " +
                  (provider === item ? "gx-btn-primary" : "gx-btn-secondary")
                }
              >
                {item === "korapay" ? "KoraPay" : "Paystack"}
              </button>
            ))}
          </div>
          <label className="gx-label mt-3 block">Amount to pay (₦)</label>
          <input
            className="gx-input mt-1"
            type="number"
            min={100}
            step={1}
            value={nairaAmount || (suggestedNaira === "" ? "" : String(suggestedNaira))}
            onChange={(event) => setNairaAmount(event.target.value)}
            data-testid="squad-platform-amount"
          />
          <p className="mt-2 text-xs text-slate-400">
            Estimated wallet credit: <b className="text-white">{fmt(previewCoins, 2)} GTX</b>
          </p>
          <Btn
            className="mt-3 w-full"
            disabled={!rate || !platformReady || financeQuery.isLoading}
            onClick={buyFromPlatform}
            data-testid="squad-platform-buy"
          >
            Buy GTX from platform
          </Btn>
          {!platformReady && (
            <p className="mt-2 text-[11px] text-amber-300">
              Platform payment is not currently enabled. You can use a verified Coin Trader below.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <p className="gx-label text-slate-300">Move wallet coins into your club</p>
          <p className="mt-1 text-xs text-slate-400">
            After a platform purchase or completed Coin Trader order, move the amount you need into
            this club treasury.
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <span>Available in your wallet</span>
            <b className="gx-mono text-white">{fmt(walletCoins)} GTX</b>
          </div>
          <label className="gx-label mt-3 block">GTX to add to club treasury</label>
          <input
            className="gx-input mt-1"
            type="number"
            min={1}
            max={walletCoins}
            step="0.01"
            value={coinsToMove}
            onChange={(event) => setCoinsToMove(event.target.value)}
            placeholder="Enter amount"
            data-testid="squad-wallet-inject-amount"
          />
          <Btn
            className="mt-3 w-full"
            disabled={!coinsToMove || Number(coinsToMove) <= 0 || Number(coinsToMove) > walletCoins}
            onClick={moveToClub}
            data-testid="squad-wallet-inject"
          >
            Add coins to club treasury
          </Btn>
          <p className="mt-2 text-[11px] text-slate-500">
            The grant is already in your club treasury; it cannot be withdrawn or used for
            facilities.
          </p>
        </div>
      </div>
      <div className="mt-4">
        <ClubCoinTraderFundingPanel initialAmount={String(estimatedCoinsNeeded)} />
      </div>
    </div>
  );
}

function SquadStep({ clubId, onDone }: any) {
  const { data: club, refetch } = useClub(clubId);
  const [unsigningId, setUnsigningId] = useState<string | null>(null);
  const [autopicking, setAutopicking] = useState(false);
  const [tactic, setTactic] = useState("tiki_taka");
  const [formation, setFormation] = useState("4-3-3");
  const [budgetCap, setBudgetCap] = useState("0");
  const [targetSquadSize, setTargetSquadSize] = useState("22");
  const [queue, setQueue] = useState<any[]>([]);
  const [checkingOut, setCheckingOut] = useState(false);

  const allRegisteredSquad = club?.squad || [];
  const registeredCount = Number(
    club?.formation?.total_registered_players ?? allRegisteredSquad.length,
  );
  const remainingToForm = Number(
    club?.formation?.remaining_to_form ?? Math.max(0, 22 - registeredCount),
  );
  const hasGk = Boolean(
    club?.formation?.has_goalkeeper ??
    allRegisteredSquad.some(
      (p: any) =>
        (p.position || "").toLowerCase().includes("goal") ||
        (p.position || "").toLowerCase() === "gk",
    ),
  );
  const isMatchEligible = Boolean(club?.formation?.is_formed ?? (registeredCount >= 22 && hasGk));
  const clubCash = Number(club?.economy?.cash_gtex || 0);

  const handleTacticChange = (nextTactic: string) => {
    setTactic(nextTactic);
    const map: Record<string, string> = {
      tiki_taka: "4-3-3",
      possession: "4-3-3",
      gegenpress: "4-2-3-1",
      counter: "4-2-3-1",
      direct: "4-4-2",
      low_block: "5-4-1",
    };
    if (map[nextTactic]) setFormation(map[nextTactic]);
  };

  const handleUnsign = async (p: any) => {
    setUnsigningId(p.id);
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/unsign`, {
        player_id: p.id || p.player_ref,
      });
      const refund = data?.refunded ?? data?.refund_amount ?? p.value_coin ?? 0;
      toast.success(`Removed ${p.name}. Refunded ${fmt(refund)} GTX to club treasury.`);
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setUnsigningId(null);
    }
  };

  const handleAutopick = async () => {
    setAutopicking(true);
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/autopick`, {
        budget_gtex: Number(budgetCap) > 0 ? Number(budgetCap) : undefined,
        tactic,
        formation,
        target_squad_size: Number(targetSquadSize) || 22,
      });
      const count = data?.signed?.length ?? data?.signed_count ?? 0;
      toast.success(
        data?.message ||
          (count > 0
            ? `Staff auto-picked ${count} player(s) for ${data.formation || formation} (${(data.tactic || tactic).replace(/_/g, " ")})! Remaining cash: ${fmt(data.cash)} GTX`
            : "No affordable players found within current budget."),
      );
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAutopicking(false);
    }
  };

  const grantRemaining = Number(club?.economy?.squad_grant || 0);
  const clubCoinsNow = Number(club?.economy?.cash_gtex || 0);
  const outsideGrant = Math.max(0, clubCoinsNow - grantRemaining);
  const queueValue = (lane: "welcome" | "paid") =>
    queue
      .filter((p) => marketLane(p) === lane)
      .reduce((sum, p) => sum + Number(p.quote?.price || 0), 0);
  const welcomeQueued = queueValue("welcome");
  const paidQueued = queueValue("paid");
  const welcomeOver = welcomeQueued > grantRemaining + 0.001;
  const paidOver = paidQueued > outsideGrant + 0.001;
  const signedWelcome = allRegisteredSquad.filter((p: any) => marketLane(p) === "welcome");
  const signedPaid = allRegisteredSquad.filter((p: any) => marketLane(p) === "paid");
  const signedValue = (rows: any[]) => rows.reduce((sum, p) => sum + Number(p.value_coin || 0), 0);

  const toggleQueue = (player: any) => {
    setQueue((current) => {
      const id = player.player_id;
      if (current.some((p) => p.player_id === id)) return current.filter((p) => p.player_id !== id);
      return [...current, player];
    });
  };

  const checkoutBasket = async () => {
    if (!queue.length) return;
    if (welcomeOver || paidOver) {
      toast.error(
        "A basket is over its available coins. Remove players or top up before you sign them.",
      );
      return;
    }
    setCheckingOut(true);
    try {
      for (const player of queue) {
        await api.post(`/owner/clubs/${clubId}/sign`, { player_id: player.player_id });
      }
      toast.success(`Signed ${queue.length} player(s) from your baskets.`);
      setQueue([]);
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
      refetch();
    } finally {
      setCheckingOut(false);
    }
  };

  return (
    <Panel
      eyebrow="Step 2 · Activate by acquiring players"
      title="Sign your starting squad"
      testid="onboarding-squad-step"
      action={
        <div className="flex flex-col items-end gap-1">
          <p className="text-[10px] uppercase tracking-widest text-slate-500">Club cash</p>
          <Coin amount={club?.economy?.cash_gtex} testid="onboarding-cash" />
        </div>
      }
    >
      {/* Club Legacy: Manager / GM / Chief Scout & Tactical Auto-Pick Controls */}
      <div
        className="mb-4 rounded-sm border border-emerald-500/20 bg-slate-950/80 p-4"
        data-testid="onboarding-tactical-recruitment-panel"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-white/10">
          <div>
            <p className="gx-eyebrow text-emerald-400">Club Legacy & Recruitment Committee</p>
            <p className="text-xs text-slate-300">
              Set the style and budget, then auto-pick or build a basket yourself. Auto-pick stays
              on this page so you can see every player, remove anyone, and top up before you
              continue. Staff are hired on the next page.
            </p>
          </div>
          <Chip tone="cyan">Welcome grant buys active players at GSI 74 and under</Chip>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <label className="text-xs text-slate-400">
            Playing Style / Mentality
            <select
              value={tactic}
              onChange={(e) => handleTacticChange(e.target.value)}
              data-testid="onboarding-autopick-tactic"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            >
              <option value="tiki_taka">Tiki-Taka (4-3-3 Possession)</option>
              <option value="gegenpress">Gegenpress (4-2-3-1 High Press)</option>
              <option value="possession">Control Possession (4-3-3)</option>
              <option value="counter">Fast Counter-Attack (4-2-3-1)</option>
              <option value="direct">Direct Vertical (4-4-2)</option>
              <option value="low_block">Low-Block Fortress (5-4-1)</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Preferred Formation
            <select
              value={formation}
              onChange={(e) => setFormation(e.target.value)}
              data-testid="onboarding-autopick-formation"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            >
              <option value="4-3-3">4-3-3</option>
              <option value="4-2-3-1">4-2-3-1</option>
              <option value="4-4-2">4-4-2</option>
              <option value="3-5-2">3-5-2</option>
              <option value="3-4-3">3-4-3</option>
              <option value="5-4-1">5-4-1</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Recruitment Budget Cap (GTX)
            <input
              type="number"
              value={budgetCap}
              onChange={(e) => setBudgetCap(e.target.value)}
              data-testid="onboarding-autopick-budget"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            />
          </label>
          <label className="text-xs text-slate-400">
            Target Squad Size
            <input
              type="number"
              min={22}
              max={25}
              value={targetSquadSize}
              onChange={(e) => setTargetSquadSize(e.target.value)}
              data-testid="onboarding-autopick-size"
              className="mt-1 w-full rounded border border-white/15 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
            />
          </label>
        </div>
      </div>

      {/* Top Status & Auto-pick Toolbar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-sm border border-white/10 bg-slate-950/60 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone={isMatchEligible ? "emerald" : "gold"} testid="onboarding-squad-count">
            {club?.formation?.progress_label || `${registeredCount}/22 players registered`}
          </Chip>
          <Chip tone={hasGk ? "emerald" : "red"}>
            {hasGk ? "✓ Goalkeeper registered" : "⚠ Needs a goalkeeper"}
          </Chip>
          <span className="text-xs text-slate-400">
            A club becomes match-eligible with 22 players (First Team, Reserves, Academy) including
            a goalkeeper.
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Btn
            variant={isMatchEligible ? "ghost" : "primary"}
            disabled={autopicking || isMatchEligible}
            onClick={handleAutopick}
            className="flex items-center gap-1.5"
            data-testid="onboarding-autopick-button"
            title="Automatically sign affordable players to complete your squad within available funds"
          >
            <Sparkles size={14} className={autopicking ? "animate-spin" : "text-amber-300"} />
            {autopicking
              ? "Auto-picking…"
              : isMatchEligible
                ? "Squad Complete ✓"
                : "⚡ Auto-Pick within Budget"}
          </Btn>
        </div>
      </div>

      {/* Low cash warning if stuck */}
      {!isMatchEligible && clubCash < 800 && registeredCount > 0 && (
        <div className="mb-6 flex items-start gap-3 rounded border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-400" />
          <div>
            <p className="font-semibold text-amber-300">
              Low Treasury Balance ({fmt(clubCash)} GTX remaining)
            </p>
            <p className="mt-0.5 text-slate-300">
              You need {remainingToForm} more registered player(s)
              {!hasGk ? " including a goalkeeper" : ""}. The registration minimum and any optional
              market signings are separate requirements. Remove any signed player below to receive a
              full refund, or use <b>Auto-Pick</b> to sign affordable talent.
            </p>
          </div>
        </div>
      )}

      <div className="mb-6 grid gap-3 md:grid-cols-2" data-testid="onboarding-basket-totals">
        <div
          className={`rounded border p-3 ${welcomeOver ? "border-rose-500/50 bg-rose-500/10" : "border-emerald-500/30 bg-emerald-500/5"}`}
        >
          <p className="text-[10px] uppercase tracking-widest text-emerald-300">
            Welcome grant basket
          </p>
          <p className="mt-1 text-sm text-white">
            Signed {fmt(signedValue(signedWelcome))} GTX · In basket {fmt(welcomeQueued)} GTX
          </p>
          <p className="text-xs text-slate-400">
            Grant remaining {fmt(grantRemaining)} GTX. Active players at GSI 74 and under only.
          </p>
          {welcomeOver && (
            <p className="mt-1 text-xs text-rose-300">
              This basket is over the welcome grant. Remove players or those signings will be
              refused.
            </p>
          )}
        </div>
        <div
          className={`rounded border p-3 ${paidOver ? "border-rose-500/50 bg-rose-500/10" : "border-amber-500/30 bg-amber-500/5"}`}
        >
          <p className="text-[10px] uppercase tracking-widest text-amber-300">Paid basket</p>
          <p className="mt-1 text-sm text-white">
            Signed {fmt(signedValue(signedPaid))} GTX · In basket {fmt(paidQueued)} GTX
          </p>
          <p className="text-xs text-slate-400">
            Topped-up coins available {fmt(outsideGrant)} GTX. Legends, regens, and GSI 75+ live
            here.
          </p>
          {paidOver && (
            <p className="mt-1 text-xs text-rose-300">
              This basket needs a top-up. The welcome grant cannot pay for these players.
            </p>
          )}
        </div>
      </div>

      {queue.length > 0 && (
        <div
          className="mb-6 rounded border border-white/10 bg-black/30 p-3"
          data-testid="pending-squad-basket"
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-white">
              Basket not signed yet ({queue.length})
            </p>
            <Btn
              disabled={checkingOut || welcomeOver || paidOver}
              onClick={checkoutBasket}
              data-testid="checkout-squad-basket"
            >
              {checkingOut ? "Signing…" : "Sign basket"}
            </Btn>
          </div>
          <div className="flex flex-wrap gap-2">
            {queue.map((p) => (
              <button
                key={p.player_id}
                type="button"
                className="rounded border border-white/10 px-2 py-1 text-xs text-slate-200"
                onClick={() => toggleQueue(p)}
              >
                {p.canonical_display_name || p.player_name} · {fmt(p.quote?.price)} GTX ·{" "}
                {marketLane(p) === "welcome" ? "grant" : "paid"} · remove
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Squad Basket */}
      <div
        className="mb-8 rounded-sm border border-white/10 bg-slate-950/40 p-4"
        data-testid="squad-basket"
      >
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingCart size={16} className="text-emerald-400" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
              Signed players{" "}
              <span className="text-xs font-normal text-slate-400">
                ({allRegisteredSquad.length})
              </span>
            </h3>
          </div>
          {allRegisteredSquad.length > 0 && (
            <span className="text-xs text-slate-400">
              Total Squad Value:{" "}
              <b className="text-emerald-300">
                {fmt(
                  allRegisteredSquad.reduce(
                    (sum: number, p: any) => sum + Number(p.value_coin || 0),
                    0,
                  ),
                )}{" "}
                GTX
              </b>
            </span>
          )}
        </div>

        {allRegisteredSquad.length === 0 ? (
          <div className="rounded border border-dashed border-white/10 p-6 text-center text-xs text-slate-500">
            {isMatchEligible
              ? "Your 22-player starter squad is already registered. Browse the transfer market below to sign additional players and strengthen your club."
              : `No additional market signings yet (${registeredCount} of 22 players registered${hasGk ? "" : ", goalkeeper still needed"}). Use Auto-Pick or browse the transfer market below to complete your squad.`}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {allRegisteredSquad.map((p: any) => {
              const isGk =
                (p.position || "").toLowerCase().includes("goal") ||
                (p.position || "").toLowerCase() === "gk";
              const posBadge = isGk
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : (p.position || "").toLowerCase().includes("def")
                  ? "bg-blue-500/20 text-blue-300 border-blue-500/40"
                  : (p.position || "").toLowerCase().includes("mid")
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : "bg-rose-500/20 text-rose-300 border-rose-500/40";

              const isRemoving = unsigningId === p.id;

              return (
                <div
                  key={p.id}
                  data-testid={`basket-player-${p.id}`}
                  className="group relative flex flex-col justify-between rounded border border-white/10 bg-slate-900/60 p-3 transition-colors hover:border-white/20"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-block rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${posBadge}`}
                        >
                          {posShort(p.position)}
                        </span>
                        <span className="text-[10px] font-bold text-slate-400">{p.rating} OVR</span>
                      </div>
                      <p
                        className="mt-1.5 truncate text-sm font-semibold text-white"
                        title={p.name}
                      >
                        {p.name}
                      </p>
                      <p className="gx-mono mt-0.5 text-xs text-emerald-300">
                        {fmt(p.value_coin)} GTX ·{" "}
                        {marketLane(p) === "welcome" ? "welcome grant" : "paid"}
                      </p>
                    </div>

                    <button
                      type="button"
                      disabled={isRemoving}
                      onClick={() => handleUnsign(p)}
                      title={`Remove ${p.name} and refund ~${fmt(p.value_coin)} GTX`}
                      data-testid={`remove-player-${p.id}`}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-rose-500/30 bg-rose-500/10 text-rose-300 transition-colors hover:bg-rose-500 hover:text-white disabled:opacity-50"
                    >
                      {isRemoving ? (
                        <span className="animate-spin text-xs">…</span>
                      ) : (
                        <Trash2 size={13} />
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <SquadFundingPanel clubId={clubId} club={club} onClubFunded={refetch} />

      {/* Transfer Market Explorer */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="gx-eyebrow text-slate-400">Transfer Market Explorer</p>
          <span className="text-xs text-slate-500">
            Add players to a basket before you pay. Filter legends, regens, or world stars.
          </span>
        </div>
        <MarketTable
          clubId={clubId}
          signedRefs={allRegisteredSquad.map((p: any) => p.player_ref)}
          onSigned={() => refetch()}
          clubCash={clubCash}
          queuedIds={queue.map((p) => p.player_id)}
          onQueue={toggleQueue}
        />
      </div>
      <div className="mt-6 flex items-center justify-between gap-3 border-t border-white/10 pt-4">
        <p className="text-xs text-slate-400">
          {isMatchEligible
            ? "The squad stays here until you continue. Remove anyone you do not want, then hire your staff."
            : `Register ${remainingToForm} more player${remainingToForm === 1 ? "" : "s"}${hasGk ? "" : " including a goalkeeper"} before you continue.`}
        </p>
        <Btn disabled={!isMatchEligible} onClick={onDone} data-testid="onboarding-squad-continue">
          Squad looks right — hire staff
        </Btn>
      </div>
    </Panel>
  );
}

function seasonSalaryFromDemand(raw: number) {
  const amount = Math.max(0, Math.round(Number(raw) || 0));
  const scaled = amount >= 1000 ? Math.floor(amount / 10) : amount;
  return Math.max(40, scaled);
}

function seasonSalaryGtx(raw: number) {
  const amount = Math.max(0, Math.round(Number(raw) || 0));
  const scaled = amount >= 1000 ? Math.floor(amount / 10) : amount;
  const season = Math.max(150, scaled);
  return Math.max(40, Math.floor((season * 35) / 100));
}

const STAFF_ROLES = [
  {
    key: "first_team_manager",
    label: "First-team manager",
    hint: "Picks the side and the tactics.",
  },
  {
    key: "general_manager",
    label: "General manager",
    hint: "Runs recruitment, wages, and the squad plan.",
  },
  {
    key: "head_of_youth_development",
    label: "Head of youth development",
    hint: "Runs the academy and the pathway into the first team.",
  },
];

function StaffRolePicker({ clubId, role, chosen, onChoose }: any) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["onboarding-staff", clubId, role.key, query],
    queryFn: async () => {
      const people: any[] = [];
      if (role.key === "first_team_manager") {
        try {
          const { data: catalog } = await api.get("/managers/catalog", {
            params: { search: query || undefined, limit: 12 },
          });
          for (const manager of catalog.items || []) {
            people.push({
              key: `manager:${manager.manager_id}`,
              name: manager.display_name,
              detail: `${manager.rarity || "coach"} · ${(manager.mentality || "").replace(/_/g, " ")}`,
              blurb: manager.philosophy_summary,
              salary: seasonSalaryGtx(
                manager.annual_wage_fancoin || manager.recruit_price_fancoin || 3500,
              ),
              manager_id: manager.manager_id,
            });
          }
        } catch {
          /* The staff market below still covers this role. */
        }
      }
      let fromMarket = 0;
      try {
        const { data: market } = await api.get(
          `/owner/clubs/${clubId}/living-world/staff-market/candidates`,
          {
            params: {
              role: role.key,
              search: query || undefined,
              limit: 12,
              employment_status: "all",
            },
          },
        );
        for (const candidate of market.candidates || []) {
          fromMarket += 1;
          people.push({
            key: `profile:${candidate.profile_id}`,
            name: candidate.name,
            detail: `${candidate.role_label || role.label} · ${candidate.style || candidate.nation || "Staff"}`,
            blurb: candidate.nation
              ? `${candidate.nation} · rating ${candidate.rating}`
              : `Rating ${candidate.rating}`,
            salary:
              candidate.expected_salary_fan_coin || candidate.expected_salary_gtex
                ? seasonSalaryFromDemand(
                    candidate.expected_salary_fan_coin || candidate.expected_salary_gtex,
                  )
                : null,
            profile_id: candidate.profile_id,
          });
        }
      } catch {
        fromMarket = 0;
      }
      if (fromMarket === 0) {
        try {
          const { data: office } = await api.get(`/owner/clubs/${clubId}/staff`);
          const needle = query.trim().toLowerCase();
          for (const candidate of office.candidates || []) {
            if (candidate.role !== role.key) continue;
            const name = String(candidate.name || "");
            if (needle && !name.toLowerCase().includes(needle)) continue;
            people.push({
              key: `catalog:${candidate.id || candidate.staff_id}`,
              name,
              detail: candidate.specialty || candidate.style || role.label,
              blurb: candidate.bio,
              salary:
                candidate.salary_gtx || candidate.salary
                  ? seasonSalaryGtx(candidate.salary_gtx || candidate.salary)
                  : null,
              profile_id: candidate.id || candidate.staff_id,
            });
          }
        } catch {
          /* Default caretaker remains available. */
        }
      }
      return people.slice(0, 12);
    },
  });
  return (
    <div
      className="rounded-sm border border-white/10 bg-slate-950/50 p-4"
      data-testid={`staff-role-${role.key}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">{role.label}</p>
          <p className="text-xs text-slate-400">{role.hint}</p>
        </div>
        {chosen ? (
          <Chip tone="emerald">{chosen.use_default ? "Default" : chosen.name}</Chip>
        ) : (
          <Chip>Not chosen</Chip>
        )}
      </div>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(search.trim());
        }}
      >
        <input
          className="gx-input"
          placeholder={`Search ${role.label.toLowerCase()}s`}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          data-testid={`staff-search-${role.key}`}
        />
        <Btn type="submit" variant="secondary">
          Search
        </Btn>
      </form>
      <div className="mt-3 space-y-2">
        {isLoading ? <p className="text-xs text-slate-500">Searching the staff market…</p> : null}
        {(data || []).map((person: any) => (
          <div
            key={person.key}
            className="flex items-start justify-between gap-3 rounded border border-white/10 px-3 py-2"
          >
            <div>
              <p className="text-sm font-semibold text-white">{person.name}</p>
              <p className="text-[11px] text-slate-400">{person.detail}</p>
              <p className="text-[11px] text-emerald-300">
                {person.salary == null ? "Wage not filed" : `Season salary ${fmt(person.salary)} GTX`}
              </p>
            </div>
            <Btn
              variant="secondary"
              onClick={() => onChoose({ ...person, use_default: false, role: role.key })}
              data-testid={`choose-staff-${person.manager_id || person.profile_id}`}
            >
              Agree contract
            </Btn>
          </div>
        ))}
        {!isLoading && (data || []).length === 0 ? (
          <p className="text-xs text-slate-500">
            No staff match that search. Try another name, or use the default.
          </p>
        ) : null}
      </div>
      <Btn
        className="mt-3"
        variant="ghost"
        onClick={() => onChoose({ use_default: true, role: role.key, name: "Default", salary: 0 })}
        data-testid={`staff-default-${role.key}`}
      >
        Use default — no salary
      </Btn>
    </div>
  );
}

function ManagerStep({ clubId, onDone }: any) {
  const { data: club, refetch } = useClub(clubId);
  const [choices, setChoices] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState(false);
  const salaryDue = STAFF_ROLES.reduce(
    (sum, role) => sum + Number(choices[role.key]?.salary || 0),
    0,
  );
  const outsideGrant = Math.max(
    0,
    Number(club?.economy?.cash_gtex || 0) - Number(club?.economy?.squad_grant || 0),
  );
  const shortfall = Math.max(0, salaryDue - outsideGrant);
  const ready = STAFF_ROLES.every((role) => choices[role.key]);
  const confirm = async () => {
    setBusy(true);
    try {
      for (const role of STAFF_ROLES) {
        const choice = choices[role.key];
        await api.post(`/owner/clubs/${clubId}/onboarding/staff`, {
          role: role.key,
          use_default: Boolean(choice.use_default),
          manager_id: choice.manager_id,
          profile_id: choice.profile_id,
        });
      }
      toast.success("Staff contracts are in place.");
      refetch();
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
      refetch();
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel
      eyebrow="Step 3 · Hire the people who run the club"
      title="Appoint your staff"
      testid="onboarding-manager-step"
    >
      <p className="mb-4 text-sm text-slate-300">
        A club needs a first-team manager, a general manager, and a head of youth development. They
        are not bought. They draw a salary when you agree the contract. Search the full market. If
        the salary is more than you want to pay right now, use the default for that role and hire a
        named person later.
      </p>
      <div className="mb-4 grid gap-4">
        {STAFF_ROLES.map((role) => (
          <StaffRolePicker
            key={role.key}
            clubId={clubId}
            role={role}
            chosen={choices[role.key]}
            onChoose={(choice: any) =>
              setChoices((current) => ({ ...current, [role.key]: choice }))
            }
          />
        ))}
      </div>
      <p className="mb-3 text-xs text-slate-400" data-testid="staff-salary-total">
        Season salaries selected: <b className="text-white">{fmt(salaryDue)} GTX</b>. Coins outside
        the welcome grant: <b className="text-white">{fmt(outsideGrant)} GTX</b>.
      </p>
      <SquadFundingPanel
        clubId={clubId}
        club={club}
        onClubFunded={refetch}
        purpose="wages"
        shortfall={shortfall}
      />
      <Btn disabled={!ready || busy} onClick={confirm} data-testid="confirm-onboarding-staff">
        {busy ? "Agreeing contracts…" : "Confirm staff and continue"}
      </Btn>
    </Panel>
  );
}

function AcademyStep({ clubId, onDone }: { clubId: string; onDone: () => void }) {
  const { data: club, refetch } = useClub(clubId);
  const [busyIntake, setBusyIntake] = useState(false);

  const regens = (club?.squad || []).filter(
    (p: any) => p.is_regen || p.squad_status === "academy" || p.acquired_via === "academy",
  );

  const handleManualIntake = async () => {
    setBusyIntake(true);
    try {
      await api.post(`/owner/clubs/${clubId}/academy/intake`);
      toast.success("Genesis academy intake scouted! New wonderkids signed.");
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyIntake(false);
    }
  };

  const hoydName = club?.staff?.head_of_youth_development?.name || "";
  const hoydRating = club?.staff?.head_of_youth_development?.rating;

  return (
    <Panel
      eyebrow="Step 4 · Youth Academy & Genesis Wonderkids"
      title="Inaugural Academy Intake"
      testid="onboarding-academy-step"
      action={
        <Btn
          onClick={onDone}
          className="flex items-center gap-2"
          data-testid="onboarding-proceed-competition"
        >
          <span>Open my club</span>
          <ArrowRight size={14} />
        </Btn>
      }
    >
      <div className="mb-6">
        <GtexSceneViewport
          sceneId="academy_upgrade"
          compact
          title={`3D Youth Academy Campus · Genesis Intake`}
          subtitle={`${club?.club_name || "GTEX Club"} · Inaugural Class of Homegrown Wonderkids`}
          badgeText="3D GENESIS INTAKE"
          clubName={club?.club_name}
          facilityLevel={1}
          stats={[
            { label: "Genesis Regens", value: `${regens.length} Prospects`, accent: "#00E676" },
            { label: "Campus Tier", value: "Level 1 Academy", accent: "#38BDF8" },
            { label: "Ceilings", value: "85–95 POT", accent: "#F5B83D" },
          ]}
        />
      </div>

      {/* Head of Youth Development Briefing */}
      <div className="mb-6 rounded-sm border border-purple-500/20 bg-purple-950/20 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-purple-500/20 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              <Sprout size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-white uppercase tracking-wider">
                {hoydName || "Head of youth"}{" "}
                <span className="text-[11px] font-normal text-purple-300">
                  · Head of Youth Development{hoydRating ? ` (Rating: ${hoydRating})` : ""}
                </span>
              </p>
              <p className="text-[11px] text-slate-400">Youth Scouting & Development Briefing</p>
            </div>
          </div>
          <Chip tone="cyan">HOYD Autonomy Active</Chip>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-slate-300">
          "Welcome to the training grounds, Boss. While the first-team squad was being finalized,
          our academy scouts canvassed local regional trials and secured our inaugural class of
          youth wonderkids. These regens are training on Pitch 3 and possess elite development
          ceilings. With proper match exposure, coaching, and facility upgrades, they will form the
          backbone of your dynasty."
        </p>
      </div>

      {/* Genesis Wonderkids Grid */}
      <div className="mb-6 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="gx-eyebrow text-emerald-400">Inaugural Academy Class</p>
            <p className="text-xs text-slate-400">
              High-potential homegrown talents signed directly to your youth roster
            </p>
          </div>
          {regens.length === 0 && (
            <Btn
              variant="secondary"
              disabled={busyIntake}
              onClick={handleManualIntake}
              className="flex items-center gap-1.5 text-xs"
              data-testid="onboarding-scout-genesis-intake"
            >
              <Sparkles size={13} className="text-amber-300" />
              <span>{busyIntake ? "Scouting Intake…" : "Scout Genesis Intake"}</span>
            </Btn>
          )}
        </div>

        {regens.length === 0 ? (
          <div className="rounded border border-dashed border-white/10 p-6 text-center text-xs text-slate-400">
            <p>Your genesis academy class is preparing for their medicals.</p>
            <Btn className="mt-3" disabled={busyIntake} onClick={handleManualIntake}>
              {busyIntake ? "Generating Wonderkids…" : "Trigger Inaugural Intake"}
            </Btn>
          </div>
        ) : (
          <div
            className="grid grid-cols-1 gap-4 md:grid-cols-3"
            data-testid="onboarding-genesis-regens"
          >
            {regens.map((p: any) => {
              const pers = p.personality || p.personality_json || {};
              const archetype = p.archetype || pers.archetype || "Ambitious Prodigy";
              const mood = p.mood_state || pers.mood || "Thriving";
              const monologue =
                p.inner_monologue ||
                pers.inner_monologue ||
                `Grinding daily with the academy coaches. When my call-up comes, I'll be 100% ready.`;
              const ceiling = Math.max(0, (p.potential || 85) - (p.rating || 60));

              return (
                <div
                  key={p.id || p.name}
                  className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 shadow-lg hover:border-emerald-500/30 transition-colors"
                  data-testid={`genesis-regen-${p.id}`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 border-b border-white/10 pb-3">
                      <div>
                        <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 text-[9px] font-black uppercase">
                          {archetype}
                        </span>
                        <h4 className="mt-1 text-sm font-bold text-white">{p.name}</h4>
                        <p className="text-[11px] text-slate-400">
                          Age {p.age || 17} · {posShort(p.position)}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="gx-mono text-lg font-black text-white">{p.rating}</span>
                        <span className="text-[10px] text-slate-500"> OVR</span>
                        <p className="gx-mono text-[11px] font-bold text-amber-300">
                          POT {p.potential || 88}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>Ceiling</span>
                        <span className="gx-mono text-emerald-300 font-bold">
                          +{ceiling} Growth
                        </span>
                      </div>
                      <div className="h-1.5 rounded-sm bg-white/5">
                        <div
                          className="h-1.5 rounded-sm bg-gradient-to-r from-emerald-500 to-amber-400"
                          style={{
                            width: `${Math.min(100, ((p.rating || 60) / Math.max(1, p.potential || 90)) * 100)}%`,
                          }}
                        />
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Mood: <b className="text-slate-200">{mood}</b>
                      </p>
                      <div className="rounded border border-white/5 bg-black/40 p-2 text-[11px] italic text-slate-300">
                        "{monologue}"
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[10px] text-slate-400">
                    <span className="text-purple-300">HOYD Monitored</span>
                    <span className="gx-mono text-emerald-300">
                      {fmt(p.value_coin || 3500)} GTX
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Build-A-Son Legacy Program Educational Banner */}
      <div
        className="mb-6 rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-amber-950/20 to-black p-4"
        data-testid="onboarding-build-a-son-banner"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40">
              <Dna size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-xs font-black uppercase tracking-wider text-amber-300">
                  Build-A-Son Legacy Program
                </p>
                <Chip tone="gold">Dynasty Feature</Chip>
              </div>
              <p className="mt-1 text-xs text-slate-300 leading-relaxed max-w-2xl">
                As your senior players establish legendary status, you can pass on their genetic DNA
                bloodlines, mental composure, and fan devotion to custom dynasty scions right here
                in your Academy Command (<b>/app/academy</b>).
              </p>
            </div>
          </div>
          <div className="shrink-0">
            <div className="text-right">
              <p className="text-[10px] text-slate-500 uppercase">Bloodlines Engine</p>
              <p className="text-xs font-bold text-amber-300">20/20 Loyalty Guarantee</p>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Proceed Action */}
      <div className="flex items-center justify-between border-t border-white/10 pt-4">
        <p className="text-xs text-slate-400">
          Your wonderkids will continue developing as competitive matchdays and training cycles
          progress.
        </p>
        <Btn
          onClick={onDone}
          className="flex items-center gap-2"
          data-testid="onboarding-proceed-competition-bottom"
        >
          <span>Open my club</span>
          <ArrowRight size={14} />
        </Btn>
      </div>
    </Panel>
  );
}

function CreateFirstClub({ onDone, onCancel, another }: any) {
  const [wizardStep, setWizardStep] = useState<
    "name" | "philosophy" | "roster" | "studio" | "review"
  >("name");
  const [name, setName] = useState("");
  const loc = useClubLocation();
  const [busy, setBusy] = useState(false);

  // Club DNA plus deterministic, ready-made visual choices. No AI services are called.
  const [recruitmentFocus, setRecruitmentFocus] = useState("youth");
  const [preferredAgeBracket, setPreferredAgeBracket] = useState("U23");
  const [nationalityFocus, setNationalityFocus] = useState("preferred");
  const [preferredStyle, setPreferredStyle] = useState("traditional");
  const [recommendation, setRecommendation] = useState<any>(null);
  const [selectedCrestIdx, setSelectedCrestIdx] = useState(0);
  const [crestFilter, setCrestFilter] = useState<"all" | "heritage" | "modern" | "royal">("all");
  const [crestShape, setCrestShape] = useState<"all" | "shield" | "round" | "diamond" | "pennant">(
    "all",
  );
  const [crestQuery, setCrestQuery] = useState("");
  const [crestPage, setCrestPage] = useState(0);
  const [kitPattern, setKitPattern] = useState("all");
  const [kitQuery, setKitQuery] = useState("");
  const [kitPage, setKitPage] = useState(0);
  const [selectedKitTab, setSelectedKitTab] = useState<"home" | "away" | "third" | "goalkeeper">(
    "home",
  );
  const [selectedKitPresetId, setSelectedKitPresetId] = useState(KIT_PRESETS[0].id);
  const [kitSet, setKitSet] = useState<any>(null);

  const location = loc.validation;
  const clubName = name.trim();

  // Build crest and uniform previews from GTEX's bundled design library.
  const handleGenerateIdentity = () => {
    if (clubName.length < 3) {
      toast.error("Enter a club name with at least 3 characters.");
      return;
    }
    if ("error" in location) {
      toast.error(location.error);
      return;
    }

    const dna = buildClubDNA(
      clubName,
      location.cityName,
      location.countryCode,
      recruitmentFocus,
      preferredAgeBracket,
      nationalityFocus,
    );
    const crestConcepts = buildCrestLibrary(clubName);
    const initialCrestIndex = preferredCrestIndex(crestConcepts, preferredStyle);
    const firstKitPreset = KIT_PRESETS[0];

    setRecommendation({
      short_code: crestConcepts[0]?.initials,
      crest_concepts: crestConcepts,
      ...dna,
    });
    setSelectedCrestIdx(initialCrestIndex);
    setCrestFilter("all");
    setCrestShape("all");
    setCrestQuery("");
    setCrestPage(0);
    setKitPattern("all");
    setKitQuery("");
    setKitPage(0);
    setSelectedKitPresetId(firstKitPreset.id);
    setKitSet(buildKitSet(firstKitPreset.id, clubName));
    setSelectedKitTab("home");
    setWizardStep("studio");
    toast.success(
      `Design library ready: ${crestConcepts.length} crest designs and ${KIT_PRESETS.length} uniform collections.`,
    );
  };

  const create = async () => {
    if (clubName.length < 3) {
      toast.error("Enter a club name with at least 3 characters.");
      return;
    }
    const validatedLocation = loc.validation;
    if ("error" in validatedLocation) {
      toast.error(validatedLocation.error);
      return;
    }
    setBusy(true);
    try {
      const slug = `${clubName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36).slice(-4)}`;
      const activeCrest = recommendation?.crest_concepts?.[selectedCrestIdx];
      const homeKit = kitSet?.home;

      const primaryColor = activeCrest?.primary_color || homeKit?.primary_color || "#0F766E";
      const secondaryColor = activeCrest?.secondary_color || homeKit?.secondary_color || "#F8FAFC";
      const accentColor = activeCrest?.accent_color || homeKit?.accent_color || "#F59E0B";

      const dnaPayload = recommendation
        ? {
            primary_philosophy: recommendation.primary_philosophy,
            secondary_philosophies: recommendation.secondary_philosophies,
            nationality_mode: recommendation.nationality_mode,
            target_nationalities: recommendation.target_nationalities,
            allow_dual_nationality: true,
            age_mode: recommendation.age_mode,
            preferred_max_age: recommendation.preferred_max_age,
            allow_age_exceptions: true,
            transfer_strategy: recommendation.transfer_strategy,
            financial_philosophy: recommendation.financial_philosophy,
            club_vision_narrative: recommendation.vision_narrative,
          }
        : {
            primary_philosophy:
              recruitmentFocus === "academy"
                ? "academy_first"
                : recruitmentFocus === "selling"
                  ? "selling_club"
                  : "youth_development",
            secondary_philosophies: ["financially_sustainable"],
            nationality_mode: nationalityFocus,
            target_nationalities:
              nationalityFocus === "none" ? [] : [validatedLocation.countryCode],
            allow_dual_nationality: true,
            age_mode: preferredAgeBracket === "none" ? "none" : "preferred",
            preferred_max_age:
              preferredAgeBracket === "none"
                ? null
                : parseInt(preferredAgeBracket.replace("U", ""), 10),
            allow_age_exceptions: true,
            transfer_strategy: "buy_young_develop_sell",
            financial_philosophy: "sustainable",
          };

      const badgePayload = activeCrest
        ? {
            shape: activeCrest.shape,
            icon_family: activeCrest.icon_family,
            primary_color: activeCrest.primary_color,
            secondary_color: activeCrest.secondary_color,
            accent_color: activeCrest.accent_color,
            initials: activeCrest.initials,
            trophy_star_count: activeCrest.trophy_stars,
            badge_url: activeCrest.data_uri,
          }
        : null;

      const jerseyPayload = kitSet
        ? {
            home: {
              primary_color: kitSet.home.primary_color,
              secondary_color: kitSet.home.secondary_color,
              accent_color: kitSet.home.accent_color,
              pattern_type: kitSet.home.pattern_type,
              collar_style: kitSet.home.collar_style,
              sleeve_style: kitSet.home.sleeve_style,
              shorts_color: kitSet.home.shorts_color,
              socks_color: kitSet.home.socks_color,
              front_text: kitSet.home.front_text,
            },
            away: {
              primary_color: kitSet.away.primary_color,
              secondary_color: kitSet.away.secondary_color,
              accent_color: kitSet.away.accent_color,
              pattern_type: kitSet.away.pattern_type,
              collar_style: kitSet.away.collar_style,
              sleeve_style: kitSet.away.sleeve_style,
              shorts_color: kitSet.away.shorts_color,
              socks_color: kitSet.away.socks_color,
              front_text: kitSet.away.front_text,
            },
            third: {
              primary_color: kitSet.third.primary_color,
              secondary_color: kitSet.third.secondary_color,
              accent_color: kitSet.third.accent_color,
              pattern_type: kitSet.third.pattern_type,
              collar_style: kitSet.third.collar_style,
              sleeve_style: kitSet.third.sleeve_style,
              shorts_color: kitSet.third.shorts_color,
              socks_color: kitSet.third.socks_color,
              front_text: kitSet.third.front_text,
            },
            goalkeeper: {
              primary_color: kitSet.goalkeeper.primary_color,
              secondary_color: kitSet.goalkeeper.secondary_color,
              accent_color: kitSet.goalkeeper.accent_color,
              pattern_type: kitSet.goalkeeper.pattern_type,
              collar_style: kitSet.goalkeeper.collar_style,
              sleeve_style: kitSet.goalkeeper.sleeve_style,
              shorts_color: kitSet.goalkeeper.shorts_color,
              socks_color: kitSet.goalkeeper.socks_color,
              front_text: kitSet.goalkeeper.front_text,
            },
          }
        : null;

      await api.post("/clubs", {
        club_name: clubName,
        slug,
        short_name: (activeCrest?.initials || clubName.slice(0, 12)).toUpperCase(),
        crest_asset_ref: activeCrest?.data_uri || null,
        primary_color: primaryColor,
        secondary_color: secondaryColor,
        accent_color: accentColor,
        ...clubLocationPayload(validatedLocation),
        club_type: "community",
        dna_policy: dnaPayload,
        badge_profile: badgePayload,
        jersey_set: jerseyPayload,
      });
      onDone();
    } catch (e) {
      toast.error(clubCreateErrorMessage(e, errMsg));
    } finally {
      setBusy(false);
    }
  };

  const crestConcepts = recommendation?.crest_concepts || [];
  const visibleCrests = filterCrestLibrary(crestConcepts, {
    finish: crestFilter,
    shape: crestShape,
    query: crestQuery,
  });
  const crestPageCount = Math.max(1, Math.ceil(visibleCrests.length / CREST_PAGE_SIZE));
  const safeCrestPage = Math.min(crestPage, crestPageCount - 1);
  const pagedCrests = visibleCrests.slice(
    safeCrestPage * CREST_PAGE_SIZE,
    safeCrestPage * CREST_PAGE_SIZE + CREST_PAGE_SIZE,
  );
  const visibleKits = filterKitPresets(KIT_PRESETS, { pattern: kitPattern, query: kitQuery });
  const kitPageCount = Math.max(1, Math.ceil(visibleKits.length / KIT_PAGE_SIZE));
  const safeKitPage = Math.min(kitPage, kitPageCount - 1);
  const pagedKits = visibleKits.slice(
    safeKitPage * KIT_PAGE_SIZE,
    safeKitPage * KIT_PAGE_SIZE + KIT_PAGE_SIZE,
  );
  const featuredCrests =
    safeCrestPage === 0 &&
    crestFilter === "all" &&
    crestShape === "all" &&
    crestQuery.trim() === "";

  return (
    <div
      className="gx-pitch-grid flex min-h-screen items-center justify-center bg-[#070B11] px-4 py-8"
      data-testid="create-first-club"
    >
      <div className={`w-full ${wizardStep === "studio" ? "max-w-5xl" : "max-w-2xl"}`}>
        {/* Step Indicator Header */}
        <div className="mb-4 flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider text-emerald-400">
            GTEX Club Identity & DNA Studio
          </span>
          <div className="flex items-center gap-1.5">
            {["name", "philosophy", "roster", "studio", "review"].map((step, idx) => (
              <span
                key={step}
                className={`h-1.5 w-6 rounded-full transition-colors ${
                  wizardStep === step ? "bg-emerald-400" : "bg-white/10"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Wizard Step 1: Club Name & Location */}
        {wizardStep === "name" && (
          <Panel
            eyebrow="Step 1 of 5 · Official Registry"
            title="Name your football club"
            className="w-full"
          >
            <p className="mb-4 text-xs text-slate-300">
              Establish your club's legal name and home metropolitan region.
            </p>
            <input
              data-testid="first-club-name-input"
              aria-label="Club name"
              className="gx-input text-base font-semibold"
              placeholder="e.g., Olympique Belleville or Real Madrid"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <div className="mt-4">
              <ClubLocationFields state={loc} testIdPrefix="first-club" disabled={busy} />
            </div>

            <div className="mt-6 flex flex-col gap-2 sm:flex-row">
              <Btn
                className="flex-1"
                disabled={clubName.length < 3 || !location.valid || busy}
                onClick={() => setWizardStep("philosophy")}
                data-testid="first-club-next-philosophy"
              >
                Next: Football Philosophy & Culture →
              </Btn>
              <Btn
                variant="ghost"
                disabled={clubName.length < 3 || !location.valid || busy}
                onClick={create}
                data-testid="first-club-create-button"
              >
                Quick Create (Default Kit)
              </Btn>
            </div>
            <Btn
              className="mt-2 w-full"
              variant="ghost"
              disabled={busy}
              onClick={onCancel}
              data-testid="skip-club-creation-button"
            >
              Not now — explore GTEX first
            </Btn>
          </Panel>
        )}

        {/* Wizard Step 2: Philosophy & Recruitment Culture */}
        {wizardStep === "philosophy" && (
          <Panel
            eyebrow="Step 2 of 5 · Club DNA"
            title="Choose your football philosophy"
            className="w-full"
          >
            <p className="mb-4 text-xs text-slate-300">
              Your recruitment culture shapes squad building, scouting algorithms, and transfer
              market policies.
            </p>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {[
                {
                  id: "youth",
                  title: "Youth Development",
                  desc: "Nurture prodigies with high potential and structured minutes.",
                },
                {
                  id: "academy",
                  title: "Academy-First",
                  desc: "Organic domestic academy talent graduating into the first team.",
                },
                {
                  id: "selling",
                  title: "Selling Club",
                  desc: "Discover undervalued gems, polish their market value, sell at high margins.",
                },
                {
                  id: "superstars",
                  title: "Superstar Club",
                  desc: "Target high-profile global icons to compete at the absolute summit.",
                },
                {
                  id: "sustainable",
                  title: "Financially Sustainable",
                  desc: "Data-driven scouting with prudent contracts and balanced budgets.",
                },
                {
                  id: "balanced",
                  title: "Balanced Approach",
                  desc: "Blend youth academy prospects with proven domestic pros.",
                },
              ].map((phil) => (
                <div
                  key={phil.id}
                  onClick={() => setRecruitmentFocus(phil.id)}
                  className={`cursor-pointer rounded border p-3 transition-all ${
                    recruitmentFocus === phil.id
                      ? "border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/10"
                      : "border-white/10 bg-slate-900/40 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-white">{phil.title}</span>
                    {recruitmentFocus === phil.id && (
                      <Check size={14} className="text-emerald-400" />
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-400">{phil.desc}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center justify-between">
              <Btn variant="ghost" onClick={() => setWizardStep("name")}>
                ← Back
              </Btn>
              <Btn onClick={() => setWizardStep("roster")}>Next: Age & Nationality Policies →</Btn>
            </div>
          </Panel>
        )}

        {/* Wizard Step 3: Roster Policy & Restrictions */}
        {wizardStep === "roster" && (
          <Panel
            eyebrow="Step 3 of 5 · Roster Governance"
            title="Define recruitment boundaries"
            className="w-full"
          >
            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Target Squad Age Profile
                </label>
                <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-6">
                  {["U18", "U21", "U23", "U25", "U27", "none"].map((age) => (
                    <button
                      type="button"
                      key={age}
                      onClick={() => setPreferredAgeBracket(age)}
                      className={`rounded border py-2 text-xs font-semibold transition-colors ${
                        preferredAgeBracket === age
                          ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                          : "border-white/10 bg-slate-900/50 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      {age === "none" ? "All Ages" : age}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Nationality Recruitment Policy
                </label>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {[
                    {
                      id: "preferred",
                      label: "Preferred Domestic",
                      desc: "Prioritizes domestic talent, allows foreign signings",
                    },
                    {
                      id: "exclusive",
                      label: "Exclusive Domestic",
                      desc: "Restricted strictly to domestic & dual-nationals",
                    },
                    { id: "none", label: "Global Scouting", desc: "Zero geographic restrictions" },
                  ].map((nat) => (
                    <div
                      key={nat.id}
                      onClick={() => setNationalityFocus(nat.id)}
                      className={`cursor-pointer rounded border p-2.5 text-xs transition-colors ${
                        nationalityFocus === nat.id
                          ? "border-emerald-500 bg-emerald-500/10 text-emerald-200"
                          : "border-white/10 bg-slate-900/50 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      <p className="font-semibold text-white">{nat.label}</p>
                      <p className="mt-1 text-[11px] text-slate-400">{nat.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Visual Crest Design Style
                </label>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  {[
                    {
                      id: "traditional",
                      label: "Traditional",
                      desc: "Classic shield & sovereign heritage",
                    },
                    {
                      id: "modern",
                      label: "Modern Roundel",
                      desc: "Sleek roundel & athletic icons",
                    },
                    {
                      id: "metallic",
                      label: "Metallic Diamond",
                      desc: "Rhombus badge with gold accents",
                    },
                  ].map((s) => (
                    <button
                      type="button"
                      key={s.id}
                      onClick={() => setPreferredStyle(s.id)}
                      className={`rounded border p-2 text-left text-xs transition-colors ${
                        preferredStyle === s.id
                          ? "border-amber-400 bg-amber-400/10 text-amber-200"
                          : "border-white/10 bg-slate-900/50 text-slate-400"
                      }`}
                    >
                      <span className="block font-semibold text-white">{s.label}</span>
                      <span className="text-[10px] text-slate-400">{s.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between">
              <Btn variant="ghost" onClick={() => setWizardStep("philosophy")}>
                ← Back
              </Btn>
              <Btn
                disabled={clubName.length < 3 || !location.valid}
                onClick={handleGenerateIdentity}
                data-testid="open-club-design-library"
              >
                Browse Ready-Made Crests & Uniforms →
              </Btn>
            </div>
          </Panel>
        )}

        {/* Wizard Step 4: AI Crest & Kit Studio */}
        {wizardStep === "studio" && recommendation && (
          <Panel
            eyebrow="Step 4 of 5 · Club Design Library"
            title="Choose your club crest & uniforms"
            className="w-full"
          >
            {/* Vision Narrative Card */}
            <div className="mb-5 rounded border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-xs">
              <div className="flex items-center gap-2 font-semibold text-emerald-300">
                <Sparkles size={14} />
                <span>Club Identity Brief</span>
              </div>
              <p className="mt-1 text-slate-300 italic">{recommendation.vision_narrative}</p>
            </div>

            <div className="mb-6">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Choose Primary Club Crest · {crestConcepts.length} Designs
              </label>
              <p className="mt-1 text-[11px] text-slate-500">
                Every badge carries the club initials {crestConcepts[0]?.initials || ""}. The first
                page is the featured set.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <input
                  value={crestQuery}
                  onChange={(event) => {
                    setCrestQuery(event.target.value);
                    setCrestPage(0);
                  }}
                  placeholder="Search lion, shield, royal"
                  aria-label="Search crest designs"
                  className="min-w-[12rem] flex-1 rounded border border-white/10 bg-slate-950 px-3 py-1.5 text-xs text-white outline-none placeholder:text-slate-500"
                />
                {recommendation.crest_concepts?.[selectedCrestIdx] && (
                  <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-200">
                    Selected: {recommendation.crest_concepts[selectedCrestIdx].initials} ·{" "}
                    {recommendation.crest_concepts[selectedCrestIdx].style}
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(
                  [
                    ["all", "All finishes"],
                    ["heritage", "Heritage"],
                    ["modern", "Modern"],
                    ["royal", "Royal"],
                  ] as const
                ).map(([filter, label]) => (
                  <button
                    type="button"
                    key={filter}
                    onClick={() => {
                      setCrestFilter(filter);
                      setCrestPage(0);
                    }}
                    aria-pressed={crestFilter === filter}
                    className={`rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors ${
                      crestFilter === filter
                        ? "border-emerald-400 bg-emerald-500/15 text-emerald-300"
                        : "border-white/10 bg-slate-900/50 text-slate-400 hover:border-white/25"
                    }`}
                  >
                    {label}
                  </button>
                ))}
                {(
                  [
                    ["all", "All shapes"],
                    ["shield", "Shield"],
                    ["round", "Roundel"],
                    ["diamond", "Diamond"],
                    ["pennant", "Pennant"],
                  ] as const
                ).map(([shape, label]) => (
                  <button
                    type="button"
                    key={shape}
                    onClick={() => {
                      setCrestShape(shape);
                      setCrestPage(0);
                    }}
                    aria-pressed={crestShape === shape}
                    className={`rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors ${
                      crestShape === shape
                        ? "border-amber-300 bg-amber-400/10 text-amber-200"
                        : "border-white/10 bg-slate-900/50 text-slate-400 hover:border-white/25"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="mt-2.5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {pagedCrests.map((concept) => {
                  const idx = crestConcepts.findIndex(
                    (item: { concept_id: string }) => item.concept_id === concept.concept_id,
                  );
                  return (
                    <button
                      type="button"
                      key={concept.concept_id}
                      onClick={() => setSelectedCrestIdx(idx)}
                      aria-pressed={selectedCrestIdx === idx}
                      data-testid={`club-crest-option-${concept.concept_id}`}
                      className={`rounded border p-3 text-center transition-all ${
                        selectedCrestIdx === idx
                          ? "border-emerald-500 bg-emerald-500/15 ring-2 ring-emerald-500/30"
                          : "border-white/10 bg-slate-900/40 hover:border-white/25"
                      }`}
                    >
                      <div className="mx-auto flex h-24 w-24 items-center justify-center p-1">
                        <img
                          src={concept.data_uri}
                          alt={`${concept.initials} ${concept.style}`}
                          className="h-full w-full object-contain"
                        />
                      </div>
                      <p className="mt-2 text-xs font-semibold uppercase text-white">
                        {concept.initials} · {concept.style}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-400 line-clamp-2">
                        {concept.visual_meaning}
                      </p>
                    </button>
                  );
                })}
              </div>
              {pagedCrests.length === 0 && (
                <p className="mt-3 text-xs text-slate-400">
                  No crests match that search. Clear the filters to see the featured set.
                </p>
              )}
              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                <span>
                  {featuredCrests ? "Featured crests" : "Crest designs"} · {visibleCrests.length}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
                    disabled={safeCrestPage === 0}
                    onClick={() => setCrestPage(safeCrestPage - 1)}
                  >
                    Previous
                  </button>
                  <span>
                    {safeCrestPage + 1} / {crestPageCount}
                  </span>
                  <button
                    type="button"
                    className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
                    disabled={safeCrestPage >= crestPageCount - 1}
                    onClick={() => setCrestPage(safeCrestPage + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>

            <div className="mb-6">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Uniform Collections · {KIT_PRESETS.length} Sets
                  </label>
                  <p className="mt-1 text-[11px] text-slate-500">
                    Every set has home, away, third and goalkeeper shirts.{" "}
                    {kitSet?.home?.front_text || clubName} is printed on the chest.
                  </p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <input
                  value={kitQuery}
                  onChange={(event) => {
                    setKitQuery(event.target.value);
                    setKitPage(0);
                  }}
                  placeholder="Search royal, gold, hoops"
                  aria-label="Search uniform designs"
                  className="min-w-[12rem] flex-1 rounded border border-white/10 bg-slate-950 px-3 py-1.5 text-xs text-white outline-none placeholder:text-slate-500"
                />
                {["all", "stripes", "hoops", "sash", "chevron", "solid", "gradient"].map(
                  (pattern) => (
                    <button
                      type="button"
                      key={pattern}
                      onClick={() => {
                        setKitPattern(pattern);
                        setKitPage(0);
                      }}
                      aria-pressed={kitPattern === pattern}
                      className={`rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${
                        kitPattern === pattern
                          ? "border-emerald-400 bg-emerald-500/15 text-emerald-300"
                          : "border-white/10 bg-slate-900/50 text-slate-400"
                      }`}
                    >
                      {pattern === "all" ? "All patterns" : pattern}
                    </button>
                  ),
                )}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                {pagedKits.map((preset) => {
                  const previewSet = buildKitSet(preset.id, clubName);
                  const selected = selectedKitPresetId === preset.id;
                  return (
                    <button
                      type="button"
                      key={preset.id}
                      onClick={() => {
                        setSelectedKitPresetId(preset.id);
                        setKitSet(previewSet);
                      }}
                      aria-pressed={selected}
                      data-testid={`club-kit-preset-${preset.id}`}
                      className={`rounded border p-2 text-left transition-all ${
                        selected
                          ? "border-emerald-400 bg-emerald-500/10 ring-1 ring-emerald-500/30"
                          : "border-white/10 bg-slate-900/50 hover:border-white/25"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <img
                          src={kitSwatchDataUri(previewSet.home)}
                          alt=""
                          className="h-20 w-16 shrink-0 object-contain"
                        />
                        <div className="min-w-0">
                          <p className="truncate text-[11px] font-bold uppercase text-white">
                            {preset.name}
                          </p>
                          <p className="mt-1 line-clamp-3 text-[10px] leading-relaxed text-slate-400">
                            {preset.description}
                          </p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                <span>
                  {safeKitPage === 0 && kitPattern === "all" && kitQuery.trim() === ""
                    ? "Featured kits"
                    : "Kit designs"}{" "}
                  · {visibleKits.length}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
                    disabled={safeKitPage === 0}
                    onClick={() => setKitPage(safeKitPage - 1)}
                  >
                    Previous
                  </button>
                  <span>
                    {safeKitPage + 1} / {kitPageCount}
                  </span>
                  <button
                    type="button"
                    className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
                    disabled={safeKitPage >= kitPageCount - 1}
                    onClick={() => setKitPage(safeKitPage + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>

            {/* Kit Preview Tabs */}
            {kitSet && (
              <div className="mb-6">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Matchday Uniforms (4 Concept Kit Set)
                  </label>
                  <div className="flex gap-1 text-[11px]">
                    {(["home", "away", "third", "goalkeeper"] as const).map((tab) => (
                      <button
                        type="button"
                        key={tab}
                        onClick={() => setSelectedKitTab(tab)}
                        className={`rounded px-2.5 py-1 font-semibold uppercase transition-colors ${
                          selectedKitTab === tab
                            ? "bg-emerald-500 text-white"
                            : "bg-slate-800 text-slate-400 hover:text-white"
                        }`}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>
                </div>

                {kitSet[selectedKitTab] && (
                  <div className="mt-2.5 grid gap-4 rounded border border-white/10 bg-slate-900/60 p-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(16rem,0.8fr)]">
                    <JerseyTurntable
                      kit={kitSet[selectedKitTab]}
                      crestDataUri={recommendation.crest_concepts?.[selectedCrestIdx]?.data_uri}
                      chestText={kitSet[selectedKitTab].front_text}
                    />

                    <div className="min-w-0 flex-1 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold uppercase text-white">{selectedKitTab} Kit</span>
                        <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300 uppercase">
                          {kitSet[selectedKitTab].pattern_type} pattern
                        </span>
                        <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300 uppercase">
                          {kitSet[selectedKitTab].collar_style} collar
                        </span>
                      </div>
                      <p className="mt-3 text-sm font-black uppercase tracking-wide text-white">
                        {kitSet[selectedKitTab].front_text}
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
                        <span>Colors:</span>
                        <span
                          className="h-3.5 w-3.5 rounded-full border border-white/30"
                          style={{ backgroundColor: kitSet[selectedKitTab].primary_color }}
                          title="Primary"
                        />
                        <span
                          className="h-3.5 w-3.5 rounded-full border border-white/30"
                          style={{ backgroundColor: kitSet[selectedKitTab].secondary_color }}
                          title="Secondary"
                        />
                        <span
                          className="h-3.5 w-3.5 rounded-full border border-white/30"
                          style={{ backgroundColor: kitSet[selectedKitTab].accent_color }}
                          title="Trim"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="mt-6 flex items-center justify-between">
              <Btn variant="ghost" onClick={() => setWizardStep("roster")}>
                ← Back
              </Btn>
              <Btn onClick={() => setWizardStep("review")} data-testid="proceed-to-charter-review">
                Review Founding Charter →
              </Btn>
            </div>
          </Panel>
        )}

        {/* Wizard Step 5: Final Review & Activation */}
        {wizardStep === "review" && (
          <Panel
            eyebrow="Step 5 of 5 · Official Charter"
            title={`Founding Charter: ${clubName}`}
            className="w-full"
          >
            <div className="mb-5 space-y-3">
              <div className="flex items-center gap-4 rounded border border-white/10 bg-slate-900/60 p-4">
                {recommendation?.crest_concepts?.[selectedCrestIdx]?.data_uri && (
                  <img
                    src={recommendation.crest_concepts[selectedCrestIdx].data_uri}
                    alt="Crest"
                    className="h-16 w-16 object-contain"
                  />
                )}
                {kitSet?.home && (
                  <img
                    src={kitSwatchDataUri(kitSet.home)}
                    alt="Home kit"
                    className="h-20 w-16 object-contain"
                  />
                )}
                <div>
                  <h3 className="text-lg font-bold text-white">{clubName}</h3>
                  <p className="text-xs text-slate-400">
                    {recommendation?.vision_narrative || "Official GTEX Franchise"}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded border border-white/10 bg-slate-950/50 p-3">
                  <span className="text-[10px] uppercase text-slate-400">Philosophy</span>
                  <p className="mt-0.5 font-semibold text-emerald-300 capitalize">
                    {(recommendation?.primary_philosophy || recruitmentFocus).replace(/_/g, " ")}
                  </p>
                </div>
                <div className="rounded border border-white/10 bg-slate-950/50 p-3">
                  <span className="text-[10px] uppercase text-slate-400">Transfer Strategy</span>
                  <p className="mt-0.5 font-semibold text-cyan-300 capitalize">
                    {(recommendation?.transfer_strategy || "buy_young_develop_sell").replace(
                      /_/g,
                      " ",
                    )}
                  </p>
                </div>
              </div>

              {another ? (
                <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-slate-300">
                  <span className="font-semibold text-emerald-400">Sister club:</span>
                  <p className="mt-0.5 text-slate-400">
                    This club starts in Foundation and uses the crest and kit chosen here. Entering
                    a competition is free.
                  </p>
                </div>
              ) : (
                <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-slate-300">
                  <span className="font-semibold text-emerald-400">Owner Activation Package:</span>
                  <p className="mt-0.5 text-slate-400">
                    The first 500 eligible club owners receive <b>2,500 GTX</b> ring-fenced for
                    player signings, plus <b>1,000 FAN</b> for gifting.
                  </p>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Btn
                className="w-full"
                disabled={clubName.length < 3 || !location.valid || busy}
                onClick={create}
                data-testid="first-club-create-button"
              >
                {busy ? "Sealing Founding Charter…" : "Seal Founding Charter & Acquire Club 🏆"}
              </Btn>
              <Btn variant="ghost" onClick={() => setWizardStep("studio")}>
                ← Back to Design Library
              </Btn>
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}

export default function Onboarding() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const creating = searchParams.get("create") === "1";
  const { data, refetch, isLoading } = useQuery({
    queryKey: ["onboarding"],
    queryFn: async () => (await api.get("/owner/onboarding")).data,
    enabled: !!user,
  });
  const club = (data?.clubs || []).find((c: any) => !["active"].includes(c.stage)) || null;

  if (loading || (user && isLoading)) return <Loading label="Preparing your club" />;
  if (!user) return <Navigate to="/login" replace />;
  if (creating || (!club && !(data?.clubs || []).length)) {
    return (
      <CreateFirstClub
        another={Boolean((data?.clubs || []).length)}
        onDone={() => {
          refetch();
          navigate("/onboarding", { replace: true });
        }}
        onCancel={() => navigate(creating ? "/app/clubs" : "/app")}
      />
    );
  }
  if (!club) return <Navigate to="/app" replace />;

  let index = 0;
  if (club.stage === "squad") {
    index = 1;
  } else if (club.stage === "manager") {
    index = 2;
  } else if (club.stage === "competition" || club.stage === "active") {
    index = 3;
  }
  const next = () => refetch();
  const openClub = async () => {
    try {
      await api.post(`/owner/clubs/${club.club_id}/finish-onboarding`);
      await qc.invalidateQueries({ queryKey: ["cc"] });
      await qc.invalidateQueries({ queryKey: ["onboarding"] });
      navigate("/app");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div
      className="gx-pitch-grid min-h-screen bg-[#070B11] px-4 py-10 sm:px-10"
      data-testid="onboarding-page"
    >
      <div className="mx-auto max-w-[1200px]">
        <p className="gx-eyebrow mb-2">First-club activation</p>
        <h1 className="gx-h2 mb-8">{club.club_name}: from paperwork to matchday</h1>
        <Stepper index={index} />
        {index === 0 && <IdentityStep club={club} onboarding={data} onDone={next} />}
        {index === 1 && <SquadStep clubId={club.club_id} onDone={next} />}
        {index === 2 && <ManagerStep clubId={club.club_id} onDone={next} />}
        {index === 3 && <AcademyStep clubId={club.club_id} onDone={openClub} />}
        <p className="mt-6 text-xs text-slate-600">
          Club treasury: {fmt(club.cash)} GTX · Squad {club.squad_size}
        </p>
      </div>
    </div>
  );
}

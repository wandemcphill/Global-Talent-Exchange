import React, { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  AlertTriangle,
  ArrowRight,
  Check,
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

function useOnboardingMoney(clubId?: string) {
  const query = useQuery({
    queryKey: ["club-squad-funding-finance"],
    queryFn: async () => (await api.get("/owner/finance")).data,
    enabled: !!clubId,
  });
  const row = (query.data?.clubs || []).find((item: any) => item.club_id === clubId);
  const numberOrNull = (value: unknown) => (value == null || value === "" ? null : Number(value));
  return {
    ready: Boolean(row),
    loading: query.isLoading,
    wallet: numberOrNull(query.data?.wallet?.gtex_total),
    fan: numberOrNull(query.data?.wallet?.fan_total),
    cash: numberOrNull(row?.cash_gtex),
    deposited: numberOrNull(row?.deposited),
    grant: numberOrNull(row?.squad_grant),
    earned: numberOrNull(row?.earned),
    clubFan: numberOrNull(row?.gifts_fan_coin),
    nairaPerFan: Number(query.data?.naira_per_fan || query.data?.treasury_rates?.fan_coin_deposit_rate || 0),
    fanPerGtex: Number(query.data?.fan_coin_per_gtex || 0),
    refetch: query.refetch,
  };
}

function moneyText(value: number | null) {
  return value == null ? "…" : `${fmt(value)} GTX`;
}

function fanText(value: number | null) {
  return value == null ? "…" : `${fmt(value)} FAN`;
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
        the first {fmt(launchGrantLimit)} eligible club owners, plus 1,000 FAN toward staff
        contracts and gifting. Named staff are paid in Fan Coin, and that grant may not cover
        every role. You can convert deposited or earned GTEX, or buy more Fan Coin. The GTX grant
        stays ring-fenced for eligible player signings.
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

function SquadFundingPanel({
  clubId,
  club,
  onClubFunded,
  purpose = "squad",
  shortfall,
  registeredCount,
}: any) {
  const queryClient = useQueryClient();
  const [coinsToMove, setCoinsToMove] = useState("");
  const [nairaAmount, setNairaAmount] = useState("");
  const [provider, setProvider] = useState<"korapay" | "paystack">("korapay");
  const [providerTouched, setProviderTouched] = useState(false);
  const [buyCurrency, setBuyCurrency] = useState<"gtex" | "fan">(purpose === "wages" ? "fan" : "gtex");
  const [convertAmount, setConvertAmount] = useState("");
  const [convertFrom, setConvertFrom] = useState<"club" | "wallet">("club");
  const money = useOnboardingMoney(clubId);
  const financeQuery = useQuery({
    queryKey: ["club-squad-funding-finance"],
    queryFn: async () => (await api.get("/owner/finance")).data,
    enabled: !!clubId,
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
  const filled = (primary: number | null, fallback: unknown) =>
    primary ?? (fallback == null || fallback === "" ? null : Number(fallback));
  const walletCoins = money.wallet ?? 0;
  const clubCoins = filled(money.cash, club?.economy?.cash_gtex);
  const depositedCoins = filled(money.deposited, club?.economy?.deposited);
  const squadGrant = filled(money.grant, club?.economy?.squad_grant);
  const earnedCoins = filled(money.earned, club?.economy?.earned);
  const registeredPlayers = Number(
    registeredCount ?? club?.formation?.total_registered_players ?? club?.squad?.length ?? 0,
  );
  const playersRemaining = Math.max(0, 22 - registeredPlayers);
  const knownTreasury = clubCoins == null ? null : clubCoins + (money.wallet ?? 0);
  const squadGap =
    knownTreasury == null ? null : Math.max(0, playersRemaining * 200 - knownTreasury);
  const estimatedCoinsNeeded =
    purpose === "wages"
      ? shortfall == null
        ? null
        : Math.max(0, Number(shortfall) || 0)
      : squadGap;
  const wageMode = purpose === "wages";
  const fanRateForSuggestion = Number(
    money.nairaPerFan || rates.fan_coin_deposit_rate || 0,
  );
  const suggestedNaira = wageMode
    ? fanRateForSuggestion > 0 && estimatedCoinsNeeded != null && estimatedCoinsNeeded > 0
      ? Math.max(100, Math.ceil(estimatedCoinsNeeded * fanRateForSuggestion))
      : ""
    : rate > 0 && estimatedCoinsNeeded != null && estimatedCoinsNeeded > 0
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
  const fanRate = Number(money.nairaPerFan || rates.fan_coin_deposit_rate || 0);
  const fanQuote = fanRate > 0 ? amountToPay / fanRate : 0;
  const fanPerGtex = Number(money.fanPerGtex || finance?.fan_coin_per_gtex || 15);
  const spendableClubGtx =
    depositedCoins == null || earnedCoins == null ? null : Math.max(0, depositedCoins + earnedCoins);
  const platformReady = Boolean(finance?.payment_providers?.[provider]);
  const buyingFan = buyCurrency === "fan";

  const buyFromPlatform = async () => {
    const amount = Math.trunc(amountToPay);
    if (!Number.isFinite(amount) || amount < 100) {
      toast.error(buyingFan ? "Enter at least ₦100 to buy Fan Coin." : "Enter at least ₦100 to buy GTEX Coin.");
      return;
    }
    if (buyingFan && fanRate <= 0) {
      toast.error("Fan Coin does not have a naira rate yet.");
      return;
    }
    try {
      const { data } = await api.post("/owner/deposits/init", {
        amount_ngn: amount,
        provider,
        currency: buyCurrency,
        callback_url:
          window.location.origin +
          publicUrl(`/payment/callback?return_to=%2Fonboarding&provider=${provider}`),
      });
      window.location.href = data.authorization_url;
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  const convertToFan = async () => {
    const amount = Number(convertAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      toast.error("Enter how much GTEX Coin to convert.");
      return;
    }
    try {
      const { data } = await api.post("/owner/fan-coin/convert", {
        amount,
        club_id: convertFrom === "club" ? clubId : undefined,
      });
      toast.success(`Converted ${fmt(amount)} GTX into ${fmt(data?.fan_coin)} FAN.`);
      setConvertAmount("");
      await queryClient.invalidateQueries({ queryKey: ["club-squad-funding-finance"] });
      await queryClient.invalidateQueries({ queryKey: ["finance"] });
      await onClubFunded?.();
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
            {wageMode ? "Staff contracts" : "Fund the squad, then keep signing"}
          </p>
          <h3 className="gx-display mt-1 text-xl font-bold uppercase text-white">
            {wageMode ? "Top up to pay salaries" : "Squad funding and top-up"}
          </h3>
          <p className="mt-2 max-w-3xl text-xs leading-relaxed text-slate-300">
            {wageMode
              ? `Named staff are paid in Fan Coin. The 1,000 FAN launch grant is a start and may not cover every role. The contracts you have selected still need ${fanText(estimatedCoinsNeeded)}. Convert deposited or earned GTEX, or buy Fan Coin. Default staff stay free, and the squad grant is not spent on salaries.`
              : estimatedCoinsNeeded === 0
                ? `The treasury already covers a 22-player squad at the planning rate of 200 GTX each. You do not need to buy more coins to reach that minimum. The welcome grant, ${moneyText(squadGrant)}, stays reserved for active players at GSI 74 and under. Legends, regens, and GSI 75+ spend deposited coins, currently ${moneyText(depositedCoins)}.`
                : `22 registered players, including a goalkeeper, makes the club match-eligible. You can sign more than 22. At 200 GTX per player still needed, the treasury and wallet leave a gap of ${moneyText(estimatedCoinsNeeded)}. The welcome grant buys active players at GSI 74 and under. Legends, regens, and GSI 75+ need deposited coins.`}
          </p>
          <p className="mt-1 max-w-3xl text-[11px] text-slate-400">
            The grant is for the first 500 eligible club owners. Some premium, regen, and legend
            player signings require deposited GTX under GTEX acquisition rules.
          </p>
        </div>
        <div className="rounded-lg border border-emerald-500/25 bg-black/25 px-4 py-3 text-right">
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Club treasury</p>
          <p className="gx-mono text-xl font-bold text-emerald-300">{moneyText(clubCoins)}</p>
          <p className="mt-1 text-[10px] text-slate-400">Deposited: {moneyText(depositedCoins)}</p>
          <p className="text-[10px] text-slate-400">Squad grant remaining: {moneyText(squadGrant)}</p>
          <p className="text-[10px] text-slate-400">Earned: {moneyText(earnedCoins)}</p>
          <p className="mt-2 text-[10px] uppercase tracking-widest text-slate-400">Fan Coin</p>
          <p className="text-[10px] text-slate-400">Wallet: {fanText(money.fan)}</p>
          <p className="text-[10px] text-slate-400">Club: {fanText(money.clubFan)}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-white/10 bg-black/20 p-4">
          <p className="gx-label text-slate-300">Option 1 · Buy from GTEX</p>
          <p className="mt-1 text-xs text-slate-400">
            Pay through the platform. Choose GTEX Coin for the squad treasury, or Fan Coin for staff.
            A verified payment credits your personal wallet.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(
              [
                ["gtex", "GTEX Coin"],
                ["fan", "Fan Coin"],
              ] as const
            ).map(([item, label]) => (
              <button
                key={item}
                type="button"
                onClick={() => setBuyCurrency(item)}
                className={
                  "gx-btn flex-1 py-1.5 text-xs " +
                  (buyCurrency === item ? "gx-btn-primary" : "gx-btn-secondary")
                }
                data-testid={`squad-buy-currency-${item}`}
              >
                {label}
              </button>
            ))}
          </div>
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
          <p className="mt-2 text-xs text-slate-400" data-testid="squad-platform-quote">
            This payment buys <b className="text-white">{fmt(previewCoins, 2)} GTX</b> or{" "}
            <b className="text-white">{fanRate > 0 ? `${fmt(fanQuote, 2)} FAN` : "Fan Coin once a naira rate is set"}</b>.
            You selected {buyingFan ? "Fan Coin" : "GTEX Coin"}.
          </p>
          <Btn
            className="mt-3 w-full"
            disabled={(buyingFan ? fanRate <= 0 : !rate) || !platformReady || financeQuery.isLoading}
            onClick={buyFromPlatform}
            data-testid="squad-platform-buy"
          >
            {buyingFan ? "Buy Fan Coin" : "Buy GTX from platform"}
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
            <b className="gx-mono text-white">{moneyText(money.wallet)}</b>
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
            disabled={!coinsToMove || Number(coinsToMove) <= 0}
            onClick={moveToClub}
            data-testid="squad-wallet-inject"
          >
            Add coins to club treasury
          </Btn>
          {squadGrant != null && squadGrant > 0 && (
            <p className="mt-2 text-[11px] text-slate-500">
              The grant is already in your club treasury; it cannot be withdrawn, converted, or used
              for facilities or staff.
            </p>
          )}
        </div>
      </div>
      <div className="mt-3 rounded-lg border border-amber-500/25 bg-black/20 p-4" data-testid="fan-coin-convert">
        <p className="gx-label text-amber-200">Convert GTEX Coin to Fan Coin</p>
        <p className="mt-1 text-xs text-slate-400">
          1 GTX becomes {fmt(fanPerGtex)} FAN. Club conversion spends deposited and earned coins
          only, currently {moneyText(spendableClubGtx)}. The squad grant stays for player signings.
          Wallet conversion spends personal GTEX. Fan Coin pays staff and is not withdrawable.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(
            [
              ["club", "Club treasury"],
              ["wallet", "Personal wallet"],
            ] as const
          ).map(([item, label]) => (
            <button
              key={item}
              type="button"
              onClick={() => setConvertFrom(item)}
              className={
                "gx-btn flex-1 py-1.5 text-xs " +
                (convertFrom === item ? "gx-btn-primary" : "gx-btn-secondary")
              }
              data-testid={`fan-convert-source-${item}`}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="gx-label mt-3 block">GTX to convert</label>
        <input
          className="gx-input mt-1"
          type="number"
          min={1}
          step="0.01"
          value={convertAmount}
          onChange={(event) => setConvertAmount(event.target.value)}
          placeholder="Enter GTX"
          data-testid="fan-convert-amount"
        />
        <p className="mt-2 text-xs text-slate-400">
          You receive <b className="text-white">{fmt((Number(convertAmount) || 0) * fanPerGtex)} FAN</b>
          {convertFrom === "club" ? " in the club" : " in your wallet"}.
        </p>
        <Btn
          className="mt-3 w-full"
          disabled={!convertAmount || Number(convertAmount) <= 0}
          onClick={convertToFan}
          data-testid="fan-convert-button"
        >
          Convert to Fan Coin
        </Btn>
      </div>
      <div className="mt-4">
        <ClubCoinTraderFundingPanel
          initialAmount={estimatedCoinsNeeded != null && estimatedCoinsNeeded > 0 ? String(estimatedCoinsNeeded) : ""}
        />
      </div>
    </div>
  );
}

function SquadStep({ clubId, knownCash, onDone }: any) {
  const { data: club, refetch } = useClub(clubId);
  const money = useOnboardingMoney(clubId);
  const rosterQuery = useQuery({
    queryKey: ["club-roster", clubId],
    queryFn: async () => (await api.get(`/owner/clubs/${clubId}/roster`)).data,
    enabled: !!clubId,
  });
  const roster = rosterQuery.data;
  const [unsigningId, setUnsigningId] = useState<string | null>(null);
  const [autopicking, setAutopicking] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [tactic, setTactic] = useState("tiki_taka");
  const [formation, setFormation] = useState("4-3-3");
  const [budgetCap, setBudgetCap] = useState("");
  const [targetSquadSize, setTargetSquadSize] = useState("22");
  const [queue, setQueue] = useState<any[]>([]);
  const [checkingOut, setCheckingOut] = useState(false);

  const refreshSquad = () => {
    refetch();
    rosterQuery.refetch();
    money.refetch();
  };
  const allRegisteredSquad = roster?.squad ?? club?.squad ?? [];
  const formationStatus = roster?.formation ?? club?.formation;
  const registeredCount = Number(
    formationStatus?.total_registered_players ?? allRegisteredSquad.length,
  );
  const remainingToForm = Number(
    formationStatus?.remaining_to_form ?? Math.max(0, 22 - registeredCount),
  );
  const hasGk = Boolean(
    formationStatus?.has_goalkeeper ??
    allRegisteredSquad.some((p: any) => {
      const position = String(p.position || "").toLowerCase();
      return position.includes("goal") || position === "gk" || position.startsWith("gk/") || position.startsWith("gk ");
    }),
  );
  const isMatchEligible = Boolean(formationStatus?.is_formed ?? (registeredCount >= 22 && hasGk));
  const clubCash =
    money.cash ??
    (knownCash == null || knownCash === "" ? null : Number(knownCash));
  const squadCeiling = Number(roster?.maximum_squad ?? 80);

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
      const destination = data?.refund_destination === "wallet" ? "your wallet" : "club treasury";
      toast.success(`Removed ${p.name}. Refunded ${fmt(refund)} GTX to ${destination}.`);
      refreshSquad();
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
      refreshSquad();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAutopicking(false);
    }
  };

  const handleContinue = async () => {
    setContinuing(true);
    try {
      await api.post(`/owner/clubs/${clubId}/confirm-squad`);
      onDone();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setContinuing(false);
    }
  };

  const grantRemaining = money.grant;
  const depositedAvailable = money.deposited;
  const queueValue = (lane: "welcome" | "paid") =>
    queue
      .filter((p) => marketLane(p) === lane)
      .reduce((sum, p) => sum + Number(p.quote?.price || 0), 0);
  const welcomeQueued = queueValue("welcome");
  const paidQueued = queueValue("paid");
  const welcomeOver = grantRemaining != null && welcomeQueued > grantRemaining + 0.001;
  const paidOver = depositedAvailable != null && paidQueued > depositedAvailable + 0.001;
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
      refreshSquad();
    } catch (e) {
      toast.error(errMsg(e));
      refreshSquad();
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
          <p className="text-[10px] uppercase tracking-widest text-slate-500">Club treasury</p>
          {clubCash == null ? (
            <span className="gx-mono text-sm text-slate-400" data-testid="onboarding-cash">
              …
            </span>
          ) : (
            <Coin amount={clubCash} testid="onboarding-cash" />
          )}
          <p className="text-[10px] text-slate-500">
            Deposited {moneyText(money.deposited)} · Grant {moneyText(money.grant)} · Earned{" "}
            {moneyText(money.earned)}
          </p>
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
            <p className="gx-eyebrow text-emerald-400">Recruitment settings</p>
            <p className="text-xs text-slate-300">
              These four controls are sent with Auto-Pick. Style sets the formation it prefers.
              A blank budget spends the club treasury. The target is how many players Auto-Pick
              tries to reach, and 22 is the match-eligibility minimum, not a cap. Staff are hired
              on the next page.
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
            Recruitment budget cap (GTX)
            <input
              type="number"
              min={0}
              value={budgetCap}
              placeholder="Whole treasury"
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
              max={squadCeiling}
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
            {formationStatus?.progress_label ||
              `${registeredCount} registered · 22 to play`}
          </Chip>
          <Chip tone={hasGk ? "emerald" : "red"}>
            {hasGk ? "✓ Goalkeeper registered" : "⚠ Needs a goalkeeper"}
          </Chip>
          <span className="text-xs text-slate-400">
            22 players, including a goalkeeper, makes the club match-eligible. Signing more than 22
            is allowed.
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Btn
            variant={isMatchEligible ? "ghost" : "primary"}
            disabled={autopicking}
            onClick={handleAutopick}
            className="flex items-center gap-1.5"
            data-testid="onboarding-autopick-button"
            title="Automatically sign affordable players to complete your squad within available funds"
          >
            <Sparkles size={14} className={autopicking ? "animate-spin" : "text-amber-300"} />
            {autopicking ? "Auto-picking…" : "⚡ Auto-Pick within Budget"}
          </Btn>
        </div>
      </div>

      {/* Low cash warning if stuck */}
      {!isMatchEligible && clubCash != null && clubCash < 800 && registeredCount > 0 && (
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
            {signedWelcome.length === 0 && welcomeQueued === 0
              ? "No grant signings yet"
              : `Signed ${fmt(signedValue(signedWelcome))} GTX · In basket ${fmt(welcomeQueued)} GTX`}
          </p>
          <p className="text-xs text-slate-400">
            Grant remaining {moneyText(grantRemaining)}. This pays for active players at GSI 74 and
            under only.
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
            {signedPaid.length === 0 && paidQueued === 0
              ? "No deposited signings yet"
              : `Signed ${fmt(signedValue(signedPaid))} GTX · In basket ${fmt(paidQueued)} GTX`}
          </p>
          <p className="text-xs text-slate-400">
            Deposited coins available {moneyText(depositedAvailable)}. Legends, regens, and GSI 75+
            are paid from this, not from the grant.
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
            {`No players on the list yet (${registeredCount} registered, 22 needed to play${hasGk ? "" : ", goalkeeper still needed"}). Players you acquire show up here, and you can remove any of them. You can sign more than 22.`}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {allRegisteredSquad.map((p: any) => {
              const position = String(p.position || "").toLowerCase();
              const isGk =
                position.includes("goal") ||
                position === "gk" ||
                position.startsWith("gk/") ||
                position.startsWith("gk ");
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

      <SquadFundingPanel
        clubId={clubId}
        club={club}
        registeredCount={registeredCount}
        onClubFunded={refreshSquad}
      />

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
          onSigned={() => refreshSquad()}
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
        <Btn
          disabled={!isMatchEligible || continuing}
          onClick={handleContinue}
          data-testid="onboarding-squad-continue"
        >
          {continuing ? "Saving the squad…" : "Squad looks right — hire staff"}
        </Btn>
      </div>
    </Panel>
  );
}

function seasonSalaryFan(raw: number) {
  const amount = Math.max(0, Math.round(Number(raw) || 0));
  if (amount <= 0) return 0;
  return Math.max(1, Math.floor((amount * 35) / 100));
}

export function contractCharge(seasonSalary: number | null, years: number) {
  const span = Math.max(1, Math.min(5, Math.floor(Number(years) || 1)));
  const season = Math.max(0, Math.round(Number(seasonSalary) || 0));
  return { years: span, total: season * span };
}

export function staffDevelopment(person: any, role: string) {
  const rating = Number(person?.rating);
  const derived =
    Number.isFinite(rating) && rating > 0 ? Math.max(8, Math.min(20, Math.round(rating / 5))) : 10;
  const filed = (key: string) => {
    const value = Number(person?.[key]);
    return Number.isFinite(value) && value > 0 ? Math.max(1, Math.min(20, Math.round(value))) : null;
  };
  if (role === "head_of_youth_development") {
    const skill = filed("youth_development") ?? derived;
    return {
      skill,
      label: "Youth development",
      intakeBonus: Math.floor(skill / 4),
      potentialBonus: Math.floor(skill / 3),
    };
  }
  if (role === "general_manager") {
    return {
      skill: filed("negotiation") ?? derived,
      label: "Negotiation",
      commercial: filed("commercial_acumen") ?? derived,
    };
  }
  const skill = filed("tactical_flexibility") ?? filed("tactical_quality") ?? derived;
  return { skill, label: "Tactical flexibility" };
}

function namedAppointment(person: any) {
  if (!person || person.use_default || person.is_default || person.is_vacant) return null;
  const name = String(person.name || person.display_name || "").trim();
  if (!name || name.toLowerCase() === "default") return null;
  return { ...person, name };
}

function appointedFor(club: any, role: string) {
  return (
    namedAppointment(club?.executive_staff?.[role]) ||
    namedAppointment(club?.staff?.[role]) ||
    namedAppointment(club?.onboarding_staff?.[role])
  );
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

const PHILOSOPHY_CUES: Record<string, string[]> = {
  youth_development: ["youth", "develop", "academy", "technical"],
  academy_first: ["youth", "academy", "develop"],
  selling_club: ["pragmatic", "develop", "balanced"],
  superstar: ["attacking", "elite", "star", "physical"],
  big_spending: ["attacking", "elite", "star"],
  sustainable: ["pragmatic", "balanced", "control"],
  balanced: ["balanced", "control"],
};

function staffFitsPhilosophy(philosophy: string | undefined, blob: string) {
  const cues = PHILOSOPHY_CUES[(philosophy || "").toLowerCase()] || [];
  const hay = blob.toLowerCase();
  return cues.some((cue) => hay.includes(cue));
}

function StaffRolePicker({ clubId, role, chosen, onChoose, philosophy }: any) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<"rating" | "recommended">("recommended");
  const [years, setYears] = useState(chosen?.contract_years || 1);
  const chooseYears = (next: number) => {
    const span = Math.max(1, Math.min(5, Math.floor(next) || 1));
    setYears(span);
    if (chosen && !chosen.use_default) {
      const season = Number(chosen.season_salary ?? 0);
      const priced = contractCharge(season, span);
      onChoose({
        ...chosen,
        contract_years: priced.years,
        salary: priced.total,
        season_salary: season,
      });
    }
  };
  useEffect(() => {
    const handle = window.setTimeout(() => setQuery(search.trim()), 280);
    return () => window.clearTimeout(handle);
  }, [search]);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["onboarding-staff", clubId, role.key, query, sort, philosophy],
    queryFn: async () => {
      const people: any[] = [];
      if (role.key === "first_team_manager") {
        try {
          const { data: catalog } = await api.get("/managers/catalog", {
            params: { search: query || undefined, limit: 24, sort: "rating" },
          });
          for (const manager of catalog.items || []) {
            const mentality = String(manager.mentality || "").replace(/_/g, " ");
            const blurb = manager.philosophy_summary || "";
            people.push({
              key: `manager:${manager.manager_id}`,
              name: manager.display_name,
              detail: `${manager.rarity || "coach"} · ${mentality}`,
              blurb,
              rating: Number(manager.manager_impact || 0),
              fit:
                manager.philosophy_fit ||
                staffFitsPhilosophy(philosophy, `${mentality} ${blurb} ${(manager.traits || []).join(" ")}`),
              salary: seasonSalaryFan(
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
              limit: 24,
              employment_status: "all",
              sort,
              philosophy: philosophy || undefined,
            },
          },
        );
        for (const candidate of market.candidates || []) {
          fromMarket += 1;
          const detail = `${candidate.role_label || role.label} · ${candidate.style || candidate.nation || "Staff"}`;
          people.push({
            key: `profile:${candidate.profile_id}`,
            name: candidate.name,
            detail,
            blurb: candidate.philosophy_fit || candidate.philosophy_summary || candidate.nation || "",
            rating: Number(candidate.rating || 0),
            fit: Boolean(
              candidate.philosophy_fit ||
                staffFitsPhilosophy(
                  philosophy,
                  `${detail} ${candidate.mentality || ""} ${candidate.philosophy_summary || ""} ${candidate.style || ""}`,
                ),
            ),
            salary:
              candidate.expected_salary_fan_coin || candidate.expected_salary_gtex
                ? seasonSalaryFan(
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
              rating: Number(candidate.rating || 0),
              fit: staffFitsPhilosophy(
                philosophy,
                `${candidate.specialty || ""} ${candidate.style || ""} ${candidate.bio || ""}`,
              ),
              salary:
                candidate.salary_gtx || candidate.salary
                  ? seasonSalaryFan(candidate.salary_fan_coin || candidate.salary_gtx || candidate.salary)
                  : null,
              profile_id: candidate.id || candidate.staff_id,
            });
          }
        } catch {
          /* Default caretaker remains available. */
        }
      }
      people.sort((left: any, right: any) => {
        if (sort === "recommended" && Boolean(left.fit) !== Boolean(right.fit)) {
          return left.fit ? -1 : 1;
        }
        return (right.rating || 0) - (left.rating || 0);
      });
      const seen = new Set<string>();
      const unique = people.filter((person) => {
        const name = String(person.name || "").trim().toLowerCase();
        if (!name || seen.has(name)) return false;
        seen.add(name);
        return true;
      });
      return unique.slice(0, 12);
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
          <p className="mt-1 text-[11px] text-slate-500">
            You do not need to know a name. Highest rated people are listed first
            {philosophy ? `, and recommended ones fit ${String(philosophy).replace(/_/g, " ")}` : ""}.
            Choose 1 to 5 years. The season salary is multiplied by those years and taken once, when
            you agree the contract.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {chosen ? (
            <Chip tone="emerald">
              {chosen.use_default
                ? "Default"
                : `${chosen.name} · ${chosen.contract_years || years}y`}
            </Chip>
          ) : (
            <Chip>Not chosen</Chip>
          )}
          <label className="flex items-center gap-2 text-[11px] text-slate-400">
            Years
            <select
              className="gx-input"
              value={years}
              onChange={(event) => chooseYears(Number(event.target.value))}
              data-testid={`staff-years-${role.key}`}
            >
              {[1, 2, 3, 4, 5].map((span) => (
                <option key={span} value={span}>
                  {span} {span === 1 ? "year" : "years"}
                </option>
              ))}
            </select>
          </label>
        </div>
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
        <select
          className="gx-input max-w-[180px]"
          value={sort}
          onChange={(event) => setSort(event.target.value as "rating" | "recommended")}
          data-testid={`staff-sort-${role.key}`}
        >
          <option value="recommended">Recommended</option>
          <option value="rating">Rating</option>
        </select>
      </form>
      <div className="mt-3 space-y-2">
        {isLoading ? <p className="text-xs text-slate-500">Searching the staff market…</p> : null}
        {(data || []).map((person: any) => (
          <div
            key={person.key}
            className="flex items-start justify-between gap-3 rounded border border-white/10 px-3 py-2"
          >
            <div>
              <p className="text-sm font-semibold text-white">
                {person.rating ? <span className="mr-2 font-black text-amber-200">{person.rating}</span> : null}
                {person.name}
              </p>
              <p className="text-[11px] text-slate-400">{person.detail}</p>
              {person.fit ? (
                <p className="text-[11px] font-semibold text-cyan-300">
                  Recommended · fits {String(philosophy || "this club").replace(/_/g, " ")}
                </p>
              ) : null}
              <p className="text-[11px] text-emerald-300">
                {person.salary == null
                  ? "Wage not filed"
                  : `${years} ${years === 1 ? "year" : "years"} · ${fmt(contractCharge(person.salary, years).total)} FAN, paid once`}
              </p>
            </div>
            <Btn
              variant="secondary"
              onClick={() => {
                const priced = contractCharge(person.salary, years);
                onChoose({
                  ...person,
                  use_default: false,
                  role: role.key,
                  season_salary: person.salary,
                  contract_years: priced.years,
                  salary: priced.total,
                });
              }}
              data-testid={`choose-staff-${person.manager_id || person.profile_id}`}
            >
              Select
            </Btn>
          </div>
        ))}
        {!isLoading && isError ? (
          <p className="text-xs text-rose-300">The staff list did not load. Try the search again.</p>
        ) : null}
        {!isLoading && !isError && (data || []).length === 0 ? (
          <p className="text-xs text-slate-500">
            {query
              ? "No staff match that search. Clear it to see the highest rated people, or use the default."
              : "No staff are filed for this role yet. Use the default."}
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
  const { data: dna } = useQuery({
    queryKey: ["club-dna", clubId],
    queryFn: async () => (await api.get(`/clubs/${clubId}/dna`)).data,
    enabled: !!clubId,
  });
  const money = useOnboardingMoney(clubId);
  const [choices, setChoices] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState(false);
  const salaryDue = STAFF_ROLES.reduce(
    (sum, role) => sum + Number(choices[role.key]?.salary || 0),
    0,
  );
  const fanAvailable =
    money.fan == null && money.clubFan == null
      ? null
      : (money.fan ?? 0) + (money.clubFan ?? 0);
  const shortfall = fanAvailable == null ? null : Math.max(0, salaryDue - fanAvailable);
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
          contract_years: choice.use_default ? 1 : choice.contract_years || 1,
        });
      }
      toast.success("Staff contracts are in place.");
      await refetch();
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
        are not bought. Choose 1 to 5 years for each named person. The season salary is multiplied
        by those years and taken once, in Fan Coin, when you agree. The 1,000 FAN launch grant is a
        start and may not cover every role. Convert deposited or earned GTEX, or buy Fan Coin,
        below. If the salary is more than you want to pay right now, use the default for that role
        and hire a named person later.
      </p>
      <div className="mb-4 grid gap-4">
        {STAFF_ROLES.map((role) => (
          <StaffRolePicker
            key={role.key}
            clubId={clubId}
            role={role}
            chosen={choices[role.key]}
            philosophy={dna?.primary_philosophy}
            onChoose={(choice: any) =>
              setChoices((current) => ({ ...current, [role.key]: choice }))
            }
          />
        ))}
      </div>
      <p className="mb-3 text-xs text-slate-400" data-testid="staff-salary-total">
        Contracts selected, paid once: <b className="text-white">{fmt(salaryDue)} FAN</b>. Fan Coin on
        hand, wallet plus club: <b className="text-white">{fanText(fanAvailable)}</b>. Each contract
        is paid from whichever of those balances can cover it.
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

export function academyIntakeQuote(level: number) {
  const facilityLevel = Math.max(1, Math.floor(Number(level) || 1));
  return {
    level: facilityLevel,
    cost: 200 * facilityLevel,
    minimumArrivals: 1 + Math.floor(facilityLevel / 2),
  };
}

export function isAcademyListPlayer(player: any) {
  if (!player || player.promoted) return false;
  const status = String(player.squad_status || "").toLowerCase();
  if (status === "first_team" || status === "senior") return false;
  return status === "academy" || player.acquired_via === "academy";
}

function filedLabel(value: unknown) {
  const text = String(value || "").trim();
  if (!text || text.toLowerCase() === "not filed") return "";
  return text;
}

function AcademyStep({ clubId, onDone }: { clubId: string; onDone: () => void }) {
  const { data: club, refetch } = useClub(clubId);
  const [busyIntake, setBusyIntake] = useState(false);
  const [justScouted, setJustScouted] = useState<any[]>([]);

  const fromClub = (club?.squad || []).filter(isAcademyListPlayer);
  const youth = [...justScouted.filter(isAcademyListPlayer), ...fromClub].filter(
    (player, index, all) => {
      const key = String(player.id || player.name);
      return all.findIndex((item) => String(item.id || item.name) === key) === index;
    },
  );
  const appointed = appointedFor(club, "head_of_youth_development");
  const hoydName = appointed?.name || "";
  const hoydRating = hoydName && appointed?.rating != null ? appointed.rating : null;
  const hoydInfluence = appointed ? staffDevelopment(appointed, "head_of_youth_development") : null;
  const hiredStaff = STAFF_ROLES.map((role) => {
    const person = appointedFor(club, role.key);
    return person
      ? { role, person, influence: staffDevelopment(person, role.key) }
      : { role, person: null, influence: null };
  });
  const quote = academyIntakeQuote(club?.facilities?.academy?.level);
  const cashRaw = club?.economy?.cash_gtex ?? club?.health?.cash;
  const cash = cashRaw == null || cashRaw === "" ? null : Number(cashRaw);
  const shortOfIntake = cash != null && Number.isFinite(cash) && cash < quote.cost;
  const potentials = youth
    .map((player: any) => Number(player.potential))
    .filter((value: number) => Number.isFinite(value) && value > 0);

  const handleManualIntake = async () => {
    setBusyIntake(true);
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/academy/intake`);
      const addedPlayers = Array.isArray(data?.regens) ? data.regens : [];
      setJustScouted((current) => [...addedPlayers, ...current]);
      const added = addedPlayers.length;
      toast.success(
        added
          ? `${added} youth player${added === 1 ? "" : "s"} added to the academy list.`
          : "Youth intake filed.",
      );
      await refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyIntake(false);
    }
  };

  return (
    <Panel
      eyebrow="Step 4 · Youth academy"
      title="Academy list"
      testid="onboarding-academy-step"
    >
      <p className="mb-4 text-sm text-slate-300">
        These are the players filed on the academy list. A card shows the age, main position,
        rating and potential stored for that player. Opening the club does not charge for an intake.
      </p>

      <div className="mb-4 grid gap-2 sm:grid-cols-3" data-testid="academy-facts">
        <div className="rounded border border-white/10 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Academy level</p>
          <p className="text-sm font-semibold text-white">{quote.level}</p>
        </div>
        <div className="rounded border border-white/10 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">On the academy list</p>
          <p className="text-sm font-semibold text-white">{youth.length}</p>
        </div>
        <div className="rounded border border-white/10 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Potential range</p>
          <p className="text-sm font-semibold text-white">
            {potentials.length
              ? `${Math.min(...potentials)}–${Math.max(...potentials)}`
              : "Not filed"}
          </p>
        </div>
      </div>

      <div className="mb-4 rounded border border-white/10 bg-slate-950/40 p-3" data-testid="academy-staff">
        <div className="flex items-start gap-3">
          <Sprout size={16} className="mt-0.5 shrink-0 text-emerald-300" />
          <div>
            <p className="text-sm font-semibold text-white">
              {hoydName || "Default youth lead"}
              {hoydRating != null ? ` · rating ${hoydRating}` : ""}
              {hoydInfluence ? ` · youth development ${hoydInfluence.skill}` : ""}
            </p>
            <p className="text-xs text-slate-400">
              {hoydName && hoydInfluence
                ? `${hoydName} is the appointed head of youth. Youth development ${hoydInfluence.skill} adds ${hoydInfluence.intakeBonus} to intake potential and ${hoydInfluence.potentialBonus} to the academy potential bonus.`
                : "No named head of youth is appointed. The default lead's development rating of 10 is used when an intake is generated."}
            </p>
          </div>
        </div>
        <ul className="mt-3 space-y-1 text-xs text-slate-300">
          {hiredStaff.map(({ role, person, influence }) => (
            <li key={role.key} data-testid={`academy-appointed-${role.key}`}>
              {role.label}:{" "}
              {person ? (
                <span className="text-white">
                  {person.name}
                  {person.rating != null ? ` · rating ${person.rating}` : ""}
                  {influence ? ` · ${influence.label} ${influence.skill}` : ""}
                </span>
              ) : (
                <span className="text-slate-500">Default seat</span>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div className="mb-4 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-slate-400">
            {youth.length
              ? `${youth.length} on the academy list`
              : "Nobody is on the academy list yet."}
          </p>
          <Btn
            variant="secondary"
            disabled={busyIntake || shortOfIntake}
            onClick={handleManualIntake}
            data-testid="onboarding-scout-genesis-intake"
          >
            {busyIntake ? "Scouting…" : "Scout a youth intake"}
          </Btn>
        </div>
        <p className="text-xs text-slate-400" data-testid="academy-intake-cost">
          This charges <b className="text-white">{fmt(quote.cost)} GTX</b> from club cash
          {cash != null && Number.isFinite(cash) ? ` (${fmt(cash)} GTX on hand)` : ""}. Academy level{" "}
          {quote.level} brings at least {quote.minimumArrivals} player
          {quote.minimumArrivals === 1 ? "" : "s"}. A higher level, campus bonus, or head-of-youth
          rating can add players and raise the potential band. They arrive aged 16–18 with a current
          rating below that potential.
          {shortOfIntake ? " Club cash does not cover this intake." : ""}
        </p>

        {youth.length === 0 ? (
          <div className="rounded border border-dashed border-white/10 p-4 text-xs text-slate-400">
            No academy players are filed. Scout an intake, or open the club and do it later.
          </div>
        ) : (
          <div
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            data-testid="onboarding-genesis-regens"
          >
            {youth.map((player: any) => {
              const archetype = filedLabel(player.archetype);
              const mood = filedLabel(player.mood_state);
              const gap =
                player.potential == null || player.rating == null
                  ? null
                  : Math.max(0, Number(player.potential) - Number(player.rating));
              const fill =
                player.rating == null || player.potential == null
                  ? 0
                  : Math.min(100, (Number(player.rating) / Math.max(1, Number(player.potential))) * 100);
              return (
                <article
                  key={player.id || player.name}
                  className="rounded-lg border border-white/10 bg-slate-950/50 p-3"
                  data-testid={`genesis-regen-${player.id}`}
                >
                  <div className="flex items-start gap-3">
                    {player.portrait_url ? (
                      <img
                        src={player.portrait_url}
                        alt=""
                        className="h-12 w-12 shrink-0 rounded-full object-cover bg-slate-800"
                      />
                    ) : null}
                    <div className="min-w-0 flex-1">
                      <h4 className="truncate text-sm font-bold text-white">{player.name}</h4>
                      <p className="text-[11px] text-slate-400">
                        Age {player.age ?? "—"} · {posShort(player.position)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="gx-mono text-lg font-black leading-none text-white">
                        {player.rating ?? "—"}
                      </p>
                      <p className="gx-mono text-[11px] font-bold text-amber-300">
                        POT {player.potential ?? "—"}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 h-1.5 rounded-sm bg-white/5" title="Current rating against potential">
                    <div
                      className="h-1.5 rounded-sm bg-emerald-400"
                      style={{ width: `${fill}%` }}
                    />
                  </div>
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
                    <span>{gap == null ? "Gap not filed" : `${gap} below potential`}</span>
                    <span className="gx-mono text-emerald-300">
                      {player.value_coin == null ? "Value not filed" : `${fmt(player.value_coin)} GTX`}
                    </span>
                  </div>
                  {archetype || mood ? (
                    <p className="mt-1 text-[11px] text-slate-400">
                      {[archetype, mood].filter(Boolean).join(" · ")}
                    </p>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </div>

      <p className="mb-4 text-xs text-slate-400" data-testid="onboarding-build-a-son-banner">
        Build a Son stays on the Academy page after the club opens. It inducts an heir from a senior
        player's bloodline and charges GTX. This step does not induct one.
      </p>

      <div className="flex items-center justify-between gap-3 border-t border-white/10 pt-4">
        <p className="text-xs text-slate-400">
          Academy players stay there until they are promoted. Rating moves through training and minutes.
        </p>
        <Btn
          onClick={onDone}
          className="flex items-center gap-2"
          data-testid="onboarding-proceed-competition"
        >
          <span>Open my club</span>
          <ArrowRight size={14} />
        </Btn>
      </div>
    </Panel>
  );
}

const PHILOSOPHY_LABEL: Record<string, string> = {
  youth: "Youth development",
  academy: "Academy-first",
  selling: "Selling club",
  superstars: "Superstar club",
  sustainable: "Financially sustainable",
  balanced: "Balanced",
};

const NATIONALITY_LABEL: Record<string, string> = {
  preferred: "Preferred domestic",
  exclusive: "Exclusive domestic",
  none: "Global scouting",
};

const CREST_STYLE_LABEL: Record<string, string> = {
  traditional: "Traditional shield",
  modern: "Modern roundel",
  metallic: "Metallic diamond",
};

function CreateFirstClub({
  onDone,
  onCancel,
  another,
  launchGrant = 2500,
  launchGrantLimit = 500,
}: any) {
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
      const crestLibrary = buildCrestLibrary(clubName);
      const activeCrest =
        recommendation?.crest_concepts?.[selectedCrestIdx] ||
        crestLibrary[preferredCrestIndex(crestLibrary, preferredStyle)];
      const activeKit = kitSet || buildKitSet(selectedKitPresetId || KIT_PRESETS[0].id, clubName);
      const homeKit = activeKit?.home;

      const primaryColor = activeCrest?.primary_color || homeKit?.primary_color || "#0F766E";
      const secondaryColor = activeCrest?.secondary_color || homeKit?.secondary_color || "#F8FAFC";
      const accentColor = activeCrest?.accent_color || homeKit?.accent_color || "#F59E0B";

      const filedDna = buildClubDNA(
        clubName,
        validatedLocation.cityName,
        validatedLocation.countryCode,
        recruitmentFocus,
        preferredAgeBracket,
        nationalityFocus,
      );
      const dnaPayload = {
        primary_philosophy: filedDna.primary_philosophy,
        secondary_philosophies: filedDna.secondary_philosophies,
        nationality_mode: filedDna.nationality_mode,
        target_nationalities: filedDna.target_nationalities,
        allow_dual_nationality: true,
        age_mode: filedDna.age_mode,
        preferred_max_age: filedDna.preferred_max_age,
        allow_age_exceptions: true,
        transfer_strategy: filedDna.transfer_strategy,
        financial_philosophy: filedDna.financial_philosophy,
        club_vision_narrative: filedDna.vision_narrative,
      };
      const kitPiece = (piece: any) => ({
        primary_color: piece.primary_color,
        secondary_color: piece.secondary_color,
        accent_color: piece.accent_color,
        pattern_type: piece.pattern_type,
        collar_style: piece.collar_style,
        sleeve_style: piece.sleeve_style,
        shorts_color: piece.shorts_color,
        socks_color: piece.socks_color,
        front_text: piece.front_text,
      });

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

      const jerseyPayload = activeKit
        ? {
            home: kitPiece(activeKit.home),
            away: kitPiece(activeKit.away),
            third: kitPiece(activeKit.third),
            goalkeeper: kitPiece(activeKit.goalkeeper),
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
  const dnaPreview =
    clubName.length < 3 || "error" in location
      ? null
      : buildClubDNA(
          clubName,
          location.cityName,
          location.countryCode,
          recruitmentFocus,
          preferredAgeBracket,
          nationalityFocus,
        );

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
            {(["name", "philosophy", "roster", "studio", "review"] as const).map((step, idx) => {
              const current = ["name", "philosophy", "roster", "studio", "review"].indexOf(
                wizardStep,
              );
              const reached = idx <= current;
              return (
                <button
                  key={step}
                  type="button"
                  disabled={!reached || step === wizardStep}
                  aria-label={`Founding step ${idx + 1} of 5`}
                  onClick={() => setWizardStep(step)}
                  className={`h-1.5 w-6 rounded-full transition-colors ${
                    reached ? "bg-emerald-400" : "bg-white/10"
                  } disabled:cursor-default`}
                />
              );
            })}
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
                Create now · default kit
              </Btn>
            </div>
            <p className="mt-2 text-[11px] text-slate-500">
              Create now files {PHILOSOPHY_LABEL[recruitmentFocus] || "Youth development"},{" "}
              {preferredAgeBracket === "none" ? "all ages" : preferredAgeBracket},{" "}
              {NATIONALITY_LABEL[nationalityFocus] || "Preferred domestic"}, a{" "}
              {CREST_STYLE_LABEL[preferredStyle] || "traditional"} crest, and the first uniform set.
              The next pages change those choices before you seal the charter.
            </p>
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
              This choice is saved on the club. It sets the recruitment recommendation: formation,
              youth minutes, and whether the club buys to develop and sell, spends on established
              names, or keeps contracts disciplined.
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
                  <p className="mt-0.5 font-semibold text-emerald-300">
                    {PHILOSOPHY_LABEL[recruitmentFocus] || recruitmentFocus}
                  </p>
                </div>
                <div className="rounded border border-white/10 bg-slate-950/50 p-3">
                  <span className="text-[10px] uppercase text-slate-400">Transfer strategy</span>
                  <p className="mt-0.5 font-semibold text-cyan-300 capitalize">
                    {(dnaPreview?.transfer_strategy || "buy_young_develop_sell").replace(/_/g, " ")}
                  </p>
                </div>
                <div className="rounded border border-white/10 bg-slate-950/50 p-3">
                  <span className="text-[10px] uppercase text-slate-400">Age profile</span>
                  <p className="mt-0.5 font-semibold text-white">
                    {preferredAgeBracket === "none" ? "All ages" : preferredAgeBracket}
                  </p>
                </div>
                <div className="rounded border border-white/10 bg-slate-950/50 p-3">
                  <span className="text-[10px] uppercase text-slate-400">Nationality</span>
                  <p className="mt-0.5 font-semibold text-white">
                    {NATIONALITY_LABEL[nationalityFocus] || nationalityFocus}
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
                    The first {fmt(launchGrantLimit)} eligible club owners receive{" "}
                    <b>{fmt(launchGrant)} GTX</b> ring-fenced for player signings, plus{" "}
                    <b>1,000 FAN</b> toward staff contracts and gifting. Named staff may need more
                    Fan Coin. You can convert deposited GTEX or buy Fan Coin after the club exists.
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
  const money = useOnboardingMoney(club?.club_id);
  const footerTreasury =
    money.cash ?? (club?.cash == null || club?.cash === "" ? null : Number(club.cash));

  if (loading || (user && isLoading)) return <Loading label="Preparing your club" />;
  if (!user) return <Navigate to="/login" replace />;
  if (creating || (!club && !(data?.clubs || []).length)) {
    return (
      <CreateFirstClub
        another={Boolean((data?.clubs || []).length)}
        launchGrant={Number(data?.launch_grant ?? 2500)}
        launchGrantLimit={Number(data?.launch_grant_owner_limit ?? 500)}
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
        {index === 1 && (
          <SquadStep clubId={club.club_id} knownCash={club.cash} onDone={next} />
        )}
        {index === 2 && <ManagerStep clubId={club.club_id} onDone={next} />}
        {index === 3 && <AcademyStep clubId={club.club_id} onDone={openClub} />}
        <p className="mt-6 text-xs text-slate-600">
          Club treasury: {moneyText(footerTreasury)} · Squad {club.squad_size ?? 0}
        </p>
      </div>
    </div>
  );
}

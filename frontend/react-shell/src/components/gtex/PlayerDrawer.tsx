import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Loading, TraitBar } from "@/components/gtex/ui";
import { PlayerCard, footMark, posShort, positionParts } from "@/components/gtex/PlayerCard";

function ClubOwnerTransferDesk({ player, onClose }: { player: any; onClose: () => void }) {
  const { active } = useActiveClub();
  const refresh = useRefreshOwner();
  const clubId = player?.club_id || active?.club_id;
  const squadPlayerId = player?.id;
  const defaultPrice = Math.max(
    50,
    Math.round(Number(player?.asking_price_gtex || player?.value_coin || 150)),
  );
  const [askingPrice, setAskingPrice] = useState<string>(String(defaultPrice));
  const [loanClub, setLoanClub] = useState<string>(String(player?.loan_club || ""));
  const [busyAction, setBusyAction] = useState<string>("");

  useEffect(() => {
    setAskingPrice(
      String(
        Math.max(50, Math.round(Number(player?.asking_price_gtex || player?.value_coin || 150))),
      ),
    );
    setLoanClub(String(player?.loan_club || ""));
  }, [player?.id, player?.asking_price_gtex, player?.value_coin, player?.loan_club]);

  if (!clubId || !squadPlayerId) return null;

  const isListed = player?.status === "listed";
  const isLoaned =
    player?.loan_status === "loaned_out" || player?.personality?.loan_status === "loaned_out";
  const currentLoanClub = player?.loan_club || player?.personality?.loan_club;
  const estLoanFee = Math.max(25, Math.round(Number(player?.value_coin || 100) * 0.15));

  const handleSell = async (mode: "instant" | "list" | "unlist") => {
    setBusyAction(mode);
    try {
      const priceNum = Number(askingPrice) || defaultPrice;
      const { data } = await api.post(`/owner/clubs/${clubId}/squad/${squadPlayerId}/sell`, {
        mode,
        asking_price_gtex: priceNum,
      });
      if (mode === "instant") {
        toast.success(
          `Sold ${player.name} to ${data.buyer_club} for ${fmt(data.gross_gtex)} GTX (${fmt(data.net_gtex)} GTX net added to club cash).`,
        );
        await refresh();
        onClose();
      } else if (mode === "list") {
        toast.success(
          `${player.name} transfer-listed at ${fmt(data.asking_price_gtex)} GTX · ${data.bidder} submitted an offer in your Inbox.`,
        );
        await refresh();
      } else {
        toast.success(`${player.name} removed from the transfer list.`);
        await refresh();
      }
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusyAction("");
    }
  };

  const handleLoan = async (action: "loan_out" | "recall") => {
    setBusyAction(action);
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/squad/${squadPlayerId}/loan`, {
        action,
        destination_club: loanClub.trim() || undefined,
      });
      if (action === "loan_out") {
        toast.success(
          `Loaned ${player.name} to ${data.destination_club} (+${fmt(data.loan_fee_gtex)} GTX loan fee added to club cash).`,
        );
      } else {
        toast.success(`Recalled ${player.name} from ${data.recalled_from}.`);
      }
      await refresh();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusyAction("");
    }
  };

  const handleRelease = async () => {
    if (
      !window.confirm(
        `Release ${player.name} from your squad? Market signings refund to treasury/wallet; academy and starter players enter free agency.`,
      )
    )
      return;
    setBusyAction("release");
    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/squad/${squadPlayerId}/release`);
      const refundNote =
        Number(data?.refund_amount || 0) > 0
          ? ` · Refunded ${fmt(data.refund_amount)} GTX`
          : " · Entered free agency";
      toast.success(`Released ${player.name}${refundNote}.`);
      await refresh();
      onClose();
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusyAction("");
    }
  };

  return (
    <div
      className="rounded-sm border border-amber-400/30 bg-amber-950/15 p-4 space-y-3"
      data-testid="drawer-owner-transfer-desk"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="gx-eyebrow text-amber-300">Transfer & Contract Actions</p>
        {isListed && <Chip tone="gold">Transfer Listed</Chip>}
        {isLoaned && <Chip tone="cyan">On Loan · {currentLoanClub}</Chip>}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
            Asking / Sale Price (GTX)
          </label>
          <input
            type="number"
            min={25}
            value={askingPrice}
            onChange={(e) => setAskingPrice(e.target.value)}
            data-testid="drawer-sell-price-input"
            className="gx-input w-full py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
            Loan Destination (Optional)
          </label>
          <input
            type="text"
            placeholder="Auto-match partner club"
            value={loanClub}
            onChange={(e) => setLoanClub(e.target.value)}
            data-testid="drawer-loan-club-input"
            className="gx-input w-full py-1.5 text-xs"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={Boolean(busyAction)}
          onClick={() => void handleSell("instant")}
          data-testid="drawer-instant-sell-btn"
          className="rounded border border-emerald-400/50 bg-emerald-500/20 px-2.5 py-2 text-xs font-bold uppercase tracking-wide text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-50"
        >
          {busyAction === "instant" ? "Selling…" : `Instant Sell (${fmt(askingPrice)} GTX)`}
        </button>
        <button
          type="button"
          disabled={Boolean(busyAction)}
          onClick={() => void handleSell(isListed ? "unlist" : "list")}
          data-testid="drawer-transfer-list-btn"
          className="rounded border border-amber-400/50 bg-amber-500/20 px-2.5 py-2 text-xs font-bold uppercase tracking-wide text-amber-200 hover:bg-amber-500/30 disabled:opacity-50"
        >
          {busyAction === "list" || busyAction === "unlist"
            ? "Updating…"
            : isListed
              ? "Remove Listing"
              : "Transfer List"}
        </button>
        <button
          type="button"
          disabled={Boolean(busyAction)}
          onClick={() => void handleLoan(isLoaned ? "recall" : "loan_out")}
          data-testid="drawer-loan-btn"
          className="rounded border border-cyan-400/50 bg-cyan-500/20 px-2.5 py-2 text-xs font-bold uppercase tracking-wide text-cyan-200 hover:bg-cyan-500/30 disabled:opacity-50"
        >
          {busyAction === "loan_out" || busyAction === "recall"
            ? "Processing…"
            : isLoaned
              ? "Recall from Loan"
              : `Loan Out (+${fmt(estLoanFee)} GTX)`}
        </button>
        <button
          type="button"
          disabled={Boolean(busyAction)}
          onClick={() => void handleRelease()}
          data-testid="drawer-release-btn"
          className="rounded border border-rose-400/50 bg-rose-500/20 px-2.5 py-2 text-xs font-bold uppercase tracking-wide text-rose-200 hover:bg-rose-500/30 disabled:opacity-50"
        >
          {busyAction === "release" ? "Releasing…" : "Release Player"}
        </button>
      </div>
    </div>
  );
}

function PlayerAcquisition({ playerId }: { playerId: string }) {
  const qc = useQueryClient();
  const { data: market, isError } = useQuery({
    queryKey: ["player-acquisition", playerId],
    queryFn: async () => (await api.get(`/v2/players/${playerId}/shares/market`)).data,
    retry: false,
  });
  const { data: holdings = [] } = useQuery({
    queryKey: ["my-player-acquisitions"],
    queryFn: async () => (await api.get("/v2/players/me/shares/holdings")).data,
    retry: false,
  });
  if (isError)
    return (
      <p className="text-xs text-slate-500" data-testid="drawer-no-acquisition">
        This player is not currently available to acquire.
      </p>
    );
  if (!market) return null;

  const owned =
    Array.isArray(holdings) &&
    holdings.some(
      (holding: any) => holding.player_id === playerId && Number(holding.share_count) > 0,
    );
  const available = Math.max(
    0,
    Number(market.released_shares ?? market.total_shares) - Number(market.circulating_shares || 0),
  );
  const buy = async () => {
    if (owned || available < 1) return;
    try {
      const { data: result } = await api.post(`/v2/players/${playerId}/shares/buy`, {
        share_count: 1,
      });
      toast.success(
        `Player acquired · ${fmt(result.net_amount_coin ?? result.gross_amount_coin, 2)} GTX`,
      );
      await qc.invalidateQueries({ queryKey: ["player-acquisition", playerId] });
      await qc.invalidateQueries({ queryKey: ["my-player-acquisitions"] });
    } catch (error) {
      toast.error(errMsg(error));
      await qc.invalidateQueries({ queryKey: ["my-player-acquisitions"] });
    }
  };

  return (
    <div className="rounded-sm border border-white/10 p-4" data-testid="drawer-player-acquisition">
      <p className="gx-eyebrow mb-2">Player acquisition</p>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="gx-label">Acquisition price</p>
          <p className="gx-mono text-white">{fmt(market.share_price_coin, 2)} GTX</p>
        </div>
        <div>
          <p className="gx-label">Units available</p>
          <p className="gx-mono text-white">{available}</p>
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Each account may acquire one complete unit of this player. Units cannot be resold or traded.
      </p>
      <div className="mt-3">
        <Btn onClick={buy} disabled={owned || available < 1} data-testid="drawer-acquire-player">
          {owned ? "Already acquired" : available < 1 ? "No units available" : "Acquire player"}
        </Btn>
      </div>
    </div>
  );
}

function RegenDossier({ playerId, fallbackPlayer }: { playerId: string; fallbackPlayer?: any }) {
  const {
    data: m,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["market-player", playerId],
    queryFn: async () => (await api.get(`/market/players/${playerId}`)).data,
    retry: false,
  });
  if ((isError || !m) && fallbackPlayer) {
    const pers = fallbackPlayer.personality || {};
    const attrs = fallbackPlayer.attributes || pers.attributes || {};
    const regenPlaystyle: string | undefined =
      fallbackPlayer.playstyle || pers.playstyle || fallbackPlayer.archetype;
    const regenTraits: string[] = Array.isArray(fallbackPlayer.traits)
      ? fallbackPlayer.traits
      : Array.isArray(pers.traits)
        ? pers.traits
        : [];
    const posText = fallbackPlayer.position_display || fallbackPlayer.position || "";
    const footText =
      footMark(
        fallbackPlayer.preferred_foot ||
          fallbackPlayer.dominant_foot ||
          pers.preferred_foot ||
          pers.dominant_foot,
      ) || "Not filed";
    const heightCm = fallbackPlayer.height_cm || pers.height_cm;
    const ceiling = Math.max(
      0,
      Number(fallbackPlayer.potential || 0) - Number(fallbackPlayer.rating || 0),
    );
    return (
      <div className="space-y-5" data-testid="drawer-regen-dossier">
        <div className="mx-auto max-w-[240px]">
          <PlayerCard
            testid="drawer-regen-card"
            name={fallbackPlayer.name}
            rating={fallbackPlayer.rating}
            potential={fallbackPlayer.potential}
            position={posText}
            age={fallbackPlayer.age}
            heightCm={heightCm}
            foot={
              fallbackPlayer.preferred_foot ||
              fallbackPlayer.dominant_foot ||
              pers.preferred_foot ||
              pers.dominant_foot
            }
            image={fallbackPlayer.portrait_url || fallbackPlayer.image}
            regen
            archetype={regenPlaystyle}
            traits={regenTraits}
            badge={ceiling >= 15 ? "Wonderkid" : "Academy Prospect"}
            stats={[
              { k: "Ceiling", v: `+${ceiling}` },
              { k: "Morale", v: fallbackPlayer.morale ?? "-" },
              { k: "Value", v: fmt(fallbackPlayer.value_coin) },
            ]}
          />
        </div>
        <div className="flex flex-wrap gap-2" data-testid="drawer-positions">
          <Chip tone="emerald">
            {fallbackPlayer.squad_status === "academy" ? "Academy prospect" : "Club regen"}
          </Chip>
          {positionParts(posText).map((part) => (
            <Chip key={part} tone="cyan">
              {posShort(part)}
            </Chip>
          ))}
          {fallbackPlayer.mood_state && fallbackPlayer.mood_state !== "Not filed" && (
            <Chip tone="gold">Mood: {fallbackPlayer.mood_state}</Chip>
          )}
          {(fallbackPlayer.nationality || pers.nationality) && (
            <Chip tone="gold">{fallbackPlayer.nationality || pers.nationality}</Chip>
          )}
          {(fallbackPlayer.father_name ||
            fallbackPlayer.bloodline?.parent_name ||
            pers.father_name) && (
            <Chip tone="purple">
              Son of{" "}
              {fallbackPlayer.father_name ||
                fallbackPlayer.bloodline?.parent_name ||
                pers.father_name}
            </Chip>
          )}
          {heightCm && <Chip>{heightCm} cm</Chip>}
        </div>
        <p className="text-sm font-semibold text-amber-200" data-testid="drawer-foot">
          Favoured foot: {footText}
        </p>
        {(fallbackPlayer.performance_summary || fallbackPlayer.contract_summary) && (
          <div className="rounded-sm border border-emerald-500/20 bg-emerald-500/[0.04] p-3.5 text-xs space-y-1.5">
            {fallbackPlayer.performance_summary && (
              <p className="text-emerald-200">
                <b>Match performance:</b> {fallbackPlayer.performance_summary}
              </p>
            )}
            {fallbackPlayer.contract_summary && (
              <p className="text-slate-300">
                <b>Contract decision:</b> {fallbackPlayer.contract_summary}
              </p>
            )}
          </div>
        )}
        {(regenPlaystyle || regenTraits.length > 0) && (
          <div
            className="rounded-sm border border-cyan-500/20 bg-cyan-500/[0.04] p-3.5 text-xs space-y-2"
            data-testid="drawer-regen-traits"
          >
            {regenPlaystyle && (
              <div className="flex items-center justify-between gap-2">
                <span className="gx-eyebrow text-cyan-300">Style of Play</span>
                <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[11px] font-bold text-cyan-200">
                  {regenPlaystyle}
                </span>
              </div>
            )}
            {regenTraits.length > 0 && (
              <div>
                <p className="gx-eyebrow text-slate-400 mb-1.5">Traits & Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {regenTraits.map((trait, i) => (
                    <span
                      key={`${trait}-${i}`}
                      className="rounded border border-white/10 bg-white/[0.05] px-2 py-0.5 text-[11px] font-medium text-slate-200"
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {Object.keys(attrs).length > 0 && (
          <div className="space-y-2.5" data-testid="drawer-regen-attributes">
            {["pace", "shooting", "passing", "dribbling", "defending", "physical"].map((k) =>
              attrs[k] != null ? (
                <TraitBar key={k} label={label(k)} value={Number(attrs[k])} max={99} />
              ) : null,
            )}
          </div>
        )}
      </div>
    );
  }
  if (isLoading || !m) return <Loading label="Pulling the academy file" />;
  const id = m.identity || {};
  const a = m.attributes || {};
  const regenPlaystyle: string | undefined = id.playstyle || m.playstyle;
  const regenTraits: string[] =
    Array.isArray(id.traits) && id.traits.length > 0
      ? id.traits
      : Array.isArray(id.skills) && id.skills.length > 0
        ? id.skills
        : [];
  return (
    <div className="space-y-5" data-testid="drawer-regen-dossier">
      <div className="mx-auto max-w-[240px]">
        <PlayerCard
          testid="drawer-regen-card"
          name={id.player_name}
          rating={a.overall}
          potential={a.potential}
          position={id.normalized_position || id.position}
          age={id.age}
          nationality={id.nationality}
          club={id.current_club_name}
          image={id.image_url}
          regen
          archetype={regenPlaystyle}
          traits={regenTraits}
          badge={a.potential - a.overall >= 15 ? "Wonderkid" : "Regen"}
          stats={[
            { k: "Ceiling", v: `+${Math.max(0, (a.potential || 0) - (a.overall || 0))}` },
            { k: "Nation", v: id.nationality_code || "-" },
            { k: "Age", v: id.age ?? "-" },
          ]}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <Chip tone="emerald">Pre-seeded national regen</Chip>
        {id.position && <Chip tone="cyan">{id.position}</Chip>}
        {regenPlaystyle && <Chip tone="gold">{regenPlaystyle}</Chip>}
      </div>
      {(regenPlaystyle || regenTraits.length > 0) && (
        <div
          className="rounded-sm border border-cyan-500/20 bg-cyan-500/[0.04] p-3.5 text-xs space-y-2"
          data-testid="drawer-regen-traits"
        >
          {regenPlaystyle && (
            <div className="flex items-center justify-between">
              <span className="gx-eyebrow text-cyan-300">Style of Play</span>
              <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[11px] font-bold text-cyan-200">
                {regenPlaystyle}
              </span>
            </div>
          )}
          {regenTraits.length > 0 && (
            <div>
              <p className="gx-eyebrow text-slate-400 mb-1.5">Traits & Skills</p>
              <div className="flex flex-wrap gap-1.5">
                {regenTraits.map((trait, i) => (
                  <span
                    key={`${trait}-${i}`}
                    className="rounded border border-white/10 bg-white/[0.05] px-2 py-0.5 text-[11px] font-medium text-slate-200"
                  >
                    {trait}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <div className="space-y-2.5" data-testid="drawer-regen-attributes">
        {["pace", "shooting", "passing", "dribbling", "defending", "physical"].map((k) => (
          <TraitBar key={k} label={label(k)} value={a[k] ?? 0} max={99} />
        ))}
      </div>
      <PlayerAcquisition playerId={playerId} />
    </div>
  );
}

export function PlayerDrawer({
  playerId,
  player,
  onClose,
  extra,
}: {
  playerId: string | null;
  player?: any;
  onClose: () => void;
  extra?: React.ReactNode;
}) {
  const {
    data: p,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["real-player", playerId],
    queryFn: async () => (await api.get(`/v2/players/real-universe/${playerId}`)).data,
    enabled: !!playerId,
    retry: false,
  });
  const { data: form } = useQuery({
    queryKey: ["player-form", playerId],
    queryFn: async () =>
      (await api.get(`/v2/players/${playerId}/form`, { params: { include_performances: false } }))
        .data,
    enabled: !!playerId,
  });
  const { data: quote } = useQuery({
    queryKey: ["player-quote", playerId],
    queryFn: async () =>
      (await api.get("/owner/market/quote", { params: { player_ids: playerId } })).data.quotes[
        playerId as string
      ],
    enabled: !!playerId,
  });
  if (!playerId) return null;
  const signals =
    p?.attributes && Object.keys(p.attributes).length > 0
      ? p.attributes
      : p?.normalized_signals || {};
  const tierNorm = String(p?.real_player_tier || "").toLowerCase();
  const isLegend = tierNorm === "legend";
  const isRegen = Boolean(p?.is_regen) || p?.is_real_player === false || tierNorm === "regen";
  const honors: string[] = Array.isArray(p?.metadata_json?.honors) ? p.metadata_json.honors : [];
  const playstyle: string | undefined =
    p?.playstyle ||
    p?.summary_json?.playstyle ||
    p?.metadata_json?.playstyle ||
    p?.metadata_json?.archetype;
  const playerTraits: string[] =
    Array.isArray(p?.traits) && p.traits.length > 0
      ? p.traits
      : Array.isArray(p?.skills) && p.skills.length > 0
        ? p.skills
        : Array.isArray(p?.summary_json?.traits) && p.summary_json.traits.length > 0
          ? p.summary_json.traits
          : Array.isArray(p?.metadata_json?.traits) && p.metadata_json.traits.length > 0
            ? p.metadata_json.traits
            : [];
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      data-testid="player-drawer"
    >
      <aside
        className="gx-scroll h-full w-full max-w-md overflow-y-auto border-l border-white/10 bg-[#070B11] p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <p className="gx-eyebrow">Scouting report</p>
          <button
            onClick={onClose}
            data-testid="player-drawer-close"
            className="text-slate-400 transition-colors hover:text-white"
          >
            <X size={18} />
          </button>
        </div>
        {isError ? (
          <div className="space-y-5">
            <RegenDossier playerId={playerId} fallbackPlayer={player} />
            {player && <ClubOwnerTransferDesk player={player} onClose={onClose} />}
            {extra}
          </div>
        ) : isLoading || !p ? (
          <Loading label="Pulling the dossier" />
        ) : (
          <div className="space-y-5">
            <div className="mx-auto max-w-[240px]">
              <PlayerCard
                name={p.canonical_display_name || p.player_name}
                rating={quote?.rating ?? p.governed_gsi ?? p.summary_json?.gsi ?? p.average_rating}
                potential={
                  isLegend
                    ? undefined
                    : (p.potential ?? p.summary_json?.potential ?? quote?.potential)
                }
                position={p.position}
                age={p.age}
                heightCm={p.height_cm}
                foot={p.dominant_foot || p.preferred_foot}
                nationality={p.nationality}
                club={p.current_club_name}
                image={p.image_url}
                facebank={isRegen}
                tier={isLegend ? "legendary" : undefined}
                badge={isLegend ? "ICON · 1 OF 1" : undefined}
                archetype={playstyle}
                traits={playerTraits}
                stats={[
                  { k: "Fee", v: fmt(quote?.price) },
                  {
                    k: "Value",
                    v:
                      p.current_value_credits != null
                        ? fmt(p.current_value_credits, 1)
                        : fmt(quote?.price, 1),
                  },
                  { k: "Interest", v: p.market_interest_score ?? "-" },
                ]}
              />
            </div>
            <div className="flex flex-wrap gap-2" data-testid="drawer-positions">
              {positionParts(p.position).map((part) => (
                <Chip key={part} tone="cyan">
                  {posShort(part)}
                </Chip>
              ))}
              {playstyle && <Chip tone="gold">{playstyle}</Chip>}
              {p.current_league_name && <Chip>{p.current_league_name}</Chip>}
              {p.real_player_tier && <Chip tone="gold">{label(p.real_player_tier)}</Chip>}
              {p.lifecycle_status_label && <Chip tone="emerald">{p.lifecycle_status_label}</Chip>}
              {p.height_cm && <Chip>{p.height_cm} cm</Chip>}
            </div>
            <p className="text-sm font-semibold text-amber-200" data-testid="drawer-foot">
              Favoured foot: {footMark(p.dominant_foot || p.preferred_foot) || "Not filed"}
            </p>
            {(playstyle || playerTraits.length > 0) && (
              <div
                className="rounded-sm border border-cyan-500/20 bg-cyan-500/[0.04] p-3.5 text-xs space-y-2.5"
                data-testid="drawer-traits"
              >
                {playstyle && (
                  <div className="flex items-center justify-between" data-testid="drawer-playstyle">
                    <span className="gx-eyebrow text-cyan-300">Style of Play</span>
                    <span className="rounded bg-cyan-500/20 px-2.5 py-0.5 text-[11px] font-bold text-cyan-200">
                      {playstyle}
                    </span>
                  </div>
                )}
                {playerTraits.length > 0 && (
                  <div>
                    <p className="gx-eyebrow text-slate-400 mb-1.5">Traits & Skills</p>
                    <div className="flex flex-wrap gap-1.5">
                      {playerTraits.map((trait, i) => (
                        <span
                          key={`${trait}-${i}`}
                          className="rounded border border-white/10 bg-white/[0.05] px-2 py-0.5 text-[11px] font-medium text-slate-200"
                        >
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            {honors.length > 0 && (
              <div className="rounded-sm border border-amber-400/20 bg-amber-500/[0.04] p-3.5 text-xs space-y-1">
                <p className="gx-eyebrow text-amber-300 mb-1">Career Honors</p>
                {honors.map((h, i) => (
                  <p key={i} className="text-slate-300">
                    • {h}
                  </p>
                ))}
              </div>
            )}
            <div className="space-y-2.5" data-testid="drawer-signals">
              {Object.entries(signals)
                .filter(([, v]) => !Number.isNaN(Number(v)))
                .map(([k, v]: any) => (
                  <TraitBar
                    key={k}
                    label={label(k.replace(/_(score|signal)$/, ""))}
                    value={Math.round(Number(v))}
                    max={100}
                  />
                ))}
            </div>
            <div
              className="rounded-sm border border-white/10 p-4 text-sm"
              data-testid="drawer-form"
            >
              <p className="gx-eyebrow mb-2">GTEX form</p>
              {form?.has_sample ? (
                <p className="text-slate-300">
                  Avg rating {form.average_rating} · {form.matches_counted} matches · trend{" "}
                  {form.trend}
                </p>
              ) : (
                <p className="text-slate-500">
                  No GTEX competition minutes yet. Form builds once he plays.
                </p>
              )}
            </div>
            <PlayerAcquisition playerId={playerId} />
            {player && <ClubOwnerTransferDesk player={player} onClose={onClose} />}
            {extra}
          </div>
        )}
      </aside>
    </div>,
    document.body,
  );
}

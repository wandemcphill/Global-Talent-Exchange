import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Activity,
  Award,
  Box,
  Camera,
  CheckCircle2,
  ChevronRight,
  Coins,
  Compass,
  Eye,
  Flame,
  Layers,
  Lightbulb,
  Megaphone,
  Mic,
  Pause,
  Play,
  Radio,
  RotateCcw,
  Shield,
  Sliders,
  Sparkles,
  Target,
  Tv,
  Users,
  Volume2,
  VolumeX,
  Zap,
} from "lucide-react";
import { api, errMsg, tokens } from "@/lib/api";
import { useActiveClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";
import { Cinema3DStage, Cinema3DSceneType } from "@/components/gtex/Cinema3DStage";
import { PressRoomStage } from "@/components/gtex/PressRoomStage";
import { MatchPitchLiveScene } from "@/lib/3d/broadcast/MatchPitchLiveScene";
import { useMatchSpectatorStream } from "@/lib/3d/broadcast/useMatchSpectatorStream";
import { useMatchFullTimeGovernance } from "@/lib/3d/broadcast/useMatchFullTimeGovernance";
import { loadFiveMinuteShowcaseFixture } from "@/lib/3d/broadcast/showcaseLoader";
import { HolographicPlayerCard } from "@/components/gtex/ApexWidgets";
import { MatchdayLineupBroadcast, type MatchdaySquadMember } from "@/components/gtex/MatchdayLineupBroadcast";
import { mapAuthoritativeTactics } from "@/lib/3d/broadcast/authoritativeTactics";
import { useSkin } from "@/lib/skin-engine";
import {
  MatchSponsorIdentificationBadge,
  SilentMatchBroadcastPanel,
  useMatchCommercialInventory,
} from "@/components/advertising/GtexMatchBroadcastAds";
import type { PublicBrandAd } from "@/lib/commercial/api";
import { CinematicGiftingEngine, type CinematicGiftEvent } from "@/lib/3d/gifting/CinematicGiftingEngine";
import {
  metricText,
  pitchSource,
  seekTime,
  stepReplayClock,
  suppliedCrest,
} from "@/match2d/matchStateAdapter";
import { MatchTimelineScrubber, buildTimelineModel } from "./match-center/MatchTimelineScrubber";
import { Pitch2DView } from "@/pages/match-center/Pitch2DView";

const GIFTS = [
  { code: "stadium_roar", name: "Stadium Roar", cost: 10, rarity: "common" },
  { code: "captains_armband", name: "Captain's Armband", cost: 20, rarity: "rare" },
  { code: "home_end_banner", name: "Home End Banner", cost: 30, rarity: "rare" },
  { code: "golden_boot", name: "Golden Boot", cost: 50, rarity: "epic" },
  { code: "floodlights", name: "Floodlights", cost: 100, rarity: "epic" },
  { code: "last_minute_winner", name: "Last-Minute Winner", cost: 350, rarity: "epic" },
  { code: "paris_skyline", name: "Eiffel Tower Paris", cost: 750, rarity: "legendary" },
  { code: "wembley_stadium", name: "Wembley Stadium", cost: 2500, rarity: "legendary" },
  { code: "private_jet", name: "Private Jet Flyby", cost: 3500, rarity: "mythic" },
  { code: "ballon_dor", name: "Golden Ballon d'Or", cost: 10000, rarity: "mythic" },
  { code: "super_eagle", name: "Super Eagle", cost: 500, rarity: "legendary", anim: "super_eagle", animation_key: "super_eagle", sound_key: "eagle_scream", duration_ms: 8000 },
  { code: "black_jaguar", name: "Black Jaguar", cost: 700, rarity: "legendary", anim: "black_jaguar", animation_key: "black_jaguar", sound_key: "jaguar_roar", duration_ms: 8000 },
  { code: "white_tiger", name: "White Tiger", cost: 800, rarity: "legendary", anim: "white_tiger", animation_key: "white_tiger", sound_key: "white_tiger_roar", duration_ms: 8000 },
  { code: "polar_bear", name: "Polar Bear", cost: 900, rarity: "legendary", anim: "polar_bear", animation_key: "polar_bear", sound_key: "polar_bear_roar", duration_ms: 8000 },
];

// Tactical Style Presets
const TACTICAL_PRESETS = [
  {
    name: "GEGENPRESS",
    tagline: "Heavy Metal High Press",
    press: 88,
    line: 82,
    tempo: 84,
    risk: 80,
    formation: "4-2-4",
    mentality: "Attacking",
    color: "#00E87A",
  },
  {
    name: "TIKI-TAKA",
    tagline: "Total Positional Control",
    press: 65,
    line: 68,
    tempo: 52,
    risk: 45,
    formation: "4-3-3",
    mentality: "Balanced",
    color: "#60A5FA",
  },
  {
    name: "COUNTER",
    tagline: "Direct Vertical Breaks",
    press: 42,
    line: 38,
    tempo: 92,
    risk: 72,
    formation: "3-4-3",
    mentality: "Counter",
    color: "#FFB800",
  },
  {
    name: "LOW BLOCK",
    tagline: "Impenetrable Defensive Wall",
    press: 25,
    line: 22,
    tempo: 40,
    risk: 20,
    formation: "5-3-2",
    mentality: "Ultra Defensive",
    color: "#94A3B8",
  },
  {
    name: "BALANCED",
    tagline: "Dynamic Fluid Neutral",
    press: 50,
    line: 50,
    tempo: 50,
    risk: 50,
    formation: "4-3-3",
    mentality: "Balanced",
    color: "#10B981",
  },
];

function GiftRail({ match, clubId, onGiftSent }: any) {
  const refresh = useRefreshOwner();
  const [feed, setFeed] = useState<string[]>([]);
  const targets = [match.home_club_id, match.away_club_id].filter(
    (c: string | undefined): c is string => Boolean(c) && !String(c).startsWith("ai:"),
  );
  const [target, setTarget] = useState(targets.includes(clubId) ? clubId : targets[0]);
  const [catalog, setCatalog] = useState<any[]>(GIFTS);
  const [sendingCode, setSendingCode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/gifts/catalog")
      .then((res) => {
        if (!cancelled && Array.isArray(res.data) && res.data.length > 0) {
          const items = res.data.map((item: any) => ({
            code: item.gift_key || item.key || item.code,
            name: item.display_name || item.name,
            cost: Number(item.cost_amount ?? item.fancoin_price ?? item.amount_fancoin ?? item.cost) || 10,
            rarity: item.rarity || "common",
            anim: item.animation_key,
            animation_key: item.animation_key,
            sound_key: item.sound_key,
            duration_ms: item.duration_ms,
          }));
          setCatalog(items);
        }
      })
      .catch(() => {
        // Fallback to static catalog on offline / error
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!targets.length) return null;

  const send = async (g: any) => {
    if (sendingCode) return;
    setSendingCode(g.code);
    const idempotencyKey =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `gift-${match.id}-${g.code}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    try {
      let data: any;
      try {
        const res = await api.post("/gifts/send", {
          recipient_club_id: target,
          gift_key: g.code,
          match_id: match.id,
          quantity: 1,
          source_scope: "gtex_competition",
          idempotency_key: idempotencyKey,
        });
        data = res.data;
      } catch (err: any) {
        const status = err?.response?.status;
        if (status && ![404, 405].includes(status)) {
          throw err;
        }
        // Fallback to legacy owner endpoint only when canonical endpoint is absent (404/405 or test mock)
        const res = await api.post("/owner/gifts/send", {
          club_id: target,
          gift_code: g.code,
          match_id: match.id,
          idempotency_key: idempotencyKey,
        });
        data = res.data;
      }

      const senderName = data.sender_display_name || data.sender || "You";
      const txId = data.id || data.transaction_id || idempotencyKey;
      setFeed((f) => [`${senderName} sent ${g.name}`, ...f].slice(0, 5));
      refresh();
      const broadcast = data.broadcast || data.animation_payload || {};
      onGiftSent?.({
        id: txId,
        sender: senderName,
        name: g.name,
        gift_name: g.name,
        code: g.code,
        gift_code: g.code,
        amount: g.cost,
        rarity: data.rarity || broadcast.rarity || g.rarity || "common",
        anim: data.animation_key || broadcast.animation_key || g.anim || g.code,
        animation_key: data.animation_key || broadcast.animation_key || g.animation_key || g.anim || g.code,
        sound_key: data.sound_key || broadcast.sound_key || g.sound_key,
        duration_ms: data.duration_ms || broadcast.duration_ms || g.duration_ms,
        combo_count: data.combo_count || broadcast.combo_count || 1,
      });
      toast.success(`Gift sent: ${g.name}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSendingCode(null);
    }
  };

  return (
    <Panel eyebrow="Gift rail · Fan Coin" title="Back your club" testid="gift-rail">
      {targets.length > 1 && (
        <select data-testid="gift-target-select" className="gx-input mb-3" value={target} onChange={(e) => setTarget(e.target.value)}>
          {targets.map((t: string) => (
            <option key={t} value={t}>
              {t === match.home_club_id ? match.home_name : match.away_name}
            </option>
          ))}
        </select>
      )}
      <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto pr-1">
        {catalog.map((g) => (
          <button
            key={g.code}
            data-testid={`gift-${g.code}`}
            onClick={() => send(g)}
            className="rounded-sm border border-amber-500/20 bg-amber-500/[0.04] px-3 py-2 text-left text-xs transition-colors hover:border-amber-400/60 hover:bg-amber-500/10"
          >
            <span className="block font-semibold text-amber-200 truncate">{g.name}</span>
            <span className="gx-mono text-[10px] text-slate-400">{g.cost} FAN</span>
          </button>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-slate-500">70% goes to the club, 30% platform. Gifts never interrupt the match feed.</p>
      {feed.map((f, i) => (
        <p key={i} className="mt-1 text-xs text-amber-300">
          {f}
        </p>
      ))}
    </Panel>
  );
}

function Momentum({ values, upto }: any) {
  return (
    <div className="flex h-16 items-end gap-0.5" data-testid="momentum-bar">
      {values.map((v: number, i: number) => (
        <div key={i} className="flex flex-1 flex-col justify-end">
          <div
            className={`rounded-t-[1px] transition-[height] duration-500 ${
              i * 5 <= upto ? (v >= 50 ? "bg-emerald-400" : "bg-cyan-500") : "bg-white/5"
            }`}
            style={{ height: `${i * 5 <= upto ? Math.abs(v - 50) * 1.8 + 6 : 6}%` }}
          />
        </div>
      ))}
    </div>
  );
}

function OwnerView({ view }: any) {
  if (!view) return null;
  return (
    <Panel eyebrow="Post-match · owner view" title={view.headline} testid="post-match-narrative">
      <p className="mb-4 flex items-start gap-2 text-sm italic text-slate-300">
        <Megaphone size={16} className="mt-0.5 shrink-0 text-emerald-400" />
        {view.manager_reaction}
      </p>
      <p className="gx-label">Why it happened</p>
      <div className="mb-4 grid grid-cols-2 gap-2">
        {view.why.map((w: any) => (
          <div key={w.factor} className="rounded-sm border border-white/5 p-2 text-xs">
            <p className="text-slate-500">{w.factor}</p>
            <p
              className={`gx-mono font-semibold ${
                w.impact === "positive" ? "text-emerald-300" : w.impact === "negative" ? "text-red-300" : "text-slate-200"
              }`}
            >
              {w.value}
            </p>
          </div>
        ))}
      </div>
      <p className="gx-label">What you can do next</p>
      <ul className="space-y-1 text-sm text-slate-300">
        {view.next_actions.map((a: string) => (
          <li key={a} className="flex gap-2">
            <Lightbulb size={14} className="mt-0.5 text-amber-400" />
            {a}
          </li>
        ))}
      </ul>
      {view.revenue_notes?.length > 0 && (
        <p className="mt-3 text-xs text-slate-500">Revenue: {view.revenue_notes.join(" · ")}. Sponsor income is split 70/30.</p>
      )}
    </Panel>
  );
}

// Tactical HUD & Advisor Panel
function TacticalHUD({
  formation,
  setFormation,
  press,
  setPress,
  line,
  setLine,
  tempo,
  setTempo,
  risk,
  setRisk,
  onApplyPreset,
  matchId,
  minute,
  homeScore,
  awayScore,
  side,
  bench = [],
  starters = [],
}: {
  formation: string;
  setFormation: (f: string) => void;
  press: number;
  setPress: (v: number) => void;
  line: number;
  setLine: (v: number) => void;
  tempo: number;
  setTempo: (v: number) => void;
  risk: number;
  setRisk: (v: number) => void;
  onApplyPreset: (p: any) => void;
  matchId: string;
  minute: number;
  homeScore: number;
  awayScore: number;
  side: "home" | "away";
  bench?: Array<{ player_id?: string; name?: string; shirt_number?: number }>;
  starters?: Array<{ player_id?: string; name?: string; shirt_number?: number }>;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [advisorApplied, setAdvisorApplied] = useState(false);
  const [outPlayerId, setOutPlayerId] = useState("");
  const [inPlayerId, setInPlayerId] = useState("");
  const myScore = side === "away" ? awayScore : homeScore;
  const theirScore = side === "away" ? homeScore : awayScore;

  // Compute Assistant Manager Coach Karl's dynamic live advice
  const advisor = useMemo(() => {
    if (minute >= 75 && myScore > theirScore) {
      return {
        situation: `Lead Protection (${myScore}-${theirScore} · ${minute}')`,
        recommendation: "Opponent is overloading wide channels. Drop into Low Block 5-3-2 with counter outlet.",
        buttonText: "APPLY LOW BLOCK LOCKDOWN",
        preset: TACTICAL_PRESETS.find((p) => p.name === "LOW BLOCK"),
        color: "text-blue-400",
      };
    } else if (minute >= 60 && myScore < theirScore) {
      return {
        situation: `Goal Deficit (${myScore}-${theirScore} · ${minute}')`,
        recommendation: "Need an equalizer. Shift into Gegenpress 4-2-4 with aggressive pressing line.",
        buttonText: "APPLY GEGENPRESS OVERLOAD",
        preset: TACTICAL_PRESETS.find((p) => p.name === "GEGENPRESS"),
        color: "text-rose-400",
      };
    } else if (myScore < theirScore) {
      return {
        situation: `Trailing (${myScore}-${theirScore} · ${minute}')`,
        recommendation: "Opponent high line leaves space in behind. Quick Counter 3-4-3 will catch them.",
        buttonText: "APPLY COUNTER ATTACK",
        preset: TACTICAL_PRESETS.find((p) => p.name === "COUNTER"),
        color: "text-amber-400",
      };
    } else {
      return {
        situation: `Tactical Parity (${myScore}-${theirScore} · ${minute}')`,
        recommendation: "Midfield contest is balanced. Tiki-Taka 4-3-3 will retain possession and control rhythm.",
        buttonText: "APPLY POSSESSION CONTROL",
        preset: TACTICAL_PRESETS.find((p) => p.name === "TIKI-TAKA"),
        color: "text-emerald-400",
      };
    }
  }, [minute, myScore, theirScore]);

  const dispatchInstruction = async () => {
    setSubmitting(true);
    try {
      await api.post(`/matches/${matchId}/tactics`, {
        press_intensity: press,
        defensive_line: line,
        tempo: tempo,
        risk_level: risk,
        formation: formation,
        side,
      });
      toast.success(`Tactical order dispatched: ${formation} · Press ${press}% · Line ${line}%`);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Tactical adjustment rejected";
      toast.error(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Panel eyebrow="Live Tactical Center" title="Tactics & Assistant Manager" testid="tactics-panel">
      {/* Assistant Manager Advice Banner */}
      <div className="mb-5 rounded-md border border-white/10 bg-slate-900/90 p-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
              <Zap size={12} />
            </span>
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-300">
              COACH KARL · ASSISTANT MANAGER ADVICE
            </span>
          </div>
          <span className={`text-[10px] font-bold ${advisor.color}`}>{advisor.situation}</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-300">{advisor.recommendation}</p>
        <button
          disabled={submitting}
          onClick={async () => {
            const preset = advisor.preset;
            if (!preset) return;
            onApplyPreset(preset);
            const mentality = String(preset.mentality || "balanced").trim().toLowerCase().replace(/\s+/g, "_");
            const accepted =
              mentality === "counter" ? "attacking" : mentality === "ultra_attacking" ? "attacking" : mentality;
            setSubmitting(true);
            try {
              await api.post(`/matches/${matchId}/tactics`, {
                press_intensity: preset.press,
                defensive_line: preset.line,
                tempo: preset.tempo,
                risk_level: preset.risk,
                formation: preset.formation,
                mentality: accepted,
                side,
              });
              setAdvisorApplied(true);
              toast.success("Coach Karl's order was accepted by the match.");
            } catch (err: any) {
              const msg = err?.response?.data?.detail || err?.message || "Tactical adjustment rejected";
              toast.error(typeof msg === "string" ? msg : JSON.stringify(msg));
            } finally {
              setSubmitting(false);
            }
          }}
          className={`mt-3 flex w-full items-center justify-center gap-1.5 rounded-sm py-2 text-xs font-black uppercase tracking-wider transition-colors ${
            advisorApplied
              ? "border border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              : "bg-emerald-500 text-slate-950 hover:bg-emerald-400"
          }`}
        >
          {advisorApplied ? (
            <>
              <CheckCircle2 size={13} /> ADVICE APPLIED TO BOARD
            </>
          ) : (
            <>
              <Sparkles size={13} /> {advisor.buttonText}
            </>
          )}
        </button>
      </div>

      {/* 5 Tactical Style Presets */}
      <p className="gx-label mb-2">Tactical Style Presets</p>
      <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {TACTICAL_PRESETS.map((p) => (
          <button
            key={p.name}
            onClick={() => {
              onApplyPreset(p);
              toast.info(`Preset selected: ${p.name}`);
            }}
            className="flex flex-col rounded-sm border border-white/10 bg-white/[0.02] p-2.5 text-left transition-all hover:border-emerald-500/40 hover:bg-white/[0.05]"
          >
            <span className="text-xs font-black tracking-wide text-white">{p.name}</span>
            <span className="text-[10px] text-slate-400">{p.tagline}</span>
            <span className="gx-mono mt-1 text-[9px] font-bold text-emerald-400">{p.formation}</span>
          </button>
        ))}
      </div>

      {/* Formation Selector */}
      <div className="mb-4">
        <label className="gx-label">Base Formation</label>
        <select
          value={formation}
          onChange={(e) => setFormation(e.target.value)}
          className="gx-input w-full font-mono font-bold text-emerald-300"
        >
          <option value="4-3-3">4-3-3 (Attack / Positional)</option>
          <option value="4-2-4">4-2-4 (High Press Overload)</option>
          <option value="5-3-2">5-3-2 (Defensive Stability)</option>
          <option value="3-4-3">3-4-3 (Wide Wing-Backs)</option>
        </select>
      </div>

      {/* Tactical Sliders */}
      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Pressing Intensity</span>
            <span className="gx-mono font-bold text-emerald-400">{press}%</span>
          </div>
          <input
            type="range"
            min="10"
            max="100"
            value={press}
            onChange={(e) => setPress(Number(e.target.value))}
            className="w-full accent-emerald-500"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Defensive Line Height</span>
            <span className="gx-mono font-bold text-cyan-400">{line}%</span>
          </div>
          <input
            type="range"
            min="10"
            max="100"
            value={line}
            onChange={(e) => setLine(Number(e.target.value))}
            className="w-full accent-cyan-500"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Passing Tempo</span>
            <span className="gx-mono font-bold text-amber-400">{tempo}%</span>
          </div>
          <input
            type="range"
            min="10"
            max="100"
            value={tempo}
            onChange={(e) => setTempo(Number(e.target.value))}
            className="w-full accent-amber-500"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Risk & Creativity</span>
            <span className="gx-mono font-bold text-rose-400">{risk}%</span>
          </div>
          <input
            type="range"
            min="10"
            max="100"
            value={risk}
            onChange={(e) => setRisk(Number(e.target.value))}
            className="w-full accent-rose-500"
          />
        </div>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Player off
          <select
            value={outPlayerId}
            onChange={(event) => setOutPlayerId(event.target.value)}
            className="gx-input mt-1 w-full"
          >
            <option value="">Select starter</option>
            {starters.map((player) => (
              <option key={player.player_id} value={player.player_id}>
                {player.shirt_number} {player.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Player on
          <select
            value={inPlayerId}
            onChange={(event) => setInPlayerId(event.target.value)}
            className="gx-input mt-1 w-full"
          >
            <option value="">Select bench</option>
            {bench.map((player) => (
              <option key={player.player_id} value={player.player_id}>
                {player.shirt_number} {player.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <button
        type="button"
        disabled={submitting || !outPlayerId || !inPlayerId}
        onClick={async () => {
          setSubmitting(true);
          try {
            await api.post(`/matches/${matchId}/tactics`, {
              side,
              substitutions: [{ out_player_id: outPlayerId, in_player_id: inPlayerId }],
            });
            toast.success("Substitution sent to the match.");
          } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || "Substitution rejected";
            toast.error(typeof msg === "string" ? msg : JSON.stringify(msg));
          } finally {
            setSubmitting(false);
          }
        }}
        className="mt-3 w-full rounded-sm border border-white/15 py-2 text-xs font-black uppercase tracking-wider text-slate-200 disabled:opacity-40"
      >
        Send substitution
      </button>

      {/* Dispatch Button */}
      <button
        onClick={dispatchInstruction}
        disabled={submitting}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-sm bg-emerald-500 py-2.5 text-xs font-black tracking-wider text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
      >
        <Sliders size={14} /> {submitting ? "TRANSMITTING..." : "DISPATCH INSTRUCTION TO DUGOUT"}
      </button>
    </Panel>
  );
}

// Pre-Match Briefing Component with Strategic 3D Stadium & Walkout Stage
function PreMatchBriefing({ match, preMatch, matchId }: { match: any; preMatch?: any; matchId: string }) {
  const [pollVote, setPollVote] = useState<string | null>(null);
  const [predictionData, setPredictionData] = useState<any>(preMatch?.fan_predictions);
  const [preMatch3DScene, setPreMatch3DScene] = useState<Cinema3DSceneType>("facility_upgrade");

  const { data: initialPreds } = useQuery({
    queryKey: ["predictions", matchId],
    queryFn: async () => (await api.get(`/matches/${matchId}/predictions`)).data,
    initialData: preMatch?.fan_predictions,
    enabled: !!matchId,
  });

  const preds = predictionData || initialPreds || preMatch?.fan_predictions;
  const totalVotes = preds?.total_votes ?? 0;

  const handleVote = async (choiceKey: "home" | "draw" | "away", optLabel: string) => {
    try {
      const res = await api.post(`/matches/${matchId}/predictions`, { choice: choiceKey });
      setPollVote(optLabel);
      setPredictionData(res.data);
      toast.success(`Vote logged: ${optLabel}`);
    } catch (err: any) {
      if (err?.response?.status === 409) {
        setPollVote(optLabel);
        toast.info("Your vote has already been submitted for this match.");
      } else {
        toast.error(errMsg(err));
      }
    }
  };

  const rawKeyDuel = preMatch?.key_duel;
  const keyDuel =
    rawKeyDuel && rawKeyDuel.available !== false
      ? {
          home_player:
            rawKeyDuel.home_player ??
            (rawKeyDuel.home_player_name
              ? {
                  id: rawKeyDuel.home_player_id,
                  name: rawKeyDuel.home_player_name,
                  role: rawKeyDuel.home_player_role,
                  shirt_number: rawKeyDuel.home_player_shirt_number,
                  rating: rawKeyDuel.home_player_rating,
                }
              : null),
          away_player:
            rawKeyDuel.away_player ??
            (rawKeyDuel.away_player_name
              ? {
                  id: rawKeyDuel.away_player_id,
                  name: rawKeyDuel.away_player_name,
                  role: rawKeyDuel.away_player_role,
                  shirt_number: rawKeyDuel.away_player_shirt_number,
                  rating: rawKeyDuel.away_player_rating,
                }
              : null),
        }
      : null;
  const homeForm: string[] = preMatch?.home_form || [];
  const awayForm: string[] = preMatch?.away_form || [];

  return (
    <div className="space-y-6">
      {/* Official Broadcast Starting XIs (Tunnel Graphic + Editorial Matchday Poster) */}
      <Panel
        eyebrow="Official Matchday Team Sheets"
        title="Confirmed Starting XIs & Lineup Suggestion"
        testid="pre-match-lineups-panel"
      >
        <MatchdayLineupBroadcast
          homeClubId={match.home_club_id}
          homeClubName={match.home_name}
          awayClubId={match.away_club_id}
          awayClubName={match.away_name}
          competitionName="GTEX MATCHDAY LIVE"
          matchdayNumber={match.round || 1}
          defaultView="dual"
        />
      </Panel>

      {/* Strategic Pre-Match 3D Broadcast Showcase: Stadium Flyover / Walkout Tunnel / Trophy Plinth */}
      <Panel eyebrow="3D Broadcast Pre-Match Show" title="Stadium Cathedral & Tunnel Walkout Stage">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-slate-400">
            Interactive 3D pre-match inspection: orbit the stadium bowl, inspect kit liveries in the walkout tunnel, or preview the matchday silverware.
          </p>
          <div className="flex items-center gap-1.5">
            {[
              { id: "facility_upgrade" as Cinema3DSceneType, label: "3D STADIUM FLYOVER" },
              { id: "signing_walkout" as Cinema3DSceneType, label: "3D TUNNEL WALKOUT" },
              { id: "competition_final" as Cinema3DSceneType, label: "3D TROPHY PLINTH" },
            ].map((s) => (
              <button
                key={s.id}
                onClick={() => setPreMatch3DScene(s.id)}
                className={`rounded-sm px-2.5 py-1 text-[10px] font-black tracking-wider transition-all ${
                  preMatch3DScene === s.id
                    ? "border border-emerald-400 bg-emerald-500/20 text-emerald-300"
                    : "border border-white/10 bg-white/5 text-slate-400 hover:text-white"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <Cinema3DStage
          scene={preMatch3DScene}
          title={
            preMatch3DScene === "facility_upgrade"
              ? `${match.home_name} STADIUM BOWL`
              : preMatch3DScene === "signing_walkout"
              ? `${keyDuel?.home_player?.name || "VICTOR OSIMHEN"} #9`
              : `${match.home_name} VS ${match.away_name}`
          }
          subtitle="Pre-Match 3D Broadcast Inspection · Drag 360° or Toggle Director Cut"
          badgeText="PRE-MATCH 3D STAGE"
          clubName={match.home_name}
          compact
        />
      </Panel>

      {/* Win Probability & Fan Poll */}
      <Panel eyebrow="Match Intelligence" title="Win Probability & Predictions" testid="pre-match-poll">
        <div className="mb-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-sm border border-emerald-500/20 bg-emerald-500/5 p-3">
            <span className="text-slate-400">{match.home_name}</span>
            <p className="gx-display text-2xl font-black text-emerald-400">
              {totalVotes > 0 ? `${preds.home_win_pct}%` : "—"}
            </p>
          </div>
          <div className="rounded-sm border border-slate-500/20 bg-slate-500/5 p-3">
            <span className="text-slate-400">Draw</span>
            <p className="gx-display text-2xl font-black text-slate-300">
              {totalVotes > 0 ? `${preds.draw_pct}%` : "—"}
            </p>
          </div>
          <div className="rounded-sm border border-amber-500/20 bg-amber-500/5 p-3">
            <span className="text-slate-400">{match.away_name}</span>
            <p className="gx-display text-2xl font-black text-amber-400">
              {totalVotes > 0 ? `${preds.away_win_pct}%` : "—"}
            </p>
          </div>
        </div>

        <div className="mb-2 flex items-center justify-between">
          <p className="gx-label mb-0">Fan Matchday Vote</p>
          <span className="gx-mono text-[10px] text-slate-500">
            {totalVotes > 0 ? `${totalVotes} verified fan votes` : "Awaiting first verified votes"}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { key: "home" as const, label: "HOME WIN" },
            { key: "draw" as const, label: "DRAW" },
            { key: "away" as const, label: "AWAY WIN" },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleVote(key, label)}
              className={`rounded-sm py-2 text-xs font-bold transition-colors ${
                pollVote === label
                  ? "border border-emerald-500 bg-emerald-500/20 text-emerald-300"
                  : "border border-white/10 bg-white/[0.02] text-slate-300 hover:border-white/30"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Real Competition Form */}
        <div className="mt-4 border-t border-white/5 pt-3">
          <p className="gx-label mb-2">Recent Competition Form</p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-sm border border-white/5 bg-slate-900/40 p-2">
              <span className="text-[10px] text-slate-400">{match.home_name}</span>
              <div className="mt-1 flex gap-1">
                {homeForm.length > 0 ? (
                  homeForm.map((f, i) => (
                    <span
                      key={i}
                      className={`flex h-5 w-5 items-center justify-center rounded-xs text-[10px] font-bold ${
                        f === "W"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : f === "D"
                          ? "bg-slate-500/20 text-slate-300"
                          : "bg-red-500/20 text-red-300"
                      }`}
                    >
                      {f}
                    </span>
                  ))
                ) : (
                  <span className="text-[10px] italic text-slate-500">No prior fixtures recorded</span>
                )}
              </div>
            </div>
            <div className="rounded-sm border border-white/5 bg-slate-900/40 p-2">
              <span className="text-[10px] text-slate-400">{match.away_name}</span>
              <div className="mt-1 flex gap-1">
                {awayForm.length > 0 ? (
                  awayForm.map((f, i) => (
                    <span
                      key={i}
                      className={`flex h-5 w-5 items-center justify-center rounded-xs text-[10px] font-bold ${
                        f === "W"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : f === "D"
                          ? "bg-slate-500/20 text-slate-300"
                          : "bg-red-500/20 text-red-300"
                      }`}
                    >
                      {f}
                    </span>
                  ))
                ) : (
                  <span className="text-[10px] italic text-slate-500">No prior fixtures recorded</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* Key Player Duel */}
      <Panel eyebrow="Scouting Report" title="Key Player Head-to-Head Duel" testid="player-duel">
        {keyDuel?.home_player && keyDuel?.away_player ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 rounded-sm border border-emerald-500/30 bg-emerald-500/5 p-3 text-center">
                <span className="inline-block rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                  HOME TALISMAN
                </span>
                <p className="mt-1 text-base font-bold text-white">{keyDuel.home_player.name}</p>
                <p className="text-xs text-slate-400">
                  {keyDuel.home_player.role || "Role unavailable"}
                  {keyDuel.home_player.shirt_number ? ` · #${keyDuel.home_player.shirt_number}` : ""}
                </p>
                <div className="mt-2 flex justify-around text-xs">
                  <div>
                    <span className="block text-[10px] text-slate-500">RATING</span>
                    <span className="gx-mono font-bold text-emerald-300">{keyDuel.home_player.rating ?? "N/A"}</span>
                  </div>
                </div>
              </div>
              <HolographicPlayerCard
                name={keyDuel.home_player.name}
                position={keyDuel.home_player.role || "ST"}
                overall={Number(keyDuel.home_player.rating) || 89}
                clubName={match.home_name}
                tier="diamond"
              />
            </div>

            <div>
              <div className="mb-2 rounded-sm border border-amber-500/30 bg-amber-500/5 p-3 text-center">
                <span className="inline-block rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                  AWAY DANGERMAN
                </span>
                <p className="mt-1 text-base font-bold text-white">{keyDuel.away_player.name}</p>
                <p className="text-xs text-slate-400">
                  {keyDuel.away_player.role || "Role unavailable"}
                  {keyDuel.away_player.shirt_number ? ` · #${keyDuel.away_player.shirt_number}` : ""}
                </p>
                <div className="mt-2 flex justify-around text-xs">
                  <div>
                    <span className="block text-[10px] text-slate-500">RATING</span>
                    <span className="gx-mono font-bold text-amber-300">{keyDuel.away_player.rating ?? "N/A"}</span>
                  </div>
                </div>
              </div>
              <HolographicPlayerCard
                name={keyDuel.away_player.name}
                position={keyDuel.away_player.role || "RW"}
                overall={Number(keyDuel.away_player.rating) || 88}
                clubName={match.away_name}
                tier="gold"
              />
            </div>
          </div>
        ) : (
          <p className="p-3 text-center text-xs italic text-slate-500">
            Player duels and tactical matchups will be evaluated once official lineups are finalized.
          </p>
        )}
      </Panel>
    </div>
  );
}

// Post-Match Analytics & Press Room Component with 3D MOTM Gala & 3D Press Conference Studio
function PostMatchAnalytics({
  match,
  postMatch,
  stats,
  matchId,
  homeScore,
  awayScore,
  clubId,
}: {
  match: any;
  postMatch?: any;
  stats?: any;
  matchId: string;
  homeScore: number;
  awayScore: number;
  clubId?: string;
}) {
  const [pressAnswers, setPressAnswers] = useState<Record<number, number>>({});
  const [submittingPress, setSubmittingPress] = useState(false);
  const [rewardsClaimed, setRewardsClaimed] = useState(false);
  const [claimingRewards, setClaimingRewards] = useState(false);
  const [show3DMotmStage, setShow3DMotmStage] = useState(true);
  const motm = postMatch?.motm;
  const shotMap: Array<{
    minute: number;
    is_home: boolean;
    x: number;
    y: number;
    xg: number;
    outcome: string;
    player_name?: string;
  }> = postMatch?.shot_map || [];

  const homeXgRaw = stats?.home_expected_goals ?? postMatch?.xg?.home;
  const awayXgRaw = stats?.away_expected_goals ?? postMatch?.xg?.away;
  const homeXg = homeXgRaw === null || homeXgRaw === undefined || !Number.isFinite(Number(homeXgRaw)) ? null : Number(homeXgRaw);
  const awayXg = awayXgRaw === null || awayXgRaw === undefined || !Number.isFinite(Number(awayXgRaw)) ? null : Number(awayXgRaw);

  const claimRewards = async () => {
    setClaimingRewards(true);
    try {
      const res = await api.post(`/matches/${matchId}/rewards/claim`);
      setRewardsClaimed(true);
      if (res.data?.status === "already_claimed") {
        toast.info("Matchday settlement rewards were already claimed for this fixture.");
      } else {
        const amount = res.data?.talent_coin ?? res.data?.net_amount;
        toast.success(
          amount === undefined || amount === null
            ? "Match reward was settled to your wallet."
            : `Match reward settled: ${amount} $TALENT.`,
        );
      }
    } catch (err: any) {
      toast.error(errMsg(err));
    } finally {
      setClaimingRewards(false);
    }
  };

  const questions = [
    {
      outlet: "THE ATHLETIC · TACTICAL DESK",
      journalist: "Samir Croft",
      q: "Manager, your side adapted rapidly during high-intensity sequences. What was your key tactical directive?",
      opts: [
        { text: '"We instructed our fullbacks to invert and create central superiority."', effect: "+15 TACTICS · +10 BOARD", tone: "tactical" },
        { text: '"The squad adapted to the tempo flawlessly. Pure collective discipline."', effect: "+20 MORALE · +10 CHEMISTRY", tone: "inspirational" },
        { text: '"We remained pragmatic and exploited defensive transition errors."', effect: "+12 PRAGMATISM", tone: "pragmatic" },
      ],
    },
    {
      outlet: "SKY SPORTS FOOTBALL",
      journalist: "Laura Evans",
      q: "The fans generated a tremendous roar. How crucial was that stadium atmosphere today?",
      opts: [
        { text: '"This result belongs to our supporters. They pushed us across the line."', effect: "+25 FAN APPROVAL", tone: "fan_focused" },
        { text: '"Professional job. We enjoy tonight and resume work at 8 AM tomorrow."', effect: "+15 STANDARDS", tone: "disciplined" },
        { text: '"Every match demands this intensity. We are raising the bar."', effect: "+18 DETERMINATION", tone: "ambitious" },
      ],
    },
  ];

  const submitPressConference = async (qIdx: number, optIdx: number, opt: any) => {
    setPressAnswers((prev) => ({ ...prev, [qIdx]: optIdx }));
    setSubmittingPress(true);
    try {
      if (clubId) {
        await api.post(`/owner/clubs/${clubId}/press-conference`, {
          match_id: matchId,
          statement: opt.text,
          tone: opt.tone || "confident",
        });
        toast.success(`Published to GTEX Wire: ${opt.effect}`);
      } else {
        toast.success(`Statement noted: ${opt.text}`);
      }
    } catch (err: any) {
      toast.error(errMsg(err));
    } finally {
      setSubmittingPress(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* MOTM Celebration + 3D MOTM Trophy Pedestal */}
      <Panel eyebrow="Full-time Honors" title="Player of the Match" testid="motm-card">
        <div className="mb-3 flex justify-end">
          <button
            onClick={() => setShow3DMotmStage(!show3DMotmStage)}
            className="rounded-sm border border-amber-400/40 bg-amber-500/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-amber-300 hover:bg-amber-500/20"
          >
            {show3DMotmStage ? "HIDE 3D MOTM GALA PEDESTAL" : "SHOW 3D MOTM GALA PEDESTAL"}
          </button>
        </div>

        {show3DMotmStage && (
          <div className="mb-4 overflow-hidden rounded-lg">
            <Cinema3DStage
              scene="world_gala"
              title={motm?.player_name || "VICTOR OSIMHEN"}
              subtitle={`${motm?.team_name || match.home_name} · Official Man of the Match Honors`}
              badgeText="3D MOTM TROPHY PLINTH"
              subjectName={motm?.player_name || "VICTOR OSIMHEN"}
              overallRating={motm?.rating ? Number(motm.rating).toFixed(1) : "9.2"}
              clubName={motm?.team_name || match.home_name}
              compact
            />
          </div>
        )}

        {motm?.available === true ? (
          <div className="flex items-center justify-between rounded-md border border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-slate-900 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-amber-400 bg-amber-500 text-lg font-black text-slate-950">
                #{motm.shirt_number ?? "—"}
              </div>
              <div>
                <p className="text-sm font-black text-amber-300">{motm.player_name}</p>
                <p className="text-xs text-slate-400">
                  {motm.team_name || "Team unavailable"} · {motm.goals} Goal{motm.goals === 1 ? "" : "s"} · {motm.assists ?? "N/A"} Assist{motm.assists === 1 ? "" : "s"}
                </p>
                {motm.summary && <p className="mt-1 text-[11px] text-slate-300">{motm.summary}</p>}
              </div>
            </div>
            <div className="text-right">
              <span className="rounded-sm bg-amber-500 px-2 py-0.5 text-xs font-black text-slate-950">
                {motm.rating === null || motm.rating === undefined ? "RATING N/A" : `${Number(motm.rating).toFixed(1)} RATING`}
              </span>
              <p className="mt-1 text-[10px] text-amber-200">{motm.pass_acc === null || motm.pass_acc === undefined ? "Pass accuracy N/A" : `${motm.pass_acc}% Pass Acc`}</p>
            </div>
          </div>
        ) : (
          <p className="p-4 text-center text-xs text-slate-500">Player of the match evaluation pending.</p>
        )}
      </Panel>

      {/* Interactive xG Shot Map with Trajectory Vectors */}
      <Panel eyebrow="Spatial Analytics" title="Expected Goals (xG) Shot Map" testid="shot-map">
        <div className="relative aspect-[16/9] w-full overflow-hidden rounded-md border border-white/10 bg-[#0B2014] p-3">
          <svg className="h-full w-full" viewBox="0 0 1000 560">
            <rect width="1000" height="560" fill="#0D2818" />
            <rect x="20" y="20" width="960" height="520" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.3" />
            <line x1="500" y1="20" x2="500" y2="540" stroke="#FFFFFF" strokeWidth="2" opacity="0.3" />
            <circle cx="500" cy="280" r="70" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.3" />
            <rect x="20" y="130" width="140" height="300" fill="none" stroke="#FFFFFF" strokeWidth="1.5" opacity="0.25" />
            <rect x="840" y="130" width="140" height="300" fill="none" stroke="#FFFFFF" strokeWidth="1.5" opacity="0.25" />

            {/* Shots + Shot Vectors */}
            {shotMap.length > 0 ? (
              shotMap.map((s, idx) => {
                const cx = s.x * 1000;
                const cy = s.y * 560;
                const isGoal = s.outcome === "goal";
                const isSaved = s.outcome === "saved";
                const color = isGoal ? "#00E87A" : isSaved ? "#60A5FA" : "#F87171";
                const r = isGoal ? 14 : Math.max(7, Math.min(13, (s.xg || 0.15) * 20));
                const goalX = s.is_home ? 980 : 20;
                const goalY = 280;
                return (
                  <g key={`shot-${idx}`} className="cursor-pointer">
                    <line
                      x1={cx}
                      y1={cy}
                      x2={goalX}
                      y2={goalY}
                      stroke={color}
                      strokeWidth={isGoal ? "2" : "1.2"}
                      strokeDasharray={isGoal ? "none" : "4 4"}
                      opacity="0.55"
                    />
                    <circle cx={cx} cy={cy} r={r} fill={color} stroke="#FFFFFF" strokeWidth={isGoal ? 2 : 1.5} />
                    {isGoal && (
                      <text x={cx} y={cy + 4} textAnchor="middle" fill="#000" fontSize="11" fontWeight="bold">
                        ⚽
                      </text>
                    )}
                  </g>
                );
              })
            ) : (
              <text x="500" y="280" textAnchor="middle" fill="#94A3B8" fontSize="13" fontStyle="italic">
                No shot events recorded in this match (0.00 xG)
              </text>
            )}
          </svg>
          <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex gap-3">
              <span className="flex items-center gap-1 text-emerald-400">● Goal</span>
              <span className="flex items-center gap-1 text-blue-400">● Saved</span>
              <span className="flex items-center gap-1 text-red-400">● Missed</span>
            </div>
            <span className="gx-mono font-bold text-white">
              xG: {homeXg === null ? "N/A" : homeXg.toFixed(2)} vs {awayXg === null ? "N/A" : awayXg.toFixed(2)}
            </span>
          </div>
        </div>
      </Panel>

      {/* Simulated Media Reaction + 3D Press Room Studio Toggle */}
      <Panel eyebrow="AI Simulation · Press Room" title="Simulated Media Reaction (Press Room Briefing)" testid="press-conference">
        <div className="mb-4">
          <PressRoomStage
            clubName={match.home_name}
            scoreLine={`FT ${homeScore} - ${awayScore}`}
          />
        </div>

        <div className="space-y-4">
          {questions.map((q, qIdx) => (
            <div key={qIdx} className="rounded-sm border border-white/10 bg-slate-900/60 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-blue-400">{q.outlet}</span>
                <span className="text-[10px] text-slate-500">{q.journalist}</span>
              </div>
              <p className="mt-1 text-xs italic text-slate-200">{q.q}</p>
              <div className="mt-3 space-y-1.5">
                {q.opts.map((opt, optIdx) => (
                  <button
                    key={optIdx}
                    disabled={submittingPress}
                    onClick={() => submitPressConference(qIdx, optIdx, opt)}
                    className={`flex w-full items-center justify-between rounded-sm px-3 py-2 text-left text-xs transition-colors ${
                      pressAnswers[qIdx] === optIdx
                        ? "border border-emerald-500/50 bg-emerald-500/15 text-white"
                        : "border border-white/5 bg-white/[0.02] text-slate-300 hover:border-white/20"
                    }`}
                  >
                    <span>{opt.text}</span>
                    <span className="gx-mono text-[9px] font-bold text-emerald-400">{opt.effect}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Rewards & Token Settlement */}
      <Panel eyebrow="Progression" title="Matchday XP & Token Settlement" testid="settlement-card">
        <div className="rounded-md border border-amber-500/30 bg-slate-900 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300">Manager Level 14 (+550 XP)</span>
            <span className="gx-mono font-bold text-amber-400">+25 $TALENT Tokens</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div className={`h-full transition-all duration-500 ${rewardsClaimed ? "w-[95%] bg-emerald-400" : "w-[85%] bg-amber-400"}`} />
          </div>
          <button
            onClick={claimRewards}
            disabled={rewardsClaimed || claimingRewards}
            className={`mt-4 flex w-full items-center justify-center gap-1.5 rounded-sm py-2 text-xs font-black uppercase tracking-wider transition-colors ${
              rewardsClaimed
                ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "bg-amber-500 text-slate-950 hover:bg-amber-400 disabled:opacity-50"
            }`}
          >
            {rewardsClaimed ? (
              <>
                <CheckCircle2 size={13} /> REWARDS DEPOSITED TO WALLET
              </>
            ) : claimingRewards ? (
              <>
                <Coins size={13} className="animate-spin" /> CLAIMING SETTLEMENT...
              </>
            ) : (
              <>
                <Coins size={13} /> CLAIM MATCH REWARD
              </>
            )}
          </button>
        </div>
      </Panel>
    </div>
  );
}

export default function MatchCenter() {
  const { active: activeClub } = useActiveClub();
  const refreshOwner = useRefreshOwner();
  const { id } = useParams();
  const [params] = useSearchParams();
  const clubId = params.get("club") || activeClub?.club_id || "";
  const { getModuleView, setModuleView } = useSkin();
  const matchView = getModuleView("match_center");
  // Public matches stay on the 2D pitch until an admin turns match_3d_gameplay on.
  const [view3DBroadcast, setView3DBroadcast] = useState<boolean>(false);
  const { data: clientFlags } = useQuery({
    queryKey: ["client-feature-flags"],
    queryFn: async () => {
      try {
        return (await api.get("/feature-flags/client")).data as { feature_key: string; enabled: boolean }[];
      } catch {
        return [] as { feature_key: string; enabled: boolean }[];
      }
    },
  });
  const match3dEnabled = (clientFlags || []).some((flag) => flag.feature_key === "match_3d_gameplay" && flag.enabled);
  const [isTheatreMode, setIsTheatreMode] = useState<boolean>(
    params.get("theatre") === "1" || params.get("theatre") === "true"
  );

  const modeParam = params.get("mode");
  const durationParam = params.get("duration");
  const showcaseDurationSec = Number(durationParam) > 0 ? Number(durationParam) : 300;
  const viewerQuerySuffix = useMemo(() => {
    const q = new URLSearchParams();
    if (modeParam) q.set("mode", modeParam);
    if (durationParam) q.set("target_duration_seconds", durationParam);
    const qs = q.toString();
    return qs ? `?${qs}` : "";
  }, [modeParam, durationParam]);

  const { data: viewerData, refetch: refetchViewerData } = useQuery({
    queryKey: ["match-viewer", id, modeParam, durationParam],
    queryFn: async () => {
      if (id === "u2a-006-showcase") {
        return await loadFiveMinuteShowcaseFixture(showcaseDurationSec);
      }
      try {
        return (await api.get(`/match-viewer/${id}${viewerQuerySuffix}`)).data;
      } catch {
        return null;
      }
    },
    enabled: !!id,
    retry: false,
  });

  const { data: m, isLoading } = useQuery({
    queryKey: ["match", id, modeParam, durationParam],
    queryFn: async () => {
      if (id === "u2a-006-showcase") {
        const showcase = await loadFiveMinuteShowcaseFixture(showcaseDurationSec);
        if (!showcase) return null;
        return {
          match_id: showcase.match_id,
          id: showcase.match_id,
          home_club_id: showcase.home_team.team_id,
          away_club_id: showcase.away_team.team_id,
          home_name: showcase.home_team.team_name,
          away_name: showcase.away_team.team_name,
          venue_name: showcase.venue_name,
          status: "LIVE",
          round: 1,
          events: showcase.events,
          frames: showcase.frames,
          home_team: showcase.home_team,
          away_team: showcase.away_team,
          duration_seconds: (showcase as any).duration_seconds ?? showcaseDurationSec,
        };
      }
      try {
        return (await api.get(`/owner/matches/${id}`)).data;
      } catch {
        const viewer = (await api.get(`/match-viewer/${id}${viewerQuerySuffix}`)).data;
        if (viewer && viewer.match_id) {
          return {
            match_id: viewer.match_id,
            id: viewer.match_id,
            home_club_id: viewer.home_team?.team_id || "home-club",
            away_club_id: viewer.away_team?.team_id || "away-club",
            home_name: viewer.home_team?.team_name || "Home XI",
            away_name: viewer.away_team?.team_name || "Away XI",
            venue_name: viewer.venue_name || "GTEX National Arena",
            status: "LIVE",
            round: 1,
            events: viewer.events || [],
            frames: viewer.frames || [],
            home_team: viewer.home_team,
            away_team: viewer.away_team,
            duration_seconds: viewer.duration_seconds,
          };
        }
        throw new Error("Match not found");
      }
    },
    enabled: !!id,
  });

  const { data: liveState } = useQuery({
    queryKey: ["match-live-state", id],
    queryFn: async () => {
      try {
        return (await api.get(`/matches/${id}/state`)).data;
      } catch {
        return null;
      }
    },
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const phase = String(data.phase || "").toLowerCase();
      return phase === "completed" ? false : 2500;
    },
    enabled: !!id && id !== "u2a-006-showcase",
    retry: false,
  });

  const { data: appliedTactics } = useQuery({
    queryKey: ["match-applied-tactics", id],
    queryFn: async () => {
      try {
        return (await api.get(`/matches/${id}/tactics`)).data;
      } catch {
        return null;
      }
    },
    refetchInterval: 5000,
    enabled: !!id && id !== "u2a-006-showcase",
    retry: false,
  });
  const authoritativeTactics = useMemo(() => mapAuthoritativeTactics(appliedTactics), [appliedTactics]);
  const isViewerAuthenticated = Boolean(tokens.get());
  const requestSpectatorTicket = useCallback(async (targetMatchId: string): Promise<string | null> => {
    const res = await api.post(`/matches/${encodeURIComponent(targetMatchId)}/spectate-ticket`);
    return res.data?.ticket ?? null;
  }, []);

  // Live Gifting Broadcast Animation Queue (FIFO with Transaction-ID Deduplication)
  const [giftQueue, setGiftQueue] = useState<any[]>([]);
  const seenGiftIdsRef = useRef<Set<string>>(new Set());
  const activeGift = giftQueue[0] ?? null;

  const enqueueGift = useCallback((rawGift: any) => {
    if (!rawGift) return;
    const giftCode = rawGift.gift_code || rawGift.gift_key || rawGift.code || "stadium_roar";
    const sender = rawGift.sender_display_name || rawGift.sender || "Supporter";
    const amount = rawGift.amount ?? rawGift.cost ?? 10;
    const dedupKey = String(
      rawGift.id ||
        rawGift.transaction_id ||
        rawGift.idempotency_key ||
        `${sender}-${giftCode}-${amount}-${rawGift.created_at || ""}`
    );
    if (seenGiftIdsRef.current.has(dedupKey)) {
      return;
    }
    seenGiftIdsRef.current.add(dedupKey);
    if (seenGiftIdsRef.current.size > 200) {
      const oldest = seenGiftIdsRef.current.values().next().value;
      if (oldest) seenGiftIdsRef.current.delete(oldest);
    }
    const normalized = {
      id: dedupKey,
      code: giftCode,
      gift_code: giftCode,
      name: rawGift.gift_name || rawGift.name || "Gift Celebration",
      gift_name: rawGift.gift_name || rawGift.name || "Gift Celebration",
      sender,
      recipient: rawGift.recipient_display_name || rawGift.recipient || "Squad",
      cost: amount,
      amount,
      rarity: rawGift.rarity || "common",
      anim: rawGift.animation_key || rawGift.anim || giftCode,
      animation_key: rawGift.animation_key || rawGift.anim || giftCode,
      sound_key: rawGift.sound_key || rawGift.broadcast?.sound_key || rawGift.animation_payload?.sound_key,
      duration_ms: rawGift.duration_ms || rawGift.broadcast?.duration_ms || rawGift.animation_payload?.duration_ms || 4500,
      combo_count: Number(rawGift.combo_count ?? rawGift.broadcast?.combo_count ?? rawGift.animation_payload?.combo_count ?? 1) || 1,
    };
    setGiftQueue((prev) => [...prev, normalized]);
  }, []);

  const handleGiftAnimationComplete = useCallback(() => {
    setGiftQueue((prev) => prev.slice(1));
  }, []);

  // Clock & Playback Controls
  const initialSeekSeconds = Number(params.get("seek") ?? params.get("time") ?? 0);
  const [playbackSeconds, setPlaybackSeconds] = useState(
    Number.isFinite(initialSeekSeconds) && initialSeekSeconds > 0 ? initialSeekSeconds : 0,
  );
  const snapshotVersionRef = useRef(-1);
  const initializedReplayRef = useRef<string>("");
  const [reconnectToken, setReconnectToken] = useState(0);
  const [acceptedLive, setAcceptedLive] = useState<any>(null);

  const spectatorStream = useMatchSpectatorStream({
    matchId: id || "",
    enabled: Boolean(id && id !== "u2a-006-showcase"),
    isAuthenticated: isViewerAuthenticated,
    requestTicket: isViewerAuthenticated ? requestSpectatorTicket : undefined,
    onResyncRequired: () => {
      snapshotVersionRef.current = -1;
      setReconnectToken((value) => value + 1);
      refetchViewerData();
    },
    onGiftReceived: (g: any) => {
      enqueueGift(g);
    },
  });
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState(Number(params.get("speed")) || 1.0);
  const [audioAtmosphere, setAudioAtmosphere] = useState(false);

  // End-whistle -> Owner Authority governance (backend validates completion, ownership and idempotency).
  const isMatchComplete = String(
    spectatorStream.latestScore?.status || acceptedLive?.phase || liveState?.phase || "",
  ).toLowerCase() === "completed";
  useMatchFullTimeGovernance(
    id,
    spectatorStream.recentEvents,
    Boolean(id && id !== "u2a-006-showcase" && isViewerAuthenticated),
    isMatchComplete,
    refreshOwner
  );

  // Active Tab
  const [activeTab, setActiveTab] = useState<"pitch" | "lineups" | "tactics" | "pre_match" | "post_match" | "commentary">("pitch");
  const [showKickoffLineups, setShowKickoffLineups] = useState<boolean>(
    Boolean(params.get("live") && params.get("dismissWalkout") !== "1")
  );

  // Pitch Overlay & Camera Perspective Toggles
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showTactics, setShowTactics] = useState(false);
  const [showLanes, setShowLanes] = useState(false);
  const [showVoronoi, setShowVoronoi] = useState(false);
  const [cameraMode, setCameraMode] = useState<"2d" | "2.5d" | "zoom">("2.5d");
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);
  const [show3DCutIn, setShow3DCutIn] = useState(false);
  useEffect(() => {
    if (!clientFlags) return;
    if (!match3dEnabled) {
      setView3DBroadcast(false);
      setIsTheatreMode(false);
      setShow3DCutIn(false);
      return;
    }
  }, [clientFlags, match3dEnabled]);
  const [cutInScene, setCutInScene] = useState<Cinema3DSceneType>("signing_walkout");

  // Tactics State
  const [formation, setFormation] = useState("4-3-3");
  const [press, setPress] = useState(65);
  const [line, setLine] = useState(68);
  const [tempo, setTempo] = useState(52);
  const [risk, setRisk] = useState(45);

  useEffect(() => {
    const recent = (liveState as any)?.recent_gifts;
    if (Array.isArray(recent) && recent.length > 0) {
      const latest = recent[recent.length - 1];
      enqueueGift(latest);
    }
  }, [liveState, enqueueGift]);

  useEffect(() => {
    if (!liveState) return;
    const version = Number(liveState.snapshot_version ?? 0);
    if (version < snapshotVersionRef.current) return;
    snapshotVersionRef.current = version;
    setAcceptedLive(liveState);
    if (Number.isFinite(Number(liveState.time_seconds)) && !isPaused) {
      setPlaybackSeconds((prev) => Math.max(prev, Number(liveState.time_seconds)));
    }
  }, [liveState, isPaused]);

  useEffect(() => {
    const streamTime = Number(spectatorStream.lastFrame?.time_seconds);
    if (!Number.isFinite(streamTime) || isPaused) return;
    setPlaybackSeconds((prev) => Math.max(prev, streamTime));
  }, [spectatorStream.lastFrame?.time_seconds, isPaused]);

  const recordedFrames = useMemo(
    () => (viewerData?.frames?.length ? viewerData.frames : m?.frames || []),
    [viewerData?.frames, m?.frames],
  );
  const timedRecordedFrames = useMemo<Array<Record<string, any> & { timeSeconds: number; clockMinute: number }>>(
    () =>
      recordedFrames.map((frame: any) => ({
        ...frame,
        timeSeconds: Number(frame?.time_seconds ?? frame?.timeSeconds ?? 0),
        clockMinute: Number(frame?.clock_minute ?? frame?.clockMinute ?? 0),
      })),
    [recordedFrames],
  );
  const replayDurationSeconds = useMemo(() => {
    const lastFrameSec =
      timedRecordedFrames.length > 0
        ? timedRecordedFrames[timedRecordedFrames.length - 1].timeSeconds
        : 0;
    return Math.max(
      lastFrameSec,
      Number(viewerData?.duration_seconds || m?.duration_seconds || 0),
    );
  }, [timedRecordedFrames, viewerData?.duration_seconds, m?.duration_seconds]);

  // Initialize recorded replay clock to the first frame's authoritative time when joining/loading.
  useEffect(() => {
    if (acceptedLive || timedRecordedFrames.length === 0) return;
    const key = `${id || ""}:${timedRecordedFrames.length}:${timedRecordedFrames[0].timeSeconds}`;
    if (initializedReplayRef.current === key) return;
    initializedReplayRef.current = key;
    if (initialSeekSeconds > 0) {
      setPlaybackSeconds(Math.min(replayDurationSeconds || initialSeekSeconds, initialSeekSeconds));
    } else if (timedRecordedFrames[0].timeSeconds > 0) {
      setPlaybackSeconds(timedRecordedFrames[0].timeSeconds);
    }
  }, [id, acceptedLive, timedRecordedFrames, initialSeekSeconds, replayDurationSeconds]);

  // Monotonic wall-clock progression for recorded replays.
  useEffect(() => {
    if (acceptedLive || spectatorStream.lastFrame || isPaused || timedRecordedFrames.length < 2) {
      return undefined;
    }
    let lastTickMs = typeof performance !== "undefined" ? performance.now() : Date.now();
    const timer = window.setInterval(() => {
      const nowMs = typeof performance !== "undefined" ? performance.now() : Date.now();
      const deltaMs = Math.max(0, nowMs - lastTickMs);
      lastTickMs = nowMs;
      setPlaybackSeconds((current) =>
        stepReplayClock({
          currentTimeSeconds: current,
          deltaMs,
          durationSeconds: replayDurationSeconds,
          paused: isPaused,
          speed,
        }),
      );
    }, 50);
    return () => window.clearInterval(timer);
  }, [acceptedLive, spectatorStream.lastFrame, isPaused, timedRecordedFrames.length, replayDurationSeconds, speed]);

  const replayPair = useMemo(
    () =>
      timedRecordedFrames.length > 0
        ? seekTime(timedRecordedFrames, playbackSeconds)
        : { left: null, right: null, t: 0 },
    [timedRecordedFrames, playbackSeconds],
  );
  const activeReplayFrame = useMemo(
    () => (replayPair.t >= 0.5 && replayPair.right ? replayPair.right : replayPair.left),
    [replayPair],
  );

  const homeLivePitch = useMemo(
    () =>
      (
        spectatorStream.lastFrame?.players ||
        acceptedLive?.pitch_players ||
        liveState?.pitch_players ||
        []
      ).filter((p: any) => p.is_home !== false && String(p.side || "home").toLowerCase() !== "away"),
    [spectatorStream.lastFrame, acceptedLive?.pitch_players, liveState?.pitch_players],
  );
  const awayLivePitch = useMemo(
    () =>
      (
        spectatorStream.lastFrame?.players ||
        acceptedLive?.pitch_players ||
        liveState?.pitch_players ||
        []
      ).filter((p: any) => p.is_home === false || String(p.side || "").toLowerCase() === "away"),
    [spectatorStream.lastFrame, acceptedLive?.pitch_players, liveState?.pitch_players],
  );

  const minute = useMemo(() => {
    if (!isPaused && spectatorStream.latestScore?.minute !== undefined) {
      return Math.max(0, Math.round(Number(spectatorStream.latestScore.minute)));
    }
    if (!isPaused && spectatorStream.lastFrame?.clock_minute !== undefined) {
      return Math.max(0, Math.round(Number(spectatorStream.lastFrame.clock_minute)));
    }
    if (acceptedLive?.minute !== undefined) {
      return Math.max(0, Math.round(Number(acceptedLive.minute)));
    }
    if (replayPair.left) {
      const leftMin = Number(replayPair.left.clockMinute ?? 0);
      const rightMin = Number(replayPair.right?.clockMinute ?? leftMin);
      return Math.max(0, Math.round(leftMin + (rightMin - leftMin) * replayPair.t));
    }
    return 0;
  }, [isPaused, spectatorStream.latestScore?.minute, spectatorStream.lastFrame?.clock_minute, acceptedLive?.minute, replayPair]);

  const phaseName = String(
    spectatorStream.latestScore?.status ||
      spectatorStream.lastFrame?.phase ||
      acceptedLive?.phase ||
      liveState?.phase ||
      activeReplayFrame?.phase ||
      "",
  ).toLowerCase();
  // Only the real half-time break counts; "first_half" / "second_half" merely contain the word "half".
  const isHalftime = /^(half_?time|half_time_break|ht|break)$/.test(phaseName.replace(/[\s-]+/g, "_"));
  const matchAds = useMatchCommercialInventory(id, true);

  const shown = useMemo(() => {
    const baseEvents = acceptedLive?.timeline?.length
      ? acceptedLive.timeline
      : acceptedLive?.events?.length
        ? acceptedLive.events
        : viewerData?.events?.length
          ? viewerData.events
          : m?.events || [];
    const streamEvents = spectatorStream.recentEvents || [];
    const combined = [...baseEvents, ...streamEvents];
    const seen = new Set<string>();
    const filtered: any[] = [];
    const isLiveAuthoritative = Boolean(acceptedLive || spectatorStream.lastFrame);
    for (const ev of combined) {
      if (!ev) continue;
      const evMin = Number(ev.minute ?? ev.clock_minute ?? 0);
      const evSec = ev.time_seconds !== undefined ? Number(ev.time_seconds) : null;
      if (!isLiveAuthoritative) {
        if (evSec !== null && Number.isFinite(evSec)) {
          if (evSec > playbackSeconds + 0.05) continue;
        } else if (evMin > minute + 0.2) {
          continue;
        }
      }
      const key = String(
        ev.event_id ||
          ev.id ||
          `${evMin}:${ev.type || ev.event_type || ""}:${ev.team || ev.side || ""}:${ev.text || ev.description || ""}`,
      );
      if (seen.has(key)) continue;
      seen.add(key);
      filtered.push({
        ...ev,
        minute: evMin,
        type: ev.type || ev.event_type,
        team: ev.team || ev.side,
      });
    }
    return filtered;
  }, [acceptedLive, viewerData?.events, m?.events, spectatorStream.recentEvents, spectatorStream.lastFrame, playbackSeconds, minute]);

  const commentary = useMemo(() => {
    const played = timedRecordedFrames;
    const isLiveAuthoritative = Boolean(acceptedLive || spectatorStream.lastFrame);
    const calls = played
      .filter((frame: { overlay_text?: string; clockMinute?: number; timeSeconds?: number }) => {
        if (!frame.overlay_text) return false;
        if (!isLiveAuthoritative && Number.isFinite(frame.timeSeconds)) {
          return Number(frame.timeSeconds) <= playbackSeconds + 0.05;
        }
        return Number(frame.clockMinute || 0) <= minute + 0.2;
      })
      .map((frame: { overlay_text?: string; clockMinute?: number }) => ({
        minute: Math.max(1, Math.round(Number(frame.clockMinute || 0))),
        text: String(frame.overlay_text),
        type: "open_play",
      }));
    const merged: Array<{ minute: number; text?: string; title?: string; description?: string; type?: string }> = [];
    for (const item of [...shown, ...calls].sort((left: { minute: number }, right: { minute: number }) => Number(left.minute) - Number(right.minute))) {
      const text = String(item.text || item.title || item.description || "");
      if (!text) continue;
      if (merged.length && String(merged[merged.length - 1].text || merged[merged.length - 1].title || "") === text) continue;
      merged.push(item);
    }
    return merged;
  }, [shown, timedRecordedFrames, acceptedLive, spectatorStream.lastFrame, playbackSeconds, minute]);

  const isRecordedReplay = !acceptedLive && !spectatorStream.lastFrame && timedRecordedFrames.length >= 2;
  const timelineModel = useMemo(() => buildTimelineModel(timedRecordedFrames as any, (viewerData?.events?.length ? viewerData.events : m?.events) || [], replayDurationSeconds), [timedRecordedFrames, viewerData?.events, m?.events, replayDurationSeconds]);

  // Authoritative live stats win; otherwise derive only what shown events can honestly support
  // (shot attempts and cards). Possession, xG, etc. stay "—" rather than being invented.
  const liveStats = useMemo(() => {
    if (acceptedLive?.stats) return acceptedLive.stats;
    const homeId = String(viewerData?.home_team?.team_id || "");
    const awayId = String(viewerData?.away_team?.team_id || "");
    const sideOf = (ev: any): "home" | "away" | null => {
      const t = String(ev?.team || ev?.side || ev?.team_id || "").toLowerCase();
      if (t === "home" || (homeId && t === homeId.toLowerCase())) return "home";
      if (t === "away" || (awayId && t === awayId.toLowerCase())) return "away";
      return null;
    };
    const rows: any[] = Array.isArray(shown) ? (shown as any[]) : [];
    if (!rows.length) return undefined;
    const tally = { hs: 0, as: 0, hy: 0, ay: 0, hr: 0, ar: 0, known: 0 };
    for (const ev of rows) {
      const type = String(ev?.type || ev?.event_type || "").toLowerCase();
      const sd = sideOf(ev);
      if (!sd) continue;
      if (["shot", "miss", "save", "goal", "penalty_goal"].includes(type)) {
        tally.known += 1;
        if (sd === "home") tally.hs += 1;
        else tally.as += 1;
      } else if (type === "yellow_card") {
        tally.known += 1;
        if (sd === "home") tally.hy += 1;
        else tally.ay += 1;
      } else if (type === "red_card") {
        tally.known += 1;
        if (sd === "home") tally.hr += 1;
        else tally.ar += 1;
      }
    }
    if (!tally.known) return undefined;
    return {
      home_shots: tally.hs,
      away_shots: tally.as,
      home_yellow_cards: tally.hy,
      away_yellow_cards: tally.ay,
      home_red_cards: tally.hr,
      away_red_cards: tally.ar,
    } as any;
  }, [acceptedLive?.stats, shown, viewerData?.home_team?.team_id, viewerData?.away_team?.team_id]);

  if (isLoading || !m) return <Loading label="Loading match" />;

  const fallbackScore = shown
    .filter((e: any) => e.type === "goal" || e.type === "penalty_goal")
    .reduce((acc: any, e: any) => ({ ...acc, [e.team]: (acc[e.team] || 0) + 1 }), {
      home: 0,
      away: 0,
    });

  const score = {
    home:
      spectatorStream.latestScore?.home_score ??
      spectatorStream.lastFrame?.home_score ??
      acceptedLive?.home?.score ??
      liveState?.home?.score ??
      activeReplayFrame?.home_score ??
      fallbackScore.home,
    away:
      spectatorStream.latestScore?.away_score ??
      spectatorStream.lastFrame?.away_score ??
      acceptedLive?.away?.score ??
      liveState?.away?.score ??
      activeReplayFrame?.away_score ??
      fallbackScore.away,
  };
  const replayFinished =
    !acceptedLive &&
    !spectatorStream.lastFrame &&
    timedRecordedFrames.length > 1 &&
    replayDurationSeconds > 0 &&
    playbackSeconds >= replayDurationSeconds - 0.001;
  const done =
    phaseName === "completed" ||
    phaseName === "full_time" ||
    phaseName === "fulltime" ||
    replayFinished;
  const hasAuthoritativeFeed = Boolean(
    acceptedLive || spectatorStream.lastFrame || timedRecordedFrames.length > 0,
  );
  const isScheduled =
    phaseName === "pre_match" && minute === 0;
  const side = m.home_club_id === clubId ? "home" : m.away_club_id === clubId ? "away" : m.narrative?.home_owner_view ? "home" : "away";

  const sourceKind = pitchSource({
    matchId: id,
    hasSnapshot: Boolean(acceptedLive?.pitch_players?.length || spectatorStream.lastFrame?.players?.length),
    hasFrames: recordedFrames.length > 0,
  });

  const managerSide = side === "away" ? acceptedLive?.away : acceptedLive?.home;

  const applyPreset = (preset: any) => {
    setPress(preset.press);
    setLine(preset.line);
    setTempo(preset.tempo);
    setRisk(preset.risk);
    setFormation(preset.formation);
  };

  return (
    <div data-testid="match-center-page" className="grid gap-6 max-md:flex max-md:flex-col lg:grid-cols-12">
      <div className="space-y-6 max-md:flex max-md:flex-col lg:col-span-8">
        {/* Main Match Header & Broadcast Scoreboard */}
        <section className="gx-scoreboard-box gx-pitch-grid gx-panel-live relative order-1 overflow-hidden rounded-2xl border border-[#25354B] p-5 sm:p-6 shadow-2xl">
          {/* Top Broadcast Venue & Status Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] pb-3.5">
            {/* Layer 3: Football Display Mode Switcher */}
            <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-black/40 p-1" data-testid="match-center-view-toggle">
              <button
                type="button"
                onClick={() => {
                  setModuleView("match_center", "broadcast");
                  setActiveTab("pitch");
                }}
                data-testid="match-view-broadcast"
                className={`rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                  matchView === "broadcast"
                    ? "bg-emerald-500 text-black shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Broadcast View
              </button>
              <button
                type="button"
                onClick={() => {
                  setModuleView("match_center", "tactical");
                  setActiveTab("tactics");
                }}
                data-testid="match-view-tactical"
                className={`rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                  matchView === "tactical"
                    ? "bg-emerald-500 text-black shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Tactical Command
              </button>
              <button
                type="button"
                onClick={() => {
                  setModuleView("match_center", "compact");
                  setActiveTab("commentary");
                }}
                data-testid="match-view-compact"
                className={`rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                  matchView === "compact"
                    ? "bg-emerald-500 text-black shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Compact Ticker
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={!hasAuthoritativeFeed ? "slate" : done ? "slate" : isScheduled ? "cyan" : "emerald"}>
                {!hasAuthoritativeFeed ? (
                  "Preview · authoritative match feed unavailable"
                ) : done ? (
                  "Full time"
                ) : isScheduled ? (
                  "Pre-Match Briefing"
                ) : (
                  <>
                    <Radio size={10} className="gx-live-dot" /> Live · {minute}'
                  </>
                )}
              </Chip>

              {/* Broadcast Match Period Capsule */}
              <div className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-[#080F1C]/70 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-widest text-slate-300">
                <span
                  className={
                    done
                      ? "size-1.5 rounded-full bg-slate-400"
                      : isScheduled
                        ? "size-1.5 rounded-full bg-amber-400"
                        : "size-1.5 rounded-full bg-[#00C991] animate-ping"
                  }
                />
                <span>
                  {done
                    ? "Full Time"
                    : isScheduled
                      ? "Pre-Match"
                      : phaseName === "penalty_shootout"
                        ? "Penalties"
                        : phaseName === "extra_time"
                          ? "Extra Time"
                          : isHalftime
                            ? "Halftime"
                            : minute <= 45
                              ? "1st Half"
                              : "2nd Half"}
                </span>
              </div>

              <MatchSponsorIdentificationBadge ad={matchAds.sponsorAd} />

              {/* Pause/Resume Toggle */}
              {!done && hasAuthoritativeFeed && (
                <button
                  type="button"
                  data-testid="match-pause-toggle"
                  onClick={() => setIsPaused(!isPaused)}
                  className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-[#14243A] px-2.5 py-1 text-xs font-bold text-slate-200 transition hover:border-[#00C991]/50 hover:bg-[#14243A]/90 hover:text-white"
                >
                  {isPaused ? <Play size={12} className="text-[#00E8A8]" /> : <Pause size={12} className="text-amber-400" />}
                  <span>{isPaused ? "RESUME" : "PAUSE"}</span>
                </button>
              )}

              {/* Speed Cycle Pill */}
              {!done && hasAuthoritativeFeed && (
                <button
                  type="button"
                  data-testid="match-speed-toggle"
                  onClick={() => setSpeed((s) => (s === 0.5 ? 1.0 : s === 1.0 ? 2.0 : 0.5))}
                  className="gx-mono rounded-xl border border-[#00C991]/40 bg-[#00C991]/15 px-2.5 py-1 text-xs font-black text-[#00E8A8] transition hover:bg-[#00C991]/25"
                >
                  {speed.toFixed(1)}x
                </button>
              )}

              {/* Stadium Audio Ambiance Toggle */}
              <button
                onClick={() => {
                  setAudioAtmosphere(!audioAtmosphere);
                  toast.info(audioAtmosphere ? "Stadium crowd audio muted" : "Synthesized stadium atmosphere active");
                }}
                className={`flex items-center gap-1.5 rounded-xl border px-2.5 py-1 text-xs font-bold transition-all ${
                  audioAtmosphere
                    ? "border-[#42B9EC]/50 bg-[#42B9EC]/20 text-[#42B9EC] shadow-[0_0_12px_rgba(66,185,236,0.3)]"
                    : "border-white/10 bg-white/5 text-slate-400 hover:text-white"
                }`}
              >
                {audioAtmosphere ? <Volume2 size={12} /> : <VolumeX size={12} />}
                <span className="hidden sm:inline">CROWD SFX</span>
              </button>
            </div>

          </div>

          {/* Authentic Television Esports Scoreboard Hero */}
          <div className="my-6 grid grid-cols-12 items-center gap-3">
            {/* Home Club Team Card */}
            <div className="col-span-4 flex flex-col items-center sm:items-end text-center sm:text-right">
              <div className="flex items-center gap-2.5 flex-row-reverse sm:flex-row">
                <div>
                  <p className="gx-display text-lg sm:text-2xl font-black uppercase text-white tracking-tight leading-none" title={m.home_name}>
                    {m.home_name}
                  </p>
                  <div className="mt-1 flex items-center justify-center sm:justify-end gap-1.5">
                    <span className="gx-mono text-[10px] font-extrabold text-[#00E8A8] bg-[#00C991]/15 px-1.5 py-0.5 rounded border border-[#00C991]/30">
                      {formation}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase hidden sm:inline">HOME</span>
                  </div>
                </div>
                {suppliedCrest(acceptedLive?.home?.crest_url) ? (
                  <img src={suppliedCrest(acceptedLive?.home?.crest_url) || ""} alt="" className="size-10 shrink-0 rounded-xl object-cover" />
                ) : (
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#00E8A8] to-[#00A677] text-slate-950 font-black text-sm shadow-lg border border-white/20">
                  {m.home_name?.slice(0, 2).toUpperCase() || "HM"}
                </div>
                )}
              </div>
            </div>

            {/* Central Score Digits Display */}
            <div className="col-span-4 flex flex-col items-center justify-center">
              <div className="flex items-center gap-2 sm:gap-3 rounded-2xl border border-white/15 bg-[#080F1C]/90 px-4 sm:px-6 py-2 shadow-2xl backdrop-blur-xl">
                <span className="gx-display text-4xl sm:text-6xl font-black text-white tracking-tight drop-shadow-md">
                  {score.home}
                </span>
                <span className="text-xl sm:text-2xl font-black text-white/30">
                  :
                </span>
                <span className="gx-display text-4xl sm:text-6xl font-black text-white tracking-tight drop-shadow-md">
                  {score.away}
                </span>
              </div>
              <span
                data-testid="match-clock-display"
                className="gx-mono mt-1.5 text-[11px] font-black text-[#00E8A8] tracking-widest uppercase"
              >
                {done ? "FINAL" : phaseName === "penalty_shootout" ? "PENALTIES" : phaseName === "extra_time" ? `${minute}' EXTRA TIME` : phaseName === "full_time" || phaseName === "fulltime" ? "FULL TIME" : `${minute}' MATCHDAY`}
              </span>
              <p className="sr-only" data-testid="match-score">
                {score.home} – {score.away}
              </p>
            </div>

            {/* Away Club Team Card */}
            <div className="col-span-4 flex flex-col items-center sm:items-start text-center sm:text-left">
              <div className="flex items-center gap-2.5">
                {suppliedCrest(acceptedLive?.away?.crest_url) ? (
                  <img src={suppliedCrest(acceptedLive?.away?.crest_url) || ""} alt="" className="size-10 shrink-0 rounded-xl object-cover" />
                ) : (
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#F3CA5A] to-[#C79727] text-slate-950 font-black text-sm shadow-lg border border-white/20">
                  {m.away_name?.slice(0, 2).toUpperCase() || "AW"}
                </div>
                )}
                <div>
                  <p className="gx-display text-lg sm:text-2xl font-black uppercase text-white tracking-tight leading-none" title={m.away_name}>
                    {m.away_name}
                  </p>
                  <div className="mt-1 flex items-center justify-center sm:justify-start gap-1.5">
                    <span className="gx-mono text-[10px] font-extrabold text-[#E5B63F] bg-[#E5B63F]/15 px-1.5 py-0.5 rounded border border-[#E5B63F]/30">
                      {acceptedLive?.away?.formation || "—"}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase hidden sm:inline">AWAY</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tactical Momentum Scrubber with Pitch Zones */}
          <div className="border-t border-white/[0.08] pt-3 mt-4">
            <div className="flex items-center justify-between mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <span className="flex items-center gap-1.5 text-white">
                <Activity size={12} className="text-[#00C991]" />
                Tactical Momentum & Field Dominance
              </span>
              <span className="gx-mono text-slate-300">
                {m.narrative?.mentality?.home || "Balanced"} vs {m.narrative?.mentality?.away || "Balanced"}
              </span>
            </div>
            <Momentum values={m.narrative?.momentum || []} upto={minute} />
          </div>
        </section>

        {/* Match Navigation Tabs */}
        <div className="hidden flex-wrap gap-2 border-b border-[#25354B] pb-3 md:flex">
          {[
            { id: "pitch", label: view3DBroadcast ? "3D MATCHDAY BROADCAST (WEBGL)" : "2D / 2.5D MATCH PITCH", icon: Tv },
            { id: "lineups", label: "MATCHDAY LINEUPS", icon: Users },
            { id: "tactics", label: "TACTICS & ADVISOR", icon: Sliders },
            { id: "pre_match", label: "PRE-MATCH + 3D STAGE", icon: Target },
            { id: "post_match", label: "POST-MATCH + 3D GALA", icon: Award },
            { id: "commentary", label: "LIVE FEED", icon: Radio },
          ].map((tab) => {
            const IconComponent = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
                  isActive
                    ? "border border-[#00C991]/50 bg-gradient-to-r from-[#00C991]/20 to-[#00C991]/5 text-white shadow-[0_4px_16px_rgba(0,201,145,0.25)]"
                    : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-white"
                }`}
              >
                <IconComponent size={14} className={isActive ? "text-[#00E8A8]" : "text-slate-400"} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: 2D / 2.5D Match Pitch Board */}
        <div className={`${activeTab === "pitch" ? "block" : "hidden"} order-2 space-y-4 max-md:block`}>
            {/* Pitch Camera & Tactical Shader Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-white/10 bg-slate-900/85 p-2.5">
              {/* Camera Perspective Switcher */}
              {/* 2D-only controls: hidden in WebGL mode (3D uses the broadcast HUD camera controls) */}
              {!view3DBroadcast && (
              <div className="flex items-center gap-1.5">
                <Camera size={13} className="text-emerald-400" />
                {[
                  { id: "2d" as const, label: "2D TOP-DOWN" },
                  { id: "2.5d" as const, label: "2.5D TV BROADCAST" },
                  { id: "zoom" as const, label: "DIRECTOR ZOOM" },
                ].map((cam) => (
                  <button
                    key={cam.id}
                    type="button"
                    data-testid={`cam-mode-${cam.id}`}
                    aria-pressed={cameraMode === cam.id}
                    onClick={() => setCameraMode(cam.id)}
                    className={`rounded-sm px-2 py-1 text-[10px] font-black tracking-wider transition-colors ${
                      cameraMode === cam.id
                        ? "border border-emerald-400/60 bg-emerald-500/20 text-emerald-300"
                        : "bg-white/5 text-slate-400 hover:text-white"
                    }`}
                  >
                    {cam.label}
                  </button>
                ))}
              </div>
              )}

              {/* 3D WebGL Broadcast / 2D Tactical Toggle & 16:9 Match Theatre Launch */}
              <div className="flex items-center gap-1.5">
                {match3dEnabled && (
                <button
                  type="button"
                  data-testid="toggle-3d-broadcast-mode"
                  onClick={() => setView3DBroadcast(!view3DBroadcast)}
                  className={`flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-[10px] font-black tracking-wider transition-colors ${
                    view3DBroadcast
                      ? "border border-cyan-400/60 bg-cyan-500/25 text-cyan-200"
                      : "bg-white/5 text-slate-400 hover:text-white"
                  }`}
                >
                  <Tv size={11} className={view3DBroadcast ? "text-cyan-400" : "text-slate-400"} />
                  <span>{view3DBroadcast ? "3D BROADCAST" : "2D PITCH"}</span>
                </button>
                )}
                {match3dEnabled && (
                <button
                  type="button"
                  data-testid="enter-match-theatre-button"
                  onClick={() => {
                    setView3DBroadcast(true);
                    setIsTheatreMode((t) => !t);
                  }}
                  className={`flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-[10px] font-black tracking-wider transition-colors ${
                    isTheatreMode
                      ? "border border-emerald-400 bg-emerald-500 text-slate-950"
                      : "border border-emerald-400/50 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25"
                  }`}
                >
                  <span>{isTheatreMode ? "EXIT 16:9 THEATRE" : "16:9 MATCH THEATRE"}</span>
                </button>
                )}
              </div>

              {/* Spatial Shaders + Event-Driven 3D Cut-In Triggers */}
              {!view3DBroadcast && (
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  data-testid="toggle-voronoi"
                  aria-pressed={showVoronoi}
                  onClick={() => setShowVoronoi(!showVoronoi)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showVoronoi ? "bg-blue-500/20 text-blue-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Compass size={11} /> VORONOI
                </button>
                <button
                  type="button"
                  data-testid="toggle-heatmap"
                  aria-pressed={showHeatmap}
                  onClick={() => setShowHeatmap(!showHeatmap)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showHeatmap ? "bg-rose-500/20 text-rose-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Flame size={11} /> HEATMAP
                </button>
                <button
                  type="button"
                  data-testid="toggle-tactics"
                  aria-pressed={showTactics}
                  onClick={() => setShowTactics(!showTactics)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showTactics ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Layers size={11} /> TACTICS
                </button>
                <button
                  type="button"
                  data-testid="toggle-passing-lanes"
                  aria-pressed={showLanes}
                  onClick={() => setShowLanes(!showLanes)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showLanes ? "bg-cyan-500/20 text-cyan-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Activity size={11} /> PASSING LANES
                </button>
                {match3dEnabled && (
                <button
                  type="button"
                  onClick={() => {
                    setCutInScene("signing_walkout");
                    setShow3DCutIn(!show3DCutIn);
                  }}
                  className={`flex items-center gap-1 rounded-sm border px-2.5 py-1 text-[10px] font-black tracking-wider transition-colors ${
                    show3DCutIn
                      ? "border-amber-400 bg-amber-500/25 text-amber-200"
                      : "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
                  }`}
                >
                  <Box size={11} /> 3D GOAL / TUNNEL CAM
                </button>
                )}
              </div>
              )}
            </div>

            {/* Kickoff Broadcast Lineup Walkout Sheet (Auto-shown on Kickoff) */}
            {showKickoffLineups && minute <= 10 && (
              <div className="rounded-xl border border-sky-400/25 bg-slate-950/90 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-[11px] font-black uppercase tracking-wider text-sky-300">
                    Official Kickoff Broadcast Team Sheets · {m.home_name} vs {m.away_name}
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowKickoffLineups(false)}
                    className="rounded border border-white/15 bg-white/5 px-2.5 py-0.5 text-[10px] font-bold uppercase text-slate-300 hover:text-white"
                  >
                    Dismiss Walkout Graphics
                  </button>
                </div>
                <MatchdayLineupBroadcast
                  homeClubId={m.home_club_id}
                  homeClubName={m.home_name}
                  awayClubId={m.away_club_id}
                  awayClubName={m.away_name}
                  editableClubId={clubId}
                  competitionName="GTEX MATCHDAY LIVE"
                  matchdayNumber={m.round || 1}
                  formationOverride={formation}
                  onFormationChange={setFormation}
                  homePitchPlayers={homeLivePitch}
                  awayPitchPlayers={awayLivePitch}
                  defaultView="dual"
                />
              </div>
            )}

            {/* 3D WebGL Live Match Broadcast Canvas or 2D Pitch Fallback */}
            {view3DBroadcast ? (
              <div className="relative">
                <MatchPitchLiveScene
                  matchViewState={viewerData || m}
                  isLive={Boolean(params.get("live"))}
                  viewerCount={spectatorStream.viewerCount}
                  qualityTier={(params.get("tier") as any) || (params.get("quality") as any) || "high"}
                  playbackSpeed={speed}
                  isPaused={isPaused}
                  liveFrame={spectatorStream.lastFrame}
                  liveEvents={spectatorStream.recentEvents}
                  liveScore={spectatorStream.latestScore}
                  tacticalConfig={authoritativeTactics}
                  isTheatreMode={isTheatreMode}
                  onToggleTheatreMode={() => setIsTheatreMode((t) => !t)}
                  onToggle2DCompanion={() => {
                    setIsTheatreMode(false);
                    setView3DBroadcast(false);
                  }}
                />
                {activeGift && (
                  <CinematicGiftingEngine
                    activeGift={activeGift}
                    onAnimationComplete={handleGiftAnimationComplete}
                    soundEnabled={true}
                  />
                )}
              </div>
            ) : (
              <div className="relative">
                <Pitch2DView
                  matchId={id}
                  frames={recordedFrames}
                  timeSeconds={playbackSeconds}
                  snapshotVersion={Number(acceptedLive?.snapshot_version ?? 0)}
                  snapshotPlayers={acceptedLive?.pitch_players}
                  snapshotBall={acceptedLive?.ball}
                  socketFrame={spectatorStream.lastFrame}
                  events={shown}
                  activeEventType={
                    (spectatorStream.lastFrame as any)?.active_event?.event_type ||
                    (spectatorStream.lastFrame as any)?.event_type ||
                    acceptedLive?.active_event_type ||
                    activeReplayFrame?.active_event?.event_type ||
                    activeReplayFrame?.event_type ||
                    null
                  }
                  homeColor={acceptedLive?.home?.primary_color_hex || viewerData?.home_team?.primary_color || "#00e87a"}
                  awayColor={acceptedLive?.away?.primary_color_hex || viewerData?.away_team?.primary_color || "#ffb800"}
                  goalkeeperHome={acceptedLive?.home?.goalkeeper_color || viewerData?.home_team?.goalkeeper_color || "#f8fafc"}
                  goalkeeperAway={acceptedLive?.away?.goalkeeper_color || viewerData?.away_team?.goalkeeper_color || "#111827"}
                  homeScore={score.home}
                  awayScore={score.away}
                  homeName={m.home_name}
                  awayName={m.away_name}
                  homeCrest={acceptedLive?.home?.crest_url}
                  awayCrest={acceptedLive?.away?.crest_url}
                  selectedKey={selectedPlayer}
                  onSelect={setSelectedPlayer}
                  demo={sourceKind === "demo"}
                  reconnectToken={reconnectToken}
                  connectionStatus={spectatorStream.connectionStatus}
                  matchPhase={phaseName || null}
                  paused={isPaused}
                  playbackSpeed={speed}
                  cameraMode={cameraMode}
                  onCameraModeChange={setCameraMode}
                  showVoronoi={showVoronoi}
                  showHeatmap={showHeatmap}
                  showTactics={showTactics}
                  showPassingLanes={showLanes}
                />
                {isRecordedReplay && (<MatchTimelineScrubber model={timelineModel} currentSeconds={playbackSeconds} onSeek={(s) => setPlaybackSeconds(s)} />)}
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {[
                    ["Shots", `${metricText(liveStats?.home_shots)} – ${metricText(liveStats?.away_shots)}`],
                    ["Possession", `${metricText(liveStats?.home_possession)} – ${metricText(liveStats?.away_possession)}`],
                    ["xG", `${metricText(liveStats?.home_expected_goals)} – ${metricText(liveStats?.away_expected_goals)}`],
                    ["Cards", `${metricText(liveStats?.home_yellow_cards)}/${metricText(liveStats?.home_red_cards)} – ${metricText(liveStats?.away_yellow_cards)}/${metricText(liveStats?.away_red_cards)}`],
                    ["Pass accuracy", `${metricText(liveStats?.home_pass_accuracy)} – ${metricText(liveStats?.away_pass_accuracy)}`],
                    ["xT", `${metricText(liveStats?.home_expected_threat)} – ${metricText(liveStats?.away_expected_threat)}`],
                    ["PPDA", `${metricText(liveStats?.home_ppda)} – ${metricText(liveStats?.away_ppda)}`],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
                      <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">{label}</span>
                      <span className="gx-mono text-xs font-black text-white">{value}</span>
                    </div>
                  ))}
                </div>
                {activeGift && (
                  <CinematicGiftingEngine
                    activeGift={activeGift}
                    onAnimationComplete={handleGiftAnimationComplete}
                    soundEnabled={true}
                  />
                )}
              </div>
            )}
          </div>

        {/* Tab 1B: Official Broadcast Matchday Lineups */}
        {activeTab === "lineups" && (
          <Panel
            eyebrow="Official Matchday Team Sheets"
            title={`${m.home_name} vs ${m.away_name} · Starting XIs`}
            testid="match-center-lineups-tab"
          >
            <MatchdayLineupBroadcast
              homeClubId={m.home_club_id}
              homeClubName={m.home_name}
              awayClubId={m.away_club_id}
              awayClubName={m.away_name}
              editableClubId={clubId}
              competitionName="GTEX MATCHDAY LIVE"
              matchdayNumber={m.round || 1}
              formationOverride={formation}
              onFormationChange={setFormation}
              homePitchPlayers={homeLivePitch}
              awayPitchPlayers={awayLivePitch}
              defaultView="dual"
            />
          </Panel>
        )}

        {/* Tab 2: Tactics & In-Match Advisor */}
        <div className={`${activeTab === "tactics" ? "block" : "hidden"} order-4 max-md:block`}>
          <TacticalHUD
            formation={formation}
            setFormation={setFormation}
            press={press}
            setPress={setPress}
            line={line}
            setLine={setLine}
            tempo={tempo}
            setTempo={setTempo}
            risk={risk}
            setRisk={setRisk}
            onApplyPreset={applyPreset}
            matchId={id || ""}
            minute={minute}
            homeScore={score.home}
            awayScore={score.away}
            side={side}
            bench={managerSide?.bench || []}
            starters={managerSide?.players || []}
          />
        </div>

        {/* Tab 3: Pre-Match Package */}
        {activeTab === "pre_match" && (
          <PreMatchBriefing match={m} preMatch={liveState?.pre_match} matchId={id || ""} />
        )}

        {/* Tab 4: Post-Match Analytics & Press Room */}
        {activeTab === "post_match" && (
          <PostMatchAnalytics
            match={m}
            postMatch={liveState?.post_match}
            stats={liveState?.stats}
            matchId={id || ""}
            homeScore={score.home}
            awayScore={score.away}
            clubId={clubId}
          />
        )}

        {/* Tab 5: Live Commentary & Events */}
        <div className={`${activeTab === "commentary" ? "block" : "hidden"} order-3 max-md:block`}>
          <Panel eyebrow="Live commentary" title="Event feed" testid="commentary-feed">
            <ol className="space-y-2">
              {[...commentary].reverse().map((e: any, i: number) => (
                <li
                  key={i}
                  className={`gx-rise flex gap-3 rounded-sm px-3 py-2 text-sm ${
                    e.type === "goal" ? "border border-emerald-500/30 bg-emerald-500/10 text-white" : "text-slate-300"
                  }`}
                >
                  <span className="gx-mono w-10 shrink-0 text-slate-500">{e.minute}'</span>
                  {e.type === "goal" && <Flame size={14} className="mt-0.5 text-emerald-400" />}
                  <span>{e.text || e.title || e.description}</span>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>

      {/* Right Column: Commercial Broadcast Panel, Owner View, Gift Rail, Navigation */}
      <div className="order-5 space-y-6 lg:col-span-4">
        <SilentMatchBroadcastPanel
          liveAd={matchAds.livePanelAd}
          halftimeAd={matchAds.halftimeAd}
          isHalftime={isHalftime}
        />
        {done && <OwnerView view={m.narrative?.[`${side}_owner_view`]} />}
        <GiftRail
          match={m}
          clubId={clubId}
          onGiftSent={(g: any) => {
            enqueueGift(g);
          }}
        />
        <Link
          to={`/app/competitions/${m.competition_id}`}
          className="gx-btn gx-btn-secondary flex w-full items-center justify-center gap-1.5"
          data-testid="back-to-competition"
        >
          <span>Back to competition</span>
          <ChevronRight size={14} />
        </Link>
      </div>
    </div>
  );
}

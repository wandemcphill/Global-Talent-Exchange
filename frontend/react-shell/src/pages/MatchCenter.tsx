import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Activity,
  Award,
  CheckCircle2,
  ChevronRight,
  Coins,
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
  Volume2,
  VolumeX,
  Zap,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";

const GIFTS = [
  { code: "stadium_roar", name: "Stadium Roar", cost: 10 },
  { code: "captains_armband", name: "Captain's Armband", cost: 20 },
  { code: "home_end_banner", name: "Home End Banner", cost: 30 },
  { code: "golden_boot", name: "Golden Boot", cost: 50 },
  { code: "floodlights", name: "Floodlights", cost: 100 },
  { code: "legendary_stadium", name: "Legendary Stadium", cost: 1000 },
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

function GiftRail({ match, clubId }: any) {
  const refresh = useRefreshOwner();
  const [feed, setFeed] = useState<string[]>([]);
  const targets = [match.home_club_id, match.away_club_id].filter((c: string) => !c.startsWith("ai:"));
  const [target, setTarget] = useState(targets.includes(clubId) ? clubId : targets[0]);
  if (!targets.length) return null;
  const send = async (g: any) => {
    try {
      const { data } = await api.post("/owner/gifts/send", { club_id: target, gift_code: g.code, match_id: match.id });
      setFeed((f) => [`${data.sender} sent ${g.name}`, ...f].slice(0, 5));
      refresh();
      toast.success(`Gift sent: ${g.name}`);
    } catch (e) {
      toast.error(errMsg(e));
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
      <div className="grid grid-cols-2 gap-2">
        {GIFTS.map((g) => (
          <button
            key={g.code}
            data-testid={`gift-${g.code}`}
            onClick={() => send(g)}
            className="rounded-sm border border-amber-500/20 bg-amber-500/[0.04] px-3 py-2 text-left text-xs transition-colors hover:border-amber-400/60 hover:bg-amber-500/10"
          >
            <span className="block font-semibold text-amber-200">{g.name}</span>
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

// 2D Pitch Interactive View
function Pitch2DView({
  selectedPlayer,
  onSelectPlayer,
  showHeatmap,
  showTactics,
  showLanes,
  ballOwner,
  pitchPlayers,
  ball,
}: {
  selectedPlayer: number | null;
  onSelectPlayer: (num: number | null) => void;
  showHeatmap: boolean;
  showTactics: boolean;
  showLanes: boolean;
  ballOwner: { team: "home" | "away"; num: number } | null;
  pitchPlayers?: Array<{
    player_id?: string;
    name?: string;
    shirt_number?: number;
    x: number;
    y: number;
    is_home?: boolean;
    has_ball?: boolean;
    role?: string;
  }>;
  ball?: { x: number; y: number } | null;
}) {
  const homeCoords = (pitchPlayers || [])
    .filter((p) => p.is_home)
    .map((p, idx) => ({
      x: p.x,
      y: p.y,
      num: p.shirt_number || idx + 1,
      role: p.role || "N/A",
      hasBall: Boolean(p.has_ball),
      name: p.name,
    }));
  const awayCoords = (pitchPlayers || [])
    .filter((p) => !p.is_home)
    .map((p, idx) => ({
      x: p.x,
      y: p.y,
      num: p.shirt_number || idx + 1,
      role: p.role || "N/A",
      hasBall: Boolean(p.has_ball),
      name: p.name,
    }));

  const selectedObj = homeCoords.find((p) => p.num === selectedPlayer);
  const ballX = ball ? ball.x * 1000 : null;
  const ballY = ball ? ball.y * 625 : null;

  return (
    <div className="relative aspect-[16/10] w-full overflow-hidden rounded-lg border border-emerald-500/30 bg-[#0A1F13] shadow-2xl">
      <svg className="absolute inset-0 h-full w-full select-none" viewBox="0 0 1000 625">
        <defs>
          <radialGradient id="pitch-turf" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="#143A22" />
            <stop offset="100%" stopColor="#0B2014" />
          </radialGradient>
          <pattern id="grass-stripes" width="100" height="625" patternUnits="userSpaceOnUse">
            <rect width="50" height="625" fill="#174328" opacity="0.3" />
            <rect x="50" width="50" height="625" fill="#0D2617" opacity="0.1" />
          </pattern>
          <radialGradient id="heat-home" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00E87A" stopOpacity="0.45" />
            <stop offset="50%" stopColor="#00E87A" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#00E87A" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="heat-away" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FFB800" stopOpacity="0.40" />
            <stop offset="50%" stopColor="#FFB800" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#FFB800" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="heat-ball" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FF4500" stopOpacity="0.75" />
            <stop offset="60%" stopColor="#FFA500" stopOpacity="0.30" />
            <stop offset="100%" stopColor="#FFA500" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Pitch Turf & Lines */}
        <rect width="1000" height="625" fill="url(#pitch-turf)" />
        <rect width="1000" height="625" fill="url(#grass-stripes)" />
        <rect x="40" y="30" width="920" height="565" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <line x1="500" y1="30" x2="500" y2="595" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <circle cx="500" cy="312.5" r="75" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <circle cx="500" cy="312.5" r="4" fill="#FFFFFF" opacity="0.7" />

        {/* Home Box */}
        <rect x="40" y="145" width="140" height="335" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <rect x="40" y="215" width="50" height="195" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <circle cx="130" cy="312.5" r="3" fill="#FFFFFF" opacity="0.7" />
        <path d="M 180 260 A 65 65 0 0 1 180 365" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />

        {/* Away Box */}
        <rect x="820" y="145" width="140" height="335" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <rect x="910" y="215" width="50" height="195" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />
        <circle cx="870" cy="312.5" r="3" fill="#FFFFFF" opacity="0.7" />
        <path d="M 820 260 A 65 65 0 0 0 820 365" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.5" />

        {/* Heatmap Overlay */}
        {showHeatmap && (
          <g className="transition-opacity duration-300">
            {homeCoords.map((p, idx) => (
              <circle key={`heat-h-${p.num || idx}`} cx={p.x * 1000} cy={p.y * 625} r="100" fill="url(#heat-home)" />
            ))}
            {awayCoords.map((p, idx) => (
              <circle key={`heat-a-${p.num || idx}`} cx={p.x * 1000} cy={p.y * 625} r="100" fill="url(#heat-away)" />
            ))}
            {ball && <circle cx={ballX ?? 0} cy={ballY ?? 0} r="130" fill="url(#heat-ball)" />}
          </g>
        )}

        {/* Tactical Line Overlay */}
        {showTactics && (
          <g>
            <line x1="210" y1="35" x2="210" y2="590" stroke="#00E87A" strokeWidth="2" strokeDasharray="6 4" opacity="0.65" />
            <line x1="790" y1="35" x2="790" y2="590" stroke="#FFB800" strokeWidth="2" strokeDasharray="6 4" opacity="0.65" />
            <polygon points="80,312 210,120 440,200 440,430 210,510" fill="#00E87A" fillOpacity="0.06" stroke="#00E87A" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
          </g>
        )}

        {/* Passing Lanes from Selected Player */}
        {showLanes && selectedObj && (
          <g>
            {homeCoords
              .filter((p) => p.num !== selectedObj.num)
              .map((p, idx) => (
                <line
                  key={`lane-${p.num || idx}`}
                  x1={selectedObj.x * 1000}
                  y1={selectedObj.y * 625}
                  x2={p.x * 1000}
                  y2={p.y * 625}
                  stroke="#00E87A"
                  strokeWidth="1.6"
                  strokeDasharray="4 3"
                  opacity="0.6"
                />
              ))}
          </g>
        )}

        {homeCoords.length === 0 && awayCoords.length === 0 && (
          <text x="500" y="312" textAnchor="middle" fill="#CBD5E1" fontSize="16" fontWeight="700">
            LIVE PLAYER COORDINATES UNAVAILABLE
          </text>
        )}

        {/* Home Players */}
        {homeCoords.map((p, idx) => {
          const isSelected = selectedPlayer === p.num;
          const hasBall = (p as any).hasBall || (ballOwner?.team === "home" && ballOwner?.num === p.num);
          return (
            <g
              key={`home-${p.num || idx}`}
              transform={`translate(${p.x * 1000}, ${p.y * 625})`}
              className="cursor-pointer transition-transform duration-300 hover:scale-110"
              onClick={() => onSelectPlayer(isSelected ? null : p.num)}
            >
              {isSelected && <circle r="22" fill="none" stroke="#00E87A" strokeWidth="2" opacity="0.8" className="animate-ping" />}
              <circle r="14" fill="#0F172A" stroke={hasBall ? "#00E87A" : "#FFFFFF"} strokeWidth={hasBall ? 2.5 : 1.5} />
              <circle r="11" fill="#00E87A" />
              <text y="4" textAnchor="middle" fill="#0F172A" fontSize="10" fontWeight="900" fontFamily="JetBrains Mono">
                {p.num || idx + 1}
              </text>
              <rect x="-18" y="16" width="36" height="13" rx="2" fill="#0A0C0F" opacity="0.8" />
              <text y="26" textAnchor="middle" fill="#A7F3D0" fontSize="8" fontWeight="800">
                {p.role}
              </text>
            </g>
          );
        })}

        {/* Away Players */}
        {awayCoords.map((p, idx) => {
          const hasBall = (p as any).hasBall || (ballOwner?.team === "away" && ballOwner?.num === p.num);
          return (
            <g key={`away-${p.num || idx}`} transform={`translate(${p.x * 1000}, ${p.y * 625})`} className="cursor-pointer">
              <circle r="14" fill="#0F172A" stroke={hasBall ? "#FFB800" : "#FFFFFF"} strokeWidth={hasBall ? 2.5 : 1.5} />
              <circle r="11" fill="#FFB800" />
              <text y="4" textAnchor="middle" fill="#0F172A" fontSize="10" fontWeight="900" fontFamily="JetBrains Mono">
                {p.num || idx + 1}
              </text>
              <rect x="-18" y="16" width="36" height="13" rx="2" fill="#0A0C0F" opacity="0.8" />
              <text y="26" textAnchor="middle" fill="#FDE68A" fontSize="8" fontWeight="800">
                {p.role}
              </text>
            </g>
          );
        })}

        {/* A ball marker is rendered only when the feed supplies its position. */}
        {ball && (
          <g transform={`translate(${ballX}, ${ballY})`}>
            <ellipse cx="0" cy="5" rx="8" ry="4" fill="#000000" opacity="0.4" />
            <circle r="6" fill="#FFFFFF" stroke="#0F172A" strokeWidth="1" />
            <circle r="2" fill="#00E87A" />
          </g>
        )}
      </svg>
    </div>
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
}) {
  const [submitting, setSubmitting] = useState(false);
  const [advisorApplied, setAdvisorApplied] = useState(false);

  // Compute Assistant Manager Coach Karl's dynamic live advice
  const advisor = useMemo(() => {
    if (minute >= 75 && homeScore > awayScore) {
      return {
        situation: `Lead Protection (${homeScore}-${awayScore} · ${minute}')`,
        recommendation: "Opponent is overloading wide channels. Drop into Low Block 5-3-2 with counter outlet.",
        buttonText: "APPLY LOW BLOCK LOCKDOWN",
        preset: TACTICAL_PRESETS.find((p) => p.name === "LOW BLOCK"),
        color: "text-blue-400",
      };
    } else if (minute >= 60 && homeScore < awayScore) {
      return {
        situation: `Goal Deficit (${homeScore}-${awayScore} · ${minute}')`,
        recommendation: "Need an equalizer. Shift into Gegenpress 4-2-4 with aggressive pressing line.",
        buttonText: "APPLY GEGENPRESS OVERLOAD",
        preset: TACTICAL_PRESETS.find((p) => p.name === "GEGENPRESS"),
        color: "text-rose-400",
      };
    } else if (homeScore < awayScore) {
      return {
        situation: `Trailing (${homeScore}-${awayScore} · ${minute}')`,
        recommendation: "Opponent high line leaves space in behind. Quick Counter 3-4-3 will catch them.",
        buttonText: "APPLY COUNTER ATTACK",
        preset: TACTICAL_PRESETS.find((p) => p.name === "COUNTER"),
        color: "text-amber-400",
      };
    } else {
      return {
        situation: `Tactical Parity (${homeScore}-${awayScore} · ${minute}')`,
        recommendation: "Midfield contest is balanced. Tiki-Taka 4-3-3 will retain possession and control rhythm.",
        buttonText: "APPLY POSSESSION CONTROL",
        preset: TACTICAL_PRESETS.find((p) => p.name === "TIKI-TAKA"),
        color: "text-emerald-400",
      };
    }
  }, [minute, homeScore, awayScore]);

  const dispatchInstruction = async () => {
    setSubmitting(true);
    try {
      await api.post(`/api/matches/${matchId}/tactics`, {
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
          onClick={() => {
            if (advisor.preset) onApplyPreset(advisor.preset);
            setAdvisorApplied(true);
            toast.success("Coach Karl's recommendation applied to tactical board!");
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

// Pre-Match Briefing Component
function PreMatchBriefing({ match, preMatch, matchId }: { match: any; preMatch?: any; matchId: string }) {
  const [pollVote, setPollVote] = useState<string | null>(null);
  const [predictionData, setPredictionData] = useState<any>(preMatch?.fan_predictions);

  const { data: initialPreds } = useQuery({
    queryKey: ["predictions", matchId],
    queryFn: async () => (await api.get(`/api/matches/${matchId}/predictions`)).data,
    initialData: preMatch?.fan_predictions,
    enabled: !!matchId,
  });

  const preds = predictionData || initialPreds || preMatch?.fan_predictions;
  const totalVotes = preds?.total_votes ?? 0;

  const handleVote = async (choiceKey: "home" | "draw" | "away", optLabel: string) => {
    try {
      const res = await api.post(`/api/matches/${matchId}/predictions`, { choice: choiceKey });
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

  const keyDuel = preMatch?.key_duel;
  const homeForm: string[] = preMatch?.home_form || [];
  const awayForm: string[] = preMatch?.away_form || [];

  return (
    <div className="space-y-6">
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
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-sm border border-emerald-500/30 bg-emerald-500/5 p-4 text-center">
              <span className="inline-block rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                HOME TALISMAN
              </span>
              <p className="mt-2 text-base font-bold text-white">{keyDuel.home_player.name}</p>
              <p className="text-xs text-slate-400">
                {keyDuel.home_player.role} · #{keyDuel.home_player.shirt_number}
              </p>
              <div className="mt-3 flex justify-around text-xs">
                <div>
                  <span className="block text-[10px] text-slate-500">RATING</span>
                  <span className="gx-mono font-bold text-emerald-300">{keyDuel.home_player.rating ?? "N/A"}</span>
                </div>
              </div>
            </div>

            <div className="rounded-sm border border-amber-500/30 bg-amber-500/5 p-4 text-center">
              <span className="inline-block rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                AWAY DANGERMAN
              </span>
              <p className="mt-2 text-base font-bold text-white">{keyDuel.away_player.name}</p>
              <p className="text-xs text-slate-400">
                {keyDuel.away_player.role} · #{keyDuel.away_player.shirt_number}
              </p>
              <div className="mt-3 flex justify-around text-xs">
                <div>
                  <span className="block text-[10px] text-slate-500">RATING</span>
                  <span className="gx-mono font-bold text-amber-300">{keyDuel.away_player.rating ?? "N/A"}</span>
                </div>
              </div>
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

// Post-Match Analytics & Press Room Component
function PostMatchAnalytics({
  match,
  postMatch,
  stats,
  matchId,
  homeScore,
  awayScore,
}: {
  match: any;
  postMatch?: any;
  stats?: any;
  matchId: string;
  homeScore: number;
  awayScore: number;
}) {
  const [pressAnswers, setPressAnswers] = useState<Record<number, number>>({});
  const [rewardsClaimed, setRewardsClaimed] = useState(false);
  const [claimingRewards, setClaimingRewards] = useState(false);

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
      const res = await api.post(`/api/matches/${matchId}/rewards/claim`);
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
        { text: '"We instructed our fullbacks to invert and create central superiority."', effect: "+15 TACTICS · +10 BOARD" },
        { text: '"The squad adapted to the tempo flawlessly. Pure collective discipline."', effect: "+20 MORALE · +10 CHEMISTRY" },
        { text: '"We remained pragmatic and exploited defensive transition errors."', effect: "+12 PRAGMATISM" },
      ],
    },
    {
      outlet: "SKY SPORTS FOOTBALL",
      journalist: "Laura Evans",
      q: "The fans generated a tremendous roar. How crucial was that stadium atmosphere today?",
      opts: [
        { text: '"This result belongs to our supporters. They pushed us across the line."', effect: "+25 FAN APPROVAL" },
        { text: '"Professional job. We enjoy tonight and resume work at 8 AM tomorrow."', effect: "+15 STANDARDS" },
        { text: '"Every match demands this intensity. We are raising the bar."', effect: "+18 DETERMINATION" },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      {/* MOTM Celebration */}
      <Panel eyebrow="Full-time Honors" title="Player of the Match" testid="motm-card">
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

      {/* Interactive xG Shot Map */}
      <Panel eyebrow="Spatial Analytics" title="Expected Goals (xG) Shot Map" testid="shot-map">
        <div className="relative aspect-[16/9] w-full overflow-hidden rounded-md border border-white/10 bg-[#0B2014] p-3">
          <svg className="h-full w-full" viewBox="0 0 1000 560">
            <rect width="1000" height="560" fill="#0D2818" />
            <rect x="20" y="20" width="960" height="520" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.3" />
            <line x1="500" y1="20" x2="500" y2="540" stroke="#FFFFFF" strokeWidth="2" opacity="0.3" />
            <circle cx="500" cy="280" r="70" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.3" />

            {/* Shots */}
            {shotMap.length > 0 ? (
              shotMap.map((s, idx) => {
                const cx = s.x * 1000;
                const cy = s.y * 560;
                const isGoal = s.outcome === "goal";
                const isSaved = s.outcome === "saved";
                const color = isGoal ? "#00E87A" : isSaved ? "#60A5FA" : "#F87171";
                const r = isGoal ? 14 : Math.max(7, Math.min(13, (s.xg || 0.15) * 20));
                return (
                  <g key={`shot-${idx}`} className="cursor-pointer">
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

      {/* Simulated Media Reaction */}
      <Panel eyebrow="AI Simulation · Press Room" title="Simulated Media Reaction (Press Room Briefing)" testid="press-conference">
        <p className="mb-3 text-[11px] text-slate-400">
          Post-match reactions are dynamically simulated from pitch actions and match statistics.
        </p>
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
                    onClick={() => {
                      setPressAnswers((prev) => ({ ...prev, [qIdx]: optIdx }));
                      toast.info("Response selected for preview only; no manager effects were applied.");
                    }}
                    className={`flex w-full items-center justify-between rounded-sm px-3 py-2 text-left text-xs transition-colors ${
                      pressAnswers[qIdx] === optIdx
                        ? "border border-emerald-500/50 bg-emerald-500/15 text-white"
                        : "border border-white/5 bg-white/[0.02] text-slate-300 hover:border-white/20"
                    }`}
                  >
                    <span>{opt.text}</span>
                    <span className="gx-mono text-[9px] font-bold text-slate-500">PREVIEW ONLY</span>
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
  const { id } = useParams();
  const [params] = useSearchParams();
  const clubId = params.get("club") || "";
  const { data: m, isLoading } = useQuery({
    queryKey: ["match", id],
    queryFn: async () => (await api.get(`/owner/matches/${id}`)).data,
    enabled: !!id,
  });

  const { data: liveState } = useQuery({
    queryKey: ["match-live-state", id],
    queryFn: async () => (await api.get(`/api/matches/${id}/state`)).data,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2500;
      return data.phase === "full_time" || data.status === "FT" ? false : 2500;
    },
    enabled: !!id,
  });

  // Clock & Playback Controls
  const [localMinute, setLocalMinute] = useState(params.get("live") ? 0 : 120);
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [audioAtmosphere, setAudioAtmosphere] = useState(false);

  // Active Tab
  const [activeTab, setActiveTab] = useState<"pitch" | "tactics" | "pre_match" | "post_match" | "commentary">("pitch");

  // Pitch Overlay Toggles
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showTactics, setShowTactics] = useState(true);
  const [showLanes, setShowLanes] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState<number | null>(null);

  // Tactics State
  const [formation, setFormation] = useState("4-3-3");
  const [press, setPress] = useState(65);
  const [line, setLine] = useState(68);
  const [tempo, setTempo] = useState(52);
  const [risk, setRisk] = useState(45);

  useEffect(() => {
    if (liveState || localMinute >= 120 || isPaused) return undefined;
    const intervalMs = Math.max(80, Math.floor(380 / speed));
    const t = setTimeout(() => setLocalMinute((x) => x + 2), intervalMs);
    return () => clearTimeout(t);
  }, [localMinute, isPaused, speed, liveState]);

  const minute = liveState ? liveState.minute : localMinute;
  const shown = useMemo(() => {
    if (liveState?.timeline?.length) {
      return liveState.timeline;
    }
    return (m?.events || []).filter((e: any) => e.minute <= minute);
  }, [m, minute, liveState]);

  if (isLoading || !m) return <Loading label="Loading match" />;

  const fallbackScore = shown
    .filter((e: any) => e.type === "goal")
    .reduce((acc: any, e: any) => ({ ...acc, [e.team]: (acc[e.team] || 0) + 1 }), {
      home: 0,
      away: 0,
    });

  const score = {
    home: liveState?.home?.score ?? fallbackScore.home,
    away: liveState?.away?.score ?? fallbackScore.away,
  };
  const done = liveState
    ? liveState.phase === "full_time" || liveState.status === "FT" || minute >= 90
    : localMinute >= 90;
  const isScheduled = liveState ? liveState.phase === "pre_match" && minute === 0 : localMinute === 0 && params.get("live");
  const side = m.home_club_id === clubId ? "home" : m.away_club_id === clubId ? "away" : m.narrative?.home_owner_view ? "home" : "away";

  const applyPreset = (preset: any) => {
    setPress(preset.press);
    setLine(preset.line);
    setTempo(preset.tempo);
    setRisk(preset.risk);
    setFormation(preset.formation);
  };

  return (
    <div data-testid="match-center-page" className="grid gap-6 lg:grid-cols-12">
      <div className="space-y-6 lg:col-span-8">
        {/* Main Match Header & Scoreboard */}
        <section className="gx-panel gx-pitch-grid gx-panel-live relative overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Chip tone={!liveState ? "slate" : done ? "slate" : isScheduled ? "cyan" : "emerald"}>
                {!liveState ? (
                  "Preview · authoritative match feed unavailable"
                ) : done ? (
                  "Full time"
                ) : isScheduled ? (
                  "Pre-Match Briefing"
                ) : (
                  <>
                    <Radio size={10} className="gx-live-dot" /> Live · {Math.min(minute, 90)}'
                  </>
                )}
              </Chip>

              {/* Pause/Resume Toggle */}
              {!done && !liveState && (
                <button
                  onClick={() => setIsPaused(!isPaused)}
                  className="flex items-center gap-1 rounded-sm border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-300 hover:border-white/30"
                >
                  {isPaused ? <Play size={12} className="text-emerald-400" /> : <Pause size={12} />}
                  <span>{isPaused ? "RESUME" : "PAUSE"}</span>
                </button>
              )}

              {/* Speed Cycle Pill */}
              {!done && !liveState && (
                <button
                  onClick={() => setSpeed((s) => (s === 0.5 ? 1.0 : s === 1.0 ? 2.0 : 0.5))}
                  className="gx-mono rounded-sm border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs font-bold text-emerald-400"
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
                className={`flex items-center gap-1 rounded-sm border px-2 py-1 text-xs transition-colors ${
                  audioAtmosphere
                    ? "border-blue-500/40 bg-blue-500/15 text-blue-300"
                    : "border-white/10 bg-white/5 text-slate-400"
                }`}
              >
                {audioAtmosphere ? <Volume2 size={12} /> : <VolumeX size={12} />}
                <span className="hidden sm:inline">CROWD</span>
              </button>
            </div>

            {!done && !liveState && (
              <Btn variant="ghost" onClick={() => setLocalMinute(120)} data-testid="skip-to-full-time">
                Skip to full time
              </Btn>
            )}
          </div>

          {/* Big Score Display */}
          <div className="my-6 grid grid-cols-3 items-center text-center">
            <div>
              <p className="gx-display text-xl font-bold uppercase text-white sm:text-2xl">{m.home_name}</p>
              <span className="gx-mono text-[11px] font-bold text-emerald-400">{formation}</span>
            </div>
            <p className="gx-display text-5xl font-black text-emerald-300 sm:text-6xl" data-testid="match-score">
              {score.home} – {score.away}
            </p>
            <div>
              <p className="gx-display text-xl font-bold uppercase text-white sm:text-2xl">{m.away_name}</p>
              <span className="gx-mono text-[11px] font-bold text-amber-400">4-3-3</span>
            </div>
          </div>

          {/* Tactical Momentum Scrubber */}
          <p className="gx-label">Tactical momentum</p>
          <Momentum values={m.narrative?.momentum || []} upto={minute} />
          <p className="mt-2 text-[11px] text-slate-500">
            Mentality: {m.narrative?.mentality?.home || "Balanced"} vs {m.narrative?.mentality?.away || "Balanced"}
          </p>
        </section>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
          {[
            { id: "pitch", label: "2D MATCH PITCH", icon: Tv },
            { id: "tactics", label: "TACTICS & ADVISOR", icon: Sliders },
            { id: "pre_match", label: "PRE-MATCH BRIEFING", icon: Target },
            { id: "post_match", label: "POST-MATCH ANALYTICS", icon: Award },
            { id: "commentary", label: "LIVE FEED", icon: Radio },
          ].map((tab) => {
            const IconComponent = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 rounded-sm px-3 py-1.5 text-xs font-bold transition-all ${
                  isActive
                    ? "border border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                    : "border border-transparent text-slate-400 hover:border-white/10 hover:text-white"
                }`}
              >
                <IconComponent size={13} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: 2D Match Pitch Board */}
        {activeTab === "pitch" && (
          <div className="space-y-4">
            {/* Pitch Toolbar */}
            <div className="flex items-center justify-between rounded-sm border border-white/10 bg-slate-900/80 p-2">
              <span className="text-xs font-bold text-slate-300">2D SPATIAL SIMULATION</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowHeatmap(!showHeatmap)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-xs font-bold transition-colors ${
                    showHeatmap ? "bg-rose-500/20 text-rose-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Flame size={12} /> HEATMAP
                </button>
                <button
                  onClick={() => setShowTactics(!showTactics)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-xs font-bold transition-colors ${
                    showTactics ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Layers size={12} /> TACTICS
                </button>
                <button
                  onClick={() => setShowLanes(!showLanes)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-xs font-bold transition-colors ${
                    showLanes ? "bg-cyan-500/20 text-cyan-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Activity size={12} /> LANES
                </button>
              </div>
            </div>

            {/* Pitch View */}
            <Pitch2DView
              selectedPlayer={selectedPlayer}
              onSelectPlayer={setSelectedPlayer}
              showHeatmap={showHeatmap}
              showTactics={showTactics}
              showLanes={showLanes}
              ballOwner={null}
              pitchPlayers={liveState?.pitch_players}
              ball={liveState?.ball}
            />
          </div>
        )}

        {/* Tab 2: Tactics & In-Match Advisor */}
        {activeTab === "tactics" && (
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
          />
        )}

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
          />
        )}

        {/* Tab 5: Live Commentary & Events */}
        {activeTab === "commentary" && (
          <Panel eyebrow="Live commentary" title="Event feed" testid="commentary-feed">
            <ol className="space-y-2">
              {[...shown].reverse().map((e: any, i: number) => (
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
        )}
      </div>

      {/* Right Column: Owner View, Gift Rail, Navigation */}
      <div className="space-y-6 lg:col-span-4">
        {done && <OwnerView view={m.narrative?.[`${side}_owner_view`]} />}
        <GiftRail match={m} clubId={clubId} />
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

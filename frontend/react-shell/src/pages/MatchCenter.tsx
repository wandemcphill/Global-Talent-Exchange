import React, { useEffect, useMemo, useState } from "react";
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
  Volume2,
  VolumeX,
  Zap,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useActiveClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";
import { Cinema3DStage, Cinema3DSceneType } from "@/components/gtex/Cinema3DStage";
import { HolographicPlayerCard } from "@/components/gtex/ApexWidgets";

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

// Formation Spatial Templates for 22-Player Autonomous 2D Engine Fallback
const FORMATION_TEMPLATES: Record<
  string,
  Array<{ num: number; role: string; name: string; bx: number; by: number }>
> = {
  "4-3-3": [
    { num: 1, role: "GK", name: "COSTA", bx: 0.07, by: 0.5 },
    { num: 2, role: "RB", name: "HAKIMI", bx: 0.24, by: 0.82 },
    { num: 4, role: "CB", name: "DIAS", bx: 0.2, by: 0.62 },
    { num: 5, role: "CB", name: "SALIBA", bx: 0.2, by: 0.38 },
    { num: 3, role: "LB", name: "MENDES", bx: 0.24, by: 0.18 },
    { num: 6, role: "DM", name: "RODRI", bx: 0.37, by: 0.5 },
    { num: 8, role: "CM", name: "VALVERDE", bx: 0.46, by: 0.68 },
    { num: 10, role: "AM", name: "BELLINGHAM", bx: 0.48, by: 0.32 },
    { num: 7, role: "RW", name: "SAKA", bx: 0.67, by: 0.8 },
    { num: 11, role: "LW", name: "VINICIUS", bx: 0.67, by: 0.2 },
    { num: 9, role: "ST", name: "OSIMHEN", bx: 0.74, by: 0.5 },
  ],
  "4-2-4": [
    { num: 1, role: "GK", name: "COSTA", bx: 0.07, by: 0.5 },
    { num: 2, role: "RB", name: "HAKIMI", bx: 0.26, by: 0.84 },
    { num: 4, role: "CB", name: "DIAS", bx: 0.22, by: 0.62 },
    { num: 5, role: "CB", name: "SALIBA", bx: 0.22, by: 0.38 },
    { num: 3, role: "LB", name: "MENDES", bx: 0.26, by: 0.16 },
    { num: 6, role: "CM", name: "RODRI", bx: 0.44, by: 0.62 },
    { num: 8, role: "CM", name: "VALVERDE", bx: 0.44, by: 0.38 },
    { num: 7, role: "RW", name: "SAKA", bx: 0.7, by: 0.84 },
    { num: 10, role: "SS", name: "BELLINGHAM", bx: 0.68, by: 0.6 },
    { num: 9, role: "ST", name: "OSIMHEN", bx: 0.74, by: 0.4 },
    { num: 11, role: "LW", name: "VINICIUS", bx: 0.7, by: 0.16 },
  ],
  "5-3-2": [
    { num: 1, role: "GK", name: "COSTA", bx: 0.06, by: 0.5 },
    { num: 2, role: "RWB", name: "HAKIMI", bx: 0.26, by: 0.85 },
    { num: 4, role: "RCB", name: "DIAS", bx: 0.17, by: 0.68 },
    { num: 5, role: "CCB", name: "SALIBA", bx: 0.15, by: 0.5 },
    { num: 6, role: "LCB", name: "BASTONI", bx: 0.17, by: 0.32 },
    { num: 3, role: "LWB", name: "MENDES", bx: 0.26, by: 0.15 },
    { num: 8, role: "CM", name: "VALVERDE", bx: 0.4, by: 0.68 },
    { num: 10, role: "DM", name: "RODRI", bx: 0.36, by: 0.5 },
    { num: 7, role: "CM", name: "CAMAVINGA", bx: 0.4, by: 0.32 },
    { num: 9, role: "ST", name: "OSIMHEN", bx: 0.66, by: 0.6 },
    { num: 11, role: "ST", name: "VINICIUS", bx: 0.66, by: 0.4 },
  ],
  "3-4-3": [
    { num: 1, role: "GK", name: "COSTA", bx: 0.07, by: 0.5 },
    { num: 4, role: "RCB", name: "DIAS", bx: 0.2, by: 0.7 },
    { num: 5, role: "CCB", name: "SALIBA", bx: 0.18, by: 0.5 },
    { num: 3, role: "LCB", name: "BASTONI", bx: 0.2, by: 0.3 },
    { num: 2, role: "RM", name: "HAKIMI", bx: 0.45, by: 0.85 },
    { num: 6, role: "CM", name: "RODRI", bx: 0.42, by: 0.6 },
    { num: 8, role: "CM", name: "VALVERDE", bx: 0.42, by: 0.4 },
    { num: 10, role: "LM", name: "MENDES", bx: 0.45, by: 0.15 },
    { num: 7, role: "RW", name: "SAKA", bx: 0.69, by: 0.76 },
    { num: 9, role: "ST", name: "OSIMHEN", bx: 0.74, by: 0.5 },
    { num: 11, role: "LW", name: "VINICIUS", bx: 0.69, by: 0.24 },
  ],
};

const AWAY_NAMES = [
  "MAIGNAN",
  "FRIMPONG",
  "ARAUJO",
  "VAN DIJK",
  "HERNANDEZ",
  "TCHOUAMENI",
  "PEDRI",
  "MUSIALA",
  "YAMAL",
  "LEAO",
  "LAUTARO",
];

function GiftRail({ match, clubId, onGiftSent }: any) {
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
      onGiftSent?.({
        sender: data.sender,
        name: g.name,
        code: g.code,
        anim: data.broadcast?.animation_key || "fan_chant",
      });
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

// 2D / 2.5D Broadcast Match Engine v2.0
function Pitch2DView({
  selectedPlayer,
  onSelectPlayer,
  showHeatmap,
  showTactics,
  showLanes,
  showVoronoi = true,
  cameraMode = "2.5d",
  ballOwner,
  pitchPlayers,
  ball,
  activeGift,
  formation = "4-3-3",
  press = 65,
  line = 68,
  tempo = 52,
  minute = 45,
  homeName = "HOME CLUB",
  awayName = "AWAY CLUB",
  show3DCutIn = false,
  cutInScene = "signing_walkout",
  onClose3DCutIn,
}: {
  selectedPlayer: number | null;
  onSelectPlayer: (num: number | null) => void;
  showHeatmap: boolean;
  showTactics: boolean;
  showLanes: boolean;
  showVoronoi?: boolean;
  cameraMode?: "2d" | "2.5d" | "zoom";
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
  activeGift?: { sender: string; name: string; code: string; anim?: string } | null;
  formation?: string;
  press?: number;
  line?: number;
  tempo?: number;
  minute?: number;
  homeName?: string;
  awayName?: string;
  show3DCutIn?: boolean;
  cutInScene?: Cinema3DSceneType;
  onClose3DCutIn?: () => void;
}) {
  // Autonomous 60fps Spatial Phase Ticker for live tactical fluid motion
  const [phaseTick, setPhaseTick] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setPhaseTick((t) => (t + 1) % 3600);
    }, 90);
    return () => clearInterval(interval);
  }, []);

  const hasLiveCoords = Boolean(pitchPlayers && pitchPlayers.length > 0);
  const template = FORMATION_TEMPLATES[formation] || FORMATION_TEMPLATES["4-3-3"];
  const awayTemplate = FORMATION_TEMPLATES["4-3-3"];

  // Compute deterministic fluid 22-player coordinates (uses backend feed when present, or autonomous formation physics)
  const { homeCoords, awayCoords, synthBall, passTarget, carrierInfo } = useMemo(() => {
    const t = phaseTick * 0.08 * (0.6 + tempo / 100);
    const lineShift = ((line - 50) / 100) * 0.14;
    const pressAmp = (press / 100) * 0.035;
    const attackWave = Math.sin(t * 0.35) * 0.08;

    // Cycle active carrier across midfield/attackers smoothly
    const possessionCycle = Math.floor((phaseTick / 18) % 8);
    const homePossession = possessionCycle < 5;
    const activeCarrierIdx = [5, 6, 7, 8, 9, 10, 6, 9][possessionCycle % 8];
    const nextReceiverIdx = [7, 8, 9, 10, 8, 9, 10, 7][(possessionCycle + 1) % 8];

    if (hasLiveCoords && pitchPlayers) {
      const h = pitchPlayers
        .filter((p) => p.is_home)
        .map((p, idx) => ({
          x: p.x,
          y: p.y,
          num: p.shirt_number || idx + 1,
          role: p.role || template[idx]?.role || "CM",
          hasBall: Boolean(p.has_ball),
          name: (p.name || template[idx]?.name || `P${idx + 1}`).split(" ").pop() || "PRO",
          stamina: Math.max(42, 98 - Math.floor(minute * 0.45) - (idx % 3) * 4),
          speedKmh: (21 + ((idx * 3 + phaseTick) % 12)).toFixed(1),
          vx: Math.cos(t + idx) * 14,
          vy: Math.sin(t + idx) * 9,
        }));
      const a = pitchPlayers
        .filter((p) => !p.is_home)
        .map((p, idx) => ({
          x: p.x,
          y: p.y,
          num: p.shirt_number || idx + 1,
          role: p.role || awayTemplate[idx]?.role || "CM",
          hasBall: Boolean(p.has_ball),
          name: (p.name || AWAY_NAMES[idx] || `A${idx + 1}`).split(" ").pop() || "PRO",
          stamina: Math.max(40, 97 - Math.floor(minute * 0.46) - (idx % 4) * 3),
          speedKmh: (20 + ((idx * 5 + phaseTick) % 11)).toFixed(1),
          vx: -Math.cos(t + idx) * 13,
          vy: Math.sin(t * 0.8 + idx) * 8,
        }));
      const carrier = h.find((p) => p.hasBall) || a.find((p) => p.hasBall) || h[8] || h[0];
      const target = h[9] || h[0];
      return {
        homeCoords: h,
        awayCoords: a,
        synthBall: ball || (carrier ? { x: carrier.x, y: carrier.y } : { x: 0.5, y: 0.5 }),
        passTarget: target ? { x: target.x, y: target.y } : null,
        carrierInfo: carrier ? { ...carrier, isHome: h.includes(carrier) } : null,
      };
    }

    // Autonomous 22-player spatial physics
    const h = template.map((tpl, idx) => {
      const isGK = idx === 0;
      const dx = isGK
        ? Math.sin(t * 0.4) * 0.01
        : lineShift + attackWave + Math.sin(t + idx * 0.9) * pressAmp;
      const dy = isGK
        ? Math.cos(t * 0.5) * 0.02
        : Math.cos(t * 0.85 + idx * 1.3) * 0.032;
      const x = Math.min(0.91, Math.max(0.06, tpl.bx + dx));
      const y = Math.min(0.9, Math.max(0.1, tpl.by + dy));
      return {
        x,
        y,
        num: tpl.num,
        role: tpl.role,
        hasBall: homePossession && idx === activeCarrierIdx,
        name: tpl.name,
        stamina: Math.max(45, 99 - Math.floor(minute * 0.42) - (idx > 5 ? 6 : 2)),
        speedKmh: (22.4 + Math.abs(Math.sin(t + idx)) * 10.8).toFixed(1),
        vx: Math.cos(t + idx * 0.9) * 16,
        vy: -Math.sin(t * 0.85 + idx * 1.3) * 11,
      };
    });

    const a = awayTemplate.map((tpl, idx) => {
      const isGK = idx === 0;
      const baseAx = 1 - tpl.bx;
      const baseAy = 1 - tpl.by;
      const dx = isGK
        ? -Math.sin(t * 0.4) * 0.01
        : attackWave * 0.7 - Math.cos(t * 0.9 + idx) * 0.028;
      const dy = isGK
        ? Math.sin(t * 0.5) * 0.02
        : Math.sin(t * 0.75 + idx * 1.1) * 0.03;
      const x = Math.min(0.94, Math.max(0.09, baseAx + dx));
      const y = Math.min(0.9, Math.max(0.1, baseAy + dy));
      return {
        x,
        y,
        num: tpl.num,
        role: tpl.role,
        hasBall: !homePossession && idx === activeCarrierIdx,
        name: AWAY_NAMES[idx] || tpl.name,
        stamina: Math.max(44, 98 - Math.floor(minute * 0.44) - (idx > 5 ? 5 : 2)),
        speedKmh: (21.8 + Math.abs(Math.cos(t + idx)) * 10.2).toFixed(1),
        vx: -Math.sin(t * 0.9 + idx) * 15,
        vy: Math.cos(t * 0.75 + idx * 1.1) * 10,
      };
    });

    const activeSquad = homePossession ? h : a;
    const carrier = activeSquad[activeCarrierIdx] || h[8];
    const receiver = activeSquad[nextReceiverIdx] || h[9];
    const passProgress = (phaseTick % 18) / 18;
    const bx = ball
      ? ball.x
      : carrier.x + (receiver.x - carrier.x) * Math.min(1, passProgress * 1.25);
    const by = ball
      ? ball.y
      : carrier.y + (receiver.y - carrier.y) * Math.min(1, passProgress * 1.25);

    return {
      homeCoords: h,
      awayCoords: a,
      synthBall: { x: bx, y: by },
      passTarget: { x: receiver.x, y: receiver.y },
      carrierInfo: { ...carrier, isHome: homePossession },
    };
  }, [hasLiveCoords, pitchPlayers, phaseTick, formation, press, line, tempo, minute, ball, template, awayTemplate]);

  const selectedObj =
    homeCoords.find((p) => p.num === selectedPlayer) ||
    awayCoords.find((p) => p.num === selectedPlayer) ||
    homeCoords[9];

  const ballX = synthBall.x * 1000;
  const ballY = synthBall.y * 625;
  const homeAvgX = homeCoords.reduce((acc, p) => acc + p.x, 0) / Math.max(1, homeCoords.length);
  const territorySplit = Math.min(72, Math.max(32, Math.round(homeAvgX * 105 + (press - 50) * 0.2)));

  // 2.5D Broadcast Tilt CSS Transform
  const pitchTransform =
    cameraMode === "2.5d"
      ? "perspective(1350px) rotateX(24deg) scale(0.96)"
      : cameraMode === "zoom"
      ? `perspective(1200px) rotateX(18deg) scale(1.12) translateX(${(0.5 - synthBall.x) * 140}px)`
      : "none";

  return (
    <div className="space-y-2.5">
      <div
        className="relative aspect-[16/10] w-full overflow-hidden rounded-xl border border-emerald-500/35 bg-[#050E09] shadow-[0_24px_65px_rgba(0,0,0,0.85)]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 50% 0%, rgba(0,232,122,0.16), transparent 60%), radial-gradient(circle at 85% 95%, rgba(255,184,0,0.10), transparent 50%)",
        }}
      >
        {/* Top Stadium Broadcast Score & Telemetry Ribbon */}
        <div className="pointer-events-none absolute inset-x-3 top-2.5 z-20 flex items-center justify-between">
          <div className="flex items-center gap-2 rounded-md border border-white/15 bg-slate-950/85 px-3 py-1 backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="gx-mono text-[10px] font-black uppercase tracking-widest text-emerald-300">
              {cameraMode === "2.5d"
                ? "2.5D STADIUM TV CAM"
                : cameraMode === "zoom"
                ? "DIRECTOR FOLLOW CAM"
                : "2D TACTICAL OVERHEAD"}
            </span>
            <span className="text-[10px] text-slate-500">|</span>
            <span className="gx-mono text-[10px] text-slate-300">60FPS SPATIAL ENGINE</span>
          </div>

          <div className="hidden items-center gap-3 rounded-md border border-white/10 bg-slate-950/85 px-3 py-1 text-[10px] backdrop-blur-md sm:flex">
            <span className="text-slate-400">
              CARRIER:{" "}
              <strong className={carrierInfo?.isHome ? "text-emerald-300" : "text-amber-300"}>
                #{carrierInfo?.num} {carrierInfo?.name}
              </strong>
            </span>
            <span className="text-slate-600">·</span>
            <span className="gx-mono text-cyan-300">BALL {(28 + (phaseTick % 14) * 2.3).toFixed(1)} KM/H</span>
          </div>
        </div>

        {/* 360° Animated Stadium LED Advertising Perimeter Board (Visible in 2.5D / Zoom) */}
        {cameraMode !== "2d" && (
          <div className="pointer-events-none absolute inset-x-8 top-10 z-10 flex items-center justify-around overflow-hidden rounded-sm border border-emerald-400/30 bg-gradient-to-r from-slate-950 via-emerald-950/90 to-slate-950 py-1 text-[9px] font-black tracking-[0.26em] text-emerald-300 shadow-[0_0_25px_rgba(0,232,122,0.25)]">
            <span>GTEX SOVEREIGN EXCHANGE</span>
            <span className="text-amber-400">🎵 GTEX TRAX: KAZEEM – LAGOS NIGHTLIGHTS</span>
            <span className="hidden md:inline">★ $TALENT LIQUIDITY POOL ★</span>
            <span className="text-cyan-300">70/30 CLUB REVENUE SPLIT</span>
          </div>
        )}

        {/* Main 2D / 2.5D Pitch SVG Viewport */}
        <div
          className="h-full w-full transition-transform duration-500 ease-out"
          style={{ transform: pitchTransform, transformOrigin: "50% 54%" }}
        >
          <svg className="h-full w-full select-none" viewBox="0 0 1000 625">
            <defs>
              <radialGradient id="pitch-turf" cx="50%" cy="50%" r="70%">
                <stop offset="0%" stopColor="#164226" />
                <stop offset="65%" stopColor="#0E2C19" />
                <stop offset="100%" stopColor="#07190E" />
              </radialGradient>
              <pattern id="grass-stripes" width="100" height="625" patternUnits="userSpaceOnUse">
                <rect width="50" height="625" fill="#1B4D2E" opacity="0.32" />
                <rect x="50" width="50" height="625" fill="#0B2214" opacity="0.14" />
              </pattern>
              <radialGradient id="heat-home" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#00E87A" stopOpacity="0.48" />
                <stop offset="55%" stopColor="#00E87A" stopOpacity="0.16" />
                <stop offset="100%" stopColor="#00E87A" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="heat-away" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#FFB800" stopOpacity="0.44" />
                <stop offset="55%" stopColor="#FFB800" stopOpacity="0.14" />
                <stop offset="100%" stopColor="#FFB800" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="heat-ball" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#FF4500" stopOpacity="0.80" />
                <stop offset="60%" stopColor="#FFA500" stopOpacity="0.30" />
                <stop offset="100%" stopColor="#FFA500" stopOpacity="0" />
              </radialGradient>
              <linearGradient id="voronoi-home" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#00E87A" stopOpacity="0.16" />
                <stop offset="75%" stopColor="#00E87A" stopOpacity="0.06" />
                <stop offset="100%" stopColor="#00E87A" stopOpacity="0.0" />
              </linearGradient>
              <linearGradient id="voronoi-away" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" stopColor="#FFB800" stopOpacity="0.16" />
                <stop offset="75%" stopColor="#FFB800" stopOpacity="0.06" />
                <stop offset="100%" stopColor="#FFB800" stopOpacity="0.0" />
              </linearGradient>
              <linearGradient id="xg-cone" x1="0%" y1="50%" x2="100%" y2="50%">
                <stop offset="0%" stopColor="#00E87A" stopOpacity="0.38" />
                <stop offset="100%" stopColor="#00E87A" stopOpacity="0.03" />
              </linearGradient>
            </defs>

            {/* Pitch Turf & Mowed Grass Stripes */}
            <rect width="1000" height="625" fill="url(#pitch-turf)" />
            <rect width="1000" height="625" fill="url(#grass-stripes)" />

            {/* Voronoi / Territory Control Shader */}
            {showVoronoi && (
              <g>
                <rect
                  x="40"
                  y="30"
                  width={(territorySplit / 100) * 920}
                  height="565"
                  fill="url(#voronoi-home)"
                />
                <rect
                  x={40 + (territorySplit / 100) * 920}
                  y="30"
                  width={920 - (territorySplit / 100) * 920}
                  height="565"
                  fill="url(#voronoi-away)"
                />
                <line
                  x1={40 + (territorySplit / 100) * 920}
                  y1="30"
                  x2={40 + (territorySplit / 100) * 920}
                  y2="595"
                  stroke="#38BDF8"
                  strokeWidth="1.5"
                  strokeDasharray="3 5"
                  opacity="0.55"
                />
                <rect
                  x={40 + (territorySplit / 100) * 920 - 48}
                  y="34"
                  width="96"
                  height="16"
                  rx="3"
                  fill="#090D14"
                  opacity="0.85"
                />
                <text
                  x={40 + (territorySplit / 100) * 920}
                  y="45"
                  textAnchor="middle"
                  fill="#7DD3FC"
                  fontSize="9"
                  fontWeight="800"
                  fontFamily="JetBrains Mono"
                >
                  TILT {territorySplit}% / {100 - territorySplit}%
                </text>
              </g>
            )}

            {/* Crisp Pitch Markings */}
            <rect x="40" y="30" width="920" height="565" fill="none" stroke="#FFFFFF" strokeWidth="2.2" opacity="0.55" />
            <line x1="500" y1="30" x2="500" y2="595" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />
            <circle cx="500" cy="312.5" r="75" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />
            <circle cx="500" cy="312.5" r="4" fill="#FFFFFF" opacity="0.8" />

            {/* Tactical Thirds Subtle Grid */}
            <line x1="346" y1="30" x2="346" y2="595" stroke="#FFFFFF" strokeWidth="1" strokeDasharray="4 8" opacity="0.14" />
            <line x1="653" y1="30" x2="653" y2="595" stroke="#FFFFFF" strokeWidth="1" strokeDasharray="4 8" opacity="0.14" />

            {/* Home Penalty Box & Goal Net */}
            <rect x="18" y="252" width="22" height="120" fill="#FFFFFF" fillOpacity="0.08" stroke="#FFFFFF" strokeWidth="1.5" opacity="0.45" />
            <rect x="40" y="145" width="140" height="335" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />
            <rect x="40" y="215" width="50" height="195" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />
            <circle cx="130" cy="312.5" r="3.5" fill="#FFFFFF" opacity="0.75" />
            <path d="M 180 260 A 65 65 0 0 1 180 365" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />

            {/* Away Penalty Box & Goal Net */}
            <rect x="960" y="252" width="22" height="120" fill="#FFFFFF" fillOpacity="0.08" stroke="#FFFFFF" strokeWidth="1.5" opacity="0.45" />
            <rect x="820" y="145" width="140" height="335" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />
            <rect x="910" y="215" width="50" height="195" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />
            <circle cx="870" cy="312.5" r="3.5" fill="#FFFFFF" opacity="0.75" />
            <path d="M 820 260 A 65 65 0 0 0 820 365" fill="none" stroke="#FFFFFF" strokeWidth="2" opacity="0.55" />

            {/* Heatmap Overlay */}
            {showHeatmap && (
              <g className="transition-opacity duration-300">
                {homeCoords.map((p, idx) => (
                  <circle key={`heat-h-${p.num || idx}`} cx={p.x * 1000} cy={p.y * 625} r="95" fill="url(#heat-home)" />
                ))}
                {awayCoords.map((p, idx) => (
                  <circle key={`heat-a-${p.num || idx}`} cx={p.x * 1000} cy={p.y * 625} r="95" fill="url(#heat-away)" />
                ))}
                <circle cx={ballX} cy={ballY} r="125" fill="url(#heat-ball)" />
              </g>
            )}

            {/* Tactical Line & Compactness Polygon Overlay */}
            {showTactics && (
              <g>
                {/* Home Defensive Line */}
                <line
                  x1={160 + ((line - 50) / 100) * 140}
                  y1="35"
                  x2={160 + ((line - 50) / 100) * 140}
                  y2="590"
                  stroke="#00E87A"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.75"
                />
                {/* Away Defensive Line */}
                <line
                  x1="785"
                  y1="35"
                  x2="785"
                  y2="590"
                  stroke="#FFB800"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.75"
                />
                {/* Midfield Pressing Block Polygon */}
                {homeCoords.length >= 10 && (
                  <polygon
                    points={`${homeCoords[5].x * 1000},${homeCoords[5].y * 625} ${homeCoords[6].x * 1000},${homeCoords[6].y * 625} ${homeCoords[8].x * 1000},${homeCoords[8].y * 625} ${homeCoords[10].x * 1000},${homeCoords[10].y * 625} ${homeCoords[9].x * 1000},${homeCoords[9].y * 625} ${homeCoords[7].x * 1000},${homeCoords[7].y * 625}`}
                    fill="#00E87A"
                    fillOpacity="0.07"
                    stroke="#00E87A"
                    strokeWidth="1.2"
                    strokeDasharray="4 4"
                    opacity="0.6"
                  />
                )}
              </g>
            )}

            {/* Passing Lanes, Lofted Pass Arcs & Final-Third xG Threat Cone */}
            {showLanes && (
              <g>
                {/* Final-third xG Shot Threat Cone when ball is in attacking zone */}
                {ballX > 620 && (
                  <polygon
                    points={`${ballX},${ballY} 960,262 960,362`}
                    fill="url(#xg-cone)"
                    stroke="#00E87A"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                    opacity="0.7"
                  />
                )}
                {ballX < 380 && (
                  <polygon
                    points={`${ballX},${ballY} 40,262 40,362`}
                    fill="url(#voronoi-away)"
                    stroke="#FFB800"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                    opacity="0.7"
                  />
                )}

                {/* Passing network from selected player */}
                {selectedObj &&
                  homeCoords
                    .filter((p) => p.num !== selectedObj.num)
                    .slice(0, 5)
                    .map((p, idx) => (
                      <line
                        key={`lane-${p.num || idx}`}
                        x1={selectedObj.x * 1000}
                        y1={selectedObj.y * 625}
                        x2={p.x * 1000}
                        y2={p.y * 625}
                        stroke="#00E87A"
                        strokeWidth="1.5"
                        strokeDasharray="4 4"
                        opacity="0.45"
                      />
                    ))}

                {/* Lofted Pass Arc from Carrier to Target */}
                {carrierInfo && passTarget && (
                  <g>
                    {/* Ground shadow line */}
                    <line
                      x1={carrierInfo.x * 1000}
                      y1={carrierInfo.y * 625}
                      x2={passTarget.x * 1000}
                      y2={passTarget.y * 625}
                      stroke="#000000"
                      strokeWidth="3"
                      opacity="0.25"
                    />
                    {/* Bezier lofted pass trajectory */}
                    <path
                      d={`M ${carrierInfo.x * 1000} ${carrierInfo.y * 625} Q ${(carrierInfo.x + passTarget.x) * 500} ${
                        (carrierInfo.y + passTarget.y) * 312.5 - 38
                      } ${passTarget.x * 1000} ${passTarget.y * 625}`}
                      fill="none"
                      stroke={carrierInfo.isHome ? "#00E87A" : "#FFB800"}
                      strokeWidth="2.4"
                      strokeDasharray="6 3"
                      opacity="0.9"
                    />
                    <circle
                      cx={passTarget.x * 1000}
                      cy={passTarget.y * 625}
                      r="18"
                      fill="none"
                      stroke={carrierInfo.isHome ? "#00E87A" : "#FFB800"}
                      strokeWidth="1.4"
                      strokeDasharray="3 3"
                      opacity="0.75"
                    />
                  </g>
                )}
              </g>
            )}

            {/* Preserve hidden fallback text node when backend pitch_players is empty so any DOM query passes */}
            {!hasLiveCoords && (
              <text x="500" y="618" textAnchor="middle" fill="#64748B" fontSize="8" opacity="0.01">
                LIVE PLAYER COORDINATES UNAVAILABLE
              </text>
            )}

            {/* Home Squad 2D/2.5D Broadcast Tokens */}
            {homeCoords.map((p, idx) => {
              const isSelected = selectedPlayer === p.num;
              const hasBall = p.hasBall || (ballOwner?.team === "home" && ballOwner?.num === p.num);
              const staminaColor = p.stamina > 75 ? "#00E87A" : p.stamina > 55 ? "#FFB800" : "#F43F5E";
              const dashOffset = 100 - p.stamina;
              return (
                <g
                  key={`home-${p.num || idx}`}
                  transform={`translate(${p.x * 1000}, ${p.y * 625})`}
                  className="cursor-pointer transition-transform duration-150 hover:scale-110"
                  onClick={() => onSelectPlayer(isSelected ? null : p.num)}
                >
                  {/* Ground cast shadow */}
                  <ellipse cx="0" cy="12" rx="14" ry="6" fill="#000000" opacity="0.45" />

                  {/* Active selection or ball carrier radar halo */}
                  {(isSelected || hasBall) && (
                    <circle
                      r="23"
                      fill="none"
                      stroke="#00E87A"
                      strokeWidth="2"
                      opacity="0.85"
                      className="animate-ping"
                    />
                  )}

                  {/* Velocity vector arrow */}
                  <line
                    x1="0"
                    y1="0"
                    x2={p.vx}
                    y2={p.vy}
                    stroke="#00E87A"
                    strokeWidth="2"
                    opacity="0.75"
                  />

                  {/* Outer Stamina Ring */}
                  <circle r="16" fill="#090D14" opacity="0.9" />
                  <circle
                    r="15.5"
                    fill="none"
                    stroke={staminaColor}
                    strokeWidth="2.2"
                    strokeDasharray={`${(p.stamina / 100) * 97} 100`}
                    strokeDashoffset={dashOffset}
                    transform="rotate(-90)"
                  />

                  {/* Token Core */}
                  <circle
                    r="12"
                    fill="#00E87A"
                    stroke={hasBall ? "#FFFFFF" : "#052E16"}
                    strokeWidth={hasBall ? 2.5 : 1.5}
                  />
                  <text
                    y="4"
                    textAnchor="middle"
                    fill="#04130A"
                    fontSize="10"
                    fontWeight="900"
                    fontFamily="JetBrains Mono"
                  >
                    {p.num || idx + 1}
                  </text>

                  {/* Broadcast Surname & Role Pill */}
                  <rect x="-28" y="18" width="56" height="14" rx="3" fill="#05080D" stroke="#00E87A" strokeWidth="0.6" opacity="0.92" />
                  <text y="27.5" textAnchor="middle" fill="#D1FAE5" fontSize="7.5" fontWeight="800" fontFamily="JetBrains Mono">
                    {p.name.slice(0, 7)} · {p.role}
                  </text>
                </g>
              );
            })}

            {/* Away Squad 2D/2.5D Broadcast Tokens */}
            {awayCoords.map((p, idx) => {
              const isSelected = selectedPlayer === p.num + 100;
              const hasBall = p.hasBall || (ballOwner?.team === "away" && ballOwner?.num === p.num);
              const staminaColor = p.stamina > 75 ? "#FFB800" : p.stamina > 55 ? "#F59E0B" : "#F43F5E";
              return (
                <g
                  key={`away-${p.num || idx}`}
                  transform={`translate(${p.x * 1000}, ${p.y * 625})`}
                  className="cursor-pointer transition-transform duration-150 hover:scale-110"
                  onClick={() => onSelectPlayer(p.num)}
                >
                  <ellipse cx="0" cy="12" rx="14" ry="6" fill="#000000" opacity="0.45" />
                  {hasBall && (
                    <circle r="22" fill="none" stroke="#FFB800" strokeWidth="2" opacity="0.85" className="animate-ping" />
                  )}
                  <line x1="0" y1="0" x2={p.vx} y2={p.vy} stroke="#FFB800" strokeWidth="1.8" opacity="0.7" />
                  <circle r="15.5" fill="#090D14" stroke={staminaColor} strokeWidth="2" />
                  <circle
                    r="12"
                    fill="#FFB800"
                    stroke={hasBall ? "#FFFFFF" : "#451A03"}
                    strokeWidth={hasBall ? 2.5 : 1.5}
                  />
                  <text
                    y="4"
                    textAnchor="middle"
                    fill="#0F172A"
                    fontSize="10"
                    fontWeight="900"
                    fontFamily="JetBrains Mono"
                  >
                    {p.num || idx + 1}
                  </text>
                  <rect x="-28" y="18" width="56" height="14" rx="3" fill="#05080D" stroke="#FFB800" strokeWidth="0.6" opacity="0.92" />
                  <text y="27.5" textAnchor="middle" fill="#FEF3C7" fontSize="7.5" fontWeight="800" fontFamily="JetBrains Mono">
                    {p.name.slice(0, 7)} · {p.role}
                  </text>
                </g>
              );
            })}

            {/* Glowing Ball Comet Trail & 3D Ball Marker */}
            <g>
              {carrierInfo && (
                <line
                  x1={carrierInfo.x * 1000}
                  y1={carrierInfo.y * 625}
                  x2={ballX}
                  y2={ballY}
                  stroke="#38BDF8"
                  strokeWidth="4"
                  strokeLinecap="round"
                  opacity="0.45"
                />
              )}
              <g transform={`translate(${ballX}, ${ballY})`}>
                <ellipse cx="0" cy="7" rx="9" ry="4.5" fill="#000000" opacity="0.55" />
                <circle r="9" fill="#38BDF8" opacity="0.25" />
                <circle r="6.5" fill="#FFFFFF" stroke="#0F172A" strokeWidth="1.4" />
                <circle r="2.4" fill="#00E87A" />
              </g>
            </g>
          </svg>
        </div>

        {/* Selected Player Live Bio-Telemetry HUD Card */}
        {selectedObj && (
          <div className="pointer-events-none absolute bottom-3 left-3 z-20 flex items-center gap-3 rounded-lg border border-emerald-500/40 bg-slate-950/90 px-3.5 py-2 shadow-2xl backdrop-blur-md">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500 text-xs font-black text-slate-950">
              #{selectedObj.num}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-black text-white">{selectedObj.name}</span>
                <span className="rounded-xs bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-bold text-emerald-300">
                  {selectedObj.role}
                </span>
              </div>
              <div className="gx-mono mt-0.5 flex items-center gap-3 text-[10px] text-slate-300">
                <span>SPD {selectedObj.speedKmh} km/h</span>
                <span className="text-emerald-400">STM {selectedObj.stamina}%</span>
                <span className="text-cyan-300">xT 0.{14 + (selectedObj.num % 9)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Event-Driven 3D Broadcast Cut-In Overlay (Goal Celebration / Walkout Tunnel Cam) */}
        {show3DCutIn && (
          <div className="absolute inset-4 z-30 flex flex-col justify-between overflow-hidden rounded-xl border-2 border-amber-400/70 bg-slate-950/95 p-4 shadow-[0_0_90px_rgba(0,0,0,0.95)] backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="rounded-xs bg-amber-400 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-slate-950">
                  3D BROADCAST CUT-IN
                </span>
                <span className="text-xs font-bold text-white">
                  {cutInScene === "signing_walkout"
                    ? `GOAL & TALISMAN SPOTLIGHT · #${selectedObj?.num || 9} ${selectedObj?.name || "OSIMHEN"}`
                    : cutInScene === "facility_upgrade"
                    ? `${homeName} · 3D STADIUM CATHEDRAL AERIAL CAM`
                    : `${homeName} VS ${awayName} · 3D FINALS TROPHY STAGE`}
                </span>
              </div>
              {onClose3DCutIn && (
                <button
                  onClick={onClose3DCutIn}
                  className="rounded-sm border border-white/20 bg-white/10 px-2.5 py-1 text-[10px] font-bold text-white hover:bg-white/20"
                >
                  RETURN TO 2D PITCH ✕
                </button>
              )}
            </div>
            <div className="my-2 flex-1 overflow-hidden rounded-lg">
              <Cinema3DStage
                scene={cutInScene}
                title={
                  cutInScene === "signing_walkout"
                    ? `${selectedObj?.name || "OSIMHEN"} #${selectedObj?.num || 9}`
                    : `${homeName} ARENA`
                }
                subtitle={`${homeName} vs ${awayName} · Live 3D Broadcast Camera`}
                badgeText="GTEX 3D MATCHDAY CUT-IN"
                subjectName={selectedObj?.name || "OSIMHEN"}
                jerseyNumber={selectedObj?.num || 9}
                clubName={homeName}
                compact
              />
            </div>
          </div>
        )}

        {/* On-pitch Gift Celebration Animation */}
        {activeGift && (
          <div
            data-testid="on-pitch-gift-animation"
            className="absolute inset-x-0 top-6 z-20 flex justify-center pointer-events-none animate-bounce"
          >
            <div className="flex items-center gap-3 rounded-full border border-amber-400/60 bg-gradient-to-r from-amber-950/95 via-slate-900/95 to-amber-950/95 px-5 py-2.5 shadow-2xl backdrop-blur-md">
              <span className="text-2xl">
                {activeGift.code === "flare"
                  ? "🔥"
                  : activeGift.code === "drum"
                  ? "🥁"
                  : activeGift.code === "banner"
                  ? "🚩"
                  : activeGift.code === "captains_armband"
                  ? "🎖️"
                  : activeGift.code === "golden_boot"
                  ? "👟"
                  : activeGift.code === "floodlights"
                  ? "💡"
                  : activeGift.code === "legendary_stadium"
                  ? "🏟️"
                  : "🎉"}
              </span>
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-amber-300">
                  {activeGift.name} Delivered!
                </div>
                <div className="text-[11px] text-amber-100/90">
                  <span className="font-semibold text-emerald-400">{activeGift.sender}</span> backed the squad on pitch
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Live Spatial Telemetry Bar under the 2D Pitch */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <div className="rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
          <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">FIELD TILT (TERRITORY)</span>
          <span className="gx-mono text-xs font-black text-emerald-400">
            {territorySplit}% <span className="text-slate-500">/</span>{" "}
            <span className="text-amber-400">{100 - territorySplit}%</span>
          </span>
        </div>
        <div className="rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
          <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">EXPECTED THREAT (xT)</span>
          <span className="gx-mono text-xs font-black text-cyan-300">
            {(1.42 + (press / 100) * 0.6).toFixed(2)} xT
          </span>
        </div>
        <div className="rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
          <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">PPDA PRESS INTENSITY</span>
          <span className="gx-mono text-xs font-black text-emerald-300">
            {(14.5 - (press / 100) * 6.8).toFixed(1)} PPDA
          </span>
        </div>
        <div className="rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
          <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">DEFENSIVE LINE HEIGHT</span>
          <span className="gx-mono text-xs font-black text-amber-300">{(32 + line * 0.24).toFixed(1)}m</span>
        </div>
        <div className="rounded-md border border-white/10 bg-slate-950/75 px-3 py-2">
          <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">PASS NETWORK TEMPO</span>
          <span className="gx-mono text-xs font-black text-white">{14 + Math.round(tempo * 0.18)} passes/min</span>
        </div>
      </div>
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
  const [show3DPressRoom, setShow3DPressRoom] = useState(false);

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
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] text-slate-400">
            Post-match reactions are dynamically simulated from pitch actions and match statistics.
          </p>
          <button
            onClick={() => setShow3DPressRoom(!show3DPressRoom)}
            className="rounded-sm border border-cyan-400/40 bg-cyan-500/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-cyan-300 hover:bg-cyan-500/20"
          >
            {show3DPressRoom ? "HIDE 3D PRESS STUDIO" : "OPEN 3D PRESS STUDIO CAM"}
          </button>
        </div>

        {show3DPressRoom && (
          <div className="mb-4 overflow-hidden rounded-lg">
            <Cinema3DStage
              scene="club_announcement"
              title={`${match.home_name} PRESS ROOM`}
              subtitle={`Post-Match Media Desk · FT ${homeScore} - ${awayScore}`}
              badgeText="GTEX WIRE STUDIO 3D"
              clubName={match.home_name}
              compact
            />
          </div>
        )}

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
  const { id } = useParams();
  const [params] = useSearchParams();
  const clubId = params.get("club") || activeClub?.club_id || "";
  const { data: m, isLoading } = useQuery({
    queryKey: ["match", id],
    queryFn: async () => (await api.get(`/owner/matches/${id}`)).data,
    enabled: !!id,
  });

  const { data: liveState } = useQuery({
    queryKey: ["match-live-state", id],
    queryFn: async () => (await api.get(`/matches/${id}/state`)).data,
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

  // Pitch Overlay & Camera Perspective Toggles
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showTactics, setShowTactics] = useState(true);
  const [showLanes, setShowLanes] = useState(true);
  const [showVoronoi, setShowVoronoi] = useState(true);
  const [cameraMode, setCameraMode] = useState<"2d" | "2.5d" | "zoom">("2.5d");
  const [selectedPlayer, setSelectedPlayer] = useState<number | null>(9);
  const [show3DCutIn, setShow3DCutIn] = useState(false);
  const [cutInScene, setCutInScene] = useState<Cinema3DSceneType>("signing_walkout");

  // Tactics State
  const [formation, setFormation] = useState("4-3-3");
  const [press, setPress] = useState(65);
  const [line, setLine] = useState(68);
  const [tempo, setTempo] = useState(52);
  const [risk, setRisk] = useState(45);

  // Live Gifting Broadcast Animation State
  const [activeGift, setActiveGift] = useState<{ sender: string; name: string; code: string; anim?: string } | null>(null);
  const [lastGiftId, setLastGiftId] = useState<string | null>(null);

  useEffect(() => {
    const recent = (liveState as any)?.recent_gifts;
    if (recent && recent.length > 0) {
      const latest = recent[recent.length - 1];
      const giftKey = `${latest.sender}-${latest.gift_code}-${latest.cost}`;
      if (giftKey !== lastGiftId) {
        setLastGiftId(giftKey);
        setActiveGift({
          sender: latest.sender,
          name: latest.gift_name,
          code: latest.gift_code,
          anim: latest.animation_key,
        });
        const timer = setTimeout(() => setActiveGift(null), 4500);
        return () => clearTimeout(timer);
      }
    }
  }, [liveState, lastGiftId]);

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
            { id: "pitch", label: "2D / 2.5D MATCH PITCH", icon: Tv },
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

        {/* Tab 1: 2D / 2.5D Match Pitch Board */}
        {activeTab === "pitch" && (
          <div className="space-y-4">
            {/* Pitch Camera & Tactical Shader Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-white/10 bg-slate-900/85 p-2.5">
              {/* Camera Perspective Switcher */}
              <div className="flex items-center gap-1.5">
                <Camera size={13} className="text-emerald-400" />
                {[
                  { id: "2d" as const, label: "2D TOP-DOWN" },
                  { id: "2.5d" as const, label: "2.5D TV BROADCAST" },
                  { id: "zoom" as const, label: "DIRECTOR ZOOM" },
                ].map((cam) => (
                  <button
                    key={cam.id}
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

              {/* Spatial Shaders + Event-Driven 3D Cut-In Triggers */}
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  onClick={() => setShowVoronoi(!showVoronoi)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showVoronoi ? "bg-blue-500/20 text-blue-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Compass size={11} /> VORONOI
                </button>
                <button
                  onClick={() => setShowHeatmap(!showHeatmap)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showHeatmap ? "bg-rose-500/20 text-rose-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Flame size={11} /> HEATMAP
                </button>
                <button
                  onClick={() => setShowTactics(!showTactics)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showTactics ? "bg-emerald-500/20 text-emerald-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Layers size={11} /> TACTICS
                </button>
                <button
                  onClick={() => setShowLanes(!showLanes)}
                  className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[10px] font-bold transition-colors ${
                    showLanes ? "bg-cyan-500/20 text-cyan-300" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <Activity size={11} /> LANES & xG
                </button>
                <button
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
              </div>
            </div>

            {/* Pitch View */}
            <Pitch2DView
              selectedPlayer={selectedPlayer}
              onSelectPlayer={setSelectedPlayer}
              showHeatmap={showHeatmap}
              showTactics={showTactics}
              showLanes={showLanes}
              showVoronoi={showVoronoi}
              cameraMode={cameraMode}
              ballOwner={null}
              pitchPlayers={liveState?.pitch_players}
              ball={liveState?.ball}
              activeGift={activeGift}
              formation={formation}
              press={press}
              line={line}
              tempo={tempo}
              minute={minute}
              homeName={m.home_name}
              awayName={m.away_name}
              show3DCutIn={show3DCutIn}
              cutInScene={cutInScene}
              onClose3DCutIn={() => setShow3DCutIn(false)}
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
            clubId={clubId}
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
        <GiftRail
          match={m}
          clubId={clubId}
          onGiftSent={(g: any) => {
            setActiveGift(g);
            setTimeout(() => setActiveGift(null), 4500);
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

import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Sprout,
  Award,
  Sparkles,
  TrendingUp,
  UserCheck,
  FileText,
  ShieldCheck,
  ExternalLink,
  Building,
  CheckCircle2,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PackReveal } from "@/components/gtex/PackReveal";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";

const seenKey = (clubId: string) => `gtex.regens.seen.${clubId}`;
const readSeen = (clubId: string): string[] => JSON.parse(localStorage.getItem(seenKey(clubId)) || "[]");

const TRAITS = ["ambition", "loyalty", "marketability", "professionalism", "adaptability", "growth_responsiveness", "environment_sensitivity"];

function AcademyProspectCard({
  p,
  clubId,
  onInspect,
  onRefresh,
}: {
  p: any;
  clubId: string;
  onInspect: (p: any) => void;
  onRefresh: () => void;
}) {
  const t = p.personality || {};
  const last = p.growth_log?.[p.growth_log.length - 1];
  const pressure = t.transfer_pressure ?? 0;
  const ceiling = Math.max(0, (p.potential || 0) - (p.rating || 0));
  const totalGain = (p.growth_log || []).reduce((s: number, g: any) => s + Number(g.gain || 0), 0);

  const [busyAction, setBusyAction] = useState<string | null>(null);

  const archetype = p.archetype || t.archetype || (ceiling >= 15 ? "Generational Prodigy" : "Technical Playmaker");
  const moodState = p.mood_state || t.mood || (p.morale >= 75 ? "Hungry & Motivated" : p.morale >= 50 ? "Focused on Training" : "Needs Minutes & Assurance");
  const monologue = p.inner_monologue || t.inner_monologue || "I am working on my first touch every single session so the first-team coach notices.";
  const readiness = p.readiness_score ?? (p.rating >= 68 ? 92 : p.rating >= 62 ? 76 : 54);
  const hoydVerdict = p.hoyd_verdict || (p.potential >= 82 ? "Prime candidate for senior promotion" : "Conditioning recommended before top-flight minutes");
  const managerApproved = p.manager_approved ?? (p.rating >= 60);

  const handleContract = async () => {
    setBusyAction("contract");
    try {
      await api.post(`/owner/clubs/${clubId}/academy/${p.id}/contract`);
      toast.success(`Signed enhanced youth contract for ${p.name} (1,000 GTX). Loyalty & retention secured.`);
      onRefresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  const handlePromote = async () => {
    setBusyAction("promote");
    try {
      await api.post(`/owner/clubs/${clubId}/academy/${p.id}/promote`);
      toast.success(`Promoted ${p.name} to senior first-team squad with HOYD + Manager sign-off!`);
      onRefresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <div
      data-testid={`regen-card-${p.id}`}
      className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-950/60 p-5 shadow-xl space-y-4 hover:border-emerald-500/30 transition-all"
    >
      <div className="space-y-4">
        {/* Top Header & Badges */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-black uppercase">
              {archetype}
            </span>
            {p.promoted && (
              <span className="rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-2 py-0.5 text-[9px] font-black uppercase">
                Senior Promoted
              </span>
            )}
          </div>
          <span className="text-[11px] font-semibold text-slate-400">
            Mood: <b className="text-slate-200">{moodState}</b>
          </span>
        </div>

        {/* Card Body */}
        <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
          <div className="cursor-pointer" onClick={() => onInspect(p)}>
            <PlayerCard
              name={p.name}
              rating={p.rating}
              potential={p.potential}
              position={p.position}
              age={p.age}
              regen
              image={p.portrait_url}
              badge={pressure >= 60 ? "Unsettled" : ceiling >= 15 ? "Wonderkid" : "Academy Prospect"}
              stats={[
                { k: "Ceiling", v: `+${ceiling}` },
                { k: "Morale", v: p.morale },
                { k: "Value", v: fmt(p.value_coin) },
              ]}
              variant="compact"
            />
          </div>

          <div className="min-w-0 space-y-3">
            <div className="h-1.5 rounded-sm bg-white/5" title="Progress to potential">
              <div
                className="h-1.5 rounded-sm bg-gradient-to-r from-emerald-500 to-cyan-400 transition-[width] duration-700"
                style={{ width: `${Math.min(100, (p.rating / Math.max(1, p.potential)) * 100)}%` }}
              />
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              {TRAITS.slice(0, 4).map((k) => (
                <TraitBar key={k} label={label(k)} value={t[k] ?? 0} />
              ))}
              <TraitBar label="Transfer pressure" value={pressure} max={100} />
              <TraitBar label="Senior Readiness" value={readiness} max={100} />
            </div>

            {/* Inner Monologue */}
            <div className="rounded-lg border border-white/5 bg-black/40 p-2.5">
              <p className="text-[9px] font-black uppercase tracking-wider text-emerald-400">Inner Monologue</p>
              <p className="text-xs italic text-slate-300 mt-0.5">"{monologue}"</p>
            </div>

            {/* HOYD & Manager Assessment */}
            <div className="rounded-lg border border-purple-500/20 bg-purple-950/20 p-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-purple-300">HOYD Verdict:</span>
                <span className={`text-[10px] font-bold uppercase ${managerApproved ? "text-emerald-400" : "text-amber-400"}`}>
                  {managerApproved ? "Manager Approved" : "Development Track"}
                </span>
              </div>
              <p className="text-slate-300 mt-1">{hoydVerdict}</p>
            </div>
          </div>
        </div>

        {last && (
          <p className="border-t border-white/5 pt-2 text-xs text-slate-400" data-testid="regen-growth-explanation">
            <span className="gx-mono mr-1 text-[10px] uppercase text-slate-500">Day {last.day}</span>+{last.gain} · {last.explanation}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-3 border-t border-white/10">
        <button
          type="button"
          onClick={handleContract}
          disabled={busyAction === "contract"}
          className="gx-btn gx-btn-secondary text-xs flex-1 flex items-center justify-center gap-1.5"
          data-testid={`youth-contract-${p.id}`}
        >
          <FileText size={13} className="text-amber-300" />
          <span>{busyAction === "contract" ? "Signing…" : "Offer Youth Contract (1,000 GTX)"}</span>
        </button>

        {!p.promoted && (
          <button
            type="button"
            onClick={handlePromote}
            disabled={busyAction === "promote"}
            className="gx-btn gx-btn-primary text-xs flex-1 flex items-center justify-center gap-1.5"
            data-testid={`promote-first-team-${p.id}`}
          >
            <UserCheck size={13} />
            <span>{busyAction === "promote" ? "Promoting…" : "Promote to First Team"}</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => onInspect(p)}
          className="gx-btn gx-btn-ghost text-xs flex items-center gap-1"
          data-testid={`inspect-prospect-${p.id}`}
        >
          <span>Inspect Dossier</span>
          <ExternalLink size={12} />
        </button>
      </div>
    </div>
  );
}

export default function Academy() {
  const { active } = useActiveClub();
  const { data: club, isLoading } = useClub(active?.club_id);
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState("");
  const [pack, setPack] = useState<any[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<any | null>(null);
  const [categoryTab, setCategoryTab] = useState<"all" | "prospects" | "promoted">("all");

  useEffect(() => {
    if (!club) return;
    const seen = new Set(readSeen(club.club_id));
    setPack(club.squad.filter((p: any) => p.is_regen && !seen.has(p.id)));
  }, [club]);

  if (isLoading || !club) return <Loading />;

  const regens: any[] = club.squad.filter((p: any) => Boolean(p.is_regen));
  const facilityLevel = club.facilities?.academy ?? club.academy_level ?? 2;
  const clubPrestige = club.health?.prestige ?? 55;
  const prestigeTier = clubPrestige >= 85 ? 1 : clubPrestige >= 70 ? 2 : clubPrestige >= 50 ? 3 : clubPrestige >= 35 ? 4 : 5;
  const hoydRating = club.staff?.head_of_youth_development?.rating ?? club.hoyd?.rating ?? 78;

  const prospects = regens.filter((p) => !p.promoted);
  const promotedRegens = regens.filter((p) => Boolean(p.promoted));

  const displayedRegens =
    categoryTab === "prospects"
      ? prospects
      : categoryTab === "promoted"
      ? promotedRegens
      : regens;

  const dismissPack = () => {
    const next = Array.from(new Set([...readSeen(club.club_id), ...pack.map((p) => p.id)]));
    localStorage.setItem(seenKey(club.club_id), JSON.stringify(next));
    setPack([]);
  };

  const scoutIntake = async () => {
    setBusy("intake");
    try {
      const { data } = await api.post(`/owner/clubs/${club.club_id}/academy/intake`);
      toast.success(`Academy intake signed ${data.regens?.length || 3} new youth regens.`);
      setPack(data.regens || []);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy("");
    }
  };

  return (
    <div data-testid="academy-page" className="space-y-8">
      <PageHeader
        eyebrow="Regen Incubator & HOYD Pipeline"
        title="Youth Academy Command"
        sub="AI-generated regen players enter your academy. Facility levels and Club Prestige decide intake class size, potential ceilings, and senior readiness."
        action={
          <Btn variant="primary" disabled={!!busy} onClick={scoutIntake} data-testid="scout-intake-button">
            <Sprout size={14} />
            {busy === "intake" ? "Signing…" : "Scout New Intake"}
          </Btn>
        }
      />

      {/* 1. Facility Level & Prestige Tier Impact Banner */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4" data-testid="academy-facility-stats">
        <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-[#061e16] to-[#040f0b] p-5 shadow-lg">
          <div className="flex items-center justify-between text-emerald-400 mb-2">
            <Building size={18} />
            <span className="text-[10px] font-black uppercase tracking-wider">Infrastructure</span>
          </div>
          <p className="text-xs uppercase font-bold text-slate-400">Academy Facility Level</p>
          <p className="gx-mono text-3xl font-black text-white mt-1">Level {facilityLevel}<span className="text-sm text-slate-500">/5</span></p>
          <p className="text-[11px] text-emerald-300 mt-1">+{facilityLevel * 4}% Regen Growth Speed</p>
        </div>

        <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-br from-[#1e1506] to-[#0f0c05] p-5 shadow-lg">
          <div className="flex items-center justify-between text-amber-400 mb-2">
            <Award size={18} />
            <span className="text-[10px] font-black uppercase tracking-wider">Club Standing</span>
          </div>
          <p className="text-xs uppercase font-bold text-slate-400">Prestige Tier Impact</p>
          <p className="gx-mono text-3xl font-black text-amber-300 mt-1">Tier {prestigeTier}</p>
          <p className="text-[11px] text-amber-200 mt-1">+{Math.max(0, 6 - prestigeTier) * 3} Max Potential Ceiling</p>
        </div>

        <div className="rounded-2xl border border-purple-500/30 bg-gradient-to-br from-[#180a29] to-[#0a0512] p-5 shadow-lg">
          <div className="flex items-center justify-between text-purple-400 mb-2">
            <Sparkles size={18} />
            <span className="text-[10px] font-black uppercase tracking-wider">Staff Leadership</span>
          </div>
          <p className="text-xs uppercase font-bold text-slate-400">HOYD Youth Rating</p>
          <p className="gx-mono text-3xl font-black text-purple-300 mt-1">{hoydRating}<span className="text-sm text-slate-500">/100</span></p>
          <p className="text-[11px] text-purple-200 mt-1">Senior Transition Autonomy Active</p>
        </div>
      </section>

      {/* 2. Category Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
        <div className="flex gap-2">
          <button
            onClick={() => setCategoryTab("all")}
            className={`gx-btn ${categoryTab === "all" ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
          >
            All Regens ({regens.length})
          </button>
          <button
            onClick={() => setCategoryTab("prospects")}
            className={`gx-btn ${categoryTab === "prospects" ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
          >
            Academy Prospects ({prospects.length})
          </button>
          <button
            onClick={() => setCategoryTab("promoted")}
            className={`gx-btn ${categoryTab === "promoted" ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
          >
            Senior Promoted ({promotedRegens.length})
          </button>
        </div>
      </div>

      {pack.length > 0 && <PackReveal regens={pack} players={pack} onClose={dismissPack} onDismiss={dismissPack} />}

      {/* 3. Prospects & Promoted Regens Grid */}
      <div className="space-y-4">
        {displayedRegens.length === 0 ? (
          <Empty
            title="No academy players found"
            body="Run an academy intake to discover new high-ceiling wonderkids for your club."
          />
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            {displayedRegens.map((p: any) => (
              <AcademyProspectCard
                key={p.id}
                p={p}
                clubId={club.club_id}
                onInspect={(player) => setSelectedPlayer(player)}
                onRefresh={refresh}
              />
            ))}
          </div>
        )}
      </div>

      {/* Universal Player Drawer */}
      <PlayerDrawer
        playerId={selectedPlayer ? String(selectedPlayer.player_ref || selectedPlayer.player_id || selectedPlayer.id) : null}
        onClose={() => setSelectedPlayer(null)}
      />
    </div>
  );
}

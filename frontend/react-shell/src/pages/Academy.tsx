import React, { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Sprout,
  Award,
  Sparkles,
  UserCheck,
  FileText,
  ExternalLink,
  Building,
  Crown,
  Dna,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PackReveal } from "@/components/gtex/PackReveal";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";

const seenKey = (clubId: string) => `gtex.regens.seen.${clubId}`;
const readSeen = (clubId: string): string[] => JSON.parse(localStorage.getItem(seenKey(clubId)) || "[]");

const TRAITS = ["ambition", "loyalty", "marketability", "professionalism", "adaptability", "growth_responsiveness", "environment_sensitivity"];
const SON_POSITIONS = ["ST", "RW", "LW", "AM", "CM", "DM", "RB", "LB", "CB", "GK"];

function BuildASonDesk({ club, onOrderUpdated }: { club: any; onOrderUpdated: () => void }) {
  const qc = useQueryClient();
  const [parentId, setParentId] = useState("");
  const [sonName, setSonName] = useState("");
  const [sonPosition, setSonPosition] = useState("ST");
  const [sonCountry, setSonCountry] = useState("NGA");
  const [busyOrder, setBusyOrder] = useState<string | null>(null);

  const { data: options } = useQuery({
    queryKey: ["request-son-options", club?.club_id],
    queryFn: async () => {
      try {
        return (await api.get("/regens/request-son/options")).data;
      } catch {
        return null;
      }
    },
    enabled: Boolean(club?.club_id),
  });

  const { data: ordersData } = useQuery({
    queryKey: ["regen-creation-orders", club?.club_id],
    queryFn: async () => {
      try {
        return (await api.get("/regens/creation-orders", { params: { limit: 10 } })).data;
      } catch {
        return { orders: [] };
      }
    },
    enabled: Boolean(club?.club_id),
  });

  const eligibleParents: any[] =
    options?.eligible_parents?.length > 0
      ? options.eligible_parents
      : (club?.squad || []).slice(0, 8).map((p: any) => ({
          player_id: p.player_ref || p.player_id || p.id,
          full_name: p.name,
          position: p.position,
          country_code: p.nationality || "NGA",
          club_name: club?.club_name,
        }));

  useEffect(() => {
    if (!parentId && eligibleParents.length > 0) {
      setParentId(String(eligibleParents[0].player_id));
    }
  }, [eligibleParents, parentId]);

  const baseCost = Number(options?.pricing?.base_cost_coin ?? 1500);
  const nameCost = sonName.trim() ? Number(options?.pricing?.name_cost_coin ?? 500) : 0;
  const customCost = Number(options?.pricing?.customization_cost_coin ?? 500);
  const totalEstimated = baseCost + nameCost + customCost;

  const orders: any[] = ordersData?.orders || ordersData?.items || [];

  const handleRequestSon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!parentId) {
      toast.error("Select a parent club legend / senior player to pass on the bloodline.");
      return;
    }
    setBusyOrder("create");
    try {
      const { data: order } = await api.post("/regens/request-son", {
        parent_player_id: parentId,
        requested_name: sonName.trim() || undefined,
        requested_position: sonPosition,
        requested_country_code: sonCountry.trim().toUpperCase() || undefined,
        payment_method: "wallet",
      });
      // Immediately pay with wallet & generate if pending payment
      if (order?.id && order.status !== "generated") {
        try {
          await api.post(`/regens/creation-orders/${order.id}/pay-with-wallet`);
          await api.post(`/regens/creation-orders/${order.id}/generate-after-payment`);
        } catch {
          // Order created; user can complete payment/generation from the order row below
        }
      }
      toast.success(`Build-A-Son dynasty order submitted${sonName ? ` for ${sonName}` : ""}!`);
      setSonName("");
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["regen-creation-orders"] }),
        qc.invalidateQueries({ queryKey: ["request-son-options"] }),
      ]);
      onOrderUpdated();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusyOrder(null);
    }
  };

  const handleCompleteOrder = async (orderId: string, step: "pay" | "generate") => {
    setBusyOrder(`${orderId}:${step}`);
    try {
      if (step === "pay") {
        await api.post(`/regens/creation-orders/${orderId}/pay-with-wallet`);
        toast.success("Build-A-Son order paid from GTEX wallet.");
      } else {
        await api.post(`/regens/creation-orders/${orderId}/generate-after-payment`);
        toast.success("Dynasty heir generated and inducted into your Academy!");
      }
      await qc.invalidateQueries({ queryKey: ["regen-creation-orders"] });
      onOrderUpdated();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusyOrder(null);
    }
  };

  return (
    <Panel
      eyebrow="Canonical Regen Creation Engine · Dynasty Bloodline"
      title="Build-A-Son Legacy Program"
      testid="build-a-son-panel"
    >
      <div className="mb-6">
        <Cinema3DStage
          scene="build_a_son"
          compact
          title={`3D Bloodline Induction · ${sonName.trim() || "Dynasty Heir Jr."}`}
          subtitle={`Passing the Torch at ${club?.club_name || "GTEX FC"} · Position: ${sonPosition} (${sonCountry})`}
          badgeText="3D DNA TUNNEL WALKOUT"
          clubName={club?.club_name || "GTEX FC"}
          subjectName={sonName.trim() || "Dynasty Heir Jr."}
          subjectRole={`${sonPosition} · Second-Generation Club Scion`}
          jerseyNumber={sonPosition === "ST" ? 9 : sonPosition === "AM" || sonPosition === "RW" ? 10 : 7}
          overallRating={74}
          potentialRating={94}
          quote="Growing up in these stands, wearing my father's crest is my destiny."
        />
      </div>
      <div className="grid gap-6 lg:grid-cols-12">
        <form onSubmit={handleRequestSon} className="space-y-4 lg:col-span-7" data-testid="build-a-son-form">
          <p className="text-xs text-slate-300 leading-relaxed">
            Induct a second-generation dynasty heir into <b className="text-white">{club?.club_name}</b> using the canonical{" "}
            <span className="gx-mono text-emerald-300">/regens/request-son</span> pipeline. Select an eligible club parent to pass on DNA bloodline traits, position affinity, and supporter adoration.
          </p>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="gx-label">Parent Player (Bloodline Progenitor)</label>
              <select
                className="gx-input mt-1"
                value={parentId}
                onChange={(e) => setParentId(e.target.value)}
                data-testid="build-a-son-parent-select"
              >
                {eligibleParents.map((p: any) => (
                  <option key={p.player_id} value={p.player_id}>
                    {p.full_name} ({p.position || "PRO"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="gx-label">Requested Heir Name (Optional)</label>
              <input
                type="text"
                maxLength={120}
                placeholder="e.g. Adewale Jr."
                value={sonName}
                onChange={(e) => setSonName(e.target.value)}
                className="gx-input mt-1"
                data-testid="build-a-son-name-input"
              />
            </div>

            <div>
              <label className="gx-label">Preferred Position</label>
              <select
                className="gx-input mt-1"
                value={sonPosition}
                onChange={(e) => setSonPosition(e.target.value)}
                data-testid="build-a-son-position-select"
              >
                {SON_POSITIONS.map((pos) => (
                  <option key={pos} value={pos}>
                    {pos}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="gx-label">Nationality Code (ISO)</label>
              <input
                type="text"
                maxLength={8}
                placeholder="NGA"
                value={sonCountry}
                onChange={(e) => setSonCountry(e.target.value.toUpperCase())}
                className="gx-input mt-1 uppercase"
                data-testid="build-a-son-country-input"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/25 bg-amber-500/5 p-3 text-xs">
            <div className="flex items-center gap-2 text-amber-200">
              <Crown size={15} className="text-amber-400" />
              <span>
                Base: <b>{fmt(baseCost)}</b> · Name: <b>{fmt(nameCost)}</b> · Custom Position: <b>{fmt(customCost)}</b>
              </span>
            </div>
            <Btn type="submit" variant="gold" disabled={busyOrder === "create"} data-testid="build-a-son-submit">
              <Dna size={14} />
              {busyOrder === "create" ? "Inducting Heir…" : `Induct Dynasty Son · ${fmt(totalEstimated)} GTX`}
            </Btn>
          </div>
        </form>

        <div className="space-y-3 rounded-xl border border-white/10 bg-slate-950/60 p-4 lg:col-span-5" data-testid="build-a-son-orders">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">
              Dynasty Creation Orders ({orders.length})
            </span>
            <Chip tone="emerald">DNA Lineage Active</Chip>
          </div>

          {orders.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">
              No Build-A-Son creation orders yet. Submit the form to induct your first dynasty scion.
            </p>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {orders.map((ord: any) => (
                <div
                  key={ord.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/40 p-2.5 text-xs"
                  data-testid={`son-order-${ord.id}`}
                >
                  <div>
                    <p className="font-bold text-white">
                      {ord.requested_name || ord.generated_player?.full_name || "Dynasty Heir"} ·{" "}
                      <span className="text-emerald-300">{ord.requested_position || ord.generated_player?.position || "ST"}</span>
                    </p>
                    <p className="text-[11px] text-slate-400">
                      Status: <b className="uppercase text-amber-300">{label(ord.status)}</b> · <Coin amount={Number(ord.amount_coin || 0)} />
                    </p>
                  </div>
                  <div className="flex gap-1.5">
                    {ord.status === "pending_payment" && (
                      <Btn
                        variant="gold"
                        onClick={() => handleCompleteOrder(ord.id, "pay")}
                        disabled={busyOrder === `${ord.id}:pay`}
                      >
                        Pay Wallet
                      </Btn>
                    )}
                    {ord.status === "paid" && !ord.generated_player_id && (
                      <Btn
                        variant="primary"
                        onClick={() => handleCompleteOrder(ord.id, "generate")}
                        disabled={busyOrder === `${ord.id}:generate`}
                      >
                        Generate Son
                      </Btn>
                    )}
                    {ord.generated_player && (
                      <Chip tone="emerald">
                        OVR {ord.generated_player.current_rating} / POT {ord.generated_player.potential_rating}
                      </Chip>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}

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

  const [busyAction, setBusyAction] = useState<string | null>(null);

  const archetype = p.archetype || t.archetype || (ceiling >= 15 ? "Generational Prodigy" : "Technical Playmaker");
  const moodState = p.mood_state || t.mood || (p.morale >= 75 ? "Hungry & Motivated" : p.morale >= 50 ? "Focused on Training" : "Needs Minutes & Assurance");
  const monologue = p.inner_monologue || t.inner_monologue || "I am working on my first touch every single session so the first-team coach notices.";
  const readiness = p.readiness_score ?? (p.rating >= 68 ? 92 : p.rating >= 62 ? 76 : 54);
  const hoydVerdict = p.hoyd_verdict || (p.potential >= 82 ? "Prime candidate for senior promotion" : "Conditioning recommended before top-flight minutes");
  const managerApproved = p.manager_approved ?? (p.rating >= 60);
  const originBackstory = p.origin_backstory || t.origin_backstory;
  const superAgent = p.super_agent || t.super_agent;
  const dramaArc = p.drama_arc || t.drama_arc;

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
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-black uppercase">
              {archetype}
            </span>
            {originBackstory?.label && (
              <span className="rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 text-[9px] font-black uppercase">
                {originBackstory.label}
              </span>
            )}
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

            {/* Backstory / Super-Agent / Drama Arc */}
            {(originBackstory || superAgent || dramaArc) && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-950/15 p-2.5 text-[11px] space-y-1">
                {originBackstory?.hook && (
                  <p className="text-amber-200">
                    <b>Backstory:</b> {originBackstory.hook}
                  </p>
                )}
                {superAgent?.name && (
                  <p className="text-slate-300">
                    <b>Agent:</b> {superAgent.name} ({superAgent.style})
                  </p>
                )}
                {dramaArc?.headline && (
                  <p className="text-rose-300">
                    <b>Active Arc:</b> {dramaArc.headline}
                  </p>
                )}
              </div>
            )}

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
  const facilityLevel = Number(
    typeof club.facilities?.academy === 'object' && club.facilities?.academy !== null
      ? club.facilities?.academy?.level
      : club.facilities?.academy ?? club.academy_level ?? 2
  ) || 2;
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

      {/* 1A. 3D Generational Wonderkid Emergence & Youth Campus Diorama */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Cinema3DStage
          scene="wonderkid_emergence"
          compact
          title={`3D Generational Wonderkid Walkout · ${regens[0]?.name || "Crown Jewel #10"}`}
          subtitle={`HOYD Report: "Cancel all transfer plans — a generational talent has emerged on Pitch 3."`}
          badgeText="3D GOLDEN FLARE WALKOUT"
          clubName={club.club_name}
          subjectName={regens[0]?.name || "Academy Prodigy"}
          jerseyNumber={10}
          overallRating={regens[0]?.rating || 76}
          potentialRating={regens[0]?.potential?.max || 95}
          stats={[
            { label: "Ceiling", value: `${regens[0]?.potential?.max || 95} POT`, accent: "#F5B83D" },
            { label: "HOYD Rating", value: `${hoydRating}/100`, accent: "#00E676" },
          ]}
        />
        <Cinema3DStage
          scene="academy_upgrade"
          compact
          title={`3D Youth Academy Campus · Level ${facilityLevel}/5`}
          subtitle={`${club.club_name} Biomechanics, 3G Domes & DNA Scouting Complex`}
          badgeText="3D ACADEMY CAMPUS"
          clubName={club.club_name}
          subjectName={`${club.club_name} Youth Complex L${facilityLevel}`}
          facilityLevel={facilityLevel}
          stats={[
            { label: "Growth Speed", value: `+${facilityLevel * 4}%`, accent: "#00E676" },
            { label: "Prestige Ceiling", value: `Tier ${prestigeTier}`, accent: "#38BDF8" },
          ]}
        />
      </div>

      {/* 1B. Canonical Build-A-Son Legacy Program */}
      <BuildASonDesk club={club} onOrderUpdated={refresh} />

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

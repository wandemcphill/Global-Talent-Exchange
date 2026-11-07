import React, { useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { clubCreateErrorMessage } from "./clubLocationCatalog";
import { ClubLocationFields, clubLocationPayload, useClubLocation } from "@/components/gtex/ClubLocationFields";
import {
  fmt,
  label,
  useActiveClub,
  useClub,
  useClubShowroom,
  useClubStaff,
  useControlCenter,
  useNewsroom,
  useRefreshOwner,
} from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";
import {
  Building,
  Gift,
  Sparkles,
  BookOpen,
  ExternalLink,
  CheckCircle,
  Coins,
  LockKeyhole,
  X,
  PackageCheck,
  Shield,
  Users,
  Sliders,
  Trophy,
  ArrowRight,
  Eye,
  EyeOff,
  Copy,
  RefreshCw,
  AlertCircle,
  Newspaper,
  Check,
  Landmark,
  GraduationCap,
  Activity,
  Layers,
} from "lucide-react";

// ============================================================================
// 1. Facilities & 3D Campus Panel
// ============================================================================
function Facilities({ club }: any) {
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState<string | null>(null);

  const up = async (kind: string) => {
    setBusy(kind);
    try {
      const { data } = await api.post(`/owner/clubs/${club.club_id}/facilities/${kind}/upgrade`);
      toast.success(`${label(kind)} level ${data.level}. ${data.effect}`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const facilities = club.facilities || {};

  return (
    <Panel
      eyebrow="Club Infrastructure"
      title="Facilities & 3D Campus Complex"
      testid="facilities-panel"
      className="lg:col-span-12"
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-500/20 bg-sky-950/20 p-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-sky-400">Interactive Infrastructure</span>
          <p className="mt-1 text-xs text-slate-300">
            Expand training pitches, cathedral stadiums, medical labs, and the youth complex to drive performance multipliers.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={`/app/campus`}
            className="flex items-center gap-1.5 rounded-lg border border-sky-400/30 bg-sky-500/10 px-3 py-2 text-xs font-bold text-sky-200 transition hover:bg-sky-500/20"
            data-testid="open-campus-builder-link"
          >
            <Building className="h-3.5 w-3.5" />
            <span>3D Campus Builder</span>
            <ExternalLink className="h-3 w-3" />
          </Link>
          <Link
            to={`/app/showroom`}
            className="flex items-center gap-1.5 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs font-bold text-amber-200 transition hover:bg-amber-500/20"
            data-testid="open-facilities-showroom-link"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Showroom Fleet</span>
            <ExternalLink className="h-3 w-3" />
          </Link>
          <Link
            to={`/app/clubs/${club.club_id}/story`}
            className="flex items-center gap-1.5 rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-200 transition hover:bg-emerald-500/20"
            data-testid="open-club-story-link"
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span>Club Story & Dynasty</span>
          </Link>
        </div>
      </div>

      <div className="mb-6">
        <Cinema3DStage
          scene="facility_upgrade"
          compact
          title={`3D Stadium Cathedral & Campus Cutaway · ${club.club_name}`}
          subtitle="Interactive 3D Architectural Blueprint-to-Cathedral Morph · Stadium, Academy & Medical"
          badgeText="3D INFRASTRUCTURE"
          clubName={club.club_name}
          subjectName={`${club.club_name} Arena & Youth Campus`}
          facilityLevel={Number(facilities?.stadium?.level ?? facilities?.academy?.level ?? 3)}
          stats={[
            { label: "Stadium Tier", value: `L${facilities?.stadium?.level ?? 2}/5`, accent: "#38BDF8" },
            { label: "Academy Campus", value: `L${facilities?.academy?.level ?? 2}/5`, accent: "#00E676" },
          ]}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(facilities).map(([k, f]: any) => (
          <div key={k} className="rounded-xl border border-white/10 bg-slate-950/60 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="gx-display text-sm font-bold uppercase text-white">{label(k)}</p>
                <span className="text-[11px] text-slate-400">Campus Asset</span>
              </div>
              <span className="gx-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                L{f.level}/5
              </span>
            </div>

            <div className="flex gap-1.5">
              {[1, 2, 3, 4, 5].map((n) => (
                <span
                  key={n}
                  className={`h-1.5 flex-1 rounded-full ${n <= f.level ? "bg-emerald-400 shadow-sm" : "bg-white/10"}`}
                />
              ))}
            </div>

            <p className="text-[11px] text-slate-400 min-h-[32px]">
              {k === "stadium" && "Expands matchday gate receipts, hospitality suites, and tier capacity."}
              {k === "academy" && "Increases regen intake potential, wonderkid discovery rates, and youth coaching."}
              {k === "training" && "Accelerates squad tactical familiarity, conditioning, and training progress."}
              {k === "medical" && "Reduces match injury downtime and increases player physical recovery speed."}
              {k === "commercial" && "Boosts sponsorship contract values, merchandise royalties, and fan reach."}
              {!["stadium", "academy", "training", "medical", "commercial"].includes(k) && "Campus operational upgrade asset."}
            </p>

            <Btn
              variant="secondary"
              className="mt-2 w-full text-xs font-bold"
              disabled={!f.next_cost || busy === k}
              onClick={() => up(k)}
              data-testid={`upgrade-${k}-button`}
            >
              {f.next_cost ? <>Upgrade · {fmt(f.next_cost)} GTX</> : "Max level achieved"}
            </Btn>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// ============================================================================
// 2. Organisational Structure & Executive Staff Panel
// ============================================================================
function OrganisationalStructurePanel({ club }: any) {
  const { data: staffData, isLoading, refetch } = useClubStaff(club.club_id);
  const [activeTab, setActiveTab] = useState<"hierarchy" | "effects" | "candidates">("hierarchy");
  const [hiringBusy, setHiringBusy] = useState<string | null>(null);

  const appointed = staffData?.appointed || {};
  const staffEffects = staffData?.staff_effects || {};
  const candidates: any[] = staffData?.candidates || [];

  const handleHire = async (candidate: any) => {
    setHiringBusy(candidate.id || candidate.staff_id);
    try {
      await api.post(`/owner/clubs/${club.club_id}/staff/hire`, {
        staff_id: candidate.id || candidate.staff_id,
        role: candidate.role,
        contract_years: 3,
        pay_with_fan_coin: true,
      });
      toast.success(`Hired ${candidate.name} as ${label(candidate.role)}.`);
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setHiringBusy(null);
    }
  };

  const ROLES = [
    { key: "first_team_manager", title: "First-Team Manager / Head Coach", fallbackDesc: "Tactical direction, starting lineup selection, and matchday leadership." },
    { key: "general_manager", title: "General Manager (GM)", fallbackDesc: "Commercial contracts, transfer budget execution, and executive operations." },
    { key: "head_of_youth_development", title: "Head of Youth Development (HOYD)", fallbackDesc: "Youth academy curriculum, wonderkid intake, and regen development." },
    { key: "chief_scout", title: "Chief Scout", fallbackDesc: "Global market intelligence, opponent scouting reports, and hidden talent identification." },
    { key: "medical_director", title: "Head of Sports Science & Medical", fallbackDesc: "Physical conditioning, recovery acceleration, and injury risk prevention." },
  ];

  return (
    <Panel
      eyebrow="Club Governance"
      title="Organisational Structure & Executive Staff"
      testid="organisational-structure-panel"
      className="lg:col-span-12"
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-400">Boardroom Hierarchy</span>
          <p className="mt-1 text-xs text-slate-300">
            A world-class executive staff drives performance, youth development, and commercial power.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("hierarchy")}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${activeTab === "hierarchy" ? "bg-indigo-500 text-white" : "border border-slate-700 bg-slate-900 text-slate-400 hover:text-white"}`}
          >
            Executive Hierarchy
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("effects")}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${activeTab === "effects" ? "bg-indigo-500 text-white" : "border border-slate-700 bg-slate-900 text-slate-400 hover:text-white"}`}
          >
            Staff Synergy Effects
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("candidates")}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${activeTab === "candidates" ? "bg-indigo-500 text-white" : "border border-slate-700 bg-slate-900 text-slate-400 hover:text-white"}`}
          >
            Executive Market ({candidates.length})
          </button>
        </div>
      </div>

      {isLoading ? (
        <Loading />
      ) : activeTab === "hierarchy" ? (
        <div className="space-y-4">
          {/* Owner Top Tier */}
          <div className="rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-slate-900 to-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-amber-400/40 bg-amber-400/15 text-amber-300">
                  <Shield className="h-6 w-6" />
                </div>
                <div>
                  <span className="text-[9px] font-black uppercase tracking-wider text-amber-400">CONTROLLING SHAREHOLDER & OWNER</span>
                  <h4 className="text-base font-black text-white">{club.ownership_group?.label || "Club Owner"}</h4>
                  <p className="text-xs text-slate-400">Ultimate governance, treasury authority, and strategic mandate.</p>
                </div>
              </div>
              <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-300">
                100% Voting Rights
              </span>
            </div>
          </div>

          {/* Executive Hierarchy Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {ROLES.map(({ key, title, fallbackDesc }) => {
              const staff = appointed[key];
              const isAppointed = !!staff && typeof staff === "object";
              const name = isAppointed ? staff.name || staff.display_name || "Appointed Executive" : "Vacant Position";
              const rating = isAppointed ? (staff.tactical_flexibility || staff.rating || staff.overall || 75) : null;
              const agenda = isAppointed ? (staff.personal_agenda || "Elevate club standard") : null;
              const secretTrait = isAppointed ? staff.secret_trait : null;
              const poachingRisk = isAppointed ? staff.poaching_risk : null;

              return (
                <div
                  key={key}
                  data-testid={`staff-card-${key}`}
                  className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 flex flex-col justify-between space-y-3 transition hover:border-slate-700"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{title}</span>
                      {isAppointed ? (
                        <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                          Appointed
                        </span>
                      ) : (
                        <span className="rounded bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold text-rose-300">
                          Vacant
                        </span>
                      )}
                    </div>

                    <div className="mt-3 flex items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-800 font-bold text-white text-base">
                        {isAppointed ? name.slice(0, 1) : "?"}
                      </div>
                      <div className="min-w-0">
                        <h5 className="truncate text-sm font-extrabold text-white">{name}</h5>
                        {rating && (
                          <span className="font-mono text-xs font-bold text-amber-300">
                            Rating: {rating}/100
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="mt-3 text-xs text-slate-400 line-clamp-2">
                      {isAppointed ? (staff.bio || fallbackDesc) : fallbackDesc}
                    </p>

                    {agenda && (
                      <div className="mt-3 rounded-lg border border-white/5 bg-black/30 p-2 text-[11px]">
                        <span className="font-bold text-indigo-300">Executive Agenda:</span>{" "}
                        <span className="text-slate-300">{agenda}</span>
                      </div>
                    )}

                    {secretTrait && (
                      <div className="mt-2 flex items-center gap-1.5 text-[10px] text-amber-200">
                        <Sparkles className="h-3 w-3 shrink-0" />
                        <span>{secretTrait}</span>
                      </div>
                    )}
                  </div>

                  <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[10px]">
                    <span className="text-slate-500">
                      {poachingRisk ? `Poaching Risk: ${poachingRisk.toUpperCase()}` : "Operational Ready"}
                    </span>
                    <button
                      type="button"
                      onClick={() => setActiveTab("candidates")}
                      className="text-indigo-400 hover:text-indigo-300 font-bold"
                    >
                      Browse Talent →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-3 text-[11px] text-slate-400 flex items-center gap-2">
            <LockKeyhole className="h-4 w-4 shrink-0 text-slate-500" />
            <span>
              Executive salaries and contract agreements are confidential boardroom records and are excluded from the public club profile.
            </span>
          </div>
        </div>
      ) : activeTab === "effects" ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-emerald-500/20 bg-slate-950/60 p-4">
              <span className="text-[10px] uppercase font-bold text-emerald-400">Tactical Synergy</span>
              <div className="mt-1 text-2xl font-black text-white">+{staffEffects.tactical_synergy ?? 12}%</div>
              <p className="mt-1 text-xs text-slate-400">Matchday formation discipline and in-game tactical adjustments.</p>
            </div>
            <div className="rounded-xl border border-sky-500/20 bg-slate-950/60 p-4">
              <span className="text-[10px] uppercase font-bold text-sky-400">Youth Intake Multiplier</span>
              <div className="mt-1 text-2xl font-black text-white">+{staffEffects.youth_multiplier ?? 15}%</div>
              <p className="mt-1 text-xs text-slate-400">Probability of discovering generational wonderkids in the annual intake.</p>
            </div>
            <div className="rounded-xl border border-purple-500/20 bg-slate-950/60 p-4">
              <span className="text-[10px] uppercase font-bold text-purple-400">Physical Recovery Speed</span>
              <div className="mt-1 text-2xl font-black text-white">+{staffEffects.recovery_bonus ?? 10}%</div>
              <p className="mt-1 text-xs text-slate-400">Accelerated player fitness recharge between congested fixtures.</p>
            </div>
            <div className="rounded-xl border border-amber-500/20 bg-slate-950/60 p-4">
              <span className="text-[10px] uppercase font-bold text-amber-400">Commercial Pull</span>
              <div className="mt-1 text-2xl font-black text-white">+{staffEffects.commercial_pull ?? 8}%</div>
              <p className="mt-1 text-xs text-slate-400">Reputation premium applied to incoming sponsorship contracts.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {candidates.map((cand) => (
              <div
                key={cand.id || cand.staff_id}
                className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                      {label(cand.role)}
                    </span>
                    <span className="text-xs font-mono font-bold text-amber-300">
                      OVR {cand.tactical_flexibility || cand.youth_development || cand.rating || 78}
                    </span>
                  </div>
                  <h5 className="mt-1 text-sm font-extrabold text-white">{cand.name}</h5>
                  <p className="mt-1 text-xs text-slate-400 line-clamp-2">
                    {cand.bio || `Seasoned ${label(cand.role)} with high tactical flexibility.`}
                  </p>
                  <div className="mt-2 text-[11px] text-slate-300">
                    <span className="text-slate-500">Signing Fee:</span>{" "}
                    <span className="font-mono font-bold text-amber-300">{fmt(cand.signing_fee_gtex || cand.salary || 2000)} GTX</span>
                  </div>
                </div>
                <Btn
                  variant="secondary"
                  className="w-full text-xs"
                  disabled={hiringBusy === (cand.id || cand.staff_id)}
                  onClick={() => handleHire(cand)}
                >
                  {hiringBusy === (cand.id || cand.staff_id) ? "Appointing..." : "Appoint to Role"}
                </Btn>
              </div>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

// ============================================================================
// 3. Delegation & Authority Panel
// ============================================================================
function DelegationAuthorityPanel({ club }: any) {
  const { data: staffData, refetch } = useClubStaff(club.club_id);
  const [busy, setBusy] = useState(false);

  const policy = staffData?.delegation_policy || {
    mode: "balanced",
    gm_transfer_autonomy: true,
    hoyd_youth_contracts: true,
    manager_tactics_autonomy: true,
  };

  const [mode, setMode] = useState<string>(policy.mode || "balanced");
  const [gmTransfer, setGmTransfer] = useState<boolean>(policy.gm_transfer_autonomy ?? true);
  const [hoydYouth, setHoydYouth] = useState<boolean>(policy.hoyd_youth_contracts ?? true);
  const [mgrTactics, setMgrTactics] = useState<boolean>(policy.manager_tactics_autonomy ?? true);

  const save = async (nextMode = mode, nextGm = gmTransfer, nextHoyd = hoydYouth, nextMgr = mgrTactics) => {
    setBusy(true);
    try {
      await api.put(`/owner/clubs/${club.club_id}/delegation`, {
        mode: nextMode,
        gm_transfer_autonomy: nextGm,
        hoyd_youth_contracts: nextHoyd,
        manager_tactics_autonomy: nextMgr,
      });
      toast.success("Owner authority and delegation policy saved.");
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const selectPreset = (newMode: string) => {
    setMode(newMode);
    if (newMode === "hands_on") {
      setGmTransfer(false);
      setHoydYouth(false);
      setMgrTactics(false);
      save("hands_on", false, false, false);
    } else if (newMode === "balanced") {
      setGmTransfer(true);
      setHoydYouth(true);
      setMgrTactics(true);
      save("balanced", true, true, true);
    } else if (newMode === "executive_led") {
      setGmTransfer(true);
      setHoydYouth(true);
      setMgrTactics(true);
      save("executive_led", true, true, true);
    }
  };

  return (
    <Panel
      eyebrow="Governance & Authority"
      title="Owner Delegation & Boardroom Autonomy"
      testid="delegation-authority-panel"
      className="lg:col-span-12"
    >
      <div className="mb-6 rounded-xl border border-purple-500/20 bg-purple-950/20 p-4">
        <span className="text-[10px] font-bold uppercase tracking-widest text-purple-400">Delegation Framework</span>
        <p className="mt-1 text-xs text-slate-300">
          Determine how much operational autonomy is delegated to your executive team versus requiring direct owner sign-off.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3 mb-6">
        <button
          type="button"
          onClick={() => selectPreset("hands_on")}
          className={`rounded-xl border p-4 text-left transition ${
            mode === "hands_on"
              ? "border-amber-400 bg-amber-500/10 shadow-lg shadow-amber-950/30"
              : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
          }`}
          data-testid="preset-hands-on"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase text-amber-300">Hands-On Owner</span>
            {mode === "hands_on" && <CheckCircle className="h-4 w-4 text-amber-300" />}
          </div>
          <p className="mt-2 text-xs text-slate-300">
            You personally approve every transfer negotiation, youth contract, and tactical formation change.
          </p>
        </button>

        <button
          type="button"
          onClick={() => selectPreset("balanced")}
          className={`rounded-xl border p-4 text-left transition ${
            mode === "balanced"
              ? "border-sky-400 bg-sky-500/10 shadow-lg shadow-sky-950/30"
              : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
          }`}
          data-testid="preset-balanced"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase text-sky-300">Balanced Boardroom</span>
            {mode === "balanced" && <CheckCircle className="h-4 w-4 text-sky-300" />}
          </div>
          <p className="mt-2 text-xs text-slate-300">
            Recommended. Executive staff operate autonomously within approved budgets; owner retains veto on major actions.
          </p>
        </button>

        <button
          type="button"
          onClick={() => selectPreset("executive_led")}
          className={`rounded-xl border p-4 text-left transition ${
            mode === "executive_led"
              ? "border-emerald-400 bg-emerald-500/10 shadow-lg shadow-emerald-950/30"
              : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
          }`}
          data-testid="preset-executive-led"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase text-emerald-300">Executive-Led Group</span>
            {mode === "executive_led" && <CheckCircle className="h-4 w-4 text-emerald-300" />}
          </div>
          <p className="mt-2 text-xs text-slate-300">
            Complete executive delegation. The General Manager, HOYD, and Head Coach run full day-to-day operations.
          </p>
        </button>
      </div>

      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/70 p-5">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-300">Granular Autonomy Policies</h4>

        <div className="flex items-center justify-between py-2 border-b border-white/5">
          <div>
            <div className="text-xs font-bold text-white">GM Transfer & Release-Clause Autonomy</div>
            <p className="text-[11px] text-slate-400">General Manager may negotiate player signings and fee clauses within treasury cap.</p>
          </div>
          <button
            type="button"
            onClick={() => {
              const next = !gmTransfer;
              setGmTransfer(next);
              save(mode, next, hoydYouth, mgrTactics);
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${gmTransfer ? "bg-emerald-500" : "bg-slate-700"}`}
            data-testid="toggle-gm-autonomy"
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${gmTransfer ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>

        <div className="flex items-center justify-between py-2 border-b border-white/5">
          <div>
            <div className="text-xs font-bold text-white">HOYD Youth Contracts & Intake Autonomy</div>
            <p className="text-[11px] text-slate-400">Head of Youth Development may offer professional terms directly to top academy prospects.</p>
          </div>
          <button
            type="button"
            onClick={() => {
              const next = !hoydYouth;
              setHoydYouth(next);
              save(mode, gmTransfer, next, mgrTactics);
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${hoydYouth ? "bg-emerald-500" : "bg-slate-700"}`}
            data-testid="toggle-hoyd-autonomy"
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${hoydYouth ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>

        <div className="flex items-center justify-between py-2">
          <div>
            <div className="text-xs font-bold text-white">First-Team Manager Tactics & Lineup Autonomy</div>
            <p className="text-[11px] text-slate-400">Manager has unilateral discretion over matchday starting XI, formations, and tactical subs.</p>
          </div>
          <button
            type="button"
            onClick={() => {
              const next = !mgrTactics;
              setMgrTactics(next);
              save(mode, gmTransfer, hoydYouth, next);
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${mgrTactics ? "bg-emerald-500" : "bg-slate-700"}`}
            data-testid="toggle-manager-autonomy"
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${mgrTactics ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>
      </div>
    </Panel>
  );
}

// ============================================================================
// 4. Academy & Youth Development Panel
// ============================================================================
function AcademyDevelopmentPanel({ club }: any) {
  const academyLevel = club.facilities?.academy?.level ?? 2;

  return (
    <Panel
      eyebrow="Youth Pipeline"
      title="Academy & Youth Development Engine"
      testid="academy-development-panel"
      className="lg:col-span-12"
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-5">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">Homegrown Legacy</span>
          <h4 className="mt-1 text-base font-black text-white">Academy Tier Level {academyLevel} / 5</h4>
          <p className="mt-1 text-xs text-slate-300">
            Develop future superstars through the GTEX Regen Generation Engine. Homegrown players yield 100% equity retention.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/app/academy"
            className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-black text-slate-950 transition hover:bg-emerald-400"
            data-testid="launch-academy-hub-link"
          >
            <GraduationCap className="h-4 w-4" />
            <span>Open Academy Hub</span>
          </Link>
          <Link
            to="/app/build-a-son"
            className="flex items-center gap-1.5 rounded-lg border border-amber-400/40 bg-amber-400/10 px-4 py-2 text-xs font-black text-amber-200 transition hover:bg-amber-400/20"
            data-testid="launch-build-a-son-link"
          >
            <Sparkles className="h-4 w-4" />
            <span>Regen Studio</span>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <span className="text-[10px] uppercase font-bold text-slate-400">Intake Quality Rating</span>
          <div className="mt-1 text-2xl font-black text-emerald-400">{academyLevel * 18 + 10} / 100</div>
          <p className="mt-1 text-[11px] text-slate-400">Determines the ceiling potential of new prospects enrolled each season.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <span className="text-[10px] uppercase font-bold text-slate-400">Active Academy Squad</span>
          <div className="mt-1 text-2xl font-black text-white">8 Registered Prospects</div>
          <p className="mt-1 text-[11px] text-slate-400">Under-18 talent receiving daily coaching and physical development.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <span className="text-[10px] uppercase font-bold text-slate-400">Next Scheduled Intake</span>
          <div className="mt-1 text-2xl font-black text-amber-300">Spring Cycle</div>
          <p className="mt-1 text-[11px] text-slate-400">The GTEX youth generation worker evaluates academy facility tier upon arrival.</p>
        </div>
      </div>
    </Panel>
  );
}

// ============================================================================
// 5. Club Identity & Public Profile Publishing Panel
// ============================================================================
function ClubIdentityPublishingPanel({ club }: any) {
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState(false);

  const initialVisibility = club.visibility || "public";
  const [visibility, setVisibility] = useState<string>(initialVisibility);
  const [shortName, setShortName] = useState<string>(club.short_name || "");
  const [venueName, setVenueName] = useState<string>(club.home_venue_name || "");
  const [description, setDescription] = useState<string>(club.description || "");
  const [primaryColor, setPrimaryColor] = useState<string>(club.primary_color || "#0F766E");
  const [secondaryColor, setSecondaryColor] = useState<string>(club.secondary_color || "#F8FAFC");
  const [accentColor, setAccentColor] = useState<string>(club.accent_color || "#F59E0B");

  const publicUrl = `${window.location.origin}/club/${club.slug || club.club_id}`;

  const copyLink = () => {
    navigator.clipboard.writeText(publicUrl);
    toast.success("Public profile link copied to clipboard.");
  };

  const handleToggleVisibility = async () => {
    const next = visibility === "public" ? "private" : "public";
    setBusy(true);
    try {
      await api.patch(`/api/clubs/${club.club_id}`, { visibility: next });
      setVisibility(next);
      toast.success(`Club profile visibility set to ${next.toUpperCase()}.`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const handleSaveIdentity = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.patch(`/api/clubs/${club.club_id}`, {
        short_name: shortName.trim() || undefined,
        home_venue_name: venueName.trim() || undefined,
        description: description.trim() || undefined,
        primary_color: primaryColor,
        secondary_color: secondaryColor,
        accent_color: accentColor,
      });
      toast.success("Club identity details saved.");
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      eyebrow="Web Presence & Brand"
      title="Club Identity & Public Profile Publishing"
      testid="identity-publishing-panel"
      className="lg:col-span-12"
    >
      {/* Visibility Status Banner */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950/80 p-5">
        <div className="flex items-center gap-3">
          <div className={`flex h-12 w-12 items-center justify-center rounded-xl border ${visibility === "public" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-amber-500/40 bg-amber-500/10 text-amber-300"}`}>
            {visibility === "public" ? <Eye className="h-6 w-6" /> : <EyeOff className="h-6 w-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider ${visibility === "public" ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30" : "bg-amber-500/10 text-amber-300 border border-amber-500/30"}`}>
                {visibility === "public" ? "PUBLIC PROFILE ACTIVE" : "PRIVATE PROFILE (UNLISTED)"}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-300">
              {visibility === "public"
                ? "Your club is publicly accessible to the GTEX universe, fans, and prospective signings."
                : "Your club is unlisted. Only authenticated club executives can view this profile."}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Btn
            variant="secondary"
            onClick={copyLink}
            className="text-xs"
            data-testid="copy-public-profile-url-button"
          >
            <Copy className="h-3.5 w-3.5 mr-1" />
            <span>Copy Link</span>
          </Btn>
          <Link
            to={`/club/${club.slug || club.club_id}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs font-bold text-white transition hover:bg-slate-800"
            data-testid="view-public-profile-link"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>View Public Profile</span>
          </Link>
          <Btn
            variant={visibility === "public" ? "destructive" : "primary"}
            onClick={handleToggleVisibility}
            disabled={busy}
            className="text-xs"
            data-testid="toggle-visibility-button"
          >
            {busy ? "Updating..." : visibility === "public" ? "Unpublish (Set Private)" : "Publish to Web"}
          </Btn>
        </div>
      </div>

      {/* Privacy Policy & Boundaries Card */}
      <div className="mb-6 rounded-xl border border-sky-500/20 bg-sky-950/20 p-4">
        <div className="flex items-center gap-2 text-xs font-bold text-sky-300">
          <Shield className="h-4 w-4" />
          <span>Public Profile Privacy & Data Boundaries</span>
        </div>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 text-xs leading-5">
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 p-3">
            <span className="font-bold text-emerald-300">✓ Public Sporting Records</span>
            <ul className="mt-1 list-disc list-inside text-slate-300 space-y-0.5">
              <li>Club crest, colors, founded year, and stadium</li>
              <li>Public squad roster and standout player cards</li>
              <li>Club manager, GM, and HOYD appointed names</li>
              <li>Silverware, honours, and transport fleet</li>
            </ul>
          </div>
          <div className="rounded-lg border border-amber-500/20 bg-amber-950/10 p-3">
            <span className="font-bold text-amber-300">🔒 Boardroom Confidential</span>
            <ul className="mt-1 list-disc list-inside text-slate-300 space-y-0.5">
              <li>Club bank treasury balance & cash disbursements</li>
              <li>Player contract wages & confidential release clauses</li>
              <li>Executive salaries & severance terms</li>
              <li>Internal boardroom chat, directives, and dilemmas</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Identity Form */}
      <form onSubmit={handleSaveIdentity} className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-5">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-300">Edit Club Identity & Branding</h4>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-[10px] font-bold uppercase text-slate-400">Short Name</label>
            <input
              type="text"
              maxLength={40}
              value={shortName}
              onChange={(e) => setShortName(e.target.value)}
              placeholder="e.g. AFC Lagos"
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white outline-none focus:border-sky-400"
              data-testid="input-short-name"
            />
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase text-slate-400">Home Venue / Stadium Name</label>
            <input
              type="text"
              maxLength={120}
              value={venueName}
              onChange={(e) => setVenueName(e.target.value)}
              placeholder="e.g. Cathedral Arena"
              className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white outline-none focus:border-sky-400"
              data-testid="input-venue-name"
            />
          </div>
        </div>

        <div>
          <label className="text-[10px] font-bold uppercase text-slate-400">Club History & Ethos Description</label>
          <textarea
            rows={3}
            maxLength={1000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Tell the story of your club, football philosophy, and regional identity..."
            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white outline-none focus:border-sky-400"
            data-testid="textarea-description"
          />
        </div>

        <div>
          <label className="text-[10px] font-bold uppercase text-slate-400">Official Club Colors</label>
          <div className="mt-2 flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="h-8 w-8 cursor-pointer rounded border border-white/20 bg-transparent"
              />
              <span className="text-xs text-slate-300 font-mono">Primary: {primaryColor}</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={secondaryColor}
                onChange={(e) => setSecondaryColor(e.target.value)}
                className="h-8 w-8 cursor-pointer rounded border border-white/20 bg-transparent"
              />
              <span className="text-xs text-slate-300 font-mono">Secondary: {secondaryColor}</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="h-8 w-8 cursor-pointer rounded border border-white/20 bg-transparent"
              />
              <span className="text-xs text-slate-300 font-mono">Accent: {accentColor}</span>
            </div>
          </div>
        </div>

        <div className="pt-2">
          <Btn type="submit" variant="primary" disabled={busy} data-testid="save-identity-button">
            {busy ? "Saving..." : "Save Identity Changes"}
          </Btn>
        </div>
      </form>
    </Panel>
  );
}

// ============================================================================
// 6. Club News & Notifications Panel
// ============================================================================
function ClubNewsNotificationsPanel({ club }: any) {
  const [category, setCategory] = useState("all");
  const { data, isLoading, refetch } = useNewsroom(club.club_id, category, 25);
  const items: any[] = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];

  return (
    <Panel
      eyebrow="Live Wire"
      title="Club Newsroom & Boardroom Dispatches"
      testid="news-notifications-panel"
      className="lg:col-span-12"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1">
          {["all", "match", "transfer", "infrastructure", "commercial"].map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategory(cat)}
              className={`rounded-lg px-3 py-1 text-xs font-bold uppercase transition ${
                category === cat ? "bg-amber-400 text-slate-950" : "bg-slate-900 text-slate-400 hover:text-white"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-300 hover:text-white"
          >
            <RefreshCw className="h-3 w-3" />
            <span>Refresh</span>
          </button>
          <Link
            to="/app/newsroom"
            className="flex items-center gap-1 text-xs font-bold text-amber-300 hover:text-amber-200"
          >
            <span>Full Newsroom</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      {isLoading ? (
        <Loading />
      ) : items.length === 0 ? (
        <Empty
          title="No dispatches recorded"
          body="Matchday events, transfer milestones, and facility upgrades will publish here automatically."
        />
      ) : (
        <div className="space-y-2">
          {items.map((item: any) => (
            <div
              key={item.id}
              className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 transition hover:border-slate-700"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-300">
                <Newspaper className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <h5 className="truncate text-xs font-bold text-white">{item.headline || item.title || "Dispatch"}</h5>
                  <span className="text-[10px] text-slate-500 shrink-0">
                    {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Just now"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400 line-clamp-2">{item.summary || item.body || item.content}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

// ============================================================================
// 7. Showroom & Luxury Assets Panel
// ============================================================================
function ShowroomPanel({ club }: any) {
  const refresh = useRefreshOwner();
  const { data, isLoading } = useClubShowroom(club.club_id);
  const { data: clubDetail } = useClub(club.club_id);
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [acquiringItem, setAcquiringItem] = useState<any | null>(null);
  const [giftingItem, setGiftingItem] = useState<any | null>(null);
  const [recipientType, setRecipientType] = useState<"player" | "staff">("player");
  const [selectedStaffRole, setSelectedStaffRole] = useState<string>("first_team_manager");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [giftNote, setGiftNote] = useState<string>("");
  const [giftReceipt, setGiftReceipt] = useState<any | null>(null);
  const [purchaseReceipt, setPurchaseReceipt] = useState<any | null>(null);

  const purchaseIntentKeys = useRef(new Map<string, string>());
  const giftIntentKeys = useRef(new Map<string, string>());
  const stableIntentKey = (store: React.MutableRefObject<Map<string, string>>, identity: string, prefix: string) => {
    const existing = store.current.get(identity);
    if (existing) return existing;
    const nonce = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const created = `${prefix}:${club.club_id}:${identity}:${nonce}`;
    store.current.set(identity, created);
    return created;
  };

  const rawCatalog = data?.catalog ?? data?.showroom?.catalog ?? data?.showroom;
  const rawOwnedAssets = data?.owned_assets ?? data?.showroom?.owned_assets;
  const rawSquad = data?.squad ?? clubDetail?.squad ?? club.squad;
  const items: any[] = Array.isArray(rawCatalog) ? rawCatalog : [];
  const ownedAssets: any[] = Array.isArray(rawOwnedAssets) ? rawOwnedAssets : [];
  const squad: any[] = Array.isArray(rawSquad) ? rawSquad : [];
  const eligibleRegens: any[] = squad.filter((player: any) => player?.is_regen === true);
  const selectedPlayer = eligibleRegens.find((p: any) => p.id === selectedPlayerId);
  const keyOf = (item: any) => String(item?.catalog_key || item?.key || item?.id || "");
  const formatPrice = (item: any) => fmt(item?.price_gtex, 2);
  const assetImage = (item: any) => item?.image_url || "";

  const handlePurchase = async (item: any) => {
    const catalogKey = keyOf(item);
    if (!catalogKey || busyItem) return;
    setBusyItem(catalogKey);
    try {
      const res = await api.post(`/owner/clubs/${club.club_id}/showroom/purchase`, {
        catalog_key: catalogKey,
        idempotency_key: stableIntentKey(purchaseIntentKeys, catalogKey, "showroom-purchase"),
      });
      const result = res.data ?? {};
      purchaseIntentKeys.current.delete(catalogKey);
      setAcquiringItem(null);
      setPurchaseReceipt({ item, result });
      const acquiredName = result?.asset?.custom_name || item?.name || "prestige asset";
      if (result?.broadcast_globally === true) {
        toast.success(`Acquired ${acquiredName}. Verified notice published to the GTEX global wire.`);
      } else {
        toast.success(`Acquired ${acquiredName} for club operations.`);
      }
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyItem(null);
    }
  };

  const clubPrestige = data?.club_prestige ?? clubDetail?.health?.prestige ?? club?.health?.prestige ?? 60;
  const prestigeTierNum = data?.prestige_tier ?? (clubPrestige >= 90 ? 1 : clubPrestige >= 75 ? 2 : clubPrestige >= 55 ? 3 : clubPrestige >= 35 ? 4 : 5);
  const prestigeTierLabel = prestigeTierNum === 1 ? "Tier 1: Global Superclub" : prestigeTierNum === 2 ? "Tier 2: Continental Challenger" : prestigeTierNum === 3 ? "Tier 3: National Contender" : prestigeTierNum === 4 ? "Tier 4: Regional Pioneer" : "Tier 5: Grassroots Foundation";

  const staffRoles = [
    { role: "first_team_manager", name: "First-Team Manager", effect: "+15 Morale & Tactical Alignment" },
    { role: "general_manager", name: "General Manager", effect: "+20 Loyalty & Sponsor Relations" },
    { role: "head_of_youth", name: "Head of Youth Dev", effect: "+15 Academy Pipeline Loyalty" },
    { role: "chief_scout", name: "Chief Scout", effect: "+15 Scouting Motivation" },
    { role: "medical_director", name: "Head of Medical", effect: "+15 Fitness Regimen Dedication" },
  ];

  const handleGift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!giftingItem || busyItem) return;
    if (recipientType === "player" && !selectedPlayerId) return;
    const catalogKey = keyOf(giftingItem);
    if (!catalogKey) {
      toast.error("This showroom item is missing its catalogue reference.");
      return;
    }
    const targetIdentifier = recipientType === "player" ? selectedPlayerId : selectedStaffRole;
    const giftIntent = `${catalogKey}:${targetIdentifier}`;
    setBusyItem(`gift:${catalogKey}`);
    try {
      const { data: responseData } = await api.post(`/owner/clubs/${club.club_id}/showroom/gift`, {
        player_id: recipientType === "player" ? selectedPlayerId : undefined,
        recipient_type: recipientType,
        staff_role: recipientType === "staff" ? selectedStaffRole : undefined,
        catalog_key: catalogKey,
        note: giftNote.trim(),
        idempotency_key: stableIntentKey(giftIntentKeys, giftIntent, "showroom-gift"),
      });
      const result = responseData ?? {};
      giftIntentKeys.current.delete(giftIntent);
      const recipient = recipientType === "player"
        ? (result?.player || selectedPlayer)
        : { name: staffRoles.find(r => r.role === selectedStaffRole)?.name || selectedStaffRole.replace(/_/g, " ").toUpperCase(), role: selectedStaffRole };
      setGiftReceipt({ item: giftingItem, player: recipient, note: giftNote.trim(), result, recipientType });
      setGiftingItem(null);
      setSelectedPlayerId("");
      setGiftNote("");
      const giftName = giftingItem?.name || result?.asset?.custom_name || "luxury gift";
      toast.success(`GTEX recorded ${giftName} for ${recipient?.name || "recipient"}.`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyItem(null);
    }
  };

  const rarityFor = (item: any) => {
    const category = String(item.category || "").toLowerCase();
    if (category === "jet" || item.price_gtex >= 4000) return "Prestige";
    if (item.can_gift_to_player) return "Player eligible";
    if (category === "facility") return "Infrastructure";
    return "Private collection";
  };

  return (
    <Panel
      eyebrow="Luxury Fleet & Gifting"
      title="Showroom & Prestige Assets"
      testid="showroom-panel"
      className="lg:col-span-12"
    >
      <div className="mb-5 flex flex-col gap-3 rounded-xl border border-amber-500/20 bg-gradient-to-r from-amber-500/[0.09] via-slate-900/60 to-transparent p-4 sm:flex-row sm:items-center">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-amber-300/30 bg-amber-400/10 text-amber-200">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.23em] text-amber-200">The owner's private collection</div>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-300">
            Acquire prestige assets through the club treasury, or purchase a player-eligible gift and deliver it directly to a registered squad member.
          </p>
        </div>
        <div className="sm:ml-auto flex items-center gap-3 shrink-0">
          <div className="shrink-0 rounded-lg border border-amber-500/30 bg-amber-950/40 px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-amber-300 font-bold">Prestige Rating</div>
            <div className="font-mono text-sm font-black text-amber-200">
              {clubPrestige}/100 <span className="text-[10px] text-slate-400">· Tier {prestigeTierNum}</span>
            </div>
            <div className="text-[9px] text-amber-300/80 font-medium">{prestigeTierLabel}</div>
          </div>
          <Link
            to="/app/showroom"
            className="flex items-center gap-1 rounded-lg border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs font-bold text-amber-200 hover:bg-amber-400/20 transition-colors"
            data-testid="open-dedicated-showroom-link"
          >
            <span>Dedicated Showroom</span>
            <ExternalLink className="h-3 w-3" />
          </Link>
          <div className="shrink-0 rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-slate-500">Treasury</div>
            <div className="font-mono text-sm font-bold text-amber-200">{fmt(club.cash || club.economy?.cash_gtex)} GTX</div>
          </div>
        </div>
      </div>

      {isLoading ? (
        <Loading />
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-8 text-center">
          <Gift className="mx-auto mb-3 h-8 w-8 text-amber-300" />
          <div className="text-sm font-bold text-white">Showroom catalogue unavailable</div>
          <p className="mx-auto mt-2 max-w-md text-xs text-slate-400">
            GTEX did not return the luxury catalogue. Refresh the club data before trying to purchase or gift any item.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((it: any) => {
            const key = keyOf(it);
            const isJet = it.category === "jet";
            const isBusy = busyItem === key;
            return (
              <article
                key={key}
                data-testid={`showroom-item-${key}`}
                className="group flex min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 shadow-lg shadow-black/15 transition-all duration-300 hover:-translate-y-0.5 hover:border-amber-400/40 hover:shadow-amber-900/10"
              >
                <div className="relative h-44 overflow-hidden border-b border-white/5 bg-slate-950">
                  {assetImage(it) ? (
                    <img
                      src={assetImage(it)}
                      alt={it.name}
                      className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.opacity = "0";
                      }}
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-900 via-slate-950 to-amber-900/10">
                      <Building className="h-12 w-12 text-amber-300/70" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/10 to-transparent" />
                  <div className="absolute left-3 top-3">
                    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[9px] font-black uppercase tracking-wider ${isJet ? "border-amber-300/40 bg-amber-400/15 text-amber-200" : "border-slate-600 bg-slate-950/80 text-slate-300"}`}>
                      {isJet ? <ExternalLink className="h-3 w-3" /> : <LockKeyhole className="h-3 w-3" />}
                      {isJet ? "Eligible global wire" : "Private"}
                    </span>
                  </div>
                  <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between gap-2">
                    <span className="rounded-md border border-white/10 bg-slate-950/75 px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-slate-200">{rarityFor(it)}</span>
                    <span className="flex items-center gap-1 rounded-md bg-slate-950/80 px-2 py-1 font-mono text-[11px] font-black text-amber-200">
                      <Coins className="h-3 w-3" /> {formatPrice(it)} GTX
                    </span>
                  </div>
                </div>

                <div className="flex flex-1 flex-col p-4">
                  <div className="min-h-[92px]">
                    <h4 className="text-sm font-extrabold leading-snug text-white">{it.name}</h4>
                    <p className="mt-1 line-clamp-3 text-[11px] leading-5 text-slate-400">{it.model || it.description || "A limited prestige asset for your club collection."}</p>
                  </div>
                  <div className="mt-auto space-y-2 border-t border-slate-800 pt-3">
                    <div className="flex items-center justify-between gap-2 text-[10px] text-slate-500">
                      <span>Club treasury debit</span>
                      <span className="font-mono font-bold text-slate-300">{formatPrice(it)} GTX</span>
                    </div>
                    <div className="flex gap-2">
                      <Btn
                        variant="secondary"
                        className="flex-1 text-xs"
                        disabled={!key || !!busyItem}
                        onClick={() => setAcquiringItem(it)}
                      >
                        {isBusy ? "Processing..." : "Acquire asset"}
                      </Btn>
                      {it.can_gift_to_player && (
                        <div className="min-w-0 flex-1">
                          <Btn
                            variant="ghost"
                            className="w-full border border-purple-400/25 px-3 text-xs text-purple-300 hover:border-purple-300/60 hover:text-purple-200"
                            disabled={!!busyItem}
                            title={`Gift ${it.name} to player or staff`}
                            onClick={() => {
                              setGiftingItem(it);
                              setRecipientType("player");
                              setSelectedPlayerId(eligibleRegens[0]?.id || squad[0]?.id || "");
                            }}
                          >
                            <Gift className="mr-1 h-3.5 w-3.5" /> Gift Asset
                          </Btn>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Purchase Modal */}
      {acquiringItem && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-purchase-confirm">
          <div className="w-full max-w-md overflow-hidden rounded-2xl border border-amber-300/35 bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/20 shadow-2xl">
            <div className="relative h-40 bg-slate-950">
              {assetImage(acquiringItem) && <img src={assetImage(acquiringItem)} alt={acquiringItem.name} className="h-full w-full object-cover" />}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent" />
              <button type="button" onClick={() => setAcquiringItem(null)} className="absolute right-3 top-3 rounded-full border border-white/15 bg-black/60 p-2 text-white"><X className="h-4 w-4" /></button>
              <div className="absolute bottom-3 left-4 right-4">
                <div className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-200">Treasury authorisation</div>
                <h3 className="mt-1 text-lg font-black text-white">{acquiringItem.name}</h3>
              </div>
            </div>
            <div className="space-y-4 p-5">
              <p className="text-xs leading-5 text-slate-300">Confirm this acquisition. GTEX will validate the catalogue item and debit the verified price from your club treasury.</p>
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-black/25 px-3 py-3">
                <span className="text-xs text-slate-400">Total price</span>
                <span className="font-mono text-base font-black text-amber-200">{formatPrice(acquiringItem)} GTX</span>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => setAcquiringItem(null)} className="flex-1 rounded-lg border border-slate-700 px-4 py-3 text-xs font-bold text-slate-300 hover:bg-white/5" disabled={!!busyItem}>Cancel</button>
                <button type="button" onClick={() => handlePurchase(acquiringItem)} className="flex-1 rounded-lg bg-amber-300 px-4 py-3 text-xs font-black text-slate-950 transition hover:bg-amber-200 disabled:opacity-50" disabled={!!busyItem}>
                  {busyItem ? "Processing..." : `Confirm · ${formatPrice(acquiringItem)} GTX`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Gift Modal */}
      {giftingItem && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-gift-confirm">
          <div className="w-full max-w-lg overflow-hidden rounded-2xl border border-purple-400/30 bg-gradient-to-br from-slate-900 via-slate-950 to-purple-950/25 shadow-2xl">
            <div className="relative h-44 bg-slate-950">
              {assetImage(giftingItem) && <img src={assetImage(giftingItem)} alt={giftingItem.name} className="h-full w-full object-cover opacity-90" />}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/10 to-transparent" />
              <button type="button" onClick={() => setGiftingItem(null)} className="absolute right-3 top-3 rounded-full border border-white/15 bg-black/60 p-2 text-white"><X className="h-4 w-4" /></button>
              <div className="absolute bottom-3 left-4 right-4">
                <div className="flex items-center gap-1 text-[9px] font-black uppercase tracking-[0.2em] text-purple-200"><Gift className="h-3 w-3" /> A personal club reward</div>
                <h3 className="mt-1 text-lg font-black text-white">{giftingItem.name}</h3>
                <div className="mt-1 font-mono text-xs font-bold text-amber-200">{formatPrice(giftingItem)} GTX · charged to club treasury</div>
              </div>
            </div>
            <form onSubmit={handleGift} className="space-y-4 p-5">
              <div className="flex rounded-lg border border-purple-500/30 bg-purple-950/40 p-1">
                <button
                  type="button"
                  onClick={() => setRecipientType("player")}
                  className={`flex-1 rounded-md py-1.5 text-xs font-bold transition ${recipientType === "player" ? "bg-purple-600 text-white" : "text-purple-300"}`}
                >
                  Squad Player / Regen
                </button>
                <button
                  type="button"
                  onClick={() => setRecipientType("staff")}
                  className={`flex-1 rounded-md py-1.5 text-xs font-bold transition ${recipientType === "staff" ? "bg-purple-600 text-white" : "text-purple-300"}`}
                >
                  Coach / Executive Staff
                </button>
              </div>

              {recipientType === "player" ? (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Choose player or regen</label>
                  <div className="mt-2 grid max-h-52 gap-2 overflow-y-auto sm:grid-cols-2">
                    {(eligibleRegens.length > 0 ? eligibleRegens : squad).map((p: any) => (
                      <button
                        type="button"
                        key={p.id}
                        onClick={() => setSelectedPlayerId(p.id)}
                        className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${selectedPlayerId === p.id ? "border-purple-300/70 bg-purple-400/10" : "border-slate-800 bg-slate-950/50 hover:border-slate-600"}`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-extrabold text-white">{p.name}</div>
                          <div className="mt-0.5 text-[10px] text-slate-500">{p.position || "Squad player"} · OVR {p.rating ?? "—"}</div>
                        </div>
                        {selectedPlayerId === p.id && <CheckCircle className="h-4 w-4 shrink-0 text-purple-200" />}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Select Coach or Executive Staff</label>
                  <div className="mt-2 space-y-2">
                    {staffRoles.map((s) => (
                      <button
                        type="button"
                        key={s.role}
                        onClick={() => setSelectedStaffRole(s.role)}
                        className={`flex w-full items-center justify-between rounded-xl border p-3 text-left transition ${selectedStaffRole === s.role ? "border-purple-300/70 bg-purple-400/10" : "border-slate-800 bg-slate-950/50"}`}
                      >
                        <div>
                          <div className="text-xs font-bold text-white">{s.name}</div>
                          <div className="text-[10px] text-purple-300">{s.effect}</div>
                        </div>
                        {selectedStaffRole === s.role && <CheckCircle className="h-4 w-4 text-purple-200" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Personal note</label>
                <input
                  type="text"
                  maxLength={180}
                  value={giftNote}
                  onChange={(e) => setGiftNote(e.target.value)}
                  placeholder="A reward for the performance. A message from the owner."
                  className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-3 text-xs text-white outline-none focus:border-purple-300/60"
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setGiftingItem(null)} className="flex-1 rounded-lg border border-slate-700 px-4 py-3 text-xs font-bold text-slate-300 hover:bg-white/5" disabled={!!busyItem}>Cancel</button>
                <button
                  type="submit"
                  disabled={(recipientType === "player" && !selectedPlayerId) || (recipientType === "staff" && !selectedStaffRole) || !!busyItem}
                  className="flex-1 rounded-lg bg-purple-500 px-4 py-3 text-xs font-black text-white transition hover:bg-purple-400 disabled:opacity-50"
                >
                  {busyItem === `gift:${keyOf(giftingItem)}` ? "Delivering..." : `Confirm gift · ${formatPrice(giftingItem)} GTX`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Purchase Receipt */}
      {purchaseReceipt && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-purchase-receipt">
          <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-amber-300/50 bg-slate-950 p-6 text-center shadow-2xl">
            <CheckCircle className="mx-auto h-12 w-12 text-emerald-400" />
            <h3 className="mt-3 text-xl font-black text-white">{purchaseReceipt.result?.asset?.custom_name || purchaseReceipt.item.name}</h3>
            <p className="mt-2 text-xs text-slate-300">The GTEX showroom has confirmed the purchase and recorded the charge against your club treasury.</p>
            <button type="button" onClick={() => setPurchaseReceipt(null)} className="mt-5 w-full rounded-lg bg-amber-300 px-4 py-3 text-xs font-black text-slate-950 hover:bg-amber-200">Return to showroom</button>
          </div>
        </div>
      )}

      {/* Gift Receipt */}
      {giftReceipt && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/85 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-gift-receipt">
          <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-purple-300/50 bg-slate-950 p-6 text-center shadow-2xl">
            <Gift className="mx-auto h-12 w-12 text-purple-300" />
            <h3 className="mt-3 text-xl font-black text-white">{giftReceipt.item.name}</h3>
            <p className="mt-2 text-xs text-slate-300">A personal gift from the club owner to {giftReceipt.player?.name || "Recipient"}.</p>
            <button type="button" onClick={() => setGiftReceipt(null)} className="mt-5 w-full rounded-lg bg-purple-400 px-4 py-3 text-xs font-black text-slate-950 hover:bg-purple-300">Return to the club</button>
          </div>
        </div>
      )}
    </Panel>
  );
}

// ============================================================================
// 8. Capital & Treasury Panel
// ============================================================================
function Capital({ club, clubs }: any) {
  const refresh = useRefreshOwner();
  const [amount, setAmount] = useState("1000");
  const [target, setTarget] = useState("");
  const run = async (path: string, body: any, ok: string) => {
    try {
      await api.post(path, body);
      toast.success(ok);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const sisters = clubs.filter((c: any) => c.club_id !== club.club_id);

  return (
    <Panel eyebrow="Approved capital actions" title="Treasury & Liquidity" testid="capital-panel" className="lg:col-span-6">
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Club cash" value={<Coin amount={club.economy?.cash_gtex ?? club.cash} />} />
        <Stat label="Pending payouts" value={<Coin amount={club.economy?.pending_payouts ?? 0} />} />
      </div>
      <label className="gx-label mt-5">Amount (GTX)</label>
      <input
        data-testid="capital-amount-input"
        className="gx-input"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <Btn
          variant="secondary"
          data-testid="inject-capital-button"
          onClick={() =>
            run(
              "/owner/capital/inject",
              { club_id: club.club_id, amount: Number(amount) },
              "Capital injected from your wallet."
            )
          }
        >
          Inject from wallet
        </Btn>
        <Btn
          variant="secondary"
          data-testid="distribute-button"
          onClick={() =>
            run(
              "/owner/capital/distribute",
              { club_id: club.club_id, amount: Number(amount) },
              "Distributed earned revenue to your wallet."
            )
          }
        >
          Distribute earnings
        </Btn>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Only earned club revenue (gate, prizes, sponsors, sales) can be distributed. Launch grants stay in the club.
      </p>
      {sisters.length > 0 && (
        <div className="mt-5 border-t border-white/5 pt-4">
          <label className="gx-label">Move to sister club (capped 25%, disclosed)</label>
          <div className="flex gap-2">
            <select
              data-testid="sister-club-select"
              className="gx-input"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Select club</option>
              {sisters.map((s: any) => (
                <option key={s.club_id} value={s.club_id}>
                  {s.club_name}
                </option>
              ))}
            </select>
            <Btn
              variant="secondary"
              disabled={!target}
              data-testid="sister-transfer-button"
              onClick={() =>
                run(
                  "/owner/capital/sister-transfer",
                  { from_club_id: club.club_id, to_club_id: target, amount: Number(amount) },
                  "Related-party capital move ledgered."
                )
              }
            >
              Move
            </Btn>
          </div>
        </div>
      )}
    </Panel>
  );
}

// ============================================================================
// 9. Commercial & Sponsors Panel
// ============================================================================
function Commercial({ club }: any) {
  const { data } = useQuery({
    queryKey: ["supporters", club.club_id],
    queryFn: async () => (await api.get(`/owner/clubs/${club.club_id}/supporters`)).data.leaderboard,
  });
  const sponsors = club.sponsors || [];
  const disclosures = club.disclosures || [];

  return (
    <>
      <Panel eyebrow="Commercial · 70/30 split" title="Sponsors" testid="sponsors-panel" className="lg:col-span-6">
        {sponsors.length === 0 ? (
          <Empty title="No sponsors" body="Sponsor offers arrive in your inbox as fans and commercial level grow." />
        ) : (
          <div className="space-y-2">
            {sponsors.map((s: any) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-sm border border-white/5 p-3 text-sm"
              >
                <div>
                  <p className="text-white">{s.sponsor}</p>
                  <p className="text-xs text-slate-500">
                    {s.slot} · {s.matches_remaining} matches left
                  </p>
                </div>
                <div className="text-right">
                  <Coin amount={s.club_share} />
                  <p className="text-[10px] text-slate-500">club share / match</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel eyebrow="Supporters" title="Gift leaderboard" testid="supporters-panel" className="lg:col-span-6">
        {(data || []).length === 0 ? (
          <Empty title="No gifts yet" body="Fans gift during and after matches." />
        ) : (
          <ol className="space-y-2">
            {data.map((r: any, i: number) => (
              <li key={r.user_id} className="flex justify-between text-sm">
                <span>
                  <span className="gx-mono mr-2 text-slate-500">{i + 1}</span>
                  {r.username}
                </span>
                <Coin amount={r.fan_coin_sent} currency="FAN" />
              </li>
            ))}
          </ol>
        )}
      </Panel>
      <Panel eyebrow="Transparency" title="Related-party history" testid="disclosures-panel" className="lg:col-span-6">
        {disclosures.length === 0 ? (
          <p className="text-sm text-slate-500">No related-party transfers disclosed.</p>
        ) : (
          disclosures.map((d: any) => (
            <div key={d.id} className="mb-2 rounded-sm border border-amber-500/20 p-3 text-xs text-slate-300">
              {d.player_name}: fee {fmt(d.fee)} (fair value {fmt(d.fair_value)})
            </div>
          ))
        )}
      </Panel>
    </>
  );
}

// ============================================================================
// 10. Multi-Club Expansion Form
// ============================================================================
function NewClub({ count, max }: any) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const loc = useClubLocation();
  const [busy, setBusy] = useState(false);
  if (count >= max) return null;
  const location = loc.validation;
  const clubName = name.trim();

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
      await api.post("/clubs", {
        club_name: clubName,
        slug,
        short_name: clubName.slice(0, 12),
        primary_color: "#0F766E",
        secondary_color: "#F8FAFC",
        accent_color: "#F59E0B",
        ...clubLocationPayload(validatedLocation),
        club_type: "community",
      });
      navigate("/onboarding");
    } catch (e) {
      toast.error(clubCreateErrorMessage(e, errMsg));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel eyebrow={`Expand · ${count}/${max} clubs`} title="Add a Sister Club" testid="new-club-panel">
      <p className="mb-3 text-sm text-slate-400">
        Owning several clubs establishes a registered multi-club ownership group. Sister clubs cannot share a prize bracket,
        and transfers between them must sit inside a verified fair-value band.
      </p>
      <div className="space-y-2">
        <input
          data-testid="new-club-name-input"
          aria-label="Club name"
          className="gx-input"
          placeholder="Club name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div>
          <ClubLocationFields state={loc} testIdPrefix="new-club" disabled={busy} />
        </div>
        <Btn disabled={clubName.length < 3 || !location.valid || busy} onClick={create} data-testid="create-club-button">
          Create
        </Btn>
      </div>
    </Panel>
  );
}

// ============================================================================
// 11. HQ Overview Operational Hub
// ============================================================================
function HQOverview({ club, onSelectTab }: { club: any; onSelectTab: (tabId: string) => void }) {
  const facilities = club.facilities || {};
  const stadiumLevel = facilities.stadium?.level ?? 2;
  const academyLevel = facilities.academy?.level ?? 2;
  const visibility = club.visibility || "public";

  return (
    <div className="space-y-6">
      {/* Operational Readiness Status Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-sky-500/20 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-sky-400">Stadium Arena</span>
            <span className="rounded bg-sky-500/10 px-2 py-0.5 text-[10px] font-bold text-sky-300">L{stadiumLevel}/5</span>
          </div>
          <div className="mt-2 text-base font-black text-white">{club.home_venue_name || "Cathedral Stadium"}</div>
          <p className="mt-1 text-xs text-slate-400">Capacity ~{stadiumLevel * 15000 + 10000} · Hybrid Pitch Ready</p>
          <button
            type="button"
            onClick={() => onSelectTab("facilities")}
            className="mt-3 text-xs font-bold text-sky-400 hover:text-sky-300 flex items-center gap-1"
          >
            <span>Campus Blueprint</span> →
          </button>
        </div>

        <div className="rounded-xl border border-emerald-500/20 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-emerald-400">Academy Pipeline</span>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300">L{academyLevel}/5</span>
          </div>
          <div className="mt-2 text-base font-black text-white">Active Regen Pipeline</div>
          <p className="mt-1 text-xs text-slate-400">Youth recruitment ceiling active · Next intake prepared</p>
          <button
            type="button"
            onClick={() => onSelectTab("academy")}
            className="mt-3 text-xs font-bold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            <span>Youth Pipeline</span> →
          </button>
        </div>

        <div className="rounded-xl border border-indigo-500/20 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-indigo-400">Boardroom Hierarchy</span>
            <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-300">Staff Active</span>
          </div>
          <div className="mt-2 text-base font-black text-white">{club.manager?.name || "Manager Appointed"}</div>
          <p className="mt-1 text-xs text-slate-400">Tactical alignment high · Executive team intact</p>
          <button
            type="button"
            onClick={() => onSelectTab("organisation")}
            className="mt-3 text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            <span>Executive Staff</span> →
          </button>
        </div>

        <div className="rounded-xl border border-amber-500/20 bg-slate-950/70 p-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-amber-400">Public Profile</span>
            <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${visibility === "public" ? "bg-emerald-500/10 text-emerald-300" : "bg-amber-500/10 text-amber-300"}`}>
              {visibility.toUpperCase()}
            </span>
          </div>
          <div className="mt-2 text-base font-black text-white">Global Sporting Identity</div>
          <p className="mt-1 text-xs text-slate-400">
            {visibility === "public" ? "Web profile published & verified" : "Profile currently unlisted"}
          </p>
          <button
            type="button"
            onClick={() => onSelectTab("identity")}
            className="mt-3 text-xs font-bold text-amber-400 hover:text-amber-300 flex items-center gap-1"
          >
            <span>Publishing Hub</span> →
          </button>
        </div>
      </div>

      {/* Quick Launchpad */}
      <div className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 p-6">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-4">Command Action Launcher</h4>
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
          <Link
            to="/app/campus"
            className="flex items-center gap-3 rounded-xl border border-white/5 bg-slate-950/60 p-3.5 transition hover:border-sky-500/40 hover:bg-sky-500/5"
            data-testid="quick-link-campus"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-500/10 text-sky-300">
              <Building className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-extrabold text-white">3D Campus</div>
              <span className="text-[10px] text-slate-400">Cathedral architect</span>
            </div>
          </Link>

          <Link
            to="/app/showroom"
            className="flex items-center gap-3 rounded-xl border border-white/5 bg-slate-950/60 p-3.5 transition hover:border-amber-500/40 hover:bg-amber-500/5"
            data-testid="quick-link-showroom"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-300">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-extrabold text-white">Showroom Fleet</div>
              <span className="text-[10px] text-slate-400">Jets & prestige collection</span>
            </div>
          </Link>

          <Link
            to="/app/academy"
            className="flex items-center gap-3 rounded-xl border border-white/5 bg-slate-950/60 p-3.5 transition hover:border-emerald-500/40 hover:bg-emerald-500/5"
            data-testid="quick-link-academy"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-300">
              <GraduationCap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-extrabold text-white">Youth Academy</div>
              <span className="text-[10px] text-slate-400">Regens & wonderkids</span>
            </div>
          </Link>

          <Link
            to={`/club/${club.slug || club.club_id}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 rounded-xl border border-white/5 bg-slate-950/60 p-3.5 transition hover:border-purple-500/40 hover:bg-purple-500/5"
            data-testid="quick-link-public-profile"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-300">
              <Eye className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-extrabold text-white">Public Profile</div>
              <span className="text-[10px] text-slate-400">Live fan showcase</span>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN CLUB HQ PAGE COMPONENT
// ============================================================================
export default function MyClubs() {
  const { clubs, active, select } = useActiveClub();
  const { data: cc } = useControlCenter();
  const { data: club, isLoading } = useClub(active?.club_id);
  const [activeTab, setActiveTab] = useState<string>("overview");

  const TABS = [
    { id: "overview", label: "HQ Overview", icon: Activity },
    { id: "organisation", label: "Organisation & Staff", icon: Users },
    { id: "delegation", label: "Delegation & Governance", icon: Sliders },
    { id: "facilities", label: "Facilities & Campus", icon: Building },
    { id: "academy", label: "Youth Development", icon: GraduationCap },
    { id: "treasury", label: "Treasury & Showroom", icon: Coins },
    { id: "identity", label: "Identity & Publishing", icon: Eye },
    { id: "news", label: "Dispatches & News", icon: Newspaper },
  ];

  return (
    <div data-testid="my-clubs-page" className="space-y-6 pb-12">
      <PageHeader
        eyebrow="Club HQ"
        title={club?.club_name || "Club Operations"}
        sub={club?.ownership_group?.label || "Multi-Club Ownership Group"}
        action={
          <div className="flex flex-wrap items-center gap-2">
            {club && (
              <>
                <Link
                  to={`/club/${club.slug || club.club_id}`}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-sky-400/40 bg-sky-500/10 text-sky-200 font-bold text-xs transition hover:bg-sky-500/20"
                  data-testid="header-public-profile-link"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Public Profile</span>
                </Link>
                <Link
                  to={`/app/clubs/${club.club_id}/story`}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors"
                  data-testid="header-club-story-link"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Club Story</span>
                </Link>
              </>
            )}
            <div className="flex gap-1">
              {clubs.map((c: any) => (
                <button
                  key={c.club_id}
                  data-testid={`select-club-${c.club_id}`}
                  onClick={() => select(c.club_id)}
                  className={`gx-btn text-xs ${c.club_id === active?.club_id ? "gx-btn-primary" : "gx-btn-secondary"}`}
                >
                  {c.club_name}
                </button>
              ))}
            </div>
          </div>
        }
      />

      {isLoading || !club ? (
        <Loading />
      ) : (
        <div className="space-y-6">
          {/* Executive Summary Banner */}
          <Panel className="lg:col-span-12" testid="club-summary">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-6">
              <Stat label="Club value" value={<Coin amount={club.value} />} />
              <Stat label="Fans" value={fmt(club.health?.fans)} />
              <Stat label="Prestige" value={club.health?.prestige ?? 60} />
              <Stat label="Squad" value={club.health?.squad_size ?? 0} />
              <Stat label="Manager" value={club.manager?.name || "-"} />
              <Stat
                label="Status"
                value={<Chip tone={club.stage === "active" ? "emerald" : "gold"}>{club.stage || "Active"}</Chip>}
              />
            </div>
          </Panel>

          {/* Tabbed Navigation Bar */}
          <div className="flex overflow-x-auto gap-1 border-b border-white/10 pb-2 scrollbar-none" data-testid="club-hq-tabs">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  data-testid={`tab-${tab.id}`}
                  className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold transition-all ${
                    isActive
                      ? "bg-amber-400 text-slate-950 shadow-md font-extrabold"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Active Tab Views */}
          {activeTab === "overview" && (
            <div className="space-y-6" data-testid="tab-content-overview">
              <HQOverview club={club} onSelectTab={(t) => setActiveTab(t)} />
              <Facilities club={club} />
              <div className="grid gap-6 lg:grid-cols-12">
                <Capital club={club} clubs={clubs} />
                <Commercial club={club} />
              </div>
            </div>
          )}

          {activeTab === "organisation" && (
            <div data-testid="tab-content-organisation">
              <OrganisationalStructurePanel club={club} />
            </div>
          )}

          {activeTab === "delegation" && (
            <div data-testid="tab-content-delegation">
              <DelegationAuthorityPanel club={club} />
            </div>
          )}

          {activeTab === "facilities" && (
            <div data-testid="tab-content-facilities">
              <Facilities club={club} />
            </div>
          )}

          {activeTab === "academy" && (
            <div data-testid="tab-content-academy">
              <AcademyDevelopmentPanel club={club} />
            </div>
          )}

          {activeTab === "treasury" && (
            <div className="space-y-6" data-testid="tab-content-treasury">
              <ShowroomPanel club={club} />
              <div className="grid gap-6 lg:grid-cols-12">
                <Capital club={club} clubs={clubs} />
                <Commercial club={club} />
              </div>
            </div>
          )}

          {activeTab === "identity" && (
            <div data-testid="tab-content-identity">
              <ClubIdentityPublishingPanel club={club} />
            </div>
          )}

          {activeTab === "news" && (
            <div data-testid="tab-content-news">
              <ClubNewsNotificationsPanel club={club} />
            </div>
          )}

          {/* Add a Sister Club Form */}
          <div className="pt-4 border-t border-white/5">
            <NewClub count={clubs.length} max={cc?.max_clubs || 3} />
          </div>
        </div>
      )}
    </div>
  );
}

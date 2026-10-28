import React, { useState, useMemo } from "react";
import {
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  X,
  Users,
  UserCheck,
  UserMinus,
  MessageSquare,
  Settings2,
  TrendingUp,
  Sparkles,
  Shield,
  HeartPulse,
  Search,
  Award,
  DollarSign,
  Briefcase,
  Sprout,
  Send,
  Shirt,
  Compass,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, useActiveClub, useClub, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Loading, PageHeader, Panel, TraitBar } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";
import { PlayerDrawer } from "@/components/gtex/PlayerDrawer";
import { journeyLinks, readJourneyParams, SQUAD_SEASON_LABEL } from "@/lib/playerJourney";

function ManagerSheet({ club }: any) {
  const m = club.manager_profile || {};
  const refresh = useRefreshOwner();
  const fire = async () => {
    if (!window.confirm("Dismissing the manager triggers compensation and unsettles the squad. Continue?")) return;
    try {
      const { data } = await api.post(`/owner/clubs/${club.club_id}/manager/fire`);
      toast.warning(`Paid ${fmt(data.compensation)} GTX compensation. ${data.why}`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Manager realism engine" title={m.name} testid="manager-sheet" className="lg:col-span-5"
      action={<Btn variant="danger" onClick={fire} data-testid="fire-manager-button">Dismiss</Btn>}>
      <div className="mb-5 flex flex-wrap gap-2">
        <Chip tone="cyan">{m.tactical_preference}</Chip>
        <Chip tone="gold">Temperament: {m.temperament}</Chip>
        <Chip tone="purple">{m.rarity}</Chip>
      </div>
      <div className="space-y-3">
        <TraitBar label="Tactical Vision" value={m.tactics_stat} />
        <TraitBar label="Discipline" value={m.discipline} />
        <TraitBar label="Youth Development" value={m.youth_dev} />
        <TraitBar label="Player Loyalty" value={m.loyalty} />
      </div>
      <p className="mt-4 text-xs italic text-slate-400">"{m.philosophy_summary}"</p>
    </Panel>
  );
}

function HireManager({ club }: any) {
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState<string | null>(null);
  const { data: catalog = [] } = useQuery({ queryKey: ["mgr-catalog-6"], queryFn: async () => (await api.get("/managers/catalog", { params: { limit: 6 } })).data.items });
  const hire = async (m: any) => {
    setBusy(m.manager_id);
    try {
      await api.post(`/owner/clubs/${club.club_id}/manager`, { manager: { manager_id: m.manager_id, display_name: m.display_name, rarity: m.rarity, mentality: m.mentality, tactics: m.tactics, traits: m.traits, philosophy_summary: m.philosophy_summary } });
      toast.success(`Hired ${m.display_name} as manager.`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <Panel eyebrow="Candidate market" title="Available managers" testid="hire-manager-panel" className="lg:col-span-12">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {catalog.map((m: any) => (
          <div key={m.manager_id} className="rounded border border-white/10 bg-slate-900/60 p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-white">{m.display_name}</p>
                <p className="text-xs text-slate-400">{m.mentality} · {m.rarity}</p>
              </div>
              <Btn variant="secondary" onClick={() => hire(m)} disabled={busy === m.manager_id}>
                {busy === m.manager_id ? "Hiring…" : "Hire"}
              </Btn>
            </div>
            <p className="mt-2 text-xs text-slate-400">{m.philosophy_summary}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function SquadCards({ club, onSelectPlayer }: any) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-testid="squad-cards-grid">
      {club.squad.map((p: any) => (
        <div key={p.id} className="cursor-pointer" onClick={() => onSelectPlayer && onSelectPlayer(p)}>
          <PlayerCard
            name={p.name}
            rating={p.rating}
            potential={p.potential}
            position={p.position}
            age={p.age}
            nationality={p.nationality}
            club={club.club_name}
            image={p.image || p.portrait_url || p.image_url}
            regen={Boolean(p.is_regen)}
            variant="compact"
            testid={`squad-player-${p.id}`}
            onClick={() => onSelectPlayer && onSelectPlayer(p)}
          />
        </div>
      ))}
    </div>
  );
}

function SquadTable({ club, targetPlayerId, onSelectPlayer }: any) {
  const [view, setView] = useState<"table" | "cards">("table");
  const [mentality, setMentality] = useState(club.mentality || "balanced");
  const save = async (m: string) => {
    try {
      await api.put(`/owner/clubs/${club.club_id}/mentality`, { mentality: m });
      setMentality(m);
      toast.success(`Default mentality updated to ${m}.`);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow={`${club.squad.length} players`} title="Squad" testid="squad-table-panel" className="lg:col-span-7"
      action={<div className="flex flex-wrap gap-1">{["cards", "table"].map((v) => <button key={v} data-testid={`squad-view-${v}`} onClick={() => setView(v as any)} className={`gx-btn ${view === v ? "gx-btn-primary" : "gx-btn-ghost"}`}>{v}</button>)}<span className="mx-1 w-px bg-white/10" />{["defensive", "balanced", "attacking"].map((m) => <button key={m} data-testid={`default-mentality-${m}`} onClick={() => save(m)} className={`gx-btn ${mentality === m ? "gx-btn-primary" : "gx-btn-secondary"}`}>{m}</button>)}</div>}>
      {view === "cards" ? <div className="gx-scroll max-h-[640px] overflow-auto pr-1"><SquadCards club={club} onSelectPlayer={onSelectPlayer} /></div> : (
      <div className="gx-scroll max-h-[560px] overflow-auto">
        <table className="gx-table w-full min-w-[620px]">
          <thead><tr><th>Player</th><th>Pos</th><th>Age</th><th>Rtg/Pot</th><th>Morale</th><th>Mins</th><th>Value</th></tr></thead>
          <tbody>
            {club.squad.map((p: any) => {
              const isTarget = targetPlayerId && (p.id === targetPlayerId || p.player_id === targetPlayerId);
              return (
                <tr
                  key={p.id}
                  data-testid={`squad-row-${p.id}`}
                  onClick={() => onSelectPlayer && onSelectPlayer(p)}
                  className={`cursor-pointer transition-colors hover:bg-emerald-500/10 ${isTarget ? "bg-emerald-500/10 border-l-4 border-emerald-400" : ""}`}
                >
                  <td className="font-medium text-white">
                    {p.name} {p.is_regen && <Chip tone="emerald">Regen</Chip>} {p.status === "listed" && <Chip tone="gold">Listed</Chip>} {p.injured_days > 0 && <Chip tone="red">Injured</Chip>}
                    {isTarget && <Chip tone="cyan">Target Prospect</Chip>}
                  </td>
                  <td className="capitalize">{p.position}</td>
                  <td className="gx-mono">{p.age}</td>
                  <td className="gx-mono">{p.rating}<span className="text-slate-500">/{p.potential}</span></td>
                  <td className="gx-mono">{p.morale}</td>
                  <td className="gx-mono">{p.minutes}</td>
                  <td className="gx-mono font-medium text-emerald-300">{fmt(p.value_coin)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      )}
    </Panel>
  );
}

function SquadRegistrationPanel({ club, targetPlayerId }: any) {
  const [busy, setBusy] = useState("");
  const registrationQuery = useQuery({
    queryKey: ["squad-registration", club.club_id],
    queryFn: async () =>
      (await api.get("/clubs/" + encodeURIComponent(club.club_id) + "/squad-registration", {
        params: { season_label: SQUAD_SEASON_LABEL },
      })).data,
    enabled: Boolean(club?.club_id),
  });
  const registration = registrationQuery.data || null;
  const status = String(registration?.status || "not synced").toLowerCase();
  const endpoint = "/clubs/" + encodeURIComponent(club.club_id) + "/squad-registration";

  const targetInRegistration = Boolean(
    targetPlayerId && (registration?.players || []).some((rp: any) => rp.player_id === targetPlayerId || rp.id === targetPlayerId),
  );
  const targetInClubSquad = Boolean(
    targetPlayerId && (club.squad || []).some((sp: any) => sp.id === targetPlayerId || sp.player_id === targetPlayerId),
  );

  const sync = async () => {
    setBusy("sync");
    try {
      const playerIds = (club.squad || []).map((p: any) => String(p.player_ref || p.id));
      await api.post(endpoint, { season_label: SQUAD_SEASON_LABEL, player_ids: playerIds });
      await registrationQuery.refetch();
      toast.success("Club squad synced for registration.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };
  const submit = async () => {
    if (!registration) {
      toast.error("Sync the squad first, then submit registration.");
      return;
    }
    setBusy("submit");
    try {
      await api.post(endpoint + "/submit", undefined, { params: { season_label: SQUAD_SEASON_LABEL } });
      await registrationQuery.refetch();
      toast.success("Squad registration submitted.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };
  const lock = async () => {
    if (!window.confirm("Locking the squad finalizes this competition roster for the current registration window. Continue?")) return;
    setBusy("lock");
    try {
      await api.post(endpoint + "/lock", undefined, { params: { season_label: SQUAD_SEASON_LABEL } });
      await registrationQuery.refetch();
      toast.success("Squad registration locked.");
    } catch (error) {
      toast.error(errMsg(error));
    } finally {
      setBusy("");
    }
  };
  const tone = status === "locked" ? "emerald" : status === "submitted" ? "cyan" : status === "draft" ? "gold" : "slate";
  const canSync = status !== "locked";
  const canSubmit = Boolean(registration) && status !== "locked";
  const canLock = Boolean(registration) && status !== "locked";

  return (
    <Panel
      eyebrow="Competition readiness"
      title="Lineup & squad registration"
      testid="squad-registration-panel"
      className="mb-6"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone={tone}>{status === "not synced" ? "Not synced" : status}</Chip>
          <span className="text-xs text-slate-400">
            {registration ? String((registration.players || []).length) + " registered players" : "No roster registered yet"}
          </span>
          <span className="text-xs text-slate-500">Season: {registration?.season_label || SQUAD_SEASON_LABEL}</span>
        </div>

        {/* Targeted prospect journey status */}
        {targetPlayerId && (
          <div
            className={`rounded-lg p-3 text-xs border flex items-center justify-between gap-2 ${
              targetInRegistration
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                : targetInClubSquad
                ? "bg-amber-950/40 border-amber-500/40 text-amber-200"
                : "bg-slate-900/60 border-white/10 text-slate-300"
            }`}
            data-testid="target-prospect-registration-status"
          >
            <div className="flex items-center gap-2">
              {targetInRegistration ? (
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle size={16} className="text-amber-400 shrink-0" />
              )}
              <span>
                {targetInRegistration
                  ? `Target prospect ${targetPlayerId} is confirmed in this competition registration (${status}).`
                  : targetInClubSquad
                  ? `Target prospect ${targetPlayerId} is in your club squad roster, but not yet included in the competition registration. Click "Sync squad" below to update the roster.`
                  : `Target prospect ${targetPlayerId} is not in this club's squad yet. Verify transfer settlement in the Transfer Hub before registering.`}
              </span>
            </div>
          </div>
        )}

        {registration && Object.keys(registration.position_summary || {}).length > 0 && (
          <div className="flex flex-wrap gap-2" data-testid="squad-registration-position-summary">
            {Object.entries(registration.position_summary || {}).map(([position, count]: [string, any]) => (
              <Chip key={position}>{position}: {count}</Chip>
            ))}
          </div>
        )}
        <p className="max-w-3xl text-sm leading-6 text-slate-400">
          Sync the current club roster, submit it for eligibility checks, then lock it when ready. Registration is persisted separately from the tactical starting XI.
        </p>
        {registrationQuery.isError && (
          <p role="alert" className="text-sm text-amber-300">
            Registration status could not be loaded. Sync can retry the registration request.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Btn
            variant="secondary"
            onClick={sync}
            disabled={Boolean(busy) || registrationQuery.isLoading || !canSync}
            data-testid="squad-sync-registration-button"
          >
            {busy === "sync" ? "Syncing…" : "Sync squad"}
          </Btn>
          <Btn
            onClick={submit}
            disabled={Boolean(busy) || registrationQuery.isLoading || !canSubmit}
            data-testid="squad-submit-registration-button"
          >
            {busy === "submit" ? "Submitting…" : "Submit registration"}
          </Btn>
          <Btn
            variant="secondary"
            onClick={lock}
            disabled={Boolean(busy) || registrationQuery.isLoading || !canLock}
            data-testid="squad-lock-registration-button"
          >
            {busy === "lock" ? "Locking…" : "Lock registration"}
          </Btn>
        </div>
        {status === "locked" && (
          <p className="text-xs text-emerald-300">This registration is locked. The squad must be reopened through an authorized lifecycle flow before it can be changed.</p>
        )}
      </div>
    </Panel>
  );
}

const STAFF_ROLES: Array<{
  key: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  badgeTone: "purple" | "cyan" | "emerald" | "gold" | "red";
  effectKey: string;
  effectLabel: string;
}> = [
  {
    key: "general_manager",
    label: "General Manager (GM)",
    icon: Briefcase,
    color: "text-purple-400",
    badgeTone: "purple",
    effectKey: "transfer_fee_discount_pct",
    effectLabel: "Transfer Discount & Sponsorship",
  },
  {
    key: "first_team_manager",
    label: "First-Team Manager",
    icon: Shirt,
    color: "text-sky-400",
    badgeTone: "cyan",
    effectKey: "tactical_match_bonus",
    effectLabel: "Tactics & Matchday Momentum",
  },
  {
    key: "head_of_youth_development",
    label: "Head of Youth Dev (HOYD)",
    icon: Sprout,
    color: "text-emerald-400",
    badgeTone: "emerald",
    effectKey: "academy_potential_bonus",
    effectLabel: "Academy Potential & Regen Growth",
  },
  {
    key: "chief_scout",
    label: "Chief Scout",
    icon: Search,
    color: "text-amber-400",
    badgeTone: "gold",
    effectKey: "scouting_precision_bonus",
    effectLabel: "Scouting Precision & Wonderkid Pull",
  },
  {
    key: "medical_director",
    label: "Medical Director",
    icon: HeartPulse,
    color: "text-rose-400",
    badgeTone: "red",
    effectKey: "injury_recovery_bonus",
    effectLabel: "Injury Recovery & Fatigue Guard",
  },
];

function StaffChatModal({
  clubId,
  initialRole = "general_manager",
  appointedStaff,
  onClose,
}: {
  clubId: string;
  initialRole?: string;
  appointedStaff?: any;
  onClose: () => void;
}) {
  const [activeRole, setActiveRole] = useState(initialRole);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  const { data: chatData, refetch } = useQuery({
    queryKey: ["staff-chat", clubId, activeRole],
    queryFn: async () => {
      try {
        const { data } = await api.get(`/owner/clubs/${clubId}/staff/chat`, {
          params: { role: activeRole },
        });
        return data;
      } catch {
        return { history: [] };
      }
    },
    enabled: Boolean(clubId && activeRole),
  });

  React.useEffect(() => {
    if (chatData?.history) {
      setHistory(chatData.history);
    }
  }, [chatData]);

  const currentRoleConfig = STAFF_ROLES.find((r) => r.key === activeRole) || STAFF_ROLES[0];
  const staffMember = appointedStaff?.[activeRole] || { name: `${currentRoleConfig.label}` };

  const suggestions: Record<string, string[]> = {
    general_manager: [
      "Review our transfer budget and financial runway.",
      "Are there commercial sponsor partnerships on the table?",
      "Recommend priority signings for this window.",
    ],
    first_team_manager: [
      "How sharp is squad morale and readiness for the next match?",
      "Can we adjust to a high pressing tactical shape?",
      "Who deserves more starting minutes in training?",
    ],
    head_of_youth_development: [
      "Which academy prospect has the highest ceiling?",
      "Who is ready for a first-team senior contract?",
      "How are our youth training facilities performing?",
    ],
    chief_scout: [
      "What top-tier regens have we spotted across Africa & Latin America?",
      "Provide a scouting dossier on available wonderkids.",
      "Which positions lack depth in our current pipeline?",
    ],
    medical_director: [
      "Report on current squad fitness and injury recovery timelines.",
      "Are any key players carrying fatigue risks?",
      "What preventive conditioning regimens are active?",
    ],
  };

  const handleSend = async (customText?: string) => {
    const text = (customText || message).trim();
    if (!text || busy) return;
    setBusy(true);

    const userEntry = {
      sender: "Club Owner",
      role: "owner",
      role_label: "Owner",
      message: text,
      timestamp: new Date().toISOString(),
    };
    setHistory((prev) => [...prev, userEntry]);
    setMessage("");

    try {
      const { data } = await api.post(`/owner/clubs/${clubId}/staff/chat`, {
        role: activeRole,
        message: text,
      });
      if (data?.reply) {
        setHistory((prev) => [...prev, data.reply]);
      } else if (data?.history) {
        setHistory(data.history);
      }
      refetch();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="staff-chat-modal">
      <div className="flex h-[600px] w-full max-w-2xl flex-col rounded-2xl border border-white/10 bg-[#070B11] shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/10 bg-slate-950/80 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-xl bg-purple-500/20 text-purple-300 border border-purple-500/30">
              <MessageSquare size={18} />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="gx-display text-lg font-black uppercase text-white">Boardroom AI Staff Chat</h3>
                <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-[9px] font-black uppercase">
                  Persona Grounded
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Direct council with <b className="text-white">{staffMember.name}</b> · {currentRoleConfig.label}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:text-white hover:bg-white/10"><X size={18} /></button>
        </div>

        {/* Role Selector Tabs */}
        <div className="flex overflow-x-auto border-b border-white/10 bg-black/40 px-4 py-2 gap-1.5">
          {STAFF_ROLES.map((r) => {
            const Icon = r.icon;
            const active = r.key === activeRole;
            return (
              <button
                key={r.key}
                onClick={() => setActiveRole(r.key)}
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold whitespace-nowrap transition-all ${
                  active
                    ? "bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon size={14} className={r.color} />
                <span>{r.label.split(" (")[0]}</span>
              </button>
            );
          })}
        </div>

        {/* Message Viewport */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {history.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <p className="text-sm font-bold text-slate-300">Start the council with your {currentRoleConfig.label}</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Ask questions regarding transfers, tactical adjustments, youth contracts, or training regimens.
              </p>
            </div>
          ) : (
            history.map((msg, idx) => {
              const isOwner = msg.role === "owner" || msg.sender === "Club Owner";
              return (
                <div key={idx} className={`flex flex-col ${isOwner ? "items-end" : "items-start"}`}>
                  <span className="text-[10px] font-bold text-slate-500 mb-1 px-1">
                    {msg.sender || (isOwner ? "Owner" : currentRoleConfig.label)}
                  </span>
                  <div
                    className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                      isOwner
                        ? "bg-emerald-600 text-white rounded-br-none shadow-md"
                        : "bg-slate-900 border border-white/10 text-slate-200 rounded-bl-none shadow-md"
                    }`}
                  >
                    {msg.message}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Quick Suggestion Prompts */}
        <div className="border-t border-white/10 bg-slate-950/60 px-4 py-2 flex flex-wrap gap-1.5">
          {(suggestions[activeRole] || []).map((sug, i) => (
            <button
              key={i}
              onClick={() => handleSend(sug)}
              disabled={busy}
              className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] text-slate-300 hover:border-purple-400/50 hover:text-white transition"
            >
              “{sug}”
            </button>
          ))}
        </div>

        {/* Message Input Box */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 border-t border-white/10 bg-slate-950 p-4"
        >
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={`Ask ${staffMember.name || currentRoleConfig.label}...`}
            className="gx-input flex-1 text-xs"
            disabled={busy}
          />
          <button
            type="submit"
            disabled={!message.trim() || busy}
            className="gx-btn gx-btn-primary flex items-center gap-1.5 text-xs px-4"
          >
            <Send size={13} />
            <span>{busy ? "Thinking…" : "Send"}</span>
          </button>
        </form>
      </div>
    </div>
  );
}

function BoardroomSection({ club }: any) {
  const refresh = useRefreshOwner();
  const [chatRole, setChatRole] = useState<string | null>(null);
  const [hiringBusy, setHiringBusy] = useState<string | null>(null);
  const [marqueePremiums, setMarqueePremiums] = useState<Record<string, boolean>>({});
  const [delegationBusy, setDelegationBusy] = useState(false);
  const [roleFilter, setRoleFilter] = useState("all");

  const { data: staffData, refetch: refetchStaff } = useQuery({
    queryKey: ["club-staff", club.club_id],
    queryFn: async () => {
      try {
        const { data } = await api.get(`/owner/clubs/${club.club_id}/staff`);
        return data;
      } catch {
        return null;
      }
    },
    enabled: Boolean(club?.club_id),
  });

  const appointed = staffData?.appointed_staff || {
    first_team_manager: club.manager_profile || {
      name: club.manager?.name || "Kwame Mensah",
      tactics_stat: 76,
      discipline: 74,
      youth_dev: 78,
    },
    general_manager: { name: "Adeola Alabi", attributes: { negotiations: 82, commercial: 80 } },
    head_of_youth_development: { name: "Ousmane Diallo", attributes: { talent_spotting: 85, youth_conditioning: 81 } },
    chief_scout: { name: "Lars Lindstrom", attributes: { international_network: 83, precision: 80 } },
    medical_director: { name: "Dr. Chioma Eze", attributes: { sports_medicine: 86, rehabilitation: 84 } },
  };

  const effects = staffData?.staff_effects || {
    transfer_fee_discount_pct: 5,
    sponsor_revenue_bonus_pct: 8,
    academy_potential_bonus: 4,
    tactical_match_bonus: 3,
    scouting_precision_bonus: 6,
    injury_recovery_bonus: 10,
  };

  const delegation = staffData?.delegation_policy || {
    mode: "balanced",
    gm_transfer_autonomy: false,
    hoyd_youth_contracts: false,
    manager_tactics_autonomy: true,
  };

  const clubPrestige = staffData?.club_prestige ?? club.health?.prestige ?? 55;
  const prestigeTier = staffData?.prestige_tier ?? (clubPrestige >= 85 ? 1 : clubPrestige >= 70 ? 2 : clubPrestige >= 50 ? 3 : clubPrestige >= 35 ? 4 : 5);
  const candidates: any[] = staffData?.candidates || [
    { staff_id: "st-cand-1", role: "general_manager", name: "David Sterling", min_prestige: 60, salary_gtex: 12500, specialty: "Continental Broadcast & Kit Sponsor Magnate" },
    { staff_id: "st-cand-2", role: "head_of_youth_development", name: "Bakary Traore", min_prestige: 50, salary_gtex: 9000, specialty: "Master of African Academy Regens & Pace Archetypes" },
    { staff_id: "st-cand-3", role: "chief_scout", name: "Matteo Silva", min_prestige: 65, salary_gtex: 11000, specialty: "South American Wonderkid & High-Ceiling Specialist" },
    { staff_id: "st-cand-4", role: "medical_director", name: "Dr. Elena Rostova", min_prestige: 55, salary_gtex: 9500, specialty: "Advanced Cryotherapy & Hamstring Injury Recovery" },
  ];

  const handleHire = async (candidate: any) => {
    setHiringBusy(candidate.staff_id);
    const usePremium = Boolean(marqueePremiums[candidate.staff_id]);
    try {
      await api.post(`/owner/clubs/${club.club_id}/staff/hire`, {
        staff_id: candidate.staff_id,
        role: candidate.role,
        marquee_wage_premium: usePremium,
      });
      toast.success(`Appointed ${candidate.name} as ${candidate.role.replace(/_/g, " ")}.`);
      await refetchStaff();
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setHiringBusy(null);
    }
  };

  const handleFireStaff = async (role: string) => {
    if (!window.confirm(`Dismiss ${role.replace(/_/g, " ")} from executive staff?`)) return;
    try {
      await api.post(`/owner/clubs/${club.club_id}/staff/${role}/fire`);
      toast.warning(`Dismissed ${role.replace(/_/g, " ")}.`);
      await refetchStaff();
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const handleUpdateDelegation = async (updates: Partial<typeof delegation>) => {
    setDelegationBusy(true);
    const nextPolicy = { ...delegation, ...updates };
    try {
      await api.put(`/owner/clubs/${club.club_id}/delegation`, nextPolicy);
      toast.success("Boardroom delegation policy updated.");
      await refetchStaff();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setDelegationBusy(false);
    }
  };

  const filteredCandidates = roleFilter === "all" ? candidates : candidates.filter((c) => c.role === roleFilter);

  return (
    <section className="space-y-6 mb-8" data-testid="executive-boardroom-section">
      {/* 1. Header & Prestige Tier Overview */}
      <div className="rounded-2xl border-2 border-purple-500/30 bg-gradient-to-br from-[#180a29] via-[#0d091a] to-[#06040c] p-6 sm:p-8 shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-purple-400/40 bg-purple-950/80 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-purple-300">
              <Shield size={12} /> Executive Boardroom & Football Operations
            </div>
            <h2 className="gx-display mt-2 text-2xl sm:text-3xl font-black uppercase text-white">
              Club Executive Leadership
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
              Appoint elite executives to amplify transfer fee discounts, academy regens, tactical acumen, and medical recovery.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-white/10 bg-black/50 p-3 text-right">
              <p className="text-[10px] uppercase font-bold text-slate-400">Club Prestige</p>
              <p className="gx-mono text-2xl font-black text-amber-300">{clubPrestige}/100</p>
              <span className="text-[10px] font-bold uppercase text-emerald-400">Tier {prestigeTier} Standing</span>
            </div>
          </div>
        </div>

        {/* Staff Effects Grid */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-center">
            <p className="text-[9px] uppercase font-bold text-slate-400">Transfer Discount</p>
            <p className="gx-mono text-lg font-black text-purple-300 mt-0.5">-{effects.transfer_fee_discount_pct ?? 5}%</p>
            <p className="text-[9px] text-slate-500">GM Autonomy</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-center">
            <p className="text-[9px] uppercase font-bold text-slate-400">Sponsor Bonus</p>
            <p className="gx-mono text-lg font-black text-emerald-300 mt-0.5">+{effects.sponsor_revenue_bonus_pct ?? 8}%</p>
            <p className="text-[9px] text-slate-500">Commercial</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-center">
            <p className="text-[9px] uppercase font-bold text-slate-400">Academy Potential</p>
            <p className="gx-mono text-lg font-black text-cyan-300 mt-0.5">+{effects.academy_potential_bonus ?? 4} pts</p>
            <p className="text-[9px] text-slate-500">HOYD Intake</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-center">
            <p className="text-[9px] uppercase font-bold text-slate-400">Tactical Match Bonus</p>
            <p className="gx-mono text-lg font-black text-amber-300 mt-0.5">+{effects.tactical_match_bonus ?? 3} pts</p>
            <p className="text-[9px] text-slate-500">Manager Tactics</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-center">
            <p className="text-[9px] uppercase font-bold text-slate-400">Scouting Precision</p>
            <p className="gx-mono text-lg font-black text-blue-300 mt-0.5">+{effects.scouting_precision_bonus ?? 6}%</p>
            <p className="text-[9px] text-slate-500">Chief Scout</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/40 p-3 text-center">
            <p className="text-[9px] uppercase font-bold text-slate-400">Injury Recovery</p>
            <p className="gx-mono text-lg font-black text-rose-300 mt-0.5">+{effects.injury_recovery_bonus ?? 10}%</p>
            <p className="text-[9px] text-slate-500">Medical Speed</p>
          </div>
        </div>
      </div>

      {/* 2. 5 Appointed Executive Roles */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5" data-testid="appointed-staff-grid">
        {STAFF_ROLES.map((roleDef) => {
          const person = appointed[roleDef.key];
          const Icon = roleDef.icon;
          const isAppointed = Boolean(person?.name);

          return (
            <div
              key={roleDef.key}
              className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 shadow-lg space-y-3 hover:border-white/20 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className={`flex size-8 items-center justify-center rounded-lg bg-white/5 ${roleDef.color}`}>
                    <Icon size={16} />
                  </span>
                  <Chip tone={roleDef.badgeTone}>{isAppointed ? "Appointed" : "Vacant"}</Chip>
                </div>
                <p className="text-[10px] font-black uppercase text-slate-400 tracking-wider mt-2">
                  {roleDef.label}
                </p>
                <h4 className="font-bold text-white text-sm truncate mt-0.5">
                  {person?.name || "Unassigned"}
                </h4>
                <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                  {person?.specialty || person?.philosophy_summary || roleDef.effectLabel}
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setChatRole(roleDef.key)}
                  className="w-full rounded-lg bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/40 py-1.5 text-xs font-bold text-purple-200 flex items-center justify-center gap-1.5 transition"
                  data-testid={`chat-staff-${roleDef.key}`}
                >
                  <MessageSquare size={13} />
                  <span>Talk to Staff</span>
                </button>
                {isAppointed && (
                  <button
                    type="button"
                    onClick={() => handleFireStaff(roleDef.key)}
                    className="w-full text-center text-[10px] font-bold uppercase text-red-400 hover:text-red-300 py-1 transition"
                  >
                    Dismiss / Replace
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. Boardroom Delegation Policy Controls */}
      <Panel eyebrow="Strategic Governance" title="Boardroom Delegation Policy" testid="delegation-policy-panel">
        <p className="text-xs text-slate-400 mb-4 max-w-2xl leading-relaxed">
          Decide how much authority to delegate to your General Manager, Head of Youth Development, and First-Team Manager.
        </p>

        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className="text-xs uppercase font-bold text-slate-400 mr-2">Governance Mode:</span>
          {(["hands_on", "balanced", "gm_led"] as const).map((m) => (
            <button
              key={m}
              type="button"
              disabled={delegationBusy}
              onClick={() => handleUpdateDelegation({ mode: m })}
              className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition ${
                delegation.mode === m
                  ? "bg-purple-600 text-white shadow-md border border-purple-400"
                  : "bg-white/5 text-slate-400 hover:text-white border border-white/10"
              }`}
            >
              {m.replace(/_/g, " ")}
            </button>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-3 pt-3 border-t border-white/10">
          <label className="flex items-start gap-3 rounded-xl border border-white/10 bg-black/30 p-3.5 cursor-pointer hover:bg-black/50 transition">
            <input
              type="checkbox"
              checked={Boolean(delegation.gm_transfer_autonomy)}
              onChange={(e) => handleUpdateDelegation({ gm_transfer_autonomy: e.target.checked })}
              className="mt-0.5 rounded border-white/20 bg-slate-900 text-purple-600"
            />
            <div>
              <p className="text-xs font-bold text-white">GM Transfer Autonomy</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Allows GM to negotiate fees and submit shortlist targets.</p>
            </div>
          </label>

          <label className="flex items-start gap-3 rounded-xl border border-white/10 bg-black/30 p-3.5 cursor-pointer hover:bg-black/50 transition">
            <input
              type="checkbox"
              checked={Boolean(delegation.hoyd_youth_contracts)}
              onChange={(e) => handleUpdateDelegation({ hoyd_youth_contracts: e.target.checked })}
              className="mt-0.5 rounded border-white/20 bg-slate-900 text-emerald-600"
            />
            <div>
              <p className="text-xs font-bold text-white">HOYD Youth Autonomy</p>
              <p className="text-[11px] text-slate-400 mt-0.5">HOYD automatically signs contracts for top academy gems.</p>
            </div>
          </label>

          <label className="flex items-start gap-3 rounded-xl border border-white/10 bg-black/30 p-3.5 cursor-pointer hover:bg-black/50 transition">
            <input
              type="checkbox"
              checked={Boolean(delegation.manager_tactics_autonomy)}
              onChange={(e) => handleUpdateDelegation({ manager_tactics_autonomy: e.target.checked })}
              className="mt-0.5 rounded border-white/20 bg-slate-900 text-sky-600"
            />
            <div>
              <p className="text-xs font-bold text-white">Manager Tactical Autonomy</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Manager commands in-match tactical changes and subs.</p>
            </div>
          </label>
        </div>
      </Panel>

      {/* 4. Candidate Market per Role */}
      <Panel eyebrow="Talent Acquisition" title="Executive & Coaching Candidate Market" testid="staff-candidates-panel">
        <div className="flex flex-wrap gap-2 mb-5">
          <button
            onClick={() => setRoleFilter("all")}
            className={`gx-btn ${roleFilter === "all" ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
          >
            All Candidates ({candidates.length})
          </button>
          {STAFF_ROLES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRoleFilter(r.key)}
              className={`gx-btn ${roleFilter === r.key ? "gx-btn-primary" : "gx-btn-ghost"} text-xs`}
            >
              {r.label.split(" (")[0]}
            </button>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCandidates.map((cand) => {
            const meetsPrestige = clubPrestige >= (cand.min_prestige || 50);
            const isHiring = hiringBusy === cand.staff_id;
            const usePremium = Boolean(marqueePremiums[cand.staff_id]);

            return (
              <div
                key={cand.staff_id}
                className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-3"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-white text-sm">{cand.name}</p>
                      <p className="text-xs text-purple-300 font-semibold uppercase">{cand.role.replace(/_/g, " ")}</p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[9px] font-black uppercase border ${
                        meetsPrestige
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                      }`}
                    >
                      Min Prestige {cand.min_prestige || 50}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 mt-2 leading-relaxed">{cand.specialty}</p>

                  <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <span>Base Wage:</span>
                    <b className="gx-mono text-white">{fmt(cand.salary_gtex || 10000)} GTX / season</b>
                  </div>

                  {!meetsPrestige && (
                    <label className="mt-3 flex items-center gap-2 rounded bg-amber-950/40 border border-amber-500/30 p-2 text-[10px] text-amber-200 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={usePremium}
                        onChange={(e) =>
                          setMarqueePremiums((prev) => ({ ...prev, [cand.staff_id]: e.target.checked }))
                        }
                        className="rounded border-amber-500/40 bg-slate-900 text-amber-500"
                      />
                      <span>Offer Marquee Wage Premium (+25% wage to bypass prestige deficit)</span>
                    </label>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleHire(cand)}
                  disabled={Boolean(hiringBusy) || (!meetsPrestige && !usePremium)}
                  className={`w-full rounded-lg py-2 text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                    meetsPrestige || usePremium
                      ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-md"
                      : "bg-slate-800 text-slate-500 cursor-not-allowed"
                  }`}
                  data-testid={`hire-staff-${cand.staff_id}`}
                >
                  <UserCheck size={14} />
                  <span>
                    {isHiring
                      ? "Appointing…"
                      : !meetsPrestige && !usePremium
                      ? "Prestige Too Low"
                      : "Appoint to Role"}
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* Staff AI Chat Modal */}
      {chatRole && (
        <StaffChatModal
          clubId={club.club_id}
          initialRole={chatRole}
          appointedStaff={appointed}
          onClose={() => setChatRole(null)}
        />
      )}
    </section>
  );
}

export default function Squad() {
  const location = useLocation();
  const navigate = useNavigate();
  const { active } = useActiveClub();
  const [selectedPlayer, setSelectedPlayer] = useState<any | null>(null);

  const journeyParams = useMemo(() => readJourneyParams(location.search), [location.search]);
  const targetPlayerId = journeyParams.player;

  const {
    data: club,
    isLoading,
    isError,
    refetch,
  } = useClub(active?.club_id);

  const clearTarget = () => {
    const searchParams = new URLSearchParams(location.search);
    searchParams.delete("player");
    const nextSearch = searchParams.toString();
    navigate({ search: nextSearch ? `?${nextSearch}` : "" }, { replace: true });
  };

  if (!active?.club_id) {
    return (
      <div data-testid="squad-no-club" className="space-y-6">
        <PageHeader
          eyebrow="Owner workspace"
          title="Choose a club to manage a squad"
          sub="Your GTEX member account is ready. Squad and manager tools become available when you create, join, or take over a club."
        />
        <Panel eyebrow="Club ownership is optional" title="Start with the club that is right for you">
          <p className="text-sm leading-6 text-slate-300">
            You can explore GTEX and manage eligible national-team activities without
            owning a club. To open the squad roster, first choose a club for your
            owner workspace.
          </p>
          <Link
            to="/app/clubs"
            data-testid="squad-choose-club-link"
            className="gx-btn gx-btn-primary mt-4 inline-flex"
          >
            Create or choose a club
          </Link>
        </Panel>
      </div>
    );
  }

  if (isLoading) return <Loading label="Loading your squad..." />;

  if (isError || !club) {
    return (
      <div data-testid="squad-unavailable" className="space-y-6">
        <PageHeader
          eyebrow="Owner workspace"
          title="Squad temporarily unavailable"
          sub="GTEX could not load this club's squad. Your club data has not been changed."
        />
        <Panel eyebrow="Connection status" title="Unable to load squad details">
          <p className="text-sm leading-6 text-slate-300">
            Retry the request. If the problem continues, return to My Clubs and
            select the club again.
          </p>
          <Btn variant="secondary" className="mt-4" onClick={() => void refetch()}>
            Retry squad
          </Btn>
          <Link
            to="/app/clubs"
            className="gx-btn gx-btn-ghost ml-2 mt-4 inline-flex"
          >
            Open My Clubs
          </Link>
        </Panel>
      </div>
    );
  }

  return (
    <div data-testid="squad-page">
      <PageHeader
        eyebrow="Manager & squad"
        title="Squad room"
        sub={club.club_name + " · " + club.squad.length + " registered players · Wage bill " + fmt(club.wage_bill) + " GTX / match"}
        action={
          <Link
            to={"/app/lineup?club_id=" + encodeURIComponent(club.club_id)}
            data-testid="open-lineup-tactics-button"
            className="gx-btn gx-btn-primary inline-flex items-center"
          >
            Open Lineup & Tactics <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        }
      />

      {targetPlayerId && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-cyan-500/40 bg-cyan-950/60 p-3 text-xs text-cyan-200">
          <span>
            Tracking journey target prospect: <b className="font-mono text-white">{targetPlayerId}</b>
          </span>
          <button
            type="button"
            onClick={clearTarget}
            className="rounded p-0.5 hover:bg-white/10 text-slate-300 hover:text-white"
            title="Clear target filter"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* 1. Competition Roster Registration */}
      <SquadRegistrationPanel club={club} targetPlayerId={targetPlayerId} />

      {/* 2. Executive & Staff Boardroom */}
      <BoardroomSection club={club} />

      {/* 3. Pitch Operations & Squad Roster */}
      <div className="grid gap-6 lg:grid-cols-12 mt-6">
        <ManagerSheet club={club} />
        <SquadTable club={club} targetPlayerId={targetPlayerId} onSelectPlayer={setSelectedPlayer} />
        <HireManager club={club} />
      </div>

      {/* 4. Universal Player Dossier Drawer */}
      <PlayerDrawer
        playerId={selectedPlayer ? String(selectedPlayer.player_ref || selectedPlayer.player_id || selectedPlayer.id) : null}
        onClose={() => setSelectedPlayer(null)}
      />
    </div>
  );
}

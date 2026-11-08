/**
 * GTEX Living Football Ecosystem — Stage 2 Persistent 3D Club Interactions
 * PersonaSpatialInteractionModal: Real-time bilateral persona dialogue & HUD.
 *
 * Surfaced when raycasting / clicking 3D personas (Boardroom, Tactician Suite, Campus HQ).
 * Renders the 7 canonical relationship dimensions:
 *   alignment, influence, loyalty, trust, respect, affinity, tension
 * Dispatches mutations to /owner/clubs/{club_id}/living-world/personas/{role}/interact
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  X,
  Sparkles,
  Shield,
  Activity,
  Heart,
  Flame,
  Award,
  Zap,
  CheckCircle2,
  Send,
  MessageSquare,
  Clock,
  Compass,
  Sliders,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import {
  clubPersonaDetailsEndpoint,
  clubPersonaInteractEndpoint,
  type PersonaDetailsResponse,
  type PersonaInteractionActionType,
  type PersonaInteractionResponse,
} from "@/lib/ownerBriefing";

export interface PersonaSpatialInteractionModalProps {
  clubId: string;
  personaRole: string | null;
  isOpen: boolean;
  onClose: () => void;
  onInteractionComplete?: (response: PersonaInteractionResponse) => void;
  onOpenGmDelegation?: () => void;
}

const ACTION_BUTTONS: Array<{
  key: PersonaInteractionActionType;
  label: string;
  description: string;
  deltaPreview: string;
  badgeColor: string;
}> = [
  {
    key: "align_strategy",
    label: "Align Strategic Vision",
    description: "Convene strategic summit to harmonize philosophy & transfer priorities.",
    deltaPreview: "+6 Alignment, +3 Influence, -3 Tension",
    badgeColor: "border-emerald-500/30 text-emerald-300 bg-emerald-500/10",
  },
  {
    key: "praise_leadership",
    label: "Praise Leadership",
    description: "Formally commend executive stewardship and departmental performance.",
    deltaPreview: "+5 Trust, +6 Loyalty, -5 Tension",
    badgeColor: "border-sky-500/30 text-sky-300 bg-sky-500/10",
  },
  {
    key: "demand_accountability",
    label: "Demand Accountability",
    description: "Challenge recent lapses and demand immediate performance benchmarks.",
    deltaPreview: "+7 Tension, +4 Influence, -3 Loyalty",
    badgeColor: "border-rose-500/30 text-rose-300 bg-rose-500/10",
  },
  {
    key: "request_briefing",
    label: "Request Briefing",
    description: "Ask for immediate situational assessment and tactical readiness notes.",
    deltaPreview: "+4 Respect, +3 Trust, +3 Alignment",
    badgeColor: "border-amber-500/30 text-amber-300 bg-amber-500/10",
  },
];

export const PersonaSpatialInteractionModal: React.FC<PersonaSpatialInteractionModalProps> = ({
  clubId,
  personaRole,
  isOpen,
  onClose,
  onInteractionComplete,
  onOpenGmDelegation,
}) => {
  const queryClient = useQueryClient();
  const [customDialogue, setCustomDialogue] = useState<string>("");
  const [lastReply, setLastReply] = useState<string | null>(null);
  const [lastDelta, setLastDelta] = useState<PersonaInteractionResponse["delta_applied"] | null>(null);

  const {
    data: details,
    isLoading,
    refetch,
  } = useQuery<PersonaDetailsResponse | null>({
    queryKey: ["club-persona-details", clubId, personaRole],
    queryFn: async () => {
      if (!clubId || !personaRole) return null;
      const { data } = await api.get(clubPersonaDetailsEndpoint(clubId, personaRole));
      return data as PersonaDetailsResponse;
    },
    enabled: Boolean(clubId && personaRole && isOpen),
  });

  const interactMutation = useMutation({
    mutationFn: async ({
      actionType,
      text,
    }: {
      actionType: PersonaInteractionActionType;
      text?: string;
    }) => {
      if (!personaRole) throw new Error("No persona selected");
      const { data } = await api.post(clubPersonaInteractEndpoint(clubId, personaRole), {
        action_type: actionType,
        dialogue_text: text || undefined,
      });
      return data as PersonaInteractionResponse;
    },
    onSuccess: (res) => {
      setLastReply(res.dialogue_reply);
      setLastDelta(res.delta_applied);
      setCustomDialogue("");
      toast.success(`${res.persona.name}: Interaction Recorded`);
      refetch();
      queryClient.invalidateQueries({ queryKey: ["club-operations-hub", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-living-world-timeline", clubId] });
      onInteractionComplete?.(res);
    },
    onError: (err) => {
      toast.error(errMsg(err));
    },
  });

  if (!isOpen || !personaRole) return null;

  const persona = details?.persona;
  const rel = details?.relationship;

  return (
    <div
      data-testid="persona-spatial-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-emerald-500/30 bg-gradient-to-b from-[#091526] via-[#060e1c] to-[#03070f] text-slate-100 shadow-2xl shadow-emerald-950/40">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/30">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold tracking-tight text-white">
                  {persona?.name || personaRole.replace(/_/g, " ").toUpperCase()}
                </h3>
                <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400 ring-1 ring-emerald-500/25">
                  {persona?.role_label || "Executive"}
                </span>
              </div>
              <p className="text-xs text-slate-400 capitalize">
                {persona?.department || "Department"} Suite • Day {details?.world_day || 1}
              </p>
            </div>
          </div>
          <button
            type="button"
            data-testid="close-persona-modal-btn"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading && !details ? (
            <div className="flex h-40 items-center justify-center text-xs text-slate-400">
              Loading persona intelligence...
            </div>
          ) : (
            <>
              {/* Relationship Dimensions Grid (7 Metrics) */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Bilateral Relationship Spine
                  </span>
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[11px] font-medium text-emerald-300 ring-1 ring-emerald-500/30">
                    {rel?.status_label || "Active Relationship"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {/* Persistent Stage 1 Dimensions */}
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-emerald-400">Alignment</span>
                      <span className="font-mono font-bold text-white">{rel?.alignment ?? 65}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-emerald-400 transition-all duration-500"
                        style={{ width: `${rel?.alignment ?? 65}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-indigo-400">Influence</span>
                      <span className="font-mono font-bold text-white">{rel?.influence ?? 60}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-indigo-400 transition-all duration-500"
                        style={{ width: `${rel?.influence ?? 60}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-purple-400">Loyalty</span>
                      <span className="font-mono font-bold text-white">{rel?.loyalty ?? 60}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-purple-400 transition-all duration-500"
                        style={{ width: `${rel?.loyalty ?? 60}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-rose-400">Tension</span>
                      <span className="font-mono font-bold text-white">{rel?.tension ?? 10}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-rose-400 transition-all duration-500"
                        style={{ width: `${rel?.tension ?? 10}%` }}
                      />
                    </div>
                  </div>

                  {/* Core Dimensions */}
                  <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Trust</span>
                      <span className="font-mono font-bold text-white">{rel?.trust ?? 55}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-teal-400 transition-all duration-500"
                        style={{ width: `${rel?.trust ?? 55}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Respect</span>
                      <span className="font-mono font-bold text-white">{rel?.respect ?? 60}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-amber-400 transition-all duration-500"
                        style={{ width: `${rel?.respect ?? 60}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-white/5 bg-white/[0.02] p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Affinity</span>
                      <span className="font-mono font-bold text-white">{rel?.affinity ?? 50}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-sky-400 transition-all duration-500"
                        style={{ width: `${rel?.affinity ?? 50}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Live Persona Speech Bubble Feedback */}
              {lastReply && (
                <div
                  data-testid="persona-reply-bubble"
                  className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 transition-all"
                >
                  <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
                    <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                      <MessageSquare className="h-3.5 w-3.5" />
                      {persona?.name} (Response)
                    </span>
                    {lastDelta && (
                      <span className="text-[10px] font-mono text-emerald-300">
                        {Object.entries(lastDelta)
                          .filter(([, v]) => v !== 0)
                          .map(([k, v]) => `${v > 0 ? "+" : ""}${v} ${k}`)
                          .join(" • ")}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-xs italic text-slate-200">"{lastReply}"</p>
                </div>
              )}

              {/* GM Delegation & Authority Banner (when interacting with General Manager) */}
              {personaRole === "general_manager" && onOpenGmDelegation && (
                <div className="flex items-center justify-between rounded-xl border border-sky-500/30 bg-sky-500/10 p-3">
                  <div>
                    <span className="text-xs font-bold text-sky-300">
                      General Manager Delegation Policy
                    </span>
                    <p className="text-[11px] text-slate-400">
                      Configure authority matrix, financial limits, and review escalated proposals.
                    </p>
                  </div>
                  <button
                    type="button"
                    data-testid="open-gm-delegation-from-persona-btn"
                    onClick={() => {
                      onClose();
                      onOpenGmDelegation();
                    }}
                    className="flex items-center gap-1.5 rounded-lg border border-sky-500/40 bg-sky-500/20 px-3 py-1.5 text-xs font-bold text-sky-300 transition-all hover:bg-sky-500/30 shadow-md shadow-sky-500/10"
                  >
                    <Sliders className="h-3.5 w-3.5" />
                    <span>Authority Matrix</span>
                  </button>
                </div>
              )}

              {/* Bilateral Action Triggers */}
              <div>
                <span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Execute Executive Interaction
                </span>
                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  {ACTION_BUTTONS.map((btn) => (
                    <button
                      key={btn.key}
                      type="button"
                      data-testid={`action-btn-${btn.key}`}
                      disabled={interactMutation.isPending}
                      onClick={() => interactMutation.mutate({ actionType: btn.key, text: customDialogue })}
                      className="flex flex-col items-start rounded-xl border border-white/10 bg-white/[0.02] p-3 text-left transition-all hover:border-emerald-500/40 hover:bg-emerald-500/5 disabled:opacity-50"
                    >
                      <div className="flex w-full items-center justify-between">
                        <span className="text-xs font-bold text-white">{btn.label}</span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ring-1 ring-inset ${btn.badgeColor}`}
                        >
                          {btn.deltaPreview}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-slate-400">{btn.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Speech Dialogue Dispatch */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <span className="mb-1.5 block text-[11px] font-bold uppercase text-slate-400">
                  Custom Strategic Message
                </span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customDialogue}
                    onChange={(e) => setCustomDialogue(e.target.value)}
                    placeholder={`Direct message to ${persona?.name || "staff"}...`}
                    className="flex-1 rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    disabled={!customDialogue.trim() || interactMutation.isPending}
                    onClick={() =>
                      interactMutation.mutate({
                        actionType: "general_dialogue",
                        text: customDialogue,
                      })
                    }
                    className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-40"
                  >
                    <Send className="h-3.5 w-3.5" />
                    <span>Speak</span>
                  </button>
                </div>
              </div>

              {/* Active Departmental Directives */}
              {details?.active_directives && details.active_directives.length > 0 && (
                <div>
                  <span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-400">
                    Active Directives in Department ({details.active_directives.length})
                  </span>
                  <div className="space-y-2">
                    {details.active_directives.map((dir) => (
                      <div
                        key={dir.id}
                        className="flex items-center justify-between rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs"
                      >
                        <div>
                          <p className="font-semibold text-white">{dir.title}</p>
                          <p className="text-[11px] text-slate-400">{dir.instruction}</p>
                        </div>
                        <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono text-amber-300">
                          Due Day {dir.deadline_day}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

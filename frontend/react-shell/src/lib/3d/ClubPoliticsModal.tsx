import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, errMsg } from "@/lib/api";
import {
  ClubPoliticsOverviewResponse,
  PoliticalCycleEvaluateResponse,
  PoliticalEventRespondPayload,
  PoliticalEventRespondResponse,
  MediaStatementPayload,
  MediaStatementResponse,
  clubPoliticsOverviewEndpoint,
  clubPoliticsEvaluateCycleEndpoint,
  clubPoliticsEventRespondEndpoint,
  clubPoliticsMediaStatementEndpoint,
} from "@/lib/ownerBriefing";

export interface ClubPoliticsModalProps {
  clubId: string;
  isOpen: boolean;
  onClose: () => void;
  initialTab?: "board" | "squad" | "events" | "media" | "supporters";
}

const STATEMENT_OPTIONS = [
  {
    key: "vote_of_confidence",
    label: "Public Vote of Confidence",
    desc: "Reaffirm full boardroom backing for First-Team Manager Emmanuel Amuneke.",
    impact: "+7 Manager Trust, -5 Tension, +3 Board Confidence",
  },
  {
    key: "demand_performance",
    label: "Demand Immediate Pitch Standards",
    desc: "Issue a stern public warning that current performances must improve immediately.",
    impact: "+4 Supporter Confidence, -6 Manager Trust, +10 Manager Tension",
  },
  {
    key: "praise_youth_academy",
    label: "Champion Youth Academy Pathway",
    desc: "Highlight Kunle Adeyemi's academy graduates as the cornerstone of the club's identity.",
    impact: "+8 HOYD Trust, +6 Supporter Confidence, +0.05x Matchday Atmosphere",
  },
];

export const ClubPoliticsModal: React.FC<ClubPoliticsModalProps> = ({
  clubId,
  isOpen,
  onClose,
  initialTab = "board",
}) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"board" | "squad" | "events" | "media" | "supporters">(
    initialTab
  );
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [eventNotes, setEventNotes] = useState<Record<string, string>>({});
  const [selectedStatementType, setSelectedStatementType] = useState<string>("vote_of_confidence");
  const [customQuote, setCustomQuote] = useState<string>("");

  const {
    data: overview,
    isLoading,
    error,
  } = useQuery<ClubPoliticsOverviewResponse>({
    queryKey: ["clubPoliticsOverview", clubId],
    queryFn: async () => {
      const res = await api.get<ClubPoliticsOverviewResponse>(
        clubPoliticsOverviewEndpoint(clubId)
      );
      return ((res as any)?.data ?? res) as ClubPoliticsOverviewResponse;
    },
    enabled: isOpen && Boolean(clubId),
  });

  const invalidatePolitics = () => {
    queryClient.invalidateQueries({ queryKey: ["clubPoliticsOverview", clubId] });
    queryClient.invalidateQueries({ queryKey: ["ownerClubEvents", clubId] });
    queryClient.invalidateQueries({ queryKey: ["ownerClubRelationships", clubId] });
  };

  const evaluateCycleMutation = useMutation<PoliticalCycleEvaluateResponse, unknown, void>({
    mutationFn: async () => {
      const res = await api.post<PoliticalCycleEvaluateResponse>(
        clubPoliticsEvaluateCycleEndpoint(clubId),
        {}
      );
      return ((res as any)?.data ?? res) as PoliticalCycleEvaluateResponse;
    },
    onSuccess: (res) => {
      invalidatePolitics();
      setStatusMessage({
        type: "success",
        text: `Political cycle evaluated (Day ${res.world_day}): ${res.events_evaluated} new dilemma(s) surfaced.`,
      });
      if (res.events_evaluated > 0) {
        setActiveTab("events");
      }
    },
    onError: (err) => {
      setStatusMessage({
        type: "error",
        text: errMsg(err),
      });
    },
  });

  const respondEventMutation = useMutation<
    PoliticalEventRespondResponse,
    unknown,
    { eventId: string; payload: PoliticalEventRespondPayload }
  >({
    mutationFn: async ({ eventId, payload }) => {
      const res = await api.post<PoliticalEventRespondResponse>(
        clubPoliticsEventRespondEndpoint(clubId, eventId),
        payload
      );
      return ((res as any)?.data ?? res) as PoliticalEventRespondResponse;
    },
    onSuccess: (res) => {
      invalidatePolitics();
      setStatusMessage({
        type: "success",
        text: res.outcome_summary || "Political dilemma resolved.",
      });
    },
    onError: (err) => {
      setStatusMessage({
        type: "error",
        text: errMsg(err),
      });
    },
  });

  const mediaStatementMutation = useMutation<
    MediaStatementResponse,
    unknown,
    MediaStatementPayload
  >({
    mutationFn: async (payload) => {
      const res = await api.post<MediaStatementResponse>(
        clubPoliticsMediaStatementEndpoint(clubId),
        payload
      );
      return ((res as any)?.data ?? res) as MediaStatementResponse;
    },
    onSuccess: (res) => {
      invalidatePolitics();
      setCustomQuote("");
      setStatusMessage({
        type: "success",
        text: res.outcome_text || "Public communiqué dispatched to the press.",
      });
    },
    onError: (err) => {
      setStatusMessage({
        type: "error",
        text: errMsg(err),
      });
    },
  });

  if (!isOpen) return null;

  const board = overview?.board_politics;
  const dressing = overview?.dressing_room;
  const medical = overview?.medical_department;
  const youth = overview?.youth_development;
  const supporters = overview?.supporter_sentiment;
  const media = overview?.media_and_rumours;
  const activeEvents = overview?.active_political_events || [];

  return (
    <div
      data-testid="club-politics-modal"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9600,
        backgroundColor: "rgba(2, 6, 23, 0.84)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        color: "#F8FAFC",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "1060px",
          maxHeight: "90vh",
          backgroundColor: "#0F172A",
          border: "1px solid rgba(139, 92, 246, 0.35)",
          borderRadius: "16px",
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.85)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid rgba(148, 163, 184, 0.15)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background:
              "linear-gradient(90deg, rgba(139, 92, 246, 0.16) 0%, rgba(15, 23, 42, 0.95) 100%)",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span
                style={{
                  backgroundColor: "rgba(139, 92, 246, 0.22)",
                  color: "#C4B5FD",
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "3px 8px",
                  borderRadius: "999px",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Living Football World • Stage 6
              </span>
              {overview && (
                <span style={{ color: "#94A3B8", fontSize: "12px" }}>
                  World Day {overview.world_day} • Media Profile:{" "}
                  <strong style={{ color: "#E2E8F0" }}>{media?.media_profile}</strong>
                </span>
              )}
            </div>
            <h2 style={{ margin: "6px 0 0", fontSize: "20px", fontWeight: 700 }}>
              Club Governance, Internal Politics & Consequences
            </h2>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <button
              data-testid="run-politics-cycle-btn"
              onClick={() => evaluateCycleMutation.mutate()}
              disabled={evaluateCycleMutation.isPending}
              style={{
                backgroundColor: "#8B5CF6",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "8px",
                padding: "9px 14px",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {evaluateCycleMutation.isPending ? "Evaluating..." : "Run Politics Cycle"}
            </button>
            <button
              data-testid="close-club-politics-modal-btn"
              onClick={onClose}
              style={{
                backgroundColor: "rgba(255, 255, 255, 0.08)",
                color: "#E2E8F0",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "8px",
                padding: "8px 14px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div
          style={{
            display: "flex",
            gap: "6px",
            padding: "12px 24px",
            borderBottom: "1px solid rgba(148, 163, 184, 0.12)",
            backgroundColor: "rgba(2, 6, 23, 0.45)",
            flexWrap: "wrap",
          }}
        >
          {[
            { id: "board", label: "Boardroom & Governance" },
            { id: "squad", label: "Dressing Room & Medical" },
            {
              id: "events",
              label: `Active Dilemmas (${activeEvents.length})`,
            },
            { id: "media", label: "Media & Press Room" },
            { id: "supporters", label: "Supporters & Community" },
          ].map((tab) => (
            <button
              key={tab.id}
              data-testid={`politics-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: "8px 14px",
                borderRadius: "8px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                border:
                  activeTab === tab.id
                    ? "1px solid #8B5CF6"
                    : "1px solid transparent",
                backgroundColor:
                  activeTab === tab.id
                    ? "rgba(139, 92, 246, 0.2)"
                    : "transparent",
                color: activeTab === tab.id ? "#DDD6FE" : "#94A3B8",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Status Banner */}
        {statusMessage && (
          <div
            data-testid="club-politics-status-banner"
            style={{
              margin: "12px 24px 0",
              padding: "10px 14px",
              borderRadius: "8px",
              fontSize: "13px",
              backgroundColor:
                statusMessage.type === "success"
                  ? "rgba(16, 185, 129, 0.15)"
                  : "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${
                statusMessage.type === "success" ? "#10B981" : "#EF4444"
              }`,
              color: statusMessage.type === "success" ? "#6EE7B7" : "#FCA5A5",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>{statusMessage.text}</span>
            <button
              onClick={() => setStatusMessage(null)}
              style={{
                background: "none",
                border: "none",
                color: "inherit",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Body */}
        <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
          {isLoading && (
            <div style={{ padding: "40px", textAlign: "center", color: "#94A3B8" }}>
              Loading club governance and dressing room dynamics...
            </div>
          )}

          {error && (
            <div
              style={{
                padding: "20px",
                backgroundColor: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "8px",
                color: "#FCA5A5",
              }}
            >
              Failed to load club politics overview: {errMsg(error)}
            </div>
          )}

          {overview && activeTab === "board" && board && (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Summary Bar */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                <div
                  style={{
                    padding: "16px",
                    backgroundColor: "rgba(30, 41, 59, 0.7)",
                    borderRadius: "12px",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                    Boardroom Confidence
                  </div>
                  <div
                    data-testid="board-confidence-value"
                    style={{
                      fontSize: "24px",
                      fontWeight: 800,
                      color: board.board_confidence >= 70 ? "#34D399" : "#FBBF24",
                      marginTop: "4px",
                    }}
                  >
                    {board.board_confidence}%
                  </div>
                </div>

                <div
                  style={{
                    padding: "16px",
                    backgroundColor: "rgba(30, 41, 59, 0.7)",
                    borderRadius: "12px",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                    Investor Sentiment
                  </div>
                  <div
                    data-testid="investor-sentiment-value"
                    style={{
                      fontSize: "24px",
                      fontWeight: 800,
                      color: "#38BDF8",
                      marginTop: "4px",
                    }}
                  >
                    {board.investor_sentiment}%
                  </div>
                </div>

                <div
                  style={{
                    padding: "16px",
                    backgroundColor: "rgba(30, 41, 59, 0.7)",
                    borderRadius: "12px",
                    border: "1px solid rgba(148, 163, 184, 0.15)",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                    Boardroom Mood
                  </div>
                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: 700,
                      color: "#C4B5FD",
                      marginTop: "6px",
                      textTransform: "capitalize",
                    }}
                  >
                    {board.board_mood}
                  </div>
                </div>
              </div>

              {/* Board Directors */}
              <div>
                <h3 style={{ margin: "0 0 12px", fontSize: "15px", fontWeight: 700 }}>
                  Board of Directors & Voting Blocks
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))",
                    gap: "12px",
                  }}
                >
                  {board.directors.map((dir) => (
                    <div
                      key={dir.id}
                      data-testid={`director-card-${dir.id}`}
                      style={{
                        padding: "16px",
                        borderRadius: "12px",
                        backgroundColor: "rgba(30, 41, 59, 0.55)",
                        border: "1px solid rgba(148, 163, 184, 0.18)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 700, fontSize: "15px" }}>
                            {dir.name}
                          </div>
                          <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                            {dir.role_title} • Archetype:{" "}
                            <span style={{ color: "#E2E8F0", textTransform: "capitalize" }}>
                              {dir.archetype}
                            </span>
                          </div>
                        </div>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "999px",
                            backgroundColor:
                              dir.stance === "satisfied"
                                ? "rgba(16, 185, 129, 0.2)"
                                : "rgba(245, 158, 11, 0.2)",
                            color: dir.stance === "satisfied" ? "#6EE7B7" : "#FCD34D",
                            textTransform: "uppercase",
                          }}
                        >
                          {dir.stance} ({dir.confidence_score}%)
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: "13px", color: "#CBD5E1" }}>
                        {dir.bio}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: "12px",
                          color: "#94A3B8",
                          borderTop: "1px solid rgba(148, 163, 184, 0.1)",
                          paddingTop: "8px",
                        }}
                      >
                        <span>Primary Focus: {dir.primary_focus}</span>
                        <span>Influence Weight: {dir.influence_weight}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {overview && activeTab === "squad" && dressing && (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Squad & Leadership Summary */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                <div
                  style={{
                    padding: "14px",
                    backgroundColor: "rgba(30, 41, 59, 0.65)",
                    borderRadius: "10px",
                    border: "1px solid rgba(148, 163, 184, 0.14)",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                    Average Squad Morale
                  </div>
                  <div
                    data-testid="squad-avg-morale"
                    style={{ fontSize: "22px", fontWeight: 800, color: "#34D399" }}
                  >
                    {dressing.average_morale}/100
                  </div>
                </div>

                {dressing.leadership_group && (
                  <div
                    style={{
                      padding: "14px",
                      backgroundColor: "rgba(30, 41, 59, 0.65)",
                      borderRadius: "10px",
                      border: "1px solid rgba(148, 163, 184, 0.14)",
                    }}
                  >
                    <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                      Club Captain & Intermediary
                    </div>
                    <div style={{ fontSize: "15px", fontWeight: 700, marginTop: "2px" }}>
                      {dressing.leadership_group.captain_name}
                    </div>
                    <div style={{ fontSize: "12px", color: "#38BDF8" }}>
                      Vice: {dressing.leadership_group.vice_captain_name} • Trust:{" "}
                      {dressing.leadership_group.owner_trust}%
                    </div>
                  </div>
                )}

                {medical && (
                  <div
                    style={{
                      padding: "14px",
                      backgroundColor: "rgba(30, 41, 59, 0.65)",
                      borderRadius: "10px",
                      border: "1px solid rgba(148, 163, 184, 0.14)",
                    }}
                  >
                    <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                      Medical Director ({medical.director.name})
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 700, marginTop: "2px" }}>
                      {medical.injured_players.length} Injured Player(s) • Protocol Lv.{" "}
                      {medical.recovery_protocol}
                    </div>
                  </div>
                )}

                {youth && (
                  <div
                    style={{
                      padding: "14px",
                      backgroundColor: "rgba(30, 41, 59, 0.65)",
                      borderRadius: "10px",
                      border: "1px solid rgba(148, 163, 184, 0.14)",
                    }}
                  >
                    <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                      HOYD ({youth.hoyd.name})
                    </div>
                    <div style={{ fontSize: "14px", fontWeight: 700, marginTop: "2px" }}>
                      Academy Tier {youth.academy_tier} • {youth.prospects_monitored}{" "}
                      U-20 Prospect(s)
                    </div>
                  </div>
                )}
              </div>

              {/* Squad Factions */}
              {dressing.factions && (
                <div>
                  <h4 style={{ margin: "0 0 10px", fontSize: "14px", fontWeight: 700 }}>
                    Dressing Room Factions
                  </h4>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                      gap: "10px",
                    }}
                  >
                    {Object.entries(dressing.factions).map(([key, fac]) => (
                      <div
                        key={key}
                        data-testid={`squad-faction-${key}`}
                        style={{
                          padding: "12px",
                          borderRadius: "10px",
                          backgroundColor: "rgba(15, 23, 42, 0.6)",
                          border: "1px solid rgba(148, 163, 184, 0.15)",
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: "14px" }}>
                          {fac.label}
                        </div>
                        <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "4px" }}>
                          Cohesion: {fac.cohesion}% • Sentiment:{" "}
                          <strong style={{ color: "#E2E8F0", textTransform: "capitalize" }}>
                            {fac.sentiment}
                          </strong>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Unhappy Players */}
              <div>
                <h4 style={{ margin: "0 0 10px", fontSize: "14px", fontWeight: 700 }}>
                  Dressing Room Grievances ({dressing.unhappy_players.length})
                </h4>
                {dressing.unhappy_players.length === 0 ? (
                  <div style={{ color: "#94A3B8", fontSize: "13px" }}>
                    No squad grievances reported. Dressing room morale is harmonious.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {dressing.unhappy_players.map((p) => (
                      <div
                        key={p.id}
                        data-testid={`unhappy-player-${p.id}`}
                        style={{
                          padding: "12px 14px",
                          borderRadius: "10px",
                          backgroundColor: "rgba(239, 68, 68, 0.1)",
                          border: "1px solid rgba(239, 68, 68, 0.28)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div>
                          <span style={{ fontWeight: 700 }}>{p.name}</span>{" "}
                          <span style={{ fontSize: "12px", color: "#94A3B8" }}>
                            ({p.position} • OVR {p.rating})
                          </span>
                          <div style={{ fontSize: "12px", color: "#FCA5A5" }}>
                            Grievance: {p.issue}
                          </div>
                        </div>
                        <div
                          style={{
                            fontSize: "13px",
                            fontWeight: 700,
                            color: "#F87171",
                          }}
                        >
                          Morale: {p.morale}/100
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {overview && activeTab === "events" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {activeEvents.length === 0 ? (
                <div
                  style={{
                    padding: "36px",
                    textAlign: "center",
                    backgroundColor: "rgba(30, 41, 59, 0.4)",
                    borderRadius: "12px",
                    color: "#94A3B8",
                  }}
                >
                  No unresolved political or medical dilemmas. Click{" "}
                  <strong>Run Politics Cycle</strong> to evaluate current squad and
                  department tensions.
                </div>
              ) : (
                activeEvents.map((ev) => (
                  <div
                    key={ev.id}
                    data-testid={`political-event-card-${ev.id}`}
                    style={{
                      padding: "18px",
                      borderRadius: "12px",
                      backgroundColor: "rgba(30, 41, 59, 0.65)",
                      border: "1px solid rgba(139, 92, 246, 0.35)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "12px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "3px 8px",
                          borderRadius: "999px",
                          backgroundColor: "rgba(245, 158, 11, 0.2)",
                          color: "#FCD34D",
                          textTransform: "uppercase",
                        }}
                      >
                        {ev.category} • {ev.severity}
                      </span>
                      <span style={{ fontSize: "12px", color: "#94A3B8" }}>
                        World Day {ev.world_day}
                      </span>
                    </div>

                    <div>
                      <div style={{ fontSize: "16px", fontWeight: 700 }}>
                        {ev.title}
                      </div>
                      <p
                        style={{
                          margin: "6px 0 0",
                          fontSize: "13px",
                          color: "#CBD5E1",
                          lineHeight: 1.5,
                        }}
                      >
                        {ev.description}
                      </p>
                    </div>

                    <input
                      data-testid={`event-note-input-${ev.id}`}
                      type="text"
                      placeholder="Optional owner directive note for club audit trail..."
                      value={eventNotes[ev.id] || ""}
                      onChange={(e) =>
                        setEventNotes((prev) => ({
                          ...prev,
                          [ev.id]: e.target.value,
                        }))
                      }
                      style={{
                        backgroundColor: "#0F172A",
                        border: "1px solid rgba(148, 163, 184, 0.25)",
                        borderRadius: "8px",
                        padding: "8px 12px",
                        color: "#F8FAFC",
                        fontSize: "13px",
                      }}
                    />

                    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                      {(ev.actions || []).map((act) => (
                        <button
                          key={act.action_id}
                          data-testid={`respond-event-${ev.id}-${act.action_id}-btn`}
                          disabled={respondEventMutation.isPending}
                          onClick={() =>
                            respondEventMutation.mutate({
                              eventId: ev.id,
                              payload: {
                                action_id: act.action_id,
                                decision_note: eventNotes[ev.id] || undefined,
                              },
                            })
                          }
                          style={{
                            flex: "1 1 240px",
                            textAlign: "left",
                            padding: "12px",
                            borderRadius: "10px",
                            backgroundColor: "rgba(139, 92, 246, 0.16)",
                            border: "1px solid rgba(139, 92, 246, 0.4)",
                            color: "#F8FAFC",
                            cursor: "pointer",
                          }}
                        >
                          <div style={{ fontWeight: 700, fontSize: "13px" }}>
                            {act.label}
                          </div>
                          {act.description && (
                            <div
                              style={{
                                fontSize: "12px",
                                color: "#CBD5E1",
                                marginTop: "3px",
                              }}
                            >
                              {act.description}
                            </div>
                          )}
                          {act.delta_summary && (
                            <div
                              style={{
                                fontSize: "11px",
                                color: "#C4B5FD",
                                marginTop: "6px",
                                fontWeight: 600,
                              }}
                            >
                              Consequences: {act.delta_summary}
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {overview && activeTab === "media" && media && (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Dispatch Statement Card */}
              <div
                style={{
                  padding: "18px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(30, 41, 59, 0.6)",
                  border: "1px solid rgba(148, 163, 184, 0.18)",
                }}
              >
                <h3 style={{ margin: "0 0 12px", fontSize: "15px", fontWeight: 700 }}>
                  Issue Official Owner Communiqué
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                    gap: "10px",
                    marginBottom: "14px",
                  }}
                >
                  {STATEMENT_OPTIONS.map((opt) => (
                    <div
                      key={opt.key}
                      data-testid={`media-statement-type-${opt.key}`}
                      onClick={() => setSelectedStatementType(opt.key)}
                      style={{
                        padding: "12px",
                        borderRadius: "10px",
                        cursor: "pointer",
                        border:
                          selectedStatementType === opt.key
                            ? "2px solid #8B5CF6"
                            : "1px solid rgba(148, 163, 184, 0.2)",
                        backgroundColor:
                          selectedStatementType === opt.key
                            ? "rgba(139, 92, 246, 0.18)"
                            : "rgba(15, 23, 42, 0.6)",
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: "13px" }}>
                        {opt.label}
                      </div>
                      <div
                        style={{
                          fontSize: "12px",
                          color: "#94A3B8",
                          marginTop: "4px",
                        }}
                      >
                        {opt.desc}
                      </div>
                      <div
                        style={{
                          fontSize: "11px",
                          color: "#A78BFA",
                          marginTop: "6px",
                          fontWeight: 600,
                        }}
                      >
                        {opt.impact}
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <input
                    data-testid="media-custom-text-input"
                    type="text"
                    placeholder="Optional custom quote for press release..."
                    value={customQuote}
                    onChange={(e) => setCustomQuote(e.target.value)}
                    style={{
                      flex: 1,
                      backgroundColor: "#0F172A",
                      border: "1px solid rgba(148, 163, 184, 0.25)",
                      borderRadius: "8px",
                      padding: "10px 12px",
                      color: "#F8FAFC",
                      fontSize: "13px",
                    }}
                  />
                  <button
                    data-testid="dispatch-media-statement-btn"
                    disabled={mediaStatementMutation.isPending}
                    onClick={() =>
                      mediaStatementMutation.mutate({
                        statement_type: selectedStatementType,
                        custom_text: customQuote || undefined,
                      })
                    }
                    style={{
                      backgroundColor: "#10B981",
                      color: "#022C22",
                      border: "none",
                      borderRadius: "8px",
                      padding: "10px 18px",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {mediaStatementMutation.isPending
                      ? "Dispatching..."
                      : "Release Statement"}
                  </button>
                </div>
              </div>

              {/* Active Rumours & Press Feed */}
              <div>
                <h4 style={{ margin: "0 0 10px", fontSize: "14px", fontWeight: 700 }}>
                  Recent Headlines & Club Communiqués
                </h4>
                {media.active_rumours.length === 0 ? (
                  <div style={{ color: "#94A3B8", fontSize: "13px" }}>
                    No recent press statements or media flashpoints recorded.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {media.active_rumours.map((r) => (
                      <div
                        key={r.id}
                        data-testid={`media-rumour-item-${r.id}`}
                        style={{
                          padding: "12px 14px",
                          borderRadius: "10px",
                          backgroundColor: "rgba(30, 41, 59, 0.5)",
                          border: "1px solid rgba(148, 163, 184, 0.14)",
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: "14px" }}>
                          {r.headline}
                        </div>
                        <div
                          style={{
                            fontSize: "12px",
                            color: "#CBD5E1",
                            marginTop: "4px",
                            fontStyle: "italic",
                          }}
                        >
                          &ldquo;{r.quote}&rdquo;
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {overview && activeTab === "supporters" && supporters && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: "16px",
              }}
            >
              <div
                style={{
                  padding: "20px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(30, 41, 59, 0.65)",
                  border: "1px solid rgba(148, 163, 184, 0.16)",
                }}
              >
                <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                  Supporter Confidence Index
                </div>
                <div
                  data-testid="supporter-confidence-value"
                  style={{
                    fontSize: "28px",
                    fontWeight: 800,
                    color: "#34D399",
                    marginTop: "6px",
                  }}
                >
                  {supporters.confidence}%
                </div>
              </div>

              <div
                style={{
                  padding: "20px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(30, 41, 59, 0.65)",
                  border: "1px solid rgba(148, 163, 184, 0.16)",
                }}
              >
                <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                  Matchday Atmosphere Multiplier
                </div>
                <div
                  data-testid="atmosphere-multiplier-value"
                  style={{
                    fontSize: "28px",
                    fontWeight: 800,
                    color: "#FBBF24",
                    marginTop: "6px",
                  }}
                >
                  {supporters.atmosphere_multiplier}x
                </div>
              </div>

              <div
                style={{
                  padding: "20px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(30, 41, 59, 0.65)",
                  border: "1px solid rgba(148, 163, 184, 0.16)",
                }}
              >
                <div style={{ fontSize: "12px", color: "#94A3B8" }}>
                  Supporters Trust Climate
                </div>
                <div
                  style={{
                    fontSize: "22px",
                    fontWeight: 700,
                    color: "#38BDF8",
                    marginTop: "8px",
                  }}
                >
                  {supporters.fan_trust_rating}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

import React, { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { InboxItem } from "@/components/gtex/InboxItem";
import { Empty, Loading, PageHeader } from "@/components/gtex/ui";
import { api } from "@/lib/api";
import { useActiveClub, useClubCommunications, useRefreshOwner } from "@/lib/owner";
import {
  Inbox,
  Clock,
  Users,
  AlertTriangle,
  Search,
  Handshake,
  Calendar,
  Archive,
  CheckCheck,
  MessageSquare,
  Megaphone,
  Shield,
  Send,
  CheckCircle2,
  Sparkles,
  UserCheck,
  Compass,
} from "lucide-react";

const CATEGORIES = [
  { key: "all", label: "All Items", icon: Inbox },
  { key: "requests", label: "Requests", icon: Users },
  { key: "deadlines", label: "Deadlines", icon: Clock },
  { key: "staff_recommendations", label: "Staff", icon: Users },
  { key: "player_issues", label: "Player Matters", icon: AlertTriangle },
  { key: "scouting_reports", label: "Scouting", icon: Search },
  { key: "negotiations", label: "Negotiations", icon: Handshake },
  { key: "scheduling", label: "Scheduling", icon: Calendar },
  { key: "archive", label: "Archive", icon: Archive },
];

type CommsDestination =
  | "inbox"
  | "direct"
  | "staff_room"
  | "squad_room"
  | "meetings"
  | "decisions"
  | "announcements"
  | "archive";

export default function InboxPage() {
  const [searchParams] = useSearchParams();
  const initialStatus = searchParams.get("status") || "open";
  const initialCategory = searchParams.get("category") || "all";
  const queryClubId = searchParams.get("club_id");
  const initialUnreadOnly = searchParams.get("unread_only") === "true";
  const initialTab = (searchParams.get("tab") as CommsDestination) || "inbox";

  const [destination, setDestination] = useState<CommsDestination>(
    initialCategory === "archive" ? "archive" : initialTab
  );
  const [status, setStatus] = useState(initialStatus);
  const [selectedCategory, setSelectedCategory] = useState(initialCategory);
  const [unreadOnly, setUnreadOnly] = useState(initialUnreadOnly);

  const { clubs, active } = useActiveClub();
  const [selectedClubId, setSelectedClubId] = useState<string>(
    queryClubId || (active?.club_id ? active.club_id : "all")
  );
  const effectiveClubId = selectedClubId !== "all" ? selectedClubId : active?.club_id;
  const refresh = useRefreshOwner();

  // Direct conversations & rooms state
  const [activeThreadId, setActiveThreadId] = useState<string>("staff:first_team_manager");
  const [senderRole, setSenderRole] = useState<"owner" | "manager">("owner");
  const [draftMessage, setDraftMessage] = useState<string>("");
  const [roomDraft, setRoomDraft] = useState<string>("");
  const [busyAction, setBusyAction] = useState<boolean>(false);

  // Meeting composer state
  const [meetingTitle, setMeetingTitle] = useState<string>("");
  const [meetingType, setMeetingType] = useState<string>("boardroom");
  const [meetingAgenda, setMeetingAgenda] = useState<string>("");

  // Announcement composer state
  const [annTitle, setAnnTitle] = useState<string>("");
  const [annBody, setAnnBody] = useState<string>("");
  const [annAudience, setAnnAudience] = useState<string>("all_club");
  const [annToNewsroom, setAnnToNewsroom] = useState<boolean>(true);

  const isArchiveCategory = selectedCategory === "archive" || destination === "archive";
  const effectiveStatus = isArchiveCategory ? "archived" : status;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["inbox", effectiveStatus, selectedCategory, selectedClubId, unreadOnly],
    queryFn: async () => {
      const params: any = {
        status: effectiveStatus,
      };
      if (selectedClubId !== "all") {
        params.club_id = selectedClubId;
      }
      if (unreadOnly) {
        params.unread_only = true;
      }
      if (selectedCategory !== "all" && selectedCategory !== "archive") {
        params.category = selectedCategory;
      }
      const res = await api.get("/owner/inbox", { params });
      return res.data;
    },
  });

  const { data: commsData, refetch: refetchComms } = useClubCommunications(effectiveClubId);

  const items: any[] = data?.items || [];
  const counts = data?.counts || {};
  const commsCounts = commsData?.counts || {};
  const directThreads: any[] = commsData?.direct_threads || [];
  const staffContacts: any[] = commsData?.staff_contacts || [];
  const playerContacts: any[] = commsData?.player_contacts || [];
  const staffRoomFeed: any[] = commsData?.staff_room || [];
  const squadRoomFeed: any[] = commsData?.squad_room || [];
  const meetingsList: any[] = commsData?.meetings || [];
  const announcementsList: any[] = commsData?.announcements || [];
  const dilemma = commsData?.requests_decisions?.boardroom_dilemma || null;

  const currentThread =
    directThreads.find((t) => t.thread_id === activeThreadId) || directThreads[0] || null;

  const handleSendDirectMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveClubId || !draftMessage.trim() || busyAction) return;
    setBusyAction(true);
    try {
      const targetThreadId = currentThread?.thread_id || activeThreadId;
      const res = await api.post(`/owner/clubs/${effectiveClubId}/communications/messages`, {
        thread_id: targetThreadId,
        message: draftMessage.trim(),
        sender_role: senderRole,
        topic: "general",
      });
      setDraftMessage("");
      toast.success(`Reply received from ${res.data?.reply_message?.sender_name || "Contact"}`);
      refetchComms();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Failed to send message");
    } finally {
      setBusyAction(false);
    }
  };

  const handleSendRoomMessage = async (roomKey: "room:staff" | "room:squad") => {
    if (!effectiveClubId || !roomDraft.trim() || busyAction) return;
    setBusyAction(true);
    try {
      await api.post(`/owner/clubs/${effectiveClubId}/communications/messages`, {
        thread_id: roomKey,
        message: roomDraft.trim(),
        sender_role: senderRole,
      });
      setRoomDraft("");
      toast.success(
        roomKey === "room:squad"
          ? "Address delivered to Squad Room (+2 Squad Morale)!"
          : "Directive posted to Executive Staff Room!"
      );
      refetchComms();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Failed to post to room");
    } finally {
      setBusyAction(false);
    }
  };

  const handleConveneMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveClubId || !meetingTitle.trim() || busyAction) return;
    setBusyAction(true);
    try {
      await api.post(`/owner/clubs/${effectiveClubId}/communications/meetings`, {
        title: meetingTitle.trim(),
        meeting_type: meetingType,
        agenda: meetingAgenda.trim(),
        convene_now: true,
      });
      setMeetingTitle("");
      setMeetingAgenda("");
      toast.success("Club meeting convened and minutes ratified (+5 Manager Mood, +3 Squad Morale)!");
      refetchComms();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Failed to convene meeting");
    } finally {
      setBusyAction(false);
    }
  };

  const handlePublishAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveClubId || !annTitle.trim() || !annBody.trim() || busyAction) return;
    setBusyAction(true);
    try {
      const res = await api.post(`/owner/clubs/${effectiveClubId}/communications/announcements`, {
        title: annTitle.trim(),
        body: annBody.trim(),
        audience: annAudience,
        publish_to_newsroom: annToNewsroom,
      });
      setAnnTitle("");
      setAnnBody("");
      toast.success(
        res.data?.newsroom_article
          ? "Official communiqué published to Club & syndicated to GTEX Newsroom!"
          : "Official club announcement published!"
      );
      refetchComms();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Failed to publish announcement");
    } finally {
      setBusyAction(false);
    }
  };

  const handleResolveDilemma = async (choiceId: string) => {
    if (!effectiveClubId || busyAction) return;
    setBusyAction(true);
    try {
      const res = await api.post(`/owner/clubs/${effectiveClubId}/briefing/resolve-dilemma`, {
        choice_id: choiceId,
      });
      toast.success(res.data?.outcome || "Boardroom decision ratified!");
      refetchComms();
      refresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail?.detail || "Decision failed");
    } finally {
      setBusyAction(false);
    }
  };

  const DESTINATIONS: Array<{ id: CommsDestination; label: string; icon: any; badge?: number }> = [
    { id: "inbox", label: "1. Inbox", icon: Inbox, badge: counts.unread || commsCounts.inbox_unread },
    { id: "direct", label: "2. Direct Threads", icon: MessageSquare, badge: commsCounts.direct_unread },
    { id: "staff_room", label: "3. Staff Room", icon: Shield },
    { id: "squad_room", label: "4. Squad Room", icon: Users },
    { id: "meetings", label: "5. Meetings", icon: Calendar, badge: commsCounts.scheduled_meetings },
    { id: "decisions", label: "6. Requests & Decisions", icon: Handshake, badge: commsCounts.open_decisions },
    { id: "announcements", label: "7. Announcements", icon: Megaphone, badge: commsCounts.announcements },
    { id: "archive", label: "8. Archive", icon: Archive, badge: counts.archive || commsCounts.archived },
  ];

  return (
    <div data-testid="inbox-page" className="space-y-6">
      <PageHeader
        eyebrow="GTEX Unified Club Communications"
        title="Command, Threads & Decisions"
        sub="Persistent communication network connecting Club Owners, First-Team Managers, Executive Staff, and Squad Players with real permissions and actionable decisions."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/app/campus"
              className="px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center gap-1"
            >
              <Compass className="w-3.5 h-3.5" /> 3D Campus
            </Link>
            {/* Club Filter */}
            {clubs.length > 1 && (
              <select
                value={selectedClubId}
                onChange={(e) => setSelectedClubId(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-xs text-white rounded px-2.5 py-1.5 focus:outline-none focus:border-amber-400"
              >
                <option value="all">All Clubs</option>
                {clubs.map((c) => (
                  <option key={c.club_id} value={c.club_id}>
                    {c.club_name}
                  </option>
                ))}
              </select>
            )}

            <button
              type="button"
              data-testid="inbox-filter-unread"
              aria-pressed={unreadOnly}
              onClick={() => setUnreadOnly((current) => !current)}
              className={`flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-semibold border transition-colors ${
                unreadOnly
                  ? "bg-amber-500 text-slate-950 border-amber-400"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
              }`}
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Unread only
            </button>

            {/* Status Toggles (hidden in archive view) */}
            {!isArchiveCategory && (
              <div className="flex gap-1 bg-slate-900/60 p-1 rounded-lg border border-slate-800">
                {["open", "resolved", "all"].map((s) => (
                  <button
                    key={s}
                    data-testid={`inbox-filter-${s}`}
                    onClick={() => setStatus(s)}
                    className={`px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-colors ${
                      status === s
                        ? "bg-amber-500 text-slate-950 font-bold shadow"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        }
      />

      {/* 8-Destination Club Communications Navigation Bar */}
      <div className="flex flex-wrap gap-2 p-2 rounded-2xl bg-slate-950/90 border border-white/10">
        {DESTINATIONS.map((d) => {
          const Icon = d.icon;
          const isCurrent = destination === d.id;
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => {
                setDestination(d.id);
                if (d.id === "archive") {
                  setSelectedCategory("archive");
                } else if (selectedCategory === "archive") {
                  setSelectedCategory("all");
                }
              }}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition ${
                isCurrent
                  ? "bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/20"
                  : "bg-slate-900/80 text-slate-300 hover:bg-slate-800 border border-white/5"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{d.label}</span>
              {Boolean(d.badge && d.badge > 0) && (
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-black ${
                    isCurrent ? "bg-slate-950 text-emerald-300" : "bg-amber-500/20 text-amber-300"
                  }`}
                >
                  {d.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* DESTINATION 1 & 8: INBOX & ARCHIVE */}
      {(destination === "inbox" || destination === "archive") && (
        <>
          <div className="flex items-center space-x-1 border-b border-slate-800 pb-2 overflow-x-auto no-scrollbar">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isActive = selectedCategory === cat.key;
              return (
                <button
                  key={cat.key}
                  onClick={() => {
                    setSelectedCategory(cat.key);
                    if (cat.key === "archive") setDestination("archive");
                    else setDestination("inbox");
                  }}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? "bg-slate-800 text-amber-400 font-bold border border-amber-500/30"
                      : "text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{cat.label}</span>
                  {cat.key === "deadlines" && counts.deadlines > 0 && (
                    <span className="bg-red-500/20 text-red-400 text-[10px] px-1.5 rounded-full font-mono">
                      {counts.deadlines}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {isLoading ? (
            <Loading />
          ) : error ? (
            <div
              data-testid="inbox-error-state"
              className="p-6 rounded-xl bg-red-950/20 border border-red-500/30 text-red-300"
            >
              <p className="font-semibold">Unable to load owner inbox</p>
              <p className="text-xs text-red-400 mt-1">
                {(error as any)?.message || "Failed to reach GTEX owner services."}
              </p>
              <button
                onClick={() => refetch()}
                className="mt-3 px-3 py-1 bg-red-900/40 hover:bg-red-900/60 border border-red-700/50 rounded text-xs text-white"
              >
                Retry
              </button>
            </div>
          ) : items.length === 0 ? (
            <Empty
              title="No Messages"
              body={
                isArchiveCategory
                  ? "No archived messages found."
                  : "Advance the world day from the Control Center or review active matches to generate new correspondence."
              }
            />
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {items.map((i: any) => (
                <InboxItem key={i.id} item={i} />
              ))}
            </div>
          )}
        </>
      )}

      {/* DESTINATION 2: DIRECT CONVERSATIONS (Owner/Manager ↔ Staff & Squad Players) */}
      {destination === "direct" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Directory of Staff & Players */}
          <div className="lg:col-span-4 rounded-2xl border border-white/10 bg-slate-900/90 p-4 space-y-4 max-h-[640px] overflow-y-auto">
            <div>
              <div className="text-[11px] font-black uppercase tracking-wider text-emerald-400 mb-2">
                Executive & Coaching Staff
              </div>
              <div className="space-y-1.5">
                {staffContacts.map((sc) => {
                  const isSel = activeThreadId === sc.contact_id;
                  return (
                    <button
                      key={sc.contact_id}
                      type="button"
                      onClick={() => setActiveThreadId(sc.contact_id)}
                      className={`w-full p-2.5 rounded-xl border text-left flex items-center gap-3 transition ${
                        isSel
                          ? "border-emerald-400 bg-emerald-500/15"
                          : "border-white/5 bg-slate-950/70 hover:border-white/20"
                      }`}
                    >
                      <img
                        src={sc.portrait_url}
                        alt={sc.name}
                        className="w-10 h-10 rounded-full object-cover border border-white/15 shrink-0"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-bold text-white truncate">{sc.name}</div>
                        <div className="text-[11px] text-slate-400 truncate">{sc.title}</div>
                      </div>
                      <span className="text-[10px] font-bold text-emerald-300">{sc.mood}%</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-black uppercase tracking-wider text-amber-400 mb-2">
                Squad Players & Academy Regens ({playerContacts.length})
              </div>
              <div className="space-y-1.5">
                {playerContacts.map((pc) => {
                  const isSel = activeThreadId === pc.contact_id;
                  return (
                    <button
                      key={pc.contact_id}
                      type="button"
                      onClick={() => setActiveThreadId(pc.contact_id)}
                      className={`w-full p-2.5 rounded-xl border text-left flex items-center gap-3 transition ${
                        isSel
                          ? "border-amber-400 bg-amber-500/15"
                          : "border-white/5 bg-slate-950/70 hover:border-white/20"
                      }`}
                    >
                      <img
                        src={pc.portrait_url}
                        alt={pc.name}
                        className="w-10 h-10 rounded-full object-cover border border-white/15 shrink-0"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-bold text-white truncate">
                          {pc.name} {pc.is_regen ? "· ✨ Regen" : ""}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {pc.position} · OVR {pc.rating} · Morale {pc.morale}%
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Active Conversation Thread */}
          <div className="lg:col-span-8 rounded-2xl border border-white/10 bg-slate-900/95 flex flex-col h-[640px]">
            <div className="p-4 border-b border-white/10 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                {currentThread?.portrait_url && (
                  <img
                    src={currentThread.portrait_url}
                    alt=""
                    className="w-11 h-11 rounded-full object-cover border border-emerald-400/40"
                  />
                )}
                <div>
                  <div className="text-sm font-black text-white">
                    {currentThread?.participant_name || activeThreadId.replace("staff:", "").replace(/_/g, " ")}
                  </div>
                  <div className="text-xs text-slate-400">
                    {currentThread?.participant_role || "Direct Club Communication Line"}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">Speaking as:</span>
                <button
                  type="button"
                  onClick={() => setSenderRole("owner")}
                  className={`px-2.5 py-1 rounded-lg font-bold ${
                    senderRole === "owner" ? "bg-amber-400 text-slate-950" : "bg-white/5 text-slate-300"
                  }`}
                >
                  Club Owner
                </button>
                <button
                  type="button"
                  onClick={() => setSenderRole("manager")}
                  className={`px-2.5 py-1 rounded-lg font-bold ${
                    senderRole === "manager" ? "bg-emerald-400 text-slate-950" : "bg-white/5 text-slate-300"
                  }`}
                >
                  First-Team Manager
                </button>
              </div>
            </div>

            <div className="flex-1 p-4 space-y-3 overflow-y-auto">
              {(currentThread?.messages || []).length === 0 ? (
                <div className="text-center text-xs text-slate-400 py-12">
                  Start a direct conversation below. All messages persist to the club communication log and generate
                  grounded replies based on real club state.
                </div>
              ) : (
                (currentThread?.messages || []).map((m: any) => {
                  const isMe = m.sender_type === "owner" || m.sender_type === "manager";
                  return (
                    <div
                      key={m.id}
                      className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}
                    >
                      <div className="text-[10px] text-slate-400 mb-1 px-1">
                        {m.sender_name} · {m.sender_role} · Day {m.world_day || 1}
                      </div>
                      <div
                        className={`max-w-xl rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                          isMe
                            ? "bg-emerald-500 text-slate-950 font-semibold"
                            : "bg-slate-950 border border-white/10 text-slate-200"
                        }`}
                      >
                        {m.body}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <form onSubmit={handleSendDirectMessage} className="p-4 border-t border-white/10 flex gap-2">
              <input
                type="text"
                value={draftMessage}
                onChange={(e) => setDraftMessage(e.target.value)}
                placeholder="Ask about tactics, transfer budget, academy readiness, contract morale, or training..."
                className="flex-1 rounded-xl bg-slate-950 border border-white/15 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-400"
              />
              <button
                type="submit"
                disabled={busyAction || !draftMessage.trim()}
                className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" /> Send
              </button>
            </form>
          </div>
        </div>
      )}

      {/* DESTINATION 3 & 4: STAFF ROOM & SQUAD ROOM */}
      {(destination === "staff_room" || destination === "squad_room") && (
        <div className="rounded-2xl border border-white/10 bg-slate-900/90 p-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-black text-white">
                {destination === "staff_room"
                  ? "Executive & Coaching Staff Room"
                  : "First-Team & Academy Squad Dressing Room"}
              </h2>
              <p className="text-xs text-slate-400">
                {destination === "staff_room"
                  ? "Cross-departmental alignment between the Owner, General Manager, First-Team Manager, HOYD, Chief Scout, and Medical Director."
                  : "Live dressing-room pulse, captain updates, and direct leadership addresses that boost squad morale."}
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={roomDraft}
              onChange={(e) => setRoomDraft(e.target.value)}
              placeholder={
                destination === "staff_room"
                  ? "Post a strategic directive to all department heads..."
                  : "Address the squad before the next competitive fixture..."
              }
              className="flex-1 rounded-xl bg-slate-950 border border-white/15 px-4 py-2.5 text-xs text-white"
            />
            <button
              type="button"
              disabled={busyAction || !roomDraft.trim()}
              onClick={() =>
                handleSendRoomMessage(destination === "staff_room" ? "room:staff" : "room:squad")
              }
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black"
            >
              Post to Room
            </button>
          </div>

          <div className="space-y-3">
            {(destination === "staff_room" ? staffRoomFeed : squadRoomFeed).map((entry: any) => (
              <div key={entry.id} className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-emerald-400">
                    {entry.sender_name} · {entry.sender_role}
                  </span>
                  <span className="text-slate-500">
                    {entry.department || entry.tag} · World Day {entry.world_day || 1}
                  </span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed">{entry.body}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DESTINATION 5: MEETINGS */}
      {destination === "meetings" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <form
            onSubmit={handleConveneMeeting}
            className="lg:col-span-5 rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4"
          >
            <h3 className="text-base font-black text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-400" /> Convene Club Meeting
            </h3>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Meeting Subject</label>
              <input
                type="text"
                value={meetingTitle}
                onChange={(e) => setMeetingTitle(e.target.value)}
                placeholder="e.g., Q2 Transfer Budget & Stadium Expansion Alignment"
                className="w-full rounded-xl bg-slate-950 border border-white/15 px-3 py-2 text-xs text-white"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Summit Type</label>
              <select
                value={meetingType}
                onChange={(e) => setMeetingType(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-white/15 px-3 py-2 text-xs text-white"
              >
                <option value="boardroom">Boardroom Executive Alignment</option>
                <option value="tactical">Manager & Coaching Tactical Review</option>
                <option value="academy_pathway">Academy Regen Promotion Summit</option>
                <option value="squad_leadership">Players & Captain Leadership Council</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Agenda & Action Mandates</label>
              <textarea
                rows={3}
                value={meetingAgenda}
                onChange={(e) => setMeetingAgenda(e.target.value)}
                placeholder="Outline key decisions and targets..."
                className="w-full rounded-xl bg-slate-950 border border-white/15 p-3 text-xs text-white"
              />
            </div>
            <button
              type="submit"
              disabled={busyAction || !meetingTitle.trim()}
              className="w-full py-2.5 rounded-xl bg-amber-400 hover:bg-amber-300 disabled:opacity-40 text-slate-950 text-xs font-black"
            >
              Convene Meeting Now (+5 Manager Mood, +3 Squad Morale)
            </button>
          </form>

          <div className="lg:col-span-7 space-y-3">
            {meetingsList.map((m: any) => (
              <div key={m.meeting_id} className="p-4 rounded-2xl bg-slate-900 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-amber-400">{m.meeting_type}</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[11px] font-bold">
                    {m.status} · Day {m.scheduled_world_day}
                  </span>
                </div>
                <div className="text-base font-bold text-white">{m.title}</div>
                <p className="text-xs text-slate-300">{m.agenda}</p>
                {m.outcome_summary && (
                  <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
                    {m.outcome_summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DESTINATION 6: REQUESTS & DECISIONS */}
      {destination === "decisions" && (
        <div className="space-y-6">
          {dilemma && (
            <div className="rounded-2xl border border-amber-400/40 bg-slate-900 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase tracking-wider text-amber-400">
                  Executive Boardroom Dilemma · Status: {dilemma.status}
                </span>
              </div>
              <h3 className="text-xl font-black text-white">{dilemma.title}</h3>
              <p className="text-xs text-slate-300 leading-relaxed">{dilemma.description || dilemma.context}</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {(dilemma.choices || []).map((ch: any) => (
                  <div
                    key={ch.choice_id}
                    className="p-4 rounded-xl bg-slate-950 border border-white/10 flex flex-col justify-between gap-3"
                  >
                    <div>
                      <div className="text-sm font-bold text-white">{ch.label}</div>
                      <p className="text-xs text-slate-400 mt-1">{ch.description || ch.impact}</p>
                    </div>
                    <button
                      type="button"
                      disabled={busyAction || dilemma.status === "resolved"}
                      onClick={() => handleResolveDilemma(ch.choice_id)}
                      className="w-full py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black"
                    >
                      {dilemma.selected_choice_id === ch.choice_id ? "Ratified Choice" : "Approve Option"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {items
              .filter((i: any) => i.is_decision)
              .map((i: any) => (
                <InboxItem key={i.id} item={i} />
              ))}
          </div>
        </div>
      )}

      {/* DESTINATION 7: ANNOUNCEMENTS */}
      {destination === "announcements" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <form
            onSubmit={handlePublishAnnouncement}
            className="lg:col-span-5 rounded-2xl border border-white/10 bg-slate-900 p-5 space-y-4"
          >
            <h3 className="text-base font-black text-white flex items-center gap-2">
              <Megaphone className="w-4 h-4 text-emerald-400" /> Issue Official Club Communiqué
            </h3>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Headline</label>
              <input
                type="text"
                value={annTitle}
                onChange={(e) => setAnnTitle(e.target.value)}
                placeholder="Official Club Statement..."
                className="w-full rounded-xl bg-slate-950 border border-white/15 px-3 py-2 text-xs text-white"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Target Audience</label>
              <select
                value={annAudience}
                onChange={(e) => setAnnAudience(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-white/15 px-3 py-2 text-xs text-white"
              >
                <option value="all_club">All Club (Board, Staff, Squad & Supporters)</option>
                <option value="squad_only">Internal Dressing Room Only</option>
                <option value="staff_only">Internal Executive Staff Only</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Communiqué Body</label>
              <textarea
                rows={4}
                value={annBody}
                onChange={(e) => setAnnBody(e.target.value)}
                placeholder="Write the official club announcement..."
                className="w-full rounded-xl bg-slate-950 border border-white/15 p-3 text-xs text-white"
              />
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={annToNewsroom}
                onChange={(e) => setAnnToNewsroom(e.target.checked)}
              />
              Also syndicate as a verified public dispatch in the GTEX Newsroom
            </label>
            <button
              type="submit"
              disabled={busyAction || !annTitle.trim() || !annBody.trim()}
              className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 text-xs font-black"
            >
              Publish Official Communiqué
            </button>
          </form>

          <div className="lg:col-span-7 space-y-3">
            {announcementsList.map((a: any) => (
              <div key={a.announcement_id} className="p-4 rounded-2xl bg-slate-900 border border-white/10 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-emerald-400">{a.author}</span>
                  <span className="text-slate-400">
                    Audience: {a.audience} · Day {a.world_day}
                  </span>
                </div>
                <div className="text-base font-bold text-white">{a.title}</div>
                <p className="text-xs text-slate-300 leading-relaxed">{a.body}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

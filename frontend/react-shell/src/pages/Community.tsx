import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Ban,
  Bookmark,
  CornerDownRight,
  Flag,
  Hash,
  Heart,
  MessageCircle,
  Pencil,
  Pin,
  Plus,
  Send,
  Shield,
  ShieldAlert,
  Trophy,
  UserPlus,
  Users,
  VolumeX,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useActiveClub } from "@/lib/owner";
import { useRealtimeTopics } from "@/lib/realtime";
import { Btn, Chip, Empty, Loading, PageHeader, Panel } from "@/components/gtex/ui";

const TABS = [
  { id: "home", label: "Home" },
  { id: "channels", label: "Chat & Channels" },
  { id: "competitions", label: "Competitions" },
  { id: "clubs", label: "Clubs" },
  { id: "people", label: "People & Players" },
  { id: "messages", label: "Messages" },
] as const;
type TabId = (typeof TABS)[number]["id"] | "moderation";

const POST_TYPES: { value: string; label: string }[] = [
  { value: "football_discussion", label: "Football discussion" },
  { value: "club_showcase", label: "Club showcase" },
  { value: "club_achievement", label: "Club achievement" },
  { value: "club_recruitment", label: "Club recruitment" },
  { value: "supporter_recruitment", label: "Supporter recruitment" },
  { value: "competition_ad", label: "Competition advertisement" },
  { value: "player_showcase", label: "Player spotlight" },
  { value: "regen_showcase", label: "Regen spotlight" },
  { value: "transfer_update", label: "Transfer talk" },
  { value: "matchday", label: "Matchday" },
  { value: "poll", label: "Poll" },
];

const fmtTime = (iso?: string | null) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "short", timeStyle: "short" }) : "");
const name = (u: any) => u?.display_name || u?.username || "GTEX user";

function Avatar({ user, size = 8 }: { user: any; size?: number }) {
  const letter = name(user).slice(0, 1).toUpperCase();
  return user?.avatar_url ? (
    <img src={user.avatar_url} alt="" className={`size-${size} rounded-full object-cover`} />
  ) : (
    <span className={`flex size-${size} shrink-0 items-center justify-center rounded-full bg-[#14243A] text-xs font-black text-[#42B9EC]`}>{letter}</span>
  );
}

async function toggleClubSupport(clubId: string, following: boolean) {
  const body = { target_type: "club", club_id: clubId };
  if (following) await api.delete("/social/follows", { data: body });
  else await api.post("/social/follows", body);
}

async function reportTarget(target_type: string, target_id: string, subject_user_id?: string) {
  const description = window.prompt("Why are you reporting this? (optional)") ?? null;
  if (description === null) return;
  try {
    await api.post("/community/reports", { target_type, target_id, description, subject_user_id });
    toast.success("Report sent to GTEX moderators");
  } catch (e) {
    toast.error(errMsg(e));
  }
}

/* ------------------------------ Home feed ------------------------------ */

function PostCard({ post, onChange, viewerId }: { post: any; onChange: () => void; viewerId?: string }) {
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<any[] | null>(null);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(post.title || "");
  const [editBody, setEditBody] = useState(post.body || "");
  const loadComments = async () => {
    try {
      const { data } = await api.get(`/community/posts/${post.id}/comments`);
      setComments(data.comments || []);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const act = async (fn: () => Promise<any>) => {
    try {
      await fn();
      onChange();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editBody.trim()) return;
    await act(() => api.patch(`/community/posts/${post.id}`, { title: editTitle || undefined, body: editBody }));
    setEditing(false);
  };
  const club = post.club_card;
  const comp = post.competition_card;
  const player = post.player_card;
  return (
    <article data-testid={`post-${post.id}`} className="gx-panel overflow-hidden p-4">
      <header className="flex flex-wrap items-start gap-3">
        <Avatar user={post.author} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-white">
            {name(post.author)} <span className="font-normal text-slate-400">@{post.author?.username}</span>
          </p>
          <p className="text-[11px] text-slate-400">
            {fmtTime(post.created_at)}
            {post.channel_slug && (
              <>
                {" · "}
                <Link className="text-[#42B9EC] hover:underline" to={`/app/community?tab=channels&channel=${post.channel_slug}`}>
                  #{post.channel_slug}
                </Link>
              </>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {post.is_official && <Chip tone="emerald">Official</Chip>}
          <Chip tone={post.post_type.includes("recruit") || post.post_type === "competition_ad" ? "gold" : "cyan"}>
            {post.post_type.replace(/_/g, " ")}
          </Chip>
        </div>
      </header>
      {editing ? (
        <form onSubmit={saveEdit} className="mt-3 space-y-2">
          <input className="gx-input w-full" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Title (optional)" maxLength={200} />
          <textarea className="gx-input min-h-20 w-full" value={editBody} onChange={(e) => setEditBody(e.target.value)} maxLength={4000} required />
          <div className="flex justify-end gap-2">
            <Btn variant="ghost" onClick={() => setEditing(false)}>Cancel</Btn>
            <Btn type="submit">Save</Btn>
          </div>
        </form>
      ) : (
        <>
          {post.title && <h3 className="mt-3 text-base font-extrabold text-white break-words">{post.title}</h3>}
          <p className="mt-2 whitespace-pre-wrap break-words text-sm text-slate-200">{post.body}</p>
        </>
      )}
      {Array.isArray(post.tags) && post.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {post.tags.map((tg: string) => (
            <span key={tg} className="rounded bg-[#14243A] px-2 py-0.5 text-[11px] text-[#42B9EC]">#{tg}</span>
          ))}
        </div>
      )}

      {club && (
        <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-[#25354B] bg-[#0E1A2C] p-3">
          <Shield size={18} className="text-[#00C991]" />
          <div className="min-w-0 flex-1">
            <Link to={`/club/${club.slug}`} className="font-bold text-white hover:underline">{club.club_name}</Link>
            <p className="text-xs text-slate-400">{[club.city_name, club.country_code].filter(Boolean).join(" · ")} · {club.follower_count} supporters</p>
          </div>
          {viewerId && (
            <Btn
              variant={club.viewer_follows ? "secondary" : "primary"}
              onClick={() => act(() => toggleClubSupport(club.id, !!club.viewer_follows))}
            >
              <UserPlus size={13} /> {club.viewer_follows ? "Following" : "Support"}
            </Btn>
          )}
        </div>
      )}
      {player && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#42B9EC]/30 bg-[#42B9EC]/5 p-3 text-xs text-slate-200">
          <span>
            <b className="text-white">{player.name}</b> · {player.position} {player.gsi ? `· GSI ${player.gsi}` : ""}
            {player.is_regen ? " · Academy Regen" : ""}
          </span>
          <Link to={player.is_regen ? "/app/regen-world" : "/app/market"} className="text-[#42B9EC] font-bold hover:underline">Open Market Profile</Link>
        </div>
      )}
      {comp && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#E5B63F]/30 bg-[#E5B63F]/5 p-3 text-xs text-slate-200">
          <span>
            <Trophy size={14} className="mr-1 inline text-[#E5B63F]" />
            <b>{comp.title}</b> · {comp.current_participants}/{comp.max_participants} slots · free entry · {comp.status}
          </span>
          <Link to={`/app/community?tab=competitions&competition=${comp.id}`} className="font-bold text-[#E5B63F] hover:underline">
            View & Apply
          </Link>
        </div>
      )}
      {post.poll && (
        <ul className="mt-3 space-y-1.5" aria-label="Poll options">
          {post.poll.options.map((o: any) => {
            const pct = post.poll.total_votes ? Math.round((o.votes / post.poll.total_votes) * 100) : 0;
            return (
              <li key={o.id}>
                <button
                  type="button"
                  disabled={!viewerId}
                  onClick={() => act(() => api.post(`/community/posts/${post.id}/vote`, { option_id: o.id }))}
                  className={`relative w-full overflow-hidden rounded-lg border px-3 py-2 text-left text-sm ${post.poll.viewer_option_id === o.id ? "border-[#00C991]" : "border-[#25354B]"}`}
                >
                  <span className="absolute inset-y-0 left-0 bg-[#42B9EC]/15" style={{ width: `${pct}%` }} />
                  <span className="relative">{o.label} <span className="float-right text-slate-400">{pct}% ({o.votes})</span></span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <footer className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <button type="button" disabled={!viewerId} className="gx-btn gx-btn-ghost" onClick={() => act(() => api.post(`/community/posts/${post.id}/reactions`, { reaction_type: "like" }))} aria-pressed={post.viewer_reactions?.includes("like")}>
          <Heart size={13} className={post.viewer_reactions?.includes("like") ? "fill-[#EF4444] text-[#EF4444]" : ""} /> {post.reaction_count}
        </button>
        <button type="button" className="gx-btn gx-btn-ghost" onClick={() => { setOpen(!open); if (!open && comments === null) loadComments(); }}>
          <MessageCircle size={13} /> {post.comment_count}
        </button>
        <button type="button" disabled={!viewerId} className="gx-btn gx-btn-ghost" onClick={() => act(() => api.post(`/community/posts/${post.id}/bookmark`))} aria-pressed={post.viewer_bookmarked}>
          <Bookmark size={13} className={post.viewer_bookmarked ? "fill-[#E5B63F] text-[#E5B63F]" : ""} />
        </button>
        {viewerId && post.author_user_id !== viewerId && (
          <button type="button" className="gx-btn gx-btn-ghost ml-auto" onClick={() => reportTarget("post", post.id, post.author_user_id)}>
            <Flag size={13} /> Report
          </button>
        )}
        {viewerId && post.author_user_id === viewerId && (
          <div className="ml-auto flex items-center gap-1">
            <button type="button" className="gx-btn gx-btn-ghost" onClick={() => setEditing(!editing)}>
              <Pencil size={12} /> Edit
            </button>
            <button type="button" className="gx-btn gx-btn-ghost" onClick={() => act(() => api.delete(`/community/posts/${post.id}`))}>
              Delete
            </button>
          </div>
        )}
      </footer>
      {open && (
        <div className="mt-3 space-y-2 border-t border-[#25354B] pt-3">
          {(comments || []).map((c) => (
            <p key={c.id} className="text-sm text-slate-200 break-words"><b className="text-white">{name(c.author)}</b> {c.body}</p>
          ))}
          {comments && comments.length === 0 && <p className="text-xs text-slate-400">No replies yet.</p>}
          {viewerId && (
            <form
              className="flex gap-2"
              onSubmit={async (e) => {
                e.preventDefault();
                if (!draft.trim()) return;
                try {
                  await api.post(`/community/posts/${post.id}/comments`, { body: draft });
                  setDraft("");
                  await loadComments();
                  onChange();
                } catch (err) {
                  toast.error(errMsg(err));
                }
              }}
            >
              <input className="gx-input flex-1" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Write a reply" aria-label="Reply" maxLength={2000} />
              <Btn type="submit"><Send size={13} /></Btn>
            </form>
          )}
        </div>
      )}
    </article>
  );
}

function Composer({ onPosted, clubs }: { onPosted: () => void; clubs: any[] }) {
  const [type, setType] = useState("football_discussion");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [clubId, setClubId] = useState("");
  const [playerId, setPlayerId] = useState("");
  const [playerQuery, setPlayerQuery] = useState("");
  const [compId, setCompId] = useState("");
  const [channelSlug, setChannelSlug] = useState("");
  const [tagsRaw, setTagsRaw] = useState("");
  const [showAttachments, setShowAttachments] = useState(false);
  const [opts, setOpts] = useState("");
  const [busy, setBusy] = useState(false);

  const playerSearch = useQuery({
    queryKey: ["composer-players", playerQuery, type === "regen_showcase"],
    enabled: showAttachments && playerQuery.trim().length >= 2,
    queryFn: async () =>
      (await api.get("/community/discovery/players", { params: { q: playerQuery.trim(), regens_only: type === "regen_showcase", limit: 8 } })).data.players as any[],
  });
  const compsList = useQuery({
    queryKey: ["composer-competitions"],
    enabled: showAttachments || type === "competition_ad",
    queryFn: async () => (await api.get("/community/competitions", { params: { limit: 15 } })).data.competitions as any[],
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const tags = tagsRaw.split(",").map((s) => s.trim().replace(/^#/, "")).filter(Boolean);
      await api.post("/community/posts", {
        post_type: type,
        title: title || undefined,
        body,
        channel_slug: channelSlug || undefined,
        club_id: clubId || undefined,
        player_id: playerId || undefined,
        competition_id: compId || undefined,
        tags,
        poll_options: type === "poll" ? opts.split("\n").map((s) => s.trim()).filter(Boolean) : [],
      });
      setTitle("");
      setBody("");
      setOpts("");
      setPlayerId("");
      setCompId("");
      setTagsRaw("");
      toast.success("Posted to GTEX Community");
      onPosted();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="gx-panel space-y-2 p-4" data-testid="community-composer">
      <div className="grid gap-2 sm:grid-cols-2">
        <select className="gx-input" value={type} onChange={(e) => setType(e.target.value)} aria-label="Post type">
          {POST_TYPES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
        {clubs.length > 0 && (
          <select className="gx-input" value={clubId} onChange={(e) => setClubId(e.target.value)} aria-label="Attach one of your clubs">
            <option value="">No club attached</option>
            {clubs.map((c: any) => <option key={c.club_id} value={c.club_id}>{c.club_name}</option>)}
          </select>
        )}
      </div>
      <input className="gx-input w-full" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
      <textarea className="gx-input min-h-24 w-full" placeholder="Share football thoughts, show off your club, find supporters…" value={body} onChange={(e) => setBody(e.target.value)} maxLength={4000} required />
      {type === "poll" && <textarea className="gx-input w-full" placeholder={"One poll option per line (2–6)"} value={opts} onChange={(e) => setOpts(e.target.value)} />}
      {showAttachments && (
        <div className="grid gap-2 rounded-xl border border-[#25354B] bg-[#0E1A2C] p-3 sm:grid-cols-2">
          <div>
            <input
              className="gx-input w-full text-xs"
              placeholder="Spotlight a player/regen (type 2+ chars)"
              value={playerQuery}
              onChange={(e) => setPlayerQuery(e.target.value)}
              aria-label="Search player to spotlight"
            />
            {(playerSearch.data || []).length > 0 && (
              <div className="mt-1 max-h-28 space-y-1 overflow-y-auto">
                {(playerSearch.data || []).map((pl) => (
                  <button
                    key={pl.id}
                    type="button"
                    onClick={() => { setPlayerId(pl.id); setPlayerQuery(pl.name); }}
                    className={`block w-full rounded px-2 py-1 text-left text-xs ${playerId === pl.id ? "bg-[#00C991]/20 text-white" : "bg-slate-950 text-slate-300"}`}
                  >
                    {pl.name} · {pl.position} {pl.gsi ? `· GSI ${pl.gsi}` : ""} {pl.is_regen ? "(Regen)" : ""}
                  </button>
                ))}
              </div>
            )}
          </div>
          <select className="gx-input text-xs" value={compId} onChange={(e) => setCompId(e.target.value)} aria-label="Attach competition">
            <option value="">Attach competition (optional)</option>
            {(compsList.data || []).map((c: any) => (
              <option key={c.id} value={c.id}>{c.title} ({c.slots_remaining} slots)</option>
            ))}
          </select>
          <select className="gx-input text-xs" value={channelSlug} onChange={(e) => setChannelSlug(e.target.value)} aria-label="Link topic channel">
            <option value="">Topic channel (optional)</option>
            <option value="football-talk">#football-talk</option>
            <option value="gtex-players">#gtex-players</option>
            <option value="gtex-regens">#gtex-regens</option>
            <option value="club-showcase">#club-showcase</option>
            <option value="transfer-talk">#transfer-talk</option>
            <option value="matchday">#matchday</option>
            <option value="competitions-recruitment">#competitions-recruitment</option>
            <option value="user-hosted-tournaments">#user-hosted-tournaments</option>
            <option value="tactics-debate">#tactics-debate</option>
          </select>
          <input className="gx-input text-xs" placeholder="Tags comma-separated (e.g. tactics, youth)" value={tagsRaw} onChange={(e) => setTagsRaw(e.target.value)} aria-label="Post tags" />
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button type="button" onClick={() => setShowAttachments(!showAttachments)} className="text-xs font-semibold text-[#42B9EC] hover:underline">
          {showAttachments ? "Hide spotlight & attachments" : "+ Attach player, regen, competition or tags"}
        </button>
        <Btn type="submit" disabled={busy || !body.trim()}>Post</Btn>
      </div>
    </form>
  );
}

function HomeTab({ viewerId, clubs }: { viewerId?: string; clubs: any[] }) {
  const [sort, setSort] = useState("recent");
  const [filter, setFilter] = useState("");
  const [saved, setSaved] = useState(false);
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["community-posts", sort, filter, saved],
    queryFn: async () => (await api.get("/community/posts", { params: { sort, post_type: filter || undefined, saved_only: saved || undefined } })).data,
  });
  useRealtimeTopics(["community:feed"], (ev) => { if (ev.type === "community_post_created") qc.invalidateQueries({ queryKey: ["community-posts"] }); });
  const refresh = () => qc.invalidateQueries({ queryKey: ["community-posts"] });
  return (
    <div className="space-y-4">
      {viewerId ? <Composer onPosted={refresh} clubs={clubs} /> : <p className="text-sm text-slate-300"><Link className="underline" to="/auth/login">Sign in</Link> to post and chat. Everyone can read.</p>}
      <div className="flex flex-wrap gap-2" role="toolbar" aria-label="Feed filters">
        {["recent", "trending", "top", "recruiting"].map((s) => (
          <button key={s} type="button" className={`gx-chip ${sort === s ? "border-[#00C991] text-white" : ""}`} onClick={() => setSort(s)}>{s}</button>
        ))}
        <select className="gx-input !py-1 text-xs" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {POST_TYPES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
        {viewerId && <button type="button" className={`gx-chip ${saved ? "border-[#E5B63F] text-white" : ""}`} onClick={() => setSaved(!saved)}>Saved</button>}
      </div>
      {q.isLoading ? <Loading label="Loading feed" /> : q.isError ? <Empty title="Feed unavailable" body={errMsg(q.error)} /> : (q.data?.posts || []).length === 0 ? (
        <Empty title="No posts yet" body="Be the first to start a football conversation." />
      ) : (
        (q.data.posts as any[]).map((p) => <PostCard key={p.id} post={p} onChange={refresh} viewerId={viewerId} />)
      )}
    </div>
  );
}

/* ------------------------------ Channels ------------------------------- */

function ChannelsTab({ viewerId, isAdmin }: { viewerId?: string; isAdmin?: boolean }) {
  const [params, setParams] = useSearchParams();
  const slug = params.get("channel") || "global-lounge";
  const qc = useQueryClient();
  const channels = useQuery({ queryKey: ["community-channels"], queryFn: async () => (await api.get("/community/channels")).data.channels as any[] });
  const [messages, setMessages] = useState<any[]>([]);
  const [pinnedMessages, setPinnedMessages] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<any | null>(null);
  const [newChannelOpen, setNewChannelOpen] = useState(false);
  const [newChName, setNewChName] = useState("");
  const [newChDesc, setNewChDesc] = useState("");
  const [loading, setLoading] = useState(true);
  const lastSeq = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);

  const merge = useCallback((incoming: any[]) => {
    setMessages((prev) => {
      const byId = new Map(prev.map((m) => [m.id, m]));
      incoming.forEach((m) => byId.set(m.id, m));
      const next = Array.from(byId.values()).sort((a, b) => a.seq - b.seq);
      lastSeq.current = next.length ? next[next.length - 1].seq : 0;
      return next;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessages([]);
    setPinnedMessages([]);
    setReplyTo(null);
    lastSeq.current = 0;
    api.get(`/community/channels/${slug}/messages`, { params: { limit: 50 } })
      .then(({ data }) => {
        if (cancelled) return;
        merge(data.messages);
        setPinnedMessages(data.pinned_messages || []);
        setHasMore(data.has_more);
        setNextBefore(data.next_before_seq);
      })
      .catch((e) => toast.error(errMsg(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [slug, merge]);

  const catchUp = useCallback(async () => {
    try {
      const { data } = await api.get(`/community/channels/${slug}/messages`, { params: { after_seq: lastSeq.current } });
      if (data.messages.length) merge(data.messages);
      if (Array.isArray(data.pinned_messages)) setPinnedMessages(data.pinned_messages);
    } catch { /* next reconnect retries */ }
  }, [slug, merge]);

  const { connected } = useRealtimeTopics(
    [`community:channel:${slug}`],
    (ev) => { if (ev.type === "community_channel_message" && ev.data?.message) merge([ev.data.message]); },
    catchUp
  );
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [messages.length]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const body = draft.trim();
    if (!body) return;
    try {
      const { data } = await api.post(`/community/channels/${slug}/messages`, {
        body,
        reply_to_message_id: replyTo?.id || undefined,
      });
      merge([data]);
      setDraft("");
      setReplyTo(null);
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const loadOlder = async () => {
    if (!nextBefore) return;
    const { data } = await api.get(`/community/channels/${slug}/messages`, { params: { before_seq: nextBefore, limit: 50 } });
    merge(data.messages);
    setHasMore(data.has_more);
    setNextBefore(data.next_before_seq);
  };
  const createChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newChName.trim()) return;
    try {
      const { data } = await api.post("/community/channels", { name: newChName.trim(), description: newChDesc.trim() });
      setNewChName("");
      setNewChDesc("");
      setNewChannelOpen(false);
      await qc.invalidateQueries({ queryKey: ["community-channels"] });
      setParams({ tab: "channels", channel: data.slug });
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const togglePin = async (m: any) => {
    try {
      await api.post(`/community/channels/messages/${m.id}/pin`);
      await catchUp();
      toast.success(m.pinned ? "Unpinned message" : "Pinned to channel");
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const active = (channels.data || []).find((c) => c.slug === slug);
  return (
    <div className="grid gap-4 md:grid-cols-[230px_1fr]">
      <div className="space-y-2 min-w-0">
        <nav aria-label="Channels" className="flex gap-2 overflow-x-auto pb-1 md:flex-col md:overflow-visible">
          {(channels.data || []).map((c) => (
            <button key={c.slug} type="button" onClick={() => setParams({ tab: "channels", channel: c.slug })} className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-bold ${slug === c.slug ? "border-[#00C991] bg-[#00C991]/10 text-white" : "border-[#25354B] text-slate-300"}`}>
              <Hash size={13} /> <span className="truncate">{c.name}</span>
            </button>
          ))}
        </nav>
        {viewerId && (
          <div>
            <button type="button" onClick={() => setNewChannelOpen(!newChannelOpen)} className="inline-flex items-center gap-1 text-xs font-bold text-[#42B9EC] hover:underline">
              <Plus size={13} /> New topic channel
            </button>
            {newChannelOpen && (
              <form onSubmit={createChannel} className="mt-2 space-y-1.5 rounded-xl border border-[#25354B] bg-[#0E1A2C] p-2.5">
                <input className="gx-input w-full text-xs" placeholder="Channel name" value={newChName} onChange={(e) => setNewChName(e.target.value)} minLength={3} required />
                <input className="gx-input w-full text-xs" placeholder="Description" value={newChDesc} onChange={(e) => setNewChDesc(e.target.value)} />
                <Btn type="submit" className="w-full text-xs">Create channel</Btn>
              </form>
            )}
          </div>
        )}
      </div>
      <Panel title={active?.name || "Channel"} eyebrow={connected ? "Live" : "Reconnecting when needed"} live={connected}>
        <p className="mb-3 text-xs text-slate-400">{active?.description}</p>
        {pinnedMessages.length > 0 && (
          <div className="mb-3 rounded-xl border border-[#E5B63F]/40 bg-[#E5B63F]/10 p-2.5 text-xs text-amber-100">
            <p className="font-bold flex items-center gap-1 text-[#E5B63F]"><Pin size={12} /> Pinned</p>
            <p className="mt-0.5 line-clamp-2">{pinnedMessages[0].body}</p>
          </div>
        )}
        <div className="max-h-[55vh] min-h-48 space-y-2 overflow-y-auto pr-1" role="log" aria-live="polite">
          {hasMore && <Btn variant="secondary" onClick={loadOlder}>Load older messages</Btn>}
          {loading ? <Loading label="Loading messages" /> : messages.length === 0 ? <Empty title="Quiet in here" body="Say hello and start the conversation." /> : messages.map((m) => (
            <div key={m.id} className="flex gap-2" data-seq={m.seq}>
              <Avatar user={m.sender} size={7} />
              <div className="min-w-0 flex-1">
                <p className="text-xs"><b className="text-white">{name(m.sender)}</b> <span className="text-slate-500">{fmtTime(m.created_at)}</span></p>
                {m.reply_preview && <p className="border-l-2 border-[#25354B] pl-2 text-[11px] text-slate-400 truncate">{m.reply_preview.body}</p>}
                <p className="whitespace-pre-wrap break-words text-sm text-slate-200">{m.body}</p>
              </div>
              {viewerId && (
                <div className="flex items-start gap-1">
                  <button type="button" className="text-slate-500 hover:text-white" aria-label="Reply to message" onClick={() => setReplyTo(m)}><CornerDownRight size={12} /></button>
                  {isAdmin && (
                    <button type="button" className="text-slate-500 hover:text-[#E5B63F]" aria-label="Pin message" onClick={() => togglePin(m)}><Pin size={12} /></button>
                  )}
                  {m.sender_user_id !== viewerId && (
                    <button type="button" className="text-slate-500 hover:text-white" aria-label="Report message" onClick={() => reportTarget("channel_message", m.id, m.sender_user_id)}><Flag size={12} /></button>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>
        {replyTo && (
          <div className="mt-2 flex items-center justify-between rounded-lg border border-[#25354B] bg-[#0E1A2C] px-3 py-1 text-xs text-slate-300">
            <span className="truncate">Replying to <b>{name(replyTo.sender)}</b>: {replyTo.body}</span>
            <button type="button" onClick={() => setReplyTo(null)} className="ml-2 text-slate-400 hover:text-white">×</button>
          </div>
        )}
        {viewerId ? (
          <form onSubmit={send} className="mt-3 flex gap-2">
            <input className="gx-input flex-1 min-w-0" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={`Message #${slug}`} aria-label="Message" maxLength={2000} />
            <Btn type="submit" disabled={!draft.trim()}><Send size={14} /></Btn>
          </form>
        ) : <p className="mt-3 text-xs text-slate-400">Sign in to join the chat.</p>}
      </Panel>
    </div>
  );
}

/* ---------------------------- Competitions ----------------------------- */

function CompetitionsTab({ viewerId, clubs }: { viewerId?: string; clubs: any[] }) {
  const [source, setSource] = useState("all");
  const [search, setSearch] = useState("");
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["community-competitions", source, search],
    queryFn: async () => (await api.get("/community/competitions", { params: { source: source === "all" ? undefined : source, search: search || undefined } })).data.competitions as any[],
  });
  const [reviewing, setReviewing] = useState<string | null>(null);
  const apps = useQuery({
    queryKey: ["community-applications", reviewing],
    enabled: !!reviewing,
    queryFn: async () => (await api.get(`/community/competitions/${reviewing}/applications`)).data.applications as any[],
  });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["community-competitions"] }); qc.invalidateQueries({ queryKey: ["community-applications"] }); };
  const apply = async (c: any) => {
    const note = c.visibility === "public" ? "" : window.prompt("Tell the organiser why you should be included") || "";
    try {
      const { data } = await api.post(`/community/competitions/${c.id}/apply`, { club_id: clubs[0]?.club_id, note: note || undefined });
      toast.success(data.mode === "joined" ? "You are in" : "Application sent to the organiser");
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const review = async (id: string, decision: string) => {
    try {
      await api.post(`/community/competitions/applications/${id}/review`, { decision });
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {[["all", "All"], ["user_hosted", "User-hosted"], ["gtex_official", "Official GTEX"]].map(([id, label]) => (
          <button key={id} type="button" className={`gx-chip ${source === id ? "border-[#00C991] text-white" : ""}`} onClick={() => setSource(id)}>{label}</button>
        ))}
        <input className="gx-input !py-1 text-xs" placeholder="Search competitions" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search competitions" />
      </div>
      <p className="text-xs text-slate-400">Every GTEX competition is free to enter. Prize coin is funded by the host or GTEX.</p>
      {q.isLoading ? <Loading /> : (q.data || []).length === 0 ? <Empty title="No competitions found" body="Host one from Competitions & Tournaments." /> : (q.data || []).map((c) => (
        <div key={`${c.source_kind}-${c.id}`} className="gx-panel p-4" data-testid={`comp-${c.id}`}>
          <div className="flex flex-wrap items-center gap-2">
            <Trophy size={16} className="text-[#E5B63F]" />
            <h3 className="font-extrabold text-white">{c.title}</h3>
            <Chip tone={c.is_gtex_official ? "emerald" : "cyan"}>{c.is_gtex_official ? "Official GTEX" : "User-hosted"}</Chip>
            <Chip>{c.status}</Chip>
            <Chip tone="gold">Free entry</Chip>
          </div>
          <p className="mt-1 text-sm text-slate-300 break-words">{c.description}</p>
          <p className="mt-2 text-xs text-slate-400">
            {c.current_participants}/{c.max_participants} entered · {c.slots_remaining} slots left · host {name(c.organizer)}
            {c.reward_pool_fancoin > 0 && ` · prize pool ${c.reward_pool_fancoin}`}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {!c.is_gtex_official && viewerId && !c.is_organizer && !c.viewer_joined && c.status === "open" && c.slots_remaining > 0 && c.viewer_application_status !== "pending" && (
              <Btn onClick={() => apply(c)}>{c.visibility === "public" ? "Join" : "Apply to join"}</Btn>
            )}
            {c.viewer_joined && <Chip tone="emerald">You are entered</Chip>}
            {c.viewer_application_status === "pending" && <Chip tone="gold">Application pending</Chip>}
            {c.viewer_application_status === "rejected" && <Chip tone="red">Application declined</Chip>}
            {c.is_organizer && <Btn variant="secondary" onClick={() => setReviewing(reviewing === c.id ? null : c.id)}>Applications ({c.pending_applications_count})</Btn>}
            {c.is_gtex_official && <Link className="gx-btn gx-btn-secondary" to="/app/competitions">Open in Competitions</Link>}
          </div>
          {reviewing === c.id && (
            <ul className="mt-3 space-y-2 border-t border-[#25354B] pt-3">
              {(apps.data || []).length === 0 && <li className="text-xs text-slate-400">No applications.</li>}
              {(apps.data || []).map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-white">{name(a.applicant)}</span>
                  {a.club_name && <span className="text-slate-400">· {a.club_name}</span>}
                  {a.note && <span className="text-slate-400 break-words">“{a.note}”</span>}
                  <Chip tone={a.status === "accepted" ? "emerald" : a.status === "rejected" ? "red" : "gold"}>{a.status}</Chip>
                  {a.status === "pending" && (<><Btn onClick={() => review(a.id, "accept")}>Accept</Btn><Btn variant="secondary" onClick={() => review(a.id, "reject")}>Reject</Btn></>)}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------- Clubs --------------------------------- */

function ClubsTab({ viewerId }: { viewerId?: string }) {
  const [search, setSearch] = useState("");
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["community-clubs", search], queryFn: async () => (await api.get("/community/discovery/clubs", { params: { q: search || undefined } })).data.clubs as any[] });
  return (
    <div className="space-y-3">
      <input className="gx-input w-full" placeholder="Search clubs by name or city" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search clubs" />
      {q.isLoading ? <Loading /> : (q.data || []).length === 0 ? <Empty title="No clubs yet" /> : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(q.data || []).map((c) => (
            <div key={c.id} className="gx-panel p-4">
              <div className="flex items-center gap-3">
                <span className="size-10 shrink-0 rounded-lg border border-white/20" style={{ background: c.primary_color }} />
                <div className="min-w-0 flex-1">
                  <Link to={`/club/${c.slug}`} className="block truncate font-extrabold text-white hover:underline">{c.club_name}</Link>
                  <p className="truncate text-xs text-slate-400">{[c.city_name, c.country_code, c.stadium_name].filter(Boolean).join(" · ")}</p>
                </div>
              </div>
              {c.description && <p className="mt-2 line-clamp-3 text-sm text-slate-300">{c.description}</p>}
              <p className="mt-2 text-xs text-slate-400">{c.trophy_count} trophies · {c.follower_count} supporters · owner {name(c.owner)}</p>
              {viewerId && (
                <Btn className="mt-3" variant={c.viewer_follows ? "secondary" : "primary"} onClick={async () => {
                  try { await toggleClubSupport(c.id, !!c.viewer_follows); qc.invalidateQueries({ queryKey: ["community-clubs"] }); } catch (e) { toast.error(errMsg(e)); }
                }}><UserPlus size={13} /> {c.viewer_follows ? "Following" : "Support club"}</Btn>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------- People & Players ----------------------- */

function PeopleTab({ viewerId, onMessage }: { viewerId?: string; onMessage: (userId: string) => void }) {
  const [mode, setMode] = useState<"members" | "players">("members");
  const [search, setSearch] = useState("");
  const [regensOnly, setRegensOnly] = useState(false);
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["community-people", search],
    enabled: mode === "members",
    queryFn: async () => (await api.get("/community/discovery/people", { params: { q: search || undefined } })).data.people as any[],
  });
  const playersQ = useQuery({
    queryKey: ["community-players-dir", search, regensOnly],
    enabled: mode === "players",
    queryFn: async () =>
      (await api.get("/community/discovery/players", { params: { q: search || undefined, regens_only: regensOnly } })).data.players as any[],
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={`gx-chip ${mode === "members" ? "border-[#00C991] text-white" : ""}`} onClick={() => setMode("members")}>
          Members & Organisers
        </button>
        <button type="button" className={`gx-chip ${mode === "players" ? "border-[#42B9EC] text-white" : ""}`} onClick={() => setMode("players")}>
          Players & Academy Regens
        </button>
        {mode === "players" && (
          <label className="ml-auto inline-flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" checked={regensOnly} onChange={(e) => setRegensOnly(e.target.checked)} />
            Regens only
          </label>
        )}
      </div>
      <input
        className="gx-input w-full"
        placeholder={mode === "members" ? "Search people by name or username" : "Search public players & regens by name or position"}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        aria-label={mode === "members" ? "Search people" : "Search players and regens"}
      />
      {mode === "members" ? (
        q.isLoading ? <Loading /> : (q.data || []).length === 0 ? <Empty title="Nobody found" /> : (
          <div className="grid gap-3 sm:grid-cols-2">
            {(q.data || []).map((p) => (
              <div key={p.id} className="gx-panel flex items-center gap-3 p-3">
                <Avatar user={p} size={10} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold text-white">{name(p)}</p>
                  <p className="truncate text-xs text-slate-400">@{p.username}{p.club ? ` · ${p.club.club_name}` : ""}</p>
                </div>
                {viewerId && (
                  <div className="flex gap-1">
                    <Btn variant="secondary" aria-label={`Message ${name(p)}`} onClick={() => onMessage(p.id)}><MessageCircle size={13} /></Btn>
                    <Btn variant="ghost" aria-label={`Mute ${name(p)}`} onClick={async () => { try { await api.post(`/community/users/${p.id}/mute`, { muted: !p.viewer_muted }); toast.success(p.viewer_muted ? "Unmuted" : "Muted"); qc.invalidateQueries({ queryKey: ["community-people"] }); } catch (e) { toast.error(errMsg(e)); } }}><VolumeX size={13} /></Btn>
                    <Btn variant="ghost" aria-label={`Block ${name(p)}`} onClick={async () => { try { await api.post(`/community/users/${p.id}/block`); toast.success(`Blocked ${name(p)}`); qc.invalidateQueries({ queryKey: ["community-people"] }); qc.invalidateQueries({ queryKey: ["community-posts"] }); } catch (e) { toast.error(errMsg(e)); } }}><Ban size={13} /></Btn>
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      ) : (
        playersQ.isLoading ? <Loading /> : (playersQ.data || []).length === 0 ? <Empty title="No matching players" /> : (
          <div className="grid gap-3 sm:grid-cols-2">
            {(playersQ.data || []).map((pl) => (
              <div key={pl.id} className="gx-panel flex items-center justify-between gap-3 p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold text-white">
                    {pl.name} {pl.is_regen && <Chip tone="cyan">Regen</Chip>}
                  </p>
                  <p className="truncate text-xs text-slate-400">
                    {pl.position} {pl.gsi ? `· GSI ${pl.gsi}` : ""} {pl.country ? `· ${pl.country}` : ""}
                  </p>
                </div>
                <Link className="gx-btn gx-btn-secondary text-xs shrink-0" to={pl.is_regen ? "/app/regen-world" : "/app/market"}>Scout</Link>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}

/* ------------------------------ Messages ------------------------------- */

function MessagesTab({ viewerId, startWith, clearStart }: { viewerId?: string; startWith: string | null; clearStart: () => void }) {
  const qc = useQueryClient();
  const threads = useQuery({ queryKey: ["community-pm-threads"], enabled: !!viewerId, queryFn: async () => (await api.get("/community/private-messages/threads")).data as any[] });
  const [active, setActive] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [groupTitle, setGroupTitle] = useState("");
  const [picker, setPicker] = useState("");
  const [selected, setSelected] = useState<any[]>([]);
  const lastSeq = useRef(0);
  const people = useQuery({ queryKey: ["pm-people", picker], enabled: !!viewerId && picker.length >= 2, queryFn: async () => (await api.get("/community/discovery/people", { params: { q: picker, limit: 8 } })).data.people as any[] });

  const merge = useCallback((incoming: any[]) => {
    setMessages((prev) => {
      const byId = new Map(prev.map((m) => [m.id, m]));
      incoming.forEach((m) => byId.set(m.id, m));
      const next = Array.from(byId.values()).sort((a, b) => (a.seq || 0) - (b.seq || 0));
      lastSeq.current = next.length ? next[next.length - 1].seq || 0 : 0;
      return next;
    });
  }, []);

  const open = useCallback(async (threadId: string) => {
    setActive(threadId);
    setMessages([]);
    lastSeq.current = 0;
    try {
      const { data } = await api.get(`/community/private-messages/threads/${threadId}/messages/page`, { params: { limit: 40 } });
      merge(data.messages);
      setHasMore(data.has_more);
      setNextBefore(data.next_before_seq);
      qc.invalidateQueries({ queryKey: ["community-pm-threads"] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  }, [merge, qc]);

  useEffect(() => {
    if (startWith && !selected.find((s) => s.id === startWith)) {
      setSelected([{ id: startWith, display_name: "Selected user" }]);
      clearStart();
    }
  }, [startWith, selected, clearStart]);

  const catchUp = useCallback(async () => {
    if (!active) return;
    try {
      const { data } = await api.get(`/community/private-messages/threads/${active}/messages/page`, { params: { after_seq: lastSeq.current } });
      if (data.messages.length) merge(data.messages);
    } catch { /* retry on next reconnect */ }
  }, [active, merge]);

  useRealtimeTopics(
    active ? [`pm:${active}`, "user"] : ["user"],
    (ev) => {
      if (ev.type === "pm_message" && ev.data?.thread_id === active) catchUp();
      if (ev.type === "pm_message" || ev.type === "pm_thread_created") qc.invalidateQueries({ queryKey: ["community-pm-threads"] });
    },
    catchUp,
    !!viewerId
  );

  const activeThreadObj = useMemo(() => (threads.data || []).find((t: any) => t.id === active) || null, [threads.data, active]);
  const otherParticipant = activeThreadObj?.participants?.find((p: any) => p.user_id !== viewerId) || null;

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const body = draft.trim();
    if (!body) return;
    try {
      if (active) {
        await api.post(`/community/private-messages/threads/${active}/messages`, { body });
        setDraft("");
        await catchUp();
      } else if (selected.length) {
        const { data } = await api.post("/community/private-messages/threads", {
          participant_user_ids: selected.map((s) => s.id),
          subject: selected.length > 1 ? (groupTitle.trim() || "Group chat") : "",
          initial_message: body,
        });
        setDraft("");
        setGroupTitle("");
        setSelected([]);
        await qc.invalidateQueries({ queryKey: ["community-pm-threads"] });
        await open(data.id);
      }
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  if (!viewerId) return <Empty title="Sign in for private messages" />;
  return (
    <div className="grid gap-4 md:grid-cols-[260px_1fr]">
      <div className="space-y-2 min-w-0">
        <Btn variant="secondary" onClick={() => { setActive(null); setMessages([]); }}>New conversation</Btn>
        {(threads.data || []).map((t: any) => (
          <button key={t.id} type="button" onClick={() => open(t.id)} className={`block w-full rounded-lg border px-3 py-2 text-left text-xs ${active === t.id ? "border-[#00C991] bg-[#00C991]/10" : "border-[#25354B]"}`}>
            <span className="flex items-center justify-between gap-2 font-bold text-white">
              <span className="truncate">{t.subject || `Conversation · ${t.participants.length} people`}</span>
              {t.is_group && <Chip tone="cyan">Group</Chip>}
            </span>
            <span className="text-slate-400">{fmtTime(t.last_message_at)}</span>
          </button>
        ))}
        {threads.data && threads.data.length === 0 && <p className="text-xs text-slate-400">No conversations yet.</p>}
      </div>
      <Panel title={activeThreadObj?.subject || (active ? "Conversation" : "New conversation")}>
        {!active && (
          <div className="mb-3 space-y-2">
            <input className="gx-input w-full" placeholder="Find people to message (select 2+ for group)" value={picker} onChange={(e) => setPicker(e.target.value)} aria-label="Find people" />
            {selected.length > 1 && (
              <input className="gx-input w-full text-xs" placeholder="Group name (optional)" value={groupTitle} onChange={(e) => setGroupTitle(e.target.value)} aria-label="Group name" />
            )}
            <div className="flex flex-wrap gap-1">{selected.map((s) => <button key={s.id} type="button" className="gx-chip" onClick={() => setSelected(selected.filter((x) => x.id !== s.id))}>{name(s)} ×</button>)}</div>
            {(people.data || []).filter((p) => !selected.find((s) => s.id === p.id)).map((p) => (
              <button key={p.id} type="button" className="block w-full rounded border border-[#25354B] px-2 py-1 text-left text-sm text-slate-200" onClick={() => { setSelected([...selected, p]); setPicker(""); }}>{name(p)} <span className="text-slate-500">@{p.username}</span></button>
            ))}
          </div>
        )}
        <div className="max-h-[50vh] space-y-2 overflow-y-auto" role="log" aria-live="polite">
          {hasMore && <Btn variant="secondary" onClick={async () => { const { data } = await api.get(`/community/private-messages/threads/${active}/messages/page`, { params: { before_seq: nextBefore } }); merge(data.messages); setHasMore(data.has_more); setNextBefore(data.next_before_seq); }}>Load older messages</Btn>}
          {messages.map((m) => (
            <div key={m.id} className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${m.sender_user_id === viewerId ? "ml-auto bg-[#00C991]/15" : "bg-[#14243A]"}`}>
              <p className="text-[10px] text-slate-400">{name(m.sender)} · {fmtTime(m.created_at)}</p>
              <p className="whitespace-pre-wrap break-words text-slate-100">{m.body}</p>
            </div>
          ))}
        </div>
        <form onSubmit={send} className="mt-3 flex gap-2">
          <input className="gx-input flex-1 min-w-0" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={active || selected.length ? "Write a message" : "Choose people first"} aria-label="Message" disabled={!active && selected.length === 0} maxLength={4000} />
          <Btn type="submit" disabled={!draft.trim() || (!active && !selected.length)}><Send size={14} /></Btn>
        </form>
        {active && (
          <div className="mt-2 flex flex-wrap gap-3 text-xs">
            <button type="button" className="text-slate-400 hover:text-white" onClick={async () => { try { await api.post(`/community/private-messages/threads/${active}/leave`); toast.success("Left conversation"); setActive(null); qc.invalidateQueries({ queryKey: ["community-pm-threads"] }); } catch (e) { toast.error(errMsg(e)); } }}>Leave group</button>
            {otherParticipant && (
              <button type="button" className="text-red-400 hover:underline" onClick={async () => { try { await api.post(`/community/users/${otherParticipant.user_id}/block`); toast.success("User blocked"); setActive(null); qc.invalidateQueries({ queryKey: ["community-pm-threads"] }); } catch (e) { toast.error(errMsg(e)); } }}>Block user</button>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}

/* ---------------------------- Moderation ------------------------------- */

function ModerationTab() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["community-mod-reports"],
    queryFn: async () => (await api.get("/community/admin/moderation/reports")).data.reports as any[],
  });
  const resolve = async (r: any, action: string) => {
    try {
      await api.post("/community/admin/moderation/resolve", {
        report_id: r.id,
        target_type: r.target_type,
        target_id: r.target_id,
        action,
      });
      toast.success(`Moderation action '${action}' applied`);
      qc.invalidateQueries({ queryKey: ["community-mod-reports"] });
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="space-y-3">
      {q.isLoading ? <Loading /> : (q.data || []).length === 0 ? <Empty title="Clean queue" body="No moderation reports awaiting review." /> : (
        (q.data || []).map((r) => (
          <div key={r.id} className="gx-panel p-4 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <Chip tone={r.status === "open" ? "gold" : "emerald"}>{r.status}</Chip>
              <span className="text-slate-400">{r.target_type} · {r.target_id} · reports: {r.report_count_for_target}</span>
            </div>
            <p className="text-sm text-white">{r.description || r.reason_code}</p>
            <div className="flex flex-wrap gap-2">
              <Btn onClick={() => resolve(r, "hide")}>Hide Content</Btn>
              <Btn variant="secondary" onClick={() => resolve(r, "restore")}>Restore</Btn>
              <Btn variant="ghost" onClick={() => resolve(r, "dismiss")}>Dismiss Report</Btn>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

/* -------------------------------- Page --------------------------------- */

export default function CommunityPage() {
  const { user } = useAuth();
  const { clubs } = useActiveClub() as any;
  const [params, setParams] = useSearchParams();
  const isAdmin = String(user?.role || "").toLowerCase() === "admin" || String(user?.role || "").toLowerCase() === "super_admin";
  const allTabs = useMemo(
    () => (isAdmin ? [...TABS, { id: "moderation", label: "Moderation" }] : [...TABS]),
    [isAdmin]
  );
  const tab = (allTabs.find((t) => t.id === params.get("tab"))?.id || "home") as TabId;
  const [dmTarget, setDmTarget] = useState<string | null>(null);
  const viewerId = user?.id as string | undefined;
  const ownedClubs = useMemo(() => (clubs || []).filter((c: any) => c?.club_id), [clubs]);

  return (
    <div data-testid="community-page" className="min-w-0">
      <PageHeader
        eyebrow="Open to every GTEX user"
        title="GTEX Community"
        sub="Talk football, show off clubs, find competitions and meet other managers. No club required."
        action={<Link to="/app/inbox" className="gx-btn gx-btn-secondary text-xs"><Users size={13} /> Club Owner Inbox (private)</Link>}
      />
      <div role="tablist" aria-label="Community sections" className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {allTabs.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} type="button" data-testid={`community-tab-${t.id}`} onClick={() => setParams({ tab: t.id })} className={`shrink-0 rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wider ${tab === t.id ? "border-[#00C991] bg-[#00C991]/15 text-white" : "border-[#25354B] text-slate-300"}`}>
            {t.id === "moderation" && <ShieldAlert size={12} className="mr-1 inline" />}
            {t.label}
          </button>
        ))}
      </div>
      {tab === "home" && <HomeTab viewerId={viewerId} clubs={ownedClubs} />}
      {tab === "channels" && <ChannelsTab viewerId={viewerId} isAdmin={isAdmin} />}
      {tab === "competitions" && <CompetitionsTab viewerId={viewerId} clubs={ownedClubs} />}
      {tab === "clubs" && <ClubsTab viewerId={viewerId} />}
      {tab === "people" && <PeopleTab viewerId={viewerId} onMessage={(id) => { setDmTarget(id); setParams({ tab: "messages" }); }} />}
      {tab === "messages" && <MessagesTab viewerId={viewerId} startWith={dmTarget} clearStart={() => setDmTarget(null)} />}
      {tab === "moderation" && isAdmin && <ModerationTab />}
    </div>
  );
}

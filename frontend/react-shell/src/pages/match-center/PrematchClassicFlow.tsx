import React, { useState } from "react";

type SheetPlayer = {
  player_id?: string | null;
  player_name?: string | null;
  name?: string | null;
  shirt_number?: number | null;
  role?: string | null;
  line?: string | null;
  rating?: number | null;
  mood?: string | null;
};

type StandingRow = {
  team_id?: string | null;
  team_name?: string;
  position?: number | null;
  played?: number | null;
  points?: number | null;
  goal_difference?: number | null;
  form?: string | null;
};

type ReactionCard = {
  source?: string;
  headline?: string;
  detail?: string;
  sentiment?: string | null;
};

type TalkTarget = "room" | "defenders" | "midfielders" | "attackers" | "individuals";

function displayName(player: SheetPlayer): string {
  return String(player.player_name || player.name || "").trim();
}

function band(player: SheetPlayer): "def" | "mid" | "att" | "gk" {
  const raw = `${player.line || ""} ${player.role || ""}`.toLowerCase();
  if (/gk|goal/.test(raw)) return "gk";
  if (/att|forward|str|wing/.test(raw)) return "att";
  if (/mid/.test(raw)) return "mid";
  if (/def|back/.test(raw)) return "def";
  return "mid";
}

function roleChip(player: SheetPlayer): string {
  const raw = `${player.role || ""} ${player.line || ""}`.toLowerCase();
  if (/gk|goal/.test(raw)) return "GK";
  if (/wing/.test(raw)) return "W";
  if (/full|back/.test(raw) && /def|back/.test(raw)) return "FB";
  if (/def|back/.test(raw)) return "CB";
  if (/attacking mid|\bam\b/.test(raw)) return "AM";
  if (/defensive mid|\bdm\b/.test(raw)) return "DM";
  if (/mid/.test(raw)) return "CM";
  if (/str|forward|att/.test(raw)) return "ST";
  return "XI";
}

function DressingRoomBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 bg-[#1c140f]" />
      <div className="absolute inset-y-0 left-0 w-[18%] bg-[repeating-linear-gradient(90deg,#3a2418_0_18px,#2a1a12_18px_28px)] opacity-80" />
      <div className="absolute inset-y-0 right-0 w-[18%] bg-[repeating-linear-gradient(90deg,#3a2418_0_18px,#2a1a12_18px_28px)] opacity-80" />
      <div className="absolute bottom-[18%] left-[12%] right-[12%] h-16 rounded-md bg-[#4a3424]" />
      <div className="absolute bottom-[14%] left-[16%] right-[16%] h-3 bg-[#2a2118]" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-transparent to-black/55" />
    </div>
  );
}

function StadiumBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 bg-[#8eb4d6]" />
      <div className="absolute left-0 right-0 top-[8%] h-[28%] bg-[repeating-linear-gradient(90deg,#b91c1c_0_14px,#1d4ed8_14px_28px,#e2e8f0_28px_34px)] opacity-80" />
      <div className="absolute left-0 right-0 top-[38%] h-8 bg-[#cbd5e1]" />
      <div className="absolute bottom-0 left-0 right-0 top-[46%] bg-[repeating-linear-gradient(90deg,#15803d_0_42px,#166534_42px_84px)]" />
      <div className="absolute bottom-[18%] left-1/2 h-24 w-24 -translate-x-1/2 rounded-full border-4 border-white/70" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/25" />
    </div>
  );
}

function PlayerTalkCard({ player }: { player: SheetPlayer }) {
  const name = displayName(player);
  if (!name) return null;
  return (
    <div className="flex min-w-[180px] items-center gap-2 rounded-md border border-white/10 bg-[#10192b]/95 px-2 py-1.5 text-white shadow-none">
      <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-black text-sky-200">{roleChip(player)}</span>
      <div className="min-w-0">
        <div className="truncate text-xs font-bold">{name}</div>
        <div className="text-[10px] uppercase tracking-wide text-slate-400">{player.role || player.line || "Squad"}</div>
      </div>
      {player.mood ? (
        <span className="ml-auto rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-200">
          {player.mood}
        </span>
      ) : null}
    </div>
  );
}

export function PrematchClassicFlow({
  homeName,
  awayName,
  homeColor = "#38bdf8",
  awayColor = "#f43f5e",
  homePlayers = [],
  awayPlayers = [],
  homeBench = [],
  awayBench = [],
  competitionName,
  venueName,
  kickoffLabel,
  refereeName,
  standings = [],
  reactions = [],
  storylines = [],
  coachNotes = [],
  homeForm = [],
  awayForm = [],
  onKickOff,
}: {
  homeName: string;
  awayName: string;
  homeColor?: string;
  awayColor?: string;
  homePlayers?: SheetPlayer[];
  awayPlayers?: SheetPlayer[];
  homeBench?: SheetPlayer[];
  awayBench?: SheetPlayer[];
  competitionName?: string | null;
  venueName?: string | null;
  kickoffLabel?: string | null;
  refereeName?: string | null;
  standings?: StandingRow[];
  reactions?: ReactionCard[];
  storylines?: string[];
  coachNotes?: string[];
  homeForm?: string[];
  awayForm?: string[];
  onKickOff?: () => void;
}) {
  const [view, setView] = useState<"news" | "talk" | "table">("news");
  const [talkTarget, setTalkTarget] = useState<TalkTarget>("room");
  const [addressed, setAddressed] = useState<string | null>(null);

  const homeXi = homePlayers.filter((p) => displayName(p)).slice(0, 11);
  const awayXi = awayPlayers.filter((p) => displayName(p)).slice(0, 11);
  const staffNotes = reactions.filter((card) => /staff|coach|desk/i.test(String(card.source || "")));
  const pressNotes = reactions.filter((card) => /press|fan|media/i.test(String(card.source || "")));
  const talkPool = homeXi.length ? homeXi : awayXi;
  const grouped = {
    gk: talkPool.filter((p) => band(p) === "gk"),
    def: talkPool.filter((p) => band(p) === "def"),
    mid: talkPool.filter((p) => band(p) === "mid"),
    att: talkPool.filter((p) => band(p) === "att"),
  };
  const talkLine =
    addressed ||
    coachNotes.find((note) => note.trim()) ||
    (talkTarget === "room"
      ? "The room is waiting for the team talk."
      : `Ready to speak to the ${talkTarget}.`);

  const views = [
    { id: "news" as const, label: "TEAM NEWS" },
    { id: "talk" as const, label: "TEAM TALK" },
    { id: "table" as const, label: "TABLE" },
  ];

  return (
    <section data-testid="prematch-classic-flow" className="overflow-hidden rounded-md border border-white/10">
      <div className="flex items-center justify-between gap-2 bg-[#07111f] px-3 py-2 text-white">
        <div className="text-xs font-black uppercase tracking-[0.18em]">
          {view === "news" ? "Team News" : view === "talk" ? "Team Talk" : "Pre-Match"}
        </div>
        <div className="flex gap-1">
          {views.map((item) => (
            <button
              key={item.id}
              type="button"
              data-testid={`prematch-view-${item.id}`}
              onClick={() => setView(item.id)}
              className={`rounded px-2 py-1 text-[10px] font-black tracking-wider ${
                view === item.id ? "bg-white text-slate-950" : "bg-white/10 text-slate-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {view === "table" ? (
        <div className="relative min-h-[560px]">
          <StadiumBackdrop />
          <div className="relative z-10 mx-auto mt-8 w-[min(440px,92%)] bg-white text-slate-900 shadow-none">
            <div className="bg-[#123a73] px-3 py-2 text-center text-[11px] font-black uppercase tracking-[0.2em] text-white">
              {competitionName || "Competition"}
            </div>
            <table className="w-full text-[11px]" data-testid="prematch-league-table">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="px-2 py-1">Pos</th>
                  <th className="px-2 py-1">Team</th>
                  <th className="px-2 py-1">Pld</th>
                  <th className="px-2 py-1">GD</th>
                  <th className="px-2 py-1">Pts</th>
                </tr>
              </thead>
              <tbody>
                {standings.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                      The competition table has not been filed for this match.
                    </td>
                  </tr>
                ) : (
                  standings.map((row) => {
                    const involved =
                      row.team_name === homeName || row.team_name === awayName;
                    return (
                      <tr key={`${row.position}-${row.team_name}`} className={involved ? "bg-emerald-100" : ""}>
                        <td className="px-2 py-1 font-bold">{row.position ?? "—"}</td>
                        <td className="px-2 py-1 font-semibold">{row.team_name}</td>
                        <td className="px-2 py-1">{row.played ?? "—"}</td>
                        <td className="px-2 py-1">{row.goal_difference ?? "—"}</td>
                        <td className="px-2 py-1 font-black">{row.points ?? "—"}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
            <div className="flex items-center justify-between bg-[#0f172a] px-3 py-2 text-[10px] uppercase tracking-wider text-slate-300">
              <span>{venueName || "Venue not filed"}</span>
              <span>{kickoffLabel || ""}</span>
            </div>
          </div>
          {(homeForm.length > 0 || awayForm.length > 0 || storylines[0]) && (
            <div className="relative z-10 mx-6 mt-4 rounded bg-[#e11d48] px-3 py-2 text-center text-xs font-semibold text-white">
              {storylines[0] ||
                `${homeName} ${homeForm.join(" ") || "form not filed"} · ${awayName} ${awayForm.join(" ") || "form not filed"}`}
            </div>
          )}
          {onKickOff && (
            <div className="relative z-10 flex justify-end p-4">
              <button
                type="button"
                data-testid="prematch-kickoff"
                onClick={onKickOff}
                className="rounded bg-[#0ea5a0] px-4 py-2 text-xs font-black uppercase tracking-wider text-white"
              >
                Kick off
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="relative min-h-[620px]">
          <DressingRoomBackdrop />
          {view === "news" ? (
            <div className="relative z-10 grid gap-3 p-4 lg:grid-cols-[220px_minmax(0,1fr)_240px]">
              <aside className="rounded-md bg-[#0b3a4a]/95 p-3 text-white" data-testid="prematch-staff-column">
                <h3 className="text-[11px] font-black uppercase tracking-[0.16em] text-cyan-200">Staff notes</h3>
                <ul className="mt-3 space-y-2 text-xs">
                  {staffNotes.length === 0 && coachNotes.length === 0 ? (
                    <li className="text-slate-300">No staff notes have been filed.</li>
                  ) : (
                    [...coachNotes.map((detail) => ({ source: "Coach", detail })), ...staffNotes].slice(0, 8).map((note, index) => (
                      <li key={`${note.source}-${index}`} className="border-b border-white/10 pb-2">
                        <div className="font-bold">{note.source || "Staff"}</div>
                        <div className="text-slate-200">{note.detail}</div>
                      </li>
                    ))
                  )}
                </ul>
              </aside>
              <div className="bg-white text-slate-900" data-testid="prematch-official-roster">
                <div className="flex items-center justify-between bg-[#123a73] px-3 py-2 text-white">
                  <span className="text-[11px] font-black uppercase tracking-[0.16em]">Official roster</span>
                  <span className="text-[10px] uppercase">{competitionName || "Matchday"}</span>
                </div>
                <div className="grid grid-cols-2 gap-0 text-[12px]">
                  <RosterColumn title={homeName} color={homeColor} players={homeXi} bench={homeBench} />
                  <RosterColumn title={awayName} color={awayColor} players={awayXi} bench={awayBench} />
                </div>
                <div className="border-t border-slate-200 px-3 py-2 text-[11px] text-slate-600">
                  {refereeName ? `Referee: ${refereeName}` : "Referee not filed"}
                  {venueName ? ` · ${venueName}` : ""}
                </div>
              </div>
              <aside className="rounded-md bg-[#10192b]/95 p-3 text-white" data-testid="prematch-press-column">
                <h3 className="text-[11px] font-black uppercase tracking-[0.16em] text-rose-200">Press desk</h3>
                <ul className="mt-3 space-y-3 text-xs">
                  {pressNotes.length === 0 && storylines.length === 0 ? (
                    <li className="text-slate-300">No press copy has been filed.</li>
                  ) : (
                    (pressNotes.length ? pressNotes : storylines.map((detail) => ({ source: "Desk", headline: "Match note", detail }))).slice(0, 4).map((note, index) => (
                      <li key={`${note.headline}-${index}`}>
                        <div className="font-black">{note.source}</div>
                        <div className="mt-1 text-slate-200">{note.detail || note.headline}</div>
                      </li>
                    ))
                  )}
                </ul>
              </aside>
            </div>
          ) : (
            <div className="relative z-10 grid min-h-[620px] gap-3 p-3 lg:grid-cols-[220px_minmax(0,1fr)_220px]" data-testid="prematch-team-talk">
              <div className="flex flex-col gap-2">
                {grouped.def.map((player) => (
                  <PlayerTalkCard key={String(player.player_id || displayName(player))} player={player} />
                ))}
                {grouped.gk.map((player) => (
                  <PlayerTalkCard key={String(player.player_id || displayName(player))} player={player} />
                ))}
              </div>
              <div className="flex flex-col items-center justify-center">
                <div className="mb-3 flex flex-wrap justify-center gap-1">
                  {([
                    ["room", "Room"],
                    ["defenders", "Defenders"],
                    ["midfielders", "Midfielders"],
                    ["attackers", "Attackers"],
                    ["individuals", "Individuals"],
                  ] as const).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => {
                        setTalkTarget(id);
                        setAddressed(null);
                      }}
                      className={`rounded px-2 py-1 text-[10px] font-black uppercase tracking-wider ${
                        talkTarget === id ? "bg-cyan-400 text-slate-950" : "bg-black/50 text-white"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="w-full max-w-md rounded-md bg-[#0b1220]/92 px-4 py-8 text-center text-white">
                  <p className="text-sm font-semibold">{talkLine}</p>
                  <button
                    type="button"
                    data-testid="prematch-send-talk"
                    onClick={() => setAddressed(`Addressed the ${talkTarget}.`)}
                    className="mt-4 rounded bg-white px-3 py-1.5 text-[11px] font-black uppercase tracking-wider text-slate-950"
                  >
                    Send talk
                  </button>
                </div>
                <div className="mt-3 text-[11px] font-bold uppercase tracking-wider text-white">
                  {addressed ? "Talk delivered" : "Talk open"}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                {(talkTarget === "attackers" ? grouped.att : talkTarget === "midfielders" ? grouped.mid : [...grouped.att, ...grouped.mid]).map((player) => (
                  <PlayerTalkCard key={String(player.player_id || displayName(player))} player={player} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function RosterColumn({
  title,
  color,
  players,
  bench,
}: {
  title: string;
  color: string;
  players: SheetPlayer[];
  bench: SheetPlayer[];
}) {
  return (
    <div className="border-r border-slate-200 px-3 py-2 last:border-r-0">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-[11px] font-black uppercase">{title}</span>
      </div>
      {players.length === 0 ? (
        <p className="text-[11px] text-slate-500">Starting XI not filed.</p>
      ) : (
        <ol className="space-y-0.5">
          {players.map((player) => (
            <li key={String(player.player_id || displayName(player))} className="flex justify-between gap-2">
              <span className="truncate">{displayName(player)}</span>
              <span className="font-mono text-slate-500">{player.shirt_number ?? ""}</span>
            </li>
          ))}
        </ol>
      )}
      {bench.length > 0 && (
        <div className="mt-3 border-t border-slate-200 pt-2">
          <div className="text-[10px] font-black uppercase tracking-wider text-slate-500">Substitutes</div>
          {bench.slice(0, 7).map((player) => (
            <div key={String(player.player_id || displayName(player))} className="flex justify-between text-[11px]">
              <span className="truncate">{displayName(player)}</span>
              <span className="font-mono text-slate-500">{player.shirt_number ?? ""}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

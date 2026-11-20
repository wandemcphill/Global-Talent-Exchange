import React from "react";

type StillPerson = {
  name: string;
  role: string;
  detail?: string;
  portraitUrl?: string | null;
  rating?: string | number | null;
};

const PLATES: Record<string, { src: string; eyebrow: string; title: string; focus: number }> = {
  manager_arrival: {
    src: "/presentation/manager-arrival.jpg",
    eyebrow: "Official appointment",
    title: "Manager arrival",
    focus: 0,
  },
  signing_walkout: {
    src: "/presentation/signing-walkout.jpg",
    eyebrow: "Contract desk",
    title: "Signing walkout",
    focus: 0,
  },
  world_gala: {
    src: "/presentation/awards-gala.jpg",
    eyebrow: "Gala night",
    title: "Awards gala",
    focus: 0,
  },
  luxury_turntable: {
    src: "/presentation/luxury-vault.jpg",
    eyebrow: "Club vault",
    title: "Luxury vault",
    focus: 1,
  },
  boardroom_clash: {
    src: "/presentation/boardroom.jpg",
    eyebrow: "Board in session",
    title: "Boardroom",
    focus: 1,
  },
  club_takeover: {
    src: "/presentation/stadium-night.jpg",
    eyebrow: "The club",
    title: "Club takeover",
    focus: 0,
  },
  facility_upgrade: {
    src: "/presentation/academy-pitch.jpg",
    eyebrow: "The campus",
    title: "Stadium campus",
    focus: 2,
  },
  competition_final: {
    src: "/presentation/finals-plinth.jpg",
    eyebrow: "Matchday",
    title: "Finals night",
    focus: 0,
  },
  private_jet_flex: {
    src: "/presentation/executive-jet.jpg",
    eyebrow: "Arrival",
    title: "Executive flight",
    focus: 0,
  },
  bloodline: {
    src: "/presentation/academy-pitch.jpg",
    eyebrow: "Dynasty bloodline",
    title: "The heir",
    focus: 0,
  },
};

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.slice(0, 1).toUpperCase())
    .join("");
}

function Portrait({ person, className }: { person: StillPerson; className: string }) {
  if (person.portraitUrl) {
    return (
      <img src={person.portraitUrl} alt="" className={`${className} object-cover object-top`} />
    );
  }
  return (
    <div
      className={`${className} flex items-center justify-center bg-[linear-gradient(160deg,#1a2433,#07090d)] text-white/80`}
    >
      <span className="font-black tracking-tight">{initials(person.name) || "GT"}</span>
    </div>
  );
}

function RatingMark({ value, label }: { value?: string | number | null; label: string }) {
  if (value == null || value === "") return null;
  return (
    <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-full border border-amber-300/80 bg-black/70 shadow-[0_0_0_4px_rgba(0,0,0,0.35)]">
      <b className="text-lg font-black leading-none text-white">{value}</b>
      <span className="mt-0.5 text-[8px] font-bold uppercase tracking-[0.16em] text-amber-200">
        {label}
      </span>
    </div>
  );
}

export function VogueStaffStill({
  kicker,
  clubName,
  person,
  people,
  quote,
  scene = "manager_arrival",
  ratingLabel = "IDX",
}: {
  kicker?: string;
  clubName: string;
  person?: StillPerson;
  people?: StillPerson[];
  quote?: string;
  scene?: string;
  ratingLabel?: string;
}) {
  const plate = PLATES[scene] || PLATES.manager_arrival;
  const roster = people && people.length > 0 ? people : person ? [person] : [];
  const focus = Math.min(plate.focus, Math.max(roster.length - 1, 0));
  const lead = roster[focus] || person || { name: "Not appointed", role: "Club staff" };
  const rail = roster.filter((_, index) => index !== focus);
  return (
    <article
      data-testid="vogue-staff-still"
      className="relative min-h-[440px] overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl"
    >
      <img src={plate.src} alt="" className="absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(2,6,12,0.94)_0%,rgba(2,6,12,0.78)_42%,rgba(2,6,12,0.28)_100%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.15),transparent_30%,rgba(0,0,0,0.72))]" />
      <div className="relative flex min-h-[440px] flex-col justify-between p-5 sm:p-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.42em] text-amber-300">
              {kicker || plate.eyebrow}
            </p>
            <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-white/70">
              {clubName}
            </p>
          </div>
          <p className="rounded-sm border border-white/20 bg-black/40 px-2 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-white">
            GTEX
          </p>
        </div>

        <div className="grid items-end gap-6 lg:grid-cols-[minmax(0,1fr)_240px]">
          <div className="flex max-w-3xl items-end gap-4">
            <Portrait
              person={lead}
              className="hidden h-36 w-28 rounded-md border border-white/20 text-3xl shadow-2xl sm:flex"
            />
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.32em] text-amber-200/90">
                {plate.title}
              </p>
              <h3 className="gx-display mt-2 max-w-4xl text-4xl font-black uppercase leading-[0.9] text-white sm:text-6xl">
                {lead.name}
              </h3>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <span className="rounded-sm border border-amber-300/70 bg-amber-300/10 px-2.5 py-1 text-[11px] font-black uppercase tracking-[0.18em] text-amber-100">
                  {lead.role}
                </span>
                <RatingMark value={lead.rating} label={ratingLabel} />
              </div>
              <p className="mt-4 max-w-xl text-sm leading-6 text-slate-200">
                {lead.detail || quote || "On the club record."}
              </p>
              {quote ? (
                <p className="mt-3 max-w-lg border-l-2 border-amber-300/80 pl-3 text-sm italic text-amber-50/90">
                  {quote}
                </p>
              ) : null}
            </div>
          </div>

          {rail.length > 0 ? (
            <div className="space-y-2 rounded-xl border border-white/10 bg-black/55 p-2 backdrop-blur-md">
              <p className="px-2 pt-1 text-[9px] font-black uppercase tracking-[0.28em] text-slate-400">
                Club desk
              </p>
              {rail.map((colleague) => (
                <div
                  key={`${colleague.role}-${colleague.name}`}
                  className="flex items-center gap-3 rounded-lg bg-white/5 p-2"
                >
                  <Portrait person={colleague} className="h-12 w-12 rounded-md text-sm" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-white">{colleague.name}</p>
                    <p className="truncate text-[10px] uppercase tracking-[0.14em] text-slate-400">
                      {colleague.role}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function potentialNumber(potential: unknown): number | null {
  if (typeof potential === "number" && Number.isFinite(potential)) return potential;
  if (potential && typeof potential === "object") {
    const record = potential as Record<string, unknown>;
    const value = record.high ?? record.ceiling ?? record.max ?? record.potential;
    return typeof value === "number" ? value : null;
  }
  return null;
}

export function AcademyPortraitWall({
  clubName,
  players,
}: {
  clubName: string;
  players: Array<{
    id?: string;
    name?: string;
    position?: string;
    rating?: number;
    potential?: unknown;
    portrait_url?: string | null;
    age?: number;
  }>;
}) {
  const shown = players.slice(0, 8);
  return (
    <section
      data-testid="academy-portrait-wall"
      className="relative overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl"
    >
      <img
        src="/presentation/academy-pitch.jpg"
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(2,8,6,0.82),rgba(2,8,6,0.92))]" />
      <div className="relative p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.38em] text-emerald-300">
              Youth intake
            </p>
            <h3 className="gx-display mt-1 text-3xl font-black uppercase text-white sm:text-4xl">
              {clubName}
            </h3>
          </div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
            {players.length} regen{players.length === 1 ? "" : "s"} on the books
          </p>
        </div>
        {shown.length === 0 ? (
          <p className="rounded-xl border border-dashed border-white/15 bg-black/30 px-4 py-14 text-center text-sm text-slate-300">
            No academy players yet. Scout an intake and their portraits will sit on this pitch.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {shown.map((player) => {
              const name = player.name || "Academy player";
              const potential = potentialNumber(player.potential);
              const rating = typeof player.rating === "number" ? player.rating : null;
              const person = {
                name,
                role: player.position || "Youth",
                portraitUrl: player.portrait_url,
              };
              return (
                <figure
                  key={player.id || name}
                  className="overflow-hidden rounded-xl border border-white/10 bg-black/50 shadow-lg"
                >
                  <div className="relative aspect-[3/4]">
                    <Portrait person={person} className="h-full w-full text-3xl" />
                    <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black via-black/70 to-transparent" />
                    <span className="absolute left-2 top-2 rounded-sm bg-amber-300 px-1.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-slate-950">
                      {player.position || "Youth"}
                    </span>
                    {player.age ? (
                      <span className="absolute right-2 top-2 rounded-sm bg-black/70 px-1.5 py-0.5 text-[10px] font-bold text-white">
                        {player.age}
                      </span>
                    ) : null}
                    {rating != null ? (
                      <div className="absolute bottom-2 right-2 flex h-12 w-12 flex-col items-center justify-center rounded-full border border-emerald-300/80 bg-black/80">
                        <b className="text-base font-black leading-none text-white">{rating}</b>
                        <span className="text-[8px] font-bold uppercase tracking-widest text-emerald-200">
                          OVR
                        </span>
                      </div>
                    ) : null}
                    <figcaption className="absolute inset-x-0 bottom-2 left-2 right-16 pr-2">
                      <p className="truncate text-sm font-black uppercase text-white">{name}</p>
                    </figcaption>
                  </div>
                  <div className="space-y-1 px-2 py-2">
                    <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      <span>Potential</span>
                      <span className="text-amber-200">{potential ?? "—"}</span>
                    </div>
                    <div className="h-1 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full bg-gradient-to-r from-emerald-400 to-amber-300"
                        style={{
                          width: `${Math.max(8, Math.min(potential || rating || 40, 99))}%`,
                        }}
                      />
                    </div>
                  </div>
                </figure>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

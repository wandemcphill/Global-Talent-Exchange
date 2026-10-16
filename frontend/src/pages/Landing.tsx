import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpenCheck, Building2, Coins, Gauge, ShieldCheck, Shirt, Sprout, Trophy, Users } from "lucide-react";
import { useAuth } from "@/lib/auth";

const CLARITY = [
  { icon: Building2, t: "You own a football club", d: "Up to three clubs in a persistent football world." },
  { icon: Users, t: "Players, a manager, facilities, money and fans", d: "Every club runs on real squad, staff and economy systems." },
  { icon: Gauge, t: "Your decisions move the club", d: "Approve spend, answer your manager, sell or keep talent. Growth, results and earnings follow." },
  { icon: Trophy, t: "A football ownership world", d: "Competitions, rivalries and regens with their own ambitions. Not a trading app." },
];

const LOOP = [
  { icon: Shirt, n: "01", t: "Sign players", d: "Acquire a starting squad to activate your club." },
  { icon: BookOpenCheck, n: "02", t: "Appoint a manager", d: "Hire a football brain with real traits and demands." },
  { icon: Sprout, n: "03", t: "Build facilities", d: "Training, academy, medical and stadium shape growth." },
  { icon: Trophy, n: "04", t: "Enter competitions", d: "GTEX-hosted leagues and cups, or host your own." },
  { icon: Coins, n: "05", t: "Grow club value", d: "Gate receipts, prizes and sponsors, all on one ledger." },
];

function Hero() {
  const { user } = useAuth();
  return (
    <section className="gx-noise relative min-h-[92vh] overflow-hidden">
      <img src="/img/hero.jpg" alt="Floodlit stadium" className="absolute inset-0 h-full w-full object-cover opacity-40" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#070B11] via-[#070B11]/85 to-[#070B11]/30" />
      <div className="gx-pitch-grid absolute inset-0 opacity-60" />
      <div className="relative mx-auto flex max-w-[1400px] flex-col px-6 pb-20 pt-8 sm:px-10">
        <nav className="flex items-center justify-between">
          <p className="gx-display text-3xl font-black text-white">GTEX</p>
          <div className="flex items-center gap-3">
            <Link to={user ? "/app" : "/login"} data-testid="landing-login-link" className="gx-btn gx-btn-ghost">
              {user ? "Open console" : "Sign in"}
            </Link>
            <Link to="/signup" data-testid="landing-nav-signup" className="gx-btn gx-btn-secondary">
              Claim a club
            </Link>
          </div>
        </nav>
        <div className="mt-24 max-w-3xl gx-rise">
          <p className="gx-eyebrow mb-5">Club-owner simulator · Launching in Nigeria</p>
          <h1 className="gx-h1">
            Own the club.
            <br />
            Hire the football brain.
            <br />
            <span className="text-emerald-400">Build a dynasty.</span>
          </h1>
          <p className="mt-6 max-w-xl text-base text-slate-300">
            GTEX is a living football world where you buy players to activate your club, appoint a manager with a real personality, upgrade facilities, enter competitions and grow club value.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link to={user ? "/app" : "/signup"} data-testid="landing-activate-club-cta" className="gx-btn gx-btn-primary px-6 py-3 text-sm">
              Activate my first club <ArrowRight size={16} />
            </Link>
            <a href="#how" className="gx-btn gx-btn-secondary px-6 py-3 text-sm">
              How ownership works
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function Clarity() {
  return (
    <section className="mx-auto -mt-24 max-w-[1400px] px-6 sm:px-10">
      <div className="relative grid gap-px overflow-hidden rounded-md border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
        {CLARITY.map((c, i) => (
          <div key={c.t} className="gx-rise bg-slate-950/95 p-6 backdrop-blur-xl" style={{ animationDelay: `${i * 80}ms` }}>
            <c.icon className="mb-4 text-emerald-400" size={22} />
            <p className="gx-display text-xl font-bold uppercase text-white">{c.t}</p>
            <p className="mt-2 text-sm text-slate-400">{c.d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Loop() {
  return (
    <section id="how" className="mx-auto max-w-[1400px] px-6 py-28 sm:px-10">
      <p className="gx-eyebrow mb-3">The owner loop</p>
      <h2 className="gx-h2 max-w-xl">One obvious loop. Endless consequences.</h2>
      <div className="mt-12 grid gap-4 md:grid-cols-5">
        {LOOP.map((s) => (
          <div key={s.n} className="group rounded-md border border-white/[0.08] bg-slate-900/40 p-5 transition-colors hover:border-emerald-500/40">
            <div className="flex items-center justify-between">
              <s.icon size={20} className="text-emerald-400" />
              <span className="gx-mono text-xs text-slate-600">{s.n}</span>
            </div>
            <p className="gx-display mt-6 text-lg font-bold uppercase text-white">{s.t}</p>
            <p className="mt-1 text-sm text-slate-400">{s.d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Boardroom() {
  return (
    <section className="mx-auto grid max-w-[1400px] gap-10 px-6 pb-28 sm:px-10 lg:grid-cols-12">
      <div className="relative overflow-hidden rounded-md border border-white/10 lg:col-span-7">
        <img src="/img/boardroom.jpg" alt="Executive boardroom" className="h-full max-h-[460px] w-full object-cover opacity-70" />
        <div className="absolute inset-x-4 bottom-4 rounded-sm border border-white/10 bg-slate-950/85 p-4 backdrop-blur-xl">
          <p className="gx-eyebrow text-amber-400">Owner Inbox · Manager request</p>
          <p className="mt-2 text-sm text-slate-200">"Boss, the training ground is holding our young lads back. Level 2 costs 15,157 GTEX Coin. Give me the tools and I'll give you a first-team regen by the spring."</p>
          <div className="mt-3 flex gap-2">
            <span className="gx-btn gx-btn-primary pointer-events-none">Approve spend</span>
            <span className="gx-btn gx-btn-ghost pointer-events-none">Reject</span>
          </div>
        </div>
      </div>
      <div className="flex flex-col justify-center lg:col-span-5">
        <p className="gx-eyebrow mb-3">Owner Control Center</p>
        <h2 className="gx-h2">Every screen tells you what happened, why, and what to do next.</h2>
        <ul className="mt-6 space-y-3 text-sm text-slate-300">
          <li>Managers ask for budget, request players by role, and react to poor facilities.</li>
          <li>Regens have ambition, loyalty and marketability, and they grow (or leave) based on your environment.</li>
          <li>Matches play out in a 2D live feed with momentum and post-match explanation. You set the mentality, not the touchline.</li>
        </ul>
      </div>
    </section>
  );
}

function Trust() {
  const items = [
    ["One unified ledger", "Every coin movement (entry fees, prizes, sponsor splits, gifts, withdrawals) is written once with gross, fee and net."],
    ["Balances you can read", "Withdrawable, non-withdrawable, earned, deposited, promotional and pending review, always labelled."],
    ["Fair multi-club play", "Same-owner clubs are routed apart in prize brackets; related-party transfers must sit inside a fair-value band and are disclosed."],
    ["Support, not speculation", "Club Support Units give supporter status and perks. They are not shares, investments or a promise of returns."],
  ];
  return (
    <section className="border-y border-white/[0.06] bg-slate-950/60">
      <div className="mx-auto max-w-[1400px] px-6 py-24 sm:px-10">
        <div className="flex items-center gap-3">
          <ShieldCheck className="text-emerald-400" />
          <p className="gx-eyebrow">Money, compliance & trust</p>
        </div>
        <div className="mt-10 grid gap-8 md:grid-cols-4">
          {items.map(([t, d]) => (
            <div key={t}>
              <p className="gx-display text-lg font-bold uppercase text-white">{t}</p>
              <p className="mt-2 text-sm text-slate-400">{d}</p>
            </div>
          ))}
        </div>
        <p className="mt-10 text-xs text-slate-500">Naira deposits via Paystack. Withdrawals are subject to eligibility checks, KYC thresholds and fraud review. Two currencies: GTEX Coin (club economy) and Fan Coin (gifting and fan actions, non-withdrawable).</p>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <div data-testid="landing-page" className="min-h-screen bg-[#070B11]">
      <Hero />
      <Clarity />
      <Loop />
      <Boardroom />
      <Trust />
      <section className="relative overflow-hidden">
        <img src="/img/crowd.jpg" alt="Stadium crowd" className="absolute inset-0 h-full w-full object-cover opacity-25" />
        <div className="relative mx-auto max-w-[1400px] px-6 py-28 sm:px-10">
          <h2 className="gx-h1 max-w-3xl">The home end is waiting for an owner.</h2>
          <Link to="/signup" data-testid="landing-footer-cta" className="gx-btn gx-btn-primary mt-10 px-6 py-3 text-sm">
            Activate my first club <ArrowRight size={16} />
          </Link>
        </div>
      </section>
      <footer className="mx-auto max-w-[1400px] px-6 py-8 text-xs text-slate-600 sm:px-10">© {new Date().getFullYear()} GTEX · Global Talent Exchange</footer>
    </div>
  );
}

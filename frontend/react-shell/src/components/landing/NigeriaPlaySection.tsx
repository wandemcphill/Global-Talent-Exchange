import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Building2, Coins, Dna, ShieldCheck, Trophy, Users } from "lucide-react";

const pillars = [
  {
    icon: Coins,
    title: "Buy and sell coins in naira",
    body: "Verified coin traders in Nigeria publish buy and sell desks for GTEX Coin and Fan Coin. Orders lock in canonical escrow. Naira rails include bank transfer, OPay, PalmPay, and Kuda. Discovery can be narrowed to Nigerian desks.",
  },
  {
    icon: Building2,
    title: "Create a club in foundation",
    body: "A new club starts in foundation. Promotion and relegation are the only way up. League entry is free. The owner already owns the club. The 3D operations centre is the daily desk for staff, facilities, and matchday decisions.",
  },
  {
    icon: Dna,
    title: "Academy, regens, and Build a Son",
    body: "Youth intake feeds the academy pipeline. A Build a Son order keeps the parent's surname, position, foot, and DNA unless you pay to change them, then the heir joins that club's reserve squad.",
  },
  {
    icon: Trophy,
    title: "National teams are free to enter",
    body: "Club competitions and national-team competitions have no buy-in. For a national team, the squad rental is the only cost. Prize coin is funded by GTEX.",
  },
  {
    icon: Users,
    title: "Player purchase and sales",
    body: "Active players trade as share markets. Legends are one of one: a single share, marked ICON · 1 OF 1, and no extra shares are minted after a purchase. Archived duplicate records stay off the market.",
  },
  {
    icon: ShieldCheck,
    title: "Lagos, publicly listed clubs",
    body: "Public club profiles show the squad, academy, and stadium. Coin trader accounts complete identity checks, including Nigerian BVN or NIN where that lane applies.",
  },
];

export const NigeriaPlaySection: React.FC<{ id?: string }> = ({ id = "nigeria" }) => {
  return (
    <section id={id} className="scroll-mt-[158px] bg-[#0B1626] px-6 py-20 sm:px-12" data-testid="nigeria-play-section">
      <div className="mx-auto max-w-[1440px]">
        <p className="font-['Barlow_Condensed'] text-xs font-extrabold uppercase tracking-[0.2em] text-[#36E38A]">
          Nigeria · Lagos · Naira
        </p>
        <h2 className="mt-3 max-w-4xl font-['Barlow_Condensed'] text-4xl font-black uppercase leading-[0.9] tracking-tight text-[#F2F4F8] sm:text-6xl">
          Play GTEX in Nigeria
        </h2>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-[#9AA7BD] sm:text-base">
          Global Talent Exchange is built in Lagos. Create a football club, run the 3D club operations centre,
          develop academy regens, buy and sell players, and enter national team competitions. Coin desks settle
          in Nigerian naira with escrow. Competitions themselves are free to enter.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pillars.map((pillar) => (
            <article
              key={pillar.title}
              className="rounded-2xl border border-[#22385A] bg-[#13233A]/80 p-5"
            >
              <pillar.icon size={18} className="text-[#D4AF37]" />
              <h3 className="mt-3 font-['Barlow_Condensed'] text-xl font-bold uppercase text-[#F2F4F8]">
                {pillar.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[#9AA7BD]">{pillar.body}</p>
            </article>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/signup"
            data-testid="nigeria-signup-cta"
            className="inline-flex items-center gap-2 rounded-lg bg-[#D4AF37] px-6 py-3 font-['Barlow_Condensed'] text-sm font-black uppercase tracking-wider text-[#0B1626] hover:bg-[#E8C766]"
          >
            Create a free account
            <ArrowRight size={16} />
          </Link>
          <Link
            to="/nigeria"
            className="inline-flex items-center gap-2 rounded-lg border border-[#22385A] px-6 py-3 font-['Barlow_Condensed'] text-sm font-bold uppercase tracking-wider text-[#F2F4F8] hover:border-[#D4AF37]/50"
          >
            Nigeria guide
          </Link>
        </div>
      </div>
    </section>
  );
};

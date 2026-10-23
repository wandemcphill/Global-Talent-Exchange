import React from "react";

export const ClarityStrip: React.FC = () => {
  const signals = [
    { title: "PLAYERS", body: "Discover & develop" },
    { title: "CLUBS", body: "Build & manage" },
    { title: "MARKET", body: "Trade & invest" },
    { title: "MATCHDAY", body: "Compete & win" },
    { title: "COMMUNITY", body: "Create & connect" },
  ];

  return (
    <section className="border-y border-[#22385A] bg-[#13233A] py-4">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-center gap-x-8 gap-y-3 px-6 text-center">
        {signals.map((sig) => (
          <div key={sig.title} className="flex items-center gap-2">
            <span className="font-['Barlow_Condensed'] text-xs font-extrabold tracking-wider text-[#D4AF37]">
              {sig.title}
            </span>
            <span className="text-sm font-medium text-[#9AA7BD]">
              {sig.body}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
};

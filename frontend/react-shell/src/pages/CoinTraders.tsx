import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CandlestickChart } from "lucide-react";
import { CoinTraderDesk } from "@/components/gtex/CoinTraderDesk";

export default function CoinTraders() {
  return (
    <div className="space-y-6 p-4 sm:p-8" data-testid="coin-traders-screen">
      <Link
        to="/app"
        className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white"
      >
        <ArrowLeft size={14} /> Back to GTEX
      </Link>
      <section className="relative overflow-hidden rounded-3xl border border-amber-400/25 bg-gradient-to-br from-[#211909] via-[#111522] to-[#070B11] p-6 sm:p-9">
        <div className="flex items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-amber-300/10 text-amber-300">
            <CandlestickChart size={24} />
          </span>
          <div>
            <p className="gx-eyebrow mb-2 text-amber-300">
              User wallet · optional trader capability
            </p>
            <h1 className="gx-display text-3xl font-black uppercase text-white sm:text-4xl">
              Trade GTEX Coin. Apply to operate a desk.
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
              Coin traders are the better-value way to buy and sell GTEX Coin. Buying and selling
              through a verified trader guarantees more value for money than paying the platform
              treasury rate. Members use this desk for their own orders. Running a desk is a
              separate approved application.
            </p>
          </div>
        </div>
      </section>
      <CoinTraderDesk />
    </div>
  );
}

import { AppShell } from "@/components/app-shell";
import { ActionQueue } from "@/components/dashboard/action-queue";
import { NextMatch } from "@/components/dashboard/next-match";
import { PortfolioHero } from "@/components/dashboard/portfolio-hero";
import { Watchlist } from "@/components/dashboard/watchlist";

export const metadata = { title: "Command Center — GTEX Concepts" };

export default function DashboardPage() {
  return (
    <AppShell active="/dashboard">
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Evening, Ayo</p>
          <h1 className="font-display text-4xl font-bold uppercase leading-none">Command center</h1>
        </header>
        <PortfolioHero />
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Watchlist />
          <div className="flex flex-col gap-6">
            <NextMatch />
            <ActionQueue />
          </div>
        </div>
      </div>
    </AppShell>
  );
}

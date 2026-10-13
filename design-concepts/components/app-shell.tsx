import Link from "next/link";
import { Compass, Home, LineChart, Shield, Trophy } from "lucide-react";
import { ConceptNav } from "./concept-nav";
import { MarketTicker } from "./market-ticker";

const productNav = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/discover", label: "Discover", icon: Compass },
  { href: "#", label: "Market", icon: LineChart },
  { href: "#", label: "Club", icon: Shield },
  { href: "#", label: "Match", icon: Trophy },
];

export function AppShell({ active, children }: { active: string; children: React.ReactNode }) {
  return (
    <>
      <ConceptNav active={active} />
      <MarketTicker />
      <div className="mx-auto flex max-w-7xl gap-8 px-4 pb-24 pt-6 md:px-8 md:pb-10">
        <nav aria-label="Product" className="sticky top-20 hidden h-fit w-48 shrink-0 flex-col gap-1 md:flex">
          {productNav.map(({ href, label, icon: Icon }) => {
            const isActive = href === active;
            return (
              <Link
                key={label}
                href={href}
                aria-current={isActive ? "page" : undefined}
                className={
                  isActive
                    ? "flex items-center gap-3 rounded-lg bg-primary/12 px-3 py-2.5 font-medium text-primary"
                    : "flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                }
              >
                <Icon className="size-5" aria-hidden />
                {label}
              </Link>
            );
          })}
        </nav>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
      <nav aria-label="Product mobile" className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-card/95 py-2 backdrop-blur md:hidden">
        {productNav.map(({ href, label, icon: Icon }) => (
          <Link
            key={label}
            href={href}
            aria-current={href === active ? "page" : undefined}
            className={`flex flex-col items-center gap-0.5 px-3 py-1 text-[11px] ${href === active ? "text-primary" : "text-muted-foreground"}`}
          >
            <Icon className="size-5" aria-hidden />
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}

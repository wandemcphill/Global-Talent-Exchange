import Link from "next/link";

const links = [
  { href: "/", label: "Audit" },
  { href: "/cards", label: "Cards" },
  { href: "/dashboard", label: "Command Center" },
  { href: "/discover", label: "Discover" },
  { href: "/login", label: "Login" },
  { href: "/signup", label: "Signup" },
];

export function ConceptNav({ active }: { active: string }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
      <nav aria-label="Concept pages" className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3 md:px-8">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid size-7 place-items-center rounded-md bg-primary font-display text-sm font-extrabold text-primary-foreground">
            GT
          </span>
          <span className="hidden font-display text-lg font-bold tracking-wide sm:inline">GTEX</span>
        </Link>
        <ul className="flex flex-1 items-center gap-1 overflow-x-auto text-sm">
          {links.map((link) => {
            const isActive = link.href === active;
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={isActive ? "page" : undefined}
                  className={
                    isActive
                      ? "whitespace-nowrap rounded-md bg-muted px-3 py-1.5 font-medium text-foreground"
                      : "whitespace-nowrap rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:text-foreground"
                  }
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}

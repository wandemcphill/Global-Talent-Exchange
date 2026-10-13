import { formatCoin, tickerItems } from "@/lib/data";

export function MarketTicker() {
  const items = [...tickerItems, ...tickerItems];
  return (
    <div className="overflow-hidden border-y border-border bg-card" aria-label="Live market prices">
      <ul className="flex w-max animate-ticker gap-8 py-2">
        {items.map((item, i) => {
          const up = item.change >= 0;
          return (
            <li key={`${item.label}-${i}`} aria-hidden={i >= tickerItems.length} className="flex items-baseline gap-2 font-display text-sm tracking-wide">
              <span className="font-semibold text-foreground">{item.label}</span>
              <span className="text-accent">{formatCoin(item.value)}</span>
              <span className={up ? "text-primary" : "text-destructive"}>
                {up ? "+" : "-"}
                {Math.abs(item.change).toFixed(1)}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

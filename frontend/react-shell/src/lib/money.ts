import { useSyncExternalStore } from "react";
import { fmt } from "@/lib/owner";

export type CoinKind = "GTEX" | "FAN";

type MoneyRates = {
  nairaPerGtex: number;
  nairaPerFan: number;
  fanPerGtex: number;
};

const DEFAULT_RATES: MoneyRates = {
  nairaPerGtex: 900,
  nairaPerFan: 9,
  fanPerGtex: 100,
};

let rates: MoneyRates = { ...DEFAULT_RATES };
const listeners = new Set<() => void>();

export function setMoneyRates(next: Partial<MoneyRates>) {
  const updated: MoneyRates = {
    nairaPerGtex: Number(next.nairaPerGtex) > 0 ? Number(next.nairaPerGtex) : rates.nairaPerGtex,
    nairaPerFan: Number(next.nairaPerFan) > 0 ? Number(next.nairaPerFan) : rates.nairaPerFan,
    fanPerGtex: Number(next.fanPerGtex) > 0 ? Number(next.fanPerGtex) : rates.fanPerGtex,
  };
  if (
    updated.nairaPerGtex === rates.nairaPerGtex &&
    updated.nairaPerFan === rates.nairaPerFan &&
    updated.fanPerGtex === rates.fanPerGtex
  ) {
    return;
  }
  rates = updated;
  listeners.forEach((listener) => listener());
}

export function getMoneyRates() {
  return rates;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useMoneyRates() {
  return useSyncExternalStore(subscribe, getMoneyRates, getMoneyRates);
}

export function nairaAmount(amount: number | string, currency: CoinKind, source = rates) {
  const value = Number(amount || 0);
  const rate = currency === "FAN" ? source.nairaPerFan : source.nairaPerGtex;
  return value * rate;
}

export function nairaText(amount: number | string, currency: CoinKind) {
  return `₦${fmt(nairaAmount(amount, currency), 2)}`;
}

export function coinWithNaira(amount: number | string, currency: CoinKind) {
  const badge = currency === "FAN" ? "FAN" : "GTX";
  return `${fmt(amount)} ${badge} · ${nairaText(amount, currency)}`;
}

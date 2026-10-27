declare const describe: any;
declare const test: any;
declare const expect: any;

import React from "react";
import { PlayerCard, tierOf, posShort, TIERS, resolvePlayerFallback } from "./PlayerCard";
import { RegenCard, RegenPotentialBar, resolveRegenFallback, formatGtexCoin } from "./RegenCard";

describe("PlayerCard & RegenCard Logic and Element Rendering Suite", () => {
  test("posShort normalizes positions accurately", () => {
    expect(posShort("goalkeeper")).toBe("GK");
    expect(posShort("GK")).toBe("GK");
    expect(posShort("defender")).toBe("DEF");
    expect(posShort("central midfielder")).toBe("CM");
    expect(posShort("striker")).toBe("ST");
    expect(posShort("centre-back")).toBe("CB");
    expect(posShort("attacking midfielder")).toBe("AM");
    expect(posShort(undefined)).toBe("-");
    expect(posShort("")).toBe("-");
  });

  test("tierOf categorizes ratings into Standard, Elite, Legendary and Regen", () => {
    expect(tierOf(94).name).toBe("Legendary");
    expect(tierOf(85).name).toBe("Legendary");
    expect(tierOf(84).name).toBe("Elite");
    expect(tierOf(75).name).toBe("Elite");
    expect(tierOf(74).name).toBe("Standard");
    expect(tierOf(62).name).toBe("Standard");
    expect(tierOf(65, true).name).toBe("Regen");
  });

  test("formatGtexCoin formats thousands, millions, and values cleanly", () => {
    expect(formatGtexCoin(1500000)).toBe("1.50M");
    expect(formatGtexCoin(45000)).toBe("45.0K");
    expect(formatGtexCoin(500)).toBe("500");
    expect(formatGtexCoin(undefined)).toBe("-");
  });

  test("resolvePlayerFallback & resolveRegenFallback select position-specific art", () => {
    expect(resolvePlayerFallback("GK")).toBe("/img/players/keeper.png");
    expect(resolvePlayerFallback("DEF")).toBe("/img/players/defender.png");
    expect(resolvePlayerFallback("CB")).toBe("/img/players/defender.png");
    expect(resolvePlayerFallback("MID")).toBe("/img/players/midfielder.png");
    expect(resolvePlayerFallback("ST")).toBe("/img/players/striker.png");

    expect(resolveRegenFallback("GK")).toBe("/img/players/keeper.png");
    expect(resolveRegenFallback("DEF")).toBe("/img/players/defender.png");
    expect(resolveRegenFallback("MID")).toBe("/img/players/midfielder.png");
    expect(resolveRegenFallback("FWD")).toBe("/img/players/striker.png");
  });

  test("PlayerCard element creation succeeds for all variants", () => {
    const fullElement = React.createElement(PlayerCard, {
      name: "Erling Haaland",
      rating: 91,
      position: "ST",
      nationality: "Norway",
      club: "Manchester City",
      price: 180000000,
      variant: "full",
    });
    expect(fullElement).toBeDefined();
    expect(fullElement.props.name).toBe("Erling Haaland");
    expect(fullElement.props.rating).toBe(91);

    const compactElement = React.createElement(PlayerCard, {
      name: "Bukayo Saka",
      rating: 86,
      position: "RW",
      variant: "compact",
    });
    expect(compactElement).toBeDefined();

    const thumbElement = React.createElement(PlayerCard, {
      name: "Martin Odegaard",
      rating: 88,
      position: "AM",
      variant: "thumbnail",
    });
    expect(thumbElement).toBeDefined();
  });

  test("RegenCard element creation succeeds with tactics board data", () => {
    const regenElement = React.createElement(RegenCard, {
      name: "Tariq Mansoor",
      rating: 72,
      potential: 90,
      position: "AM",
      nationality: "Ghana",
      generation: 2,
      archetype: "Maestro Playmaker",
      variant: "full",
    });
    expect(regenElement).toBeDefined();
    expect(regenElement.props.name).toBe("Tariq Mansoor");
    expect(regenElement.props.generation).toBe(2);

    const barElement = React.createElement(RegenPotentialBar, {
      current: 72,
      low: 86,
      high: 94,
    });
    expect(barElement).toBeDefined();
    expect(barElement.props.current).toBe(72);
  });
});

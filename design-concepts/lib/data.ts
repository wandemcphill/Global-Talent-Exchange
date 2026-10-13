export type Tier = "standard" | "elite" | "legendary";

export type Player = {
  id: string;
  name: string;
  shortName: string;
  position: string;
  club: string;
  nation: string;
  age: number;
  ovr: number;
  gsi: number;
  tier: Tier;
  image: string;
  price: number;
  change: number;
  owned?: number;
  attrs: { PAC: number; SHO: number; PAS: number; DRI: number; DEF: number; PHY: number };
  form: ("W" | "D" | "L")[];
  foot: "Left" | "Right";
  height: string;
  watchers: number;
};

export type Regen = {
  id: string;
  name: string;
  position: string;
  archetype: string;
  nation: string;
  age: number;
  current: number;
  ceiling: [number, number];
  generation: number;
  serial: string;
  lineage: { label: string; detail: string }[];
  traits: string[];
  image: string;
  price: number;
  story: string;
};

export const players: Player[] = [
  {
    id: "p1",
    name: "Kwame Adebayo",
    shortName: "Adebayo",
    position: "ST",
    club: "Lagos Harbour FC",
    nation: "NGA",
    age: 26,
    ovr: 88,
    gsi: 912,
    tier: "legendary",
    image: "/players/striker.png",
    price: 1284.5,
    change: 6.4,
    owned: 2.5,
    attrs: { PAC: 92, SHO: 89, PAS: 78, DRI: 86, DEF: 41, PHY: 84 },
    form: ["W", "W", "D", "W", "W"],
    foot: "Right",
    height: "1.86m",
    watchers: 4120,
  },
  {
    id: "p2",
    name: "Thiago Moreira",
    shortName: "Moreira",
    position: "CM",
    club: "Porto Alegre United",
    nation: "BRA",
    age: 24,
    ovr: 84,
    gsi: 846,
    tier: "elite",
    image: "/players/midfielder.png",
    price: 742.1,
    change: 2.1,
    attrs: { PAC: 79, SHO: 76, PAS: 88, DRI: 87, DEF: 68, PHY: 72 },
    form: ["W", "D", "W", "L", "W"],
    foot: "Left",
    height: "1.78m",
    watchers: 2310,
  },
  {
    id: "p3",
    name: "Erik Lindqvist",
    shortName: "Lindqvist",
    position: "CB",
    club: "Malmö Nord",
    nation: "SWE",
    age: 29,
    ovr: 82,
    gsi: 801,
    tier: "standard",
    image: "/players/defender.png",
    price: 418.0,
    change: -1.8,
    attrs: { PAC: 71, SHO: 44, PAS: 70, DRI: 63, DEF: 86, PHY: 85 },
    form: ["L", "W", "D", "D", "W"],
    foot: "Right",
    height: "1.91m",
    watchers: 980,
  },
  {
    id: "p4",
    name: "Álvaro Ibáñez",
    shortName: "Ibáñez",
    position: "GK",
    club: "Real Cantábrico",
    nation: "ESP",
    age: 31,
    ovr: 85,
    gsi: 858,
    tier: "elite",
    image: "/players/keeper.png",
    price: 655.75,
    change: 0.6,
    attrs: { PAC: 52, SHO: 18, PAS: 74, DRI: 40, DEF: 87, PHY: 81 },
    form: ["W", "W", "W", "D", "L"],
    foot: "Right",
    height: "1.93m",
    watchers: 1540,
  },
];

export const regens: Regen[] = [
  {
    id: "r1",
    name: "Kofi Mensah-Boateng",
    position: "RW",
    archetype: "Inverted winger",
    nation: "GHA",
    age: 17,
    current: 64,
    ceiling: [86, 91],
    generation: 3,
    serial: "GTX-R3-00417",
    lineage: [
      { label: "Academy", detail: "Accra Lions Youth" },
      { label: "Bloodline", detail: "Grandson of a Gen 1 icon" },
      { label: "Scouted", detail: "Fast Cup U18, 4 goals" },
    ],
    traits: ["Explosive first step", "Cuts inside", "Big-game temperament"],
    image: "/players/regen.png",
    price: 96.4,
    story:
      "Signed at 15 after a Fast Cup hat-trick. His DNA carries the pace profile of the 2031 Golden Boot winner.",
  },
];

export const tickerItems = [
  { label: "ADEBAYO", value: 1284.5, change: 6.4 },
  { label: "MOREIRA", value: 742.1, change: 2.1 },
  { label: "LINDQVIST", value: 418.0, change: -1.8 },
  { label: "IBÁÑEZ", value: 655.75, change: 0.6 },
  { label: "MENSAH-B.", value: 96.4, change: 14.2 },
  { label: "OKAFOR", value: 312.9, change: -3.4 },
  { label: "SATO", value: 508.2, change: 1.2 },
  { label: "DUBOIS", value: 221.6, change: 4.8 },
];

export function formatCoin(value: number) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

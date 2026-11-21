export type CrestShape = "shield" | "round" | "diamond" | "pennant";
export type CrestIcon = "star" | "lion" | "eagle" | "crown" | "oak" | "bolt";
export type CrestLayout = "plain" | "band" | "split" | "quarters" | "chevron";
export type CrestFinish = "heritage" | "modern" | "royal";

export interface CrestConcept {
  concept_id: string;
  shape: CrestShape;
  icon_family: CrestIcon;
  layout: CrestLayout;
  finish: CrestFinish;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  initials: string;
  style: string;
  trophy_stars: number;
  visual_meaning: string;
  design_explanation: string;
  svg_markup: string;
  data_uri: string;
}

export interface KitVariant {
  jersey_type: "home" | "away" | "third" | "goalkeeper";
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  pattern_type: string;
  collar_style: string;
  sleeve_style: string;
  shorts_color: string;
  socks_color: string;
  front_text: string;
}

export type KitSet = {
  home: KitVariant;
  away: KitVariant;
  third: KitVariant;
  goalkeeper: KitVariant;
};

export interface KitPreset {
  id: string;
  name: string;
  description: string;
  home: [string, string, string];
  away: [string, string, string];
  third: [string, string, string];
  goalkeeper: [string, string, string];
  pattern: string;
  collar: string;
  sleeve: string;
  patterns: [string, string, string, string];
}

export const CREST_PAGE_SIZE = 24;
export const KIT_PAGE_SIZE = 12;
const CHEST_TEXT_LIMIT = 18;

const CREST_PALETTES: Array<[string, string, string]> = [
  ["#163A70", "#F4F0E6", "#D6A84B"],
  ["#0B654B", "#F7F5EC", "#D1A34A"],
  ["#A71930", "#FFF3E6", "#17243B"],
  ["#111827", "#E6C66B", "#F9FAFB"],
  ["#087F8C", "#EDF7F4", "#EF785F"],
  ["#542583", "#F4EDE0", "#D9AF59"],
  ["#202C39", "#D8F05C", "#F8FAFC"],
  ["#3A6EA5", "#E8F2F8", "#D9B36A"],
  ["#64233C", "#E9D5BA", "#FFFFFF"],
  ["#B9502C", "#18222C", "#F0C37B"],
  ["#17513C", "#F3F0E5", "#B99C56"],
  ["#1B4296", "#DDF1FA", "#FFFFFF"],
  ["#7A1F3D", "#F6E7C1", "#1C2838"],
  ["#0E4D6C", "#F3FBFF", "#E07A3D"],
  ["#3F3A2A", "#F3E6C4", "#C4552A"],
  ["#1E3A34", "#E7F2EA", "#C6A15B"],
  ["#4C1D95", "#F5F3FF", "#F5C16C"],
  ["#7F1D1D", "#FEE2E2", "#F8FAFC"],
];

const SHAPES: Array<{ id: CrestShape; label: string }> = [
  { id: "shield", label: "Shield" },
  { id: "round", label: "Roundel" },
  { id: "diamond", label: "Diamond" },
  { id: "pennant", label: "Pennant" },
];

const ICONS: Array<{ id: CrestIcon; label: string }> = [
  { id: "lion", label: "Lion" },
  { id: "eagle", label: "Eagle" },
  { id: "crown", label: "Crown" },
  { id: "star", label: "Star" },
  { id: "oak", label: "Oak" },
  { id: "bolt", label: "Lightning" },
];

const LAYOUTS: Array<{ id: CrestLayout; label: string }> = [
  { id: "plain", label: "Plain" },
  { id: "band", label: "Band" },
  { id: "split", label: "Split" },
  { id: "quarters", label: "Quarters" },
  { id: "chevron", label: "Chevron" },
];

const FINISHES: Array<{ id: CrestFinish; label: string }> = [
  { id: "heritage", label: "Heritage" },
  { id: "modern", label: "Modern" },
  { id: "royal", label: "Royal" },
];

const PATTERN_ORDER = ["stripes", "hoops", "sash", "chevron", "solid", "gradient"] as const;

const KIT_CUTS: Array<{ label: string; pattern: string; collar: string; sleeve: string }> = [
  { label: "Crew Stripes", pattern: "stripes", collar: "crew", sleeve: "short" },
  { label: "V-Neck Hoops", pattern: "hoops", collar: "v_neck", sleeve: "raglan" },
  { label: "Polo Sash", pattern: "sash", collar: "polo", sleeve: "cuffed" },
  { label: "Wrap Chevron", pattern: "chevron", collar: "wrap", sleeve: "long" },
  { label: "Plain Crew", pattern: "solid", collar: "crew", sleeve: "cuffed" },
  { label: "Fade V-Neck", pattern: "gradient", collar: "v_neck", sleeve: "short" },
  { label: "Polo Stripes", pattern: "stripes", collar: "polo", sleeve: "raglan" },
  { label: "Wrap Hoops", pattern: "hoops", collar: "wrap", sleeve: "short" },
];

type KitStory = {
  id: string;
  name: string;
  description: string;
  home: [string, string, string];
  third: [string, string, string];
  goalkeeper: [string, string, string];
};

const KIT_STORIES: KitStory[] = [
  {
    id: "royal-heritage",
    name: "Royal Heritage",
    description: "Royal blue, white and championship gold",
    home: ["#123B8A", "#FFFFFF", "#D9A441"],
    third: ["#101827", "#D9A441", "#FFFFFF"],
    goalkeeper: ["#E9B949", "#152238", "#FFFFFF"],
  },
  {
    id: "emerald-dynasty",
    name: "Emerald Dynasty",
    description: "Deep emerald with warm gold detailing",
    home: ["#075B45", "#F4F1E8", "#D6A84B"],
    third: ["#102B26", "#56C7A3", "#F4F1E8"],
    goalkeeper: ["#E4A62C", "#102B26", "#FFFFFF"],
  },
  {
    id: "scarlet-regalia",
    name: "Scarlet Regalia",
    description: "Classic scarlet, cream and dark navy",
    home: ["#A5122A", "#FFF4E6", "#152238"],
    third: ["#152238", "#A5122A", "#FFF4E6"],
    goalkeeper: ["#C7E7F5", "#152238", "#A5122A"],
  },
  {
    id: "midnight-gold",
    name: "Midnight Gold",
    description: "Midnight navy with metallic gold",
    home: ["#081B35", "#D7B65D", "#FFFFFF"],
    third: ["#202938", "#D7B65D", "#F4F5F7"],
    goalkeeper: ["#6E43A6", "#F4F5F7", "#D7B65D"],
  },
  {
    id: "coastal-teal",
    name: "Coastal Teal",
    description: "Ocean teal, ice white and coral",
    home: ["#087F8C", "#E9F6F6", "#F27B62"],
    third: ["#123B50", "#5BC0BE", "#FFFFFF"],
    goalkeeper: ["#F1B84B", "#123B50", "#FFFFFF"],
  },
  {
    id: "purple-sovereign",
    name: "Purple Sovereign",
    description: "Regal purple with gold and ivory",
    home: ["#542583", "#F7F0DF", "#D8AD55"],
    third: ["#1D1832", "#A67BD5", "#F7F0DF"],
    goalkeeper: ["#5DB7A4", "#1D1832", "#FFFFFF"],
  },
  {
    id: "black-panther",
    name: "Black Panther",
    description: "Black, graphite and electric lime",
    home: ["#101418", "#D8F35A", "#FFFFFF"],
    third: ["#26313A", "#7FA4B8", "#FFFFFF"],
    goalkeeper: ["#D84D43", "#101418", "#FFFFFF"],
  },
  {
    id: "northern-sky",
    name: "Northern Sky",
    description: "Sky blue, navy and silver",
    home: ["#4DA6D8", "#102D4A", "#E9F1F7"],
    third: ["#102D4A", "#B9D5E8", "#FFFFFF"],
    goalkeeper: ["#E7B44B", "#102D4A", "#FFFFFF"],
  },
  {
    id: "burgundy-classic",
    name: "Burgundy Classic",
    description: "Burgundy, sand and cream",
    home: ["#641C32", "#E5D3B3", "#F8F2E8"],
    third: ["#242B36", "#C9A86A", "#F8F2E8"],
    goalkeeper: ["#3C9B76", "#242B36", "#FFFFFF"],
  },
  {
    id: "copper-forge",
    name: "Copper Forge",
    description: "Burnt orange, charcoal and pale gold",
    home: ["#B74B2A", "#17212B", "#F2C078"],
    third: ["#17212B", "#E47C42", "#F5E8D6"],
    goalkeeper: ["#3C77A8", "#17212B", "#FFFFFF"],
  },
  {
    id: "forest-tradition",
    name: "Forest Tradition",
    description: "Forest green with old-gold trim",
    home: ["#174B35", "#F4F0E4", "#B69A55"],
    third: ["#243B34", "#8CC7A5", "#F4F0E4"],
    goalkeeper: ["#D94B43", "#243B34", "#FFFFFF"],
  },
  {
    id: "ice-cobalt",
    name: "Ice Cobalt",
    description: "Cobalt, ice blue and white",
    home: ["#1745A5", "#D8F0FA", "#FFFFFF"],
    third: ["#0D1B36", "#5BA9E6", "#FFFFFF"],
    goalkeeper: ["#E8A23A", "#0D1B36", "#FFFFFF"],
  },
  {
    id: "desert-rose",
    name: "Desert Rose",
    description: "Sandstone, rose and dark plum",
    home: ["#B96E68", "#F6E9D8", "#44273F"],
    third: ["#44273F", "#DDA7A0", "#F6E9D8"],
    goalkeeper: ["#477D72", "#44273F", "#FFFFFF"],
  },
  {
    id: "monochrome-elite",
    name: "Monochrome Elite",
    description: "Black, white and silver",
    home: ["#111820", "#FFFFFF", "#A9B4BF"],
    third: ["#46515C", "#F0F2F4", "#111820"],
    goalkeeper: ["#D4AF37", "#111820", "#FFFFFF"],
  },
  {
    id: "citrus-electric",
    name: "Citrus Electric",
    description: "Electric yellow, deep blue and black",
    home: ["#D5E82D", "#102A43", "#FFFFFF"],
    third: ["#102A43", "#F36B3F", "#FFFFFF"],
    goalkeeper: ["#7D5CC6", "#102A43", "#FFFFFF"],
  },
  {
    id: "ocean-maroon",
    name: "Ocean Maroon",
    description: "Deep maroon, aqua and cream",
    home: ["#6D1D3B", "#B8E4E3", "#F5ECDD"],
    third: ["#0D3D4A", "#E0A65D", "#FFFFFF"],
    goalkeeper: ["#D95F4D", "#0D3D4A", "#FFFFFF"],
  },
  {
    id: "ivory-navy",
    name: "Ivory Navy",
    description: "Ivory body with navy and copper",
    home: ["#F4EFE4", "#14233B", "#C47B4A"],
    third: ["#14233B", "#F4EFE4", "#C47B4A"],
    goalkeeper: ["#2F9E8F", "#14233B", "#F4EFE4"],
  },
  {
    id: "crimson-ink",
    name: "Crimson Ink",
    description: "Ink black with crimson flashes",
    home: ["#1A1014", "#E11D48", "#F8E7EA"],
    third: ["#3F0D1A", "#F8E7EA", "#E11D48"],
    goalkeeper: ["#F59E0B", "#1A1014", "#F8E7EA"],
  },
  {
    id: "arctic-white",
    name: "Arctic White",
    description: "White, ice blue and deep navy",
    home: ["#F8FBFF", "#0F3A68", "#7DD3FC"],
    third: ["#0F3A68", "#F8FBFF", "#7DD3FC"],
    goalkeeper: ["#F97316", "#0F3A68", "#F8FBFF"],
  },
  {
    id: "amber-pitch",
    name: "Amber Pitch",
    description: "Amber, pitch green and cream",
    home: ["#C47B16", "#16382B", "#F6E7C1"],
    third: ["#16382B", "#E7B008", "#F6E7C1"],
    goalkeeper: ["#2563EB", "#16382B", "#F6E7C1"],
  },
  {
    id: "violet-night",
    name: "Violet Night",
    description: "Night violet with silver and lilac",
    home: ["#2E1065", "#E9D5FF", "#C4B5FD"],
    third: ["#111827", "#A78BFA", "#F5F3FF"],
    goalkeeper: ["#FACC15", "#2E1065", "#F5F3FF"],
  },
  {
    id: "lime-harbor",
    name: "Lime Harbor",
    description: "Harbor navy with lime and white",
    home: ["#0F2C3C", "#D9F99D", "#FFFFFF"],
    third: ["#14532D", "#D9F99D", "#ECFCCB"],
    goalkeeper: ["#FB7185", "#0F2C3C", "#FFFFFF"],
  },
  {
    id: "bronze-city",
    name: "Bronze City",
    description: "Bronze, charcoal and warm sand",
    home: ["#8A5A2B", "#1F2933", "#F3E6D0"],
    third: ["#1F2933", "#D6A15A", "#F3E6D0"],
    goalkeeper: ["#0EA5E9", "#1F2933", "#F3E6D0"],
  },
  {
    id: "rose-navy",
    name: "Rose Navy",
    description: "Rose red, navy and pale gold",
    home: ["#9F1239", "#172554", "#FDE68A"],
    third: ["#172554", "#FB7185", "#FDE68A"],
    goalkeeper: ["#34D399", "#172554", "#FDE68A"],
  },
  {
    id: "glacier-red",
    name: "Glacier Red",
    description: "Glacier blue with signal red",
    home: ["#0369A1", "#E0F2FE", "#DC2626"],
    third: ["#082F49", "#FCA5A5", "#E0F2FE"],
    goalkeeper: ["#FDE047", "#082F49", "#E0F2FE"],
  },
];

function xmlSafe(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

const GENERIC_CLUB_WORDS = new Set(["FC", "CF", "SC", "AC", "AFC"]);

export function clubShortCode(clubName: string): string {
  const words = clubName
    .toUpperCase()
    .split(/[^A-Z0-9]+/)
    .filter(Boolean);
  if (words.length === 0) return "FCL";

  let code = "";
  if (words.length >= 3) {
    code = words
      .slice(0, 3)
      .map((word) => word[0])
      .join("");
  } else if (words.length === 2) {
    const [first, second] = words;
    code =
      GENERIC_CLUB_WORDS.has(first) || GENERIC_CLUB_WORDS.has(second)
        ? (first + second).slice(0, 3)
        : (first[0] + second).slice(0, 3);
  } else {
    code = words[0].slice(0, 3);
  }
  return (code + "FCX").slice(0, 3);
}

export function kitChestText(clubName: string): string {
  const cleaned = clubName.trim().replace(/\s+/g, " ");
  if (!cleaned) return "FC";
  if (cleaned.length <= CHEST_TEXT_LIMIT) return cleaned.toUpperCase().slice(0, 20);
  return clubShortCode(cleaned);
}

function isLight(hex: string): boolean {
  const raw = hex.replace("#", "");
  if (raw.length < 6) return true;
  const red = Number.parseInt(raw.slice(0, 2), 16);
  const green = Number.parseInt(raw.slice(2, 4), 16);
  const blue = Number.parseInt(raw.slice(4, 6), 16);
  if ([red, green, blue].some((channel) => Number.isNaN(channel))) return true;
  return (red * 299 + green * 587 + blue * 114) / 1000 > 165;
}

function initialsFontSize(initials: string): number {
  if (initials.length <= 1) return 58;
  if (initials.length === 2) return 48;
  if (initials.length === 3) return 36;
  return 28;
}

function crestIconMarkup(icon: CrestIcon): string {
  switch (icon) {
    case "crown":
      return '<path d="M30 78 L18 27 L43 48 L50 14 L58 48 L83 27 L70 78 Z" /><rect x="28" y="80" width="44" height="10" rx="3" />';
    case "eagle":
      return '<path d="M50 20 C34 12 18 16 5 29 L27 32 L12 47 L35 45 L50 65 L65 45 L88 47 L73 32 L95 29 C82 16 66 12 50 20 Z" /><circle cx="58" cy="31" r="3" fill="#fff" />';
    case "star":
      return '<polygon points="50,4 62,37 97,38 70,59 80,94 50,73 20,94 30,59 3,38 38,37" />';
    case "oak":
      return '<path d="M50 12 C33 12 25 26 30 40 C13 45 14 65 30 72 C31 86 43 92 50 96 C57 92 69 86 70 72 C86 65 87 45 70 40 C75 26 67 12 50 12 Z" /><path d="M50 24 V92 M37 52 L50 64 L63 52" fill="none" stroke="#fff" stroke-width="4" />';
    case "bolt":
      return '<polygon points="57,3 22,53 45,53 34,97 80,38 55,38" />';
    default:
      return '<path d="M50 10 C25 10 10 30 16 57 C22 82 40 93 50 98 C60 93 78 82 84 57 C90 30 75 10 50 10 Z" /><path d="M34 38 Q50 23 66 38 M36 65 L44 67 L50 61 L56 67 L64 65" fill="none" stroke="#fff" stroke-width="4" />';
  }
}

function shapeOutline(shape: CrestShape): string {
  if (shape === "round") return '<circle cx="100" cy="116" r="85" />';
  if (shape === "diamond") return '<path d="M100 15 L185 116 L100 217 L15 116 Z" />';
  if (shape === "pennant") return '<path d="M20 20 H180 V120 L100 225 L20 120 Z" />';
  return '<path d="M25 25 Q100 12 175 25 C175 90 175 145 100 225 C25 145 25 90 25 25 Z" />';
}

function layoutMarkup(layout: CrestLayout, secondary: string, accent: string): string {
  if (layout === "band") {
    return `<rect x="18" y="78" width="164" height="24" fill="${secondary}" opacity=".92"/>`;
  }
  if (layout === "split") {
    return `<rect x="0" y="0" width="100" height="240" fill="${secondary}" opacity=".38"/>`;
  }
  if (layout === "quarters") {
    return `<rect x="0" y="0" width="100" height="120" fill="${secondary}" opacity=".34"/><rect x="100" y="120" width="100" height="120" fill="${accent}" opacity=".28"/>`;
  }
  if (layout === "chevron") {
    return `<path d="M28 96 L100 132 L172 96 L172 112 L100 150 L28 112 Z" fill="${secondary}" opacity=".9"/>`;
  }
  return "";
}

function finishMarkup(finish: CrestFinish, accent: string, secondary: string): string {
  if (finish === "modern") {
    return `<path d="M46 34 H64 M136 34 H154 M48 196 H68 M132 196 H152" stroke="${accent}" stroke-width="4" stroke-linecap="round"/>`;
  }
  if (finish === "royal") {
    return `<g fill="${accent}" stroke="${secondary}" stroke-width="1">
      <polygon points="78,16 81,24 90,25 83,31 85,40 78,35 71,40 73,31 66,25 75,24"/>
      <polygon points="100,8 104,18 114,19 106,26 108,36 100,31 92,36 94,26 86,19 96,18"/>
      <polygon points="122,16 125,24 134,25 127,31 129,40 122,35 115,40 117,31 110,25 119,24"/>
    </g>`;
  }
  return `<path d="M48 168 C28 150 30 118 52 98 M152 168 C172 150 170 118 148 98" fill="none" stroke="${accent}" stroke-width="3" stroke-linecap="round"/>`;
}

function renderCrestSvg(
  shape: CrestShape,
  icon: CrestIcon,
  layout: CrestLayout,
  primary: string,
  secondary: string,
  accent: string,
  initials: string,
  finish: CrestFinish,
): string {
  const safeInitials = xmlSafe(initials.slice(0, 3));
  const fontSize = initialsFontSize(safeInitials);
  const letterFill = isLight(secondary) ? secondary : "#F8FAFC";
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="200" height="240">
    <defs>
      <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".85"/><stop offset=".55" stop-color="${accent}"/><stop offset="1" stop-color="#4B5563"/></linearGradient>
      <linearGradient id="face" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".18"/><stop offset=".45" stop-color="#000000" stop-opacity="0"/><stop offset="1" stop-color="#000000" stop-opacity=".28"/></linearGradient>
      <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#000000" flood-opacity=".4"/></filter>
      <clipPath id="badge">${shapeOutline(shape)}</clipPath>
    </defs>
    <g filter="url(#shadow)">
      <g fill="${primary}" stroke="url(#rim)" stroke-width="7" stroke-linejoin="round">${shapeOutline(shape)}</g>
      <g clip-path="url(#badge)">
        ${layoutMarkup(layout, secondary, accent)}
        <g fill="url(#face)">${shapeOutline(shape)}</g>
        <ellipse cx="78" cy="62" rx="34" ry="16" fill="#FFFFFF" opacity=".16"/>
      </g>
    </g>
    ${finishMarkup(finish, accent, secondary)}
    <g transform="translate(69 30) scale(0.58)" fill="${accent}" stroke="${secondary}" stroke-width="2" stroke-linejoin="round">${crestIconMarkup(icon)}</g>
    <g clip-path="url(#badge)">
      <rect x="46" y="128" width="108" height="44" rx="8" fill="#0B1220" fill-opacity=".62"/>
      <text x="100" y="160" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-size="${fontSize}" font-weight="900" letter-spacing="1" fill="${letterFill}" stroke="#0B1220" stroke-width="1.4">${safeInitials}</text>
    </g>
  </svg>`;
}

export function crestDataUri(input: {
  shape: string;
  icon: string;
  primary: string;
  secondary: string;
  accent: string;
  initials: string;
}): string {
  const shapes: CrestShape[] = ["shield", "round", "diamond", "pennant"];
  const icons: CrestIcon[] = ["star", "lion", "eagle", "crown", "oak", "bolt"];
  const shape = shapes.includes(input.shape as CrestShape) ? (input.shape as CrestShape) : "shield";
  const icon = icons.includes(input.icon as CrestIcon) ? (input.icon as CrestIcon) : "star";
  const svg = renderCrestSvg(
    shape,
    icon,
    "plain",
    input.primary || "#163A70",
    input.secondary || "#F4F0E6",
    input.accent || "#D6A84B",
    input.initials || "FC",
    "heritage",
  );
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function buildCrestLibrary(clubName: string): CrestConcept[] {
  const initials = clubShortCode(clubName);
  const options: CrestConcept[] = [];
  let optionIndex = 0;
  for (const shape of SHAPES) {
    for (const icon of ICONS) {
      for (const finish of FINISHES) {
        for (const layout of LAYOUTS) {
          const palette = CREST_PALETTES[optionIndex % CREST_PALETTES.length];
          const svg = renderCrestSvg(
            shape.id,
            icon.id,
            layout.id,
            palette[0],
            palette[1],
            palette[2],
            initials,
            finish.id,
          );
          const style = `${finish.label} ${shape.label}`;
          options.push({
            concept_id: `${shape.id}-${icon.id}-${finish.id}-${layout.id}`,
            shape: shape.id,
            icon_family: icon.id,
            layout: layout.id,
            finish: finish.id,
            primary_color: palette[0],
            secondary_color: palette[1],
            accent_color: palette[2],
            initials,
            style,
            trophy_stars: 0,
            visual_meaning: `${icon.label} · ${layout.label.toLowerCase()} ${shape.label.toLowerCase()} · ${finish.label.toLowerCase()}`,
            design_explanation: `${finish.label} ${shape.label.toLowerCase()} with a ${layout.label.toLowerCase()} face, a ${icon.label.toLowerCase()} charge, and ${initials} on the badge.`,
            svg_markup: svg,
            data_uri: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
          });
          optionIndex += 1;
        }
      }
    }
  }
  return options;
}

export function preferredCrestIndex(crests: CrestConcept[], style: string): number {
  const shape: CrestShape =
    style === "modern" ? "round" : style === "metallic" ? "diamond" : "shield";
  const index = crests.findIndex((crest) => crest.shape === shape && crest.layout === "plain");
  return index < 0 ? 0 : index;
}

export function filterCrestLibrary(
  crests: CrestConcept[],
  filter: { finish?: string; shape?: string; query?: string },
): CrestConcept[] {
  const query = (filter.query || "").trim().toLowerCase();
  return crests.filter((crest) => {
    if (filter.finish && filter.finish !== "all" && crest.finish !== filter.finish) return false;
    if (filter.shape && filter.shape !== "all" && crest.shape !== filter.shape) return false;
    if (!query) return true;
    const haystack =
      `${crest.style} ${crest.icon_family} ${crest.layout} ${crest.initials} ${crest.visual_meaning}`.toLowerCase();
    return haystack.includes(query);
  });
}

function shiftPattern(pattern: string, offset: number): string {
  const index = PATTERN_ORDER.indexOf(pattern as (typeof PATTERN_ORDER)[number]);
  const start = index < 0 ? 0 : index;
  return PATTERN_ORDER[(start + offset) % PATTERN_ORDER.length];
}

function buildKitCatalog(): KitPreset[] {
  const presets: KitPreset[] = [];
  for (const story of KIT_STORIES) {
    const away: [string, string, string] = [story.home[1], story.home[0], story.home[2]];
    KIT_CUTS.forEach((cut, cutIndex) => {
      presets.push({
        id: `${story.id}-${cutIndex + 1}`,
        name: `${story.name} · ${cut.label}`,
        description: `${story.description}. ${cut.collar.replace("_", " ")} collar, ${cut.sleeve} sleeves.`,
        home: story.home,
        away,
        third: story.third,
        goalkeeper: story.goalkeeper,
        pattern: cut.pattern,
        collar: cut.collar,
        sleeve: cut.sleeve,
        patterns: [
          cut.pattern,
          shiftPattern(cut.pattern, 1),
          shiftPattern(cut.pattern, 2),
          shiftPattern(cut.pattern, 3),
        ],
      });
    });
  }
  return presets;
}

export const KIT_PRESETS: KitPreset[] = buildKitCatalog();

function variant(
  jerseyType: KitVariant["jersey_type"],
  colors: [string, string, string],
  pattern: string,
  collar: string,
  sleeve: string,
  shorts: string,
  socks: string,
  chestText: string,
): KitVariant {
  return {
    jersey_type: jerseyType,
    primary_color: colors[0],
    secondary_color: colors[1],
    accent_color: colors[2],
    pattern_type: pattern,
    collar_style: collar,
    sleeve_style: sleeve,
    shorts_color: shorts,
    socks_color: socks,
    front_text: chestText,
  };
}

export function buildKitSet(presetId: string, clubName: string): KitSet {
  const preset = KIT_PRESETS.find((item) => item.id === presetId) || KIT_PRESETS[0];
  const chestText = kitChestText(clubName);
  const [homePrimary, homeSecondary] = preset.home;
  const [awayPrimary] = preset.away;
  const [thirdPrimary] = preset.third;
  return {
    home: variant(
      "home",
      preset.home,
      preset.patterns[0],
      preset.collar,
      preset.sleeve,
      homePrimary,
      homeSecondary,
      chestText,
    ),
    away: variant(
      "away",
      preset.away,
      preset.patterns[1],
      preset.collar,
      preset.sleeve,
      awayPrimary,
      preset.away[1],
      chestText,
    ),
    third: variant(
      "third",
      preset.third,
      preset.patterns[2],
      preset.collar,
      preset.sleeve,
      thirdPrimary,
      preset.third[1],
      chestText,
    ),
    goalkeeper: variant(
      "goalkeeper",
      preset.goalkeeper,
      preset.patterns[3],
      preset.collar,
      "long",
      preset.goalkeeper[0],
      preset.goalkeeper[1],
      chestText,
    ),
  };
}

export function filterKitPresets(
  presets: KitPreset[],
  filter: { pattern?: string; query?: string },
): KitPreset[] {
  const query = (filter.query || "").trim().toLowerCase();
  return presets.filter((preset) => {
    if (filter.pattern && filter.pattern !== "all" && preset.pattern !== filter.pattern)
      return false;
    if (!query) return true;
    return `${preset.name} ${preset.description} ${preset.collar} ${preset.sleeve}`
      .toLowerCase()
      .includes(query);
  });
}

export function buildClubDNA(
  clubName: string,
  cityName: string,
  countryCode: string,
  recruitmentFocus: string,
  preferredAgeBracket: string,
  nationalityFocus: string,
) {
  const policy: Record<
    string,
    { philosophy: string; transfer: string; finance: string; narrative: string }
  > = {
    youth: {
      philosophy: "youth_development",
      transfer: "buy_young_develop_sell",
      finance: "balanced",
      narrative: "developing young talent and building a lasting football legacy",
    },
    academy: {
      philosophy: "academy_first",
      transfer: "academy_production",
      finance: "academy_focused",
      narrative: "bringing home-grown academy graduates into the first team",
    },
    selling: {
      philosophy: "selling_club",
      transfer: "buy_young_develop_sell",
      finance: "sustainable",
      narrative: "finding undervalued players, developing them and selling at the right moment",
    },
    superstars: {
      philosophy: "superstar",
      transfer: "superstars",
      finance: "big_spending",
      narrative: "competing for the biggest names and the highest honours",
    },
    sustainable: {
      philosophy: "sustainable",
      transfer: "buy_undervalued",
      finance: "sustainable",
      narrative: "building a competitive club through careful scouting and disciplined spending",
    },
    balanced: {
      philosophy: "balanced",
      transfer: "buy_undervalued",
      finance: "balanced",
      narrative: "balancing promising young players with experienced professionals",
    },
  };
  const selected = policy[recruitmentFocus] || policy.youth;
  const preferredMaxAge =
    preferredAgeBracket === "none" ? null : Number(preferredAgeBracket.replace("U", "")) || 23;
  return {
    primary_philosophy: selected.philosophy,
    secondary_philosophies: [],
    nationality_mode: nationalityFocus,
    target_nationalities: nationalityFocus === "none" ? [] : [countryCode],
    allow_dual_nationality: true,
    age_mode: preferredAgeBracket === "none" ? "none" : "preferred",
    preferred_max_age: preferredMaxAge,
    allow_age_exceptions: true,
    transfer_strategy: selected.transfer,
    financial_philosophy: selected.finance,
    vision_narrative: `${clubName} is based in ${cityName}. Its club identity is centred on ${selected.narrative}.`,
  };
}

function patternMarkup(kit: KitVariant, shirtPath: string): string {
  if (kit.pattern_type === "stripes") {
    return `<path d="M45 24 H52 V116 H45 Z M65 22 H72 V116 H65 Z M81 25 H85 V116 H81 Z" fill="${kit.secondary_color}" opacity=".85"/>`;
  }
  if (kit.pattern_type === "hoops") {
    return `<path d="M25 48 H98 V58 H25 Z M30 72 H94 V82 H30 Z M37 96 H87 V106 H37 Z" fill="${kit.secondary_color}" opacity=".9"/>`;
  }
  if (kit.pattern_type === "sash") {
    return `<path d="M27 38 L43 27 L101 94 L89 108 Z" fill="${kit.secondary_color}" opacity=".92"/>`;
  }
  if (kit.pattern_type === "chevron") {
    return `<path d="M31 45 L61 68 L92 45 L96 56 L61 83 L27 56 Z M38 85 L61 103 L84 85 L87 95 L61 114 L35 95 Z" fill="${kit.secondary_color}" opacity=".9"/>`;
  }
  if (kit.pattern_type === "gradient") {
    return `<path d="${shirtPath}" fill="url(#kit-gradient)" opacity=".85"/>`;
  }
  return "";
}

function collarMarkup(kit: KitVariant): string {
  if (kit.collar_style === "v_neck") {
    return `<path d="M48 14 L62 42 L76 14" fill="${kit.primary_color}" stroke="${kit.accent_color}" stroke-width="3" stroke-linejoin="round"/>`;
  }
  if (kit.collar_style === "polo") {
    return `<path d="M46 16 H78" stroke="${kit.accent_color}" stroke-width="3"/><path d="M48 16 L42 28 H54 Z M76 16 L82 28 H70 Z" fill="${kit.secondary_color}" stroke="${kit.accent_color}" stroke-width="1.5"/>`;
  }
  if (kit.collar_style === "wrap") {
    return `<path d="M40 20 L86 34" stroke="${kit.accent_color}" stroke-width="5" stroke-linecap="round"/>`;
  }
  return `<path d="M48 13 L62 28 L76 13" fill="none" stroke="${kit.accent_color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`;
}

function sleeveMarkup(kit: KitVariant): string {
  if (kit.sleeve_style === "long") {
    return `<path d="M39 50 L27 59 L22 92 M85 50 L97 59 L102 92" stroke="${kit.accent_color}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
  }
  if (kit.sleeve_style === "raglan") {
    return `<path d="M62 24 L27 59 M62 24 L97 59" stroke="${kit.secondary_color}" stroke-width="2.5" fill="none"/>`;
  }
  if (kit.sleeve_style === "cuffed") {
    return `<path d="M24 52 H36 M88 52 H100" stroke="${kit.accent_color}" stroke-width="4" stroke-linecap="round"/>`;
  }
  return `<path d="M39 50 L27 59 M85 50 L97 59" stroke="${kit.accent_color}" stroke-width="3" fill="none"/>`;
}

export function kitSwatchDataUri(kit: KitVariant): string {
  const shirtPath =
    "M36 24 L48 12 L62 20 L76 12 L88 24 L108 39 L97 59 L85 50 L85 116 L39 116 L39 50 L27 59 L16 39 Z";
  const pattern = patternMarkup(kit, shirtPath);
  const chest = xmlSafe(kit.front_text.slice(0, 20));
  const fontSize = chest.length > 12 ? 6.5 : chest.length > 8 ? 8 : 10;
  const letterFill = isLight(kit.secondary_color) ? kit.secondary_color : "#F8FAFC";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 124 188" width="124" height="188">
    <defs>
      <linearGradient id="kit-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${kit.secondary_color}" stop-opacity=".1"/><stop offset="1" stop-color="${kit.secondary_color}" stop-opacity=".95"/></linearGradient>
      <linearGradient id="kit-shade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".2"/><stop offset=".55" stop-color="#000000" stop-opacity="0"/><stop offset="1" stop-color="#000000" stop-opacity=".35"/></linearGradient>
      <clipPath id="shirt-clip"><path d="${shirtPath}"/></clipPath>
      <filter id="kit-shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#000" flood-opacity=".35"/></filter>
    </defs>
    <g filter="url(#kit-shadow)">
      <path d="${shirtPath}" fill="${kit.primary_color}" stroke="${kit.accent_color}" stroke-width="4" stroke-linejoin="round"/>
      <g clip-path="url(#shirt-clip)">
        ${pattern}
        <path d="${shirtPath}" fill="url(#kit-shade)"/>
        <text x="62" y="78" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-size="${fontSize}" font-weight="900" fill="${letterFill}" stroke="#111827" stroke-width=".6">${chest}</text>
      </g>
      ${collarMarkup(kit)}
      ${sleeveMarkup(kit)}
      <circle cx="86" cy="42" r="11" fill="${kit.secondary_color}" stroke="${kit.accent_color}" stroke-width="1.6"/>
      <path d="M38 114 H58 V148 H42 Z M66 114 H86 V148 H70 Z" fill="${kit.shorts_color}" stroke="${kit.accent_color}" stroke-width="2"/>
      <path d="M38 142 H58 M66 142 H86" stroke="${kit.accent_color}" stroke-width="3"/>
      <text x="48" y="134" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-size="11" font-weight="900" fill="#F8FAFC" stroke="#111827" stroke-width=".6">10</text>
      <circle cx="76" cy="130" r="7" fill="${kit.secondary_color}" stroke="#F8FAFC" stroke-width="1.4"/>
      <path d="M40 150 H56 V176 H44 Z M68 150 H84 V176 H72 Z" fill="${kit.socks_color}"/>
      <path d="M40 150 H56 M68 150 H84" stroke="${kit.accent_color}" stroke-width="3"/>
    </g>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

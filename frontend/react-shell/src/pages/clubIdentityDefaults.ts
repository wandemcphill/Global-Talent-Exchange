export type CrestShape = "shield" | "round" | "diamond" | "pennant";
export type CrestIcon = "star" | "lion" | "eagle" | "crown" | "oak" | "bolt";

export interface CrestConcept {
  concept_id: string;
  shape: CrestShape;
  icon_family: CrestIcon;
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
  patterns: [string, string, string, string];
}

export const KIT_PRESETS: KitPreset[] = [
  { id: "royal-heritage", name: "Royal Heritage", description: "Royal blue, white and championship gold", home: ["#123B8A", "#FFFFFF", "#D9A441"], away: ["#F7F8FA", "#123B8A", "#D9A441"], third: ["#101827", "#D9A441", "#FFFFFF"], goalkeeper: ["#E9B949", "#152238", "#FFFFFF"], patterns: ["stripes", "sash", "chevron", "solid"] },
  { id: "emerald-dynasty", name: "Emerald Dynasty", description: "Deep emerald with warm gold detailing", home: ["#075B45", "#F4F1E8", "#D6A84B"], away: ["#F4F1E8", "#075B45", "#D6A84B"], third: ["#102B26", "#56C7A3", "#F4F1E8"], goalkeeper: ["#E4A62C", "#102B26", "#FFFFFF"], patterns: ["hoops", "solid", "sash", "chevron"] },
  { id: "scarlet-regalia", name: "Scarlet Regalia", description: "Classic scarlet, cream and dark navy", home: ["#A5122A", "#FFF4E6", "#152238"], away: ["#FFF4E6", "#A5122A", "#152238"], third: ["#152238", "#A5122A", "#FFF4E6"], goalkeeper: ["#C7E7F5", "#152238", "#A5122A"], patterns: ["solid", "sash", "stripes", "gradient"] },
  { id: "midnight-gold", name: "Midnight Gold", description: "Premium midnight navy with metallic gold", home: ["#081B35", "#D7B65D", "#FFFFFF"], away: ["#F4F5F7", "#081B35", "#D7B65D"], third: ["#202938", "#D7B65D", "#F4F5F7"], goalkeeper: ["#6E43A6", "#F4F5F7", "#D7B65D"], patterns: ["chevron", "solid", "hoops", "gradient"] },
  { id: "coastal-teal", name: "Coastal Teal", description: "Ocean teal, ice white and coral accents", home: ["#087F8C", "#E9F6F6", "#F27B62"], away: ["#E9F6F6", "#087F8C", "#F27B62"], third: ["#123B50", "#5BC0BE", "#FFFFFF"], goalkeeper: ["#F1B84B", "#123B50", "#FFFFFF"], patterns: ["sash", "stripes", "solid", "hoops"] },
  { id: "purple-sovereign", name: "Purple Sovereign", description: "Regal purple with gold and ivory", home: ["#542583", "#F7F0DF", "#D8AD55"], away: ["#F7F0DF", "#542583", "#D8AD55"], third: ["#1D1832", "#A67BD5", "#F7F0DF"], goalkeeper: ["#5DB7A4", "#1D1832", "#FFFFFF"], patterns: ["hoops", "sash", "gradient", "solid"] },
  { id: "black-panther", name: "Black Panther", description: "Black, graphite and electric lime", home: ["#101418", "#D8F35A", "#FFFFFF"], away: ["#F3F5F3", "#101418", "#D8F35A"], third: ["#26313A", "#7FA4B8", "#FFFFFF"], goalkeeper: ["#D84D43", "#101418", "#FFFFFF"], patterns: ["chevron", "solid", "stripes", "sash"] },
  { id: "northern-sky", name: "Northern Sky", description: "Sky blue, navy and silver", home: ["#4DA6D8", "#102D4A", "#E9F1F7"], away: ["#F7FAFC", "#4DA6D8", "#102D4A"], third: ["#102D4A", "#B9D5E8", "#FFFFFF"], goalkeeper: ["#E7B44B", "#102D4A", "#FFFFFF"], patterns: ["stripes", "sash", "solid", "gradient"] },
  { id: "burgundy-classic", name: "Burgundy Classic", description: "Burgundy, sand and cream", home: ["#641C32", "#E5D3B3", "#F8F2E8"], away: ["#F8F2E8", "#641C32", "#C9A86A"], third: ["#242B36", "#C9A86A", "#F8F2E8"], goalkeeper: ["#3C9B76", "#242B36", "#FFFFFF"], patterns: ["hoops", "solid", "sash", "chevron"] },
  { id: "copper-forge", name: "Copper Forge", description: "Burnt orange, charcoal and pale gold", home: ["#B74B2A", "#17212B", "#F2C078"], away: ["#F5E8D6", "#B74B2A", "#17212B"], third: ["#17212B", "#E47C42", "#F5E8D6"], goalkeeper: ["#3C77A8", "#17212B", "#FFFFFF"], patterns: ["sash", "stripes", "chevron", "solid"] },
  { id: "forest-tradition", name: "Forest Tradition", description: "Forest green with old-gold trim", home: ["#174B35", "#F4F0E4", "#B69A55"], away: ["#F4F0E4", "#174B35", "#B69A55"], third: ["#243B34", "#8CC7A5", "#F4F0E4"], goalkeeper: ["#D94B43", "#243B34", "#FFFFFF"], patterns: ["stripes", "hoops", "solid", "gradient"] },
  { id: "ice-cobalt", name: "Ice Cobalt", description: "Cobalt, ice blue and white", home: ["#1745A5", "#D8F0FA", "#FFFFFF"], away: ["#FFFFFF", "#1745A5", "#D8F0FA"], third: ["#0D1B36", "#5BA9E6", "#FFFFFF"], goalkeeper: ["#E8A23A", "#0D1B36", "#FFFFFF"], patterns: ["gradient", "sash", "chevron", "solid"] },
  { id: "desert-rose", name: "Desert Rose", description: "Sandstone, rose and dark plum", home: ["#B96E68", "#F6E9D8", "#44273F"], away: ["#F6E9D8", "#B96E68", "#44273F"], third: ["#44273F", "#DDA7A0", "#F6E9D8"], goalkeeper: ["#477D72", "#44273F", "#FFFFFF"], patterns: ["hoops", "solid", "stripes", "sash"] },
  { id: "monochrome-elite", name: "Monochrome Elite", description: "Clean black, white and silver", home: ["#111820", "#FFFFFF", "#A9B4BF"], away: ["#FFFFFF", "#111820", "#A9B4BF"], third: ["#46515C", "#F0F2F4", "#111820"], goalkeeper: ["#D4AF37", "#111820", "#FFFFFF"], patterns: ["solid", "stripes", "chevron", "gradient"] },
  { id: "citrus-electric", name: "Citrus Electric", description: "Electric yellow, deep blue and black", home: ["#D5E82D", "#102A43", "#FFFFFF"], away: ["#F7F8F5", "#102A43", "#D5E82D"], third: ["#102A43", "#F36B3F", "#FFFFFF"], goalkeeper: ["#7D5CC6", "#102A43", "#FFFFFF"], patterns: ["stripes", "chevron", "sash", "solid"] },
  { id: "ocean-maroon", name: "Ocean Maroon", description: "Deep maroon, aqua and cream", home: ["#6D1D3B", "#B8E4E3", "#F5ECDD"], away: ["#F5ECDD", "#6D1D3B", "#B8E4E3"], third: ["#0D3D4A", "#E0A65D", "#FFFFFF"], goalkeeper: ["#D95F4D", "#0D3D4A", "#FFFFFF"], patterns: ["sash", "hoops", "solid", "gradient"] },
];

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

function xmlSafe(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}

export function clubShortCode(clubName: string): string {
  const words = clubName.trim().split(/\s+/).filter(Boolean);
  if (words.length > 1) return words.slice(0, 4).map((word) => word[0]).join("").toUpperCase().slice(0, 6);
  return (words[0] || "FC").slice(0, 3).toUpperCase();
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

function shapeMarkup(shape: CrestShape, color: string, accent: string): string {
  if (shape === "round") {
    return `<circle cx="100" cy="116" r="85" fill="${color}" stroke="${accent}" stroke-width="7"/><circle cx="100" cy="116" r="73" fill="none" stroke="#FFFFFF" stroke-opacity=".8" stroke-width="2.5"/>`;
  }
  if (shape === "diamond") {
    return `<path d="M100 15 L185 116 L100 217 L15 116 Z" fill="${color}" stroke="${accent}" stroke-width="7" stroke-linejoin="round"/><path d="M100 29 L171 116 L100 203 L29 116 Z" fill="none" stroke="#FFFFFF" stroke-opacity=".75" stroke-width="2.5"/>`;
  }
  if (shape === "pennant") {
    return `<path d="M20 20 H180 V120 L100 225 L20 120 Z" fill="${color}" stroke="${accent}" stroke-width="7" stroke-linejoin="round"/><path d="M33 33 H167 V116 L100 207 L33 116 Z" fill="none" stroke="#FFFFFF" stroke-opacity=".75" stroke-width="2.5"/>`;
  }
  return `<path d="M25 25 Q100 12 175 25 C175 90 175 145 100 225 C25 145 25 90 25 25 Z" fill="${color}" stroke="${accent}" stroke-width="7" stroke-linejoin="round"/><path d="M37 38 Q100 27 163 38 C163 96 163 143 100 209 C37 143 37 96 37 38 Z" fill="none" stroke="#FFFFFF" stroke-opacity=".75" stroke-width="2.5"/>`;
}

function renderCrestSvg(shape: CrestShape, icon: CrestIcon, primary: string, secondary: string, accent: string, initials: string): string {
  const safeInitials = xmlSafe(initials.slice(0, 6));
  const iconMarkup = crestIconMarkup(icon);
  const shapeMarkupSvg = shapeMarkup(shape, primary, accent);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="200" height="240">
    <defs>
      <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".8"/><stop offset=".5" stop-color="${accent}"/><stop offset="1" stop-color="#6B7280"/></linearGradient>
      <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#000000" flood-opacity=".4"/></filter>
    </defs>
    <g filter="url(#shadow)"><g>${shapeMarkupSvg}</g></g>
    <path d="M49 116 H151" stroke="${secondary}" stroke-opacity=".45" stroke-width="2"/>
    <g transform="translate(50 67) scale(1)" fill="${accent}" stroke="${secondary}" stroke-width="2" stroke-linejoin="round">${iconMarkup}</g>
    <rect x="55" y="170" width="90" height="29" rx="5" fill="${secondary}" stroke="url(#rim)" stroke-width="2"/>
    <text x="100" y="190" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" font-weight="900" letter-spacing="2" fill="${primary}">${safeInitials}</text>
    <path d="M75 205 Q100 219 125 205" fill="none" stroke="${accent}" stroke-width="3" stroke-linecap="round"/>
  </svg>`;
}

export function buildCrestLibrary(clubName: string): CrestConcept[] {
  const initials = clubShortCode(clubName);
  const options: CrestConcept[] = [];
  SHAPES.forEach((shape, shapeIndex) => {
    ICONS.forEach((icon, iconIndex) => {
      const palette = CREST_PALETTES[(shapeIndex * ICONS.length + iconIndex) % CREST_PALETTES.length];
      const svg = renderCrestSvg(shape.id, icon.id, palette[0], palette[1], palette[2], initials);
      const style = shape.id === "round" ? "Modern" : shape.id === "diamond" ? "Metallic" : "Heritage";
      options.push({
        concept_id: `${shape.id}-${icon.id}-${shapeIndex * ICONS.length + iconIndex + 1}`,
        shape: shape.id,
        icon_family: icon.id,
        primary_color: palette[0],
        secondary_color: palette[1],
        accent_color: palette[2],
        initials,
        style,
        trophy_stars: 0,
        visual_meaning: `${icon.label} emblem · ${shape.label.toLowerCase()} silhouette`,
        design_explanation: `Ready-made ${style.toLowerCase()} crest with a ${icon.label.toLowerCase()} symbol.`,
        svg_markup: svg,
        data_uri: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
      });
    });
  });
  return options;
}

function variant(
  jerseyType: KitVariant["jersey_type"],
  colors: [string, string, string],
  pattern: string,
  collar: string,
  sleeve: string,
  shorts: string,
  socks: string,
  shortCode: string,
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
    front_text: jerseyType === "third" ? `${shortCode} ALT` : jerseyType === "goalkeeper" ? `${shortCode} GK` : shortCode,
  };
}

export function buildKitSet(presetId: string, shortCode: string): KitSet {
  const preset = KIT_PRESETS.find((item) => item.id === presetId) || KIT_PRESETS[0];
  const [homePrimary, homeSecondary] = preset.home;
  const [awayPrimary] = preset.away;
  const [thirdPrimary] = preset.third;
  return {
    home: variant("home", preset.home, preset.patterns[0], "crew", "short", homePrimary, homeSecondary, shortCode),
    away: variant("away", preset.away, preset.patterns[1], "v_neck", "raglan", awayPrimary, preset.away[1], shortCode),
    third: variant("third", preset.third, preset.patterns[2], "polo", "short", thirdPrimary, preset.third[1], shortCode),
    goalkeeper: variant("goalkeeper", preset.goalkeeper, preset.patterns[3], "wrap", "long", preset.goalkeeper[0], preset.goalkeeper[1], shortCode),
  };
}

export function buildClubDNA(
  clubName: string,
  cityName: string,
  countryCode: string,
  recruitmentFocus: string,
  preferredAgeBracket: string,
  nationalityFocus: string,
) {
  const policy: Record<string, { philosophy: string; transfer: string; finance: string; narrative: string }> = {
    youth: { philosophy: "youth_development", transfer: "buy_young_develop_sell", finance: "balanced", narrative: "developing young talent and building a lasting football legacy" },
    academy: { philosophy: "academy_first", transfer: "academy_production", finance: "academy_focused", narrative: "bringing home-grown academy graduates into the first team" },
    selling: { philosophy: "selling_club", transfer: "buy_young_develop_sell", finance: "sustainable", narrative: "finding undervalued players, developing them and selling at the right moment" },
    superstars: { philosophy: "superstar", transfer: "superstars", finance: "big_spending", narrative: "competing for the biggest names and the highest honours" },
    sustainable: { philosophy: "financially_sustainable", transfer: "buy_undervalued", finance: "sustainable", narrative: "building a competitive club through careful scouting and disciplined spending" },
    balanced: { philosophy: "balanced", transfer: "buy_undervalued", finance: "balanced", narrative: "balancing promising young players with experienced professionals" },
  };
  const selected = policy[recruitmentFocus] || policy.youth;
  const preferredMaxAge = preferredAgeBracket === "none" ? null : Number(preferredAgeBracket.replace("U", "")) || 23;
  return {
    primary_philosophy: selected.philosophy,
    secondary_philosophies: ["financially_sustainable"],
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

export function kitSwatchDataUri(kit: KitVariant): string {
  const shirtPath = "M36 24 L48 12 L62 20 L76 12 L88 24 L108 39 L97 59 L85 50 L85 116 L39 116 L39 50 L27 59 L16 39 Z";
  let pattern = "";
  if (kit.pattern_type === "stripes") {
    pattern = '<path d="M45 24 H52 V116 H45 Z M65 22 H72 V116 H65 Z M81 25 H85 V116 H81 Z" fill="' + kit.secondary_color + '" opacity=".85"/>';
  } else if (kit.pattern_type === "hoops") {
    pattern = '<path d="M25 48 H98 V58 H25 Z M30 72 H94 V82 H30 Z M37 96 H87 V106 H37 Z" fill="' + kit.secondary_color + '" opacity=".9"/>';
  } else if (kit.pattern_type === "sash") {
    pattern = '<path d="M27 38 L43 27 L101 94 L89 108 Z" fill="' + kit.secondary_color + '" opacity=".92"/>';
  } else if (kit.pattern_type === "chevron") {
    pattern = '<path d="M31 45 L61 68 L92 45 L96 56 L61 83 L27 56 Z M38 85 L61 103 L84 85 L87 95 L61 114 L35 95 Z" fill="' + kit.secondary_color + '" opacity=".9"/>';
  } else if (kit.pattern_type === "gradient") {
    pattern = '<path d="' + shirtPath + '" fill="url(#kit-gradient)" opacity=".85"/>';
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 124 130" width="124" height="130">
    <defs>
      <linearGradient id="kit-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${kit.secondary_color}" stop-opacity=".1"/><stop offset="1" stop-color="${kit.secondary_color}" stop-opacity=".95"/></linearGradient>
      <clipPath id="shirt-clip"><path d="${shirtPath}"/></clipPath>
      <filter id="kit-shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#000" flood-opacity=".35"/></filter>
    </defs>
    <g filter="url(#kit-shadow)">
      <path d="${shirtPath}" fill="${kit.primary_color}" stroke="${kit.accent_color}" stroke-width="4" stroke-linejoin="round"/>
      <g clip-path="url(#shirt-clip)">${pattern}</g>
      <path d="M48 13 L62 28 L76 13" fill="none" stroke="${kit.accent_color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M39 50 L27 59 M85 50 L97 59" stroke="${kit.accent_color}" stroke-width="3" fill="none"/>
      <circle cx="73" cy="54" r="5" fill="${kit.secondary_color}" stroke="${kit.accent_color}" stroke-width="1.5"/>
      <path d="M53 32 H70" stroke="${kit.secondary_color}" stroke-width="3" stroke-linecap="round" opacity=".9"/>
    </g>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

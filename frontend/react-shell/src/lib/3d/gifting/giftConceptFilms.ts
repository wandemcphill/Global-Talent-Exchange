import type { InspectionFrame } from "@/lib/showroomInspection";

const FILM_BY_SHOT: Record<string, string> = {
  atmosphere: "gtex-gift-atmosphere.mp4",
  card: "gtex-gift-card.mp4",
  tactics: "gtex-gift-tactics.mp4",
  crown: "gtex-gift-crown.mp4",
  trophy: "gtex-gift-trophy.mp4",
  boot: "gtex-gift-boot.mp4",
  glove: "gtex-gift-glove.mp4",
  stadium: "gtex-maracana-gift.mp4",
  city: "gtex-gift-city.mp4",
  jet: "gtex-gift-jet.mp4",
  yacht: "gtex-gift-yacht.mp4",
  coach: "gtex-gift-coach.mp4",
  vehicle: "gtex-gift-hypercar.mp4",
  facility: "gtex-gift-campus.mp4",
  goal: "gtex-gift-goal.mp4",
  last_minute: "gtex-gift-last-minute.mp4",
  bicycle: "gtex-gift-bicycle.mp4",
  golden_goal: "gtex-gift-golden-goal.mp4",
  hat_trick: "gtex-gift-hat-trick.mp4",
  save: "gtex-gift-save.mp4",
};

export function giftConceptFilm(shot: string): InspectionFrame {
  const file = FILM_BY_SHOT[shot] || FILM_BY_SHOT.atmosphere;
  return {
    label: shot,
    kind: "video",
    src: `/assets/gifting/films/${file}`,
  };
}

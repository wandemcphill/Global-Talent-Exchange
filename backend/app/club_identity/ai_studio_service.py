from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from typing import Any

from app.club_identity.crest_svg_builder import render_crest_svg
from app.models.club_dna import (
    DNAPhilosophy,
    FinancialPhilosophy,
    PolicyAgeMode,
    PolicyNationalityMode,
    TransferStrategy,
)


@dataclass(slots=True)
class CrestConcept:
    concept_id: str
    shape: str
    icon_family: str
    primary_color: str
    secondary_color: str
    accent_color: str
    initials: str
    style: str
    trophy_stars: int
    visual_meaning: str
    design_explanation: str
    svg_markup: str
    data_uri: str


@dataclass(slots=True)
class KitConcept:
    jersey_type: str  # home, away, third, goalkeeper
    pattern_type: str  # solid, stripes, hoops, sash, chevron, gradient
    collar_style: str  # crew, v_neck, polo, wrap
    sleeve_style: str  # short, long, raglan, cuffed
    primary_color: str
    secondary_color: str
    accent_color: str
    shorts_color: str
    socks_color: str
    front_text: str
    crest_url: str | None = None
    sponsor_name: str | None = "GTEX GLOBAL"
    manufacturer_logo: str | None = "GTEX ATHLETICS"


@dataclass(slots=True)
class StudioRecommendationBundle:
    club_name: str
    short_code: str
    vision_narrative: str
    primary_philosophy: str
    secondary_philosophies: list[str]
    nationality_mode: str
    target_nationalities: list[str]
    age_mode: str
    preferred_max_age: int | None
    transfer_strategy: str
    financial_philosophy: str
    crest_concepts: list[CrestConcept]
    kit_concepts: dict[str, KitConcept]


def _to_data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def _derive_initials(club_name: str) -> str:
    words = [w.strip() for w in club_name.split() if w.strip()]
    if not words:
        return "FC"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:4]).upper()


class ClubIdentityStudioService:
    def generate_recommendation_bundle(
        self,
        *,
        club_name: str,
        country_code: str | None = "FRA",
        city_name: str | None = "Lyon",
        preferred_style: str = "traditional",
        recruitment_focus: str = "youth",  # youth, academy, selling, superstars, sustainable, balanced
        preferred_age_bracket: str = "U23",
        nationality_focus: str = "preferred",  # none, preferred, exclusive
    ) -> StudioRecommendationBundle:
        initials = _derive_initials(club_name)
        norm_country = (country_code or "FRA").strip().upper()
        norm_city = city_name or "Metropolis"

        # 1. Calibrate Club DNA based on user answers
        if recruitment_focus == "academy":
            primary_phil = DNAPhilosophy.ACADEMY_FIRST.value
            sec_phils = [DNAPhilosophy.YOUTH_DEVELOPMENT.value, DNAPhilosophy.FINANCIALLY_SUSTAINABLE.value]
            strat = TransferStrategy.ACADEMY_PRODUCTION.value
            fin = FinancialPhilosophy.ACADEMY_FOCUSED.value
            narrative = f"{club_name} is an elite academy-first football club rooted in {norm_city}, dedicated to producing world-class home-grown footballers through world-leading training facilities."
        elif recruitment_focus == "selling":
            primary_phil = DNAPhilosophy.SELLING_CLUB.value
            sec_phils = [DNAPhilosophy.YOUTH_DEVELOPMENT.value, DNAPhilosophy.FINANCIALLY_SUSTAINABLE.value]
            strat = TransferStrategy.BUY_YOUNG_DEVELOP_SELL.value
            fin = FinancialPhilosophy.SUSTAINABLE.value
            narrative = f"{club_name} operates a high-efficiency development model in {norm_city}: discovering undervalued prodigies, maximizing their market value, and generating sustainable growth through strategic player transfers."
        elif recruitment_focus == "superstars":
            primary_phil = DNAPhilosophy.SUPERSTAR.value
            sec_phils = [DNAPhilosophy.BIG_SPENDING.value]
            strat = TransferStrategy.SUPERSTARS.value
            fin = FinancialPhilosophy.BIG_SPENDING.value
            narrative = f"{club_name} is an ambitious, high-profile football superpower assembled to compete at the summit of world football with elite international icons and championship pedigree."
        elif recruitment_focus == "sustainable":
            primary_phil = DNAPhilosophy.FINANCIALLY_SUSTAINABLE.value
            sec_phils = [DNAPhilosophy.BALANCED.value]
            strat = TransferStrategy.BUY_UNDERVALUED.value
            fin = FinancialPhilosophy.SUSTAINABLE.value
            narrative = f"{club_name} balances sporting competitiveness with long-term fiscal discipline, emphasizing smart scouting, performance metrics, and sustainable squad building."
        else:  # youth (default)
            primary_phil = DNAPhilosophy.YOUTH_DEVELOPMENT.value
            sec_phils = [DNAPhilosophy.ACADEMY_FIRST.value, DNAPhilosophy.BALANCED.value]
            strat = TransferStrategy.BUY_YOUNG_DEVELOP_SELL.value
            fin = FinancialPhilosophy.BALANCED.value
            narrative = f"{club_name} is an ambitious football institution in {norm_city} focused on nurturing young domestic talent, developing agile squads, and building enduring club legacy."

        # Age settings
        age_map = {"U18": 18, "U21": 21, "U23": 23, "U25": 25, "U27": 27}
        preferred_max = age_map.get(preferred_age_bracket, 23)
        age_mode = PolicyAgeMode.PREFERRED.value if preferred_age_bracket != "none" else PolicyAgeMode.NONE.value

        # Nationality mode
        nat_mode = (
            PolicyNationalityMode.EXCLUSIVE.value
            if nationality_focus == "exclusive"
            else (PolicyNationalityMode.PREFERRED.value if nationality_focus == "preferred" else PolicyNationalityMode.NONE.value)
        )
        target_nats = [norm_country] if norm_country and nat_mode != PolicyNationalityMode.NONE.value else []

        # 2. Generate 3 Distinct Crest Concepts
        crest_concepts: list[CrestConcept] = []

        # Concept 1: Traditional Shield & Lion (Heritage)
        c1_svg = render_crest_svg(
            shape="shield",
            primary_color="#1E3A8A",  # Royal Blue
            secondary_color="#FFFFFF",
            accent_color="#F59E0B",  # Gold
            initials=initials,
            icon_family="lion",
            trophy_stars=1,
            style="traditional",
        )
        crest_concepts.append(
            CrestConcept(
                concept_id="concept-traditional-shield",
                shape="shield",
                icon_family="lion",
                primary_color="#1E3A8A",
                secondary_color="#FFFFFF",
                accent_color="#F59E0B",
                initials=initials,
                style="traditional",
                trophy_stars=1,
                visual_meaning="Classic European royal shield representing bravery, sovereignty, and football heritage.",
                design_explanation="A robust heraldic shield crowned with a championship star and a defiant lion emblem.",
                svg_markup=c1_svg,
                data_uri=_to_data_uri(c1_svg),
            )
        )

        # Concept 2: Modern Round & Eagle (Power / Athletic)
        c2_svg = render_crest_svg(
            shape="round",
            primary_color="#0F5132",  # Forest Emerald
            secondary_color="#F8FAFC",
            accent_color="#10B981",  # Vivid Mint
            initials=initials,
            icon_family="eagle",
            trophy_stars=0,
            style="modern",
        )
        crest_concepts.append(
            CrestConcept(
                concept_id="concept-modern-round",
                shape="round",
                icon_family="eagle",
                primary_color="#0F5132",
                secondary_color="#F8FAFC",
                accent_color="#10B981",
                initials=initials,
                style="modern",
                trophy_stars=0,
                visual_meaning="Concentric roundel badge signifying unity, relentless aerial vision, and modern football athleticism.",
                design_explanation="A streamlined circular crest with dashed tactical orbit lines and an aggressive eagle motif.",
                svg_markup=c2_svg,
                data_uri=_to_data_uri(c2_svg),
            )
        )

        # Concept 3: Metallic Diamond & Crown (Prestige / Sovereign)
        c3_svg = render_crest_svg(
            shape="diamond",
            primary_color="#7F1D1D",  # Deep Crimson
            secondary_color="#FEF3C7",
            accent_color="#D97706",  # Amber Gold
            initials=initials,
            icon_family="crown",
            trophy_stars=2,
            style="metallic",
        )
        crest_concepts.append(
            CrestConcept(
                concept_id="concept-metallic-diamond",
                shape="diamond",
                icon_family="crown",
                primary_color="#7F1D1D",
                secondary_color="#FEF3C7",
                accent_color="#D97706",
                initials=initials,
                style="metallic",
                trophy_stars=2,
                visual_meaning="Prestige rhombus geometry showcasing coronation, elite status, and unwavering championship aspiration.",
                design_explanation="A bevelled diamond shield with metallic gold borders and an embossed royal crown.",
                svg_markup=c3_svg,
                data_uri=_to_data_uri(c3_svg),
            )
        )

        # 3. Generate 4 Kit Concepts
        chosen_crest = crest_concepts[0]
        kits = {
            "home": KitConcept(
                jersey_type="home",
                pattern_type="stripes",
                collar_style="crew",
                sleeve_style="short",
                primary_color=chosen_crest.primary_color,
                secondary_color=chosen_crest.secondary_color,
                accent_color=chosen_crest.accent_color,
                shorts_color=chosen_crest.primary_color,
                socks_color=chosen_crest.secondary_color,
                front_text=initials,
                crest_url=chosen_crest.data_uri,
            ),
            "away": KitConcept(
                jersey_type="away",
                pattern_type="sash",
                collar_style="v_neck",
                sleeve_style="raglan",
                primary_color="#F8FAFC",  # Clean pearl white
                secondary_color=chosen_crest.primary_color,
                accent_color=chosen_crest.accent_color,
                shorts_color="#F8FAFC",
                socks_color=chosen_crest.primary_color,
                front_text=initials,
                crest_url=chosen_crest.data_uri,
            ),
            "third": KitConcept(
                jersey_type="third",
                pattern_type="chevron",
                collar_style="polo",
                sleeve_style="short",
                primary_color="#0F172A",  # Midnight black/slate
                secondary_color=chosen_crest.accent_color,
                accent_color="#38BDF8",  # Electric sky blue
                shorts_color="#0F172A",
                socks_color="#0F172A",
                front_text=f"{initials} 3RD",
                crest_url=chosen_crest.data_uri,
            ),
            "goalkeeper": KitConcept(
                jersey_type="goalkeeper",
                pattern_type="gradient",
                collar_style="wrap",
                sleeve_style="long",
                primary_color="#10B981",  # High-vis emerald green
                secondary_color="#064E3B",
                accent_color="#FACC15",
                shorts_color="#064E3B",
                socks_color="#10B981",
                front_text=f"{initials} GK",
                crest_url=chosen_crest.data_uri,
            ),
        }

        return StudioRecommendationBundle(
            club_name=club_name,
            short_code=initials,
            vision_narrative=narrative,
            primary_philosophy=primary_phil,
            secondary_philosophies=sec_phils,
            nationality_mode=nat_mode,
            target_nationalities=target_nats,
            age_mode=age_mode,
            preferred_max_age=preferred_max,
            transfer_strategy=strat,
            financial_philosophy=fin,
            crest_concepts=crest_concepts,
            kit_concepts=kits,
        )

    def apply_conversational_edit(
        self,
        *,
        current_kit: dict[str, Any],
        current_crest: dict[str, Any],
        instruction: str,
    ) -> dict[str, Any]:
        """Apply natural language instruction safely to structured kit & crest design parameters."""
        prompt = instruction.lower().strip()
        updated_kit = dict(current_kit)
        updated_crest = dict(current_crest)
        changes_applied: list[str] = []

        # Color changes
        if "gold" in prompt and "blue" in prompt:
            updated_kit["primary_color"] = "#0F172A"
            updated_kit["secondary_color"] = "#1E3A8A"
            updated_kit["accent_color"] = "#F59E0B"
            updated_crest["primary_color"] = "#1E3A8A"
            updated_crest["accent_color"] = "#F59E0B"
            changes_applied.append("Set primary color to navy/dark blue and accents to gold.")
        elif "black" in prompt:
            updated_kit["primary_color"] = "#090D14"
            updated_kit["shorts_color"] = "#090D14"
            changes_applied.append("Switched kit base to carbon black.")
        elif "green" in prompt or "emerald" in prompt:
            updated_kit["primary_color"] = "#047857"
            updated_crest["primary_color"] = "#047857"
            changes_applied.append("Updated kit and crest primary tone to emerald green.")
        elif "red" in prompt or "crimson" in prompt:
            updated_kit["primary_color"] = "#991B1B"
            updated_crest["primary_color"] = "#991B1B"
            changes_applied.append("Updated kit and crest primary tone to crimson red.")
        elif "white" in prompt:
            updated_kit["primary_color"] = "#F8FAFC"
            updated_kit["secondary_color"] = "#0F172A"
            changes_applied.append("Updated primary color to clean white.")

        # Pattern changes
        if "stripes" in prompt:
            updated_kit["pattern_type"] = "stripes"
            changes_applied.append("Applied vertical stripes pattern.")
        elif "hoops" in prompt:
            updated_kit["pattern_type"] = "hoops"
            changes_applied.append("Applied horizontal hoops pattern.")
        elif "sash" in prompt or "diagonal" in prompt:
            updated_kit["pattern_type"] = "sash"
            changes_applied.append("Applied diagonal sash pattern.")
        elif "chevron" in prompt or "v-shape" in prompt:
            updated_kit["pattern_type"] = "chevron"
            changes_applied.append("Applied chest chevron pattern.")
        elif "gradient" in prompt:
            updated_kit["pattern_type"] = "gradient"
            changes_applied.append("Applied vertical gradient fade pattern.")
        elif "solid" in prompt or "clean" in prompt:
            updated_kit["pattern_type"] = "solid"
            changes_applied.append("Set jersey body to solid clean fabric.")

        # Crest shape & style
        if "traditional" in prompt or "heritage" in prompt:
            updated_crest["shape"] = "shield"
            updated_crest["icon_family"] = "lion"
            updated_crest["style"] = "traditional"
            changes_applied.append("Changed crest to traditional shield with heraldic lion.")
        elif "modern" in prompt or "sleek" in prompt:
            updated_crest["shape"] = "round"
            updated_crest["icon_family"] = "eagle"
            updated_crest["style"] = "modern"
            changes_applied.append("Changed crest to modern roundel with streamlined eagle.")
        elif "metallic" in prompt or "crown" in prompt or "royal" in prompt:
            updated_crest["shape"] = "diamond"
            updated_crest["icon_family"] = "crown"
            updated_crest["style"] = "metallic"
            changes_applied.append("Applied metallic diamond crest with royal crown.")

        # Collar & Sleeve
        if "polo" in prompt or "collar" in prompt:
            updated_kit["collar_style"] = "polo"
            changes_applied.append("Updated collar to classic polo.")
        elif "v-neck" in prompt or "v neck" in prompt:
            updated_kit["collar_style"] = "v_neck"
            changes_applied.append("Updated collar to modern V-neck.")
        elif "long sleeve" in prompt:
            updated_kit["sleeve_style"] = "long"
            changes_applied.append("Configured long sleeves.")

        # Re-render updated SVG
        new_svg = render_crest_svg(
            shape=updated_crest.get("shape", "shield"),
            primary_color=updated_crest.get("primary_color", "#1E3A8A"),
            secondary_color=updated_crest.get("secondary_color", "#FFFFFF"),
            accent_color=updated_crest.get("accent_color", "#F59E0B"),
            initials=updated_crest.get("initials", "FC"),
            icon_family=updated_crest.get("icon_family", "lion"),
            trophy_stars=int(updated_crest.get("trophy_stars", 1)),
            style=updated_crest.get("style", "traditional"),
        )
        updated_crest["svg_markup"] = new_svg
        updated_crest["data_uri"] = _to_data_uri(new_svg)
        updated_kit["crest_url"] = updated_crest["data_uri"]

        if not changes_applied:
            changes_applied.append("Design refined to match requested visual tone.")

        return {
            "kit": updated_kit,
            "crest": updated_crest,
            "summary": " ".join(changes_applied),
        }

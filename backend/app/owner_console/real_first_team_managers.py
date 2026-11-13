"""Real head coaches the staff market was missing.

The manager catalogue already named hundreds of real coaches. The hireable
staff market did not. This module turns those people into first-team managers
and adds the active and legendary coaches who were absent from both lists.
"""

from __future__ import annotations

import unicodedata
import zlib
from typing import Any

# Folded spelling -> the one person that spelling refers to.
ALIASES = {
    "gus hiddink": "guus hiddink",
    "rohr gernot": "gernot rohr",
    "tata martino": "gerardo martino",
    "xavi": "xavi hernandez",
    "jose pekerman": "nestor pekerman",
    "leonel scaloni": "lionel scaloni",
}

WOMEN = {
    "sarina wiegman",
    "emma hayes",
    "pia sundhage",
    "jill ellis",
    "sonia bompastor",
    "silvia neid",
    "hope powell",
    "corinne diacre",
    "martina voss tecklenburg",
}

# Used when an existing catalogue row is already a first-team manager but the
# stored rating hides a great coach on the opening page of the market.
RATING_FLOORS: dict[str, dict[str, Any]] = {
    "johan cruyff": {
        "rating": 94,
        "rarity": "legendary",
        "style": "Total Football",
        "temperament": "demanding",
        "mentality": "technical",
        "preferred_formation": "4-3-3",
        "preferred_formations": ["4-3-3", "3-4-3"],
        "tactics": ["possession_control", "technical_build_up", "inverted_wingers"],
        "traits": ["technical_coaching", "expressive_freedom", "develops_young_players", "quick_substitution"],
        "philosophy_summary": "Positional rotations, a high line, and attackers who receive between the lines.",
        "bio": "Johan Cruyff built teams around the ball: short passing, constant movement, and a high defensive line.",
    },
    "jose mourinho": {
        "rating": 92,
        "rarity": "legendary",
        "style": "Organised Counter",
        "temperament": "demanding",
        "mentality": "pragmatic",
        "preferred_formation": "4-2-3-1",
        "preferred_formations": ["4-2-3-1", "4-3-3"],
        "tactics": ["compact_midblock", "counter_attack", "set_piece_focus"],
        "traits": ["defensive_organization", "strict_structure", "manages_elite_stars", "late_substitution"],
        "philosophy_summary": "A compact block, fast breaks, and set pieces treated as a planned attack.",
        "bio": "José Mourinho wins by organisation: a low block, two screening midfielders, and attacks that start the moment the ball is won.",
    },
    "kenny dalglish": {
        "rating": 88,
        "rarity": "legendary",
        "style": "Direct Wing Play",
        "temperament": "calm",
        "mentality": "attacking",
        "preferred_formation": "4-4-2",
        "preferred_formations": ["4-4-2", "4-3-3"],
        "tactics": ["wing_play", "elite_star_freedom", "technical_build_up"],
        "traits": ["manages_elite_stars", "technical_coaching", "balanced_substitution", "tactical_flexibility"],
        "philosophy_summary": "Forward passing, wide overloads, and strikers given room to combine.",
        "bio": "Kenny Dalglish's teams played forward early and trusted wide players to make the final pass.",
    },
    "herve renard": {
        "rating": 82,
        "rarity": "elite",
        "style": "Tournament Structure",
        "temperament": "demanding",
        "mentality": "pragmatic",
        "preferred_formation": "4-2-3-1",
        "preferred_formations": ["4-2-3-1", "4-4-2"],
        "tactics": ["compact_midblock", "set_piece_focus", "counter_attack"],
        "traits": ["defensive_organization", "improves_player_discipline", "strict_structure", "balanced_substitution"],
        "philosophy_summary": "Clear roles, a compact shape, and set pieces as a scoring plan.",
        "bio": "Hervé Renard made Zambia and Ivory Coast hard to play through, then won two Africa Cup of Nations with that structure.",
    },
}


def fold_name(name: str | None) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().replace("'", "").replace("’", "").replace("-", " ").split())


def canon_fold(name: str | None) -> str:
    folded = fold_name(name)
    return ALIASES.get(folded, folded)


def _coach(
    name: str,
    nation: str,
    rarity: str,
    rating: int,
    mentality: str,
    tactics: list[str],
    traits: list[str],
    philosophy: str,
    clubs: list[str],
    *,
    age: int | None = None,
    gender: str = "male",
    style: str | None = None,
    formation: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "nation": nation,
        "rarity": rarity,
        "rating": rating,
        "mentality": mentality,
        "tactics": tactics,
        "traits": traits,
        "philosophy": philosophy,
        "club_associations": clubs,
        "age": age,
        "gender": gender,
        "style": style,
        "preferred_formation": formation,
    }


EXTRA_SEED_RECORDS: list[dict[str, Any]] = [
    _coach("Bob Paisley", "England", "legendary", 93, "balanced", ["wing_play", "compact_midblock", "set_piece_focus"], ["tactical_flexibility", "balanced_substitution", "manages_elite_stars", "improves_player_discipline"], "Simple shapes, early passing into the box, and a squad rotated before it broke.", ["Liverpool"], style="Boot Room Control", formation="4-4-2"),
    _coach("Bill Shankly", "Scotland", "legendary", 92, "attacking", ["wing_play", "high_press_attack", "direct_long_ball"], ["improves_player_discipline", "boosts_physicality_focus", "quick_substitution", "strict_structure"], "High tempo, wide runners, and a team that treated the pass as a shared job.", ["Liverpool"], style="Pass and Move", formation="4-4-2"),
    _coach("Matt Busby", "Scotland", "legendary", 92, "attacking", ["wing_play", "youth_development_system", "technical_build_up"], ["develops_young_players", "academy_promotion_bias", "expressive_freedom", "technical_coaching"], "Babes before fame: young players trusted in a 4-2-4 that attacked both flanks.", ["Manchester United"], style="Youth Attack", formation="4-2-4"),
    _coach("Alf Ramsey", "England", "legendary", 91, "pragmatic", ["compact_midblock", "wing_play", "set_piece_focus"], ["strict_structure", "defensive_organization", "tactical_flexibility", "late_substitution"], "The wingless 4-4-2: full-backs who joined midfield and a block that did not chase the ball.", ["England", "Ipswich Town"], style="Wingless Control", formation="4-4-2"),
    _coach("Jock Stein", "Scotland", "legendary", 91, "attacking", ["high_press_attack", "wing_play", "set_piece_focus"], ["improves_player_discipline", "quick_substitution", "boosts_physicality_focus", "develops_young_players"], "Fast, brave football and a back line told to step up together.", ["Celtic"], style="Lisbon Lions", formation="4-2-4"),
    _coach("Herbert Chapman", "England", "legendary", 90, "pragmatic", ["compact_midblock", "counter_attack", "technical_build_up"], ["tactical_flexibility", "strict_structure", "defensive_organization", "technical_coaching"], "The W-M and a third-back who organised the rest of the team.", ["Arsenal", "Huddersfield Town"], style="Third-Back Game", formation="3-2-2-3"),
    _coach("Bill Nicholson", "England", "legendary", 89, "attacking", ["wing_play", "technical_build_up", "high_press_attack"], ["technical_coaching", "develops_young_players", "quick_substitution", "expressive_freedom"], "Push and run: one-twos, overlapping full-backs, and wingers who scored.", ["Tottenham"], style="Push and Run", formation="4-3-3"),
    _coach("Sir Bobby Robson", "England", "legendary", 90, "balanced", ["wing_play", "possession_control", "youth_development_system"], ["develops_young_players", "tactical_flexibility", "technical_coaching", "balanced_substitution"], "Wide attacks, a midfield that kept the ball, and young players brought in beside stars.", ["Ipswich Town", "England", "Barcelona", "Newcastle"], style="Wide Build-Up", formation="4-4-2"),
    _coach("Ron Greenwood", "England", "legendary", 86, "technical", ["possession_control", "technical_build_up", "wing_play"], ["technical_coaching", "develops_young_players", "expressive_freedom", "balanced_substitution"], "Football from the back, full-backs in the build-up, and wingers staying wide.", ["West Ham", "England"], style="Play Out", formation="4-4-2"),
    _coach("Don Revie", "England", "legendary", 88, "pragmatic", ["compact_midblock", "set_piece_focus", "counter_attack"], ["strict_structure", "defensive_organization", "boosts_physicality_focus", "improves_player_discipline"], "A dossier on every opponent and a 4-4-2 that was hard to play through.", ["Leeds United"], style="Dossier 4-4-2", formation="4-4-2"),
    _coach("Ernst Happel", "Austria", "legendary", 93, "pragmatic", ["compact_midblock", "counter_attack", "set_piece_focus"], ["defensive_organization", "strict_structure", "tactical_flexibility", "late_substitution"], "Man-marking when it suited, a sweeper behind, and breaks that finished quickly.", ["Feyenoord", "Hamburg", "Netherlands"], style="Sweeper Control", formation="1-3-3-3"),
    _coach("Béla Guttmann", "Hungary", "legendary", 91, "attacking", ["wing_play", "technical_build_up", "high_press_attack"], ["technical_coaching", "expressive_freedom", "quick_substitution", "manages_elite_stars"], "The 4-2-4 with inside-forwards and full-backs who attacked the space they left.", ["Benfica"], style="Four-Two-Four", formation="4-2-4"),
    _coach("Helmut Schön", "Germany", "legendary", 93, "balanced", ["possession_control", "wing_play", "compact_midblock"], ["tactical_flexibility", "manages_elite_stars", "balanced_substitution", "technical_coaching"], "A flexible 4-3-3 that could sit in and then flood one flank.", ["West Germany"], style="Tournament Flexibility", formation="4-3-3"),
    _coach("Sepp Herberger", "Germany", "legendary", 90, "pragmatic", ["counter_attack", "compact_midblock", "set_piece_focus"], ["tactical_flexibility", "strict_structure", "defensive_organization", "late_substitution"], "The match is 90 minutes: save the real shape for the half that decides it.", ["West Germany"], style="Match Management", formation="3-2-5"),
    _coach("Vittorio Pozzo", "Italy", "legendary", 92, "pragmatic", ["compact_midblock", "direct_long_ball", "counter_attack"], ["strict_structure", "defensive_organization", "improves_player_discipline", "boosts_physicality_focus"], "The metodo: a centre-half dropped in, and two inside-forwards attacking the gaps.", ["Italy"], style="Metodo", formation="2-3-2-3"),
    _coach("Miguel Muñoz", "Spain", "legendary", 88, "attacking", ["wing_play", "elite_star_freedom", "technical_build_up"], ["manages_elite_stars", "technical_coaching", "expressive_freedom", "balanced_substitution"], "Stars given a 4-2-4 and told to attack both sides at once.", ["Real Madrid"], style="European Attack", formation="4-2-4"),
    _coach("Dettmar Cramer", "Germany", "legendary", 86, "technical", ["possession_control", "technical_build_up", "youth_development_system"], ["technical_coaching", "develops_young_players", "tactical_flexibility", "balanced_substitution"], "Detail coaching: body shape, the first pass, and a team that could keep the ball under pressure.", ["Bayern Munich", "Japan"], style="Detail Coaching", formation="4-3-3"),
    _coach("Jupp Heynckes", "Germany", "legendary", 92, "attacking", ["wing_play", "high_press_attack", "possession_control"], ["tactical_flexibility", "quick_substitution", "manages_elite_stars", "technical_coaching"], "Wide wingers, full-backs beyond them, and a press that started at the striker.", ["Bayern Munich", "Real Madrid"], age=81, style="Wide Press", formation="4-2-3-1"),
    _coach("Joachim Löw", "Germany", "legendary", 90, "possession", ["possession_control", "inverted_wingers", "high_press_attack"], ["technical_coaching", "tactical_flexibility", "develops_young_players", "quick_substitution"], "Build through the goalkeeper, inverted wingers, and a high line that squeezed the game.", ["Germany"], age=66, style="Positional Attack", formation="4-2-3-1"),
    _coach("Otto Rehhagel", "Germany", "legendary", 89, "defensive", ["low_block_counter", "compact_midblock", "set_piece_focus"], ["defensive_organization", "strict_structure", "improves_player_discipline", "late_substitution"], "A narrow block, two banks of four, and breaks that used the one free runner.", ["Greece", "Werder Bremen"], age=88, style="Narrow Block", formation="4-4-2"),
    _coach("Lionel Scaloni", "Argentina", "elite_active", 91, "balanced", ["compact_midblock", "wing_play", "counter_attack"], ["tactical_flexibility", "manages_elite_stars", "defensive_organization", "balanced_substitution"], "A back five that becomes a back four, wing-backs who join late, and Messi's side of the pitch left open on purpose.", ["Argentina"], age=48, style="Flexible Back Line", formation="4-3-3"),
    _coach("Simone Inzaghi", "Italy", "elite_active", 88, "attacking", ["wing_play", "overlapping_fullbacks", "set_piece_focus"], ["tactical_flexibility", "quick_substitution", "technical_coaching", "manages_elite_stars"], "A 3-5-2 with wing-backs as the width and strikers who attack the near post on set pieces.", ["Inter", "Lazio"], age=50, style="Wing-Back 3-5-2", formation="3-5-2"),
    _coach("Gian Piero Gasperini", "Italy", "elite_active", 87, "pressing", ["high_press_attack", "overlapping_fullbacks", "wing_play"], ["tactical_flexibility", "quick_substitution", "develops_young_players", "technical_coaching"], "Man-to-man press, a back three, and wide midfielders who arrive in the box.", ["Atalanta"], age=68, style="Man-to-Man Press", formation="3-4-2-1"),
    _coach("Luis de la Fuente", "Spain", "elite_active", 86, "possession", ["possession_control", "wing_play", "technical_build_up"], ["technical_coaching", "develops_young_players", "tactical_flexibility", "balanced_substitution"], "Spain's wide 4-3-3: wingers on the touchline and midfielders who pass through pressure.", ["Spain"], age=65, style="Wide Spain", formation="4-3-3"),
    _coach("Gareth Southgate", "England", "popular", 84, "pragmatic", ["compact_midblock", "wing_play", "set_piece_focus"], ["defensive_organization", "balanced_substitution", "improves_player_discipline", "manages_elite_stars"], "A back three in the biggest games, wing-backs for width, and a midfield that protected the centre.", ["England"], age=56, style="Tournament Back Three", formation="3-4-3"),
    _coach("Erik ten Hag", "Netherlands", "elite_active", 84, "possession", ["possession_control", "high_press_attack", "wing_play"], ["technical_coaching", "strict_structure", "quick_substitution", "develops_young_players"], "Build through the half-spaces and press the moment the pass goes backwards.", ["Ajax", "Manchester United"], age=56, style="Half-Space Press", formation="4-2-3-1"),
    _coach("Xavi Hernández", "Spain", "popular", 84, "possession", ["possession_control", "technical_build_up", "inverted_wingers"], ["technical_coaching", "expressive_freedom", "develops_young_players", "tactical_flexibility"], "Short passing, a high full-back, and the ball moved until a lane into the box appeared.", ["Barcelona"], age=46, style="Short Passing", formation="4-3-3"),
    _coach("Thiago Motta", "Brazil", "popular", 82, "possession", ["possession_control", "double_pivot_control", "technical_build_up"], ["technical_coaching", "tactical_flexibility", "develops_young_players", "balanced_substitution"], "Many players between the lines, a fluid midfield, and the build started from the centre-backs.", ["Bologna", "Juventus"], age=44, style="Fluid Midfield", formation="4-2-3-1"),
    _coach("Andoni Iraola", "Spain", "popular", 83, "pressing", ["high_press_attack", "gegenpress", "wing_play"], ["quick_substitution", "boosts_physicality_focus", "tactical_flexibility", "technical_coaching"], "Man-oriented press, direct runs in behind, and full-backs who join the first wave.", ["Bournemouth", "Rayo Vallecano"], age=47, style="Man-Oriented Press", formation="4-2-3-1"),
    _coach("Régis Le Bris", "France", "popular", 80, "possession", ["possession_control", "technical_build_up", "wing_play"], ["technical_coaching", "develops_young_players", "tactical_flexibility", "balanced_substitution"], "Patient build-up, a single pivot, and wingers who come short to receive.", ["Sunderland", "Lorient"], age=50, style="Patient Build-Up", formation="4-3-3"),
    _coach("Vítor Pereira", "Portugal", "popular", 80, "pragmatic", ["compact_midblock", "wing_play", "counter_attack"], ["defensive_organization", "strict_structure", "balanced_substitution", "tactical_flexibility"], "Two banks, wide midfielders, and the ball played forward as soon as the block won it.", ["Porto", "Wolves"], age=58, style="Compact Width", formation="4-4-2"),
    _coach("Will Still", "Belgium", "popular", 78, "pressing", ["gegenpress", "high_press_attack", "wing_play"], ["quick_substitution", "develops_young_players", "boosts_physicality_focus", "tactical_flexibility"], "A young high press, straight passing, and substitutions before the hour.", ["Lens", "Reims"], age=34, style="Young Press", formation="4-2-3-1"),
    _coach("Liam Rosenior", "England", "popular", 79, "possession", ["possession_control", "technical_build_up", "inverted_wingers"], ["technical_coaching", "develops_young_players", "tactical_flexibility", "balanced_substitution"], "Play out from the back and invert a full-back so the pivot has a free angle.", ["Strasbourg", "Hull City"], age=42, style="Play From the Back", formation="4-3-3"),
    _coach("Enzo Maresca", "Italy", "elite_active", 84, "possession", ["possession_control", "inverted_wingers", "double_pivot_control"], ["technical_coaching", "strict_structure", "tactical_flexibility", "develops_young_players"], "A goalkeeper in the build, inverted full-backs, and wingers who stay high.", ["Chelsea", "Leicester City"], age=46, style="Inverted Build", formation="4-3-3"),
    _coach("Vincent Kompany", "Belgium", "popular", 82, "possession", ["possession_control", "high_press_attack", "technical_build_up"], ["technical_coaching", "develops_young_players", "strict_structure", "quick_substitution"], "Centre-backs who step in, a high line, and the press triggered by a backwards pass.", ["Bayern Munich", "Burnley"], age=40, style="Stepping Centre-Backs", formation="4-2-3-1"),
    _coach("Manuel Pellegrini", "Chile", "elite_active", 86, "attacking", ["possession_control", "wing_play", "elite_star_freedom"], ["manages_elite_stars", "technical_coaching", "balanced_substitution", "expressive_freedom"], "Attacking full-backs, a spare midfielder, and wingers given the freedom to go inside or stay wide.", ["Manchester City", "Real Madrid", "Betis"], age=73, style="Open Attack", formation="4-4-2"),
    _coach("Jorge Jesus", "Portugal", "elite_active", 86, "pressing", ["high_press_attack", "wing_play", "overlapping_fullbacks"], ["quick_substitution", "strict_structure", "tactical_flexibility", "boosts_physicality_focus"], "A high press, attacking full-backs, and the striker used as the first defender.", ["Benfica", "Flamengo"], age=72, style="High Full-Backs", formation="4-4-2"),
    _coach("Rafael Benítez", "Spain", "legendary", 90, "pragmatic", ["compact_midblock", "counter_attack", "set_piece_focus"], ["defensive_organization", "tactical_flexibility", "strict_structure", "late_substitution"], "Match plans written around the opponent, a compact 4-2-3-1, and set pieces rehearsed.", ["Liverpool", "Valencia", "Napoli"], age=66, style="Match Plan", formation="4-2-3-1"),
    _coach("Sérgio Conceição", "Portugal", "elite_active", 85, "pressing", ["high_press_attack", "wing_play", "counter_attack"], ["strict_structure", "boosts_physicality_focus", "quick_substitution", "improves_player_discipline"], "Intensity without the ball and wingers who attack the space behind a high line.", ["Porto"], age=51, style="Intense Press", formation="4-4-2"),
    _coach("Marcelo Gallardo", "Argentina", "elite_active", 88, "attacking", ["high_press_attack", "wing_play", "technical_build_up"], ["tactical_flexibility", "quick_substitution", "technical_coaching", "develops_young_players"], "River's 4-3-3: the No. 8 arrives late, and the press starts the attack.", ["River Plate"], age=50, style="Late Arrivals", formation="4-3-3"),
    _coach("Tite", "Brazil", "elite_active", 87, "balanced", ["possession_control", "compact_midblock", "wing_play"], ["defensive_organization", "tactical_flexibility", "manages_elite_stars", "balanced_substitution"], "A protected back four, full-backs who choose their moment, and the ball moved to the free side.", ["Brazil", "Corinthians"], age=65, style="Protected Build", formation="4-1-4-1"),
    _coach("Dorival Júnior", "Brazil", "popular", 82, "balanced", ["compact_midblock", "counter_attack", "wing_play"], ["tactical_flexibility", "defensive_organization", "balanced_substitution", "improves_player_discipline"], "A compact midfield that opens into a 4-3-3 once the ball is won.", ["Brazil", "Flamengo", "São Paulo"], age=64, style="Compact to Open", formation="4-4-2"),
    _coach("Mano Menezes", "Brazil", "popular", 80, "pragmatic", ["compact_midblock", "counter_attack", "double_pivot_control"], ["defensive_organization", "develops_young_players", "balanced_substitution", "strict_structure"], "Two screening midfielders and wide players asked to run at the full-back.", ["Brazil", "Corinthians"], age=64, style="Screen and Run", formation="4-2-3-1"),
    _coach("Vanderlei Luxemburgo", "Brazil", "popular", 81, "attacking", ["wing_play", "overlapping_fullbacks", "high_press_attack"], ["tactical_flexibility", "quick_substitution", "expressive_freedom", "technical_coaching"], "Attacking full-backs and a midfield diamond that changed within the same match.", ["Palmeiras", "Real Madrid"], age=74, style="Changing Diamond", formation="4-4-2"),
    _coach("Renato Gaúcho", "Brazil", "popular", 80, "attacking", ["wing_play", "counter_attack", "elite_star_freedom"], ["manages_elite_stars", "expressive_freedom", "balanced_substitution", "quick_substitution"], "Trust the forward line, keep a spare man in midfield, and attack as soon as the ball turns over.", ["Grêmio", "Flamengo"], age=64, style="Forward Trust", formation="4-2-3-1"),
    _coach("Jorge Sampaoli", "Argentina", "popular", 84, "pressing", ["high_press_attack", "overlapping_fullbacks", "gegenpress"], ["tactical_flexibility", "quick_substitution", "expressive_freedom", "technical_coaching"], "A back three, furious pressing, and full-backs who are really wingers.", ["Chile", "Sevilla", "Marseille"], age=66, style="Back-Three Press", formation="3-4-3"),
    _coach("Óscar Tabárez", "Uruguay", "legendary", 90, "pragmatic", ["compact_midblock", "counter_attack", "youth_development_system"], ["develops_young_players", "defensive_organization", "strict_structure", "balanced_substitution"], "The same idea for a decade: two holders, quick wingers, and a generation brought through together.", ["Uruguay"], age=79, style="Process and Block", formation="4-4-2"),
    _coach("César Luis Menotti", "Argentina", "legendary", 92, "technical", ["possession_control", "technical_build_up", "wing_play"], ["technical_coaching", "expressive_freedom", "develops_young_players", "tactical_flexibility"], "Keep the ball, attack down the left, and refuse to kick it long.", ["Argentina"], style="Left-Side Possession", formation="4-3-3"),
    _coach("Néstor Pekerman", "Argentina", "legendary", 85, "balanced", ["youth_development_system", "possession_control", "compact_midblock"], ["develops_young_players", "academy_promotion_bias", "technical_coaching", "balanced_substitution"], "Young sides given a structure first, then the freedom to pass out of it.", ["Argentina", "Colombia", "Venezuela"], age=77, style="Youth Structure", formation="4-2-3-1"),
    _coach("Alejandro Sabella", "Argentina", "legendary", 86, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["defensive_organization", "manages_elite_stars", "strict_structure", "late_substitution"], "A deep block, Messi free, and the rest of the team asked to run the other way.", ["Argentina", "Estudiantes"], style="Deep and Direct", formation="4-4-1-1"),
    _coach("Daniel Passarella", "Argentina", "popular", 83, "defensive", ["compact_midblock", "set_piece_focus", "direct_long_ball"], ["defensive_organization", "strict_structure", "improves_player_discipline", "boosts_physicality_focus"], "A hard back line, set pieces, and no space between the lines.", ["Argentina", "River Plate"], age=73, style="Hard Back Line", formation="4-4-2"),
    _coach("Carlos Queiroz", "Portugal", "legendary", 86, "pragmatic", ["compact_midblock", "counter_attack", "double_pivot_control"], ["defensive_organization", "tactical_flexibility", "strict_structure", "develops_young_players"], "Two screening midfielders, a narrow block, and the attack saved for the wide transition.", ["Portugal", "Iran", "Real Madrid"], age=73, style="Double Screen", formation="4-2-3-1"),
    _coach("Fernando Santos", "Portugal", "legendary", 86, "defensive", ["low_block_counter", "compact_midblock", "set_piece_focus"], ["defensive_organization", "strict_structure", "manages_elite_stars", "late_substitution"], "A low block of eight and one pass that released the forward.", ["Portugal", "Greece"], age=72, style="Low Block", formation="4-4-2"),
    _coach("Mircea Lucescu", "Romania", "legendary", 86, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["tactical_flexibility", "defensive_organization", "strict_structure", "develops_young_players"], "A disciplined block that became a 4-3-3 the moment the ball was won.", ["Shakhtar Donetsk", "Dynamo Kyiv"], age=81, style="Block to Break", formation="4-2-3-1"),
    _coach("Vahid Halilhodžić", "Bosnia and Herzegovina", "popular", 82, "defensive", ["low_block_counter", "compact_midblock", "direct_long_ball"], ["defensive_organization", "strict_structure", "boosts_physicality_focus", "improves_player_discipline"], "Deep defending, long passes into the channels, and no fancy football until the lead was safe.", ["Ivory Coast", "Morocco", "Japan"], age=74, style="Deep and Direct", formation="4-4-2"),
    _coach("Ralf Rangnick", "Germany", "elite_active", 84, "pressing", ["gegenpress", "high_press_attack", "double_pivot_control"], ["strict_structure", "quick_substitution", "develops_young_players", "tactical_flexibility"], "Press in numbers, counter in five seconds, and the goalkeeper as the first passer.", ["RB Leipzig", "Austria"], age=68, style="Gegenpress", formation="4-2-2-2"),
    _coach("Christian Streich", "Germany", "popular", 84, "pressing", ["gegenpress", "youth_development_system", "wing_play"], ["develops_young_players", "academy_promotion_bias", "quick_substitution", "improves_player_discipline"], "Freiburg's press, academy players in the first team, and a back line that stepped up together.", ["Freiburg"], age=61, style="Academy Press", formation="4-2-3-1"),
    _coach("Adi Hütter", "Austria", "popular", 83, "pressing", ["high_press_attack", "wing_play", "possession_control"], ["tactical_flexibility", "quick_substitution", "technical_coaching", "balanced_substitution"], "A high line, aggressive full-backs, and the ball played into the striker early.", ["Monaco", "Eintracht Frankfurt"], age=56, style="High Line", formation="3-4-2-1"),
    _coach("Jürgen Klinsmann", "Germany", "popular", 80, "attacking", ["high_press_attack", "wing_play", "youth_development_system"], ["develops_young_players", "expressive_freedom", "quick_substitution", "boosts_physicality_focus"], "Young legs, a high press, and wingers told to take the full-back on.", ["Germany", "United States"], age=62, style="Young Press", formation="4-2-3-1"),
    _coach("Christoph Daum", "Germany", "popular", 82, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["defensive_organization", "strict_structure", "tactical_flexibility", "improves_player_discipline"], "A compact midfield and breaks that used the wide players first.", ["Bayer Leverkusen", "Fenerbahçe"], style="Compact Break", formation="4-4-2"),
    _coach("Ruud Gullit", "Netherlands", "popular", 78, "attacking", ["wing_play", "elite_star_freedom", "possession_control"], ["manages_elite_stars", "expressive_freedom", "technical_coaching", "balanced_substitution"], "Attacking full-backs and forwards given the freedom to swap.", ["Chelsea", "Netherlands"], age=64, style="Free Forwards", formation="3-5-2"),
    _coach("Marco van Basten", "Netherlands", "popular", 77, "technical", ["possession_control", "technical_build_up", "wing_play"], ["technical_coaching", "expressive_freedom", "tactical_flexibility", "balanced_substitution"], "Technical players on the ball and a 4-3-3 that kept its shape.", ["Netherlands"], age=61, style="Technical 4-3-3", formation="4-3-3"),
    _coach("Steven Gerrard", "England", "popular", 76, "balanced", ["compact_midblock", "wing_play", "counter_attack"], ["balanced_substitution", "defensive_organization", "boosts_physicality_focus", "tactical_flexibility"], "A midfield that screened first and full-backs who joined the attack second.", ["Al-Ettifaq", "Rangers"], age=46, style="Screen Then Join", formation="4-3-3"),
    _coach("Michael Carrick", "England", "popular", 76, "possession", ["possession_control", "double_pivot_control", "technical_build_up"], ["technical_coaching", "develops_young_players", "balanced_substitution", "tactical_flexibility"], "Pass out from the back and keep a pivot so the full-back can go.", ["Middlesbrough"], age=45, style="Pivot Build", formation="4-2-3-1"),
    _coach("Thierry Henry", "France", "popular", 78, "attacking", ["wing_play", "high_press_attack", "elite_star_freedom"], ["technical_coaching", "expressive_freedom", "develops_young_players", "quick_substitution"], "Forwards who start the press and wide players who cut inside.", ["France U21"], age=49, style="Forward Press", formation="4-3-3"),
    _coach("Patrick Vieira", "France", "popular", 78, "balanced", ["double_pivot_control", "possession_control", "wing_play"], ["develops_young_players", "defensive_organization", "technical_coaching", "balanced_substitution"], "A strong double pivot and full-backs used as the width.", ["Strasbourg", "Crystal Palace"], age=50, style="Double Pivot", formation="4-3-3"),
    _coach("Frank Lampard", "England", "popular", 76, "attacking", ["wing_play", "youth_development_system", "possession_control"], ["develops_young_players", "academy_promotion_bias", "expressive_freedom", "balanced_substitution"], "Academy players in the side and midfielders encouraged to arrive in the box.", ["Chelsea", "Coventry City"], age=48, style="Box Arrivals", formation="4-3-3"),
    _coach("Wayne Rooney", "England", "popular", 75, "attacking", ["wing_play", "direct_long_ball", "high_press_attack"], ["boosts_physicality_focus", "quick_substitution", "expressive_freedom", "develops_young_players"], "Direct attacks, a high striker, and wide players asked to cross early.", ["Plymouth", "Birmingham City"], age=41, style="Direct Attack", formation="4-2-3-1"),
    _coach("Ole Gunnar Solskjær", "Norway", "popular", 78, "pragmatic", ["counter_attack", "compact_midblock", "wing_play"], ["manages_elite_stars", "defensive_organization", "balanced_substitution", "quick_substitution"], "Sit in, break quickly, and let the front three attack the space.", ["Manchester United", "Molde"], age=53, style="Quick Break", formation="4-2-3-1"),
    _coach("Ruud van Nistelrooy", "Netherlands", "popular", 77, "attacking", ["wing_play", "set_piece_focus", "direct_long_ball"], ["technical_coaching", "quick_substitution", "expressive_freedom", "balanced_substitution"], "Service into the box, a penalty-spot striker, and full-backs who cross.", ["Leicester City"], age=50, style="Service Into the Box", formation="4-2-3-1"),
    _coach("Andrea Pirlo", "Italy", "popular", 78, "possession", ["possession_control", "technical_build_up", "double_pivot_control"], ["technical_coaching", "expressive_freedom", "develops_young_players", "tactical_flexibility"], "A deep passer, a spare centre-back, and the attack built through midfield.", ["Sampdoria"], age=47, style="Deep Passer", formation="4-3-3"),
    _coach("Fabio Cannavaro", "Italy", "popular", 77, "defensive", ["compact_midblock", "low_block_counter", "set_piece_focus"], ["defensive_organization", "strict_structure", "improves_player_discipline", "balanced_substitution"], "A tight back line and breaks that started from a won header.", ["Croatia"], age=53, style="Tight Back Line", formation="4-4-2"),
    _coach("Sean Dyche", "England", "popular", 80, "physical", ["direct_long_ball", "set_piece_focus", "compact_midblock"], ["boosts_physicality_focus", "defensive_organization", "strict_structure", "improves_player_discipline"], "Second balls, a back four that does not split, and set pieces as the chance.", ["Everton", "Burnley"], age=55, style="Second Ball", formation="4-4-2"),
    _coach("Roy Hodgson", "England", "popular", 82, "defensive", ["low_block_counter", "compact_midblock", "direct_long_ball"], ["defensive_organization", "strict_structure", "late_substitution", "improves_player_discipline"], "Two banks of four and a direct pass into the channels.", ["Crystal Palace", "England"], age=79, style="Two Banks", formation="4-4-2"),
    _coach("Steve Clarke", "Scotland", "popular", 81, "pragmatic", ["compact_midblock", "counter_attack", "set_piece_focus"], ["defensive_organization", "strict_structure", "tactical_flexibility", "balanced_substitution"], "A back three, wing-backs who stay disciplined, and breaks through the wide channels.", ["Scotland"], age=63, style="Back Three", formation="3-4-2-1"),
    _coach("Stephen Keshi", "Nigeria", "legendary", 84, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["defensive_organization", "develops_young_players", "improves_player_discipline", "tactical_flexibility"], "A Nigerian block that could defend deep and still release two wingers.", ["Nigeria", "Mali", "Togo"], style="Big Boss Block", formation="4-2-3-1"),
    _coach("Clemens Westerhof", "Netherlands", "legendary", 82, "physical", ["direct_long_ball", "wing_play", "high_press_attack"], ["boosts_physicality_focus", "strict_structure", "develops_young_players", "quick_substitution"], "Power, width, and a Super Eagles side built to run for 90 minutes.", ["Nigeria"], age=86, style="Power and Width", formation="4-4-2"),
    _coach("Christian Chukwu", "Nigeria", "legendary", 80, "balanced", ["compact_midblock", "wing_play", "set_piece_focus"], ["defensive_organization", "improves_player_discipline", "develops_young_players", "balanced_substitution"], "Chairman Chukwu: an organised back line and wingers who attacked the full-back.", ["Nigeria", "Enugu Rangers"], style="Organised Width", formation="4-4-2"),
    _coach("Samson Siasia", "Nigeria", "popular", 79, "attacking", ["wing_play", "youth_development_system", "high_press_attack"], ["develops_young_players", "academy_promotion_bias", "expressive_freedom", "technical_coaching"], "Young Nigerian sides given a 4-3-3 and told to attack both flanks.", ["Nigeria", "Nigeria U23"], age=59, style="Youth 4-3-3", formation="4-3-3"),
    _coach("Sunday Oliseh", "Nigeria", "popular", 76, "balanced", ["double_pivot_control", "possession_control", "counter_attack"], ["technical_coaching", "defensive_organization", "tactical_flexibility", "balanced_substitution"], "A holding midfielder, short passes out, and the break saved for the wide players.", ["Nigeria"], age=52, style="Hold and Break", formation="4-3-3"),
    _coach("Austin Eguavoen", "Nigeria", "popular", 78, "pragmatic", ["compact_midblock", "counter_attack", "set_piece_focus"], ["defensive_organization", "strict_structure", "balanced_substitution", "improves_player_discipline"], "A compact Nigerian shape and set pieces used as the first chance.", ["Nigeria"], age=60, style="Compact Nigeria", formation="4-4-2"),
    _coach("Shuaibu Amodu", "Nigeria", "popular", 77, "pragmatic", ["compact_midblock", "wing_play", "counter_attack"], ["defensive_organization", "develops_young_players", "balanced_substitution", "improves_player_discipline"], "Shayee: a disciplined block and wingers released early.", ["Nigeria"], style="Disciplined Block", formation="4-4-2"),
    _coach("Gernot Rohr", "Germany", "popular", 80, "defensive", ["low_block_counter", "compact_midblock", "double_pivot_control"], ["defensive_organization", "strict_structure", "tactical_flexibility", "late_substitution"], "A low block, two holders, and the counter aimed at the channels.", ["Nigeria", "Burkina Faso"], age=73, style="Low Block", formation="4-2-3-1"),
    _coach("José Peseiro", "Portugal", "popular", 78, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["defensive_organization", "manages_elite_stars", "balanced_substitution", "tactical_flexibility"], "A compact 4-2-3-1 and the attack loaded onto the two wide forwards.", ["Nigeria", "Venezuela"], age=66, style="Wide Forwards", formation="4-2-3-1"),
    _coach("Finidi George", "Nigeria", "popular", 76, "attacking", ["wing_play", "counter_attack", "direct_long_ball"], ["expressive_freedom", "technical_coaching", "quick_substitution", "balanced_substitution"], "Width first: both wingers high and the full-backs asked to cross.", ["Nigeria"], age=55, style="Both Wingers High", formation="4-3-3"),
    _coach("Éric Chelle", "Mali", "popular", 79, "pragmatic", ["compact_midblock", "counter_attack", "double_pivot_control"], ["defensive_organization", "strict_structure", "tactical_flexibility", "balanced_substitution"], "A screened back four and breaks that used the striker as the target.", ["Nigeria", "Mali"], age=49, style="Screened Back Four", formation="4-2-3-1"),
    _coach("Émerse Faé", "Ivory Coast", "popular", 80, "balanced", ["compact_midblock", "counter_attack", "wing_play"], ["tactical_flexibility", "defensive_organization", "balanced_substitution", "develops_young_players"], "A young Ivory Coast side kept compact, then opened through the wide players.", ["Ivory Coast"], age=42, style="Compact Then Wide", formation="4-3-3"),
    _coach("Kwesi Appiah", "Ghana", "popular", 78, "pragmatic", ["compact_midblock", "counter_attack", "set_piece_focus"], ["defensive_organization", "develops_young_players", "balanced_substitution", "strict_structure"], "Ghana organised in two lines, with the counter and the set piece as the chance.", ["Ghana", "Sudan"], age=66, style="Two Lines", formation="4-4-2"),
    _coach("Hossam Hassan", "Egypt", "popular", 80, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["defensive_organization", "strict_structure", "manages_elite_stars", "balanced_substitution"], "A compact Egyptian block and wingers used on the break.", ["Egypt"], age=60, style="Egyptian Block", formation="4-2-3-1"),
    _coach("Aliou Cissé", "Senegal", "elite_active", 83, "defensive", ["low_block_counter", "compact_midblock", "set_piece_focus"], ["defensive_organization", "strict_structure", "improves_player_discipline", "balanced_substitution"], "Senegal's block: five in the last line when needed, and the counter through the wings.", ["Senegal"], age=50, style="Senegal Block", formation="4-4-2"),
    _coach("Djamel Belmadi", "Algeria", "elite_active", 83, "balanced", ["possession_control", "compact_midblock", "wing_play"], ["technical_coaching", "tactical_flexibility", "defensive_organization", "balanced_substitution"], "Algeria kept the ball in midfield and still had two runners wide.", ["Algeria"], age=50, style="Midfield Control", formation="4-3-3"),
    _coach("Hugo Broos", "Belgium", "popular", 82, "pragmatic", ["compact_midblock", "counter_attack", "youth_development_system"], ["develops_young_players", "defensive_organization", "strict_structure", "balanced_substitution"], "A clear back four, young players given roles, and the attack kept simple.", ["South Africa", "Cameroon"], age=74, style="Clear Roles", formation="4-2-3-1"),
    _coach("Nasreddine Nabi", "Tunisia", "popular", 80, "possession", ["possession_control", "wing_play", "technical_build_up"], ["technical_coaching", "tactical_flexibility", "balanced_substitution", "develops_young_players"], "Build through midfield and attack with the full-backs once the pivot is set.", ["Mamelodi Sundowns", "Zamalek"], age=59, style="Build Through Midfield", formation="4-3-3"),
    _coach("Benni McCarthy", "South Africa", "popular", 78, "attacking", ["wing_play", "set_piece_focus", "direct_long_ball"], ["technical_coaching", "expressive_freedom", "quick_substitution", "balanced_substitution"], "Strikers on the last line and wide players asked to deliver early.", ["Kenya", "Cape Town City"], age=48, style="Last-Line Strikers", formation="4-2-3-1"),
    _coach("Sébastien Desabre", "France", "popular", 79, "pragmatic", ["compact_midblock", "counter_attack", "double_pivot_control"], ["defensive_organization", "tactical_flexibility", "strict_structure", "balanced_substitution"], "A compact African block with two holders and a quick release to the wings.", ["DR Congo"], age=50, style="Two Holders", formation="4-2-3-1"),
    _coach("Florent Ibenge", "DR Congo", "popular", 77, "pragmatic", ["compact_midblock", "counter_attack", "wing_play"], ["defensive_organization", "balanced_substitution", "improves_player_discipline", "tactical_flexibility"], "Stay compact, win the second ball, and attack the space behind the full-back.", ["DR Congo"], style="Second Ball Wide", formation="4-4-2"),
    _coach("Amir Abdou", "France", "popular", 77, "pragmatic", ["compact_midblock", "counter_attack", "set_piece_focus"], ["defensive_organization", "strict_structure", "develops_young_players", "balanced_substitution"], "A narrow block and set pieces prepared before the match.", ["Comoros", "Mauritania"], age=54, style="Narrow Block", formation="4-4-2"),
    _coach("Tom Saintfiet", "Belgium", "popular", 76, "defensive", ["low_block_counter", "compact_midblock", "direct_long_ball"], ["defensive_organization", "strict_structure", "improves_player_discipline", "late_substitution"], "Deep defending and a direct ball into the front two.", ["Gambia", "Mali"], age=53, style="Deep and Direct", formation="4-4-2"),
    _coach("Sonia Bompastor", "France", "elite_active", 86, "possession", ["possession_control", "wing_play", "high_press_attack"], ["technical_coaching", "tactical_flexibility", "quick_substitution", "develops_young_players"], "A high press and a 4-3-3 that attacked both sides with the full-backs.", ["Chelsea Women", "Lyon Women"], age=46, gender="female", style="High 4-3-3", formation="4-3-3"),
    _coach("Silvia Neid", "Germany", "legendary", 88, "attacking", ["wing_play", "high_press_attack", "possession_control"], ["develops_young_players", "technical_coaching", "strict_structure", "quick_substitution"], "Germany's wide attack, a high press, and young players given the full position.", ["Germany Women"], age=62, gender="female", style="Wide German Attack", formation="4-2-3-1"),
    _coach("Hope Powell", "England", "legendary", 84, "balanced", ["compact_midblock", "wing_play", "youth_development_system"], ["develops_young_players", "academy_promotion_bias", "defensive_organization", "technical_coaching"], "An England side built from the academy, with a compact shape and wide attackers.", ["England Women"], age=59, gender="female", style="Academy England", formation="4-4-2"),
    _coach("Corinne Diacre", "France", "popular", 80, "pragmatic", ["compact_midblock", "counter_attack", "direct_long_ball"], ["strict_structure", "defensive_organization", "improves_player_discipline", "balanced_substitution"], "A direct France side, clear defensive roles, and the ball played forward early.", ["France Women"], age=52, gender="female", style="Direct Roles", formation="4-4-2"),
    _coach("Pia Sundhage", "Sweden", "legendary", 86, "attacking", ["wing_play", "possession_control", "high_press_attack"], ["technical_coaching", "expressive_freedom", "tactical_flexibility", "develops_young_players"], "Brave wide play and a team asked to attack even after it scored.", ["United States Women", "Brazil Women", "Sweden"], age=66, gender="female", style="Brave Width", formation="4-3-3"),
    _coach("Jill Ellis", "England", "legendary", 85, "pragmatic", ["compact_midblock", "wing_play", "set_piece_focus"], ["tactical_flexibility", "manages_elite_stars", "defensive_organization", "balanced_substitution"], "Change the shape for the opponent, keep the block tight, and use the set piece.", ["United States Women"], age=60, gender="female", style="Shape for the Opponent", formation="4-3-3"),
]


_NATIONS = {
    "sir alex ferguson": "Scotland",
    "helenio herrera": "Argentina",
    "aime jacquet": "France",
    "nereo rocco": "Italy",
    "bora milutinovic": "Serbia",
    "luiz felipe scolari": "Brazil",
    "mikel arteta": "Spain",
    "xabi alonso": "Spain",
    "julian nagelsmann": "Germany",
    "walid regragui": "Morocco",
    "pitso mosimane": "South Africa",
    "sarina wiegman": "Netherlands",
    "emma hayes": "England",
    "jose mourinho": "Portugal",
    "mario zagallo": "Brazil",
    "luciano spalletti": "Italy",
}


_FORMATION_BY_TACTIC = {
    "gegenpress": "4-2-3-1",
    "high_press_attack": "4-3-3",
    "possession_control": "4-3-3",
    "technical_build_up": "4-3-3",
    "tiki_taka": "4-3-3",
    "inverted_wingers": "4-3-3",
    "attacking_rotation": "4-4-2",
    "wing_play": "4-4-2",
    "overlapping_fullbacks": "3-4-3",
    "counter_attack": "4-4-2",
    "compact_midblock": "4-4-2",
    "direct_long_ball": "4-4-2",
    "double_pivot_control": "4-2-3-1",
    "low_block_counter": "5-4-1",
    "set_piece_focus": "4-4-2",
    "youth_development_system": "4-3-3",
    "elite_star_freedom": "4-2-3-1",
    "physical_duel_game": "4-4-2",
    "late_surge_press": "4-4-2",
}

_STYLE_BY_MENTALITY = {
    "balanced": "Balanced Control",
    "attacking": "Attacking Width",
    "defensive": "Compact Block",
    "technical": "Technical Possession",
    "pragmatic": "Pragmatic Structure",
    "pressing": "High Press",
    "possession": "Possession Control",
    "physical": "Physical Duels",
}

_TEMPERAMENT_BY_MENTALITY = {
    "balanced": "pragmatic",
    "attacking": "demanding",
    "defensive": "pragmatic",
    "technical": "calm",
    "pragmatic": "pragmatic",
    "pressing": "demanding",
    "possession": "calm",
    "physical": "demanding",
}


def _rating_for(name: str, rarity: str, explicit: int | None) -> int:
    if explicit:
        return int(explicit)
    pinned = {
        "sir alex ferguson": 96,
        "helenio herrera": 93,
        "nereo rocco": 91,
        "bora milutinovic": 88,
        "luiz felipe scolari": 91,
        "mario zagallo": 94,
        "luciano spalletti": 86,
        "hector cuper": 84,
        "ricardo gareca": 84,
        "berti vogts": 86,
        "roger schmidt": 82,
        "peter bosz": 80,
        "sarina wiegman": 90,
        "emma hayes": 88,
        "aime jacquet": 91,
        "mikel arteta": 88,
        "xabi alonso": 87,
        "julian nagelsmann": 89,
        "walid regragui": 84,
        "pitso mosimane": 84,
        "aliou cisse": 83,
        "lionel scaloni": 91,
        "simone inzaghi": 88,
        "gian piero gasperini": 87,
    }
    folded = canon_fold(name)
    if folded in pinned:
        return pinned[folded]
    bands = {"legendary": (90, 95), "elite_active": (84, 89), "popular": (74, 82)}
    low, high = bands.get(rarity, (74, 82))
    return low + (zlib.crc32(folded.encode()) % (high - low + 1))


def _fan_wage(rating: int) -> int:
    return int(round(150 + (rating - 65) * (1850 / 30)))


def _formations(record: dict[str, Any]) -> tuple[str, list[str]]:
    explicit = record.get("preferred_formation")
    tactics = [str(item) for item in record.get("tactics") or []]
    shapes = []
    for tactic in tactics:
        if "-" in tactic and any(ch.isdigit() for ch in tactic):
            shapes.append(tactic)
        elif tactic in _FORMATION_BY_TACTIC:
            shapes.append(_FORMATION_BY_TACTIC[tactic])
    ordered: list[str] = []
    for shape in shapes:
        if shape not in ordered:
            ordered.append(shape)
    primary = str(explicit or (ordered[0] if ordered else "4-3-3"))
    if primary not in ordered:
        ordered.insert(0, primary)
    return primary, ordered[:4]


def _bio(record: dict[str, Any]) -> str:
    philosophy = str(record.get("philosophy") or "").strip()
    clubs = [str(club) for club in record.get("club_associations") or [] if club]
    if clubs and not any(club in philosophy for club in clubs[:2]):
        return f"{philosophy} Clubs: {', '.join(clubs[:3])}."
    return philosophy


def _staff_rarity(seed_rarity: str) -> str:
    if seed_rarity == "legendary":
        return "legendary"
    if seed_rarity == "elite_active":
        return "elite"
    return "established"


def staff_item_from_seed(record: dict[str, Any]) -> dict[str, Any]:
    """One hireable first-team manager, paid in Fan Coin."""
    name = str(record["name"])
    rating = _rating_for(name, str(record.get("rarity") or "popular"), record.get("rating"))
    annual = _fan_wage(rating)
    signing = int(round(80 + (rating - 65) * (720 / 30)))
    formation, formations = _formations(record)
    mentality = str(record.get("mentality") or "balanced")
    folded = canon_fold(name)
    gender = str(record.get("gender") or ("female" if folded in WOMEN else "male"))
    item = {
        "id": "mgr_real_" + folded.replace(" ", "_"),
        "staff_id": "mgr_real_" + folded.replace(" ", "_"),
        "role": "first_team_manager",
        "role_label": "First Team Manager",
        "name": name,
        "nation": record.get("nation") or _NATIONS.get(folded),
        "real_club": (record.get("club_associations") or [None])[0],
        "source_job": "Head Coach",
        "rating": rating,
        "gsi": rating,
        "style": record.get("style") or _STYLE_BY_MENTALITY.get(mentality, "Balanced Control"),
        "temperament": _TEMPERAMENT_BY_MENTALITY.get(mentality, "pragmatic"),
        "ambition": min(20, max(10, round(rating / 5))),
        "loyalty": 14,
        "youth_development": 16 if "develops_young_players" in (record.get("traits") or []) else 12,
        "tactical_flexibility": min(20, max(8, round(rating / 5))),
        "negotiation": 14,
        "commercial_acumen": 12,
        "scouting_accuracy": 12,
        "medical_expertise": 8,
        "min_prestige": max(20, int(rating * 0.8)),
        "salary": annual,
        "salary_fancoin": annual,
        "salary_fan_coin": annual,
        "salary_gtex": round(annual / 10.0, 1),
        "signing_fee_gtex": signing,
        "contract_1yr_fancoin": annual,
        "contract_3yr_fancoin": annual * 3,
        "rarity": _staff_rarity(str(record.get("rarity") or "popular")),
        "gender": gender,
        "mentality": mentality,
        "preferred_formation": formation,
        "preferred_formations": formations,
        "tactics": list(record.get("tactics") or [])[:4],
        "traits": list(record.get("traits") or [])[:4],
        "philosophy_summary": record.get("philosophy"),
        "bio": _bio(record),
        "origin": "real_manager",
        "specialty": "First Team Manager",
    }
    if record.get("age"):
        item["age"] = int(record["age"])
    return item


def _paint(item: dict[str, Any], updates: dict[str, Any]) -> None:
    rating = int(updates.get("rating") or item.get("rating") or 75)
    annual = _fan_wage(rating)
    item["role"] = "first_team_manager"
    item["role_label"] = "First Team Manager"
    item["rating"] = rating
    item["gsi"] = rating
    item["rarity"] = updates.get("rarity") or item.get("rarity") or _staff_rarity("popular")
    item["salary"] = annual
    item["salary_fancoin"] = annual
    item["salary_fan_coin"] = annual
    item["salary_gtex"] = round(annual / 10.0, 1)
    item["signing_fee_gtex"] = int(round(80 + (rating - 65) * (720 / 30)))
    item["refresh_market_rating"] = True
    item["origin"] = item.get("origin") or "real_manager"
    for field in (
        "style",
        "temperament",
        "mentality",
        "preferred_formation",
        "preferred_formations",
        "tactics",
        "traits",
        "philosophy_summary",
        "bio",
    ):
        if updates.get(field) is not None:
            item[field] = updates[field]


def apply_real_first_team_managers(catalog: list[dict[str, Any]]) -> int:
    """Add missing real head coaches and correct buried or mis-filed ones.

    Returns the number of new first-team manager rows appended.
    """
    from app.manager_market.seed_catalog import build_seed_catalog

    by_fold: dict[str, list[dict[str, Any]]] = {}
    for item in catalog:
        by_fold.setdefault(canon_fold(item.get("name")), []).append(item)

    for folded, updates in RATING_FLOORS.items():
        rows = [row for row in by_fold.get(folded, []) if row.get("role") == "first_team_manager"]
        if not rows:
            continue
        current = int(rows[0].get("rating") or 0)
        if current < int(updates["rating"]):
            _paint(rows[0], updates)

    created = 0
    for record in build_seed_catalog():
        folded = canon_fold(record.get("name"))
        rows = by_fold.get(folded, [])
        if any(row.get("role") == "first_team_manager" for row in rows):
            continue
        if rows:
            target = max(
                rows,
                key=lambda row: (
                    str(row.get("source_job") or "") == "Head Coach",
                    int(row.get("rating") or 0),
                ),
            )
            built = staff_item_from_seed(record)
            _paint(target, built)
            continue
        built = staff_item_from_seed(record)
        catalog.append(built)
        by_fold.setdefault(folded, []).append(built)
        created += 1
    return created

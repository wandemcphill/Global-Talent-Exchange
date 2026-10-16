from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "first_controlled_batch_v1.json"
REVIEW_PATH = ROOT / "first_controlled_batch_v1.review.json"


def player(
    *,
    tier: str,
    key: str,
    name: str,
    nationality: str,
    nationality_code: str,
    birth_year: int,
    position: str,
    competition_level: str,
    appearances: int,
    minutes: int,
    goals: int = 0,
    assists: int = 0,
    clean_sheets: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_name": "curated-feed",
        "source_player_key": key,
        "canonical_name": name,
        "nationality": nationality,
        "nationality_code": nationality_code,
        "birth_year": birth_year,
        "primary_position": position,
        "competition_level": competition_level,
        "appearances": appearances,
        "minutes_played": minutes,
        "goals": goals,
        "assists": assists,
        "real_player_tier": tier,
    }
    if clean_sheets is not None:
        payload["clean_sheets"] = clean_sheets
    return payload


GLOBAL_STARS = [
    player(tier="global_star", key="mbappe-001", name="Kylian Mbappe", nationality="France", nationality_code="FR", birth_year=1998, position="Striker", competition_level="elite", appearances=34, minutes=2820, goals=28, assists=7),
    player(tier="global_star", key="haaland-001", name="Erling Haaland", nationality="Norway", nationality_code="NO", birth_year=2000, position="Striker", competition_level="elite", appearances=31, minutes=2550, goals=27, assists=5),
    player(tier="global_star", key="bellingham-001", name="Jude Bellingham", nationality="England", nationality_code="GB", birth_year=2003, position="Central Midfielder", competition_level="elite", appearances=33, minutes=2790, goals=14, assists=9),
    player(tier="global_star", key="vinicius-junior-001", name="Vinicius Junior", nationality="Brazil", nationality_code="BR", birth_year=2000, position="Winger", competition_level="elite", appearances=30, minutes=2440, goals=19, assists=11),
    player(tier="global_star", key="salah-001", name="Mohamed Salah", nationality="Egypt", nationality_code="EG", birth_year=1992, position="Winger", competition_level="elite", appearances=33, minutes=2810, goals=22, assists=12),
    player(tier="global_star", key="kane-001", name="Harry Kane", nationality="England", nationality_code="GB", birth_year=1993, position="Striker", competition_level="elite", appearances=32, minutes=2760, goals=29, assists=8),
    player(tier="global_star", key="rodri-001", name="Rodri", nationality="Spain", nationality_code="ES", birth_year=1996, position="Defensive Midfielder", competition_level="elite", appearances=34, minutes=2960, goals=8, assists=7),
    player(tier="global_star", key="de-bruyne-001", name="Kevin De Bruyne", nationality="Belgium", nationality_code="BE", birth_year=1991, position="Attacking Midfielder", competition_level="elite", appearances=27, minutes=1980, goals=8, assists=14),
    player(tier="global_star", key="lautaro-martinez-001", name="Lautaro Martinez", nationality="Argentina", nationality_code="AR", birth_year=1997, position="Striker", competition_level="elite", appearances=33, minutes=2750, goals=24, assists=6),
    player(tier="global_star", key="osimhen-001", name="Victor Osimhen", nationality="Nigeria", nationality_code="NG", birth_year=1998, position="Striker", competition_level="elite", appearances=31, minutes=2410, goals=19, assists=4),
    player(tier="global_star", key="kvaratskhelia-001", name="Khvicha Kvaratskhelia", nationality="Georgia", nationality_code="GE", birth_year=2001, position="Winger", competition_level="elite", appearances=32, minutes=2685, goals=13, assists=10),
    player(tier="global_star", key="wirtz-001", name="Florian Wirtz", nationality="Germany", nationality_code="DE", birth_year=2003, position="Attacking Midfielder", competition_level="elite", appearances=31, minutes=2490, goals=11, assists=12),
    player(tier="global_star", key="musiala-001", name="Jamal Musiala", nationality="Germany", nationality_code="DE", birth_year=2003, position="Attacking Midfielder", competition_level="elite", appearances=30, minutes=2335, goals=12, assists=8),
    player(tier="global_star", key="saka-001", name="Bukayo Saka", nationality="England", nationality_code="GB", birth_year=2001, position="Winger", competition_level="elite", appearances=33, minutes=2860, goals=16, assists=11),
    player(tier="global_star", key="odegaard-001", name="Martin Odegaard", nationality="Norway", nationality_code="NO", birth_year=1998, position="Attacking Midfielder", competition_level="elite", appearances=34, minutes=2895, goals=10, assists=9),
    player(tier="global_star", key="valverde-001", name="Federico Valverde", nationality="Uruguay", nationality_code="UY", birth_year=1998, position="Central Midfielder", competition_level="elite", appearances=35, minutes=3010, goals=7, assists=8),
    player(tier="global_star", key="alisson-001", name="Alisson Becker", nationality="Brazil", nationality_code="BR", birth_year=1992, position="Goalkeeper", competition_level="elite", appearances=30, minutes=2700, assists=1, clean_sheets=13),
    player(tier="global_star", key="van-dijk-001", name="Virgil van Dijk", nationality="Netherlands", nationality_code="NL", birth_year=1991, position="Centre-Back", competition_level="elite", appearances=33, minutes=2970, goals=4, assists=2, clean_sheets=14),
]

NIGERIAN_CORE = [
    player(tier="nigerian_core", key="iwobi-001", name="Alex Iwobi", nationality="Nigeria", nationality_code="NG", birth_year=1996, position="Winger", competition_level="top_flight", appearances=29, minutes=2280, goals=6, assists=7),
    player(tier="nigerian_core", key="bassey-001", name="Calvin Bassey", nationality="Nigeria", nationality_code="NG", birth_year=1999, position="Centre-Back", competition_level="top_flight", appearances=30, minutes=2550, goals=1, assists=2, clean_sheets=11),
    player(tier="nigerian_core", key="lookman-001", name="Ademola Lookman", nationality="Nigeria", nationality_code="NG", birth_year=1997, position="Winger", competition_level="elite", appearances=31, minutes=2480, goals=14, assists=8),
    player(tier="nigerian_core", key="chukwueze-001", name="Samuel Chukwueze", nationality="Nigeria", nationality_code="NG", birth_year=1999, position="Winger", competition_level="top_flight", appearances=27, minutes=1780, goals=5, assists=4),
    player(tier="nigerian_core", key="ndidi-001", name="Wilfred Ndidi", nationality="Nigeria", nationality_code="NG", birth_year=1996, position="Defensive Midfielder", competition_level="top_flight", appearances=29, minutes=2475, goals=2, assists=3),
    player(tier="nigerian_core", key="aribo-001", name="Joe Aribo", nationality="Nigeria", nationality_code="NG", birth_year=1996, position="Central Midfielder", competition_level="top_flight", appearances=26, minutes=1740, goals=3, assists=3),
    player(tier="nigerian_core", key="moses-simon-001", name="Moses Simon", nationality="Nigeria", nationality_code="NG", birth_year=1995, position="Winger", competition_level="top_flight", appearances=30, minutes=2320, goals=7, assists=8),
    player(tier="nigerian_core", key="moffi-001", name="Terem Moffi", nationality="Nigeria", nationality_code="NG", birth_year=1999, position="Striker", competition_level="top_flight", appearances=28, minutes=2055, goals=11, assists=3),
    player(tier="nigerian_core", key="awoniyi-001", name="Taiwo Awoniyi", nationality="Nigeria", nationality_code="NG", birth_year=1997, position="Striker", competition_level="top_flight", appearances=24, minutes=1680, goals=9, assists=2),
    player(tier="nigerian_core", key="iheanacho-001", name="Kelechi Iheanacho", nationality="Nigeria", nationality_code="NG", birth_year=1996, position="Striker", competition_level="top_flight", appearances=23, minutes=1380, goals=6, assists=4),
    player(tier="nigerian_core", key="osayi-samuel-001", name="Bright Osayi-Samuel", nationality="Nigeria", nationality_code="NG", birth_year=1997, position="Full-Back", competition_level="top_flight", appearances=30, minutes=2555, goals=1, assists=5, clean_sheets=9),
    player(tier="nigerian_core", key="semi-ajayi-001", name="Semi Ajayi", nationality="Nigeria", nationality_code="NG", birth_year=1993, position="Centre-Back", competition_level="top_flight", appearances=29, minutes=2520, goals=2, assists=1, clean_sheets=10),
    player(tier="nigerian_core", key="ola-aina-001", name="Ola Aina", nationality="Nigeria", nationality_code="NG", birth_year=1996, position="Full-Back", competition_level="top_flight", appearances=31, minutes=2645, goals=1, assists=4, clean_sheets=12),
    player(tier="nigerian_core", key="zaidu-sanusi-001", name="Zaidu Sanusi", nationality="Nigeria", nationality_code="NG", birth_year=1997, position="Full-Back", competition_level="top_flight", appearances=27, minutes=2210, goals=1, assists=2, clean_sheets=11),
    player(tier="nigerian_core", key="okoye-001", name="Maduka Okoye", nationality="Nigeria", nationality_code="NG", birth_year=1999, position="Goalkeeper", competition_level="top_flight", appearances=28, minutes=2520, clean_sheets=10),
    player(tier="nigerian_core", key="nwabali-001", name="Stanley Nwabali", nationality="Nigeria", nationality_code="NG", birth_year=1996, position="Goalkeeper", competition_level="top_flight", appearances=29, minutes=2610, clean_sheets=11),
    player(tier="nigerian_core", key="nathan-tella-001", name="Nathan Tella", nationality="Nigeria", nationality_code="NG", birth_year=1999, position="Winger", competition_level="top_flight", appearances=28, minutes=1845, goals=6, assists=4),
    player(tier="nigerian_core", key="onyedika-001", name="Raphael Onyedika", nationality="Nigeria", nationality_code="NG", birth_year=2001, position="Defensive Midfielder", competition_level="top_flight", appearances=31, minutes=2590, goals=2, assists=2),
    player(tier="nigerian_core", key="dele-bashiru-001", name="Fisayo Dele-Bashiru", nationality="Nigeria", nationality_code="NG", birth_year=2001, position="Attacking Midfielder", competition_level="top_flight", appearances=27, minutes=1930, goals=7, assists=3),
    player(tier="nigerian_core", key="onyeka-001", name="Frank Onyeka", nationality="Nigeria", nationality_code="NG", birth_year=1998, position="Defensive Midfielder", competition_level="top_flight", appearances=28, minutes=2140, goals=1, assists=2),
    player(tier="nigerian_core", key="torunarigha-001", name="Jordan Torunarigha", nationality="Nigeria", nationality_code="NG", birth_year=1997, position="Centre-Back", competition_level="top_flight", appearances=30, minutes=2630, goals=1, assists=1, clean_sheets=12),
    player(tier="nigerian_core", key="dessers-001", name="Cyriel Dessers", nationality="Nigeria", nationality_code="NG", birth_year=1994, position="Striker", competition_level="top_flight", appearances=31, minutes=2160, goals=14, assists=3),
    player(tier="nigerian_core", key="onuachu-001", name="Paul Onuachu", nationality="Nigeria", nationality_code="NG", birth_year=1994, position="Striker", competition_level="top_flight", appearances=26, minutes=1800, goals=10, assists=2),
    player(tier="nigerian_core", key="gift-orban-001", name="Gift Orban", nationality="Nigeria", nationality_code="NG", birth_year=2002, position="Striker", competition_level="top_flight", appearances=24, minutes=1575, goals=8, assists=2),
]

PROSPECTS = [
    player(tier="prospect", key="lamine-yamal-001", name="Lamine Yamal", nationality="Spain", nationality_code="ES", birth_year=2007, position="Winger", competition_level="elite", appearances=28, minutes=1810, goals=6, assists=8),
    player(tier="prospect", key="endrick-001", name="Endrick", nationality="Brazil", nationality_code="BR", birth_year=2006, position="Striker", competition_level="developmental", appearances=22, minutes=1180, goals=8, assists=2),
    player(tier="prospect", key="arda-guler-001", name="Arda Guler", nationality="Turkey", nationality_code="TR", birth_year=2005, position="Attacking Midfielder", competition_level="elite", appearances=19, minutes=980, goals=4, assists=3),
    player(tier="prospect", key="zaire-emery-001", name="Warren Zaire-Emery", nationality="France", nationality_code="FR", birth_year=2006, position="Central Midfielder", competition_level="elite", appearances=29, minutes=2220, goals=4, assists=5),
    player(tier="prospect", key="mainoo-001", name="Kobbie Mainoo", nationality="England", nationality_code="GB", birth_year=2005, position="Central Midfielder", competition_level="elite", appearances=27, minutes=2065, goals=3, assists=2),
    player(tier="prospect", key="garnacho-001", name="Alejandro Garnacho", nationality="Argentina", nationality_code="AR", birth_year=2004, position="Winger", competition_level="elite", appearances=31, minutes=2140, goals=7, assists=5),
    player(tier="prospect", key="joao-neves-001", name="Joao Neves", nationality="Portugal", nationality_code="PT", birth_year=2004, position="Central Midfielder", competition_level="top_flight", appearances=32, minutes=2525, goals=3, assists=4),
    player(tier="prospect", key="rico-lewis-001", name="Rico Lewis", nationality="England", nationality_code="GB", birth_year=2004, position="Full-Back", competition_level="elite", appearances=24, minutes=1515, goals=1, assists=4, clean_sheets=8),
    player(tier="prospect", key="cubarsi-001", name="Pau Cubarsi", nationality="Spain", nationality_code="ES", birth_year=2007, position="Centre-Back", competition_level="elite", appearances=24, minutes=2080, goals=1, assists=1, clean_sheets=9),
    player(tier="prospect", key="hato-001", name="Jorrel Hato", nationality="Netherlands", nationality_code="NL", birth_year=2006, position="Full-Back", competition_level="top_flight", appearances=30, minutes=2490, goals=1, assists=3, clean_sheets=10),
    player(tier="prospect", key="archie-gray-001", name="Archie Gray", nationality="England", nationality_code="GB", birth_year=2006, position="Central Midfielder", competition_level="top_flight", appearances=29, minutes=2310, goals=2, assists=3),
    player(tier="prospect", key="ethan-nwaneri-001", name="Ethan Nwaneri", nationality="England", nationality_code="GB", birth_year=2007, position="Attacking Midfielder", competition_level="developmental", appearances=15, minutes=640, goals=3, assists=2),
    player(tier="prospect", key="sesko-001", name="Benjamin Sesko", nationality="Slovenia", nationality_code="SI", birth_year=2003, position="Striker", competition_level="elite", appearances=29, minutes=1930, goals=12, assists=3),
    player(tier="prospect", key="desire-doue-001", name="Desire Doue", nationality="France", nationality_code="FR", birth_year=2005, position="Winger", competition_level="top_flight", appearances=27, minutes=1710, goals=5, assists=6),
    player(tier="prospect", key="moukoko-001", name="Youssoufa Moukoko", nationality="Germany", nationality_code="DE", birth_year=2004, position="Striker", competition_level="top_flight", appearances=21, minutes=980, goals=5, assists=2),
    player(tier="prospect", key="savinho-001", name="Savinho", nationality="Brazil", nationality_code="BR", birth_year=2004, position="Winger", competition_level="top_flight", appearances=31, minutes=2300, goals=8, assists=9),
    player(tier="prospect", key="antonio-nusa-001", name="Antonio Nusa", nationality="Norway", nationality_code="NO", birth_year=2005, position="Winger", competition_level="top_flight", appearances=24, minutes=1425, goals=4, assists=5),
    player(tier="prospect", key="ben-seghir-001", name="Eliesse Ben Seghir", nationality="Morocco", nationality_code="MA", birth_year=2005, position="Attacking Midfielder", competition_level="top_flight", appearances=23, minutes=1390, goals=4, assists=4),
    player(tier="prospect", key="bardghji-001", name="Roony Bardghji", nationality="Sweden", nationality_code="SE", birth_year=2005, position="Winger", competition_level="top_flight", appearances=20, minutes=1205, goals=6, assists=3),
    player(tier="prospect", key="vitor-roque-001", name="Vitor Roque", nationality="Brazil", nationality_code="BR", birth_year=2005, position="Striker", competition_level="top_flight", appearances=20, minutes=915, goals=5, assists=1),
    player(tier="prospect", key="mathys-tel-001", name="Mathys Tel", nationality="France", nationality_code="FR", birth_year=2005, position="Winger", competition_level="elite", appearances=24, minutes=1120, goals=6, assists=4),
    player(tier="prospect", key="el-khannouss-001", name="Bilal El Khannouss", nationality="Morocco", nationality_code="MA", birth_year=2004, position="Attacking Midfielder", competition_level="top_flight", appearances=30, minutes=2260, goals=4, assists=6),
    player(tier="prospect", key="kendry-paez-001", name="Kendry Paez", nationality="Ecuador", nationality_code="EC", birth_year=2007, position="Attacking Midfielder", competition_level="developmental", appearances=18, minutes=930, goals=3, assists=4),
    player(tier="prospect", key="estevao-001", name="Estevao Willian", nationality="Brazil", nationality_code="BR", birth_year=2007, position="Winger", competition_level="developmental", appearances=19, minutes=990, goals=5, assists=4),
    player(tier="prospect", key="valentin-carboni-001", name="Valentin Carboni", nationality="Argentina", nationality_code="AR", birth_year=2005, position="Attacking Midfielder", competition_level="top_flight", appearances=23, minutes=1415, goals=4, assists=5),
    player(tier="prospect", key="echeverri-001", name="Claudio Echeverri", nationality="Argentina", nationality_code="AR", birth_year=2006, position="Attacking Midfielder", competition_level="developmental", appearances=18, minutes=875, goals=4, assists=3),
    player(tier="prospect", key="gloukh-001", name="Oscar Gloukh", nationality="Israel", nationality_code="IL", birth_year=2004, position="Attacking Midfielder", competition_level="top_flight", appearances=29, minutes=2195, goals=8, assists=6),
    player(tier="prospect", key="bergvall-001", name="Lucas Bergvall", nationality="Sweden", nationality_code="SE", birth_year=2006, position="Central Midfielder", competition_level="top_flight", appearances=27, minutes=2040, goals=3, assists=5),
    player(tier="prospect", key="ouedraogo-001", name="Assan Ouedraogo", nationality="Germany", nationality_code="DE", birth_year=2006, position="Central Midfielder", competition_level="top_flight", appearances=20, minutes=1280, goals=2, assists=3),
    player(tier="prospect", key="tom-bischof-001", name="Tom Bischof", nationality="Germany", nationality_code="DE", birth_year=2005, position="Central Midfielder", competition_level="top_flight", appearances=22, minutes=1450, goals=2, assists=4),
    player(tier="prospect", key="khusanov-001", name="Abdukodir Khusanov", nationality="Uzbekistan", nationality_code="UZ", birth_year=2004, position="Centre-Back", competition_level="top_flight", appearances=26, minutes=2235, goals=1, assists=1, clean_sheets=9),
    player(tier="prospect", key="jhon-duran-001", name="Jhon Duran", nationality="Colombia", nationality_code="CO", birth_year=2003, position="Striker", competition_level="elite", appearances=23, minutes=1020, goals=8, assists=1),
    player(tier="prospect", key="udogie-001", name="Destiny Udogie", nationality="Italy", nationality_code="IT", birth_year=2002, position="Full-Back", competition_level="elite", appearances=28, minutes=2290, goals=2, assists=5, clean_sheets=8),
    player(tier="prospect", key="cherki-001", name="Rayan Cherki", nationality="France", nationality_code="FR", birth_year=2003, position="Attacking Midfielder", competition_level="top_flight", appearances=27, minutes=1795, goals=5, assists=8),
    player(tier="prospect", key="mikayil-faye-001", name="Mikayil Faye", nationality="Senegal", nationality_code="SN", birth_year=2004, position="Centre-Back", competition_level="developmental", appearances=18, minutes=1530, goals=1, assists=1, clean_sheets=7),
    player(tier="prospect", key="vuskovic-001", name="Luka Vuskovic", nationality="Croatia", nationality_code="HR", birth_year=2007, position="Centre-Back", competition_level="developmental", appearances=17, minutes=1490, goals=2, assists=1, clean_sheets=6),
    player(tier="prospect", key="geovany-quenda-001", name="Geovany Quenda", nationality="Portugal", nationality_code="PT", birth_year=2007, position="Winger", competition_level="developmental", appearances=16, minutes=835, goals=3, assists=3),
    player(tier="prospect", key="diego-moreira-001", name="Diego Moreira", nationality="Belgium", nationality_code="BE", birth_year=2004, position="Winger", competition_level="top_flight", appearances=22, minutes=1260, goals=2, assists=4),
    player(tier="prospect", key="buonanotte-001", name="Facundo Buonanotte", nationality="Argentina", nationality_code="AR", birth_year=2004, position="Attacking Midfielder", competition_level="elite", appearances=24, minutes=1360, goals=4, assists=4),
    player(tier="prospect", key="can-uzun-001", name="Can Uzun", nationality="Turkey", nationality_code="TR", birth_year=2005, position="Attacking Midfielder", competition_level="developmental", appearances=26, minutes=1890, goals=11, assists=4),
    player(tier="prospect", key="moscardo-001", name="Gabriel Moscardo", nationality="Brazil", nationality_code="BR", birth_year=2005, position="Defensive Midfielder", competition_level="developmental", appearances=18, minutes=1225, goals=1, assists=2),
    player(tier="prospect", key="santiago-castro-001", name="Santiago Castro", nationality="Argentina", nationality_code="AR", birth_year=2004, position="Striker", competition_level="top_flight", appearances=27, minutes=1720, goals=9, assists=3),
    player(tier="prospect", key="caleb-okoli-001", name="Caleb Okoli", nationality="Italy", nationality_code="IT", birth_year=2001, position="Centre-Back", competition_level="top_flight", appearances=29, minutes=2470, goals=1, assists=1, clean_sheets=10),
    player(tier="prospect", key="carlos-forbs-001", name="Carlos Forbs", nationality="Portugal", nationality_code="PT", birth_year=2004, position="Winger", competition_level="top_flight", appearances=21, minutes=1110, goals=3, assists=2),
    player(tier="prospect", key="julio-enciso-001", name="Julio Enciso", nationality="Paraguay", nationality_code="PY", birth_year=2004, position="Attacking Midfielder", competition_level="elite", appearances=20, minutes=1095, goals=4, assists=2),
]

FILLER_GK = [
    player(tier="filler", key="mamardashvili-001", name="Giorgi Mamardashvili", nationality="Georgia", nationality_code="GE", birth_year=2000, position="Goalkeeper", competition_level="top_flight", appearances=31, minutes=2790, clean_sheets=11),
    player(tier="filler", key="maignan-001", name="Mike Maignan", nationality="France", nationality_code="FR", birth_year=1995, position="Goalkeeper", competition_level="elite", appearances=28, minutes=2520, clean_sheets=12),
    player(tier="filler", key="sommer-001", name="Yann Sommer", nationality="Switzerland", nationality_code="CH", birth_year=1988, position="Goalkeeper", competition_level="elite", appearances=32, minutes=2880, clean_sheets=14),
    player(tier="filler", key="onana-001", name="Andre Onana", nationality="Cameroon", nationality_code="CM", birth_year=1996, position="Goalkeeper", competition_level="elite", appearances=33, minutes=2970, clean_sheets=10),
    player(tier="filler", key="david-raya-001", name="David Raya", nationality="Spain", nationality_code="ES", birth_year=1995, position="Goalkeeper", competition_level="elite", appearances=30, minutes=2700, clean_sheets=13),
    player(tier="filler", key="unai-simon-001", name="Unai Simon", nationality="Spain", nationality_code="ES", birth_year=1997, position="Goalkeeper", competition_level="top_flight", appearances=29, minutes=2610, clean_sheets=12),
    player(tier="filler", key="diogo-costa-001", name="Diogo Costa", nationality="Portugal", nationality_code="PT", birth_year=1999, position="Goalkeeper", competition_level="top_flight", appearances=31, minutes=2790, clean_sheets=13),
    player(tier="filler", key="alex-meret-001", name="Alex Meret", nationality="Italy", nationality_code="IT", birth_year=1997, position="Goalkeeper", competition_level="elite", appearances=27, minutes=2430, clean_sheets=11),
    player(tier="filler", key="kobel-001", name="Gregor Kobel", nationality="Switzerland", nationality_code="CH", birth_year=1997, position="Goalkeeper", competition_level="elite", appearances=28, minutes=2520, clean_sheets=12),
    player(tier="filler", key="jose-sa-001", name="Jose Sa", nationality="Portugal", nationality_code="PT", birth_year=1993, position="Goalkeeper", competition_level="top_flight", appearances=31, minutes=2790, clean_sheets=9),
    player(tier="filler", key="livakovic-001", name="Dominik Livakovic", nationality="Croatia", nationality_code="HR", birth_year=1995, position="Goalkeeper", competition_level="top_flight", appearances=30, minutes=2700, clean_sheets=11),
    player(tier="filler", key="trubin-001", name="Anatoliy Trubin", nationality="Ukraine", nationality_code="UA", birth_year=2001, position="Goalkeeper", competition_level="top_flight", appearances=29, minutes=2610, clean_sheets=10),
]

FILLER_DEF = [
    player(tier="filler", key="frimpong-001", name="Jeremie Frimpong", nationality="Netherlands", nationality_code="NL", birth_year=2000, position="Full-Back", competition_level="elite", appearances=31, minutes=2475, goals=6, assists=8, clean_sheets=9),
    player(tier="filler", key="dumfries-001", name="Denzel Dumfries", nationality="Netherlands", nationality_code="NL", birth_year=1996, position="Full-Back", competition_level="elite", appearances=29, minutes=2250, goals=4, assists=6, clean_sheets=11),
    player(tier="filler", key="hincapie-001", name="Piero Hincapie", nationality="Ecuador", nationality_code="EC", birth_year=2002, position="Centre-Back", competition_level="elite", appearances=30, minutes=2580, goals=2, assists=1, clean_sheets=10),
    player(tier="filler", key="romero-001", name="Cristian Romero", nationality="Argentina", nationality_code="AR", birth_year=1998, position="Centre-Back", competition_level="elite", appearances=28, minutes=2445, goals=3, assists=1, clean_sheets=9),
    player(tier="filler", key="lisandro-martinez-001", name="Lisandro Martinez", nationality="Argentina", nationality_code="AR", birth_year=1998, position="Centre-Back", competition_level="elite", appearances=24, minutes=2040, goals=1, assists=1, clean_sheets=8),
    player(tier="filler", key="kounde-001", name="Jules Kounde", nationality="France", nationality_code="FR", birth_year=1998, position="Full-Back", competition_level="elite", appearances=33, minutes=2860, goals=2, assists=4, clean_sheets=12),
    player(tier="filler", key="bastoni-001", name="Alessandro Bastoni", nationality="Italy", nationality_code="IT", birth_year=1999, position="Centre-Back", competition_level="elite", appearances=31, minutes=2680, goals=1, assists=4, clean_sheets=13),
    player(tier="filler", key="araujo-001", name="Ronald Araujo", nationality="Uruguay", nationality_code="UY", birth_year=1999, position="Centre-Back", competition_level="elite", appearances=27, minutes=2350, goals=2, assists=1, clean_sheets=11),
    player(tier="filler", key="tah-001", name="Jonathan Tah", nationality="Germany", nationality_code="DE", birth_year=1996, position="Centre-Back", competition_level="elite", appearances=32, minutes=2870, goals=3, assists=1, clean_sheets=13),
    player(tier="filler", key="kim-min-jae-001", name="Kim Min-jae", nationality="South Korea", nationality_code="KR", birth_year=1996, position="Centre-Back", competition_level="elite", appearances=31, minutes=2760, goals=2, assists=1, clean_sheets=12),
    player(tier="filler", key="nathan-ake-001", name="Nathan Ake", nationality="Netherlands", nationality_code="NL", birth_year=1995, position="Centre-Back", competition_level="elite", appearances=29, minutes=2410, goals=2, assists=2, clean_sheets=10),
    player(tier="filler", key="dimarco-001", name="Federico Dimarco", nationality="Italy", nationality_code="IT", birth_year=1997, position="Full-Back", competition_level="elite", appearances=30, minutes=2360, goals=4, assists=7, clean_sheets=11),
    player(tier="filler", key="nuno-mendes-001", name="Nuno Mendes", nationality="Portugal", nationality_code="PT", birth_year=2002, position="Full-Back", competition_level="elite", appearances=24, minutes=1870, goals=1, assists=5, clean_sheets=8),
    player(tier="filler", key="zinchenko-001", name="Oleksandr Zinchenko", nationality="Ukraine", nationality_code="UA", birth_year=1996, position="Full-Back", competition_level="elite", appearances=26, minutes=1895, goals=1, assists=4, clean_sheets=9),
    player(tier="filler", key="malo-gusto-001", name="Malo Gusto", nationality="France", nationality_code="FR", birth_year=2003, position="Full-Back", competition_level="elite", appearances=27, minutes=2010, goals=1, assists=5, clean_sheets=8),
    player(tier="filler", key="guehi-001", name="Marc Guehi", nationality="England", nationality_code="GB", birth_year=2000, position="Centre-Back", competition_level="top_flight", appearances=31, minutes=2735, goals=2, assists=1, clean_sheets=10),
    player(tier="filler", key="tapsoba-001", name="Edmond Tapsoba", nationality="Burkina Faso", nationality_code="BF", birth_year=1999, position="Centre-Back", competition_level="elite", appearances=29, minutes=2550, goals=2, assists=1, clean_sheets=11),
    player(tier="filler", key="goncalo-inacio-001", name="Goncalo Inacio", nationality="Portugal", nationality_code="PT", birth_year=2001, position="Centre-Back", competition_level="top_flight", appearances=30, minutes=2630, goals=3, assists=2, clean_sheets=12),
]

FILLER_MID = [
    player(tier="filler", key="bruno-guimaraes-001", name="Bruno Guimaraes", nationality="Brazil", nationality_code="BR", birth_year=1997, position="Central Midfielder", competition_level="elite", appearances=33, minutes=2875, goals=6, assists=7),
    player(tier="filler", key="tonali-001", name="Sandro Tonali", nationality="Italy", nationality_code="IT", birth_year=2000, position="Central Midfielder", competition_level="elite", appearances=28, minutes=2380, goals=3, assists=4),
    player(tier="filler", key="koopmeiners-001", name="Teun Koopmeiners", nationality="Netherlands", nationality_code="NL", birth_year=1998, position="Central Midfielder", competition_level="elite", appearances=32, minutes=2780, goals=11, assists=5),
    player(tier="filler", key="calhanoglu-001", name="Hakan Calhanoglu", nationality="Turkey", nationality_code="TR", birth_year=1994, position="Attacking Midfielder", competition_level="elite", appearances=31, minutes=2675, goals=9, assists=7),
    player(tier="filler", key="mac-allister-001", name="Alexis Mac Allister", nationality="Argentina", nationality_code="AR", birth_year=1998, position="Central Midfielder", competition_level="elite", appearances=33, minutes=2825, goals=7, assists=6),
    player(tier="filler", key="szoboszlai-001", name="Dominik Szoboszlai", nationality="Hungary", nationality_code="HU", birth_year=2000, position="Attacking Midfielder", competition_level="elite", appearances=30, minutes=2430, goals=6, assists=8),
    player(tier="filler", key="enzo-fernandez-001", name="Enzo Fernandez", nationality="Argentina", nationality_code="AR", birth_year=2001, position="Central Midfielder", competition_level="elite", appearances=31, minutes=2620, goals=4, assists=5),
    player(tier="filler", key="caicedo-001", name="Moises Caicedo", nationality="Ecuador", nationality_code="EC", birth_year=2001, position="Defensive Midfielder", competition_level="elite", appearances=32, minutes=2770, goals=2, assists=3),
    player(tier="filler", key="locatelli-001", name="Manuel Locatelli", nationality="Italy", nationality_code="IT", birth_year=1998, position="Defensive Midfielder", competition_level="elite", appearances=31, minutes=2690, goals=2, assists=4),
    player(tier="filler", key="conor-gallagher-001", name="Conor Gallagher", nationality="England", nationality_code="GB", birth_year=2000, position="Central Midfielder", competition_level="elite", appearances=33, minutes=2845, goals=6, assists=5),
    player(tier="filler", key="khephren-thuram-001", name="Khephren Thuram", nationality="France", nationality_code="FR", birth_year=2001, position="Central Midfielder", competition_level="top_flight", appearances=29, minutes=2370, goals=3, assists=5),
    player(tier="filler", key="zielinski-001", name="Piotr Zielinski", nationality="Poland", nationality_code="PL", birth_year=1994, position="Attacking Midfielder", competition_level="elite", appearances=28, minutes=2150, goals=5, assists=6),
    player(tier="filler", key="tielemans-001", name="Youri Tielemans", nationality="Belgium", nationality_code="BE", birth_year=1997, position="Central Midfielder", competition_level="top_flight", appearances=31, minutes=2615, goals=5, assists=6),
    player(tier="filler", key="bennacer-001", name="Ismael Bennacer", nationality="Algeria", nationality_code="DZ", birth_year=1997, position="Defensive Midfielder", competition_level="elite", appearances=25, minutes=1960, goals=2, assists=3),
    player(tier="filler", key="yangel-herrera-001", name="Yangel Herrera", nationality="Venezuela", nationality_code="VE", birth_year=1998, position="Central Midfielder", competition_level="top_flight", appearances=30, minutes=2460, goals=5, assists=4),
    player(tier="filler", key="palacios-001", name="Exequiel Palacios", nationality="Argentina", nationality_code="AR", birth_year=1998, position="Central Midfielder", competition_level="elite", appearances=30, minutes=2390, goals=4, assists=4),
    player(tier="filler", key="kokcu-001", name="Orkun Kokcu", nationality="Turkey", nationality_code="TR", birth_year=2000, position="Central Midfielder", competition_level="top_flight", appearances=31, minutes=2660, goals=6, assists=7),
    player(tier="filler", key="reijnders-001", name="Tijjani Reijnders", nationality="Netherlands", nationality_code="NL", birth_year=1998, position="Central Midfielder", competition_level="elite", appearances=32, minutes=2740, goals=6, assists=5),
]

FILLER_FWD = [
    player(tier="filler", key="gakpo-001", name="Cody Gakpo", nationality="Netherlands", nationality_code="NL", birth_year=1999, position="Winger", competition_level="elite", appearances=31, minutes=2235, goals=12, assists=6),
    player(tier="filler", key="darwin-nunez-001", name="Darwin Nunez", nationality="Uruguay", nationality_code="UY", birth_year=1999, position="Striker", competition_level="elite", appearances=32, minutes=2360, goals=15, assists=7),
    player(tier="filler", key="vlahovic-001", name="Dusan Vlahovic", nationality="Serbia", nationality_code="RS", birth_year=2000, position="Striker", competition_level="elite", appearances=30, minutes=2460, goals=17, assists=4),
    player(tier="filler", key="jonathan-david-001", name="Jonathan David", nationality="Canada", nationality_code="CA", birth_year=2000, position="Striker", competition_level="top_flight", appearances=31, minutes=2525, goals=18, assists=4),
    player(tier="filler", key="openda-001", name="Lois Openda", nationality="Belgium", nationality_code="BE", birth_year=2000, position="Striker", competition_level="elite", appearances=30, minutes=2355, goals=17, assists=4),
    player(tier="filler", key="kolo-muani-001", name="Randal Kolo Muani", nationality="France", nationality_code="FR", birth_year=1998, position="Striker", competition_level="elite", appearances=28, minutes=2020, goals=10, assists=5),
    player(tier="filler", key="solanke-001", name="Dominic Solanke", nationality="England", nationality_code="GB", birth_year=1997, position="Striker", competition_level="top_flight", appearances=32, minutes=2730, goals=18, assists=3),
    player(tier="filler", key="mbeumo-001", name="Bryan Mbeumo", nationality="Cameroon", nationality_code="CM", birth_year=1999, position="Winger", competition_level="top_flight", appearances=29, minutes=2320, goals=11, assists=6),
    player(tier="filler", key="pedro-neto-001", name="Pedro Neto", nationality="Portugal", nationality_code="PT", birth_year=2000, position="Winger", competition_level="top_flight", appearances=25, minutes=1825, goals=5, assists=8),
    player(tier="filler", key="joao-pedro-001", name="Joao Pedro", nationality="Brazil", nationality_code="BR", birth_year=2001, position="Striker", competition_level="elite", appearances=28, minutes=2060, goals=10, assists=4),
    player(tier="filler", key="ferran-torres-001", name="Ferran Torres", nationality="Spain", nationality_code="ES", birth_year=2000, position="Winger", competition_level="elite", appearances=29, minutes=1740, goals=11, assists=4),
    player(tier="filler", key="goncalo-ramos-001", name="Goncalo Ramos", nationality="Portugal", nationality_code="PT", birth_year=2001, position="Striker", competition_level="elite", appearances=27, minutes=1885, goals=12, assists=3),
    player(tier="filler", key="guirassy-001", name="Serhou Guirassy", nationality="Guinea", nationality_code="GN", birth_year=1996, position="Striker", competition_level="elite", appearances=28, minutes=2210, goals=20, assists=3),
    player(tier="filler", key="marcus-thuram-001", name="Marcus Thuram", nationality="France", nationality_code="FR", birth_year=1997, position="Striker", competition_level="elite", appearances=31, minutes=2470, goals=15, assists=8),
    player(tier="filler", key="evan-ferguson-001", name="Evan Ferguson", nationality="Ireland", nationality_code="IE", birth_year=2004, position="Striker", competition_level="elite", appearances=22, minutes=1280, goals=7, assists=2),
]


def main() -> None:
    categories = {
        "global_stars": GLOBAL_STARS,
        "nigerian_core": NIGERIAN_CORE,
        "prospects": PROSPECTS,
        "fillers_gk": FILLER_GK,
        "fillers_def": FILLER_DEF,
        "fillers_mid": FILLER_MID,
        "fillers_fwd": FILLER_FWD,
    }
    counts = {name: len(items) for name, items in categories.items()}
    assert counts["global_stars"] == 18
    assert counts["nigerian_core"] == 24
    assert counts["prospects"] == 45
    assert counts["fillers_gk"] == 12
    assert counts["fillers_def"] == 18
    assert counts["fillers_mid"] == 18
    assert counts["fillers_fwd"] == 15

    players = [
        *GLOBAL_STARS,
        *NIGERIAN_CORE,
        *PROSPECTS,
        *FILLER_GK,
        *FILLER_DEF,
        *FILLER_MID,
        *FILLER_FWD,
    ]
    assert len(players) == 150

    manifest = {
        "mode": "curated_seed",
        "players": players,
    }
    review = {
        "batch_id": "first-controlled-batch-v1",
        "total_players": len(players),
        "counts": {
            "global_stars": counts["global_stars"],
            "nigerian_core": counts["nigerian_core"],
            "prospects": counts["prospects"],
            "fillers_total": counts["fillers_gk"] + counts["fillers_def"] + counts["fillers_mid"] + counts["fillers_fwd"],
            "fillers_gk": counts["fillers_gk"],
            "fillers_def": counts["fillers_def"],
            "fillers_mid": counts["fillers_mid"],
            "fillers_fwd": counts["fillers_fwd"],
        },
        "source_player_keys": {
            name: [item["source_player_key"] for item in items]
            for name, items in categories.items()
        },
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    REVIEW_PATH.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()

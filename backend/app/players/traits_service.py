from __future__ import annotations

import hashlib
import unicodedata
from typing import Any


def _norm_name(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().replace("-", " ").replace("'", "").split())


# Authentic real-world Styles of Play and Traits/Skills sourced from EA FC 25 PlayStyles,
# Football Manager player traits, and Opta/scouting profiles.
CURATED_PLAYER_PROFILES: dict[str, tuple[str, list[str]]] = {
    # Recently calibrated & featured players
    "younes ebnoutalib": (
        "Target Man",
        [
            "Power Header",
            "Plays With Back To Goal",
            "Aerial Dominance",
            "First-Time Shots",
            "Hold-Up Play",
            "Physical Presence",
        ],
    ),
    "said el mala": (
        "Inverted Winger",
        [
            "Rapid",
            "Technical Dribbler",
            "Low Driven Shot",
            "Cuts Inside From Left Wing",
            "Quick Step",
            "Flair",
        ],
    ),
    "sadiq saleh": (
        "Goal Poacher",
        [
            "Tries To Beat Offside Trap",
            "Pressing Forward",
            "Speed Dribbler",
            "Places Shots",
            "Moves Into Channels",
        ],
    ),
    "wael mohya": (
        "Advanced Playmaker",
        [
            "Playmaker",
            "Technical Dribbler",
            "Flair",
            "Incisive Pass",
            "First Touch",
            "Press Proven",
        ],
    ),
    "zadok yohanna": (
        "Inverted Winger",
        [
            "Cuts Inside From Right Wing",
            "Speed Dribbler",
            "Finesse Shot",
            "Flair",
            "Quick Step",
        ],
    ),
    "peter edokpolor": (
        "Complete Forward",
        [
            "Power Header",
            "Speed Dribbler",
            "Tries To Beat Offside Trap",
            "Shoots With Power",
            "Aerial Threat",
        ],
    ),
    "sani suleiman": (
        "Inverted Winger",
        [
            "Rapid",
            "Speed Dribbler",
            "Cuts Inside From Wing",
            "Knocks Ball Past Opponent",
            "Flair",
        ],
    ),
    "adamu yakubu": (
        "Ball-Winning Midfielder",
        [
            "Slides Into Tackles",
            "Intercept",
            "Anticipate",
            "Bruiser",
            "Relentless",
            "Long Ball Pass",
        ],
    ),
    "shedrack egboh": (
        "Inverted Winger",
        [
            "Cuts Inside From Right Wing",
            "Finesse Shot",
            "Technical Dribbler",
            "Quick Step",
            "Flair",
        ],
    ),
    "victor adeoye": (
        "Deep-Lying Playmaker",
        [
            "Slides Into Tackles",
            "Intercept",
            "Press Proven",
            "Dictates Tempo",
            "Plays Short Simple Passes",
        ],
    ),
    "benjamin fredrick": (
        "Ball-Playing Defender",
        [
            "Anticipate",
            "Slides Into Tackles",
            "Jockey",
            "Calm Under Pressure",
            "Plays Out Of Defense",
        ],
    ),
    "vince osuji": (
        "Ball-Playing Defender",
        [
            "Bruiser",
            "Slides Into Tackles",
            "Aerial Dominance",
            "Anticipate",
            "Block",
        ],
    ),
    "victory akpe": (
        "No-Nonsense Stopper",
        [
            "Aerial Dominance",
            "Power Header",
            "Slides Into Tackles",
            "Bruiser",
            "Block",
        ],
    ),
    "abdulrasheed shehu dabai": (
        "Goal Poacher",
        [
            "Tries To Beat Offside Trap",
            "First-Time Shots",
            "Places Shots",
            "Moves Into Channels",
        ],
    ),
    "aderemi adeoye": (
        "Anchor Man",
        [
            "Slides Into Tackles",
            "Intercept",
            "Marks Opponent Tightly",
            "Block",
            "Plays Short Simple Passes",
        ],
    ),
    # Active World-Class & Marquee Superstars
    "kylian mbappe": (
        "Inside Forward / Complete Striker",
        [
            "Rapid+",
            "Quick Step",
            "Finesse Shot",
            "Technical Dribbler",
            "Outside Foot Shot (Trivela)",
            "Tries To Beat Offside Trap",
        ],
    ),
    "erling haaland": (
        "Goal Poacher & Target Man",
        [
            "Acrobatic+",
            "Power Shot",
            "Power Header",
            "Tries To Beat Offside Trap",
            "Rapid",
            "Bruiser",
        ],
    ),
    "erling braut haland": (
        "Goal Poacher & Target Man",
        [
            "Acrobatic+",
            "Power Shot",
            "Power Header",
            "Tries To Beat Offside Trap",
            "Rapid",
            "Bruiser",
        ],
    ),
    "jude bellingham": (
        "Box-to-Box Playmaker",
        [
            "Relentless+",
            "Technical Dribbler",
            "First Touch",
            "Intercept",
            "Slides Into Tackles",
            "Arrives Late In Opponent's Box",
        ],
    ),
    "vinicius junior": (
        "Inverted Winger",
        [
            "Trickster+",
            "Rapid",
            "Quick Step",
            "Flair",
            "Cuts Inside From Left Wing",
            "Technical Dribbler",
        ],
    ),
    "rodri": (
        "Deep-Lying Playmaker",
        [
            "Pinged Pass+",
            "Dictates Tempo",
            "Intercept",
            "Anticipate",
            "Power Shot",
            "Press Proven",
            "Slides Into Tackles",
        ],
    ),
    "ngolo kante": (
        "Ball-Winning Midfielder",
        [
            "Intercept+",
            "Relentless+",
            "Slides Into Tackles",
            "Anticipate",
            "Quick Step",
            "Press Proven",
        ],
    ),
    "lamine yamal": (
        "Inverted Winger & Wide Playmaker",
        [
            "Technical+",
            "Finesse Shot",
            "Outside Foot Shot (Trivela)",
            "Flair",
            "Cuts Inside From Right Wing",
            "Incisive Pass",
        ],
    ),
    "bukayo saka": (
        "Inverted Winger",
        [
            "Rapid+",
            "Finesse Shot",
            "Technical Dribbler",
            "Whipped Cross",
            "Cuts Inside From Right Wing",
            "First Touch",
        ],
    ),
    "martin odegaard": (
        "Advanced Playmaker",
        [
            "Incisive Pass+",
            "Playmaker",
            "Technical Dribbler",
            "Press Proven",
            "Outside Foot Shot (Trivela)",
            "First Touch",
        ],
    ),
    "mohamed salah": (
        "Inside Forward / Inverted Winger",
        [
            "Finesse Shot+",
            "Rapid+",
            "Cuts Inside From Right Wing",
            "Outside Foot Shot (Trivela)",
            "Chip Shot",
            "Tries To Beat Offside Trap",
        ],
    ),
    "harry kane": (
        "Deep-Lying Forward & Complete Striker",
        [
            "Finesse Shot",
            "Power Shot",
            "Long Ball Pass",
            "Outside Foot Shot (Trivela)+",
            "Dead Ball Specialist",
            "Drops Deep To Link Play",
        ],
    ),
    "kevin de bruyne": (
        "Advanced Playmaker",
        [
            "Incisive Pass+",
            "Whipped Cross+",
            "Long Ball Pass",
            "Pinged Pass",
            "Power Shot",
            "Playmaker",
        ],
    ),
    "cole palmer": (
        "Advanced Playmaker / Inverted Winger",
        [
            "Finesse Shot+",
            "Incisive Pass",
            "Technical Dribbler",
            "Penalty Specialist",
            "First Touch",
            "Outside Foot Shot (Trivela)",
        ],
    ),
    "jamal musiala": (
        "Advanced Playmaker & Dribbler",
        [
            "Technical+",
            "Trickster",
            "First Touch",
            "Flair",
            "Close Control",
            "Quick Step",
        ],
    ),
    "florian wirtz": (
        "Advanced Playmaker",
        [
            "Incisive Pass+",
            "Technical Dribbler",
            "Tiki-Taka",
            "First Touch",
            "Press Proven",
            "Playmaker",
        ],
    ),
    "pedri": (
        "Deep-Lying Playmaker",
        [
            "Incisive Pass+",
            "Tiki-Taka",
            "Technical Dribbler",
            "Press Proven",
            "First Touch",
            "Dictates Tempo",
        ],
    ),
    "vitinha": (
        "Deep-Lying Playmaker",
        [
            "Tiki-Taka+",
            "Press Proven",
            "Technical Dribbler",
            "Incisive Pass",
            "Long Shot Taker",
            "Dictates Tempo",
        ],
    ),
    "declan rice": (
        "Box-to-Box / Ball-Winning Midfielder",
        [
            "Intercept+",
            "Slides Into Tackles",
            "Anticipate",
            "Bruiser",
            "Relentless",
            "Long Ball Pass",
        ],
    ),
    "federico valverde": (
        "Box-to-Box Midfielder",
        [
            "Power Shot+",
            "Relentless+",
            "Rapid",
            "Long Shot Taker",
            "Slides Into Tackles",
            "Intercept",
        ],
    ),
    "federico santiago valverde dipetta": (
        "Box-to-Box Midfielder",
        [
            "Power Shot+",
            "Relentless+",
            "Rapid",
            "Long Shot Taker",
            "Slides Into Tackles",
            "Intercept",
        ],
    ),
    "william saliba": (
        "Ball-Playing Defender",
        [
            "Anticipate+",
            "Jockey",
            "Slides Into Tackles",
            "Block",
            "Bruiser",
            "Aerial Dominance",
        ],
    ),
    "virgil van dijk": (
        "Ball-Playing Defender & Aerial Stopper",
        [
            "Anticipate+",
            "Aerial Dominance",
            "Bruiser",
            "Long Ball Pass",
            "Power Header",
            "Leadership",
        ],
    ),
    "ruben dias": (
        "Stopper / Ball-Playing Defender",
        [
            "Bruiser+",
            "Block",
            "Slides Into Tackles",
            "Anticipate",
            "Leadership",
            "Jockey",
        ],
    ),
    "josko gvardiol": (
        "Ball-Playing Defender",
        [
            "Block+",
            "Slides Into Tackles",
            "Anticipate",
            "Long Ball Pass",
            "Bruiser",
            "Relentless",
        ],
    ),
    "ronald federico araujo da silva": (
        "Stopper / Cover Defender",
        [
            "Slides Into Tackles",
            "Bruiser+",
            "Aerial Dominance",
            "Block",
            "Rapid Recovery",
            "Jockey",
        ],
    ),
    "ronald araujo": (
        "Stopper / Cover Defender",
        [
            "Slides Into Tackles",
            "Bruiser+",
            "Aerial Dominance",
            "Block",
            "Rapid Recovery",
            "Jockey",
        ],
    ),
    "achraf hakimi": (
        "Attacking Wing-Back",
        [
            "Relentless+",
            "Quick Step",
            "Whipped Cross",
            "Speed Dribbler",
            "Slides Into Tackles",
            "Overlapping Runs",
        ],
    ),
    "trent alexander arnold": (
        "Inverted Full-Back & Playmaker",
        [
            "Whipped Cross+",
            "Long Ball Pass+",
            "Incisive Pass",
            "Dead Ball Specialist",
            "Switches Ball To Other Flank",
        ],
    ),
    "nuno mendes": (
        "Attacking Wing-Back",
        [
            "Rapid+",
            "Quick Step",
            "Whipped Cross",
            "Slides Into Tackles",
            "Speed Dribbler",
            "Relentless",
        ],
    ),
    "victor osimhen": (
        "Goal Poacher & Pressing Forward",
        [
            "Power Header+",
            "Acrobatic Finisher",
            "Tries To Beat Offside Trap",
            "Relentless High Pressing",
            "Shoots With Power",
            "Rapid",
        ],
    ),
    "ademola lookman": (
        "Inverted Winger / Inside Forward",
        [
            "Rapid",
            "Technical Dribbler",
            "Finesse Shot",
            "Flair",
            "Cuts Inside From Left Wing",
            "Big Match Performer",
        ],
    ),
    "victor boniface": (
        "Target Man & Complete Forward",
        [
            "Power Header",
            "Press Proven",
            "Trickster",
            "Shoots With Power",
            "Plays With Back To Goal",
        ],
    ),
    "mohammed kudus": (
        "Inverted Winger & Ball Carrier",
        [
            "Technical Dribbler",
            "Press Proven",
            "Flair",
            "First Touch",
            "Shoots With Power",
        ],
    ),
    "alexander isak": (
        "Complete Forward",
        [
            "Finesse Shot+",
            "Rapid",
            "Technical Dribbler",
            "First Touch",
            "Tries To Beat Offside Trap",
        ],
    ),
    "julian alvarez": (
        "Pressing Forward & Shadow Striker",
        [
            "Relentless+",
            "Finesse Shot",
            "Pressing Forward",
            "First Touch",
            "Dead Ball Specialist",
            "Technical Dribbler",
        ],
    ),
    "raphinha": (
        "Inverted Winger",
        [
            "Rapid",
            "Whipped Cross",
            "Finesse Shot",
            "Relentless",
            "Flair",
            "Cuts Inside From Right Wing",
        ],
    ),
    "rodrygo": (
        "Inside Forward / Inverted Winger",
        [
            "Technical Dribbler",
            "Finesse Shot",
            "First Touch",
            "Quick Step",
            "Flair",
        ],
    ),
    "ousmane dembele": (
        "Explosive Winger",
        [
            "Rapid+",
            "Trickster+",
            "Two-Footed Dribbler",
            "Quick Step",
            "Whipped Cross",
            "Flair",
        ],
    ),
    "desire doue": (
        "Creative Playmaker & Winger",
        [
            "Technical Dribbler",
            "Flair",
            "Trickster",
            "Incisive Pass",
            "First Touch",
        ],
    ),
    "luis fernando diaz marulanda": (
        "Inverted Winger",
        [
            "Rapid",
            "Technical Dribbler",
            "Flair",
            "Relentless",
            "Cuts Inside From Left Wing",
        ],
    ),
    "luis diaz": (
        "Inverted Winger",
        [
            "Rapid",
            "Technical Dribbler",
            "Flair",
            "Relentless",
            "Cuts Inside From Left Wing",
        ],
    ),
    "son heung min": (
        "Inside Forward & Goal Poacher",
        [
            "Finesse Shot+",
            "Rapid",
            "Two-Footed Finisher",
            "Power Shot",
            "Quick Step",
            "Tries To Beat Offside Trap",
        ],
    ),
    "robert lewandowski": (
        "Target Man & Goal Poacher",
        [
            "Power Header+",
            "Power Shot",
            "First Touch",
            "Outside Foot Shot (Trivela)",
            "Acrobatic Finisher",
            "Penalty Specialist",
        ],
    ),
    "lautaro martinez": (
        "Goal Poacher & Pressing Forward",
        [
            "Power Shot",
            "First Touch",
            "Press Proven",
            "Relentless",
            "Outside Foot Shot (Trivela)",
            "Tries To Beat Offside Trap",
        ],
    ),
    "antoine griezmann": (
        "Deep-Lying Forward & Playmaker",
        [
            "Outside Foot Shot (Trivela)+",
            "Finesse Shot",
            "Incisive Pass",
            "Technical Dribbler",
            "First Touch",
            "Relentless",
        ],
    ),
    "bruno fernandes": (
        "Advanced Playmaker",
        [
            "Incisive Pass+",
            "Long Ball Pass",
            "Pinged Pass",
            "Outside Foot Shot (Trivela)",
            "Power Shot",
            "Relentless",
        ],
    ),
    "bernardo silva": (
        "Advanced Playmaker",
        [
            "Technical+",
            "Press Proven",
            "Tiki-Taka",
            "First Touch",
            "Relentless",
            "Playmaker",
        ],
    ),
    "frenkie de jong": (
        "Deep-Lying Playmaker",
        [
            "Press Proven+",
            "Outside Foot Shot (Trivela)",
            "Incisive Pass",
            "Technical Dribbler",
            "Dictates Tempo",
        ],
    ),
    "thibaut courtois": (
        "Commanding Shot-Stopper",
        [
            "Far Reach+",
            "Cross Claimer",
            "1v1 Close Down",
            "Quick Reflexes",
            "Long Thrower",
        ],
    ),
    "gianluigi donnarumma": (
        "Shot-Stopper Goalkeeper",
        [
            "Quick Reflexes+",
            "Far Reach",
            "1v1 Close Down",
            "Penalty Saver",
            "Cross Claimer",
        ],
    ),
    "mike maignan": (
        "Sweeper Keeper",
        [
            "Rushes Out Of Goal",
            "Long Ball Distribution",
            "Quick Reflexes",
            "1v1 Close Down",
            "Leadership",
        ],
    ),
    "david raya": (
        "Sweeper Keeper",
        [
            "Cross Claimer+",
            "Long Ball Distribution",
            "Rushes Out Of Goal",
            "Footwork",
            "Quick Reflexes",
        ],
    ),
    # Pantheon & Iconic Legends
    "edson arantes do nascimento (pele)": (
        "Complete Forward & Playmaker",
        [
            "Technical+",
            "Finesse Shot+",
            "Rapid+",
            "Acrobatic Finisher",
            "Power Header",
            "Flair",
            "Two-Footed Maestro",
        ],
    ),
    "pele": (
        "Complete Forward & Playmaker",
        [
            "Technical+",
            "Finesse Shot+",
            "Rapid+",
            "Acrobatic Finisher",
            "Power Header",
            "Flair",
            "Two-Footed Maestro",
        ],
    ),
    "diego maradona": (
        "Advanced Playmaker (Enganche)",
        [
            "Technical+",
            "Trickster+",
            "Flair",
            "Incisive Pass",
            "Press Proven",
            "Dead Ball Specialist",
            "Runs With Ball Through Center",
        ],
    ),
    "lionel messi": (
        "Inverted Winger & False 9 Playmaker",
        [
            "Finesse Shot+",
            "Technical+",
            "Incisive Pass",
            "Dead Ball Specialist",
            "Quick Step",
            "Flair",
            "Chip Shot",
        ],
    ),
    "cristiano ronaldo": (
        "Inside Forward & Complete Striker",
        [
            "Power Shot+",
            "Power Header+",
            "Acrobatic Finisher",
            "Rapid",
            "Trickster",
            "Cuts Inside From Both Wings",
            "Penalty Specialist",
        ],
    ),
    "ronaldo": (
        "Complete Striker & Phenomenon",
        [
            "Rapid+",
            "Quick Step+",
            "Technical Dribbler",
            "Finesse Shot",
            "Power Shot",
            "Trickster",
            "Rounds Keeper",
        ],
    ),
    "zinedine zidane": (
        "Advanced Playmaker",
        [
            "First Touch+",
            "Incisive Pass+",
            "Technical Dribbler",
            "Flair",
            "Press Proven",
            "Outside Foot Shot (Trivela)",
            "Dictates Tempo",
        ],
    ),
    "ronaldinho": (
        "Inverted Winger & Creative Playmaker",
        [
            "Trickster+",
            "Flair+",
            "Technical Dribbler",
            "Finesse Shot",
            "Dead Ball Specialist",
            "Quick Step",
        ],
    ),
    "marco van basten": (
        "Complete Target Striker",
        [
            "Acrobatic+",
            "Power Header",
            "Finesse Shot",
            "First-Time Shots",
            "Power Shot",
            "Clinical Finisher",
        ],
    ),
    "alfredo di stefano": (
        "Complete Total Footballer & Deep-Lying Forward",
        [
            "Relentless+",
            "Playmaker",
            "Incisive Pass",
            "Finesse Shot",
            "Leadership",
            "Box-to-Box Dominance",
        ],
    ),
    "paolo maldini": (
        "Ball-Playing Defender & Defensive Icon",
        [
            "Anticipate+",
            "Slides Into Tackles+",
            "Intercept",
            "Jockey",
            "Block",
            "Leadership",
            "One-Club Icon",
        ],
    ),
    "johan cruyff": (
        "Total Football Playmaker & False 9",
        [
            "Technical+",
            "Incisive Pass+",
            "Outside Foot Shot (Trivela)",
            "Flair",
            "First Touch",
            "Quick Step",
        ],
    ),
    "franz beckenbauer": (
        "Ball-Playing Libero (Sweeper)",
        [
            "Long Ball Pass+",
            "Anticipate+",
            "Outside Foot Shot (Trivela)",
            "Intercept",
            "Dictates Tempo",
            "Leadership",
        ],
    ),
    "thierry henry": (
        "Inside Forward & Complete Striker",
        [
            "Finesse Shot+",
            "Rapid+",
            "Places Shots",
            "Tries To Beat Offside Trap",
            "Technical Dribbler",
            "Chip Shot",
        ],
    ),
    "roberto carlos": (
        "Attacking Wing-Back",
        [
            "Power Shot+",
            "Dead Ball+",
            "Outside Foot Shot (Trivela)",
            "Rapid",
            "Relentless",
            "Slides Into Tackles",
        ],
    ),
    "gianluigi buffon": (
        "Commanding Shot-Stopper",
        [
            "Far Reach+",
            "Quick Reflexes",
            "1v1 Close Down",
            "Cross Claimer",
            "Leadership",
        ],
    ),
    "lev yashin": (
        "Sweeper Keeper & Shot-Stopper",
        [
            "Quick Reflexes+",
            "Cross Claimer+",
            "1v1 Close Down",
            "Penalty Saver",
            "Rushes Out Of Goal",
        ],
    ),
    "ferenc puskas": (
        "Goal Poacher & Inside Forward",
        [
            "Power Shot+",
            "First Touch+",
            "Finesse Shot",
            "Incisive Pass",
            "Outside Foot Shot (Trivela)",
        ],
    ),
    "gerd muller": (
        "Goal Poacher",
        [
            "Finesse Shot+",
            "Acrobatic Finisher",
            "Tries To Beat Offside Trap",
            "First-Time Shots",
            "Power Header",
        ],
    ),
    "garrincha": (
        "Traditional Touchline Winger",
        [
            "Trickster+",
            "Technical+",
            "Rapid",
            "Whipped Cross",
            "Flair",
            "Knocks Ball Past Opponent",
        ],
    ),
    "romario de souza faria": (
        "Goal Poacher",
        [
            "Quick Step+",
            "Finesse Shot",
            "Chip Shot",
            "Tries To Beat Offside Trap",
            "Technical Dribbler",
            "First-Time Shots",
        ],
    ),
    "george weah": (
        "Complete Forward",
        [
            "Rapid+",
            "Power Shot",
            "Speed Dribbler",
            "Acrobatic Finisher",
            "Physical Presence",
        ],
    ),
    "rivaldo": (
        "Advanced Playmaker & Inside Forward",
        [
            "Power Shot+",
            "Acrobatic+",
            "Finesse Shot",
            "Dead Ball Specialist",
            "Technical Dribbler",
            "Flair",
        ],
    ),
    "roberto baggio": (
        "Creative Playmaker (Trequartista)",
        [
            "Technical+",
            "Finesse Shot+",
            "Incisive Pass",
            "First Touch",
            "Dead Ball Specialist",
            "Flair",
        ],
    ),
    "andres iniesta": (
        "Advanced Playmaker",
        [
            "Incisive Pass+",
            "Technical+",
            "Tiki-Taka",
            "First Touch",
            "Press Proven",
            "La Croqueta Dribbler",
        ],
    ),
    "xavi": (
        "Deep-Lying Playmaker",
        [
            "Tiki-Taka+",
            "Incisive Pass+",
            "Long Ball Pass",
            "Dictates Tempo",
            "Press Proven",
            "First Touch",
        ],
    ),
    "luka modric": (
        "Deep-Lying Playmaker",
        [
            "Outside Foot Shot (Trivela)+",
            "Incisive Pass+",
            "Press Proven",
            "Dictates Tempo",
            "Long Ball Pass",
            "Relentless",
        ],
    ),
    "kaka": (
        "Advanced Playmaker & Shadow Striker",
        [
            "Rapid+",
            "Quick Step+",
            "Finesse Shot",
            "Incisive Pass",
            "Technical Dribbler",
            "Runs With Ball Through Center",
        ],
    ),
    "michel platini": (
        "Advanced Playmaker",
        [
            "Incisive Pass+",
            "Dead Ball+",
            "Finesse Shot",
            "First Touch",
            "Playmaker",
            "Arrives Late In Opponent's Box",
        ],
    ),
    "lothar matthaus": (
        "Box-to-Box Midfielder & Libero",
        [
            "Power Shot+",
            "Relentless+",
            "Slides Into Tackles",
            "Intercept",
            "Long Ball Pass",
            "Leadership",
        ],
    ),
    "fabio cannavaro": (
        "Stopper / Cover Defender",
        [
            "Aerial+",
            "Intercept+",
            "Slides Into Tackles",
            "Anticipate",
            "Jockey",
            "Leadership",
        ],
    ),
    "franco baresi": (
        "Ball-Playing Libero",
        [
            "Intercept+",
            "Anticipate+",
            "Slides Into Tackles",
            "Long Ball Pass",
            "Block",
            "Leadership",
        ],
    ),
    "alessandro nesta": (
        "Ball-Playing Defender",
        [
            "Slides Into Tackles+",
            "Anticipate+",
            "Intercept",
            "Jockey",
            "Block",
            "Elegance Under Pressure",
        ],
    ),
    "cafu": (
        "Attacking Wing-Back",
        [
            "Relentless+",
            "Whipped Cross",
            "Rapid",
            "Quick Step",
            "Slides Into Tackles",
            "Leadership",
        ],
    ),
    "andrea pirlo": (
        "Deep-Lying Playmaker (Regista)",
        [
            "Long Ball Pass+",
            "Dead Ball+",
            "Incisive Pass",
            "Dictates Tempo",
            "Pinged Pass",
            "First Touch",
        ],
    ),
    "ruud gullit": (
        "Box-to-Box Complete Midfielder",
        [
            "Power Header+",
            "Relentless+",
            "Power Shot",
            "Bruiser",
            "Aerial Dominance",
            "Slides Into Tackles",
        ],
    ),
    "dennis bergkamp": (
        "Deep-Lying Forward & Creative Playmaker",
        [
            "First Touch+",
            "Finesse Shot+",
            "Incisive Pass",
            "Chip Shot",
            "Flair",
            "Technical Dribbler",
        ],
    ),
    "eric cantona": (
        "Deep-Lying Forward & Target Playmaker",
        [
            "Power Shot+",
            "First Touch+",
            "Flair",
            "Chip Shot",
            "Bruiser",
            "Leadership",
        ],
    ),
    "wayne rooney": (
        "Complete Forward & Box-to-Box Attacker",
        [
            "Power Shot+",
            "Relentless+",
            "Long Ball Pass",
            "Acrobatic Finisher",
            "Bruiser",
            "Slides Into Tackles",
        ],
    ),
    "steven gerrard": (
        "Box-to-Box Midfielder",
        [
            "Power Shot+",
            "Long Ball Pass+",
            "Relentless",
            "Slides Into Tackles",
            "Whipped Cross",
            "Leadership",
        ],
    ),
    "frank lampard": (
        "Box-to-Box Scoring Midfielder",
        [
            "Power Shot+",
            "Arrives Late In Opponent's Box",
            "Finesse Shot",
            "Long Shot Taker",
            "Penalty Specialist",
            "Relentless",
        ],
    ),
    "paul scholes": (
        "Deep-Lying Playmaker",
        [
            "Long Ball Pass+",
            "Power Shot+",
            "Pinged Pass",
            "Dictates Tempo",
            "First-Time Shots",
            "Slides Into Tackles",
        ],
    ),
    "roy keane": (
        "Ball-Winning Midfielder",
        [
            "Bruiser+",
            "Slides Into Tackles+",
            "Dives Into Tackles",
            "Relentless",
            "Intercept",
            "Leadership",
        ],
    ),
    "patrick vieira": (
        "Box-to-Box / Ball-Winning Midfielder",
        [
            "Intercept+",
            "Bruiser+",
            "Slides Into Tackles",
            "Relentless",
            "Block",
            "Leadership",
        ],
    ),
    "didier drogba": (
        "Target Man & Complete Striker",
        [
            "Power Header+",
            "Power Shot+",
            "Bruiser",
            "Plays With Back To Goal",
            "Acrobatic Finisher",
            "Big Match Clutch Performer",
        ],
    ),
    "samuel etoo": (
        "Goal Poacher & Inside Forward",
        [
            "Rapid+",
            "Finesse Shot+",
            "Tries To Beat Offside Trap",
            "Quick Step",
            "Chip Shot",
            "Relentless Pressing",
        ],
    ),
    "yaya toure": (
        "Box-to-Box Powerhouse Midfielder",
        [
            "Power Shot+",
            "Bruiser+",
            "Runs With Ball Through Center",
            "Dead Ball Specialist",
            "Press Proven",
            "Penalty Specialist",
        ],
    ),
    "sergio ramos": (
        "Stopper & Aerial Goal Threat",
        [
            "Power Header+",
            "Slides Into Tackles+",
            "Dives Into Tackles",
            "Bruiser",
            "Anticipate",
            "Penalty Specialist",
            "Leadership",
        ],
    ),
    "toni kroos": (
        "Deep-Lying Playmaker",
        [
            "Long Ball Pass+",
            "Pinged Pass+",
            "Dictates Tempo",
            "Dead Ball Specialist",
            "Finesse Shot",
            "First Touch",
        ],
    ),
    "arjen robben": (
        "Inverted Winger",
        [
            "Finesse Shot+",
            "Rapid+",
            "Cuts Inside From Right Wing",
            "Technical Dribbler",
            "Quick Step",
            "Avoids Using Weaker Foot",
        ],
    ),
    "franck ribery": (
        "Inverted Winger & Wide Playmaker",
        [
            "Technical+",
            "Trickster+",
            "Quick Step",
            "Flair",
            "Cuts Inside From Left Wing",
            "Incisive Pass",
        ],
    ),
    "neymar jr": (
        "Inverted Winger & Creative Playmaker",
        [
            "Trickster+",
            "Technical+",
            "Flair",
            "Finesse Shot",
            "Incisive Pass",
            "Penalty Specialist",
        ],
    ),
    "luis suarez": (
        "Complete Striker & Goal Poacher",
        [
            "Outside Foot Shot (Trivela)+",
            "Power Shot",
            "Finesse Shot",
            "Acrobatic Finisher",
            "Tries To Beat Offside Trap",
            "Relentless",
        ],
    ),
    "sergio aguero": (
        "Goal Poacher",
        [
            "Power Shot+",
            "Quick Step",
            "Finesse Shot",
            "Tries To Beat Offside Trap",
            "Technical Dribbler",
            "First-Time Shots",
        ],
    ),
    "zlatan ibrahimovic": (
        "Target Man & Complete Forward",
        [
            "Acrobatic+",
            "Power Shot+",
            "Bruiser",
            "Flair",
            "Power Header",
            "Plays With Back To Goal",
        ],
    ),
    "manuel neuer": (
        "Sweeper Keeper",
        [
            "Rushes Out Of Goal+",
            "Long Ball Distribution+",
            "1v1 Close Down",
            "Far Reach",
            "Footwork",
            "Leadership",
        ],
    ),
}

# Normalization map for legacy/regen lowercase trait tokens
_TRAIT_TOKEN_LABELS: dict[str, str] = {
    "wall": "Defensive Wall",
    "rock": "No-Nonsense Stopper",
    "playmaker": "Playmaker",
    "speedster": "Speed Dribbler",
    "long_shots": "Long Shot Taker",
    "poacher": "Goal Poacher",
    "clinical": "Clinical Finisher",
    "target_man": "Target Man",
    "engine": "Relentless Engine",
    "leader": "Leadership",
    "flair": "Flair",
    "acrobatic": "Acrobatic",
    "set_piece_specialist": "Dead Ball Specialist",
    "ball_winner": "Slides Into Tackles",
    "slides_into_tackles": "Slides Into Tackles",
    "dives_into_tackles": "Dives Into Tackles",
    "aerial": "Aerial Dominance",
    "sweeper": "Sweeper Keeper",
    "crosser": "Whipped Cross",
    "dribbler": "Technical Dribbler",
    "interceptor": "Intercept",
    "press_resistant": "Press Proven",
}


def normalize_trait_label(trait: Any) -> str | None:
    if not isinstance(trait, str):
        return None
    cleaned = trait.strip()
    if not cleaned:
        return None
    lower = cleaned.lower()
    if lower in _TRAIT_TOKEN_LABELS:
        return _TRAIT_TOKEN_LABELS[lower]
    if lower in {"iconic legend", "prime masterclass"}:
        return None
    if "_" in cleaned:
        return " ".join(w.capitalize() for w in cleaned.split("_") if w)
    return cleaned


def _position_category(pos: str | None, norm_pos: str | None) -> str:
    raw = f"{pos or ''} {norm_pos or ''}".upper()
    tokens = set(raw.replace("/", " ").replace("-", " ").replace(",", " ").split())
    if "GK" in tokens or "GOALKEEPER" in tokens:
        return "GK"
    if any(t in tokens for t in ("LW", "RW", "LM", "RM", "WINGER")) or "AM RL" in raw or "AM L" in raw or "AM R" in raw:
        return "WINGER"
    if any(t in tokens for t in ("ST", "CF", "STRIKER", "FW", "FORWARD", "FWD")) or "AM/F" in raw:
        return "ST"
    if any(t in tokens for t in ("AM", "CAM")) or "ATTACKING MIDFIELDER" in raw:
        return "AM"
    if any(t in tokens for t in ("DM", "CDM")) or "DEFENSIVE MIDFIELDER" in raw:
        return "DM"
    if (
        any(t in tokens for t in ("LB", "RB", "LWB", "RWB", "WB"))
        or "FULL BACK" in raw
        or "D/WB" in raw
        or "D L" in raw
        or "D R" in raw
    ):
        return "FB"
    if (
        any(t in tokens for t in ("CB", "DF", "DEF", "DEFENDER"))
        or "CENTRE BACK" in raw
        or "CENTER BACK" in raw
        or "D C" in raw
        or "D LC" in raw
        or "D RC" in raw
        or "D RLC" in raw
    ):
        return "CB"
    return "CM"


def _extract_stat(dna: dict[str, Any], attrs: dict[str, Any], key: str, default: int = 68) -> int:
    for src in (attrs, dna):
        val = src.get(key)
        if isinstance(val, (int, float)) and val > 0:
            v = float(val)
            if v <= 20:
                v *= 5.0
            elif v <= 1.0:
                v *= 100.0
            return int(max(1, min(99, round(v))))
    return default


def derive_playstyle_and_traits(
    *,
    player_id: str,
    full_name: str,
    position: str | None,
    normalized_position: str | None,
    preferred_foot: str | None,
    height_cm: int | None,
    gsi: int | None,
    dna: dict[str, Any],
) -> tuple[str, list[str]]:
    norm = _norm_name(full_name)
    if norm in CURATED_PLAYER_PROFILES:
        style, curated_traits = CURATED_PLAYER_PROFILES[norm]
        return style, list(curated_traits)

    attrs = dna.get("attributes") if isinstance(dna.get("attributes"), dict) else {}
    base = int(gsi or dna.get("overall") or dna.get("current_rating") or 70)
    pace = _extract_stat(dna, attrs, "pace", base)
    shooting = _extract_stat(dna, attrs, "shooting", base - 4)
    passing = _extract_stat(dna, attrs, "passing", base - 2)
    dribbling = _extract_stat(dna, attrs, "dribbling", base - 1)
    defending = _extract_stat(dna, attrs, "defending", base - 10)
    physical = _extract_stat(dna, attrs, "physical", base)
    height = int(height_cm or dna.get("height_cm") or 180)
    foot = str(preferred_foot or dna.get("preferred_foot") or "Right").strip().lower()
    cat = _position_category(position, normalized_position)

    seed = int(hashlib.md5(f"{player_id}:{full_name}".encode("utf-8")).hexdigest()[:8], 16)
    traits: list[str] = []

    if cat == "GK":
        if passing >= 64 or pace >= 56 or (seed % 3 == 0):
            playstyle = "Sweeper Keeper"
            traits.extend(["Rushes Out Of Goal", "Footwork & Distribution", "Quick Reflexes", "1v1 Close Down"])
        else:
            playstyle = "Shot-Stopper Goalkeeper"
            traits.extend(["Quick Reflexes", "Far Reach", "Cross Claimer", "1v1 Close Down"])
        if height >= 190 or physical >= 78:
            traits.append("Commanding Aerial Presence")
        else:
            traits.append("Long Thrower")

    elif cat == "CB":
        if passing >= 68 or dribbling >= 65 or (seed % 3 == 0 and passing >= 60):
            playstyle = "Ball-Playing Defender"
            traits.extend(["Slides Into Tackles", "Anticipate", "Plays Out Of Defense", "Intercept"])
        elif height >= 189 or physical >= 80:
            playstyle = "No-Nonsense Stopper"
            traits.extend(["Slides Into Tackles", "Aerial Dominance", "Power Header", "Bruiser", "Block"])
        elif pace >= 75:
            playstyle = "Sweeper / Cover Defender"
            traits.extend(["Slides Into Tackles", "Jockey", "Anticipate", "Rapid Recovery", "Intercept"])
        else:
            playstyle = "Central Stopper"
            traits.extend(["Slides Into Tackles", "Block", "Marks Opponent Tightly", "Anticipate"])
        if base >= 84 and "Leadership" not in traits:
            traits.append("Leadership")

    elif cat == "FB":
        if pace >= 79 or dribbling >= 73 or (seed % 3 == 0):
            playstyle = "Attacking Wing-Back"
            traits.extend(["Whipped Cross", "Relentless", "Speed Dribbler", "Slides Into Tackles", "Quick Step"])
        elif passing >= 72:
            playstyle = "Inverted Full-Back"
            traits.extend(["Incisive Pass", "Slides Into Tackles", "Press Proven", "Intercept", "Long Ball Pass"])
        else:
            playstyle = "Complete Wing-Back"
            traits.extend(["Slides Into Tackles", "Jockey", "Early Crosser", "Relentless", "Anticipate"])

    elif cat == "DM":
        if passing >= 75 and dribbling >= 70:
            playstyle = "Deep-Lying Playmaker"
            traits.extend(["Dictates Tempo", "Long Ball Pass", "Press Proven", "Intercept", "Slides Into Tackles"])
        elif defending >= 76 and physical >= 77:
            playstyle = "Anchor Man"
            traits.extend(["Slides Into Tackles", "Intercept", "Block", "Marks Opponent Tightly", "Bruiser"])
        else:
            playstyle = "Ball-Winning Midfielder"
            traits.extend(["Slides Into Tackles", "Dives Into Tackles", "Anticipate", "Relentless", "Intercept"])

    elif cat == "CM":
        if passing >= 77 and passing >= defending + 4:
            playstyle = "Deep-Lying Playmaker"
            traits.extend(["Playmaker", "Incisive Pass", "Dictates Tempo", "Long Ball Pass", "First Touch"])
        elif dribbling >= 76 and shooting >= 70:
            playstyle = "Mezzala / Attacking Midfielder"
            traits.extend(["Technical Dribbler", "Incisive Pass", "Long Shot Taker", "First Touch", "Flair"])
        elif defending >= 74:
            playstyle = "Ball-Winning Midfielder"
            traits.extend(["Slides Into Tackles", "Intercept", "Relentless", "Anticipate", "Bruiser"])
        else:
            playstyle = "Box-to-Box Midfielder"
            traits.extend(["Relentless", "Slides Into Tackles", "Box-to-Box Engine", "Long Shot Taker", "Press Proven"])

    elif cat == "AM":
        if shooting >= 77 and pace >= 78:
            playstyle = "Shadow Striker"
            traits.extend(
                [
                    "Finesse Shot",
                    "Arrives Late In Opponent's Box",
                    "First-Time Shots",
                    "Technical Dribbler",
                    "Quick Step",
                ]
            )
        elif dribbling >= 80 or (seed % 2 == 0 and dribbling >= 74):
            playstyle = "Creative Playmaker"
            traits.extend(["Playmaker", "Technical Dribbler", "Flair", "Incisive Pass", "First Touch"])
        else:
            playstyle = "Advanced Playmaker"
            traits.extend(
                ["Playmaker", "Incisive Pass", "Tries Killer Balls Often", "First Touch", "Outside Foot Shot (Trivela)"]
            )

    elif cat == "WINGER":
        pos_upper = f"{position or ''} {normalized_position or ''}".upper()
        is_left_wing = "LW" in pos_upper or "LM" in pos_upper or "AM L" in pos_upper
        is_right_wing = "RW" in pos_upper or "RM" in pos_upper or "AM R" in pos_upper
        if (
            (is_left_wing and foot == "right")
            or (is_right_wing and foot == "left")
            or shooting >= 74
            or (seed % 3 != 0)
        ):
            playstyle = "Inverted Winger"
            traits.extend(["Cuts Inside From Wing", "Finesse Shot", "Technical Dribbler", "Rapid", "Flair"])
        elif passing >= 76:
            playstyle = "Wide Playmaker"
            traits.extend(["Playmaker", "Whipped Cross", "Incisive Pass", "Technical Dribbler", "First Touch"])
        else:
            playstyle = "Traditional Touchline Winger"
            traits.extend(["Rapid", "Speed Dribbler", "Whipped Cross", "Knocks Ball Past Opponent", "Quick Step"])

    else:  # ST / CF / FW
        if height >= 188 or (physical >= 80 and physical >= pace + 2):
            playstyle = "Target Man"
            traits.extend(["Power Header", "Plays With Back To Goal", "Aerial Dominance", "Hold-Up Play", "Power Shot"])
        elif pace >= 82 and dribbling >= 78:
            playstyle = "Complete Forward"
            traits.extend(["Rapid", "Finesse Shot", "Tries To Beat Offside Trap", "Technical Dribbler", "Power Shot"])
        elif passing >= 74 and dribbling >= 76:
            playstyle = "Deep-Lying Forward"
            traits.extend(
                ["Drops Deep To Link Play", "Incisive Pass", "First Touch", "Finesse Shot", "Technical Dribbler"]
            )
        elif physical >= 77 and (seed % 3 == 0):
            playstyle = "Pressing Forward"
            traits.extend(
                [
                    "Relentless High Pressing",
                    "Tries To Beat Offside Trap",
                    "First-Time Shots",
                    "Power Shot",
                    "Quick Step",
                ]
            )
        else:
            playstyle = "Goal Poacher"
            traits.extend(
                [
                    "Tries To Beat Offside Trap",
                    "Finesse Shot",
                    "First-Time Shots",
                    "Places Shots",
                    "Moves Into Channels",
                ]
            )

    return playstyle, traits[:6]


def resolve_player_traits_and_playstyle(
    player: Any,
    profile: Any | None = None,
    summary: Any | None = None,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    dna = (
        dict(getattr(player, "dna_profile", None) or {})
        if isinstance(getattr(player, "dna_profile", None), dict)
        else {}
    )
    summary_data = (
        dict(getattr(summary, "summary_json", None) or {})
        if summary is not None and isinstance(getattr(summary, "summary_json", None), dict)
        else {}
    )
    prof_meta = (
        dict(getattr(profile, "metadata_json", None) or {})
        if profile is not None and isinstance(getattr(profile, "metadata_json", None), dict)
        else {}
    )

    full_name = (
        getattr(player, "canonical_display_name", None)
        or getattr(player, "full_name", None)
        or (getattr(profile, "canonical_name", None) if profile is not None else None)
        or ""
    )
    norm = _norm_name(full_name)
    if norm in CURATED_PLAYER_PROFILES:
        curated_style, curated_traits = CURATED_PLAYER_PROFILES[norm]
        t_tuple = tuple(curated_traits)
        return curated_style, t_tuple, t_tuple

    playstyle: str | None = None
    for src in (dna, summary_data, prof_meta):
        candidate = src.get("playstyle") or src.get("style_of_play") or src.get("archetype")
        if (
            isinstance(candidate, str)
            and candidate.strip()
            and candidate.strip().lower() not in {"iconic legend", "prime masterclass"}
        ):
            playstyle = candidate.strip()
            break

    collected_traits: list[str] = []
    for src in (dna, summary_data, prof_meta):
        for key in ("traits", "skills", "signature_traits"):
            raw_list = src.get(key)
            if isinstance(raw_list, (list, tuple)):
                for item in raw_list:
                    label = normalize_trait_label(item)
                    if label and label not in collected_traits:
                        collected_traits.append(label)

    derived_style, derived_traits = derive_playstyle_and_traits(
        player_id=str(getattr(player, "id", "") or ""),
        full_name=full_name,
        position=getattr(player, "position", None)
        or (getattr(profile, "primary_position", None) if profile is not None else None),
        normalized_position=getattr(player, "normalized_position", None),
        preferred_foot=getattr(player, "preferred_foot", None)
        or (getattr(profile, "dominant_foot", None) if profile is not None else None),
        height_cm=getattr(player, "height_cm", None)
        or (getattr(profile, "height_cm", None) if profile is not None else None),
        gsi=getattr(player, "governed_gsi", None),
        dna=dna,
    )

    final_playstyle = playstyle or derived_style
    if len(collected_traits) < 3:
        for dt in derived_traits:
            if dt not in collected_traits:
                collected_traits.append(dt)
            if len(collected_traits) >= 5:
                break

    traits_tuple = tuple(collected_traits[:6])
    return final_playstyle, traits_tuple, traits_tuple

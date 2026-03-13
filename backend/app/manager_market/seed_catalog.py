from __future__ import annotations

from typing import Any

CATALOG_VERSION = 6

LEGENDARY_MANAGERS: list[dict[str, Any]] = [
    {"name": "Sir Alex Ferguson", "mentality": "balanced", "tactics": ["attacking_rotation", "inverted_wingers", "late_surge_press"], "traits": ["manages_elite_stars", "tactical_flexibility", "late_substitution", "loyalty_to_veterans"], "philosophy": "Relentless standards, squad evolution, and huge-game nerve.", "rarity": "legendary", "club_associations": ["Manchester United", "Aberdeen"]},
    {"name": "Arsene Wenger", "mentality": "technical", "tactics": ["tiki_taka", "technical_build_up", "youth_development_system"], "traits": ["develops_young_players", "technical_coaching", "expressive_freedom", "balanced_substitution"], "philosophy": "Elegant build-up with trust in youth and intelligent movement.", "rarity": "legendary", "club_associations": ["Arsenal", "Monaco"]},
    {"name": "Luiz Felipe Scolari", "mentality": "balanced", "tactics": ["direct_long_ball", "compact_midblock", "physical_duel_game"], "traits": ["improves_player_discipline", "boosts_physicality_focus", "defensive_organization", "quick_substitution"], "philosophy": "Tournament pragmatism with emotional steel.", "rarity": "legendary", "club_associations": ["Brazil", "Portugal"]},
    {"name": "Johan Cruyff", "mentality": "possession", "tactics": ["tiki_taka", "false_nine", "overlapping_fullbacks"], "traits": ["technical_coaching", "expressive_freedom", "academy_promotion_bias", "quick_substitution"], "philosophy": "Positional mastery and brave possession.", "rarity": "legendary", "club_associations": ["Barcelona", "Ajax"]},
    {"name": "Arrigo Sacchi", "mentality": "pressing", "tactics": ["high_press_attack", "compact_midblock", "defensive_line_control"], "traits": ["defensive_organization", "strict_structure", "tactical_flexibility", "quick_substitution"], "philosophy": "Collective pressing and structure over stardom.", "rarity": "legendary", "club_associations": ["AC Milan", "Italy"]},
    {"name": "Vicente del Bosque", "mentality": "balanced", "tactics": ["possession_control", "elite_star_freedom", "double_pivot_control"], "traits": ["manages_elite_stars", "balanced_substitution", "technical_coaching", "improves_player_discipline"], "philosophy": "Calm authority and smooth star management.", "rarity": "legendary", "club_associations": ["Spain", "Real Madrid"]},
    {"name": "Fabio Capello", "mentality": "defensive", "tactics": ["compact_midblock", "direct_long_ball", "park_the_bus"], "traits": ["defensive_organization", "strict_structure", "late_substitution", "loyalty_to_veterans"], "philosophy": "Rigid control and ruthless efficiency.", "rarity": "legendary", "club_associations": ["Milan", "Roma", "England"]},
    {"name": "Marcello Lippi", "mentality": "balanced", "tactics": ["compact_midblock", "counter_attack", "double_pivot_control"], "traits": ["manages_elite_stars", "tactical_flexibility", "balanced_substitution", "improves_player_discipline"], "philosophy": "Tournament adaptability and composed leadership.", "rarity": "legendary", "club_associations": ["Juventus", "Italy"]},
    {"name": "Rinus Michels", "mentality": "pressing", "tactics": ["high_press_attack", "tiki_taka", "false_nine"], "traits": ["tactical_flexibility", "academy_promotion_bias", "quick_substitution", "technical_coaching"], "philosophy": "Total Football with coordinated movement everywhere.", "rarity": "legendary", "club_associations": ["Ajax", "Netherlands"]},
    {"name": "Helenio Herrera", "mentality": "defensive", "tactics": ["park_the_bus", "low_block_counter", "direct_long_ball"], "traits": ["defensive_organization", "strict_structure", "late_substitution", "improves_player_discipline"], "philosophy": "Control space, strike clinically.", "rarity": "legendary", "club_associations": ["Inter", "Barcelona"]},
    {"name": "Jose Mourinho", "mentality": "pragmatic", "tactics": ["compact_midblock", "low_block_counter", "elite_star_freedom"], "traits": ["manages_elite_stars", "defensive_organization", "late_substitution", "strict_structure"], "philosophy": "Psychological edge and knockout-game control.", "rarity": "legendary", "club_associations": ["Porto", "Chelsea", "Inter", "Real Madrid"]},
    {"name": "Louis van Gaal", "mentality": "technical", "tactics": ["possession_control", "youth_development_system", "double_pivot_control"], "traits": ["develops_young_players", "strict_structure", "technical_coaching", "balanced_substitution"], "philosophy": "Shape first, talent second, timing always.", "rarity": "legendary", "club_associations": ["Ajax", "Barcelona", "Netherlands"]},
    {"name": "Ottmar Hitzfeld", "mentality": "balanced", "tactics": ["counter_attack", "compact_midblock", "wing_play"], "traits": ["manages_elite_stars", "balanced_substitution", "improves_player_discipline", "tactical_flexibility"], "philosophy": "European composure and structural calm.", "rarity": "legendary", "club_associations": ["Borussia Dortmund", "Bayern Munich"]},
    {"name": "Brian Clough", "mentality": "attacking", "tactics": ["direct_long_ball", "wing_play", "late_surge_press"], "traits": ["expressive_freedom", "manages_elite_stars", "late_substitution", "improves_player_discipline"], "philosophy": "Swagger, conviction, and brave front-foot football.", "rarity": "legendary", "club_associations": ["Nottingham Forest", "Derby County"]},
    {"name": "Kenny Dalglish", "mentality": "attacking", "tactics": ["wing_play", "elite_star_freedom", "technical_build_up"], "traits": ["manages_elite_stars", "balanced_substitution", "expressive_freedom", "loyalty_to_veterans"], "philosophy": "Classical attacking rhythm married to man-management.", "rarity": "legendary", "club_associations": ["Liverpool", "Blackburn"]},
    {"name": "Valeriy Lobanovskyi", "mentality": "pressing", "tactics": ["high_press_attack", "double_pivot_control", "compact_midblock"], "traits": ["strict_structure", "improves_player_discipline", "tactical_flexibility", "quick_substitution"], "philosophy": "Systems football with scientific intensity.", "rarity": "legendary", "club_associations": ["Dynamo Kyiv", "USSR", "Ukraine"]},
    {"name": "Nereo Rocco", "mentality": "defensive", "tactics": ["park_the_bus", "low_block_counter", "direct_long_ball"], "traits": ["defensive_organization", "late_substitution", "strict_structure", "loyalty_to_veterans"], "philosophy": "Hard edges, tight spaces, ruthless results.", "rarity": "legendary", "club_associations": ["Milan", "Padova"]},
    {"name": "Carlos Alberto Parreira", "mentality": "balanced", "tactics": ["counter_attack", "double_pivot_control", "technical_build_up"], "traits": ["improves_player_discipline", "balanced_substitution", "manages_elite_stars", "tactical_flexibility"], "philosophy": "Tournament tempo, calm authority, and efficient talent use.", "rarity": "legendary", "club_associations": ["Brazil", "Saudi Arabia", "South Africa"]},
    {"name": "Bora Milutinovic", "mentality": "pragmatic", "tactics": ["compact_midblock", "counter_attack", "set_piece_focus"], "traits": ["tactical_flexibility", "late_substitution", "improves_player_discipline", "defensive_organization"], "philosophy": "Adapt to the squad, then steal the edge.", "rarity": "legendary", "club_associations": ["Mexico", "USA", "Nigeria", "China"]},
    {"name": "Aimé Jacquet", "mentality": "balanced", "tactics": ["compact_midblock", "double_pivot_control", "technical_build_up"], "traits": ["improves_player_discipline", "balanced_substitution", "defensive_organization", "loyalty_to_veterans"], "philosophy": "Tournament solidity with patient midfield command.", "rarity": "legendary", "club_associations": ["France"]},
]

ELITE_ACTIVE_MANAGERS: list[dict[str, Any]] = [
    {"name": "Tunde Oni", "mentality": "balanced", "tactics": ["counter_attack", "technical_build_up", "set_piece_focus", "youth_development_system"], "traits": ["develops_young_players", "tactical_flexibility", "technical_coaching", "quick_substitution"], "philosophy": "A balanced Nigerian coach and great motivator built around 3-4-3, 4-1-2-1-2 diamond, and 3-4-1-2 ideas. Prefers to play through the middle with short passing combinations, then hit sharp counters against bigger teams while leaning on set-piece detail and belief in young players.", "rarity": "elite_active", "club_associations": ["Nigeria"]},
    {"name": "Pep Guardiola", "mentality": "possession", "tactics": ["tiki_taka", "inverted_wingers", "overlapping_fullbacks", "high_press_attack"], "traits": ["technical_coaching", "tactical_flexibility", "quick_substitution", "manages_elite_stars"], "philosophy": "Positional control and suffocating territory.", "rarity": "elite_active", "club_associations": ["Manchester City", "Barcelona", "Bayern Munich"]},
    {"name": "Carlo Ancelotti", "mentality": "balanced", "tactics": ["elite_star_freedom", "counter_attack", "double_pivot_control"], "traits": ["manages_elite_stars", "balanced_substitution", "tactical_flexibility", "loyalty_to_veterans"], "philosophy": "Harmony, freedom, and big-match management.", "rarity": "elite_active", "club_associations": ["Real Madrid", "Milan", "Chelsea"]},
    {"name": "Zinedine Zidane", "mentality": "balanced", "tactics": ["elite_star_freedom", "counter_attack", "overlapping_fullbacks"], "traits": ["manages_elite_stars", "balanced_substitution", "expressive_freedom", "late_substitution"], "philosophy": "Trust talent, preserve calm, hit decisive moments.", "rarity": "elite_active", "club_associations": ["Real Madrid"]},
    {"name": "Antonio Conte", "mentality": "physical", "tactics": ["wing_play", "compact_midblock", "physical_duel_game", "counter_attack"], "traits": ["boosts_physicality_focus", "strict_structure", "quick_substitution", "improves_player_discipline"], "philosophy": "Intensity, patterns, and ruthless transition play.", "rarity": "elite_active", "club_associations": ["Juventus", "Inter", "Chelsea"]},
    {"name": "Mikel Arteta", "mentality": "technical", "tactics": ["possession_control", "inverted_wingers", "high_press_attack"], "traits": ["technical_coaching", "develops_young_players", "quick_substitution", "strict_structure"], "philosophy": "Modern spacing with collective pressing and youth trust.", "rarity": "elite_active", "club_associations": ["Arsenal"]},
    {"name": "Diego Simeone", "mentality": "defensive", "tactics": ["low_block_counter", "compact_midblock", "physical_duel_game"], "traits": ["defensive_organization", "boosts_physicality_focus", "late_substitution", "improves_player_discipline"], "philosophy": "Suffering as fuel, structure as weapon.", "rarity": "elite_active", "club_associations": ["Atletico Madrid"]},
    {"name": "Xabi Alonso", "mentality": "balanced", "tactics": ["double_pivot_control", "wing_play", "high_press_attack"], "traits": ["technical_coaching", "tactical_flexibility", "develops_young_players", "balanced_substitution"], "philosophy": "Elegant control with vertical acceleration.", "rarity": "elite_active", "club_associations": ["Bayer Leverkusen"]},
    {"name": "Unai Emery", "mentality": "pragmatic", "tactics": ["compact_midblock", "counter_attack", "set_piece_focus"], "traits": ["tactical_flexibility", "quick_substitution", "defensive_organization", "improves_player_discipline"], "philosophy": "Tournament detail and opponent-specific plans.", "rarity": "elite_active", "club_associations": ["Aston Villa", "Sevilla", "Villarreal"]},
    {"name": "Thomas Tuchel", "mentality": "pressing", "tactics": ["high_press_attack", "wing_play", "double_pivot_control"], "traits": ["tactical_flexibility", "quick_substitution", "technical_coaching", "strict_structure"], "philosophy": "Pressing choreography with structural tweaks.", "rarity": "elite_active", "club_associations": ["Chelsea", "PSG", "Bayern Munich"]},
    {"name": "Jurgen Klopp", "mentality": "pressing", "tactics": ["gegenpress", "wing_play", "late_surge_press"], "traits": ["develops_young_players", "boosts_physicality_focus", "quick_substitution", "expressive_freedom"], "philosophy": "Emotion, pressure, and vertical chaos with purpose.", "rarity": "elite_active", "club_associations": ["Liverpool", "Borussia Dortmund"]},
    {"name": "Luis Enrique", "mentality": "technical", "tactics": ["tiki_taka", "high_press_attack", "technical_build_up"], "traits": ["technical_coaching", "quick_substitution", "strict_structure", "manages_elite_stars"], "philosophy": "Bold possession with sharp pressing triggers.", "rarity": "elite_active", "club_associations": ["Spain", "Barcelona", "PSG"]},
    {"name": "Luciano Spalletti", "mentality": "balanced", "tactics": ["possession_control", "wing_play", "counter_attack"], "traits": ["tactical_flexibility", "technical_coaching", "balanced_substitution", "improves_player_discipline"], "philosophy": "Fluid attacking layers anchored by structure.", "rarity": "elite_active", "club_associations": ["Napoli", "Roma", "Italy"]},
    {"name": "Julian Nagelsmann", "mentality": "pressing", "tactics": ["high_press_attack", "wing_play", "double_pivot_control", "counter_attack"], "traits": ["tactical_flexibility", "develops_young_players", "quick_substitution", "technical_coaching"], "philosophy": "Schemes that flex shape without losing intensity.", "rarity": "elite_active", "club_associations": ["Germany", "Bayern Munich", "RB Leipzig"]},
    {"name": "Hansi Flick", "mentality": "attacking", "tactics": ["high_press_attack", "counter_attack", "overlapping_fullbacks"], "traits": ["quick_substitution", "manages_elite_stars", "technical_coaching", "balanced_substitution"], "philosophy": "Fast attacks layered over assertive pressing.", "rarity": "elite_active", "club_associations": ["Germany", "Bayern Munich", "Barcelona"]},
    {"name": "Didier Deschamps", "mentality": "pragmatic", "tactics": ["compact_midblock", "counter_attack", "double_pivot_control"], "traits": ["manages_elite_stars", "late_substitution", "improves_player_discipline", "defensive_organization"], "philosophy": "Tournament realism with elite-player balance.", "rarity": "elite_active", "club_associations": ["France"]},
    {"name": "Walid Regragui", "mentality": "balanced", "tactics": ["compact_midblock", "counter_attack", "wing_play"], "traits": ["improves_player_discipline", "defensive_organization", "balanced_substitution", "boosts_physicality_focus"], "philosophy": "Togetherness, belief, and sharp transitional play.", "rarity": "elite_active", "club_associations": ["Morocco", "Wydad"]},
    {"name": "Pitso Mosimane", "mentality": "balanced", "tactics": ["high_press_attack", "counter_attack", "wing_play"], "traits": ["improves_player_discipline", "quick_substitution", "manages_elite_stars", "tactical_flexibility"], "philosophy": "Winning pragmatism fused with competitive edge.", "rarity": "elite_active", "club_associations": ["Al Ahly", "Mamelodi Sundowns"]},
    {"name": "Ange Postecoglou", "mentality": "attacking", "tactics": ["high_press_attack", "inverted_wingers", "technical_build_up"], "traits": ["expressive_freedom", "quick_substitution", "develops_young_players", "technical_coaching"], "philosophy": "All-in front-foot football with width and bravery.", "rarity": "elite_active", "club_associations": ["Tottenham Hotspur", "Celtic", "Australia"]},
    {"name": "Sarina Wiegman", "mentality": "balanced", "tactics": ["wing_play", "possession_control", "high_press_attack"], "traits": ["improves_player_discipline", "balanced_substitution", "technical_coaching", "manages_elite_stars"], "philosophy": "Tournament order with clear attacking structure.", "rarity": "elite_active", "club_associations": ["England Women", "Netherlands Women"]},
    {"name": "Emma Hayes", "mentality": "technical", "tactics": ["possession_control", "inverted_wingers", "elite_star_freedom"], "traits": ["manages_elite_stars", "develops_young_players", "quick_substitution", "tactical_flexibility"], "philosophy": "Modern competitive detail with elite squad management.", "rarity": "elite_active", "club_associations": ["Chelsea Women", "United States Women"]},
]

CURATED_GROUPS: dict[str, list[str]] = {
    "classic_global": [
        "Cesar Luis Menotti", "Carlos Bilardo", "Mario Zagallo", "Telê Santana", "Carlos Bianchi", "Héctor Cúper", "Néstor Pekerman", "Marcelo Bielsa", "Jorge Sampaoli", "Gerardo Martino", "Ricardo Gareca", "Miguel Angel Russo", "Alejandro Sabella", "Daniel Passarella", "Oscar Tabarez", "Manuel Pellegrini", "Jorge Jesus", "Abel Ferreira", "Paulo Bento", "Fernando Santos", "Sven-Goran Eriksson", "Gus Hiddink", "Dick Advocaat", "Frank Rijkaard", "Ronald Koeman", "Guus Hiddink", "Leo Beenhakker", "Mircea Lucescu", "Vahid Halilhodzic", "Berti Vogts", "Lars Lagerback", "Roberto Martinez", "Paulo Sousa", "Murat Yakin", "Niko Kovac", "Roger Schmidt", "Peter Bosz", "Martin Jol", "Valeri Karpin", "Stanislav Cherchesov", "Roberto Donadoni", "Cesare Prandelli", "Delio Rossi", "Claudio Ranieri", "Maurizio Sarri", "Massimiliano Allegri", "Stefano Pioli", "Vincenzo Italiano", "Rudi Garcia", "Paulo Fonseca", "Leonardo Jardim", "Rene Weiler", "Quique Setien", "Julen Lopetegui", "Javier Aguirre", "Miguel Herrera", "Ricardo La Volpe", "Tata Martino", "Carlos Queiroz", "Avram Grant", "Otto Addo", "Hervé Renard", "Aliou Cissé", "Djamel Belmadi", "Florent Ibenge", "Amir Abdou", "Abdelhak Benchikha", "Luc Eymael", "Milutin Sredojevic", "Rulani Mokwena", "Nasreddine Nabi", "Jose Riveiro", "Benni McCarthy", "Tom Saintfiet", "Marc Brys", "Hugo Broos", "Clemens Westerhof", "Stephen Keshi", "Sunday Oliseh", "Shuaibu Amodu", "Samson Siasia", "Christian Chukwu", "Austin Eguavoen", "Manuel Jose", "Rohr Gernot", "Aitor Karanka", "Chris Wilder", "Neil Warnock", "Alan Pardew", "Sam Allardyce", "Sean Dyche", "Roy Hodgson", "Harry Redknapp", "Steve Bruce", "Mark Hughes", "Tony Pulis", "David Moyes", "Brendan Rodgers", "Eddie Howe", "Thomas Frank", "Oliver Glasner", "Marco Rose", "Edin Terzic", "Arne Slot", "Kieran McKenna", "Vincent Kompany", "Enzo Maresca", "Fabio Cannavaro", "Andrea Pirlo", "Thierry Henry", "Patrick Vieira", "Wayne Rooney", "Frank Lampard", "Cesc Fabregas", "Xavi", "Albert Celades", "Miroslav Klose", "Ole Gunnar Solskjaer", "Albert Stuivenberg", "John Herdman", "Jesse Marsch", "Vlatko Andonovski", "Jill Ellis", "Casey Stoney", "Pia Sundhage", "Martina Voss-Tecklenburg", "Jorge Vilda", "Phil Neville"
    ],
    "africa": [
        "Moses Basena", "Milovan Rajevac", "Jalel Kadri", "Adel Amrouche", "Corentin Martins", "Faouzi Benzarti", "Badou Zaki", "Taoussi Rachid", "Lhoussain Ammouta", "Juan Carlos Garrido", "Abdelhamid Batti", "M'hamed Fakhir", "Ammar Souayah", "Nabil Maaloul", "Roger de Sa", "Ruud Krol", "Fathi Jamal", "Mokwena Rulani", "Molefi Ntseki", "Hugo Broos", "Brahim Boulami Coach", "Kamel Kolsi", "Noureddine Zekri", "Aliou Dieng Coach", "Sredojevic Micho", "Ammar Souayah", "Fawzi al-Benzarti", "Abdelhak Benchikha", "Moad Khairi Coach", "Jean-Florent Ikwange", "Mouloudia Coach Placeholder Removed", "Sébastien Desabre", "Florent Ibenge", "Hossam El Badry", "Hossam Hassan", "Shawky Gharib", "Carlos Alós", "Helmi Toulan", "Ali Maher", "Miodrag Ješić", "Brahim Fakhir", "Khaled Galal", "Nasreddine Nabi", "Josef Zinnbauer", "Pitso Mosimane", "Manqoba Mngqithi", "Mandla Ncikazi", "Abdelhak Ben Chikha", "Abdoulaye Sow", "Souleymane Camara Coach", "Kaba Diawara", "Rabah Madjer", "Djamel Belmadi", "Madjid Bougherra", "Walid Regragui", "Rachid Taoussi", "Sofiane Boufal Coach Reference Removed", "Amir Abdou", "Tom Saintfiet", "Otto Addo", "James Kwesi Appiah", "Chris Hughton", "C.K. Akonnor", "Sellas Tetteh", "Claude Le Roy", "Yusuf Chippo Coach", "Javier Clemente", "Bora Milutinovic", "Jose Peseiro", "Finidi George", "Eric Chelle", "Augustine Eguavoen", "Daniel Amokachi", "Imama Amapakabo", "Gbenga Ogunbote", "Kennedy Boboye", "Fidelis Ilechukwu", "Abia Warriors Coach", "Rene Hiddink Placeholder Removed", "Luc Eymael", "Ayman El Yamani", "Maher Kanzari", "Aliou Cisse", "Boualem Charef", "Adel Sellimi", "Hervé Renard", "Patrice Beaumelle", "Hicham Dmii", "Tom Sainfiet", "Hugo Perez"
    ],
    "europe": [
        "Roberto De Zerbi", "Erik ten Hag", "Ruben Amorim", "Nuno Espirito Santo", "Graham Potter", "Gennaro Gattuso", "Rafael Benitez", "Ralf Rangnick", "Stefan Kuntz", "Dragan Stojkovic", "Shin Tae-yong", "Park Hang-seo", "Sergio Conceicao", "Mark van Bommel", "Abel Resino", "Murat Yakin", "Steve Clarke", "Rob Page", "Vincenzo Montella", "Thiago Motta", "Francesco Farioli", "Daniele De Rossi", "Alberto Gilardino", "Ivan Juric", "Alberto Zaccheroni", "Sinisa Mihajlovic", "Walter Mazzarri", "Giampiero Gasperini", "Alessio Dionisi", "Roberto D'Aversa", "Raffaele Palladino", "Ivan Leko", "Paolo Vanoli", "Luca Gotti", "Daniele De Rossi", "Kosta Runjaic", "Christian Streich", "Bo Svensson", "Edin Terzic", "Nuri Sahin", "Sebastian Hoeness", "Domenico Tedesco", "Adi Hutter", "Gerardo Seoane", "Urs Fischer", "Rene Maric", "Marcel Koller", "Lucien Favre", "Vladimir Petkovic", "Rene Meulensteen", "Oleksandr Petrakov", "Serhiy Rebrov", "Igor Tudor", "Slaven Bilic", "Mladen Krstajic", "Ivaylo Petev", "Stanimir Stoilov", "Yugoslav Filipovic Coach", "Andriy Shevchenko", "Paulo Sousa", "Fernando Hierro", "Albert Riera", "Jose Bordalas", "Marcelino Garcia Toral", "Ruben Baraja", "Imanol Alguacil", "Mendilibar", "Aritz Lopez Garai", "Quique Sanchez Flores", "Diego Martinez", "Míchel", "Pacheta", "Luis Garcia Plaza", "Paco Lopez", "Pepe Bordalas Alias Removed", "Abelardo", "Santi Denia", "Julio Velazquez", "Joan Francesc Ferrer Rubi", "Jagoba Arrasate", "Rob Edwards", "Russell Martin", "Michael Carrick", "Kjetil Knutsen", "Brian Priske", "Kasper Hjulmand", "Stale Solbakken", "Per-Mathias Hogmo", "Janne Andersson", "Tomasson", "Kasper Schmeichel Coach Removed", "Heimir Hallgrimsson", "Olof Mellberg", "Mikael Stahre"
    ],
    "americas": [
        "Fernando Diniz", "Dorival Junior", "Tite", "Renato Gaucho", "Mano Menezes", "Dunga", "Abel Braga", "Vanderlei Luxemburgo", "Roger Machado", "Cuca", "Dorival Silvestre Júnior", "Rogerio Ceni", "Felipao", "Tiago Nunes", "Vojvoda", "Gustavo Quinteros", "Diego Cocca", "Matias Almeyda", "Guillermo Barros Schelotto", "Ricardo Ferretti", "Antonio Mohamed", "Ignacio Ambriz", "Diego Alonso", "Marcelo Gallardo", "Martin Demichelis", "Hernan Crespo", "Eduardo Berizzo", "Gustavo Alfaro", "Diego Aguirre", "Jorge Fossati", "Alexander Medina", "Paulo Autuori", "Beccacece", "Reinaldo Rueda", "Luis Fernando Suarez", "Juan Carlos Osorio", "Rene Simoes", "Alexi Stival", "Fabián Coito", "Cesar Farías", "Noel Sanvicente", "Rafael Dudamel", "Alfio Basile", "Ariel Holan", "Gabriel Milito", "Pedro Caixinha", "Gustavo Costas", "Martin Lasarte", "Juan Antonio Pizzi", "Diego Cocca", "Juan Reynoso", "Jaime Lozano", "Ricardo Cadena", "Jorge Almiron", "Gerardo Espinoza", "Hernan Dario Gomez", "Bolillo Gomez", "Thomas Christiansen", "Luis Fernando Tena", "Jorge Luis Pinto", "Hernan Medford", "Alexandre Guimaraes", "Paulo Wanchope", "Julio Cesar Dely Valdes", "Tata Brown Coach Removed", "Bob Bradley", "Gregg Berhalter", "Bruce Arena", "Tab Ramos", "Steve Sampson", "B.J. Callaghan", "Mikey Varas", "Jim Curtin", "Wilfried Nancy", "Pat Noonan", "Oscar Pareja", "Nico Estevez", "Peter Vermes", "Caleb Porter", "Robin Fraser", "Pablo Mastroeni", "Hernan Losada", "Tyrone Mears Coach Removed", "Dean Smith", "Jesse Marsch", "John Herdman", "Tata Martino", "Wilfried Nancy", "Troy Lesesne", "Frank Klopas", "Sigi Schmid", "Dominic Kinnear"
    ],
    "asia_oceania": [
        "Graham Arnold", "Tony Popovic", "Kevin Muscat", "John Aloisi", "Ufuk Talay", "Carl Veart", "Mark Rudan", "Arthur Papas", "Ange Postecoglou", "Arnold Australia Duplicate Removed", "Akira Nishino", "Hajime Moriyasu", "Go Oiwa", "Toru Oniki", "Massimo Ficcadenti", "Tsutomu Ogura", "Yahya Al-Shehri Coach Removed", "Vissel Kobe Coach Placeholder Removed", "Lee Kang-in Coach Removed", "Hong Myung-bo", "Kim Hak-bum", "Paulo Bento", "Shin Tae-yong", "Park Hang-seo", "Alexandre Gama", "Milorad Kosanovic", "Srecko Katanec", "Bahlul Mustafazade Coach Removed", "Juan Antonio Pizzi", "Bert van Marwijk", "Roberto Mancini", "Hector Cuper", "Juan Carlos Osorio", "Pizzi Middle East Duplicate Removed", "Cosmin Olaroiu", "Razvan Lucescu", "Milos Milojevic", "Vuk Rasovic", "Ramón Diaz", "Jorge Jesus", "Leonardo Jardim", "Hernan Crespo", "Odair Hellmann", "Micael Sequeira Coach", "Zlatko Dalic Asia Removed", "Branko Ivankovic", "Aleksandar Jankovic", "Aleksandar Stanojevic", "Kim Pan-gon", "Choi Kang-hee", "Kim Do-hoon", "Boev Katanec Alias Removed", "Hassan Shehata", "Mahmoud El-Gohary", "Berti Vogts", "Carlos Queiroz", "Milos Milutinovic", "Srecko Katanec", "Javad Nekounam", "Amir Ghalenoei"
    ],
    "women": [
        "Casey Stoney", "Jill Ellis", "Pia Sundhage", "Corinne Diacre", "Phil Neville", "Mark Parsons", "Tony Gustavsson", "Desiree Ellis", "Randy Waldrum", "Reynald Pedros", "Jonatan Giraldez", "Pere Romeu", "Sonia Bompastor", "Joe Montemurro", "Peter Gerhardsson", "Tom Sermanni", "Beverly Priestman", "Nils Nielsen", "Kenneth Heiner-Moller", "Hope Powell", "Hege Riise", "Laura Harvey", "Emma Coates", "Natalia Arroyo", "Montse Tome", "Stefanie van der Gragt Coach Removed", "Helle Thomsen Coach Removed", "Gemma Grainger", "Lorne Donaldson", "Shilene Booysen", "Jerry Tshabalala", "Tinja-Riikka Korpela Coach Removed", "Rhian Wilkinson", "Gareth Taylor", "Mickael Ferreira Coach Removed", "Cindy Parlow Cone", "Sabrina Viguier", "Maren Meinert", "Tommy Stroot", "Seb Hines", "Jonas Eidevall"
    ]
}


EXTRA_CURATED_GROUPS = {
    "africa_expanded": [
        "Florent Ibenge", "Abdelhak Benchikha", "Rhulani Mokwena", "Jose Gomes", "Mladen Krstajic", "Ammar Souayah",
        "Nabil Maaloul", "Faouzi Benzarti", "Lassaad Dridi", "Mouine Chaabani", "Rui Vitoria", "Sven Vandenbroeck",
        "Pape Thiaw", "Tom Saintfiet", "Yamen Zelfani", "Khaled Ben Yahia", "Miguel Gamondi", "Alexandre Santos",
        "Milovan Rajevac", "Chris Hughton", "Otto Addo", "Kwesi Appiah", "Ibrahim Tanko", "Sellas Tetteh",
        "Tarik Sektioui", "Badou Zaki", "Vahid Halilhodzic", "Djamel Belmadi", "Madjid Bougherra", "Amir Abdou",
        "Raul Savoy", "Sebastien Desabre", "Lamine N'Diaye", "Kaba Diawara", "Paulo Duarte", "Hugo Broos",
        "Carlos Queiroz", "Jalel Kadri", "Walid Regragui", "Pitso Mosimane", "Fadlu Davids", "Benni McCarthy",
        "Roger de Sa", "Gavin Hunt", "Manqoba Mngqithi", "Eric Tinkler", "Steve Komphela", "Mandla Ncikazi",
        "John Maduka", "Kaitano Tembo", "Kinnah Phiri"
    ],
    "europe_expanded": [
        "Arne Slot", "Eddie Howe", "Andoni Iraola", "Thomas Frank", "Marco Silva", "Unai Emery", "Enzo Maresca",
        "Mauricio Pochettino", "Julen Lopetegui", "Sean Dyche", "David Moyes", "Brendan Rodgers", "Oliver Glasner",
        "Kieran McKenna", "Daniel Farke", "Carlos Corberan", "Ryan Mason", "Paulo Fonseca", "Bruno Genesio",
        "Christophe Galtier", "Didier Deschamps", "Luis Enrique", "Julian Nagelsmann", "Xabi Alonso", "Vincent Kompany",
        "Thomas Tuchel", "Peter Bosz", "Roger Schmidt", "Matthias Jaissle", "Adi Hutter", "Marcelino",
        "Ernesto Valverde", "Xavi Hernandez", "Claudio Ranieri", "Roberto Mancini", "Luciano Spalletti", "Stefano Pioli",
        "Maurizio Sarri", "Massimiliano Allegri", "Simone Inzaghi", "Fabio Grosso", "Andrea Pirlo", "Ruben Amorim",
        "Murat Yakin", "Vladimir Ivic", "Slaven Bilic", "Domenico Tedesco", "Sebastian Hoeness", "Edin Terzic",
        "Nuri Sahin", "Kjetil Knutsen", "Stale Solbakken", "Jesse Marsch", "Steve Cooper", "Lee Carsley",
        "Gareth Southgate", "Michael O'Neill", "Neil Lennon", "Aitor Karanka", "Miroslav Klose", "Ole Gunnar Solskjaer",
        "Rene Maric", "Thorsten Fink", "Dieter Hecking", "Friedhelm Funkel", "Bruno Labbadia", "Pellegrino Matarazzo"
    ],
    "americas_expanded": [
        "Fernando Batista", "Lionel Scaloni", "Marcelo Bielsa", "Nestor Lorenzo", "Daniel Garnero", "Ricardo Gareca",
        "Ramon Menezes", "Thiago Carpini", "Juan Pablo Vojvoda", "Martin Anselmi", "Luis Zubeldia", "Pedro Caixinha",
        "Eduardo Dominguez", "Martin Demichelis", "Sebastian Beccacece", "Jorge Sampaoli", "Ricardo Zielinski", "Miguel Angel Ramirez",
        "Guillermo Almada", "Fernando Ortiz", "Nicolas Larcamon", "Andre Jardine", "Martin Palermo", "Gregg Berhalter",
        "Jim Curtin", "Wilfried Nancy", "Pat Noonan", "Oscar Pareja", "Robin Fraser", "Pablo Mastroeni",
        "Dean Smith", "John Herdman", "Bradley Carnell", "Sandro Schwarz", "Frank Klopas", "Caleb Porter",
        "Peter Vermes", "Vanni Sartini", "Luchi Gonzalez", "Adrian Heath", "Bruce Arena", "Bob Bradley",
        "Pablo Repetto", "Alexander Medina", "Jorge Fossati", "Paulo Pezzolano", "Alvaro Gutierrez", "Javier Aguirre",
        "Robert Dante Siboldi", "Gustavo Alfaro", "Cesar Farias", "Rafael Dudamel"
    ],
    "asia_oceania_expanded": [
        "Tony Popovic", "Kevin Muscat", "John Aloisi", "Arthur Papas", "Carl Veart", "Ante Milicic",
        "Hajime Moriyasu", "Go Oiwa", "Toru Oniki", "Yoshida Tatsuma", "Michael Skibbe", "Maciej Skorza",
        "Kim Pan-gon", "Hong Myung-bo", "Kim Hak-bum", "Branko Ivankovic", "Aleksandar Jankovic", "Javad Nekounam",
        "Amir Ghalenoei", "Cosmin Olaroiu", "Razvan Lucescu", "Milos Milojevic", "Vuk Rasovic", "Ayman El Ramadi",
        "Abdelaziz Al Anbari", "Bert van Marwijk", "Akira Nishino", "Milorad Kosanovic", "Srecko Katanec", "Kim Do-hoon",
        "Choi Kang-hee", "Juan Ferrando", "Xisco Munoz", "Miroslav Soukup", "Dragan Talajic", "Nasser Larguet"
    ],
    "women_expanded": [
        "Emma Hayes", "Sarina Wiegman", "Desiree Ellis", "Randy Waldrum", "Jill Ellis", "Pia Sundhage",
        "Laura Harvey", "Casey Stoney", "Sonia Bompastor", "Jonatan Giraldez", "Joe Montemurro", "Peter Gerhardsson",
        "Beverly Priestman", "Hege Riise", "Rhian Wilkinson", "Hope Powell", "Gemma Grainger", "Lorne Donaldson",
        "Natalia Arroyo", "Montse Tome", "Nils Nielsen", "Kenneth Heiner-Moller", "Tom Sermanni", "Tony Gustavsson",
        "Mark Parsons", "Carla Ward", "Gareth Taylor", "Seb Hines", "Tommy Stroot", "Reynald Pedros",
        "Shilene Booysen", "Jerry Tshabalala", "Ariane Hingst", "Wouter Vinke", "Roberto Martinez", "Thiago Motta", "Francesco Farioli", "Michel", "Imanol Alguacil", "Abel Ferreira", "Fernando Diniz", "Dorival Junior", "Thierry Henry", "Herve Renard", "Aliou Cisse", "Rigobert Song", "Mamadou Diallo", "Franck Haise", "Ralf Rangnick", "Rob Edwards", "Graham Potter", "Ange Postecoglou"
    ]
}

RARITY_EXCEPTIONS = {
    "Jose Mourinho": "legendary",
    "Louis van Gaal": "legendary",
    "Ottmar Hitzfeld": "legendary",
    "Sarina Wiegman": "elite_active",
    "Emma Hayes": "elite_active",
    "Pitso Mosimane": "elite_active",
    "Walid Regragui": "elite_active",
    "Ange Postecoglou": "elite_active",
}

MENTALITIES = ["balanced", "attacking", "defensive", "technical", "pragmatic", "pressing", "possession", "physical"]
TACTIC_SETS = [
    ["counter_attack", "compact_midblock"],
    ["wing_play", "direct_long_ball"],
    ["possession_control", "technical_build_up"],
    ["high_press_attack", "inverted_wingers"],
    ["youth_development_system", "double_pivot_control"],
    ["low_block_counter", "set_piece_focus"],
    ["gegenpress", "overlapping_fullbacks"],
    ["elite_star_freedom", "technical_build_up"],
]
TRAIT_SETS = [
    ["tactical_flexibility", "balanced_substitution", "improves_player_discipline", "develops_young_players"],
    ["defensive_organization", "late_substitution", "boosts_physicality_focus", "strict_structure"],
    ["technical_coaching", "manages_elite_stars", "expressive_freedom", "quick_substitution"],
    ["academy_promotion_bias", "balanced_substitution", "technical_coaching", "tactical_flexibility"],
]


def supply_for_rarity(rarity: str) -> int:
    if rarity == "legendary":
        return 2
    if rarity == "elite_active":
        return 3
    return 10


def _normalize(name: str) -> str:
    return " ".join(name.replace("  ", " ").strip().split())


def _slug(name: str) -> str:
    slug = name.lower()
    for old, new in (("'", ""), ("’", ""), ("é", "e"), ("è", "e"), ("á", "a"), ("à", "a"), ("ó", "o"), ("ò", "o"), ("í", "i"), ("ì", "i"), ("ú", "u"), ("ù", "u"), ("ç", "c"), ("ñ", "n"), ("ö", "o"), ("ü", "u"), ("ä", "a"), ("ø", "o"), ("ß", "ss"), ("-", " ")):
        slug = slug.replace(old, new)
    return "-".join(_normalize(slug).split())


def _dedupe_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    clean: list[str] = []
    for raw in names:
        name = _normalize(raw)
        lowered = name.lower()
        if not name or lowered in seen or "removed" in lowered or "placeholder" in lowered or "alias" in lowered or "duplicate" in lowered or lowered.endswith(" coach") or " coach " in lowered:
            continue
        seen.add(lowered)
        clean.append(name)
    return clean


def build_seed_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def add_record(record: dict[str, Any]) -> None:
        manager_id = _slug(record["name"])
        if manager_id in seen_ids:
            return
        seen_ids.add(manager_id)
        rarity = record.get("rarity", "popular")
        record = dict(record)
        record["rarity"] = rarity
        record["supply_total"] = record.get("supply_total", supply_for_rarity(rarity))
        catalog.append(record)

    for item in LEGENDARY_MANAGERS + ELITE_ACTIVE_MANAGERS:
        add_record(item)

    grouped_names: list[str] = []
    for names in CURATED_GROUPS.values():
        grouped_names.extend(_dedupe_names(names))
    for names in EXTRA_CURATED_GROUPS.values():
        grouped_names.extend(_dedupe_names(names))

    for index, name in enumerate(grouped_names):
        rarity = RARITY_EXCEPTIONS.get(name, "popular")
        mentality = MENTALITIES[index % len(MENTALITIES)]
        tactics = list(TACTIC_SETS[index % len(TACTIC_SETS)])
        if index % 3 == 0:
            tactics.append("counter_attack")
        elif index % 3 == 1:
            tactics.append("wing_play")
        else:
            tactics.append("compact_midblock")
        traits = list(TRAIT_SETS[index % len(TRAIT_SETS)])
        club_associations = []
        add_record(
            {
                "name": name,
                "mentality": mentality,
                "tactics": tactics[:4],
                "traits": traits[:4],
                "philosophy": f"{name} brings a recognizable touchline identity shaped around {mentality} football.",
                "rarity": rarity,
                "club_associations": club_associations,
            }
        )

    return catalog

"""Set fair legend peaks where the stored number is clearly off.

98 stays with Pelé, Maradona, Cristiano Ronaldo, and Messi. 96 stays with
the tier-2 pantheon. 90 and above is reserved for players who were among the
best in the world. Every legend stays at 80 or higher. Share counts are left
alone. Price follows the existing legend curve.

Revision ID: 20261113_0241_legend_fair_peaks
Revises: 20261113_0240_more_country_and_position_fixes
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261113_0241_legend_fair_peaks"
down_revision = "20261113_0240_more_country_and_position_fixes"
branch_labels = None
depends_on = None

# full_name, current peak, fair peak. Matched only when exactly one legend has that name and peak.
PEAKS = (
    ("Andoni Zubizarreta", 94, 87),
    ("Eiður Smári Guðjohnsen", 94, 86),
    ("Espen Johnsen", 94, 81),
    ("Germán Burgos", 94, 82),
    ("Gonzalo Higuaín", 94, 88),
    ("Goran Pandev", 94, 85),
    ("Jan Koller", 94, 86),
    ("Jon Dahl Tomasson", 94, 85),
    ("Manuel Amoros", 94, 86),
    ("Marco Amelia", 94, 82),
    ("Paul Scholes", 94, 92),
    ("Philipp Lahm", 94, 92),
    ("Robert Prosinecki", 94, 88),
    ("Tim Flowers", 94, 82),
    ("Xabi Alonso", 94, 91),
    ("Damien Duff", 93, 86),
    ("Daniel Carvalho", 93, 84),
    ("Darko Kovacevic", 93, 84),
    ("Ed de Goey", 93, 84),
    ("Francesco Antonioli", 93, 82),
    ("Frank Rost", 93, 83),
    ("Giovanni", 93, 87),
    ("Jerzy Dudek", 93, 84),
    ("Joe Cole", 93, 86),
    ("Jose Antonio Reyes", 93, 86),
    ("Mauro Silva", 93, 87),
    ("Míchel Salgado", 93, 86),
    ("Miguel Ángel Nadal", 93, 85),
    ("Nicolas Anelka", 93, 88),
    ("Paulo Nunes", 93, 82),
    ("Roberto Dinamita", 93, 86),
    ("Roque Santa Cruz", 93, 84),
    ("Santiago Cañizares", 93, 86),
    ("Sebastiano Rossi", 93, 83),
    ("Sergi Barjuán", 93, 85),
    ("Stipe Pletikosa", 93, 84),
    ("Uli Stein", 93, 84),
    ("Fernando Morientes", 93, 87),
    ("Andreas Brehme", 93, 88),
    ("Fernando Torres", 93, 91),
    ("Eden Hazard", 93, 91),
    ("Antoine Griezmann", 93, 90),
    ("Wesley Sneijder", 93, 91),
    ("Michael Owen", 93, 90),
    ("Diego Forlán", 93, 90),
    ("Jari Litmanen", 93, 90),
    ("Jürgen Kohler", 93, 89),
    ("Javier Mascherano", 93, 88),
    ("Brian Laudrup", 93, 90),
    ("Rudi Völler", 93, 88),
    ("Roger Milla", 93, 91),
    ("Taffarel", 93, 89),
    ("Fabien Barthez", 93, 89),
    ("Kenny Dalglish", 93, 95),
    ("Carlos Tevez", 92, 90),
    ("Paulo Dybala", 92, 88),
    ("Robin van Persie", 92, 90),
    ("John Terry", 92, 89),
    ("Jamie Carragher", 92, 86),
    ("Roberto Mancini", 92, 88),
    ("Giuseppe Signori", 92, 87),
    ("Ian Rush", 92, 90),
    ("John Barnes", 92, 89),
    ("Leonardo", 92, 88),
    ("Marcelo Gallardo", 92, 86),
    ("Mauro Tassotti", 92, 88),
    ("Roberto Donadoni", 92, 87),
    ("Roberto Sensini", 92, 86),
    ("Walter Zenga", 92, 88),
    ("Dida", 92, 88),
    ("Rogério Ceni", 92, 88),
    ("Guti", 92, 86),
    ("Juan Carlos Valerón", 92, 86),
    ("Juan Mata", 92, 87),
    ("Andrey Arshavin", 92, 86),
    ("Antonio Cassano", 92, 87),
    ("Diego Milito", 92, 88),
    ("Frédéric Kanouté", 92, 86),
    ("Gustavo Poyet", 92, 85),
    ("Mirko Vucinic", 92, 85),
    ("Paolo Di Canio", 92, 86),
    ("Rodrigo Palacio", 92, 85),
    ("Sami Hyypiä", 92, 87),
    ("Sergen Yalçin", 92, 85),
    ("Teddy Sheringham", 92, 87),
    ("Willy Sagnol", 92, 86),
    ("Attilio Lombardo", 92, 85),
    ("Frank Arnesen", 92, 84),
    ("Francesco Flachi", 92, 83),
    ("Fran Yeste", 92, 83),
    ("Guillermo Barros Schelotto", 92, 86),
    ("Jérôme Rothen", 92, 84),
    ("Kléberson", 92, 84),
    ("Lee Bowyer", 92, 82),
    ("Andrew Johnson", 92, 83),
    ("Anghel Iordanescu", 92, 84),
    ("Brad Guzan", 92, 82),
    ("Chris Kirkland", 92, 81),
    ("Fernando Gamboa", 92, 81),
    ("Jan Oblak", 92, 90),
    ("Jonathan Woodgate", 92, 83),
    ("Leo Franco", 92, 82),
    ("Oscar Cordoba", 92, 86),
    ("Pablo Ibáñez", 92, 83),
    ("Per Krøldrup", 92, 81),
    ("Ricardo Bocchini", 92, 80),
    ("Tarik Oulida", 92, 81),
    ("Tomáš Repka", 92, 83),
    ("Grégory Coupet", 92, 87),
    ("Bülent Korkmaz", 91, 84),
    ("Craig Bellamy", 91, 84),
    ("Diego Tristán", 91, 84),
    ("Fernando Cavenaghi", 91, 84),
    ("Florent Malouda", 91, 86),
    ("Gordon Strachan", 91, 84),
    ("Jardel", 91, 86),
    ("Jean Vladoiu", 91, 82),
    ("Jonathan Zebina", 91, 83),
    ("José Molina", 91, 83),
    ("Karl-Heinz Förster", 91, 86),
    ("Kily González", 91, 85),
    ("Luca Bucci", 91, 82),
    ("Mamadou Niang", 91, 84),
    ("Marinko Galic", 91, 82),
    ("Mickaël Landreau", 91, 84),
    ("Mohamed Zidan", 91, 84),
    ("Moreno Torricelli", 91, 84),
    ("Stefan Klos", 91, 84),
    ("Sylvain Wiltord", 91, 86),
    ("Tuncay Sanli", 91, 84),
    ("Valdo", 91, 86),
    ("Volodymyr Bessonov", 91, 85),
    ("Volodymyr Sharan", 91, 82),
    ("Zetti", 91, 84),
    ("Claudio López", 91, 86),
    ("Christian Wörns", 91, 85),
    ("Pepe Reina", 91, 87),
    ("Víctor Valdés", 91, 88),
    ("David De Gea", 91, 89),
    ("Philippe Coutinho", 91, 87),
    ("David Ginola", 91, 87),
    ("Marcelo", 91, 88),
    ("Mehmet Scholl", 91, 88),
    ("Paco Buyo", 91, 87),
    ("Rüstü Reçber", 91, 86),
    ("Zvonimir Boban", 91, 89),
    ("Angelo Peruzzi", 91, 88),
    ("Pep Guardiola", 90, 88),
    ("Romelu Lukaku", 90, 88),
    ("Santi Cazorla", 90, 88),
    ("Shinji Kagawa", 90, 86),
    ("Tony Yeboah", 90, 86),
    ("Mats Hummels", 90, 88),
    ("Paul Pogba", 90, 88),
    ("Olivier Giroud", 90, 86),
    ("Luca Toni", 90, 87),
    ("Oliver Bierhoff", 90, 86),
    ("Predrag Mijatovic", 90, 87),
    ("Karel Poborský", 90, 86),
    ("Harry Kewell", 90, 86),
    ("Dejan Stankovic", 90, 87),
    ("Elano", 90, 85),
    ("Emre Belözoglu", 90, 86),
    ("Eric Abidal", 90, 86),
    ("Juninho Paulista", 90, 88),
    ("Jorge Burruchaga", 90, 86),
    ("Marcos Senna", 90, 86),
    ("Noureddine Naybet", 90, 86),
    ("Paolo Montero", 90, 87),
    ("Roberto Ayala", 90, 89),
    ("Gianluca Pagliuca", 90, 87),
    ("Bodo Illgner", 90, 88),
    ("Marcos", 90, 87),
    ("Aimo Diana", 90, 82),
    ("Albert Ferrer", 90, 85),
    ("Albert Luque", 90, 83),
    ("Alberto Aquilani", 90, 84),
    ("Alex Teixeira", 90, 84),
    ("Amadeo Carrizo", 90, 88),
    ("Amauri", 90, 83),
    ("Andrés Palop", 90, 83),
    ("Antonio Prats", 90, 81),
    ("Bojan Krkic", 90, 84),
    ("Brian McBride", 90, 84),
    ("Christian Abbiati", 90, 84),
    ("Colin Hendry", 90, 84),
    ("Danny", 90, 85),
    ("Djalminha", 90, 87),
    ("Dumitru Stângaciu", 90, 81),
    ("Eduardo", 90, 86),
    ("Fabian Ernst", 90, 83),
    ("Federico Marchetti", 90, 83),
    ("Flavio Roma", 90, 82),
    ("Fran", 90, 85),
    ("Graeme Le Saux", 90, 84),
    ("Graeme Sharp", 90, 84),
    ("Gustavo López", 90, 85),
    ("Ismael Urzaiz", 90, 84),
    ("Ivan Klasnic", 90, 84),
    ("Javier Chevantón", 90, 84),
    ("Jean-Alain Boumsong", 90, 82),
    ("Joachim Björklund", 90, 83),
    ("João Pinto", 90, 86),
    ("Jocelyn Angloma", 90, 85),
    ("Johan Elmander", 90, 84),
    ("Joseba Etxeberria", 90, 85),
    ("Juan Fernando Arango", 90, 85),
    ("Jussi Jääskeläinen", 90, 84),
    ("Karl-Heinz Riedle", 90, 85),
    ("Krisztián Lisztes", 90, 83),
    ("László Bölöni", 90, 84),
    ("Leovegildo Júnior", 90, 89),
    ("Ludovic Giuly", 90, 85),
    ("Marco Marchionni", 90, 83),
    ("Marco Simone", 90, 85),
    ("Marius Lacatus", 90, 85),
    ("Mateja Kežman", 90, 84),
    ("Oleksandr Shovkovskyi", 90, 85),
    ("Oliver Neuville", 90, 84),
    ("Pablo Aimar", 90, 88),
    ("Paolo Negro", 90, 83),
    ("Phil Neville", 90, 82),
    ("Richardo Rocha", 90, 86),
    ("Robert Kovac", 90, 84),
    ("Roberto Abbondanzieri", 90, 84),
    ("Rubén Baraja", 90, 86),
    ("Victor Onopko", 90, 84),
    ("Victor Piturca", 90, 82),
    ("Viktor Leonenko", 90, 82),
    ("Vincent Candela", 90, 85),
    ("Yury Nikiforov", 90, 84),
    ("Emmanuel Petit", 90, 87),
    ("Giovane Élber", 90, 86),
    ("Alan Shearer", 90, 92),
    ("Gabriel Batistuta", 90, 93),
    ("Juan Román Riquelme", 90, 93),
    ("Manuel Neuer", 90, 93),
    ("Michael Laudrup", 90, 93),
    ("Sergio Ramos", 90, 92),
    ("Aldo Duscher", 89, 81),
    ("Alessandro Gamberini", 89, 82),
    ("Alessandro Melli", 89, 83),
    ("Alessio Tacchinardi", 89, 83),
    ("Artur Boruc", 89, 84),
    ("Benoît Pedretti", 89, 82),
    ("Carlo Ancelotti", 89, 85),
    ("Carlos Kameni", 89, 83),
    ("Christian Poulsen", 89, 84),
    ("Cristiano Doni", 89, 83),
    ("Curro Torres", 89, 82),
    ("Danny Mills", 89, 82),
    ("Gary O'Neil", 89, 81),
    ("Gerald Asamoah", 89, 82),
    ("Gustavo Munúa", 89, 82),
    ("Hans Jörg Butt", 89, 83),
    ("Joe Hart", 89, 85),
    ("Jörg Heinrich", 89, 83),
    ("Julio Cruz", 89, 83),
    ("Kevin Gameiro", 89, 84),
    ("Lukáš Železník", 89, 80),
    ("Mark Pembridge", 89, 82),
    ("Mason Greenwood", 89, 84),
    ("Niko Kranjcar", 89, 84),
    ("Peter Crouch", 89, 84),
    ("Rubén Olivera", 89, 83),
    ("Sébastien Squillaci", 89, 82),
    ("Stefano Fiore", 89, 84),
    ("Stéphane Henchoz", 89, 83),
    ("Tomáš Ujfaluši", 89, 84),
    ("Vágner Love", 89, 85),
    ("Adrian Ilie", 89, 86),
    ("Aldo Serena", 89, 84),
    ("Ali Karimi", 89, 86),
    ("Andrew Cole", 89, 87),
    ("Ariel Ortega", 89, 87),
    ("Christian Vieri", 89, 90),
    ("Daniel Van Buyten", 89, 85),
    ("Daniele De Rossi", 89, 88),
    ("David Albelda", 89, 85),
    ("Dejan Savicevic", 89, 90),
    ("Denis Irwin", 89, 87),
    ("Ebbe Sand", 89, 85),
    ("Eric Gerets", 89, 87),
    ("Esteban Cambiasso", 89, 87),
    ("Fernando Couto", 89, 86),
    ("Filippo Inzaghi", 89, 88),
    ("Franco Tancredi", 89, 84),
    ("Gianluca Vialli", 89, 88),
    ("Henrik Larsson", 89, 88),
    ("Jacques Songo'o", 89, 83),
    ("Jay-Jay Okocha", 89, 90),
    ("Jérôme Boateng", 89, 87),
    ("Juan", 89, 86),
    ("Leighton Baines", 89, 86),
    ("Mario Götze", 89, 86),
    ("Nicolás Otamendi", 89, 86),
    ("Nihat Kahveci", 89, 85),
    ("Nwankwo Kanu", 89, 88),
    ("Olof Mellberg", 89, 85),
    ("Phillip Cocu", 89, 87),
    ("Rashidi Yekini", 89, 86),
    ("Ricardo", 89, 86),
    ("Roberto Dinamite", 89, 86),
    ("Ronald de Boer", 89, 86),
    ("Sébastien Frey", 89, 85),
    ("Simão Sabrosa", 89, 86),
    ("Stefan Effenberg", 89, 88),
    ("Thomas Sorensen", 89, 84),
    ("Tomáš Rosický", 89, 87),
    ("Trevor Francis", 89, 86),
    ("Vincenzo Montella", 89, 85),
    ("Vítor Baía", 89, 87),
    ("Vyacheslav Malafeev", 89, 84),
    ("Bastian Schweinsteiger", 89, 90),
    ("Lilian Thuram", 89, 91),
    ("Marc Overmars", 89, 88),
    ("Peter Shilton", 89, 90),
    ("Rinat Dasayev", 89, 91),
    ("Toninho Cerezo", 89, 88),
    ("Abedi Pelé", 85, 90),
    ("Finidi George", 88, 86),
    ("Sadio Mané", 86, 89),
)


def _resolve(conn) -> list[tuple[str, int]]:
    seen: set[tuple[str, int]] = set()
    problems: list[str] = []
    resolved: list[tuple[str, int]] = []
    for name, old, new in PEAKS:
        if (name, old) in seen:
            problems.append(f"duplicate {name} {old}")
        seen.add((name, old))
        if new < 80 or new > 96:
            problems.append(f"{name} peak {new} outside 80-96")
        rows = conn.execute(
            sa.text(
                """
                SELECT id::text
                FROM ingestion_players
                WHERE full_name = :name
                  AND governed_gsi = :old
                  AND real_player_tier = 'legend'
                """
            ),
            {"name": name, "old": old},
        ).fetchall()
        if len(rows) != 1:
            problems.append(f"{name} @ {old} matched {len(rows)}")
            continue
        resolved.append((rows[0][0], new))
    if problems:
        raise RuntimeError("; ".join(problems[:40]))
    return resolved


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    resolved = _resolve(conn)
    values = ", ".join(f"('{player_id}'::text, {gsi}::int)" for player_id, gsi in resolved)
    conn.execute(
        sa.text(
            f"""
            UPDATE ingestion_players AS ip
            SET governed_gsi = v.gsi,
                governed_potential_gsi = v.gsi,
                potential = v.gsi,
                gsi_override_reason = 'governed_legend_fair_peak_2026_11_13',
                dna_profile = jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(COALESCE(ip.dna_profile::jsonb, '{{}}'::jsonb), '{{overall}}', to_jsonb(v.gsi)),
                            '{{current_rating}}', to_jsonb(v.gsi)
                        ),
                        '{{potential}}', to_jsonb(v.gsi)
                    ),
                    '{{potential_rating}}', to_jsonb(v.gsi)
                )::json,
                updated_at = NOW()
            FROM (VALUES {values}) AS v(id, gsi)
            WHERE ip.id = v.id
            """
        )
    )
    conn.execute(
        sa.text(
            f"""
            UPDATE legendary_player_profiles AS lp
            SET governed_gsi = v.gsi,
                governed_potential_gsi = v.gsi,
                updated_at = NOW()
            FROM ingestion_players AS ip
            JOIN (VALUES {values}) AS v(id, gsi) ON ip.id = v.id
            WHERE ip.legendary_profile_id = lp.id
            """
        )
    )
    conn.execute(
        sa.text(
            f"""
            UPDATE player_share_markets AS m
            SET share_price_coin = ROUND(250.0 * POWER(v.gsi / 90.0, 3.2) * 3.6, 2),
                updated_at = NOW()
            FROM (VALUES {values}) AS v(id, gsi)
            WHERE m.player_id = v.id
            """
        )
    )
    conn.execute(
        sa.text(
            f"""
            UPDATE player_summary_read_models AS rm
            SET summary_json = (
                    COALESCE(rm.summary_json::jsonb, '{{}}'::jsonb)
                    || jsonb_build_object(
                        'gsi', v.gsi,
                        'overall', v.gsi,
                        'global_scouting_index', v.gsi,
                        'potential', v.gsi,
                        'share_price_coin', ROUND(250.0 * POWER(v.gsi / 90.0, 3.2) * 3.6, 2)
                    )
                )::json,
                average_rating = v.gsi::float8,
                current_value_credits = ROUND(250.0 * POWER(v.gsi / 90.0, 3.2) * 3.6, 2)::float8,
                updated_at = NOW()
            FROM (VALUES {values}) AS v(id, gsi)
            WHERE rm.player_id = v.id
            """
        )
    )


def downgrade() -> None:
    pass

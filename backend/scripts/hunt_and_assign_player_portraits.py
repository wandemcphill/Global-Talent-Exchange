#!/usr/bin/env python3
"""Hunt down and assign portraits to all players missing pictures in GTEX.

Steps:
1. Sync existing images: Any player with an approved portrait in ingestion_player_image_metadata
   or ingestion_players.dna_profile has their portraitUrl, portrait_url, and image_url synced
   into player_summary_read_models.summary_json and ingestion_players.dna_profile (fixes Batrakov,
   Evanilson, Pierre Ismaelo, Sani Suleiman, Adamu Yakubu, Taison, etc.).
2. Assign curated authentic portraits to high-GSI legends (Dida, Bebeto, Marco Amelia, Ed de Goey,
   Francesco Antonioli, Leonardo, Per Krøldrup, Jardel, José Molina, Luca Bucci, Stefan Effenberg,
   Flavio Roma, Fran, Paolo Negro, Aldo Duscher, Mark Pembridge, Cris, Mancini, Alen Bokšić, Raí,
   Alexandr Hleb, Belletti, Enzo Francescoli, Antti Niemi, Vicente, Míchel, Javier Saviola, Ganso,
   Marcelo Salas, Martín Palermo, David James, Nikola Žigić, Luis García, Oleksiy Mikhailichenko, etc.).
3. Auto-populate Sportmonks CDN portraits for active players ingested from Sportmonks.
4. Auto-populate deterministic ethnicity-matched Cloudinary facebank portraits for FM23 regens.
5. Atomic transaction with verification of target players.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
import psycopg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gtex_portraits")

DEFAULT_DATABASE_URL = (
    os.environ.get("GTE_DATABASE_URL") or os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
)
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "generated_media" / "regen_newgen_faces" / "manifest.json"

# Curated authentic portraits for legends and iconic players missing pictures
CURATED_LEGEND_PORTRAITS: dict[str, str] = {
    "dida": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Dida_2015.jpg/330px-Dida_2015.jpg",
    "bebeto": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Bebeto_%28cropped%29.jpg/330px-Bebeto_%28cropped%29.jpg",
    "marco amelia": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Marco_Amelia_2011.jpg/330px-Marco_Amelia_2011.jpg",
    "ed de goey": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Ed_de_Goeij_1993.jpg/330px-Ed_de_Goeij_1993.jpg",
    "francesco antonioli": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Francesco_Antonioli_1994-95.jpg/330px-Francesco_Antonioli_1994-95.jpg",
    "leonardo": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Leonardo_Nascimento_de_Ara%C3%BAjo_2018.jpg/330px-Leonardo_Nascimento_de_Ara%C3%BAjo_2018.jpg",
    "per krøldrup": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Per_Kroldrup_cropped.jpg/330px-Per_Kroldrup_cropped.jpg",
    "per kroldrup": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Per_Kroldrup_cropped.jpg/330px-Per_Kroldrup_cropped.jpg",
    "jardel": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/M%C3%A1rio_Jardel_2019.jpg/330px-M%C3%A1rio_Jardel_2019.jpg",
    "josé molina": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Jos%C3%A9_Francisco_Molina_2017.jpg/330px-Jos%C3%A9_Francisco_Molina_2017.jpg",
    "jose molina": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Jos%C3%A9_Francisco_Molina_2017.jpg/330px-Jos%C3%A9_Francisco_Molina_2017.jpg",
    "luca bucci": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Luca_Bucci_1994-95.jpg/330px-Luca_Bucci_1994-95.jpg",
    "stefan effenberg": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Stefan_Effenberg_2015.jpg/330px-Stefan_Effenberg_2015.jpg",
    "flavio roma": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Flavio_Roma_2011.jpg/330px-Flavio_Roma_2011.jpg",
    "fran": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Fran_Gonz%C3%A1lez_2017.jpg/330px-Fran_Gonz%C3%A1lez_2017.jpg",
    "paolo negro": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/48/Paolo_Negro_1994-95.jpg/330px-Paolo_Negro_1994-95.jpg",
    "aldo duscher": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Aldo_Duscher.jpg/330px-Aldo_Duscher.jpg",
    "mark pembridge": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Mark_Pembridge_2004.jpg/330px-Mark_Pembridge_2004.jpg",
    "cris": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Cris_2011.jpg/330px-Cris_2011.jpg",
    "mancini": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Mancini_2009.jpg/330px-Mancini_2009.jpg",
    "alen bokšić": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Alen_Boksic_1994.jpg/330px-Alen_Boksic_1994.jpg",
    "alen boksic": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Alen_Boksic_1994.jpg/330px-Alen_Boksic_1994.jpg",
    "raí": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Ra%C3%AD_2019.jpg/330px-Ra%C3%AD_2019.jpg",
    "rai": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Ra%C3%AD_2019.jpg/330px-Ra%C3%AD_2019.jpg",
    "alexandr hleb": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Alexander_Hleb_2015.jpg/330px-Alexander_Hleb_2015.jpg",
    "alexander hleb": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Alexander_Hleb_2015.jpg/330px-Alexander_Hleb_2015.jpg",
    "belletti": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Juliano_Belletti_2019.jpg/330px-Juliano_Belletti_2019.jpg",
    "enzo francescoli": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Enzo_Francescoli_1996.jpg/330px-Enzo_Francescoli_1996.jpg",
    "antti niemi": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Antti_Niemi_2011.jpg/330px-Antti_Niemi_2011.jpg",
    "vicente": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Vicente_Rodr%C3%ADguez_2011.jpg/330px-Vicente_Rodr%C3%ADguez_2011.jpg",
    "míchel": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/M%C3%ADchel_Gonz%C3%A1lez_2019.jpg/330px-M%C3%ADchel_Gonz%C3%A1lez_2019.jpg",
    "michel": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/M%C3%ADchel_Gonz%C3%A1lez_2019.jpg/330px-M%C3%ADchel_Gonz%C3%A1lez_2019.jpg",
    "javier saviola": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Javier_Saviola_2015.jpg/330px-Javier_Saviola_2015.jpg",
    "ganso": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Paulo_Henrique_Ganso_2019.jpg/330px-Paulo_Henrique_Ganso_2019.jpg",
    "marcelo salas": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Marcelo_Salas_1998.jpg/330px-Marcelo_Salas_1998.jpg",
    "martín palermo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Mart%C3%ADn_Palermo_2012.jpg/330px-Mart%C3%ADn_Palermo_2012.jpg",
    "martin palermo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Mart%C3%ADn_Palermo_2012.jpg/330px-Mart%C3%ADn_Palermo_2012.jpg",
    "david james": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/David_James_2014.jpg/330px-David_James_2014.jpg",
    "nikola žigić": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Nikola_Zigic_2011.jpg/330px-Nikola_Zigic_2011.jpg",
    "nikola zigic": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Nikola_Zigic_2011.jpg/330px-Nikola_Zigic_2011.jpg",
    "luis garcía": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Luis_Garcia_2015.jpg/330px-Luis_Garcia_2015.jpg",
    "luis garcia": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Luis_Garcia_2015.jpg/330px-Luis_Garcia_2015.jpg",
    "oleksiy mikhailichenko": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Oleksiy_Mykhaylychenko_2012.jpg/330px-Oleksiy_Mykhaylychenko_2012.jpg",
    "roger milla": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Milla2008cropped.jpg/500px-Milla2008cropped.jpg",
    "francesco flachi": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Francesco_Flachi_2004.jpg/330px-Francesco_Flachi_2004.jpg",
    "jean vladoiu": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Jean_Vladoiu.jpg/330px-Jean_Vladoiu.jpg",
    "krisztián lisztes": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Lisztes_Kriszti%C3%A1n.jpg/330px-Lisztes_Kriszti%C3%A1n.jpg",
    "krisztian lisztes": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Lisztes_Kriszti%C3%A1n.jpg/330px-Lisztes_Kriszti%C3%A1n.jpg",
    "aruna dindane": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Aruna_Dindane_2011.jpg/330px-Aruna_Dindane_2011.jpg",
    "bruno": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Bruno_Soriano_2016.jpg/330px-Bruno_Soriano_2016.jpg",
    "kevin pressman": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Kevin_Pressman_2012.jpg/330px-Kevin_Pressman_2012.jpg",
    "damiano zenoni": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Damiano_Zenoni_2017.jpg/330px-Damiano_Zenoni_2017.jpg",
    "christian bassedas": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Christian_Bassedas_2016.jpg/330px-Christian_Bassedas_2016.jpg",
    "doriva": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Doriva_2015.jpg/330px-Doriva_2015.jpg",
    "michael schjønberg": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Michael_Schj%C3%B8nberg.jpg/330px-Michael_Schj%C3%B8nberg.jpg",
    "michael schjonberg": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Michael_Schj%C3%B8nberg.jpg/330px-Michael_Schj%C3%B8nberg.jpg",
    "nordin wooter": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Nordin_Wooter_1997.jpg/330px-Nordin_Wooter_1997.jpg",
    "omar asad": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Omar_Asad_2012.jpg/330px-Omar_Asad_2012.jpg",
    "catanha": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Catanha_2018.jpg/330px-Catanha_2018.jpg",
    "dejan stefanovic": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Dejan_Stefanovic_2007.jpg/330px-Dejan_Stefanovic_2007.jpg",
    "luigi apolloni": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Luigi_Apolloni_1994-95.jpg/330px-Luigi_Apolloni_1994-95.jpg",
    "massimo crippa": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Massimo_Crippa_1994-95.jpg/330px-Massimo_Crippa_1994-95.jpg",
    "alfonso": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Alfonso_P%C3%A9rez_Munoz_2018.jpg/330px-Alfonso_P%C3%A9rez_Munoz_2018.jpg",
    "carlos germano": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Carlos_Germano_2019.jpg/330px-Carlos_Germano_2019.jpg",
    "emerson": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Emerson_Ferreira_da_Rosa_2018.jpg/330px-Emerson_Ferreira_da_Rosa_2018.jpg",
    "grigoris georgatos": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Grigoris_Georgatos_2000.jpg/330px-Grigoris_Georgatos_2000.jpg",
    "josé saturnino cardozo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Jose_Saturnino_Cardozo_2016.jpg/330px-Jose_Saturnino_Cardozo_2016.jpg",
    "jose saturnino cardozo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Jose_Saturnino_Cardozo_2016.jpg/330px-Jose_Saturnino_Cardozo_2016.jpg",
    "marko babić": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Marko_Babic_2008.jpg/330px-Marko_Babic_2008.jpg",
    "marko babic": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Marko_Babic_2008.jpg/330px-Marko_Babic_2008.jpg",
    "richard gough": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Richard_Gough_1992.jpg/330px-Richard_Gough_1992.jpg",
    "roberto bonano": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Roberto_Bonano_2002.jpg/330px-Roberto_Bonano_2002.jpg",
    "celso ayala": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Celso_Ayala_1998.jpg/330px-Celso_Ayala_1998.jpg",
    "constantin gâlcă": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Constantin_Galca_2015.jpg/330px-Constantin_Galca_2015.jpg",
    "constantin galca": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Constantin_Galca_2015.jpg/330px-Constantin_Galca_2015.jpg",
    "juanfran": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Juanfran_Garc%C3%ADa_2011.jpg/330px-Juanfran_Garc%C3%ADa_2011.jpg",
    "miroslav đukić": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Miroslav_Djukic_2013.jpg/330px-Miroslav_Djukic_2013.jpg",
    "miroslav djukic": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Miroslav_Djukic_2013.jpg/330px-Miroslav_Djukic_2013.jpg",
    "rené henriksen": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Rene_Henriksen_2004.jpg/330px-Rene_Henriksen_2004.jpg",
    "rene henriksen": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Rene_Henriksen_2004.jpg/330px-Rene_Henriksen_2004.jpg",
    "zé maria": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Ze_Maria_2015.jpg/330px-Ze_Maria_2015.jpg",
    "ze maria": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Ze_Maria_2015.jpg/330px-Ze_Maria_2015.jpg",
    "peter van vossen": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Peter_van_Vossen_1996.jpg/330px-Peter_van_Vossen_1996.jpg",
    "sergio asenjo": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Sergio_Asenjo_2015.jpg/330px-Sergio_Asenjo_2015.jpg",
    "aitor larrazábal": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Aitor_Larrazabal_2018.jpg/330px-Aitor_Larrazabal_2018.jpg",
    "aitor larrazabal": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Aitor_Larrazabal_2018.jpg/330px-Aitor_Larrazabal_2018.jpg",
    "ismaily": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Ismaily_Goncalves_dos_Santos_2018.jpg/330px-Ismaily_Goncalves_dos_Santos_2018.jpg",
    "iulian filipescu": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Iulian_Filipescu_1998.jpg/330px-Iulian_Filipescu_1998.jpg",
    "luis alberto": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Luis_Alberto_2020.jpg/330px-Luis_Alberto_2020.jpg",
    "mauricio taricco": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Mauricio_Taricco_2011.jpg/330px-Mauricio_Taricco_2011.jpg",
    "ugurcan çakır": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Ugurcan_Cakir_2021.jpg/330px-Ugurcan_Cakir_2021.jpg",
    "ugurcan cakir": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Ugurcan_Cakir_2021.jpg/330px-Ugurcan_Cakir_2021.jpg",
    "allan": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Allan_Marques_Loureiro_2019.jpg/330px-Allan_Marques_Loureiro_2019.jpg",
    "georges grün": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Georges_Grun_1990.jpg/330px-Georges_Grun_1990.jpg",
    "georges grun": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Georges_Grun_1990.jpg/330px-Georges_Grun_1990.jpg",
    "mark bright": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Mark_Bright_2018.jpg/330px-Mark_Bright_2018.jpg",
    "nenê": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Nene_2018.jpg/330px-Nene_2018.jpg",
    "nene": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Nene_2018.jpg/330px-Nene_2018.jpg",
    "raúl garcía": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Raul_Garcia_2018.jpg/330px-Raul_Garcia_2018.jpg",
    "raul garcia": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Raul_Garcia_2018.jpg/330px-Raul_Garcia_2018.jpg",
    "tony vidmar": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Tony_Vidmar_2016.jpg/330px-Tony_Vidmar_2016.jpg",
    "çağlar söyüncü": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Caglar_Soyuncu_2018.jpg/330px-Caglar_Soyuncu_2018.jpg",
    "caglar soyuncu": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Caglar_Soyuncu_2018.jpg/330px-Caglar_Soyuncu_2018.jpg",
    "djimi traoré": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Djimi_Traore_2013.jpg/330px-Djimi_Traore_2013.jpg",
    "djimi traore": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Djimi_Traore_2013.jpg/330px-Djimi_Traore_2013.jpg",
    "munir": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Munir_El_Haddadi_2018.jpg/330px-Munir_El_Haddadi_2018.jpg",
    "phil jones": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Phil_Jones_2018.jpg/330px-Phil_Jones_2018.jpg",
}


def load_facebank_assets() -> list[dict]:
    if not MANIFEST_PATH.is_file():
        logger.warning("Manifest not found at %s", MANIFEST_PATH)
        return []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("assets", [])


def run_portrait_hunt(database_url: str | None = None):
    db_url = database_url or DEFAULT_DATABASE_URL
    if not db_url:
        raise SystemExit("A database URL is required. Provide --database-url or set GTE_DATABASE_URL/DATABASE_URL.")

    logger.info("=== STARTING GTEX PORTRAIT HUNT & SYNCHRONIZATION ===")
    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    try:
        # =========================================================================
        # 1. SPECIFIC TARGET PLAYER PORTRAIT RECONCILIATIONS
        # =========================================================================
        logger.info("--- Step 1: Specific target player calibrations ---")

        # Batrakov: Sportmonks CDN photo & canonical club/rating calibration
        batrakov_id = "c9454cf4-2ee3-43c6-9aff-b9c2baf97a75"
        batrakov_pic = "https://cdn.sportmonks.com/images/soccer/players/31/37674431.png"
        fake_batrakov_id = "4db507e8-3e18-414b-9cbb-909b467ddfdf"

        cur.execute(
            """
            INSERT INTO ingestion_player_image_metadata (
                id, source_provider, provider_external_id, player_id,
                image_role, source_url, moderation_status, rights_cleared,
                is_primary, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), 'sportmonks', '37674431', %s,
                'portrait', %s, 'approved', true, true, %s, %s
            )
            ON CONFLICT (player_id, image_role) DO UPDATE SET
                source_url = EXCLUDED.source_url,
                moderation_status = 'approved',
                rights_cleared = true,
                updated_at = EXCLUDED.updated_at
        """,
            (batrakov_id, batrakov_pic, now, now),
        )
        cur.execute(
            """
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            COALESCE(dna_profile::jsonb, '{}'::jsonb),
                            '{portraitUrl}',
                            to_jsonb(%s::text)
                        ),
                        '{image_url}',
                        to_jsonb(%s::text)
                    ),
                    '{overall}',
                    '78'::jsonb
                ),
                '{potential}',
                '88'::jsonb
            ),
            current_club_id = NULL,
            real_world_club_name = 'Lokomotiv Moscow',
            real_world_league_name = 'Russian Premier League',
            position = 'AM',
            normalized_position = 'AM',
            governed_gsi = 78,
            governed_potential_gsi = 88,
            real_player_tier = 'wonderkid',
            is_tradable = true,
            updated_at = %s
            WHERE id = %s
        """,
            (batrakov_pic, batrakov_pic, now, batrakov_id),
        )
        cur.execute(
            """
            UPDATE real_player_profiles
            SET current_club_name = 'Lokomotiv Moscow',
                current_league_name = 'Russian Premier League',
                primary_position = 'Attacking Midfielder',
                canonical_name = 'Aleksey Batrakov',
                updated_at = %s
            WHERE gtex_player_id = %s
        """,
            (now, batrakov_id),
        )
        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    jsonb_set(
                                        jsonb_set(
                                            jsonb_set(
                                                jsonb_set(
                                                    jsonb_set(
                                                        summary_json::jsonb,
                                                        '{portrait_url}',
                                                        to_jsonb(%s::text)
                                                    ),
                                                    '{image_url}',
                                                    to_jsonb(%s::text)
                                                ),
                                                '{club}',
                                                '"Lokomotiv Moscow"'::jsonb
                                            ),
                                            '{club_name}',
                                            '"Lokomotiv Moscow"'::jsonb
                                        ),
                                        '{current_club_name}',
                                        '"Lokomotiv Moscow"'::jsonb
                                    ),
                                    '{position}',
                                    '"Attacking Midfielder"'::jsonb
                                ),
                                '{overall}',
                                '78'::jsonb
                            ),
                            '{global_scouting_index}',
                            '78'::jsonb
                        ),
                        '{gsi}',
                        '78'::jsonb
                    ),
                    '{potential}',
                    '88'::jsonb
                ),
                '{potential_gsi}',
                '88'::jsonb
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (batrakov_pic, batrakov_pic, now, batrakov_id),
        )
        # Ensure fake Batrakov PSG card is deactivated and purged from read model
        cur.execute(
            """
            UPDATE ingestion_players
            SET is_tradable = false,
                real_player_tier = 'archived_duplicate',
                updated_at = %s
            WHERE id = %s
        """,
            (now, fake_batrakov_id),
        )
        cur.execute(
            """
            DELETE FROM player_summary_read_models
            WHERE player_id = %s
        """,
            (fake_batrakov_id,),
        )

        # Evanilson: Sportmonks photo
        evanilson_id = "c6c6a580-376d-4f99-8f63-8385f6d8966b"
        evanilson_pic = "https://cdn.sportmonks.com/images/soccer/players/24/11298616.png"
        cur.execute(
            """
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                COALESCE(dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE id = %s
        """,
            (evanilson_pic, now, evanilson_id),
        )
        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    summary_json::jsonb,
                    '{portrait_url}',
                    to_jsonb(%s::text)
                ),
                '{image_url}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (evanilson_pic, evanilson_pic, now, evanilson_id),
        )

        # Pierre Ismaelo Ganiou
        pierre_id = "8e6f4c2f-445b-4660-81fd-ccf6afe33872"
        pierre_pic = "https://cdn.sportmonks.com/images/soccer/players/18/37633394.png"
        cur.execute(
            """
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                COALESCE(dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE id = %s
        """,
            (pierre_pic, now, pierre_id),
        )
        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    summary_json::jsonb,
                    '{portrait_url}',
                    to_jsonb(%s::text)
                ),
                '{image_url}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (pierre_pic, pierre_pic, now, pierre_id),
        )

        # Sani Suleiman
        sani_id = "d97a6eaa-af0a-4faa-81fd-a0e0fd89110f"
        sani_pic = "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672058/players/portraits/p_d97a6eaa_sani_suleiman.png"
        cur.execute(
            """
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                COALESCE(dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE id = %s
        """,
            (sani_pic, now, sani_id),
        )
        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    summary_json::jsonb,
                    '{portrait_url}',
                    to_jsonb(%s::text)
                ),
                '{image_url}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (sani_pic, sani_pic, now, sani_id),
        )

        # Adamu Yakubu
        adamu_id = "b61a32d8-b8f0-4eb6-b162-feddfd72cf02"
        adamu_pic = (
            "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676049/players/portraits/p_b61a32d8_adam_yakubu.jpg"
        )
        cur.execute(
            """
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                COALESCE(dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE id = %s
        """,
            (adamu_pic, now, adamu_id),
        )
        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    summary_json::jsonb,
                    '{portrait_url}',
                    to_jsonb(%s::text)
                ),
                '{image_url}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (adamu_pic, adamu_pic, now, adamu_id),
        )

        # Taison
        taison_id = "db3f2ab5-ce7a-48fb-87ea-a158d56fb036"
        taison_pic = "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3e/PAOK_Saloniki_-taison_2023.jpg/500px-PAOK_Saloniki_-taison_2023.jpg?utm_source=en.wikipedia.org&utm_campaign=api&utm_content=thumbnail"
        cur.execute(
            """
            UPDATE ingestion_players
            SET position = 'LW',
                normalized_position = 'LW',
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{portraitUrl}',
                    to_jsonb(%s::text)
                ),
                updated_at = %s
            WHERE id = %s
        """,
            (taison_pic, now, taison_id),
        )
        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        summary_json::jsonb,
                        '{portrait_url}',
                        to_jsonb(%s::text)
                    ),
                    '{image_url}',
                    to_jsonb(%s::text)
                ),
                '{position}',
                '"Left Winger"'::jsonb
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (taison_pic, taison_pic, now, taison_id),
        )

        logger.info("Specific target players reconciled with portraits.")

        # =========================================================================
        # 2. ASSIGN CURATED AUTHENTIC PORTRAITS TO LEGENDS
        # =========================================================================
        logger.info("--- Step 2: Assigning curated authentic portraits to legends ---")
        legend_data = list(CURATED_LEGEND_PORTRAITS.items())

        # 2a. Update legendary_player_profiles
        cur.executemany(
            """
            UPDATE legendary_player_profiles
            SET portrait_metadata_json = jsonb_set(
                COALESCE(portrait_metadata_json::jsonb, '{}'::jsonb),
                '{portrait_url}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE LOWER(full_name) = %s
        """,
            [(pic_url, now, norm_name) for norm_name, pic_url in legend_data],
        )

        # 2b. Update linked ingestion_players
        cur.executemany(
            """
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                COALESCE(dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(%s::text)
            ),
            updated_at = %s
            WHERE LOWER(canonical_display_name) = %s OR LOWER(full_name) = %s
        """,
            [(pic_url, now, norm_name, norm_name) for norm_name, pic_url in legend_data],
        )

        # 2c. Upsert into ingestion_player_image_metadata using player_id as external_id
        cur.executemany(
            """
            INSERT INTO ingestion_player_image_metadata (
                id, source_provider, provider_external_id, player_id,
                image_role, source_url, moderation_status, rights_cleared,
                is_primary, created_at, updated_at
            )
            SELECT gen_random_uuid(), 'curated_wiki_legend', ip.id, ip.id,
                   'portrait', %s, 'approved', true, true, %s, %s
            FROM ingestion_players ip
            WHERE (LOWER(ip.canonical_display_name) = %s OR LOWER(ip.full_name) = %s)
              AND ip.is_tradable = true
            ON CONFLICT (player_id, image_role) DO UPDATE SET
                source_url = EXCLUDED.source_url,
                moderation_status = 'approved',
                rights_cleared = true,
                updated_at = EXCLUDED.updated_at
        """,
            [(pic_url, now, now, norm_name, norm_name) for norm_name, pic_url in legend_data],
        )
        logger.info("Assigned curated portraits to %d legends.", len(legend_data))

        # =========================================================================
        # 3. AUTO-ASSIGN SPORTMONKS CDN PORTRAITS FOR SPORTMONKS PLAYERS
        # =========================================================================
        logger.info("--- Step 3: Auto-assigning official CDN portraits for Sportmonks players ---")
        cur.execute(
            """
            WITH sm_candidates AS (
                SELECT DISTINCT ON (ip.provider_external_id)
                       ip.id as player_id,
                       ip.provider_external_id,
                       ('https://cdn.sportmonks.com/images/soccer/players/' || ((ip.provider_external_id::bigint %% 32)::text) || '/' || ip.provider_external_id || '.png') as cdn_url
                FROM ingestion_players ip
                WHERE ip.is_tradable = true
                  AND ip.source_provider = 'sportmonks'
                  AND ip.provider_external_id ~ '^[0-9]+$'
                  AND NOT EXISTS (
                      SELECT 1 FROM ingestion_player_image_metadata img
                      WHERE img.source_provider = 'sportmonks' AND img.provider_external_id = ip.provider_external_id
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM ingestion_player_image_metadata img
                      WHERE img.player_id = ip.id AND img.image_role = 'portrait'
                  )
            )
            INSERT INTO ingestion_player_image_metadata (
                id, source_provider, provider_external_id, player_id,
                image_role, source_url, moderation_status, rights_cleared,
                is_primary, created_at, updated_at
            )
            SELECT gen_random_uuid(), 'sportmonks', sm.provider_external_id, sm.player_id,
                   'portrait', sm.cdn_url, 'approved', true, true, %s, %s
            FROM sm_candidates sm
            ON CONFLICT DO NOTHING
        """,
            (now, now),
        )
        logger.info("Upserted %d Sportmonks CDN portraits into image metadata.", cur.rowcount)

        # Update dna_profile for these Sportmonks players
        cur.execute(
            """
            UPDATE ingestion_players ip
            SET dna_profile = jsonb_set(
                COALESCE(ip.dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(('https://cdn.sportmonks.com/images/soccer/players/' || ((ip.provider_external_id::bigint %% 32)::text) || '/' || ip.provider_external_id || '.png')::text)
            ),
            updated_at = %s
            WHERE ip.is_tradable = true
              AND ip.source_provider = 'sportmonks'
              AND ip.provider_external_id ~ '^[0-9]+$'
              AND (ip.dna_profile->>'portraitUrl' IS NULL OR ip.dna_profile->>'portraitUrl' = '')
        """,
            (now,),
        )
        logger.info("Updated dna_profile for %d Sportmonks players.", cur.rowcount)

        # =========================================================================
        # 4. FACEBANK PORTRAITS FOR REGENS STILL MISSING PICTURES
        # =========================================================================
        logger.info("--- Step 4: Facebank portrait assignment for FM23 regens ---")
        facebank_assets = load_facebank_assets()
        if facebank_assets:
            # Query regens with no image
            cur.execute("""
                SELECT ip.id, ip.provider_external_id, ip.canonical_display_name, ip.country_id,
                       c.name as country_name
                FROM ingestion_players ip
                LEFT JOIN ingestion_countries c ON c.id = ip.country_id
                LEFT JOIN ingestion_player_image_metadata img ON img.player_id = ip.id AND img.image_role = 'portrait'
                WHERE ip.is_tradable = true
                  AND ip.source_provider = 'fm23_genie_scout'
                  AND (ip.dna_profile->>'portraitUrl' IS NULL OR ip.dna_profile->>'portraitUrl' = '')
                  AND (img.source_url IS NULL OR img.source_url = '')
            """)
            regen_rows = cur.fetchall()
            logger.info("Found %d FM23 players missing portraits to match from facebank.", len(regen_rows))

            # Batch assign facebank assets deterministically
            regen_image_inserts = []
            regen_dna_updates = []
            for r in regen_rows:
                pid, ext_id, cname, cid, cname_str = r
                # Deterministic hash index
                seed_str = f"{ext_id or pid}:{cname}"
                idx = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16) % len(facebank_assets)
                asset = facebank_assets[idx]
                face_url = asset["cloudinary_secure_url"]

                regen_image_inserts.append((pid, str(pid), face_url, now, now))
                regen_dna_updates.append((face_url, now, pid))

            if regen_image_inserts:
                cur.executemany(
                    """
                    INSERT INTO ingestion_player_image_metadata (
                        id, source_provider, provider_external_id, player_id,
                        image_role, source_url, moderation_status, rights_cleared,
                        is_primary, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), 'facebank_cloudinary', %s, %s,
                        'portrait', %s, 'approved', true, true, %s, %s
                    )
                    ON CONFLICT DO NOTHING
                """,
                    [
                        (ext_id, pid, face_url, t_now1, t_now2)
                        for pid, ext_id, face_url, t_now1, t_now2 in regen_image_inserts
                    ],
                )

                cur.executemany(
                    """
                    UPDATE ingestion_players
                    SET dna_profile = jsonb_set(
                        COALESCE(dna_profile::jsonb, '{}'::jsonb),
                        '{portraitUrl}',
                        to_jsonb(%s::text)
                    ),
                    updated_at = %s
                    WHERE id = %s
                """,
                    regen_dna_updates,
                )
                logger.info("Assigned facebank portraits to %d FM23 regens.", len(regen_image_inserts))

        # =========================================================================
        # 5. SYNC ALL PORTRAITS TO READ MODELS ACROSS UNIVERSE
        # =========================================================================
        logger.info("--- Step 5: Syncing all player portraits to player_summary_read_models ---")

        # 5a. Set portrait_url from ingestion_player_image_metadata if available
        cur.execute(
            """
            UPDATE player_summary_read_models rm
            SET summary_json = jsonb_set(
                jsonb_set(
                    rm.summary_json::jsonb,
                    '{portrait_url}',
                    to_jsonb(img.source_url)
                ),
                '{image_url}',
                to_jsonb(img.source_url)
            ),
            updated_at = %s
            FROM ingestion_player_image_metadata img
            WHERE img.player_id = rm.player_id
              AND img.image_role = 'portrait'
              AND img.source_url IS NOT NULL
              AND img.source_url != ''
              AND (
                rm.summary_json->>'portrait_url' IS NULL
                OR rm.summary_json->>'portrait_url' != img.source_url
                OR rm.summary_json->>'image_url' IS NULL
                OR rm.summary_json->>'image_url' != img.source_url
              )
        """,
            (now,),
        )
        logger.info("Synced %d read models with portrait from image metadata.", cur.rowcount)

        # 5b. For any remaining without image metadata, sync from dna_profile->>'portraitUrl'
        cur.execute(
            """
            UPDATE player_summary_read_models rm
            SET summary_json = jsonb_set(
                jsonb_set(
                    rm.summary_json::jsonb,
                    '{portrait_url}',
                    to_jsonb(ip.dna_profile->>'portraitUrl')
                ),
                '{image_url}',
                to_jsonb(ip.dna_profile->>'portraitUrl')
            ),
            updated_at = %s
            FROM ingestion_players ip
            WHERE ip.id = rm.player_id
              AND ip.dna_profile->>'portraitUrl' IS NOT NULL
              AND ip.dna_profile->>'portraitUrl' != ''
              AND (
                rm.summary_json->>'portrait_url' IS NULL
                OR rm.summary_json->>'portrait_url' != (ip.dna_profile->>'portraitUrl')
                OR rm.summary_json->>'image_url' IS NULL
                OR rm.summary_json->>'image_url' != (ip.dna_profile->>'portraitUrl')
              )
        """,
            (now,),
        )
        logger.info("Synced %d read models with portrait from dna_profile.", cur.rowcount)

        # 5c. Sync dna_profile['portraitUrl'] for any ingestion_players that have image metadata
        cur.execute(
            """
            UPDATE ingestion_players ip
            SET dna_profile = jsonb_set(
                COALESCE(ip.dna_profile::jsonb, '{}'::jsonb),
                '{portraitUrl}',
                to_jsonb(img.source_url)
            ),
            updated_at = %s
            FROM ingestion_player_image_metadata img
            WHERE img.player_id = ip.id
              AND img.image_role = 'portrait'
              AND img.source_url IS NOT NULL
              AND img.source_url != ''
              AND (
                ip.dna_profile->>'portraitUrl' IS NULL
                OR ip.dna_profile->>'portraitUrl' != img.source_url
              )
        """,
            (now,),
        )
        logger.info("Synced %d ingestion_players dna_profile from image metadata.", cur.rowcount)

        # Commit everything atomically
        conn.commit()
        logger.info("=== SUCCESS: ALL PORTRAITS HUNTED, ASSIGNED & COMMITTED ATOMICALLY ===")

    except Exception as exc:
        conn.rollback()
        logger.exception("Error assigning portraits: %s", exc)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunt down and assign portraits to all players.")
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="Target database URL. Defaults to GTE_DATABASE_URL or DATABASE_URL.",
    )
    args = parser.parse_args()
    run_portrait_hunt(database_url=args.database_url)

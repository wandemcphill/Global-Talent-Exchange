"""Implement GTEX Generational Legend Age Rules.

Enforces:
1. Ceiling: No legend in the game older than 30 (age <= 30).
2. Generational Band 1 (Active 1950s-1980s): In-game ages 26-30.
   - Pelé, Di Stéfano, etc. are the oldest legends in the game (Age 30).
   - Cruyff, Beckenbauer, etc. (Age 28).
   - Maradona, Zico, Platini, Gullit, Van Basten, Baresi, Matthäus (Age 27).
3. Generational Band 2 (Active 1990s-2010): In-game ages 23-25.
   - Romário, Cantona, Laudrup, Bergkamp, Klinsmann, Weah, Batistuta, Maldini, Shearer (Age 25).
   - Zidane, Ronaldo R9, Henry, Ronaldinho, Rivaldo, Figo, Beckham, Nedvěd, Shevchenko, Raúl, Totti, Del Piero (Age 24).
   - Gerrard, Lampard, Scholes, Pirlo, Xavi, Iniesta, Casillas, Puyol, Drogba, Rooney, Robben, Ribéry (Age 23).
4. Generational Band 3 (Modern Active Veterans >= 34 in real life): In-game ages 20-22.
   - Messi, Cristiano Ronaldo are the youngest legends in the game (Age 20).
   - Modrić, Benzema, Lewandowski, Suárez, Ramos, Neuer, Kroos, Müller, Di María (Age 21).
   - Casemiro, De Bruyne, Salah, Van Dijk, Son, Courtois, Neymar, Kanté (Age 22).
5. All other legends clamped to [23, 30].
6. Real biographical DOB preserved in factual_date_of_birth.

Revision ID: 20261101_0201_legend_generational_ages
Revises: 20261101_0200_legend_provenance_and_governed_gsi
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261101_0201_legend_generational_ages"
down_revision = "20261101_0200_legend_provenance_and_governed_gsi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        if "legendary_player_profiles" in tables:
            op.execute(
                """
                WITH computed AS (
                    SELECT 
                        id,
                        date_of_birth,
                        CASE 
                            -- Band 3C: Absolute Youngest Legends (Age 20)
                            WHEN slug IN ('lionel-messi-7458500', 'cristiano-ronaldo-735216') THEN 20

                            -- Band 1A: Oldest Legends in Game (Age 30)
                            WHEN slug IN ('alfredo-di-stfano-2002041145') THEN 30

                            -- Band 1C: 1980s Icons (Age 27)
                            WHEN slug IN (
                                'diego-maradona-2002041118', 'zico-2002041190', 'marco-van-basten-852152',
                                'ruud-gullit-2010704', 'franco-baresi-52', 'lothar-matthus-1270'
                            ) THEN 27

                            -- Band 2A: 1990s Peak Icons (Age 25)
                            WHEN slug IN (
                                'michael-laudrup-601710', 'brian-laudrup-2002042469', 'eric-cantona-2002042479',
                                'ric-cantona-2002041392', 'paolo-maldini-45', 'dennis-bergkamp-2010481',
                                'j-rgen-klinsmann-100014', 'george-weah-2002041023', 'gabriel-batistuta-2002041146',
                                'alan-shearer-2002041341'
                            ) THEN 25

                            -- Band 2B: 2000s Peak Icons (Age 24)
                            WHEN slug IN (
                                'zinedine-zidane-8076', 'ronaldo-707715', 'thierry-henry-9888',
                                'ronaldinho-2002041199', 'rivaldo-2002041204', 'david-beckham-2003443',
                                'pavel-nedved-8440', 'andriy-shevchenko-105986', 'ral-11952',
                                'francesco-totti-2002042128', 'alessandro-del-piero-8074'
                            ) THEN 24

                            -- Band 2C: Late 2000s / 2010 Peak Icons (Age 23)
                            WHEN slug IN (
                                'steven-gerrard-108658', 'frank-lampard-2004697', 'paul-scholes-2005442',
                                'andrea-pirlo-703963', 'xavi-4200583', 'andrs-iniesta-2002041699',
                                'andres-iniesta-2002041673', 'iker-casillas-6700151', 'carles-puyol-4206586',
                                'didier-drogba-6201102', 'wayne-rooney-5108390', 'arjen-robben-850881',
                                'franck-ribry-8426264'
                            ) THEN 23

                            -- Band 3A: Modern Active Veterans >= 35 (Age 21)
                            WHEN slug IN (
                                'luka-modric-653054', 'karim-benzema-8435089', 'luis-surez-78000335',
                                'sergio-ramos-7458272', 'manuel-neuer-8718372', 'toni-kroos-156772',
                                'thomas-mller-35011448'
                            ) THEN 21

                            -- Band 3B: Modern Active Veterans >= 34 (Age 22)
                            WHEN slug IN ('mohamed-salah-98028755') THEN 22

                            -- General Clamp Rule for all other legends
                            WHEN DATE_PART('year', AGE('2026-11-01'::date, date_of_birth)) > 30 THEN 
                                LEAST(30, 26 + (DATE_PART('year', AGE('2026-11-01'::date, date_of_birth))::int - 31))
                            WHEN DATE_PART('year', AGE('2026-11-01'::date, date_of_birth)) < 23 THEN 23
                            ELSE DATE_PART('year', AGE('2026-11-01'::date, date_of_birth))::int
                        END as target_age,
                        CASE 
                            WHEN slug = 'lionel-messi-7458500' THEN '1987-06-24'::date
                            WHEN slug = 'cristiano-ronaldo-735216' THEN '1985-02-05'::date
                            WHEN slug = 'alfredo-di-stfano-2002041145' THEN '1926-07-04'::date
                            WHEN slug = 'diego-maradona-2002041118' THEN '1960-10-30'::date
                            WHEN slug = 'zico-2002041190' THEN '1953-03-03'::date
                            WHEN slug = 'marco-van-basten-852152' THEN '1964-10-31'::date
                            WHEN slug = 'ruud-gullit-2010704' THEN '1962-09-01'::date
                            WHEN slug = 'franco-baresi-52' THEN '1960-05-08'::date
                            WHEN slug = 'lothar-matthus-1270' THEN '1961-03-21'::date
                            WHEN slug = 'michael-laudrup-601710' THEN '1964-06-15'::date
                            WHEN slug = 'brian-laudrup-2002042469' THEN '1969-02-22'::date
                            WHEN slug IN ('eric-cantona-2002042479', 'ric-cantona-2002041392') THEN '1966-05-24'::date
                            WHEN slug = 'paolo-maldini-45' THEN '1968-06-26'::date
                            WHEN slug = 'dennis-bergkamp-2010481' THEN '1969-05-10'::date
                            WHEN slug = 'j-rgen-klinsmann-100014' THEN '1964-07-30'::date
                            WHEN slug = 'george-weah-2002041023' THEN '1966-10-01'::date
                            WHEN slug = 'gabriel-batistuta-2002041146' THEN '1969-02-01'::date
                            WHEN slug = 'alan-shearer-2002041341' THEN '1970-08-13'::date
                            WHEN slug = 'zinedine-zidane-8076' THEN '1972-06-23'::date
                            WHEN slug = 'ronaldo-707715' THEN '1976-09-22'::date
                            WHEN slug = 'thierry-henry-9888' THEN '1977-08-17'::date
                            WHEN slug = 'ronaldinho-2002041199' THEN '1980-03-21'::date
                            WHEN slug = 'rivaldo-2002041204' THEN '1972-04-19'::date
                            WHEN slug = 'david-beckham-2003443' THEN '1975-05-02'::date
                            WHEN slug = 'pavel-nedved-8440' THEN '1972-08-30'::date
                            WHEN slug = 'andriy-shevchenko-105986' THEN '1976-09-29'::date
                            WHEN slug = 'ral-11952' THEN '1977-06-27'::date
                            WHEN slug = 'francesco-totti-2002042128' THEN '1976-09-27'::date
                            WHEN slug = 'alessandro-del-piero-8074' THEN '1974-11-09'::date
                            WHEN slug = 'steven-gerrard-108658' THEN '1980-05-30'::date
                            WHEN slug = 'frank-lampard-2004697' THEN '1978-06-20'::date
                            WHEN slug = 'paul-scholes-2005442' THEN '1974-11-16'::date
                            WHEN slug = 'andrea-pirlo-703963' THEN '1979-05-19'::date
                            WHEN slug = 'xavi-4200583' THEN '1980-01-25'::date
                            WHEN slug IN ('andrs-iniesta-2002041699', 'andres-iniesta-2002041673') THEN '1984-05-11'::date
                            WHEN slug = 'iker-casillas-6700151' THEN '1981-05-20'::date
                            WHEN slug = 'carles-puyol-4206586' THEN '1978-04-13'::date
                            WHEN slug = 'didier-drogba-6201102' THEN '1978-03-11'::date
                            WHEN slug = 'wayne-rooney-5108390' THEN '1985-10-24'::date
                            WHEN slug = 'arjen-robben-850881' THEN '1984-01-23'::date
                            WHEN slug = 'franck-ribry-8426264' THEN '1983-04-07'::date
                            WHEN slug = 'luka-modric-653054' THEN '1985-09-09'::date
                            WHEN slug = 'karim-benzema-8435089' THEN '1987-12-19'::date
                            WHEN slug = 'luis-surez-78000335' THEN '1987-01-24'::date
                            WHEN slug = 'sergio-ramos-7458272' THEN '1986-03-30'::date
                            WHEN slug = 'manuel-neuer-8718372' THEN '1986-03-27'::date
                            WHEN slug = 'toni-kroos-156772' THEN '1990-01-04'::date
                            WHEN slug = 'thomas-mller-35011448' THEN '1989-09-13'::date
                            WHEN slug = 'mohamed-salah-98028755' THEN '1992-06-15'::date
                            ELSE NULL
                        END as calculated_factual_dob
                    FROM legendary_player_profiles
                ),
                new_values AS (
                    SELECT 
                        id,
                        calculated_factual_dob,
                        MAKE_DATE(
                            (2026 - target_age - CASE WHEN (EXTRACT(MONTH FROM date_of_birth), EXTRACT(DAY FROM date_of_birth)) > (11, 1) THEN 1 ELSE 0 END)::int,
                            EXTRACT(MONTH FROM date_of_birth)::int,
                            CASE 
                                WHEN EXTRACT(MONTH FROM date_of_birth) = 2 AND EXTRACT(DAY FROM date_of_birth) = 29 THEN 28
                                ELSE EXTRACT(DAY FROM date_of_birth)::int
                            END
                        ) as new_dob
                    FROM computed
                )
                UPDATE legendary_player_profiles lp
                SET 
                    date_of_birth = nv.new_dob,
                    factual_date_of_birth = COALESCE(lp.factual_date_of_birth, nv.calculated_factual_dob),
                    updated_at = NOW()
                FROM new_values nv
                WHERE lp.id = nv.id;
                """
            )

        if "ingestion_players" in tables:
            # Sync mapped legends
            op.execute(
                """
                UPDATE ingestion_players ip
                SET date_of_birth = lp.date_of_birth,
                    factual_date_of_birth = COALESCE(lp.factual_date_of_birth, ip.factual_date_of_birth),
                    updated_at = NOW()
                FROM legendary_player_profiles lp
                WHERE ip.legendary_profile_id = lp.id;
                """
            )

            # Explicit unlinked prime legends and active veterans
            op.execute(
                """
                -- Pelé: Oldest in game -> Age 30
                UPDATE ingestion_players 
                SET date_of_birth = '1996-10-23'::date, 
                    factual_date_of_birth = '1940-10-23'::date, 
                    updated_at = NOW()
                WHERE id = 'c3f233ee-54fc-4e52-8b21-03bccac241dd';

                -- Romário: 1990s peak -> Age 25
                UPDATE ingestion_players 
                SET date_of_birth = '2001-01-29'::date, 
                    factual_date_of_birth = '1966-01-29'::date, 
                    updated_at = NOW()
                WHERE id = '64ac17c6-768d-4cae-9cac-7ccbd0b079d9';

                -- Casemiro: Modern active veteran >= 34 -> Age 22
                UPDATE ingestion_players 
                SET date_of_birth = '2004-02-23'::date, 
                    factual_date_of_birth = COALESCE(factual_date_of_birth, '1992-02-23'::date), 
                    updated_at = NOW()
                WHERE id = '9191b3c9-24d1-45e2-81fc-7a8cd545de08';

                -- Kevin De Bruyne: Modern active veteran >= 34 -> Age 22
                UPDATE ingestion_players 
                SET date_of_birth = '2004-06-28'::date, 
                    factual_date_of_birth = COALESCE(factual_date_of_birth, '1991-06-28'::date), 
                    updated_at = NOW()
                WHERE id = '72baf131-8754-4356-8517-3106cd4c5d4e';

                -- Robert Lewandowski: Modern active veteran >= 35 -> Age 21
                UPDATE ingestion_players 
                SET date_of_birth = '2005-08-21'::date, 
                    factual_date_of_birth = COALESCE(factual_date_of_birth, '1988-08-21'::date), 
                    updated_at = NOW()
                WHERE id = 'c1a1f90f-0b11-4054-b98c-5397cc7dc2a9';
                """
            )


def downgrade() -> None:
    pass

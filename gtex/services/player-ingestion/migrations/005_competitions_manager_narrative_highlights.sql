ALTER TABLE fixtures
  ADD COLUMN IF NOT EXISTS competition_id BIGINT,
  ADD COLUMN IF NOT EXISTS fixture_type TEXT DEFAULT 'league',
  ADD COLUMN IF NOT EXISTS round_number INT,
  ADD COLUMN IF NOT EXISTS stage TEXT,
  ADD COLUMN IF NOT EXISTS priority INT DEFAULT 50;

CREATE TABLE IF NOT EXISTS season_competitions (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('league', 'cup', 'continental')),
  season_id BIGINT REFERENCES seasons(id) ON DELETE CASCADE,
  priority INT DEFAULT 50,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS season_competition_teams (
  competition_id BIGINT REFERENCES season_competitions(id) ON DELETE CASCADE,
  team_id BIGINT REFERENCES teams(team_id),
  seed INT,
  qualified_from TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (competition_id, team_id)
);

CREATE TABLE IF NOT EXISTS season_managers (
  id BIGSERIAL PRIMARY KEY,
  team_id BIGINT UNIQUE REFERENCES teams(team_id),
  name TEXT,
  mentality TEXT NOT NULL DEFAULT 'balanced',
  adaptability INT NOT NULL DEFAULT 50,
  risk INT NOT NULL DEFAULT 50,
  pressure FLOAT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS season_narratives (
  id BIGSERIAL PRIMARY KEY,
  fixture_id BIGINT REFERENCES fixtures(id) ON DELETE CASCADE,
  competition_id BIGINT REFERENCES season_competitions(id) ON DELETE SET NULL,
  team_id BIGINT REFERENCES teams(team_id),
  player_id BIGINT REFERENCES players(player_id),
  type TEXT NOT NULL,
  description TEXT NOT NULL,
  impact FLOAT NOT NULL DEFAULT 0,
  metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS season_match_events (
  id BIGSERIAL PRIMARY KEY,
  fixture_id BIGINT REFERENCES fixtures(id) ON DELETE CASCADE,
  minute INT NOT NULL,
  sequence INT NOT NULL,
  type TEXT NOT NULL,
  team_id BIGINT REFERENCES teams(team_id),
  player_id BIGINT REFERENCES players(player_id),
  description TEXT NOT NULL,
  is_highlight BOOLEAN NOT NULL DEFAULT FALSE,
  animation_key TEXT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

DROP INDEX IF EXISTS idx_fixtures_unique_match;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fixtures_unique_match_scope
  ON fixtures (
    season_id,
    COALESCE(competition_id, 0),
    home_team,
    away_team,
    COALESCE(round_number, 0),
    COALESCE(stage, '')
  );

CREATE INDEX IF NOT EXISTS idx_season_competitions_season_type
  ON season_competitions (season_id, type, priority);

CREATE INDEX IF NOT EXISTS idx_season_competition_teams_team
  ON season_competition_teams (team_id);

CREATE INDEX IF NOT EXISTS idx_season_managers_team
  ON season_managers (team_id);

CREATE INDEX IF NOT EXISTS idx_season_narratives_fixture
  ON season_narratives (fixture_id, type);

CREATE INDEX IF NOT EXISTS idx_season_match_events_fixture_sequence
  ON season_match_events (fixture_id, sequence);

CREATE INDEX IF NOT EXISTS idx_season_match_events_highlights
  ON season_match_events (fixture_id, is_highlight, minute);

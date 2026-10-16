ALTER TABLE season_match_events
  ADD COLUMN IF NOT EXISTS commentary TEXT,
  ADD COLUMN IF NOT EXISTS score_text TEXT,
  ADD COLUMN IF NOT EXISTS audio_url TEXT;

CREATE TABLE IF NOT EXISTS season_player_relationships (
  player_a BIGINT REFERENCES players(player_id) ON DELETE CASCADE,
  player_b BIGINT REFERENCES players(player_id) ON DELETE CASCADE,
  chemistry FLOAT NOT NULL DEFAULT 0,
  relationship_type TEXT NOT NULL DEFAULT 'teammate',
  last_updated TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (player_a, player_b),
  CHECK (player_a < player_b),
  CHECK (chemistry >= -1 AND chemistry <= 1)
);

CREATE TABLE IF NOT EXISTS season_youth_academies (
  team_id BIGINT PRIMARY KEY REFERENCES teams(team_id) ON DELETE CASCADE,
  nationality_bias TEXT,
  identity TEXT,
  yearly_intake INT NOT NULL DEFAULT 3,
  quality FLOAT NOT NULL DEFAULT 0.5,
  last_generated_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS season_scouting_assignments (
  id BIGSERIAL PRIMARY KEY,
  team_id BIGINT REFERENCES teams(team_id) ON DELETE CASCADE,
  manager_id BIGINT REFERENCES season_managers(id) ON DELETE SET NULL,
  region TEXT NOT NULL,
  min_potential INT NOT NULL DEFAULT 75,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS season_scouting_reports (
  id BIGSERIAL PRIMARY KEY,
  assignment_id BIGINT REFERENCES season_scouting_assignments(id) ON DELETE CASCADE,
  player_id BIGINT REFERENCES players(player_id) ON DELETE CASCADE,
  team_id BIGINT REFERENCES teams(team_id) ON DELETE CASCADE,
  region TEXT NOT NULL,
  potential INT,
  fit_score FLOAT NOT NULL DEFAULT 0,
  summary TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (assignment_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_season_player_relationships_player_b
  ON season_player_relationships (player_b);

CREATE INDEX IF NOT EXISTS idx_season_player_relationships_chemistry
  ON season_player_relationships (chemistry);

CREATE INDEX IF NOT EXISTS idx_season_scouting_assignments_team_status
  ON season_scouting_assignments (team_id, status);

CREATE INDEX IF NOT EXISTS idx_season_scouting_reports_team_region
  ON season_scouting_reports (team_id, region);

CREATE INDEX IF NOT EXISTS idx_season_match_events_commentary
  ON season_match_events (fixture_id, minute)
  WHERE commentary IS NOT NULL;

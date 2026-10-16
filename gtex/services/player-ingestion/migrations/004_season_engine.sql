ALTER TABLE players
  ADD COLUMN IF NOT EXISTS is_retired BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS retired_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS seasons (
  id BIGSERIAL PRIMARY KEY,
  name TEXT,
  league_id BIGINT,
  start_date DATE,
  end_date DATE,
  is_active BOOLEAN DEFAULT TRUE,
  simulation_date DATE,
  last_tick_date DATE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixtures (
  id BIGSERIAL PRIMARY KEY,
  season_id BIGINT REFERENCES seasons(id) ON DELETE CASCADE,
  home_team BIGINT REFERENCES teams(team_id),
  away_team BIGINT REFERENCES teams(team_id),
  match_date TIMESTAMP,
  played BOOLEAN DEFAULT FALSE,
  home_score INT,
  away_score INT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CHECK (home_team IS NULL OR away_team IS NULL OR home_team <> away_team)
);

CREATE TABLE IF NOT EXISTS standings (
  team_id BIGINT REFERENCES teams(team_id),
  season_id BIGINT REFERENCES seasons(id) ON DELETE CASCADE,
  played INT DEFAULT 0,
  wins INT DEFAULT 0,
  draws INT DEFAULT 0,
  losses INT DEFAULT 0,
  goals_for INT DEFAULT 0,
  goals_against INT DEFAULT 0,
  points INT DEFAULT 0,
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (team_id, season_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fixtures_unique_match
  ON fixtures (season_id, home_team, away_team);

CREATE INDEX IF NOT EXISTS idx_fixtures_matchday
  ON fixtures (match_date, played);

CREATE INDEX IF NOT EXISTS idx_fixtures_season_played
  ON fixtures (season_id, played);

CREATE INDEX IF NOT EXISTS idx_seasons_active
  ON seasons (is_active, start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_standings_table
  ON standings (season_id, points DESC, goals_for DESC);

CREATE INDEX IF NOT EXISTS idx_players_retired
  ON players (is_retired);

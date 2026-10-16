ALTER TABLE players
  ADD COLUMN IF NOT EXISTS form FLOAT DEFAULT 0.5,
  ADD COLUMN IF NOT EXISTS sharpness FLOAT DEFAULT 0.5,
  ADD COLUMN IF NOT EXISTS is_injured BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS injury_return_date TIMESTAMP,
  ADD COLUMN IF NOT EXISTS minutes_played INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_match_rating FLOAT DEFAULT 0;

UPDATE players
SET
  form = COALESCE(form, 0.5),
  sharpness = COALESCE(sharpness, 0.5),
  is_injured = COALESCE(is_injured, FALSE),
  minutes_played = COALESCE(minutes_played, 0),
  last_match_rating = COALESCE(last_match_rating, 0);

CREATE TABLE IF NOT EXISTS teams (
  team_id BIGINT PRIMARY KEY,
  name TEXT,
  league_id BIGINT,
  strength FLOAT DEFAULT 50,
  updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE teams
  ADD COLUMN IF NOT EXISTS team_id BIGINT,
  ADD COLUMN IF NOT EXISTS name TEXT,
  ADD COLUMN IF NOT EXISTS league_id BIGINT,
  ADD COLUMN IF NOT EXISTS strength FLOAT DEFAULT 50,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS idx_teams_team_id_unique ON teams (team_id);
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players (team_id);
CREATE INDEX IF NOT EXISTS idx_players_injury_status ON players (is_injured, injury_return_date);
CREATE INDEX IF NOT EXISTS idx_players_match_form ON players (form, sharpness);

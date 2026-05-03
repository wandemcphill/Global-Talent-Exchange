ALTER TABLE players
  ADD COLUMN IF NOT EXISTS position TEXT,
  ADD COLUMN IF NOT EXISTS overall INT,
  ADD COLUMN IF NOT EXISTS potential INT,
  ADD COLUMN IF NOT EXISTS pace INT,
  ADD COLUMN IF NOT EXISTS shooting INT,
  ADD COLUMN IF NOT EXISTS passing INT,
  ADD COLUMN IF NOT EXISTS dribbling INT,
  ADD COLUMN IF NOT EXISTS defending INT,
  ADD COLUMN IF NOT EXISTS physical INT,
  ADD COLUMN IF NOT EXISTS morale FLOAT DEFAULT 50.0,
  ADD COLUMN IF NOT EXISTS fitness FLOAT DEFAULT 100.0,
  ADD COLUMN IF NOT EXISTS traits TEXT[] DEFAULT ARRAY[]::TEXT[],
  ADD COLUMN IF NOT EXISTS personality TEXT;

CREATE TABLE IF NOT EXISTS tactics (
  team_id BIGINT PRIMARY KEY,
  formation TEXT NOT NULL DEFAULT '4-2-3-1',
  style TEXT NOT NULL DEFAULT 'balanced',
  pressing INT NOT NULL DEFAULT 55,
  tempo INT NOT NULL DEFAULT 55,
  width INT NOT NULL DEFAULT 55,
  line_height INT NOT NULL DEFAULT 55,
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transfers (
  id BIGSERIAL PRIMARY KEY,
  player_id BIGINT REFERENCES players(player_id) ON DELETE CASCADE,
  from_team BIGINT,
  to_team BIGINT,
  fee INT,
  date TIMESTAMP DEFAULT NOW(),
  source TEXT DEFAULT 'simulation'
);

CREATE INDEX IF NOT EXISTS idx_players_position ON players (position);
CREATE INDEX IF NOT EXISTS idx_players_potential_age ON players (potential, age);
CREATE INDEX IF NOT EXISTS idx_transfers_player_id ON transfers (player_id);
CREATE INDEX IF NOT EXISTS idx_transfers_date ON transfers (date);

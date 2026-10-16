CREATE TABLE IF NOT EXISTS players (
  player_id BIGINT PRIMARY KEY,
  name TEXT,
  nationality TEXT,
  age INT,
  image_url TEXT,
  is_regen BOOLEAN DEFAULT FALSE,
  rights_cleared BOOLEAN,
  updated_at TIMESTAMP DEFAULT NOW(),
  source_hash TEXT,
  source_provider TEXT,
  league_id BIGINT,
  team_id BIGINT,
  image_source TEXT
);

CREATE TABLE IF NOT EXISTS sync_state (
  key TEXT PRIMARY KEY,
  last_synced TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_players_is_regen ON players (is_regen);
CREATE INDEX IF NOT EXISTS idx_players_updated_at ON players (updated_at);
CREATE INDEX IF NOT EXISTS idx_players_league_team ON players (league_id, team_id);

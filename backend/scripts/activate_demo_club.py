import sys
from datetime import datetime, timezone
import sqlite3

db_path = r"C:\Users\ayomc\.gemini\antigravity\scratch\Global-Talent-Exchange\backend\test_playwright.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get user id for seed.scout@gte.local
cur.execute("SELECT id FROM users WHERE email='seed.scout@gte.local'")
user_row = cur.fetchone()
if not user_row:
    print("User not found!")
    sys.exit(1)
user_id = user_row[0]

# Get club profile id
cur.execute("SELECT id, club_name FROM club_profiles WHERE club_name LIKE '%Argentina%'")
club_row = cur.fetchone()
if not club_row:
    print("Club profile not found!")
    sys.exit(1)
club_id, club_name = club_row

# Insert or update owner_club_states
now = datetime.now(timezone.utc).isoformat()
facilities = '{"academy": 2, "training": 2, "stadium": 2, "medical": 2, "analytics": 2}'
manager = '{"manager_id": "mgr_default_01", "name": "Marcus Vance", "display_name": "Marcus Vance", "rarity": "rare", "mentality": "balanced", "tactics": ["possession"], "traits": ["tactician"]}'

cur.execute(
    """
INSERT INTO owner_club_states (
    id, club_id, owner_user_id, club_name, stage, manager_json, facilities_json,
    fans, prestige, mentality, value_history_json, world_day, academy_intake_sequence, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(club_id) DO UPDATE SET stage='active', manager_json=excluded.manager_json, facilities_json=excluded.facilities_json
""",
    (
        f"state_{club_id[:8]}",
        club_id,
        user_id,
        club_name,
        "active",
        manager,
        facilities,
        15000,
        75,
        "balanced",
        "[]",
        1,
        0,
        now,
    ),
)

conn.commit()
conn.close()
print(f"Club {club_name} ({club_id}) is now set to ACTIVE with manager name for user {user_id}!")

import sys, time, collections
sys.path.insert(0, "/app/gtex/backend")
from sqlalchemy import event
from app.core.database import get_engine, get_session_factory, load_model_modules
load_model_modules()
engine = get_engine()
stats = collections.Counter()
timing = collections.Counter()
@event.listens_for(engine, "before_cursor_execute")
def _b(conn, cursor, statement, params, context, executemany):
    context._t = time.time()
@event.listens_for(engine, "after_cursor_execute")
def _a(conn, cursor, statement, params, context, executemany):
    key = statement.strip().split("\n")[0][:110]
    stats[key] += 1
    timing[key] += time.time() - context._t
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.models.user import User
S = get_session_factory()
with S() as s:
    svc = NationalTeamTournamentService(s)
    actor = s.get(User, "09ed5191-7b2d-4eff-a656-f26b58408758")
    stats.clear(); timing.clear()
    t = time.time()
    out = svc.list_rental_players(competition_id="8e33f8f7-f18e-48c8-9eed-a678639b56cc", limit=12, country_code="NG", entry_id="3487e6de-cbe3-4344-abbc-e969026e0e01", actor=actor)
    print("list", out["total"], len(out["items"]), round(time.time() - t, 1), "queries", sum(stats.values()))
    for it in out["items"][:3]:
        print(it["player_name"], it["eligibility"]["eligible"], it["eligibility"]["reasons"])
for k, v in sorted(timing.items(), key=lambda x: -x[1])[:8]:
    print(round(v, 2), stats[k], k)

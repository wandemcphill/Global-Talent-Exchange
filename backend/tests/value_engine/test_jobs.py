from datetime import datetime, timezone
import unittest

from backend.app.ingestion.models import CompetitionContext, NormalizedMatchEvent
from backend.app.value_engine.jobs import InMemoryValueSnapshotRepository, ValueSnapshotJob
from backend.app.value_engine.models import DemandSignal, PlayerValueInput, ScoutingSignal


class ValueSnapshotJobTests(unittest.TestCase):
    def test_job_builds_and_persists_snapshots_for_each_player(self) -> None:
        competition = CompetitionContext(competition_id="league-a", name="League A", stage="regular season")
        repository = InMemoryValueSnapshotRepository(
            inputs={
                "p-1": PlayerValueInput(
                    player_id="p-1",
                    player_name="Ada Forward",
                    as_of=datetime(2026, 3, 6, tzinfo=timezone.utc),
                    reference_market_value_eur=70_000_000,
                    current_credits=710.0,
                    match_events=(
                        NormalizedMatchEvent(
                            source="provider_a",
                            source_event_id="m1:p1",
                            match_id="match-1",
                            player_id="p-1",
                            player_name="Ada Forward",
                            team_id="a",
                            team_name="Alpha",
                            opponent_id="b",
                            opponent_name="Beta",
                            competition=competition,
                            occurred_at=datetime(2026, 3, 5, 20, 0, tzinfo=timezone.utc),
                            minutes=90,
                            rating=8.0,
                            goals=1,
                            assists=1,
                            started=True,
                            won_match=True,
                        ),
                    ),
                    demand_signal=DemandSignal(purchases=4, shortlist_adds=10, follows=25),
                    scouting_signal=ScoutingSignal(shortlist_adds=10, watchlist_adds=25, scouting_activity=4),
                ),
                "p-2": PlayerValueInput(
                    player_id="p-2",
                    player_name="Kai Creator",
                    as_of=datetime(2026, 3, 6, tzinfo=timezone.utc),
                    reference_market_value_eur=25_000_000,
                    current_credits=250.0,
                    demand_signal=DemandSignal(watchlist_adds=20, follows=50),
                    scouting_signal=ScoutingSignal(watchlist_adds=20, transfer_room_adds=5),
                ),
            }
        )

        job = ValueSnapshotJob()
        snapshots = job.run(repository, as_of=datetime(2026, 3, 6, tzinfo=timezone.utc))

        self.assertEqual(len(snapshots), 2)
        self.assertEqual(len(repository.saved_snapshots), 2)
        self.assertEqual([snapshot.player_id for snapshot in snapshots], ["p-1", "p-2"])
        self.assertTrue(all(snapshot.target_credits > 0 for snapshot in snapshots))
        self.assertTrue(all(snapshot.football_truth_value_credits > 0 for snapshot in snapshots))
        self.assertTrue(all(snapshot.market_signal_value_credits > 0 for snapshot in snapshots))
        self.assertTrue(all(snapshot.global_scouting_index >= 0 for snapshot in snapshots))


if __name__ == "__main__":
    unittest.main()

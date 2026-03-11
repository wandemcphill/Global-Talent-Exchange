from datetime import datetime, timezone
import unittest

from backend.app.ingestion.models import CompetitionContext, NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent
from backend.app.value_engine.models import DemandSignal, PlayerValueInput
from backend.app.value_engine.scoring import ValueEngine, credits_from_real_world_value


class ValueEngineScoringTests(unittest.TestCase):
    def test_baseline_conversion_keeps_100m_to_1000_rule(self) -> None:
        self.assertEqual(credits_from_real_world_value(100_000_000), 1000.0)
        self.assertEqual(credits_from_real_world_value(75_000_000), 750.0)

    def test_snapshot_combines_major_match_award_transfer_and_demand(self) -> None:
        engine = ValueEngine()
        competition = CompetitionContext(competition_id="wc", name="World Cup", stage="final")
        snapshot = engine.build_snapshot(
            PlayerValueInput(
                player_id="p-1",
                player_name="Ada Forward",
                as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
                reference_market_value_eur=90_000_000,
                current_credits=880.0,
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
                        occurred_at=datetime(2026, 3, 1, 20, 0, tzinfo=timezone.utc),
                        minutes=90,
                        rating=9.2,
                        goals=1,
                        assists=0,
                        won_match=True,
                        won_final=True,
                        big_moment=True,
                        started=True,
                    ),
                ),
                transfer_events=(
                    NormalizedTransferEvent(
                        source="transfer_wire",
                        source_event_id="tx-1",
                        player_id="p-1",
                        player_name="Ada Forward",
                        occurred_at=datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc),
                        from_club="Alpha",
                        to_club="Galacticos",
                        from_competition="League A",
                        to_competition="UEFA Club Championship",
                        reported_fee_eur=110_000_000,
                        status="completed",
                    ),
                ),
                award_events=(
                    NormalizedAwardEvent(
                        source="awards_feed",
                        source_event_id="award-1",
                        player_id="p-1",
                        player_name="Ada Forward",
                        occurred_at=datetime(2026, 3, 4, 9, 0, tzinfo=timezone.utc),
                        award_code="ballon_dor_top_3",
                        award_name="Ballon dOr",
                        rank=3,
                    ),
                ),
                demand_signal=DemandSignal(
                    purchases=12,
                    sales=4,
                    shortlist_adds=30,
                    watchlist_adds=60,
                    follows=100,
                    suspicious_purchases=2,
                    suspicious_watchlist_adds=10,
                ),
            )
        )

        self.assertGreater(snapshot.target_credits, snapshot.previous_credits)
        self.assertIn("big_moment", snapshot.drivers)
        self.assertLessEqual(snapshot.breakdown.capped_adjustment_pct, 0.12)

    def test_demand_ignores_suspicious_activity_and_caps_movement(self) -> None:
        engine = ValueEngine()
        snapshot = engine.build_snapshot(
            PlayerValueInput(
                player_id="p-2",
                player_name="Kai Creator",
                as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
                reference_market_value_eur=40_000_000,
                current_credits=400.0,
                demand_signal=DemandSignal(
                    purchases=100,
                    sales=100,
                    shortlist_adds=80,
                    watchlist_adds=250,
                    follows=500,
                    suspicious_purchases=95,
                    suspicious_sales=95,
                    suspicious_shortlist_adds=70,
                    suspicious_watchlist_adds=240,
                    suspicious_follows=490,
                ),
            )
        )

        self.assertLessEqual(snapshot.breakdown.demand_adjustment_pct, 0.05)
        self.assertGreater(snapshot.target_credits, 0.0)


if __name__ == "__main__":
    unittest.main()

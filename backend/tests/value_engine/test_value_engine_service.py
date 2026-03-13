from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock

from backend.app.ingestion.models import MarketSignal
from backend.app.value_engine.service import IngestionValueSnapshotRepository


class IngestionValueSnapshotRepositoryTests(unittest.TestCase):
    def test_build_market_pulse_parses_trade_prints_and_holder_signals(self) -> None:
        repository = IngestionValueSnapshotRepository(session=MagicMock())
        as_of = datetime(2026, 3, 6, tzinfo=timezone.utc)
        window_start = datetime(2026, 3, 1, tzinfo=timezone.utc)
        market_signals = [
            MarketSignal(
                id="sig-1",
                source_provider="synthetic",
                provider_external_id="trade-1",
                player_id="player-1",
                signal_type="trade_print_price_credits",
                score=512.0,
                as_of=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 10, 1, tzinfo=timezone.utc),
                notes='{"seller_user_id":"seller-1","buyer_user_id":"buyer-1","quantity":2}',
            ),
            MarketSignal(
                id="sig-2",
                source_provider="synthetic",
                provider_external_id="trade-2",
                player_id="player-1",
                signal_type="shadow_ignored_trade_print_price_credits",
                score=780.0,
                as_of=datetime(2026, 3, 5, 11, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 11, 1, tzinfo=timezone.utc),
                notes='{"seller_user_id":"seller-2","buyer_user_id":"buyer-2","shadow_ignored":true}',
            ),
            MarketSignal(
                id="sig-3",
                source_provider="synthetic",
                provider_external_id="holders",
                player_id="player-1",
                signal_type="holder_count",
                score=14.0,
                as_of=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 12, 1, tzinfo=timezone.utc),
            ),
            MarketSignal(
                id="sig-4",
                source_provider="synthetic",
                provider_external_id="top-holder",
                player_id="player-1",
                signal_type="top_holder_share_pct",
                score=42.0,
                as_of=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 12, 2, tzinfo=timezone.utc),
            ),
            MarketSignal(
                id="sig-5",
                source_provider="synthetic",
                provider_external_id="top-3-holders",
                player_id="player-1",
                signal_type="top_3_holder_share_pct",
                score=74.0,
                as_of=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 12, 3, tzinfo=timezone.utc),
            ),
        ]

        market_pulse = repository._build_market_pulse(
            market_signals,
            window_start=window_start,
            as_of=as_of,
        )

        self.assertEqual(len(market_pulse.trade_prints), 2)
        self.assertEqual(market_pulse.trade_prints[0].quantity, 2)
        self.assertTrue(market_pulse.trade_prints[1].shadow_ignored)
        self.assertEqual(market_pulse.holder_count, 14)
        self.assertAlmostEqual(market_pulse.top_holder_share_pct or 0.0, 0.42, places=4)
        self.assertAlmostEqual(market_pulse.top_3_holder_share_pct or 0.0, 0.74, places=4)

    def test_build_egame_signal_aggregates_aliases(self) -> None:
        repository = IngestionValueSnapshotRepository(session=MagicMock())
        as_of = datetime(2026, 3, 6, tzinfo=timezone.utc)
        window_start = datetime(2026, 3, 1, tzinfo=timezone.utc)
        market_signals = [
            MarketSignal(
                id="sig-egame-1",
                source_provider="synthetic",
                provider_external_id="egame-1",
                player_id="player-1",
                signal_type="competition_selection_count",
                score=44.0,
                as_of=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 10, 1, tzinfo=timezone.utc),
            ),
            MarketSignal(
                id="sig-egame-2",
                source_provider="synthetic",
                provider_external_id="egame-2",
                player_id="player-1",
                signal_type="boost_selection_count",
                score=7.0,
                as_of=datetime(2026, 3, 5, 10, 5, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 10, 6, tzinfo=timezone.utc),
            ),
            MarketSignal(
                id="sig-egame-3",
                source_provider="synthetic",
                provider_external_id="egame-3",
                player_id="player-1",
                signal_type="suspicious_egame_selection_count",
                score=5.0,
                as_of=datetime(2026, 3, 5, 11, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 3, 5, 11, 1, tzinfo=timezone.utc),
            ),
        ]

        egame_signal = repository._build_egame_signal(
            market_signals,
            window_start=window_start,
            as_of=as_of,
        )

        self.assertEqual(egame_signal.selection_count, 44)
        self.assertEqual(egame_signal.captain_count, 7)
        self.assertEqual(egame_signal.suspicious_selection_count, 5)


if __name__ == "__main__":
    unittest.main()

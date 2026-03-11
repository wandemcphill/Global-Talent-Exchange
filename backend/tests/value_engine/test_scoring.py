from dataclasses import replace
from datetime import datetime, timezone
import unittest

from backend.app.core.config import PriceBandLimit
from backend.app.ingestion.models import CompetitionContext, NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent
from backend.app.value_engine.models import DemandSignal, MarketPulse, PlayerValueInput, ScoutingSignal, TradePrint
from backend.app.value_engine.scoring import ValueEngine, credits_from_real_world_value


class ValueEngineScoringTests(unittest.TestCase):
    def test_baseline_conversion_keeps_100m_to_1000_rule(self) -> None:
        self.assertEqual(credits_from_real_world_value(100_000_000), 1000.0)
        self.assertEqual(credits_from_real_world_value(75_000_000), 750.0)

    def test_snapshot_combines_football_truth_market_signal_and_published_layers(self) -> None:
        engine = ValueEngine()
        competition = CompetitionContext(competition_id="wc", name="World Cup", stage="final")
        snapshot = engine.build_snapshot(
            PlayerValueInput(
                player_id="p-1",
                player_name="Ada Forward",
                as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
                reference_market_value_eur=90_000_000,
                current_credits=880.0,
                previous_ftv_credits=870.0,
                previous_pcv_credits=880.0,
                previous_gsi_score=52.0,
                liquidity_band="marquee",
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
                scouting_signal=ScoutingSignal(
                    shortlist_adds=30,
                    watchlist_adds=60,
                    transfer_room_adds=8,
                    scouting_activity=12,
                    suspicious_watchlist_adds=10,
                ),
                market_pulse=MarketPulse(
                    midpoint_price_credits=940.0,
                    best_bid_price_credits=930.0,
                    best_ask_price_credits=950.0,
                ),
            )
        )

        self.assertGreater(snapshot.football_truth_value_credits, 0.0)
        self.assertGreater(snapshot.market_signal_value_credits, snapshot.football_truth_value_credits)
        self.assertGreater(snapshot.target_credits, snapshot.previous_credits)
        self.assertEqual(snapshot.published_card_value_credits, snapshot.target_credits)
        self.assertGreater(snapshot.global_scouting_index, snapshot.previous_global_scouting_index)
        self.assertIn("big_moment", snapshot.drivers)
        self.assertIn("global_scouting_index", snapshot.drivers)
        self.assertIn("market_snapshot", snapshot.drivers)
        self.assertLessEqual(snapshot.breakdown.capped_adjustment_pct, 0.12)

    def test_low_liquidity_players_stay_closer_to_ftv_than_high_liquidity_players(self) -> None:
        engine = ValueEngine()
        payload = dict(
            player_id="p-2",
            player_name="Kai Creator",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=40_000_000,
            current_credits=400.0,
            previous_ftv_credits=400.0,
            previous_pcv_credits=400.0,
            demand_signal=DemandSignal(purchases=18, shortlist_adds=50, follows=90),
            market_pulse=MarketPulse(midpoint_price_credits=520.0),
        )

        low_liquidity = engine.build_snapshot(PlayerValueInput(liquidity_band="entry", **payload))
        high_liquidity = engine.build_snapshot(PlayerValueInput(liquidity_band="marquee", **payload))

        low_gap = abs(low_liquidity.market_signal_value_credits - low_liquidity.football_truth_value_credits)
        high_gap = abs(high_liquidity.market_signal_value_credits - high_liquidity.football_truth_value_credits)

        self.assertLess(low_gap, high_gap)
        self.assertLessEqual(low_liquidity.breakdown.liquidity_weight, high_liquidity.breakdown.liquidity_weight)
        self.assertLess(low_liquidity.target_credits, high_liquidity.target_credits)

    def test_published_card_value_moves_toward_market_signal_value_from_previous_snapshot(self) -> None:
        engine = ValueEngine()
        snapshot = engine.build_snapshot(
            PlayerValueInput(
                player_id="p-3",
                player_name="Mina Anchor",
                as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
                reference_market_value_eur=55_000_000,
                current_credits=540.0,
                previous_ftv_credits=520.0,
                previous_pcv_credits=500.0,
                liquidity_band="premium",
                demand_signal=DemandSignal(purchases=10, watchlist_adds=35, follows=70),
                market_pulse=MarketPulse(midpoint_price_credits=640.0),
            )
        )

        self.assertGreater(snapshot.market_signal_value_credits, snapshot.previous_credits)
        self.assertGreater(snapshot.target_credits, snapshot.previous_credits)
        self.assertLess(snapshot.target_credits, snapshot.market_signal_value_credits)
        self.assertAlmostEqual(snapshot.breakdown.capped_adjustment_pct * engine.config.smoothing_factor, snapshot.movement_pct, places=4)

    def test_last_trade_signal_is_not_used_as_naive_price_input(self) -> None:
        engine = ValueEngine()
        base_payload = PlayerValueInput(
            player_id="p-4",
            player_name="Noah Steady",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=35_000_000,
            current_credits=350.0,
            previous_ftv_credits=350.0,
            previous_pcv_credits=350.0,
            liquidity_band="marquee",
        )

        with_last_trade = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(last_trade_price_credits=900.0),
            )
        )
        without_last_trade = engine.build_snapshot(base_payload)

        self.assertEqual(with_last_trade.market_signal_value_credits, without_last_trade.market_signal_value_credits)
        self.assertEqual(with_last_trade.target_credits, without_last_trade.target_credits)
        self.assertIn("last_trade_ignored", with_last_trade.drivers)

    def test_scouting_index_moves_without_pulling_card_price_with_it(self) -> None:
        engine = ValueEngine()
        base_payload = PlayerValueInput(
            player_id="p-5",
            player_name="Iris Scout",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=50_000_000,
            current_credits=500.0,
            previous_ftv_credits=500.0,
            previous_pcv_credits=500.0,
            previous_gsi_score=45.0,
            liquidity_band="premium",
        )

        quiet_snapshot = engine.build_snapshot(base_payload)
        scouting_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                scouting_signal=ScoutingSignal(
                    watchlist_adds=80,
                    shortlist_adds=35,
                    transfer_room_adds=14,
                    scouting_activity=10,
                ),
            )
        )

        self.assertEqual(quiet_snapshot.target_credits, scouting_snapshot.target_credits)
        self.assertGreater(scouting_snapshot.global_scouting_index, quiet_snapshot.global_scouting_index)
        self.assertGreater(scouting_snapshot.global_scouting_index_movement_pct, quiet_snapshot.global_scouting_index_movement_pct)

    def test_card_price_can_move_without_dragging_gsi_with_it(self) -> None:
        engine = ValueEngine()
        scouting_signal = ScoutingSignal(watchlist_adds=20, shortlist_adds=8, transfer_room_adds=3, scouting_activity=4)
        base_payload = PlayerValueInput(
            player_id="p-6",
            player_name="Omar Market",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=48_000_000,
            current_credits=480.0,
            previous_ftv_credits=480.0,
            previous_pcv_credits=480.0,
            previous_gsi_score=54.0,
            liquidity_band="marquee",
            scouting_signal=scouting_signal,
        )

        neutral_snapshot = engine.build_snapshot(base_payload)
        price_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                demand_signal=DemandSignal(purchases=12, sales=4),
                market_pulse=MarketPulse(midpoint_price_credits=560.0),
            )
        )

        self.assertGreater(price_snapshot.target_credits, neutral_snapshot.target_credits)
        self.assertEqual(price_snapshot.global_scouting_index, neutral_snapshot.global_scouting_index)
        self.assertEqual(
            price_snapshot.global_scouting_index_movement_pct,
            neutral_snapshot.global_scouting_index_movement_pct,
        )

    def test_gsi_can_move_faster_than_pcv(self) -> None:
        engine = ValueEngine()
        snapshot = engine.build_snapshot(
            PlayerValueInput(
                player_id="p-7",
                player_name="Rhea Tracker",
                as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
                reference_market_value_eur=52_000_000,
                current_credits=520.0,
                previous_ftv_credits=520.0,
                previous_pcv_credits=520.0,
                previous_gsi_score=50.0,
                liquidity_band="growth",
                demand_signal=DemandSignal(purchases=3, sales=1),
                market_pulse=MarketPulse(midpoint_price_credits=540.0),
                scouting_signal=ScoutingSignal(
                    watchlist_adds=120,
                    shortlist_adds=60,
                    transfer_room_adds=18,
                    scouting_activity=22,
                ),
            )
        )

        self.assertGreater(snapshot.global_scouting_index_movement_pct, snapshot.movement_pct)
        self.assertGreater(snapshot.global_scouting_index, snapshot.previous_global_scouting_index)

    def test_shadow_ignored_wash_trades_do_not_move_price(self) -> None:
        engine = ValueEngine()
        base_payload = PlayerValueInput(
            player_id="p-8",
            player_name="Lena Signal",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=50_000_000,
            current_credits=500.0,
            previous_ftv_credits=500.0,
            previous_pcv_credits=500.0,
            liquidity_band="marquee",
        )

        neutral_snapshot = engine.build_snapshot(base_payload)
        suspicious_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    trade_prints=(
                        TradePrint(
                            trade_id="wash-1",
                            seller_user_id="alpha",
                            buyer_user_id="bravo",
                            price_credits=820.0,
                            occurred_at=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
                            shadow_ignored=True,
                        ),
                        TradePrint(
                            trade_id="wash-2",
                            seller_user_id="bravo",
                            buyer_user_id="alpha",
                            price_credits=822.0,
                            occurred_at=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
                            shadow_ignored=True,
                        ),
                    ),
                ),
            )
        )

        self.assertEqual(suspicious_snapshot.target_credits, neutral_snapshot.target_credits)
        self.assertEqual(suspicious_snapshot.market_signal_value_credits, neutral_snapshot.market_signal_value_credits)
        self.assertEqual(suspicious_snapshot.breakdown.shadow_ignored_trade_count, 2)
        self.assertEqual(suspicious_snapshot.breakdown.wash_trade_count, 2)
        self.assertEqual(suspicious_snapshot.breakdown.trusted_trade_count, 0)
        self.assertTrue(suspicious_snapshot.breakdown.thin_market)
        self.assertIn("shadow_ignored_trades", suspicious_snapshot.drivers)
        self.assertIn("wash_trade_detected", suspicious_snapshot.drivers)

    def test_wash_trades_reduce_market_pull_vs_clean_market(self) -> None:
        engine = ValueEngine()
        base_payload = PlayerValueInput(
            player_id="p-9",
            player_name="Tariq Market",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=50_000_000,
            current_credits=500.0,
            previous_ftv_credits=500.0,
            previous_pcv_credits=500.0,
            liquidity_band="marquee",
            demand_signal=DemandSignal(purchases=10, follows=35),
        )

        clean_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    midpoint_price_credits=650.0,
                    trade_prints=(
                        TradePrint(
                            trade_id="clean-1",
                            seller_user_id="u1",
                            buyer_user_id="u2",
                            price_credits=640.0,
                            occurred_at=datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="clean-2",
                            seller_user_id="u3",
                            buyer_user_id="u4",
                            price_credits=644.0,
                            occurred_at=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="clean-3",
                            seller_user_id="u5",
                            buyer_user_id="u6",
                            price_credits=647.0,
                            occurred_at=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
                        ),
                    ),
                    holder_count=28,
                    top_holder_share_pct=0.11,
                    top_3_holder_share_pct=0.29,
                ),
            )
        )
        wash_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    midpoint_price_credits=650.0,
                    trade_prints=(
                        TradePrint(
                            trade_id="wash-1",
                            seller_user_id="ring-a",
                            buyer_user_id="ring-b",
                            price_credits=648.0,
                            occurred_at=datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="wash-2",
                            seller_user_id="ring-b",
                            buyer_user_id="ring-a",
                            price_credits=650.0,
                            occurred_at=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
                        ),
                    ),
                    holder_count=28,
                    top_holder_share_pct=0.11,
                    top_3_holder_share_pct=0.29,
                ),
            )
        )

        self.assertGreater(clean_snapshot.target_credits, wash_snapshot.target_credits)
        self.assertGreater(clean_snapshot.breakdown.trade_trust_score, wash_snapshot.breakdown.trade_trust_score)
        self.assertGreater(
            clean_snapshot.breakdown.anti_manipulation_guard_multiplier,
            wash_snapshot.breakdown.anti_manipulation_guard_multiplier,
        )
        self.assertEqual(wash_snapshot.breakdown.wash_trade_count, 2)
        self.assertTrue(wash_snapshot.breakdown.thin_market)

    def test_circular_trades_are_ignored_from_trusted_trade_price(self) -> None:
        engine = ValueEngine()
        base_payload = PlayerValueInput(
            player_id="p-10",
            player_name="Juno Loop",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=50_000_000,
            current_credits=500.0,
            previous_ftv_credits=500.0,
            previous_pcv_credits=500.0,
            liquidity_band="premium",
        )

        trusted_only_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    trade_prints=(
                        TradePrint(
                            trade_id="trusted-1",
                            seller_user_id="real-a",
                            buyer_user_id="real-b",
                            price_credits=530.0,
                            occurred_at=datetime(2026, 3, 5, 13, 0, tzinfo=timezone.utc),
                        ),
                    ),
                ),
            )
        )
        circular_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    trade_prints=(
                        TradePrint(
                            trade_id="trusted-1",
                            seller_user_id="real-a",
                            buyer_user_id="real-b",
                            price_credits=530.0,
                            occurred_at=datetime(2026, 3, 5, 13, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="cycle-1",
                            seller_user_id="c1",
                            buyer_user_id="c2",
                            price_credits=700.0,
                            occurred_at=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="cycle-2",
                            seller_user_id="c2",
                            buyer_user_id="c3",
                            price_credits=702.0,
                            occurred_at=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="cycle-3",
                            seller_user_id="c3",
                            buyer_user_id="c1",
                            price_credits=701.0,
                            occurred_at=datetime(2026, 3, 5, 11, 0, tzinfo=timezone.utc),
                        ),
                    ),
                ),
            )
        )

        self.assertLess(circular_snapshot.target_credits, trusted_only_snapshot.target_credits)
        self.assertEqual(circular_snapshot.breakdown.snapshot_market_price_credits, 530.0)
        self.assertEqual(circular_snapshot.breakdown.trusted_trade_price_credits, 530.0)
        self.assertEqual(circular_snapshot.breakdown.circular_trade_count, 3)
        self.assertIn("circular_trade_detected", circular_snapshot.drivers)

    def test_holder_concentration_penalty_and_thin_market_dampen_market_signal(self) -> None:
        engine = ValueEngine()
        base_payload = PlayerValueInput(
            player_id="p-11",
            player_name="Nia Float",
            as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
            reference_market_value_eur=50_000_000,
            current_credits=500.0,
            previous_ftv_credits=500.0,
            previous_pcv_credits=500.0,
            liquidity_band="marquee",
            demand_signal=DemandSignal(purchases=8, follows=40),
        )

        deep_market_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    midpoint_price_credits=560.0,
                    trade_prints=(
                        TradePrint(
                            trade_id="deep-1",
                            seller_user_id="d1",
                            buyer_user_id="d2",
                            price_credits=558.0,
                            occurred_at=datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="deep-2",
                            seller_user_id="d3",
                            buyer_user_id="d4",
                            price_credits=561.0,
                            occurred_at=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
                        ),
                        TradePrint(
                            trade_id="deep-3",
                            seller_user_id="d5",
                            buyer_user_id="d6",
                            price_credits=559.0,
                            occurred_at=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
                        ),
                    ),
                    holder_count=36,
                    top_holder_share_pct=0.12,
                    top_3_holder_share_pct=0.31,
                ),
            )
        )
        concentrated_snapshot = engine.build_snapshot(
            replace(
                base_payload,
                market_pulse=MarketPulse(
                    midpoint_price_credits=560.0,
                    trade_prints=(
                        TradePrint(
                            trade_id="thin-1",
                            seller_user_id="x1",
                            buyer_user_id="x2",
                            price_credits=560.0,
                            occurred_at=datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc),
                        ),
                    ),
                    holder_count=4,
                    top_holder_share_pct=0.55,
                    top_3_holder_share_pct=0.95,
                ),
            )
        )

        self.assertGreater(deep_market_snapshot.target_credits, concentrated_snapshot.target_credits)
        self.assertGreater(
            concentrated_snapshot.breakdown.holder_concentration_penalty_pct,
            0.0,
        )
        self.assertTrue(concentrated_snapshot.breakdown.thin_market)
        self.assertIn("holder_concentration_penalty", concentrated_snapshot.drivers)
        self.assertIn("thin_market", concentrated_snapshot.drivers)

    def test_price_band_limits_cap_blended_target_when_market_signal_runs_hot(self) -> None:
        base_engine = ValueEngine()
        engine = ValueEngine(
            config=replace(
                base_engine.config,
                ftv_weight=0.0,
                msv_weight=1.0,
                price_band_limits=(
                    PriceBandLimit(code="default", min_ratio=0.80, max_ratio=1.20),
                    PriceBandLimit(code="entry", min_ratio=0.95, max_ratio=1.05),
                ),
            )
        )
        snapshot = engine.build_snapshot(
            PlayerValueInput(
                player_id="p-12",
                player_name="Band Guard",
                as_of=datetime(2026, 3, 5, tzinfo=timezone.utc),
                reference_market_value_eur=40_000_000,
                current_credits=400.0,
                previous_ftv_credits=400.0,
                previous_pcv_credits=400.0,
                liquidity_band="entry",
                demand_signal=DemandSignal(purchases=20, follows=80),
                market_pulse=MarketPulse(midpoint_price_credits=640.0),
            )
        )

        self.assertGreater(snapshot.market_signal_value_credits, snapshot.breakdown.price_band_ceiling_credits)
        self.assertEqual(snapshot.breakdown.band_limited_target_credits, snapshot.breakdown.price_band_ceiling_credits)
        self.assertLessEqual(snapshot.target_credits, snapshot.breakdown.price_band_ceiling_credits)
        self.assertIn("price_band_guard", snapshot.drivers)


if __name__ == "__main__":
    unittest.main()

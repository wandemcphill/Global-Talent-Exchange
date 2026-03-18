from __future__ import annotations

import ast
from pathlib import Path
from sqlalchemy import create_engine, inspect, text

from backend.app.core.config import BACKEND_ROOT
from backend.app.core.database import ensure_database_schema_current


def _migration_graph_heads() -> set[str]:
    versions_dir = BACKEND_ROOT / "migrations" / "versions"
    revisions: set[str] = set()
    down_revisions: set[str] = set()

    for path in versions_dir.glob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        revision: str | None = None
        down_revision: str | tuple[str, ...] | None = None
        for node in module.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "revision":
                    revision = ast.literal_eval(node.value)
                elif target.id == "down_revision":
                    down_revision = ast.literal_eval(node.value)
        if revision is None:
            continue
        revisions.add(revision)
        if isinstance(down_revision, str):
            down_revisions.add(down_revision)
        elif isinstance(down_revision, tuple):
            down_revisions.update(item for item in down_revision if item)

    heads = revisions - down_revisions
    assert len(heads) == 1
    return heads


def test_persistence_migrations_create_expected_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'persistence-migrations.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    ensure_database_schema_current(engine)

    inspector = inspect(engine)
    assert inspector.has_table("club_reputation_profile")
    assert inspector.has_table("reputation_event_log")
    assert inspector.has_table("reputation_snapshot")
    assert inspector.has_table("league_event_records")
    assert inspector.has_table("replay_archive_records")
    assert inspector.has_table("replay_archive_countdowns")
    assert inspector.has_table("fast_cup_records")
    assert inspector.has_table("card_loan_listings")
    assert inspector.has_table("card_loan_contracts")
    assert inspector.has_table("starter_squad_rentals")
    assert inspector.has_table("sponsor_offers")
    assert inspector.has_table("sponsor_offer_rules")
    assert inspector.has_table("club_sponsors")
    assert inspector.has_table("highlight_share_templates")
    assert inspector.has_table("highlight_share_exports")
    assert inspector.has_table("highlight_share_amplifications")
    assert inspector.has_table("creator_league_configs")
    assert inspector.has_table("creator_league_tiers")
    assert inspector.has_table("creator_league_seasons")
    assert inspector.has_table("creator_league_season_tiers")
    assert inspector.has_table("creator_broadcast_mode_configs")
    assert inspector.has_table("creator_broadcast_purchases")
    assert inspector.has_table("creator_season_passes")
    assert inspector.has_table("creator_match_gift_events")
    assert inspector.has_table("creator_stadium_controls")
    assert inspector.has_table("creator_stadium_profiles")
    assert inspector.has_table("creator_stadium_pricing")
    assert inspector.has_table("creator_stadium_ticket_purchases")
    assert inspector.has_table("creator_stadium_placements")
    assert inspector.has_table("creator_revenue_settlements")
    assert inspector.has_table("creator_club_share_market_controls")
    assert inspector.has_table("creator_club_share_markets")
    assert inspector.has_table("creator_club_share_holdings")
    assert inspector.has_table("creator_club_share_purchases")
    assert inspector.has_table("creator_club_share_distributions")
    assert inspector.has_table("creator_club_share_payouts")
    assert inspector.has_table("club_valuation_snapshots")
    assert inspector.has_table("club_sale_listings")
    assert inspector.has_table("club_sale_inquiries")
    assert inspector.has_table("club_sale_offers")
    assert inspector.has_table("club_sale_transfers")
    assert inspector.has_table("club_sale_audit_events")
    assert inspector.has_table("creator_match_chat_rooms")
    assert inspector.has_table("creator_match_chat_messages")
    assert inspector.has_table("creator_match_tactical_advice")
    assert inspector.has_table("creator_club_follows")
    assert inspector.has_table("creator_fan_groups")
    assert inspector.has_table("creator_fan_group_memberships")
    assert inspector.has_table("creator_fan_competitions")
    assert inspector.has_table("creator_fan_competition_entries")
    assert inspector.has_table("creator_fan_wall_events")
    assert inspector.has_table("creator_rivalry_signal_outputs")
    assert inspector.has_table("fan_prediction_fixtures")
    assert inspector.has_table("fan_prediction_outcomes")
    assert inspector.has_table("fan_prediction_submissions")
    assert inspector.has_table("fan_prediction_token_ledger")
    assert inspector.has_table("fan_prediction_reward_grants")
    assert inspector.has_table("fan_war_profiles")
    assert inspector.has_table("fan_war_points")
    assert inspector.has_table("country_creator_assignments")
    assert inspector.has_table("nations_cup_entries")
    assert inspector.has_table("nations_cup_fan_metrics")
    assert inspector.has_table("fanbase_rankings")
    assert inspector.has_table("streamer_tournament_policies")
    assert inspector.has_table("streamer_tournaments")
    assert inspector.has_table("streamer_tournament_invites")
    assert inspector.has_table("streamer_tournament_entries")
    assert inspector.has_table("streamer_tournament_rewards")
    assert inspector.has_table("streamer_tournament_risk_signals")
    assert inspector.has_table("streamer_tournament_reward_grants")
    assert inspector.has_table("card_loan_negotiations")
    assert inspector.has_table("card_swap_listings")
    assert inspector.has_table("card_swap_executions")
    assert inspector.has_table("card_marketplace_audit_events")

    creator_league_config_columns = {column["name"] for column in inspector.get_columns("creator_league_configs")}
    assert {
        "broadcast_purchases_enabled",
        "season_pass_sales_enabled",
        "match_gifting_enabled",
        "settlement_review_enabled",
        "settlement_review_total_revenue_coin",
        "settlement_review_creator_share_coin",
        "settlement_review_platform_share_coin",
        "settlement_review_shareholder_distribution_coin",
    } <= creator_league_config_columns

    creator_share_market_control_columns = {
        column["name"] for column in inspector.get_columns("creator_club_share_market_controls")
    }
    assert {
        "issuance_enabled",
        "purchase_enabled",
        "max_primary_purchase_value_coin",
    } <= creator_share_market_control_columns

    creator_stadium_control_columns = {column["name"] for column in inspector.get_columns("creator_stadium_controls")}
    assert {
        "ticket_sales_enabled",
        "max_placement_price_coin",
    } <= creator_stadium_control_columns

    creator_revenue_settlement_columns = {column["name"] for column in inspector.get_columns("creator_revenue_settlements")}
    assert {
        "review_status",
        "review_reason_codes_json",
        "policy_snapshot_json",
        "reviewed_by_user_id",
        "reviewed_at",
        "review_note",
    } <= creator_revenue_settlement_columns

    player_card_listing_columns = {column["name"] for column in inspector.get_columns("player_card_listings")}
    assert "is_negotiable" in player_card_listing_columns

    loan_listing_columns = {column["name"] for column in inspector.get_columns("card_loan_listings")}
    assert {"is_negotiable", "borrower_rights_json", "lender_restrictions_json"} <= loan_listing_columns

    loan_contract_columns = {column["name"] for column in inspector.get_columns("card_loan_contracts")}
    assert {
        "accepted_negotiation_id",
        "requested_loan_fee_credits",
        "platform_fee_credits",
        "lender_net_credits",
        "platform_fee_bps",
        "fee_floor_applied",
        "loan_duration_days",
        "accepted_at",
        "settled_at",
        "settlement_reference",
        "accepted_terms_json",
        "borrower_rights_json",
        "lender_rights_json",
        "lender_restrictions_json",
    } <= loan_contract_columns

    club_sale_listing_columns = {column["name"] for column in inspector.get_columns("club_sale_listings")}
    assert {
        "listing_id",
        "club_id",
        "seller_user_id",
        "asking_price",
        "valuation_snapshot_id",
        "system_valuation_minor",
        "valuation_breakdown_json",
        "note",
    } <= club_sale_listing_columns

    club_sale_inquiry_columns = {column["name"] for column in inspector.get_columns("club_sale_inquiries")}
    assert {
        "inquiry_id",
        "club_id",
        "listing_id",
        "seller_user_id",
        "buyer_user_id",
        "message",
        "response_message",
    } <= club_sale_inquiry_columns

    club_sale_offer_columns = {column["name"] for column in inspector.get_columns("club_sale_offers")}
    assert {
        "offer_id",
        "club_id",
        "listing_id",
        "inquiry_id",
        "parent_offer_id",
        "seller_user_id",
        "buyer_user_id",
        "proposer_user_id",
        "counterparty_user_id",
        "offered_price",
        "responded_message",
    } <= club_sale_offer_columns

    club_sale_transfer_columns = {column["name"] for column in inspector.get_columns("club_sale_transfers")}
    assert {
        "transfer_id",
        "club_id",
        "listing_id",
        "offer_id",
        "valuation_snapshot_id",
        "seller_user_id",
        "buyer_user_id",
        "executed_sale_price",
        "platform_fee_amount",
        "seller_net_amount",
        "platform_fee_bps",
        "settlement_reference",
        "ledger_transaction_id",
    } <= club_sale_transfer_columns

    club_sale_audit_columns = {column["name"] for column in inspector.get_columns("club_sale_audit_events")}
    assert {
        "club_id",
        "listing_id",
        "inquiry_id",
        "offer_id",
        "transfer_id",
        "actor_user_id",
        "action",
        "status_from",
        "status_to",
        "payload_json",
    } <= club_sale_audit_columns

    with engine.connect() as connection:
        versions = connection.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()

    target_heads = _migration_graph_heads()
    assert len(versions) == 1
    assert set(versions) == target_heads

    engine.dispose()

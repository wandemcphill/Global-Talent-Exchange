from __future__ import annotations

import ast
from pathlib import Path
from sqlalchemy import create_engine, inspect, text

from app.core.config import BACKEND_ROOT
from app.core.database import ensure_database_schema_current


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
    assert inspector.has_table("match_events")
    assert inspector.has_table("competition_queue_records")
    assert inspector.has_table("player_faces")
    assert inspector.has_table("commentary_events")
    assert inspector.has_table("event_outbox")
    assert inspector.has_table("projection_event_receipts")
    assert inspector.has_table("competition_standing_projections")
    assert inspector.has_table("player_stats_projections")
    assert inspector.has_table("manager_profiles")
    assert inspector.has_table("manager_contracts")
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
    assert inspector.has_table("real_data_providers")
    assert inspector.has_table("real_world_competitions")
    assert inspector.has_table("real_world_clubs")
    assert inspector.has_table("real_players")
    assert inspector.has_table("reality_mode_settings")
    assert inspector.has_table("real_data_sync_jobs")
    assert inspector.has_table("federations")
    assert inspector.has_table("federation_leagues")
    assert inspector.has_table("federation_memberships")
    assert inspector.has_table("federation_proposals")
    assert inspector.has_table("federation_votes")
    assert inspector.has_table("federation_sanctions")
    assert inspector.has_table("federation_treasury_entries")
    assert inspector.has_table("federation_narrative_snapshots")
    assert inspector.has_table("federation_rule_audits")
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
    assert inspector.has_table("real_player_import_batches")
    assert inspector.has_table("real_player_import_rows")
    assert inspector.has_table("real_player_import_staging")
    assert inspector.has_table("real_player_reference_mappings")
    assert inspector.has_table("real_player_unresolved_references")
    assert inspector.has_table("real_player_value_lineages")
    assert inspector.has_table("real_player_source_links")
    assert inspector.has_table("real_player_profiles")
    assert inspector.has_table("spectator_sessions")
    assert inspector.has_table("highlight_events")
    assert inspector.has_table("manager_duels")
    assert inspector.has_table("manager_duel_profiles")
    assert inspector.has_table("predictions")
    assert inspector.has_table("club_finance_profiles")
    assert inspector.has_table("club_finance_sponsors")
    assert inspector.has_table("club_finance_transactions")
    assert inspector.has_table("broadcast_rights")
    assert inspector.has_table("broadcast_rights_auctions")
    assert inspector.has_table("broadcast_rights_bids")
    assert inspector.has_table("broadcast_access_grants")
    assert inspector.has_table("view_sessions")
    assert inspector.has_table("broadcast_revenue_distributions")
    assert inspector.has_table("ownership_groups")
    assert inspector.has_table("ownership_group_clubs")
    assert inspector.has_table("ownership_group_budget_movements")
    assert inspector.has_table("ownership_group_events")
    assert inspector.has_table("player_relationships")
    assert inspector.has_table("transfer_listings")
    assert inspector.has_table("transfer_listing_bids")
    assert inspector.has_table("player_decision_profiles")
    assert inspector.has_table("coach_profiles")
    assert inspector.has_table("coach_demands")
    assert inspector.has_table("player_coach_relationships")
    assert inspector.has_table("club_team_dynamics")
    assert inspector.has_table("market_watchlist_entries")
    assert inspector.has_table("transfer_negotiations")
    assert inspector.has_table("season_passes")
    assert inspector.has_table("season_pass_claims")
    assert inspector.has_table("season_pass_xp_grants")
    assert inspector.has_table("live_events")

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

    real_player_import_batch_columns = {column["name"] for column in inspector.get_columns("real_player_import_batches")}
    assert {
        "batch_key",
        "provider_name",
        "provider_job_key",
        "source_type",
        "mode",
        "status",
        "requested_at",
        "submitted_row_count",
        "normalized_row_count",
        "matched_existing_count",
        "created_player_count",
        "updated_player_count",
        "authoritative_snapshot_count",
        "metadata_json",
        "summary_json",
    } <= real_player_import_batch_columns

    real_player_import_row_columns = {column["name"] for column in inspector.get_columns("real_player_import_rows")}
    assert {
        "batch_id",
        "row_number",
        "source_name",
        "source_player_key",
        "canonical_name",
        "status",
        "match_action",
        "import_action",
        "gtex_player_id",
        "source_link_id",
        "real_player_profile_id",
        "authoritative_snapshot_id",
        "player_import_item_id",
        "exact_identity_key",
        "name_birthyear_club_key",
        "name_birthyear_nationality_key",
        "secondary_position_keys_json",
        "raw_payload_json",
        "normalized_payload_json",
        "candidate_players_json",
        "review_status",
        "audit_findings_json",
    } <= real_player_import_row_columns

    real_player_import_staging_columns = {column["name"] for column in inspector.get_columns("real_player_import_staging")}
    assert {
        "provider_name",
        "provider_player_id",
        "provider_club_id",
        "provider_competition_id",
        "provider_season_id",
        "full_name",
        "import_state",
        "last_import_cursor",
        "source_payload_hash",
        "last_import_run_id",
        "latest_payload_json",
        "metadata_json",
    } <= real_player_import_staging_columns

    real_player_reference_mapping_columns = {
        column["name"] for column in inspector.get_columns("real_player_reference_mappings")
    }
    assert {
        "source_name",
        "entity_type",
        "provider_external_id",
        "provider_reference_key",
        "normalized_label",
        "canonical_country_id",
        "canonical_competition_id",
        "canonical_club_id",
        "mapping_status",
        "resolution_method",
        "confidence_score",
        "is_active",
        "metadata_json",
    } <= real_player_reference_mapping_columns

    real_player_unresolved_reference_columns = {
        column["name"] for column in inspector.get_columns("real_player_unresolved_references")
    }
    assert {
        "source_name",
        "entity_type",
        "provider_external_id",
        "provider_reference_key",
        "normalized_label",
        "reason_code",
        "status",
        "occurrence_count",
        "first_seen_at",
        "last_seen_at",
        "resolved_at",
        "canonical_country_id",
        "canonical_competition_id",
        "canonical_club_id",
        "sample_payload_json",
        "metadata_json",
    } <= real_player_unresolved_reference_columns

    real_player_value_lineage_columns = {column["name"] for column in inspector.get_columns("real_player_value_lineages")}
    assert {
        "player_id",
        "snapshot_id",
        "as_of",
        "snapshot_type",
        "config_version",
        "adapter_code",
        "adapter_version",
        "source_reference_tier",
        "source_market_value_eur",
        "bridge_market_value_eur",
        "base_value_credits",
        "floor_credits",
        "ceiling_credits",
        "inputs_json",
        "components_json",
        "explanation_json",
    } <= real_player_value_lineage_columns

    real_player_profile_indexes = {index["name"] for index in inspector.get_indexes("real_player_profiles")}
    assert {
        "ix_real_player_profiles_batch_id",
        "ix_real_player_profiles_pricing_snapshot_id",
    } <= real_player_profile_indexes

    real_player_import_row_indexes = {index["name"] for index in inspector.get_indexes("real_player_import_rows")}
    assert {
        "ix_real_player_import_rows_batch_status",
        "ix_real_player_import_rows_exact_identity_key",
        "ix_real_player_import_rows_review_status",
    } <= real_player_import_row_indexes

    real_player_reference_mapping_indexes = {
        index["name"] for index in inspector.get_indexes("real_player_reference_mappings")
    }
    assert {
        "ix_real_player_reference_mappings_entity_type",
        "ix_real_player_reference_mappings_status",
        "ix_real_player_reference_mappings_provider_external_id",
    } <= real_player_reference_mapping_indexes

    real_player_value_lineage_indexes = {
        index["name"] for index in inspector.get_indexes("real_player_value_lineages")
    }
    assert {
        "ix_real_player_value_lineages_player_id",
        "ix_real_player_value_lineages_snapshot_id",
        "ix_real_player_value_lineages_snapshot_type",
    } <= real_player_value_lineage_indexes

    player_columns = {column["name"] for column in inspector.get_columns("ingestion_players")}
    assert "morale" in player_columns

    prediction_columns = {column["name"] for column in inspector.get_columns("predictions")}
    assert {
        "user_id",
        "match_id",
        "predicted_outcome",
        "confidence_level",
        "reward_earned",
        "difficulty_multiplier",
        "actual_outcome",
        "resolved_at",
    } <= prediction_columns

    finance_profile_columns = {column["name"] for column in inspector.get_columns("club_finance_profiles")}
    assert {
        "user_id",
        "balance",
        "weekly_wages",
        "sponsorship_income",
        "match_income",
        "broadcast_income",
        "transfer_profit",
        "expenses",
        "transfers_blocked",
        "forced_sale_required",
        "forced_sale_player_id",
    } <= finance_profile_columns

    broadcast_right_columns = {column["name"] for column in inspector.get_columns("broadcast_rights")}
    assert {
        "competition_id",
        "owner_id",
        "acquisition_price",
        "revenue_share_percentage",
        "exclusivity",
        "start_date",
        "end_date",
        "metadata_json",
    } <= broadcast_right_columns

    broadcast_auction_columns = {column["name"] for column in inspector.get_columns("broadcast_rights_auctions")}
    assert {
        "competition_id",
        "seller_owner_id",
        "reserve_price",
        "revenue_share_percentage",
        "exclusivity",
        "start_date",
        "end_date",
        "starts_at",
        "ends_at",
        "status",
        "winning_right_id",
        "metadata_json",
    } <= broadcast_auction_columns

    view_session_columns = {column["name"] for column in inspector.get_columns("view_sessions")}
    assert {
        "user_id",
        "match_id",
        "competition_id",
        "paid_amount",
        "timestamp",
        "metadata_json",
    } <= view_session_columns

    broadcast_distribution_columns = {
        column["name"] for column in inspector.get_columns("broadcast_revenue_distributions")
    }
    assert {
        "match_id",
        "competition_id",
        "broadcast_right_id",
        "recipient_type",
        "recipient_id",
        "amount",
        "reference_key",
        "processed_at",
        "metadata_json",
    } <= broadcast_distribution_columns

    ownership_group_columns = {column["name"] for column in inspector.get_columns("ownership_groups")}
    assert {
        "owner_user_id",
        "name",
        "clubs_json",
        "budget_pool",
        "reputation_score",
        "philosophy",
        "global_brand_strength",
        "shared_budget_enabled",
        "metadata_json",
    } <= ownership_group_columns

    ownership_group_club_columns = {column["name"] for column in inspector.get_columns("ownership_group_clubs")}
    assert {"group_id", "club_id", "metadata_json"} <= ownership_group_club_columns

    ownership_group_budget_columns = {
        column["name"] for column in inspector.get_columns("ownership_group_budget_movements")
    }
    assert {
        "group_id",
        "source_club_id",
        "target_club_id",
        "movement_type",
        "amount",
        "reference_key",
        "created_by_user_id",
        "metadata_json",
    } <= ownership_group_budget_columns

    ownership_group_event_columns = {column["name"] for column in inspector.get_columns("ownership_group_events")}
    assert {"group_id", "event_type", "headline", "impact_json", "metadata_json"} <= ownership_group_event_columns

    sponsor_columns = {column["name"] for column in inspector.get_columns("club_finance_sponsors")}
    assert {"name", "tier", "payout", "requirements_json", "active"} <= sponsor_columns

    season_pass_columns = {column["name"] for column in inspector.get_columns("season_passes")}
    assert {"user_id", "season_id", "tier", "xp", "level", "rewards_json"} <= season_pass_columns

    live_event_columns = {column["name"] for column in inspector.get_columns("live_events")}
    assert {"name", "start_date", "end_date", "rules_json", "rewards_json", "started_notification_sent_at"} <= live_event_columns

    competition_queue_columns = {column["name"] for column in inspector.get_columns("competition_queue_records")}
    assert {
        "queue_name",
        "job_name",
        "idempotency_key",
        "aggregate_id",
        "partition_key",
        "status",
        "published_at",
        "payload_json",
        "metadata_json",
    } <= competition_queue_columns

    event_outbox_columns = {column["name"] for column in inspector.get_columns("event_outbox")}
    assert {
        "event_id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "partition_key",
        "producer",
        "version",
        "occurred_at",
        "payload_json",
        "headers_json",
        "status",
        "processed_at",
        "relay_attempts",
        "last_error",
    } <= event_outbox_columns

    projection_receipt_columns = {column["name"] for column in inspector.get_columns("projection_event_receipts")}
    assert {
        "projection_name",
        "event_id",
        "event_type",
        "aggregate_id",
        "metadata_json",
    } <= projection_receipt_columns

    standing_projection_columns = {column["name"] for column in inspector.get_columns("competition_standing_projections")}
    assert {
        "competition_id",
        "season_id",
        "competition_type",
        "club_id",
        "club_name",
        "matches_played",
        "wins",
        "draws",
        "losses",
        "goals_for",
        "goals_against",
        "goal_difference",
        "points",
        "last_fixture_id",
    } <= standing_projection_columns

    player_projection_columns = {column["name"] for column in inspector.get_columns("player_stats_projections")}
    assert {
        "competition_id",
        "season_id",
        "competition_type",
        "player_id",
        "player_name",
        "team_id",
        "team_name",
        "appearances",
        "starts",
        "minutes_played",
        "goals",
        "assists",
        "saves",
        "yellow_cards",
        "red_cards",
        "wins",
        "draws",
        "losses",
        "cumulative_xg",
        "average_rating",
        "rating_samples",
        "last_fixture_id",
    } <= player_projection_columns

    with engine.connect() as connection:
        versions = connection.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()

    target_heads = _migration_graph_heads()
    assert len(versions) == 1
    assert set(versions) == target_heads

    engine.dispose()

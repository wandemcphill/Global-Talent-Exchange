"""Remove remaining pre-launch test accounts, test clubs, and seeded competitions.

Revision ID: 20261116_0256_remove_test_accounts_and_seeded_owner_competitions
Revises: 20261116_0255_optional_trader_recovery_credentials
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0256_remove_test_accounts_and_seeded_owner_competitions"
down_revision = "20261116_0255_optional_trader_recovery_credentials"
branch_labels = None
depends_on = None

_CLEANUP_SQL = """
DO $$
DECLARE
    v_test_emails TEXT[] := ARRAY[
        'gtex.clubowner.jul01@gmail.com',
        'gtex.trader.jul01@gmail.com',
        'gtex.creator.jul01@gmail.com',
        'ayotest9921@example.com'
    ];
    v_test_club_slugs TEXT[] := ARRAY['lagos-marlins-fc', 'ayomide-test-fc'];
    v_seeded_comp_names TEXT[] := ARRAY[
        'GTEX Lagos Launch Cup',
        'Naija Rising Stars League',
        'Weekend Knockout Shield'
    ];
    v_user_ids TEXT[];
    v_club_ids TEXT[];
    v_org_ids TEXT[];
    v_comp_ids TEXT[];
    v_nt_entry_ids TEXT[];
    v_wallet_ids TEXT[];
    v_tx_ids TEXT[];
    v_affected_system_wallet_ids TEXT[];
    v_creator_profile_ids TEXT[];
    v_has_append_only_trigger BOOLEAN;
BEGIN
    SELECT COALESCE(ARRAY_AGG(id::TEXT), ARRAY[]::TEXT[])
    INTO v_user_ids
    FROM users
    WHERE lower(email) = ANY(v_test_emails);

    SELECT COALESCE(ARRAY_AGG(id::TEXT), ARRAY[]::TEXT[])
    INTO v_club_ids
    FROM club_profiles
    WHERE owner_user_id = ANY(v_user_ids)
       OR lower(slug) = ANY(v_test_club_slugs);

    SELECT COALESCE(ARRAY_AGG(id::TEXT), ARRAY[]::TEXT[])
    INTO v_org_ids
    FROM organizations
    WHERE club_profile_id = ANY(v_club_ids);

    SELECT COALESCE(ARRAY_AGG(id::TEXT), ARRAY[]::TEXT[])
    INTO v_creator_profile_ids
    FROM creator_profiles
    WHERE user_id = ANY(v_user_ids);

    SELECT COALESCE(ARRAY_AGG(id::TEXT), ARRAY[]::TEXT[])
    INTO v_comp_ids
    FROM owner_competitions
    WHERE (host_type = 'gtex' AND name = ANY(v_seeded_comp_names))
       OR host_user_id = ANY(v_user_ids);

    SELECT COALESCE(ARRAY_AGG(nte.id::TEXT), ARRAY[]::TEXT[])
    INTO v_nt_entry_ids
    FROM national_team_entries AS nte
    JOIN national_team_competitions AS ntc ON ntc.id = nte.competition_id
    LEFT JOIN users AS u ON u.id = nte.entry_owner_user_id
    WHERE nte.entry_owner_user_id = ANY(v_user_ids)
       OR (
           nte.squad_size = 0
           AND (
               (lower(u.email) = 'vidvimedialtd@gmail.com' AND ntc.key = 'gtex-afcon')
               OR (lower(u.email) = 'fliptrybe.ng@gmail.com' AND ntc.key = 'gtex-u17-asian-cup')
           )
       );

    SELECT COALESCE(ARRAY_AGG(w.id::TEXT), ARRAY[]::TEXT[])
    INTO v_wallet_ids
    FROM wallets AS w
    WHERE w.owner_user_id = ANY(v_user_ids)
       OR EXISTS (
           SELECT 1
           FROM unnest(v_club_ids) AS cid
           WHERE w.code = 'club:' || cid
              OR w.code LIKE 'club:' || cid || ':%'
       )
       OR EXISTS (
           SELECT 1
           FROM unnest(v_comp_ids) AS comp_id
           WHERE w.code = 'competition:' || comp_id
              OR w.code LIKE 'competition:' || comp_id || ':%'
       );

    SELECT COALESCE(ARRAY_AGG(DISTINCT tx_id), ARRAY[]::TEXT[])
    INTO v_tx_ids
    FROM (
        SELECT le.transaction_id::TEXT AS tx_id
        FROM ledger_entries AS le
        WHERE le.account_id = ANY(v_wallet_ids)
           OR le.created_by_user_id = ANY(v_user_ids)
        UNION
        SELECT t.id::TEXT AS tx_id
        FROM transactions AS t
        WHERE t.created_by_user_id = ANY(v_user_ids)
    ) AS tx_union;

    SELECT COALESCE(ARRAY_AGG(DISTINCT le.account_id::TEXT), ARRAY[]::TEXT[])
    INTO v_affected_system_wallet_ids
    FROM ledger_entries AS le
    WHERE le.transaction_id = ANY(v_tx_ids)
      AND NOT (le.account_id = ANY(v_wallet_ids));

    -- 1. Clean un-FK'd owner_console and tournament tables.
    DELETE FROM owner_matches
    WHERE competition_id = ANY(v_comp_ids)
       OR home_club_id = ANY(v_club_ids)
       OR away_club_id = ANY(v_club_ids);

    DELETE FROM owner_competition_entries
    WHERE competition_id = ANY(v_comp_ids)
       OR club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_competitions
    WHERE id = ANY(v_comp_ids);

    DELETE FROM owner_ledger_events
    WHERE club_id = ANY(v_club_ids)
       OR user_id = ANY(v_user_ids)
       OR (related_object_type = 'competition' AND related_object_id = ANY(v_comp_ids));

    DELETE FROM owner_inbox_items
    WHERE user_id = ANY(v_user_ids)
       OR club_id = ANY(v_club_ids);

    DELETE FROM owner_squad_players
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_deposit_intents
    WHERE user_id = ANY(v_user_ids);

    DELETE FROM owner_withdrawals
    WHERE user_id = ANY(v_user_ids);

    DELETE FROM owner_integrity_flags
    WHERE user_id = ANY(v_user_ids)
       OR club_id = ANY(v_club_ids)
       OR related_object_id = ANY(v_comp_ids);

    DELETE FROM owner_related_party_transfers
    WHERE owner_user_id = ANY(v_user_ids)
       OR from_club_id = ANY(v_club_ids)
       OR to_club_id = ANY(v_club_ids);

    DELETE FROM owner_sponsor_deals
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_support_units
    WHERE user_id = ANY(v_user_ids)
       OR club_id = ANY(v_club_ids);

    DELETE FROM owner_broadcast_events
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_showroom_assets
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_newsroom_articles
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_scouting_watchlists
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_events
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_relationships
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_relationship_history
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_directives
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_delegated_decisions
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids)
       OR decided_by_user_id = ANY(v_user_ids);

    DELETE FROM owner_club_decision_audit_logs
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_delegation_policies
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_club_messages
    WHERE club_id = ANY(v_club_ids)
       OR sender_user_id = ANY(v_user_ids)
       OR conversation_id IN (
           SELECT id
           FROM owner_club_conversations
           WHERE club_id = ANY(v_club_ids)
              OR owner_user_id = ANY(v_user_ids)
       );

    DELETE FROM owner_club_conversations
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_club_meetings
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids)
       OR created_by_user_id = ANY(v_user_ids);

    DELETE FROM owner_club_announcements
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids)
       OR published_by_user_id = ANY(v_user_ids);

    DELETE FROM owner_staff_decision_records
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_recruitment_assignments
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_states
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_supporter_profiles
    WHERE club_id = ANY(v_club_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM owner_supporter_segments
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_supporter_events
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_media_stories
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_history_entries
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_season_archives
    WHERE club_id = ANY(v_club_ids)
       OR competition_id = ANY(v_comp_ids);

    DELETE FROM owner_club_managerial_tenures
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_transfer_records
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_academy_graduates
    WHERE club_id = ANY(v_club_ids);

    DELETE FROM owner_club_rivalries
    WHERE club_id = ANY(v_club_ids)
       OR rival_club_id = ANY(v_club_ids);

    -- 2. Clean empty October test national_team_entries (preserving kept active squads).
    DELETE FROM national_team_competition_entries AS ntce
    WHERE ntce.user_id = ANY(v_user_ids)
       OR EXISTS (
           SELECT 1
           FROM national_team_entries AS nte
           WHERE nte.id = ANY(v_nt_entry_ids)
             AND nte.competition_id = ntce.competition_id
             AND nte.entry_owner_user_id = ntce.user_id
       );

    DELETE FROM national_team_rental_contracts
    WHERE entry_id = ANY(v_nt_entry_ids)
       OR user_id = ANY(v_user_ids);

    DELETE FROM national_team_entries
    WHERE id = ANY(v_nt_entry_ids);

    -- 3. Remove test ledger entries, transactions, and wallets atomically.
    DELETE FROM payout_requests
    WHERE account_id = ANY(v_wallet_ids)
       OR user_id = ANY(v_user_ids)
       OR hold_transaction_id = ANY(v_tx_ids)
       OR settlement_transaction_id = ANY(v_tx_ids);

    UPDATE payment_events
    SET ledger_transaction_id = NULL
    WHERE ledger_transaction_id = ANY(v_tx_ids);

    UPDATE creator_marketplace_participations
    SET wallet_transaction_id = NULL
    WHERE wallet_transaction_id = ANY(v_tx_ids);

    UPDATE ledger_balance_projections
    SET last_transaction_id = NULL
    WHERE last_transaction_id = ANY(v_tx_ids);

    SELECT EXISTS (
        SELECT 1
        FROM pg_trigger AS t
        JOIN pg_class AS c ON c.oid = t.tgrelid
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = current_schema()
          AND c.relname = 'ledger_entries'
          AND t.tgname = 'trg_ledger_entries_append_only'
          AND NOT t.tgisinternal
    )
    INTO v_has_append_only_trigger;

    IF v_has_append_only_trigger THEN
        EXECUTE 'ALTER TABLE ledger_entries DISABLE TRIGGER trg_ledger_entries_append_only';
    END IF;

    BEGIN
        DELETE FROM ledger_entries
        WHERE transaction_id = ANY(v_tx_ids)
           OR account_id = ANY(v_wallet_ids);
    EXCEPTION
        WHEN OTHERS THEN
            IF v_has_append_only_trigger THEN
                EXECUTE 'ALTER TABLE ledger_entries ENABLE TRIGGER trg_ledger_entries_append_only';
            END IF;
            RAISE;
    END;

    IF v_has_append_only_trigger THEN
        EXECUTE 'ALTER TABLE ledger_entries ENABLE TRIGGER trg_ledger_entries_append_only';
    END IF;

    UPDATE ledger_balance_projections AS lbp
    SET balance = COALESCE(
            (
                SELECT SUM(le.amount)
                FROM ledger_entries AS le
                WHERE le.account_id = lbp.account_id
            ),
            0.0000
        ),
        last_transaction_id = (
            SELECT le.transaction_id
            FROM ledger_entries AS le
            WHERE le.account_id = lbp.account_id
            ORDER BY le.created_at DESC, le.id DESC
            LIMIT 1
        )
    WHERE lbp.account_id = ANY(v_affected_system_wallet_ids);

    DELETE FROM ledger_balance_projections
    WHERE account_id = ANY(v_wallet_ids)
       OR owner_user_id = ANY(v_user_ids);

    DELETE FROM transactions
    WHERE id = ANY(v_tx_ids);

    DELETE FROM wallets
    WHERE id = ANY(v_wallet_ids);

    -- 4. Clean RESTRICT references and telemetry/audit logs tied to test accounts.
    DELETE FROM advertiser_refund_records
    WHERE approved_by_user_id = ANY(v_user_ids);

    DELETE FROM brand_ad_review_events
    WHERE actor_user_id = ANY(v_user_ids);

    DELETE FROM fraud_cases
    WHERE user_id = ANY(v_user_ids)
       OR assigned_admin_user_id = ANY(v_user_ids)
       OR resolved_by_user_id = ANY(v_user_ids);

    DELETE FROM system_events
    WHERE created_by_user_id = ANY(v_user_ids)
       OR (
           subject_type IN ('user', 'club', 'club_profile', 'owner_competition', 'national_team_entry')
           AND subject_id = ANY(v_user_ids || v_club_ids || v_comp_ids || v_nt_entry_ids)
       );

    DELETE FROM analytics_events
    WHERE user_id = ANY(v_user_ids);

    DELETE FROM risk_signals
    WHERE user_id = ANY(v_user_ids);

    DELETE FROM audit_logs
    WHERE actor_user_id = ANY(v_user_ids)
       OR (
           resource_type IN ('user', 'club', 'club_profile', 'owner_competition', 'organization', 'national_team_entry')
           AND resource_id = ANY(v_user_ids || v_club_ids || v_comp_ids || v_org_ids || v_nt_entry_ids)
       );

    DELETE FROM access_audit_logs
    WHERE actor_user_id = ANY(v_user_ids)
       OR target_user_id = ANY(v_user_ids)
       OR organization_id = ANY(v_org_ids);

    DELETE FROM player_share_events
    WHERE user_id = ANY(v_user_ids)
       OR actor_user_id = ANY(v_user_ids);

    DELETE FROM share_codes
    WHERE owner_user_id = ANY(v_user_ids)
       OR owner_creator_id = ANY(v_creator_profile_ids)
       OR lower(code) = 'zaracreates';

    DELETE FROM referral_rewards
    WHERE referred_user_id = ANY(v_user_ids)
       OR beneficiary_user_id = ANY(v_user_ids)
       OR beneficiary_creator_id = ANY(v_creator_profile_ids);

    DELETE FROM referral_events
    WHERE referred_user_id = ANY(v_user_ids)
       OR referrer_user_id = ANY(v_user_ids)
       OR creator_profile_id = ANY(v_creator_profile_ids);

    DELETE FROM referral_attributions
    WHERE referred_user_id = ANY(v_user_ids)
       OR referrer_user_id = ANY(v_user_ids)
       OR creator_profile_id = ANY(v_creator_profile_ids);

    -- 5. Remove test organizations, clubs, and users (cascading dependent user tables).
    DELETE FROM organizations
    WHERE id = ANY(v_org_ids);

    DELETE FROM club_profiles
    WHERE id = ANY(v_club_ids);

    DELETE FROM users
    WHERE id = ANY(v_user_ids);
END
$$;
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(sa.text(_CLEANUP_SQL))


def downgrade() -> None:
    # Permanent removal of pre-launch test users, test clubs, and seeded competitions.
    pass

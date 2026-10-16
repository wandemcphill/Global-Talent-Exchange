import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/competition_models.dart';

void main() {
  test('parses backend-style competition summary payload', () {
    final CompetitionSummary summary = CompetitionSummary.fromJson(
      <String, Object?>{
        'id': 'ugc-900',
        'name': 'Precision Skill League',
        'format': 'league',
        'visibility': 'public',
        'status': 'open_for_join',
        'creator_id': 'creator-9',
        'creator_name': 'Creator Nine',
        'participant_count': 7,
        'capacity': 12,
        'currency': 'credit',
        'entry_fee': 15,
        'platform_fee_pct': 0.10,
        'host_fee_pct': 0.05,
        'platform_fee_amount': 10.5,
        'host_fee_amount': 5.25,
        'prize_pool': 89.25,
        'payout_structure': <Map<String, Object?>>[
          <String, Object?>{'place': 1, 'percent': 0.5, 'amount': 44.625},
          <String, Object?>{'place': 2, 'percent': 0.3, 'amount': 26.775},
          <String, Object?>{'place': 3, 'percent': 0.2, 'amount': 17.85},
        ],
        'rules_summary': 'Published rules summary',
        'join_eligibility': <String, Object?>{
          'eligible': true,
          'reason': null,
          'requires_invite': false,
        },
        'beginner_friendly': true,
        'created_at': '2026-03-11T12:00:00Z',
        'updated_at': '2026-03-12T12:00:00Z',
      },
    );

    expect(summary.id, 'ugc-900');
    expect(summary.isLeague, isTrue);
    expect(summary.entryFee, 15);
    expect(summary.platformFeePct, 0.10);
    expect(summary.hostFeePct, 0.05);
    expect(summary.payoutStructure, hasLength(3));
    expect(summary.joinEligibility.eligible, isTrue);
    expect(summary.beginnerFriendly, isTrue);
  });

  test('parses nested financial payload variation', () {
    final CompetitionSummary summary = CompetitionSummary.fromJson(
      <String, Object?>{
        'id': 'ugc-901',
        'name': 'Creator Cup',
        'format': 'cup',
        'visibility': 'invite_only',
        'status': 'filled',
        'creatorId': 'creator-10',
        'creatorName': 'Creator Ten',
        'participantCount': 16,
        'capacity': 16,
        'financials': <String, Object?>{
          'currency': 'credit',
          'entry_fee': 20,
          'platform_fee_pct': 0.10,
          'host_fee_pct': 0.02,
          'platform_fee_amount': 32,
          'host_fee_amount': 6.4,
          'prize_pool': 281.6,
          'payout_structure': <Map<String, Object?>>[
            <String, Object?>{'place': 1, 'percent': 0.65, 'amount': 183.04},
            <String, Object?>{'place': 2, 'percent': 0.35, 'amount': 98.56},
          ],
        },
        'rulesSummary': 'Invite-only rules summary',
        'joinEligibility': <String, Object?>{
          'eligible': false,
          'reason': 'competition_full',
          'requiresInvite': true,
        },
        'createdAt': '2026-03-10T12:00:00Z',
        'updatedAt': '2026-03-12T13:00:00Z',
      },
    );

    expect(summary.isCup, isTrue);
    expect(summary.visibility, CompetitionVisibility.inviteOnly);
    expect(summary.status, CompetitionStatus.filled);
    expect(summary.prizePool, 281.6);
    expect(summary.joinEligibility.reason, 'competition_full');
    expect(summary.joinEligibility.requiresInvite, isTrue);
  });

  test('parses Fast Match entitlement and Fast Cup escrow metadata', () {
    final CompetitionSummary summary = CompetitionSummary.fromJson(
      <String, Object?>{
        'id': 'fast-cup-1',
        'name': 'Fast Cup Flash',
        'format': 'cup',
        'visibility': 'public',
        'status': 'open_for_join',
        'creator_id': 'gtex-fastlane',
        'creator_name': 'GTEX Fast Lane',
        'participant_count': 0,
        'capacity': 8,
        'currency': 'credit',
        'entry_fee': 12,
        'platform_fee_pct': 0.10,
        'host_fee_pct': 0.02,
        'prize_pool': 0,
        'match_type': 'fast_match',
        'fast_match_entitlement': <String, Object?>{
          'free_matches_remaining': 7,
          'free_matches_used': 3,
          'charge_on_loss': true,
          'charge_required_now': false,
          'entry_currency': 'credit',
          'entry_currency_label': 'Fan Coin',
          'fan_coin_entry_fee': 12,
          'entitlement_status': 'free_run',
        },
        'fast_cup_registration': <String, Object?>{
          'registration_id': 'registration-1',
          'escrow_status': 'escrowed',
          'entry_fee_amount': 12,
          'entry_fee_currency': 'credit',
          'wallet_ledger_id': 'ledger-1',
        },
        'join_eligibility': <String, Object?>{'eligible': true},
        'created_at': '2026-05-16T12:00:00Z',
        'updated_at': '2026-05-16T12:00:00Z',
      },
    );

    expect(summary.isFastMatch, isTrue);
    expect(summary.fastMatchEntitlement!.freeMatchesRemaining, 7);
    expect(summary.fastMatchEntitlement!.entryCurrencyLabel, 'Fan Coin');
    expect(summary.economyNotice, contains('Server entitlement'));
    expect(summary.fastCupRegistration!.isEscrowBacked, isTrue);
    expect(summary.fastCupRegistration!.entryFeeLabel, '12 Fan Coin');
  });

  test('parses quick-game response as Fast Match start metadata', () {
    final FastMatchEntitlementView entitlement =
        FastMatchEntitlementView.fromJson(<String, Object?>{
          'match_id': 'match-1',
          'live_match_key': 'live-1',
          'viewer_route': '/match-viewer/live-1',
          'free_matches_remaining': 0,
          'free_matches_used': 10,
          'charge_on_loss': true,
          'charge_required_now': true,
          'entry_currency': 'credit',
          'entry_currency_label': 'Fan Coin',
          'fan_coin_entry_fee': 12,
          'entitlement_status': 'paid_required',
          'settlement_status': 'pending',
        });

    expect(entitlement.liveMatchKey, 'live-1');
    expect(entitlement.chargeRequiredNow, isTrue);
    expect(entitlement.entryFeeLabel, '12 Fan Coin');
  });
}

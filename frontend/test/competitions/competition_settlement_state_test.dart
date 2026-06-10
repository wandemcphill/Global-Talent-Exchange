import 'package:test/test.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/compete/domain/competition_bracket_models.dart';

void main() {
  group('competition settlement state parsing', () {
    test('completed competition without settlement readiness renders degraded', () {
      final CompetitionSummary summary = CompetitionSummary.fromJson(
        <String, Object?>{
          'id': 'settle-1',
          'name': 'Settled Cup',
          'format': 'cup',
          'visibility': 'public',
          'status': 'completed',
          'lifecycle': <String, Object?>{
            'stage': 'completed',
            'bracket_published': true,
          },
          'creator_id': 'host-1',
          'creator_name': 'Host One',
          'participant_count': 8,
          'capacity': 8,
          'currency': 'credit',
          'entry_fee': 10,
          'platform_fee_pct': 0.10,
          'host_fee_pct': 0.03,
          'platform_fee_amount': 8.0,
          'host_fee_amount': 2.4,
          'prize_pool': 69.6,
          'payout_structure': <Object?>[
            <String, Object?>{'place': 1, 'percent': 0.6, 'amount': 41.76},
            <String, Object?>{'place': 2, 'percent': 0.4, 'amount': 27.84},
          ],
          'rules_summary': 'Settlement state test',
          'join_eligibility': <String, Object?>{'eligible': false},
          'beginner_friendly': false,
          'created_at': '2026-01-01T00:00:00Z',
          'updated_at': '2026-06-10T00:00:00Z',
        },
      );

      expect(summary.status, CompetitionStatus.completed);
      expect(summary.lifecycle?.stage, CompetitionLifecycleStage.completed);
      expect(summary.lifecycle?.isTerminal, isTrue);
      expect(summary.lifecycle?.isLive, isFalse);
    });

    test('settlement_ready lifecycle stage round-trips as scheduled variant', () {
      final CompetitionSummary summary = CompetitionSummary.fromJson(
        <String, Object?>{
          'id': 'settle-2',
          'name': 'Pre-settle Cup',
          'format': 'cup',
          'visibility': 'public',
          'status': 'completed',
          'lifecycle': <String, Object?>{
            'stage': 'settlement_ready',
          },
          'creator_id': 'host-2',
          'creator_name': 'Host Two',
          'participant_count': 4,
          'capacity': 4,
          'currency': 'credit',
          'entry_fee': 5,
          'platform_fee_pct': 0.10,
          'host_fee_pct': 0.0,
          'platform_fee_amount': 2.0,
          'host_fee_amount': 0.0,
          'prize_pool': 18.0,
          'payout_structure': <Object?>[
            <String, Object?>{'place': 1, 'percent': 1.0, 'amount': 18.0},
          ],
          'rules_summary': 'Settlement ready test',
          'join_eligibility': <String, Object?>{'eligible': false},
          'beginner_friendly': false,
          'created_at': '2026-01-01T00:00:00Z',
          'updated_at': '2026-06-10T00:00:00Z',
        },
      );

      // settlement_ready maps to completed — the competition has ended and awaits payout
      expect(summary.lifecycle?.rawStage, 'settlement_ready');
      expect(summary.lifecycle?.stage, CompetitionLifecycleStage.completed);
      expect(summary.lifecycle?.isTerminal, isTrue);
    });

    test('missing lifecycle block renders null lifecycle without fabricating stage', () {
      final CompetitionSummary summary = CompetitionSummary.fromJson(
        <String, Object?>{
          'id': 'settle-3',
          'name': 'No Lifecycle Cup',
          'format': 'cup',
          'visibility': 'public',
          'status': 'completed',
          'creator_id': 'host-3',
          'creator_name': 'Host Three',
          'participant_count': 2,
          'capacity': 2,
          'currency': 'credit',
          'entry_fee': 0,
          'platform_fee_pct': 0,
          'host_fee_pct': 0,
          'platform_fee_amount': 0,
          'host_fee_amount': 0,
          'prize_pool': 0,
          'payout_structure': const <Object?>[],
          'rules_summary': 'No lifecycle test',
          'join_eligibility': <String, Object?>{'eligible': false},
          'beginner_friendly': false,
          'created_at': '2026-01-01T00:00:00Z',
          'updated_at': '2026-06-10T00:00:00Z',
        },
      );

      // Must be null, not a fabricated fallback stage
      expect(summary.lifecycle, isNull);
      expect(summary.status, CompetitionStatus.completed);
    });

    test('disputed competition lifecycle stage renders correctly', () {
      final CompetitionSummary summary = CompetitionSummary.fromJson(
        <String, Object?>{
          'id': 'settle-4',
          'name': 'Disputed Cup',
          'format': 'cup',
          'visibility': 'public',
          'status': 'completed',
          'lifecycle': <String, Object?>{
            'stage': 'disputed',
            'blocked_reason': 'Backend-reported dispute under review.',
          },
          'creator_id': 'host-4',
          'creator_name': 'Host Four',
          'participant_count': 4,
          'capacity': 4,
          'currency': 'credit',
          'entry_fee': 5,
          'platform_fee_pct': 0.10,
          'host_fee_pct': 0.0,
          'platform_fee_amount': 2.0,
          'host_fee_amount': 0.0,
          'prize_pool': 18.0,
          'payout_structure': <Object?>[
            <String, Object?>{'place': 1, 'percent': 1.0, 'amount': 18.0},
          ],
          'rules_summary': 'Disputed state test',
          'join_eligibility': <String, Object?>{'eligible': false},
          'beginner_friendly': false,
          'created_at': '2026-01-01T00:00:00Z',
          'updated_at': '2026-06-10T00:00:00Z',
        },
      );

      expect(summary.lifecycle?.stage, CompetitionLifecycleStage.disputed);
      // disputed is not in the terminal set (completed/cancelled/refunded) —
      // the backend may still resolve it without inventing the terminal outcome.
      expect(summary.lifecycle?.isTerminal, isFalse);
      expect(
        summary.lifecycle?.blockedReason,
        'Backend-reported dispute under review.',
      );
    });

    test('refunded competition lifecycle marks terminal without inventing payout data', () {
      final CompetitionSummary summary = CompetitionSummary.fromJson(
        <String, Object?>{
          'id': 'settle-5',
          'name': 'Refunded Cup',
          'format': 'cup',
          'visibility': 'public',
          'status': 'cancelled',
          'lifecycle': <String, Object?>{'stage': 'refunded'},
          'creator_id': 'host-5',
          'creator_name': 'Host Five',
          'participant_count': 2,
          'capacity': 8,
          'currency': 'credit',
          'entry_fee': 5,
          'platform_fee_pct': 0,
          'host_fee_pct': 0,
          'platform_fee_amount': 0,
          'host_fee_amount': 0,
          'prize_pool': 0,
          'payout_structure': const <Object?>[],
          'rules_summary': 'Refunded state test',
          'join_eligibility': <String, Object?>{'eligible': false},
          'beginner_friendly': false,
          'created_at': '2026-01-01T00:00:00Z',
          'updated_at': '2026-06-10T00:00:00Z',
        },
      );

      expect(summary.lifecycle?.stage, CompetitionLifecycleStage.refunded);
      expect(summary.lifecycle?.isTerminal, isTrue);
      expect(summary.prizePool, 0);
    });
  });
}

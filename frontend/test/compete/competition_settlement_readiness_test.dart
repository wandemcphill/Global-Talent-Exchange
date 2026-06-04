import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/compete.dart';

void main() {
  group('HostedSettlementReadiness', () {
    test('marks missing backend readiness payload as degraded', () {
      final HostedCompetitionFinance finance =
          HostedCompetitionFinance.fromJson(<String, Object?>{
            'currency': 'FAN',
            'participant_count': 4,
            'entry_fee_fancoin': 5,
            'gross_collected': 20,
            'projected_reward_pool': 18,
            'projected_platform_fee': 2,
            'escrow_balance': 20,
            'settled_prizes': 0,
            'settled_platform_fee': 0,
            'status': 'completed',
          });

      expect(finance.settlementReadiness.isDegraded, isTrue);
      expect(finance.settlementReadiness.hasAuthoritativePayload, isFalse);
      expect(
        finance.settlementReadiness.missingData,
        contains('settlement_readiness'),
      );
      expect(finance.settlementReadiness.displayLabel, 'Settlement degraded');
    });

    test('parses authoritative ready settlement controls', () {
      final HostedCompetitionFinance finance =
          HostedCompetitionFinance.fromJson(<String, Object?>{
            'currency': 'FAN',
            'participant_count': 8,
            'entry_fee_fancoin': 10,
            'gross_collected': 80,
            'projected_reward_pool': 72,
            'projected_platform_fee': 8,
            'escrow_balance': 80,
            'settled_prizes': 0,
            'settled_platform_fee': 0,
            'status': 'completed',
            'settlement_readiness': <String, Object?>{
              'status': 'ready',
              'escrow_balanced': true,
              'standings_complete': true,
              'placements_submitted': true,
              'required_approvals': 2,
              'pending_approvals': 0,
            },
          });

      expect(finance.settlementReadiness.isReady, isTrue);
      expect(finance.settlementReadiness.escrowBalanced, isTrue);
      expect(finance.settlementReadiness.standingsComplete, isTrue);
      expect(finance.settlementReadiness.placementsSubmitted, isTrue);
      expect(finance.settlementReadiness.requiredApprovals, 2);
      expect(finance.settlementReadiness.pendingApprovals, 0);
      expect(finance.settlementReadiness.displayLabel, 'Settlement ready');
    });
  });

  group('CompetitionBackendFeed', () {
    test('distinguishes synced, empty, and blocked feed labels', () {
      final CompetitionBackendFeed<String> synced =
          CompetitionBackendFeed.fromItems<String>(<String>['row']);
      final CompetitionBackendFeed<String> empty =
          CompetitionBackendFeed.fromItems<String>(<String>[]);
      final CompetitionBackendFeed<String> blocked =
          CompetitionBackendFeed.blocked<String>(Exception('offline'));

      expect(synced.countLabel('Standings'), 'Standings 1');
      expect(empty.countLabel('Standings'), 'Standings empty');
      expect(blocked.countLabel('Standings'), 'Standings blocked');
      expect(blocked.message, isNotEmpty);
    });
  });
}

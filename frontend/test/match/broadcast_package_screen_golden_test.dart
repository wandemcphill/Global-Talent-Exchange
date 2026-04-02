import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match/presentation/broadcast_package_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import '../support/gtex_match_broadcast_fixture.dart';
import '../support/tolerant_golden_comparator.dart';

void main() {
  testWidgets('broadcast package premium surface matches golden', (
    WidgetTester tester,
  ) async {
    // Minor blur and antialiasing differences across local Windows runs and
    // Linux CI should not fail this full-screen golden.
    installTolerantGoldenComparator(
      testFilePath: 'test/match/broadcast_package_screen_golden_test.dart',
      precisionTolerance: 0.005,
    );

    await tester.binding.setSurfaceSize(const Size(1440, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: BroadcastPackageScreen(
          matchKey: 'broadcast-package-golden',
          competition: CompetitionSummary(
            id: 'broadcast-package-golden',
            name: 'Broadcast Package Golden',
            format: CompetitionFormat.league,
            visibility: CompetitionVisibility.public,
            status: CompetitionStatus.inProgress,
            creatorId: 'gtex',
            creatorName: 'GTEX',
            participantCount: 2,
            capacity: 2,
            currency: 'coin',
            entryFee: 0,
            platformFeePct: 0,
            hostFeePct: 0,
            platformFeeAmount: 0,
            hostFeeAmount: 0,
            prizePool: 0,
            payoutStructure: const <CompetitionPayoutBreakdown>[],
            rulesSummary: 'Broadcast package golden fixture.',
            matchType: MatchType.gtexHosted,
            joinEligibility: const CompetitionJoinEligibility(eligible: false),
            beginnerFriendly: true,
            createdAt: DateTime.utc(2026, 1, 1),
            updatedAt: DateTime.utc(2026, 1, 1),
          ),
          viewStateLoader: () async => buildBroadcastTestViewState(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 64));

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../goldens/broadcast_package_premium_surface.png'),
    );
  });
}

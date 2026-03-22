import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/screens/clubs/academy_overview_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/clubs/academy_player_row.dart';

void main() {
  testWidgets('academy overview shows pathway summary and opens player detail',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: AcademyOverviewScreen(api: ClubOpsApi.fixture()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Academy pathway'), findsOneWidget);
    expect(find.text('Royal Lagos Fc'), findsOneWidget);
    await tester.ensureVisible(find.text('Players'));
    await tester.tap(find.text('Players'));
    await tester.pumpAndSettle();
    expect(find.text('Academy players'), findsOneWidget);

    await tester.tap(find.text('Amara Cole'));
    await tester.pumpAndSettle();
    expect(find.text('Player pathway'), findsOneWidget);
    expect(find.text('Development progress'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Recent promotions'),
      300,
    );
    expect(find.text('Recent promotions'), findsOneWidget);
  });

  testWidgets('academy player rows handle long mixed metadata without overflow',
      (WidgetTester tester) async {
    const AcademyPlayer player = AcademyPlayer(
      id: 'academy-long-name',
      playerId: 'player-long-name',
      name: 'Very Long Canonical Real Player Name With Regen Context Attached',
      position: 'Attacking Midfielder',
      age: 18,
      pathwayStage: 'Elite pathway candidate',
      potentialBand: 'High',
      developmentProgressPercent: 68,
      readinessScore: 72,
      minutesTarget: 900,
      statusLabel: 'Promotion watch',
      nextMilestone: 'First-team integration',
      strengths: <String>['Passing'],
      focusAreas: <String>['Strength'],
      nationalityCode: 'NG',
      secondaryPositions: <String>['RW', 'LW', 'CM'],
      currentValueCredits: 1825,
      avatarSeedToken: 'academy-long-name-seed',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(
          body: SizedBox(
            width: 280,
            child: AcademyPlayerRow(player: player),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Very Long Canonical Real Player Name'),
        findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_hub/widgets/squad_readiness_panel.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('squad readiness panel exposes readiness lanes as backend gaps', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const Scaffold(
          body: SizedBox(
            width: 1100,
            child: SingleChildScrollView(
              child: SquadReadinessPanel(
                snapshot: SquadReadinessSnapshot(
                  clubName: 'Royal Lagos FC',
                  registeredPlayerCount: null,
                  scoutingSignalCount: 0,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Squad and player readiness'), findsOneWidget);
    expect(find.text('Availability'), findsOneWidget);
    expect(find.text('Injuries'), findsOneWidget);
    expect(find.text('Morale'), findsOneWidget);
    expect(find.text('Chemistry'), findsOneWidget);
    expect(find.text('Contracts'), findsOneWidget);
    expect(find.text('Scouting notes'), findsOneWidget);
    expect(
      find.textContaining('No local availability is inferred from squad size.'),
      findsOneWidget,
    );
    expect(find.text('11 available'), findsNothing);
    expect(find.text('Fully fit'), findsNothing);
  });

  testWidgets('squad count does not become generated player availability', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const Scaffold(
          body: SizedBox(
            width: 1100,
            child: SingleChildScrollView(
              child: SquadReadinessPanel(
                snapshot: SquadReadinessSnapshot(
                  clubName: 'Ibadan Lions FC',
                  registeredPlayerCount: 23,
                  scoutingSignalCount: 2,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('club-squad-readiness-registry')),
      findsOneWidget,
    );
    expect(find.text('23'), findsOneWidget);
    expect(find.text('2 signals'), findsOneWidget);
    expect(
      find.textContaining('No local availability is inferred from squad size.'),
      findsOneWidget,
    );
    expect(find.text('23 available'), findsNothing);
    expect(find.text('Available players'), findsNothing);
    expect(find.text('Match-fit XI'), findsNothing);
  });
}

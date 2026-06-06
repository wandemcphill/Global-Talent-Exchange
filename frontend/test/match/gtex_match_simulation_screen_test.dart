import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/presentation/gtex_match_simulation_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('simulation screen is quarantined behind backend realtime', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const GtexMatchSimulationScreen(
          result: Object(),
          competitionLabel: 'GTEX Arena Night',
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 32));

    expect(find.text('Route blocked'), findsWidgets);
    expect(find.text('Backend route blocked'), findsWidgets);
    expect(
      find.textContaining('Local match playback is quarantined'),
      findsWidgets,
    );
    expect(find.text('MATCH ROUTE GATE'), findsWidgets);
    expect(find.text('Live commentary'), findsNothing);
    expect(find.text('Timeline'), findsNothing);
  });
}

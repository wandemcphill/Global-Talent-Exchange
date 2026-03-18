import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/screens/competitions/competition_discovery_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('discovery shows safe sections and creator competitions',
      (WidgetTester tester) async {
    final CompetitionController controller = CompetitionController(
      api: CompetitionApi.fixture(),
      currentUserId: 'demo-user',
      currentUserName: 'Demo Fan',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: CompetitionDiscoveryScreen(
          controller: controller,
          currentUserId: 'demo-user',
          currentUserName: 'Demo Fan',
          isAuthenticated: false,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Create competition'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Creator competitions'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Creator competitions'));
    await tester.pumpAndSettle();

    expect(find.text('Coastal Creator Cup'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Weekend Creator Cup'),
      find.byType(ListView).first,
      const Offset(0, -300),
    );

    expect(find.text('Weekend Creator Cup'), findsOneWidget);
    expect(find.text('Coastal Creator Cup'), findsOneWidget);
  });
}

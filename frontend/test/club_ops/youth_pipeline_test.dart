import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/screens/clubs/youth_pipeline_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('youth pipeline screen shows funnel stages and notes',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: YouthPipelineScreen(api: ClubOpsApi.fixture()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Youth pipeline'), findsOneWidget);
    expect(find.text('Pipeline summary'), findsOneWidget);
    expect(find.text('Tracked'), findsOneWidget);
    expect(find.text('Scholarship'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Pipeline notes'),
      300,
    );
    expect(find.text('Pipeline notes'), findsOneWidget);
  });
}

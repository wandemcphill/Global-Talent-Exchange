import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/screens/clubs/club_sponsorships_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
      'club sponsorships screen shows contracts and opens catalog and detail',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubSponsorshipsScreen(api: ClubOpsApi.fixture()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Sponsorship contracts'), findsOneWidget);
    expect(find.text('North Star Mobility'), findsOneWidget);

    await tester.tap(find.text('North Star Mobility'));
    await tester.pumpAndSettle();
    expect(find.text('Sponsorship contract'), findsOneWidget);
    expect(find.text('Deliverables'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Open catalog'));
    await tester.tap(find.text('Open catalog'));
    await tester.pumpAndSettle();
    expect(find.text('Sponsorship catalog'), findsOneWidget);
    expect(find.text('Principal partnership'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Asset slot visibility'),
      300,
    );
    expect(find.text('Asset slot visibility'), findsOneWidget);
  });
}

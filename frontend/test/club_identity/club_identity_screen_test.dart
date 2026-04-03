import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club identity route is preview-only', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const ClubIdentityScreen(clubId: 'atlas-fc'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Identity Preview'), findsOneWidget);
    expect(find.text('Identity surfaces'), findsOneWidget);
    expect(
      find.textContaining('badge, club code, and kit palette'),
      findsOneWidget,
    );
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_controller.dart';
import 'package:gte_frontend/features/club_identity/jerseys/presentation/club_identity_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('club identity route is preview-only', (
    WidgetTester tester,
  ) async {
    final ClubIdentityController controller = ClubIdentityController(
      clubId: 'atlas-fc',
      repository: MockClubIdentityRepository(latency: Duration.zero),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: ClubIdentityScreen(
          clubId: 'atlas-fc',
          controller: controller,
        ),
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

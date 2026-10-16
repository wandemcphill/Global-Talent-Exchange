import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'blocked integrity screen shrink-wraps notes in a narrow viewport',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 780));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: const GteRouteIntegrityScreen.blocked(
            title: 'Match broadcast unavailable',
            message:
                'Broadcast routes are blocked until live broadcast sessions can be served without fallback snapshots or fabricated event streams.',
            icon: Icons.podcasts_outlined,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 32));

      expect(find.text('Route Truth'), findsOneWidget);
      expect(find.text('Mounted Shell'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}

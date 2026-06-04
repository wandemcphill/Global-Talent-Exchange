import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match_center/legacy_match_runtime_blocked_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('3D route is blocked for the 2D manager launch', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: const LegacyMatchRuntimeBlockedScreen(matchKey: 'live-match-001'),
      ),
    );

    expect(find.text('Route blocked'), findsWidgets);
    expect(find.text('FLUTTER_3D'), findsNothing);
    expect(find.text('NATIVE_3D'), findsNothing);
    expect(find.textContaining(_promotionCopyPattern), findsNothing);
    expect(find.byType(FilledButton), findsNothing);
    expect(find.byType(ElevatedButton), findsNothing);
    expect(find.byType(TextButton), findsNothing);
  });
}

final RegExp _promotionCopyPattern = RegExp(
  [
    r'upgrade\s+(?:to|for)\s+3d',
    r'unlock\s+3d',
    r'open\s+3d',
    r'launch\s+3d',
    r'watch\s+3d',
    r'premium\s+3d',
    r'native\s+3d',
    r'pseudo-?3d',
    r'unity',
    r'3d\s+(?:route|surface|viewer|experience|broadcast)',
  ].join('|'),
  caseSensitive: false,
);

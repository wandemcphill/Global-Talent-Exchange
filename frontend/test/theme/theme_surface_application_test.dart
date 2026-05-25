import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/features/profile/profile_screen.dart';
import 'package:gte_frontend/shared/widgets/app_background.dart';
import 'package:gte_frontend/theme/gte_theme_controller.dart';
import 'package:gte_frontend/theme/gte_theme_metadata.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/theme/gte_theme_registry.dart';
import 'package:gte_frontend/theme/gte_theme_scope.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('profile settings surface reflects the active theme label', (
    WidgetTester tester,
  ) async {
    final GteThemeController controller = GteThemeController(
      initialThemeId: GteThemeId.ultraRed,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          profileDataProvider.overrideWith(
            (Ref ref) async => const ProfileData.unauthenticated(),
          ),
        ],
        child: GteThemeControllerScope(
          controller: controller,
          child: MaterialApp(
            theme: GteShellTheme.build(controller.activeTheme),
            home: const Scaffold(body: ProfileScreen()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ultra Red'), findsWidgets);
    expect(find.text('Open theme selector'), findsOneWidget);
  });

  testWidgets('glass theme background adds backdrop filtering', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(GteThemeRegistry.paloAltoGlass),
        home: const AppBackground(child: SizedBox.expand()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(BackdropFilter), findsWidgets);
  });

  testWidgets('theme picker shows the six production themes', (
    WidgetTester tester,
  ) async {
    final GteThemeController controller = GteThemeController(
      initialThemeId: GteThemeId.foundersBlack,
    );

    await tester.pumpWidget(
      GteThemeControllerScope(
        controller: controller,
        child: MaterialApp(
          theme: GteShellTheme.build(controller.activeTheme),
          home: const Scaffold(body: GteThemePickerSheet()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Founders Black'), findsOneWidget);
    expect(find.text('Palo Alto Glass'), findsOneWidget);
    await _scrollTo(tester, find.text('Sand Hill Gold'));
    expect(find.text('Sand Hill Gold'), findsOneWidget);
    await _scrollTo(tester, find.text('Menlo Night Blue'));
    expect(find.text('Menlo Night Blue'), findsOneWidget);
    await _scrollTo(tester, find.text('Ultra Red'));
    expect(find.text('Ultra Red'), findsOneWidget);
    await _scrollTo(tester, find.text('Matchday Light'));
    expect(find.text('Matchday Light'), findsOneWidget);
  });
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    240,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}

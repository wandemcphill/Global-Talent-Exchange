import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/social/data/gtex_community_pulse_provider.dart';
import 'package:gte_frontend/features/social/models/gtex_community_models.dart';
import 'package:gte_frontend/features/social/social_screen.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// PHASE 4H - the truth pass.
///
/// A number the product has not been given is unknown, and unknown is not
/// zero. These pin the places the audit found stating measured-looking
/// figures the backend never sent.
void main() {
  Future<void> pumpCommunity(
    WidgetTester tester, {
    required bool isAuthenticated,
  }) async {
    tester.view.physicalSize = const Size(1600, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          communityPulseProvider.overrideWith(
            (Ref ref) async => GtexCommunityPulse.anonymous(),
          ),
        ],
        child: MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: CommunityScreen(
              api: CommunityApi.fixture(),
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              isAuthenticated: isAuthenticated,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('a guest is never told their community counts are zero', (
    WidgetTester tester,
  ) async {
    // The community digest is only fetched for a signed-in session, so for a
    // visitor the screen holds no digest at all. It used to fall back to
    // `?? 0` and report four measured-looking counts - watchlist, live
    // threads, direct threads, unread hints - about a person it knows
    // nothing about.
    await pumpCommunity(tester, isAuthenticated: false);

    await tester.tap(find.text('Live threads').first);
    await tester.pumpAndSettle();

    expect(
      find.ancestor(
        of: find.text('Watchlist'),
        matching: find.byType(GtexPanel),
      ),
      findsWidgets,
      reason: 'the social pulse panel is not on screen to assert against',
    );

    // Every count in the pulse reads as unknown, and none of them reads 0.
    expect(
      find.descendant(of: find.byType(GtexPanel), matching: find.text('0')),
      findsNothing,
      reason:
          'the community pulse reported a zero count for a session whose '
          'digest was never fetched',
    );
    expect(
      find.text('-'),
      findsWidgets,
      reason: 'absent counts should render as GTEX unknown, not as a number',
    );

    // The unread-hints chip is dropped entirely rather than claiming zero.
    expect(find.textContaining('UNREAD HINTS'), findsNothing);
  });
}

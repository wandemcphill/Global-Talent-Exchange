import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match_center/gte_live_match_hub_route_screen.dart';
import 'package:gte_frontend/features/match_center/live_match_overview_provider.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';

void main() {
  testWidgets('empty live overview blocks without a fabricated matchday lane', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveMatchOverviewRepositoryProvider.overrideWithValue(
            const _FakeLiveMatchOverviewRepository(
              overview: LiveMatchOverview(
                entries: <LiveMatchOverviewEntry>[],
                generatedAt: null,
                sourcePath: '/api/broadcast/home',
              ),
            ),
          ),
        ],
        child: const MaterialApp(
          home: GteLiveMatchHubRouteScreen(
            dependencies: _dependencies,
            clubName: 'Lagos Stars',
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text('Backend live lanes blocked'));

    expect(find.text('Backend live lanes blocked'), findsOneWidget);
    expect(find.text('Fallback signal'), findsNothing);
    expect(find.text('Lagos Stars live matchday lane'), findsNothing);
    expect(find.text('Open 2D'), findsNothing);
  });

  testWidgets(
    'degraded live overview blocks route recovery instead of fallback',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            liveMatchOverviewRepositoryProvider.overrideWithValue(
              const _FakeLiveMatchOverviewRepository(
                error: GteApiException(
                  type: GteApiErrorType.unavailable,
                  message: 'Broadcast home unavailable.',
                ),
              ),
            ),
          ],
          child: const MaterialApp(
            home: GteLiveMatchHubRouteScreen(
              dependencies: _dependencies,
              clubName: 'Lagos Stars',
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Live matchday feed degraded'), findsOneWidget);
      expect(find.text('Fallback signal'), findsNothing);
      expect(find.text('Lagos Stars live matchday lane'), findsNothing);
      expect(find.text('Open 2D'), findsNothing);
    },
  );
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isNotEmpty) {
    await tester.ensureVisible(finder.first);
    await tester.pumpAndSettle();
    return;
  }
  final Finder listView = find.byType(ListView, skipOffstage: false);
  if (listView.evaluate().isEmpty) {
    return;
  }
  for (int index = 0; index < 12 && finder.evaluate().isEmpty; index += 1) {
    await tester.drag(listView.first, const Offset(0, -240));
    await tester.pumpAndSettle();
  }
}

class _FakeLiveMatchOverviewRepository implements LiveMatchOverviewRepository {
  const _FakeLiveMatchOverviewRepository({this.overview, this.error});

  final LiveMatchOverview? overview;
  final Object? error;

  @override
  Future<LiveMatchOverview> loadOverview() async {
    if (error != null) {
      throw error!;
    }
    return overview!;
  }
}

const GteNavigationDependencies _dependencies = GteNavigationDependencies(
  apiBaseUrl: 'https://example.test',
  backendMode: GteBackendMode.live,
  currentClubId: 'club-1',
  currentClubName: 'Lagos Stars',
  isAuthenticated: true,
);

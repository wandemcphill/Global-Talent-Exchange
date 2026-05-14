import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/match/match_viewer_route_screen.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

void main() {
  testWidgets(
    'live match viewer route blocks instead of mounting demo fallback',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapRoute(
          backendMode: GteBackendMode.live,
          repository: const _UnavailableLiveMatchViewerRepository(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Live match unavailable'), findsOneWidget);
      expect(find.byType(GtexMatchViewerScreen), findsNothing);
    },
  );

  testWidgets(
    'explicit fixture mode can still mount the local match viewer fallback',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapRoute(
          backendMode: GteBackendMode.fixture,
          repository: const _UnavailableLiveMatchViewerRepository(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(GtexMatchViewerScreen), findsOneWidget);
      expect(find.text('Live match unavailable'), findsNothing);
    },
  );
}

Widget _wrapRoute({
  required GteBackendMode backendMode,
  required LiveMatchViewerRepository repository,
}) {
  return ProviderScope(
    overrides: [
      appConfigProvider.overrideWithValue(
        GteAppConfig(
          apiBaseUrl: 'https://example.test',
          backendMode: backendMode,
        ),
      ),
      liveMatchViewerRepositoryProvider.overrideWithValue(repository),
    ],
    child: const MaterialApp(
      home: MatchViewerRouteScreen(matchKey: 'missing-live-match'),
    ),
  );
}

class _UnavailableLiveMatchViewerRepository
    implements LiveMatchViewerRepository {
  const _UnavailableLiveMatchViewerRepository();

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    throw StateError('match viewer unavailable');
  }

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    throw StateError('match viewer unavailable');
  }
}

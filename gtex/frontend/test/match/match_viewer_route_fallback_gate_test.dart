import 'dart:async';

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

      expect(find.text('Match viewer unavailable'), findsNWidgets(2));
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
      expect(find.text('Match viewer unavailable'), findsNothing);
    },
  );

  testWidgets(
    'a pending match viewer bootstrap times out into a truthful retry state',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1200);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final _HangingLiveMatchViewerRepository repository =
          _HangingLiveMatchViewerRepository();
      await tester.pumpWidget(
        _wrapRoute(
          backendMode: GteBackendMode.live,
          repository: repository,
          bootstrapTimeout: const Duration(milliseconds: 1),
        ),
      );
      await tester.pump();
      expect(find.text('Preparing match viewer'), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 1));
      await tester.pumpAndSettle();
      expect(find.text('Match viewer unavailable'), findsNWidgets(2));
      expect(
        find.text(
          'The match service did not respond in time or is temporarily unavailable.',
        ),
        findsOneWidget,
      );
      expect(find.text('Verifying shipped capability'), findsNothing);
      expect(find.byType(GtexMatchViewerScreen), findsNothing);

      await tester.ensureVisible(find.text('Try again'));
      await tester.tap(find.text('Try again'));
      await tester.pump();
      expect(repository.bootstrapAttempts, 2);
      await tester.pump(const Duration(milliseconds: 1));
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'a missing live session and replay is shown as unavailable rather than a loading state',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapRoute(
          backendMode: GteBackendMode.live,
          repository: const _NotFoundLiveMatchViewerRepository(),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('No match available'), findsNWidgets(2));
      expect(find.text('Open Match Center'), findsOneWidget);
      expect(find.text('Verifying shipped capability'), findsNothing);
      expect(find.byType(GtexMatchViewerScreen), findsNothing);
    },
  );
}

Widget _wrapRoute({
  required GteBackendMode backendMode,
  required LiveMatchViewerRepository repository,
  Duration? bootstrapTimeout,
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
      if (bootstrapTimeout != null)
        matchViewerBootstrapTimeoutProvider.overrideWithValue(bootstrapTimeout),
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

class _NotFoundLiveMatchViewerRepository implements LiveMatchViewerRepository {
  const _NotFoundLiveMatchViewerRepository();

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    throw const GteApiException(
      type: GteApiErrorType.notFound,
      message: 'Match viewer payload was not found.',
      statusCode: 404,
    );
  }

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    throw UnimplementedError();
  }
}

class _HangingLiveMatchViewerRepository implements LiveMatchViewerRepository {
  int bootstrapAttempts = 0;

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) {
    bootstrapAttempts += 1;
    return Completer<LiveMatchViewerBootstrap>().future;
  }

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    throw UnimplementedError();
  }
}

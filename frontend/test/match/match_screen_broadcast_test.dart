import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match/live_match_overview_provider.dart';
import 'package:gte_frontend/features/match/match_screen.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/models/data_source_status.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/widgets/data_source_badge.dart';

void main() {
  testWidgets('match screen renders live broadcast-home matches honestly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(_testAppConfig),
          initialAuthSessionProvider.overrideWithValue(
            const AuthSession(
              userId: 'user-1',
              accessToken: 'token-1',
              refreshToken: 'refresh-1',
              sessionId: 'session-1',
              role: 'admin',
            ),
          ),
          liveMatchOverviewRepositoryProvider.overrideWithValue(
            const _FakeLiveMatchOverviewRepository(
              overview: LiveMatchOverview(
                entries: <LiveMatchOverviewEntry>[
                  LiveMatchOverviewEntry(
                    matchKey: 'live-match-001',
                    title: 'Derby Live',
                    subtitle: 'Main event from the featured channel.',
                    channelLabel: 'GTEX Prime',
                    isFeatured: true,
                    isLive: true,
                  ),
                ],
                generatedAt: null,
                sourcePath: '/api/broadcast/home',
              ),
            ),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: MatchScreen()),
        ),
      ),
    );

    await tester.pumpAndSettle();

    await _scrollTo(tester, find.text('Derby Live'));
    expect(find.text('Derby Live'), findsOneWidget);
    expect(find.text('GTEX Prime'), findsOneWidget);
    expect(find.text('Open Match'), findsOneWidget);
    expect(find.text('Open 2D'), findsNothing);
    expect(find.text('Open Broadcast+'), findsNothing);
    expect(find.text('Open 3D'), findsNothing);
    expect(find.text('Open spectate probe'), findsNothing);
    expect(find.text('View coming soon note'), findsNothing);
    expect(find.text('Open simulation'), findsNothing);
  });

  testWidgets('match screen shows blocked state with no fake live fallback', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appConfigProvider.overrideWithValue(_testAppConfig),
          initialAuthSessionProvider.overrideWithValue(
            const AuthSession(
              userId: 'user-1',
              accessToken: 'token-1',
              refreshToken: 'refresh-1',
              sessionId: 'session-1',
              role: 'admin',
            ),
          ),
          liveMatchOverviewRepositoryProvider.overrideWithValue(
            const _FakeLiveMatchOverviewRepository(
              error: GteApiException(
                type: GteApiErrorType.unavailable,
                message: 'Broadcast home is unavailable.',
              ),
            ),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: MatchScreen()),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(
      find.byWidgetPredicate(
        (Widget widget) =>
            widget is DataSourceBadge &&
            widget.status == DataSourceStatus.blocked,
      ),
      findsOneWidget,
    );
    await _scrollTo(tester, find.text('Broadcast home is unavailable.'));
    expect(find.text('Matches are blocked'), findsOneWidget);
    expect(find.text('Broadcast home is unavailable.'), findsOneWidget);
    expect(find.text('Derby Live'), findsNothing);
  });
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

const GteAppConfig _testAppConfig = GteAppConfig(
  apiBaseUrl: 'https://example.test',
  backendMode: GteBackendMode.live,
);

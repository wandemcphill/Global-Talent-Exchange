import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

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
          initialAuthSessionProvider.overrideWithValue(
            const AuthSession(
              userId: 'user-1',
              accessToken: 'token-1',
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

    expect(find.text('Derby Live'), findsOneWidget);
    expect(find.text('GTEX Prime'), findsOneWidget);
    expect(find.text('Open 2D'), findsOneWidget);
    expect(find.text('Open Broadcast+'), findsOneWidget);
    expect(find.text('Open 3D'), findsOneWidget);
    expect(find.text('Open spectate probe'), findsOneWidget);
  });

  testWidgets('match screen shows blocked state with no fake live fallback', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          initialAuthSessionProvider.overrideWithValue(
            const AuthSession(
              userId: 'user-1',
              accessToken: 'token-1',
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
    expect(find.text('Open spectate probe'), findsOneWidget);
    expect(find.text('Derby Live'), findsNothing);
  });
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

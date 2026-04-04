import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/match/match_3d_route_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('3D route labels Flutter 3D honestly when live and entitled', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildWidget(
        repository: _FakeViewerRepository(
          viewState: _routeViewState(matchId: 'live-match-001'),
        ),
      ),
    );
    await _pumpUntilVisible(tester, find.text('FLUTTER_3D'));

    expect(find.text('3D Match Viewer'), findsWidgets);
    expect(find.text('FLUTTER_3D'), findsOneWidget);
    expect(find.text('NATIVE_3D'), findsNothing);
    expect(find.text('Route blocked'), findsNothing);
  });

  testWidgets('3D route stays honest for signed-in standard sessions', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildWidget(
        repository: _FakeViewerRepository(
          viewState: _routeViewState(matchId: 'live-match-001'),
        ),
        session: const AuthSession(
          userId: 'basic-user',
          accessToken: 'token-2',
          refreshToken: 'refresh-token-2',
          sessionId: 'session-2',
          role: 'user',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('3D Match Viewer'), findsWidgets);
    expect(find.text('Route blocked'), findsNothing);
    expect(find.text('FLUTTER_3D'), findsOneWidget);
    expect(find.text('NATIVE_3D'), findsNothing);
  });
}

Widget _buildWidget({
  required LiveMatchViewerRepository repository,
  AuthSession? session = const AuthSession(
    userId: 'premium-user',
    accessToken: 'token-1',
    refreshToken: 'refresh-token-1',
    sessionId: 'session-1',
    role: 'user',
    permissions: <String>['match_3d_premium'],
  ),
}) {
  return ProviderScope(
    overrides: [
      liveMatchViewerRepositoryProvider.overrideWithValue(repository),
      authProvider.overrideWithValue(session),
    ],
    child: MaterialApp(
      theme: GteShellTheme.build(),
      home: const Match3dRouteScreen(matchKey: 'live-match-001'),
    ),
  );
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  Duration step = const Duration(milliseconds: 100),
  Duration timeout = const Duration(seconds: 3),
}) async {
  final int attempts = timeout.inMilliseconds ~/ step.inMilliseconds;
  for (int index = 0; index < attempts; index += 1) {
    if (finder.evaluate().isNotEmpty) {
      return;
    }
    await tester.pump(step);
  }
  expect(finder, findsOneWidget);
}

MatchViewState _routeViewState({required String matchId}) {
  final MatchViewState base = buildBroadcastTestViewState();
  return MatchViewState(
    matchId: matchId,
    source: base.source,
    supportsOffside: base.supportsOffside,
    deterministicSeed: base.deterministicSeed,
    matchMode: base.matchMode,
    durationSeconds: base.durationSeconds,
    homeTeam: base.homeTeam,
    awayTeam: base.awayTeam,
    events: base.events,
    frames: base.frames,
    fairnessIndicator: base.fairnessIndicator,
    timelineProof: base.timelineProof,
    scoreRevealLocked: base.scoreRevealLocked,
    segmentStartSeconds: base.segmentStartSeconds,
    segmentEndSeconds: base.frames.last.timeSeconds.ceil(),
    hasMoreSegments: false,
    nextSegmentToken: null,
    monetization: base.monetization,
    presentationPackage: base.presentationPackage,
  );
}

class _FakeViewerRepository implements LiveMatchViewerRepository {
  const _FakeViewerRepository({required this.viewState});

  final MatchViewState viewState;

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    return viewState;
  }

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    return LiveMatchViewerBootstrap(
      matchKey: matchKey,
      viewer: const <String, Object?>{'title': '3D route fixture'},
      competition: CompetitionSummary(
        id: matchKey,
        name: '3D Route Fixture',
        format: CompetitionFormat.league,
        visibility: CompetitionVisibility.public,
        status: CompetitionStatus.inProgress,
        creatorId: 'gtex',
        creatorName: 'GTEX',
        participantCount: 2,
        capacity: 2,
        currency: 'coin',
        entryFee: 0,
        platformFeePct: 0,
        hostFeePct: 0,
        platformFeeAmount: 0,
        hostFeeAmount: 0,
        prizePool: 0,
        payoutStructure: const <CompetitionPayoutBreakdown>[],
        rulesSummary: '3D route truth test fixture.',
        matchType: MatchType.gtexHosted,
        joinEligibility: const CompetitionJoinEligibility(eligible: false),
        beginnerFriendly: true,
        createdAt: DateTime.utc(2026, 1, 1),
        updatedAt: DateTime.utc(2026, 1, 1),
      ),
    );
  }
}

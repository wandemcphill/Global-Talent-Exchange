import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/match/match_3d_route_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets('entitled live route exposes the Flutter 3D lane', (
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
    expect(find.text('Route blocked'), findsNothing);
  });

  testWidgets(
    'signed-in standard sessions still mount the Flutter 3D lane',
    (WidgetTester tester) async {
      final _FakeViewerRepository repository = _FakeViewerRepository(
        viewState: _routeViewState(matchId: 'live-match-001'),
      );

      await tester.pumpWidget(
        _buildWidget(
          repository: repository,
          session: const AuthSession(
            userId: 'basic-user',
            accessToken: 'token-1',
            refreshToken: 'refresh-token-1',
            sessionId: 'session-1',
            role: 'user',
          ),
        ),
      );

      await _pumpUntilVisible(tester, find.text('FLUTTER_3D'));

      expect(find.text('3D Match Viewer'), findsWidgets);
      expect(find.text('Route blocked'), findsNothing);
      expect(find.text('FLUTTER_3D'), findsOneWidget);
      expect(repository.bootstrapCalls, 1);
      expect(repository.viewStateCalls, 1);
    },
  );

  testWidgets('incomplete live payload fails closed without mounting 3D', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildWidget(
        repository: _FakeViewerRepository(
          viewState: _routeViewState(
            matchId: 'live-match-001',
            frames: const <MatchTimelineFrame>[],
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('3D Match Viewer'), findsWidgets);
    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('FLUTTER_3D'), findsNothing);
  });

  testWidgets('sign-out while on route tears the lane down safely', (
    WidgetTester tester,
  ) async {
    final _FakeViewerRepository repository = _FakeViewerRepository(
      viewState: _routeViewState(matchId: 'live-match-001'),
    );
    final ProviderContainer container = ProviderContainer(
      overrides: [
        authSessionStoreProvider.overrideWithValue(MemoryAuthSessionStore()),
        initialAuthSessionProvider.overrideWithValue(_premiumSession()),
        liveMatchViewerRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: GteShellTheme.build(),
          home: const Match3dRouteScreen(matchKey: 'live-match-001'),
        ),
      ),
    );

    await _pumpUntilVisible(tester, find.text('FLUTTER_3D'));
    expect(find.text('Route blocked'), findsNothing);

    await container
        .read(appSessionControllerProvider.notifier)
        .updateSession(null);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Route blocked'), findsOneWidget);
    expect(find.text('FLUTTER_3D'), findsNothing);
  });

  testWidgets(
    're-entering the same match remounts through the live qualified session path',
    (WidgetTester tester) async {
      final _FakeViewerRepository repository = _FakeViewerRepository(
        viewState: _routeViewState(matchId: 'live-match-001'),
      );

      await tester.pumpWidget(_buildWidget(repository: repository));
      await _pumpUntilVisible(tester, find.text('FLUTTER_3D'));

      expect(repository.bootstrapCalls, 1);
      expect(repository.viewStateCalls, 1);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();

      await tester.pumpWidget(_buildWidget(repository: repository));
      await _pumpUntilVisible(tester, find.text('FLUTTER_3D'));

      expect(repository.bootstrapCalls, 2);
      expect(repository.viewStateCalls, 2);
    },
  );
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

AuthSession _premiumSession() {
  return const AuthSession(
    userId: 'premium-user',
    accessToken: 'token-1',
    refreshToken: 'refresh-token-1',
    sessionId: 'session-1',
    role: 'user',
    permissions: <String>['match_3d_premium'],
  );
}

MatchViewState _routeViewState({
  required String matchId,
  List<MatchTimelineFrame>? frames,
}) {
  final MatchViewState base = buildBroadcastTestViewState();
  final List<MatchTimelineFrame> resolvedFrames = frames ?? base.frames;
  final int segmentEndSeconds =
      resolvedFrames.isEmpty ? 0 : resolvedFrames.last.timeSeconds.ceil();
  return MatchViewState(
    matchId: matchId,
    source: base.source,
    supportsOffside: base.supportsOffside,
    deterministicSeed: base.deterministicSeed,
    matchMode: base.matchMode,
    durationSeconds: resolvedFrames.isEmpty ? 0 : base.durationSeconds,
    homeTeam: base.homeTeam,
    awayTeam: base.awayTeam,
    events: base.events,
    frames: resolvedFrames,
    fairnessIndicator: base.fairnessIndicator,
    timelineProof: base.timelineProof,
    scoreRevealLocked: base.scoreRevealLocked,
    segmentStartSeconds: base.segmentStartSeconds,
    segmentEndSeconds: segmentEndSeconds,
    hasMoreSegments: false,
    nextSegmentToken: null,
    monetization: base.monetization,
    presentationPackage: base.presentationPackage,
  );
}

class _FakeViewerRepository implements LiveMatchViewerRepository {
  _FakeViewerRepository({this.viewState});

  final MatchViewState? viewState;
  int bootstrapCalls = 0;
  int viewStateCalls = 0;

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    viewStateCalls += 1;
    return viewState!;
  }

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    bootstrapCalls += 1;
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
        rulesSummary: '3D route test fixture.',
        matchType: MatchType.gtexHosted,
        joinEligibility: const CompetitionJoinEligibility(eligible: false),
        beginnerFriendly: true,
        createdAt: DateTime.utc(2026, 1, 1),
        updatedAt: DateTime.utc(2026, 1, 1),
      ),
    );
  }
}

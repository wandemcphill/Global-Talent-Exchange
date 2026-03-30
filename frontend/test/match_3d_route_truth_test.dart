import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';
import 'package:gte_frontend/features/match/match_3d_route_screen.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';

import 'support/gtex_match_broadcast_fixture.dart';

void main() {
  testWidgets(
    '3D route labels Flutter fallback when native bridge is unavailable',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildWidget(
          repository: _FakeViewerRepository(
            viewState: buildBroadcastTestViewState(),
          ),
          bridge: Match3DBridge(backend: const _FakeBridgeBackend(false)),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('3D Match Viewer'), findsOneWidget);
      expect(find.text('FLUTTER_3D'), findsOneWidget);
    },
  );

  testWidgets(
    '3D route remains Flutter 3D even when an optional bridge backend exists',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildWidget(
          repository: _FakeViewerRepository(
            viewState: buildBroadcastTestViewState(),
          ),
          bridge: Match3DBridge(backend: const _FakeBridgeBackend(true)),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('3D Match Viewer'), findsOneWidget);
      expect(find.text('FLUTTER_3D'), findsOneWidget);
      expect(find.text('NATIVE_3D'), findsNothing);
    },
  );

  testWidgets(
    '3D route shows blocked state when the live viewer contract fails',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildWidget(
          repository: const _FakeViewerRepository(
            error: GteApiException(
              type: GteApiErrorType.notFound,
              message: 'Match viewer payload for blocked-match was not found.',
            ),
          ),
          bridge: Match3DBridge(backend: const _FakeBridgeBackend(false)),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Route blocked'), findsOneWidget);
      expect(find.text('BLOCKED'), findsWidgets);
    },
  );
}

Widget _buildWidget({
  required LiveMatchViewerRepository repository,
  required Match3DBridge bridge,
}) {
  return ProviderScope(
    overrides: [
      liveMatchViewerRepositoryProvider.overrideWithValue(repository),
      match3dBridgeProvider.overrideWithValue(bridge),
    ],
    child: const MaterialApp(
      home: Scaffold(body: Match3dRouteScreen(matchKey: 'live-match-001')),
    ),
  );
}

class _FakeViewerRepository implements LiveMatchViewerRepository {
  const _FakeViewerRepository({this.viewState, this.error});

  final MatchViewState? viewState;
  final Object? error;

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    if (error != null) {
      throw error!;
    }
    return viewState!;
  }

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    if (error != null) {
      throw error!;
    }
    return LiveMatchViewerBootstrap(
      matchKey: matchKey,
      viewer: const <String, Object?>{'title': '3D route truth fixture'},
      competition: CompetitionSummary(
        id: matchKey,
        name: '3D Route Truth Fixture',
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

class _FakeBridgeBackend implements Match3dBridgeBackend {
  const _FakeBridgeBackend(this.available);

  final bool available;

  @override
  Stream<dynamic> get events => const Stream<dynamic>.empty();

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {}

  @override
  Future<bool> isAvailable() async => available;
}

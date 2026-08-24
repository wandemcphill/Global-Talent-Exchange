import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_models.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_repository.dart';

/// Bounded stand-in for `pumpAndSettle`.
///
/// The match centre deliberately hosts indefinite animations (the loading and
/// reconnecting spinners), so `pumpAndSettle` can never return while either is
/// on screen. Pumping a fixed number of frames advances the tree far enough to
/// assert against without risking a ten-minute timeout.
Future<void> settle(
  WidgetTester tester, {
  int frames = 6,
  Duration step = const Duration(milliseconds: 16),
}) async {
  for (int i = 0; i < frames; i += 1) {
    await tester.pump(step);
  }
}

/// Tears a mounted match centre down cleanly.
///
/// Order matters: unmounting first lets the controller cancel its reconnect
/// timer. Closing the transport while the screen is still mounted trips the
/// reconnect path and leaves a pending timer at teardown, which fails the test.
Future<void> teardown(
  WidgetTester tester,
  FakeMatchRepository repository,
) async {
  await tester.pumpWidget(const SizedBox.shrink());
  await repository.disposeControllers();
  await tester.pump();
}

/// Builds a deterministic live match snapshot for tests.
///
/// Deliberately local to the test tree: production code must never be able to
/// reach a hand-authored fixture.
GtexLiveMatchState buildMatchState({
  String matchId = 'm-1',
  int minute = 1,
  GtexMatchPhase phase = GtexMatchPhase.firstHalf,
  int homeScore = 0,
  int awayScore = 0,
  int timelineEvents = 0,
  int? homeMomentumPercent,
  List<GtexMatchHighlight> highlights = const <GtexMatchHighlight>[],
}) {
  return GtexLiveMatchState(
    matchId: matchId,
    home: GtexMatchTeam(
      id: 'home',
      name: 'Lagos Crown',
      shortName: 'LAG',
      score: homeScore,
      formation: '4-3-3',
      players: const <GtexLineupPlayer>[
        GtexLineupPlayer(
          id: 'player-7',
          name: 'A. King',
          position: 'ST',
          shirtNumber: 7,
          rating: 7.4,
        ),
      ],
    ),
    away: GtexMatchTeam(
      id: 'away',
      name: 'Accra Sentinels',
      shortName: 'ACC',
      score: awayScore,
      formation: '4-2-3-1',
      players: const <GtexLineupPlayer>[],
    ),
    minute: minute,
    phase: phase,
    pitchPlayers: const <GtexPitchPlayer>[],
    timeline: List<GtexMatchTimelineEvent>.generate(
      timelineEvents,
      (int index) => GtexMatchTimelineEvent(
        minute: index + 1,
        type: GtexPitchEventType.pass,
        title: 'Event ${index + 1}',
        description: 'Generated timeline event ${index + 1}',
      ),
    ),
    stats: const GtexMatchStats(
      homePossession: 55,
      awayPossession: 45,
      homeShots: 6,
      awayShots: 4,
      homeShotsOnTarget: 3,
      awayShotsOnTarget: 1,
      homePassAccuracy: 84,
      awayPassAccuracy: 79,
      homeExpectedGoals: 1.4,
      awayExpectedGoals: 0.7,
    ),
    highlights: highlights,
    homeMomentumPercent: homeMomentumPercent,
  );
}

/// Scriptable repository so tests can drive exact feed behaviour.
class FakeMatchRepository implements GtexMatchRepository {
  FakeMatchRepository({
    GtexLiveMatchState? initial,
    this.fetchError,
    this.tacticsError,
  }) : initial = initial ?? buildMatchState();

  final GtexLiveMatchState initial;

  /// When set, [fetchLiveMatch] throws this instead of returning.
  Object? fetchError;
  Object? tacticsError;

  int fetchCount = 0;
  int watchCount = 0;
  final List<GtexTacticalInstruction> sentInstructions =
      <GtexTacticalInstruction>[];

  /// Controllers handed out by [watchLiveMatch], newest last.
  final List<StreamController<GtexLiveMatchState>> controllers =
      <StreamController<GtexLiveMatchState>>[];

  StreamController<GtexLiveMatchState> get currentController =>
      controllers.last;

  @override
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId) async {
    fetchCount += 1;
    final Object? error = fetchError;
    if (error != null) {
      throw error;
    }
    return initial;
  }

  @override
  Stream<GtexLiveMatchState> watchLiveMatch(String matchId) {
    watchCount += 1;
    final StreamController<GtexLiveMatchState> controller =
        StreamController<GtexLiveMatchState>();
    controllers.add(controller);
    return controller.stream;
  }

  @override
  Future<void> sendTacticalInstruction(
    String matchId,
    GtexTacticalInstruction instruction,
  ) async {
    final Object? error = tacticsError;
    if (error != null) {
      throw error;
    }
    sentInstructions.add(instruction);
  }

  /// Closes every stream handed out by [watchLiveMatch].
  ///
  /// Deliberately does not await `close()`. For a single-subscription
  /// controller whose listener has already been cancelled, that future can
  /// stay uncompleted forever and wedge the test in a ten-minute timeout.
  Future<void> disposeControllers() async {
    for (final StreamController<GtexLiveMatchState> controller in controllers) {
      if (!controller.isClosed) {
        unawaited(controller.close());
      }
    }
  }
}

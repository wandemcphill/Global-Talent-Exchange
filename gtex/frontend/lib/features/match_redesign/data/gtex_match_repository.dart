import 'dart:async';

import 'gtex_match_models.dart';

abstract class GtexMatchRepository {
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId);
  Stream<GtexLiveMatchState> watchLiveMatch(String matchId);
  Future<void> sendTacticalInstruction(
    String matchId,
    GtexTacticalInstruction instruction,
  );
}

class GtexUnavailableMatchRepository implements GtexMatchRepository {
  const GtexUnavailableMatchRepository();

  StateError _unavailable(String matchId) {
    return StateError(
      'Live match repository is required for match $matchId. '
      'Fixture match data is available only in explicit tests.',
    );
  }

  @override
  Future<GtexLiveMatchState> fetchLiveMatch(String matchId) {
    return Future<GtexLiveMatchState>.error(_unavailable(matchId));
  }

  @override
  Stream<GtexLiveMatchState> watchLiveMatch(String matchId) {
    return Stream<GtexLiveMatchState>.error(_unavailable(matchId));
  }

  @override
  Future<void> sendTacticalInstruction(
    String matchId,
    GtexTacticalInstruction instruction,
  ) {
    return Future<void>.error(_unavailable(matchId));
  }
}

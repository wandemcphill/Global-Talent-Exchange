import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/data/match/match_simulation_models.dart';
import 'package:gte_frontend/features/match_center/data/match/match_value_engine.dart';

class MatchSimulationRequestFactory {
  const MatchSimulationRequestFactory._();

  static MatchSimulationRequest fromLiveSnapshot(
    LiveMatchSnapshot snapshot, {
    String? matchId,
    MatchSimulationImportance importance = MatchSimulationImportance.quickMatch,
    int? seed,
  }) {
    throw UnsupportedError(
      'Canonical match state must come from backend-authored realtime payloads.',
    );
  }
}

class MatchSimulationEngine {
  const MatchSimulationEngine({MatchValueEngine? valueEngine});

  MatchSimulationResult simulate(MatchSimulationRequest request) {
    throw UnsupportedError(
      'Local match event generation is disabled for the canonical match center.',
    );
  }
}

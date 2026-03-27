import 'dart:math';

import 'package:gte_frontend/data/match/match_simulation_models.dart';

class MatchValueEngine {
  const MatchValueEngine();

  List<MatchSimulationPlayerPerformance> apply({
    required List<MatchSimulationPlayerPerformance> performances,
    required MatchSimulationImportance importance,
  }) {
    if (performances.isEmpty) {
      return const <MatchSimulationPlayerPerformance>[];
    }

    final List<MatchSimulationPlayerPerformance> sorted =
        List<MatchSimulationPlayerPerformance>.from(performances)
          ..sort(
            (MatchSimulationPlayerPerformance left,
                MatchSimulationPlayerPerformance right) {
              final int ratingOrder = right.rating.compareTo(left.rating);
              if (ratingOrder != 0) {
                return ratingOrder;
              }
              final int goalOrder = right.goals.compareTo(left.goals);
              if (goalOrder != 0) {
                return goalOrder;
              }
              return right.assists.compareTo(left.assists);
            },
          );

    final String mvpId = sorted.first.player.id;
    final double multiplier = switch (importance) {
      MatchSimulationImportance.friendly => 0.5,
      MatchSimulationImportance.quickMatch => 1.0,
      MatchSimulationImportance.tournament => 1.5,
      MatchSimulationImportance.finalMatch => 2.0,
    };

    final List<MatchSimulationPlayerPerformance> updated =
        <MatchSimulationPlayerPerformance>[];
    for (final MatchSimulationPlayerPerformance performance in performances) {
      double deltaPct = (performance.rating - 6.5) * 0.02 * multiplier;
      if (performance.goals >= 3) {
        deltaPct += 0.10;
      }
      if (performance.cleanSheet &&
          (performance.player.isGoalkeeper || performance.player.isDefender)) {
        deltaPct += 0.05;
      }
      final bool isMvp = performance.player.id == mvpId;
      if (isMvp) {
        deltaPct += 0.08;
      }
      deltaPct = deltaPct.clamp(-0.18, 0.24).toDouble();

      final MatchFormTag formTag = _resolveFormTag(
        performance: performance,
        deltaPct: deltaPct,
      );
      updated.add(
        performance.copyWith(
          isMvp: isMvp,
          formTag: formTag,
          previousValueCredits: performance.player.baseValueCredits,
          nextValueCredits:
              performance.player.baseValueCredits * (1 + deltaPct),
          valueDeltaPct: deltaPct,
        ),
      );
    }

    updated.sort(
      (MatchSimulationPlayerPerformance left,
          MatchSimulationPlayerPerformance right) {
        final int ratingOrder = right.rating.compareTo(left.rating);
        if (ratingOrder != 0) {
          return ratingOrder;
        }
        return right.valueDeltaPct.compareTo(left.valueDeltaPct);
      },
    );
    return updated;
  }

  double applyDailyDecay(double currentValue, {int days = 1}) {
    return currentValue * pow(0.995, max(0, days));
  }

  MatchFormTag _resolveFormTag({
    required MatchSimulationPlayerPerformance performance,
    required double deltaPct,
  }) {
    if (performance.player.age <= 22 && deltaPct >= 0.04) {
      return MatchFormTag.risingTalent;
    }
    if (performance.rating >= 7.8 || deltaPct >= 0.05) {
      return MatchFormTag.inForm;
    }
    if (performance.rating <= 6.0 || deltaPct <= -0.04) {
      return MatchFormTag.outOfForm;
    }
    return MatchFormTag.steady;
  }
}

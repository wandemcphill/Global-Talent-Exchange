import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexMatchStatsPanel extends StatelessWidget {
  const GtexMatchStatsPanel({super.key, required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final GtexMatchStats stats = match.stats;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _StatRow(
          label: 'POSSESSION',
          home: '${stats.homePossession}%',
          away: '${stats.awayPossession}%',
          homeShare: stats.homePossession / 100,
        ),
        _StatRow(
          label: 'SHOTS',
          home: '${stats.homeShots}',
          away: '${stats.awayShots}',
          homeShare: _share(stats.homeShots, stats.awayShots),
        ),
        _StatRow(
          label: 'ON TARGET',
          home: '${stats.homeShotsOnTarget}',
          away: '${stats.awayShotsOnTarget}',
          homeShare: _share(stats.homeShotsOnTarget, stats.awayShotsOnTarget),
        ),
        _StatRow(
          label: 'PASS ACCURACY',
          home: '${stats.homePassAccuracy}%',
          away: '${stats.awayPassAccuracy}%',
          homeShare: _share(stats.homePassAccuracy, stats.awayPassAccuracy),
        ),
        _StatRow(
          label: 'EXPECTED GOALS',
          home: stats.homeExpectedGoals.toStringAsFixed(2),
          away: stats.awayExpectedGoals.toStringAsFixed(2),
          homeShare: _shareDouble(
            stats.homeExpectedGoals,
            stats.awayExpectedGoals,
          ),
        ),
      ],
    );
  }

  double _share(int home, int away) {
    final int total = home + away;
    if (total <= 0) {
      return .5;
    }
    return home / total;
  }

  double _shareDouble(double home, double away) {
    final double total = home + away;
    if (total <= 0) {
      return .5;
    }
    return home / total;
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow({
    required this.label,
    required this.home,
    required this.away,
    required this.homeShare,
  });

  final String label;
  final String home;
  final String away;
  final double homeShare;

  @override
  Widget build(BuildContext context) {
    final double clampedShare = homeShare.clamp(.04, .96).toDouble();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: GtexMatchVisualTokens.panelDecoration(
        background: GtexMatchVisualTokens.surfaceOverlay,
        radius: 8,
      ),
      child: Column(
        children: [
          Row(
            children: [
              SizedBox(
                width: 62,
                child: Text(
                  home,
                  style: GtexMatchVisualTokens.dataStyle.copyWith(
                    color: GtexMatchVisualTokens.live,
                  ),
                ),
              ),
              Expanded(
                child: Center(
                  child: Text(label, style: GtexMatchVisualTokens.labelStyle),
                ),
              ),
              SizedBox(
                width: 62,
                child: Text(
                  away,
                  textAlign: TextAlign.end,
                  style: GtexMatchVisualTokens.dataStyle.copyWith(
                    color: GtexMatchVisualTokens.amber,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: SizedBox(
              height: 5,
              child: Row(
                children: [
                  Expanded(
                    flex: (clampedShare * 1000).round(),
                    child: const ColoredBox(color: GtexMatchVisualTokens.live),
                  ),
                  Expanded(
                    flex: ((1 - clampedShare) * 1000).round(),
                    child: const ColoredBox(color: GtexMatchVisualTokens.amber),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

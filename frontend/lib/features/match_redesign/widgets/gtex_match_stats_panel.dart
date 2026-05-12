import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexMatchStatsPanel extends StatelessWidget {
  const GtexMatchStatsPanel({super.key, required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final stats = match.stats;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _StatRow(label: 'Possession', home: '${stats.homePossession}%', away: '${stats.awayPossession}%'),
        _StatRow(label: 'Shots', home: '${stats.homeShots}', away: '${stats.awayShots}'),
        _StatRow(label: 'On target', home: '${stats.homeShotsOnTarget}', away: '${stats.awayShotsOnTarget}'),
        _StatRow(label: 'Pass accuracy', home: '${stats.homePassAccuracy}%', away: '${stats.awayPassAccuracy}%'),
        _StatRow(label: 'Expected goals', home: stats.homeExpectedGoals.toStringAsFixed(2), away: stats.awayExpectedGoals.toStringAsFixed(2)),
      ],
    );
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow({required this.label, required this.home, required this.away});
  final String label;
  final String home;
  final String away;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white.withOpacity(.045), borderRadius: BorderRadius.circular(16)),
      child: Row(
        children: [
          SizedBox(width: 58, child: Text(home, style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w900))),
          Expanded(child: Center(child: Text(label, style: TextStyle(color: Colors.white.withOpacity(.66), fontWeight: FontWeight.w700)))),
          SizedBox(width: 58, child: Text(away, textAlign: TextAlign.end, style: const TextStyle(color: Color(0xFFFFD166), fontWeight: FontWeight.w900))),
        ],
      ),
    );
  }
}

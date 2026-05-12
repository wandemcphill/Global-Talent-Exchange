import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexPostMatchPanel extends StatelessWidget {
  const GtexPostMatchPanel({super.key, required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final winner = match.home.score == match.away.score
        ? 'Draw'
        : match.home.score > match.away.score
            ? match.home.name
            : match.away.name;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: const Color(0xFF07130E), borderRadius: BorderRadius.circular(24), border: Border.all(color: const Color(0xFF18FF88).withOpacity(.18))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Post-match summary', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          Text('Result: $winner', style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          Text('GTEX AI News can generate a match report from final stats, timeline events, player ratings, and trophy/competition context.', style: TextStyle(color: Colors.white.withOpacity(.62), height: 1.35)),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: const [
              _ActionChip(label: 'Generate match report'),
              _ActionChip(label: 'Open highlights'),
              _ActionChip(label: 'Update club form'),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionChip extends StatelessWidget {
  const _ActionChip({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text(label), backgroundColor: Colors.white.withOpacity(.08), labelStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800));
  }
}

import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexPostMatchPanel extends StatelessWidget {
  const GtexPostMatchPanel({super.key, required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final bool finalWhistle = match.phase == GtexMatchPhase.fullTime;
    final String resultLabel =
        match.home.score == match.away.score
            ? 'DRAW'
            : match.home.score > match.away.score
            ? match.home.name.toUpperCase()
            : match.away.name.toUpperCase();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: GtexMatchVisualTokens.panelDecoration(
        background: GtexMatchVisualTokens.surfaceOverlay,
        borderColor:
            finalWhistle
                ? const Color(0x6600E87A)
                : GtexMatchVisualTokens.borderStrong,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                finalWhistle
                    ? Icons.verified_rounded
                    : Icons.lock_clock_rounded,
                color:
                    finalWhistle
                        ? GtexMatchVisualTokens.live
                        : GtexMatchVisualTokens.amber,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  finalWhistle ? 'FINAL RESULT AUTHORITY' : 'REPORT LOCKED',
                  style: const TextStyle(
                    color: GtexMatchVisualTokens.textPrimary,
                    fontWeight: FontWeight.w900,
                    fontSize: 14,
                    letterSpacing: .8,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            finalWhistle ? resultLabel : 'MATCH STILL IN PROGRESS',
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontFamily: 'Barlow Condensed',
              fontSize: 28,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            finalWhistle
                ? 'Post-match report data is available only after the backend returns final stats, event ledger, and settlement state.'
                : 'The post-match surface stays blocked until the persisted match authority declares full time.',
            style: const TextStyle(
              color: GtexMatchVisualTokens.textSecondary,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _StatusTag(
                label: finalWhistle ? 'FINAL STATS READY' : 'AWAITING FT',
                color:
                    finalWhistle
                        ? GtexMatchVisualTokens.live
                        : GtexMatchVisualTokens.amber,
              ),
              const _StatusTag(
                label: 'NO CLIENT REPORT GENERATION',
                color: GtexMatchVisualTokens.textSecondary,
              ),
              const _StatusTag(
                label: 'BACKEND AUTHORITY',
                color: GtexMatchVisualTokens.blue,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatusTag extends StatelessWidget {
  const _StatusTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(.10),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(.30)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: .6,
        ),
      ),
    );
  }
}

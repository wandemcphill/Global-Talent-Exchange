import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexHighlightsPanel extends StatelessWidget {
  const GtexHighlightsPanel({
    super.key,
    required this.highlights,
    this.onReplayGoal,
  });

  final List<GtexMatchHighlight> highlights;
  final ValueChanged<int>? onReplayGoal;

  @override
  Widget build(BuildContext context) {
    if (highlights.isEmpty) {
      return const GtexMatchEmptyFeed(
        icon: Icons.movie_filter_outlined,
        title: 'Live highlights unavailable',
        message:
            'The match authority has not returned highlight records for this fixture.',
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: highlights.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final item = highlights[index];
        final Color accent = _importanceColor(item.importance);
        return Container(
          padding: const EdgeInsets.all(12),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
            borderColor: accent.withOpacity(.38),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: accent.withOpacity(.12),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: accent.withOpacity(.34)),
                ),
                child: Column(
                  children: [
                    Icon(
                      Icons.play_circle_outline_rounded,
                      color: accent,
                      size: 18,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.minute}\'',
                      style: TextStyle(
                        color: accent,
                        fontFamily: 'JetBrains Mono',
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    if (item.summary.isNotEmpty) ...[
                      const SizedBox(height: 5),
                      Text(
                        item.summary,
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.textSecondary,
                          height: 1.3,
                        ),
                      ),
                    ],
                    if (onReplayGoal != null &&
                        '${item.title} ${item.summary}'.toLowerCase().contains('goal')) ...<Widget>[
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: OutlinedButton.icon(
                          key: Key('gtex-highlight-goal-replay-${item.minute}'),
                          onPressed: () => onReplayGoal!(item.minute),
                          icon: const Icon(Icons.replay_circle_filled_outlined, size: 16),
                          label: Text('Replay goal · ${item.minute}\''),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: GtexMatchVisualTokens.amber,
                            side: BorderSide(color: GtexMatchVisualTokens.amber.withOpacity(.40)),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            minimumSize: const Size(0, 36),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Color _importanceColor(int importance) {
    if (importance >= 4) {
      return GtexMatchVisualTokens.live;
    }
    if (importance >= 2) {
      return GtexMatchVisualTokens.amber;
    }
    return GtexMatchVisualTokens.blue;
  }
}

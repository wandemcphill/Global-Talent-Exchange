import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import '../../match/widgets/gtex_matchday_ad_slot.dart';
import 'gtex_match_visual_tokens.dart';

class GtexPostMatchPanel extends StatelessWidget {
  const GtexPostMatchPanel({
    super.key,
    required this.match,
    this.onOpenPortfolio,
    this.onOpenMarket,
    this.onOpenNewsroomReport,
    this.onOpenReplay,
    this.onReplayGoal,
  });

  final GtexLiveMatchState match;
  final VoidCallback? onOpenPortfolio;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenNewsroomReport;
  final VoidCallback? onOpenReplay;
  final ValueChanged<int>? onReplayGoal;

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
                ? GtexMatchVisualTokens.live.withValues(alpha: 0.40)
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
          if (finalWhistle) ...[
            if (onReplayGoal != null &&
                match.timeline.any(
                  (GtexMatchTimelineEvent event) =>
                      event.type == GtexPitchEventType.goal,
                )) ...<Widget>[
              const SizedBox(height: 14),
              const Text(
                'GOAL REPLAYS',
                style: TextStyle(
                  color: GtexMatchVisualTokens.amber,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 8),
              for (final GtexMatchTimelineEvent event in match.timeline.where(
                (GtexMatchTimelineEvent event) =>
                    event.type == GtexPitchEventType.goal,
              ))
                Container(
                  margin: const EdgeInsets.only(bottom: 7),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                  decoration: BoxDecoration(
                    color: GtexMatchVisualTokens.surfaceRaised,
                    borderRadius: BorderRadius.circular(7),
                    border: Border.all(color: GtexMatchVisualTokens.border),
                  ),
                  child: Row(
                    children: <Widget>[
                      Container(
                        width: 34,
                        height: 34,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: GtexMatchVisualTokens.amber.withValues(alpha: .12),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: GtexMatchVisualTokens.amber.withValues(alpha: .35),
                          ),
                        ),
                        child: const Icon(
                          Icons.sports_soccer_rounded,
                          color: GtexMatchVisualTokens.amber,
                          size: 18,
                        ),
                      ),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              "${event.minute}' · ${event.playerName?.trim().isNotEmpty == true ? event.playerName!.trim() : event.title}",
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: GtexMatchVisualTokens.textPrimary,
                                fontWeight: FontWeight.w900,
                                fontSize: 12,
                              ),
                            ),
                            if (event.description.trim().isNotEmpty)
                              Text(
                                event.description,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: GtexMatchVisualTokens.textSecondary,
                                  fontSize: 10,
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      TextButton.icon(
                        key: Key('gtex-post-match-goal-replay-${event.minute}'),
                        onPressed: () => onReplayGoal!(event.minute),
                        icon: const Icon(Icons.replay_rounded, size: 15),
                        label: const Text('Replay'),
                      ),
                    ],
                  ),
                ),
            ],
            const SizedBox(height: 14),
            const GtexMatchdayAdSlot(
              placement: 'Full-time match report & replay',
              compact: true,
            ),
            const SizedBox(height: 16),
            const Divider(color: GtexMatchVisualTokens.border),
            const SizedBox(height: 12),
            const Text(
              'MATCHDAY → OWNER DECISION LOOP',
              style: TextStyle(
                color: GtexMatchVisualTokens.live,
                fontSize: 12,
                fontWeight: FontWeight.w900,
                letterSpacing: 1.0,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Performance in this fixture has updated published player valuations. Review your portfolio position or explore new talent on the market.',
              style: TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: 12,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                if (onOpenPortfolio != null)
                  FilledButton.icon(
                    key: const Key('gtex-post-match-portfolio-btn'),
                    onPressed: onOpenPortfolio,
                    icon: const Icon(
                      Icons.account_balance_wallet_outlined,
                      size: 16,
                    ),
                    label: const Text('Review Portfolio'),
                  ),
                if (onOpenMarket != null)
                  OutlinedButton.icon(
                    key: const Key('gtex-post-match-market-btn'),
                    onPressed: onOpenMarket,
                    icon: const Icon(Icons.storefront_outlined, size: 16),
                    label: const Text('Explore Transfer Hub'),
                  ),
                if (onOpenNewsroomReport != null)
                  OutlinedButton.icon(
                    key: const Key('gtex-post-match-newsroom-btn'),
                    onPressed: onOpenNewsroomReport,
                    icon: const Icon(Icons.article_outlined, size: 16),
                    label: const Text('Open Newsroom Match Report'),
                  ),
                if (onOpenReplay != null)
                  TextButton.icon(
                    key: const Key('gtex-post-match-replay-btn'),
                    onPressed: onOpenReplay,
                    icon: const Icon(
                      Icons.replay_circle_filled_outlined,
                      size: 16,
                    ),
                    label: const Text('Open 2D Replay'),
                  ),
              ],
            ),
          ],
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
        color: color.withValues(alpha: .10),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: .30)),
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

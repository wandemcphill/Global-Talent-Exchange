import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class GtexFulltimeOverlay extends StatelessWidget {
  const GtexFulltimeOverlay({
    super.key,
    required this.visible,
    required this.viewState,
    required this.onOpenHighlights,
  });

  final bool visible;
  final MatchViewState viewState;
  final VoidCallback? onOpenHighlights;

  @override
  Widget build(BuildContext context) {
    if (!visible) {
      return const SizedBox.shrink();
    }
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 460),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        decoration: BoxDecoration(
          color: const Color(0xF0101E2D),
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(
              'Full Time',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 14),
            Text(
              '${viewState.homeTeam.teamName} ${viewState.lastFrame.homeScore} - ${viewState.lastFrame.awayScore} ${viewState.awayTeam.teamName}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            if (onOpenHighlights != null) ...<Widget>[
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: onOpenHighlights,
                icon: const Icon(Icons.play_circle_outline_rounded),
                label: const Text('Post-match highlights'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

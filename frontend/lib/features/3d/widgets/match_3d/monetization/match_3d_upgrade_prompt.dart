import 'package:flutter/material.dart';

enum Match3dUpgradeAction { unlock3d, continueIn2d, upgradeTournament }

class Match3dUpgradePrompt extends StatelessWidget {
  const Match3dUpgradePrompt({
    super.key,
    required this.matchUnlockPrice,
    this.tournamentBoostPrice,
  });

  final double matchUnlockPrice;
  final double? tournamentBoostPrice;

  static Future<Match3dUpgradeAction?> show(
    BuildContext context, {
    required double matchUnlockPrice,
    double? tournamentBoostPrice,
  }) {
    return showModalBottomSheet<Match3dUpgradeAction>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Match3dUpgradePrompt(
          matchUnlockPrice: matchUnlockPrice,
          tournamentBoostPrice: tournamentBoostPrice,
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            color: const Color(0xFF0E1724),
            border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.34),
                blurRadius: 28,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Match center is locked to 2D broadcast',
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'The legacy immersive lane is quarantined while the canonical 2D broadcast match center is active.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.white70,
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed:
                      () => Navigator.of(
                        context,
                      ).pop(Match3dUpgradeAction.continueIn2d),
                  icon: const Icon(Icons.map_outlined),
                  label: const Text('Continue in 2D'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class Match3dUpgradeTeaser extends StatelessWidget {
  const Match3dUpgradeTeaser({
    super.key,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.onPressed,
    this.onDismiss,
  });

  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback onPressed;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Material(
      color: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: const Color(0xE6122033),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.20),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Row(
              children: <Widget>[
                const Icon(
                  Icons.movie_filter_outlined,
                  color: Color(0xFFFDB022),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (onDismiss != null)
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: onDismiss,
                    icon: const Icon(Icons.close, size: 18),
                    color: Colors.white70,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: theme.textTheme.bodySmall?.copyWith(color: Colors.white70),
            ),
            const SizedBox(height: 12),
            FilledButton.tonal(onPressed: onPressed, child: Text(actionLabel)),
          ],
        ),
      ),
    );
  }
}

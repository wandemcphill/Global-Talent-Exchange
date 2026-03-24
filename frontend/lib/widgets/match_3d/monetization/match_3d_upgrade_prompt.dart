import 'package:flutter/material.dart';

enum Match3dUpgradeAction {
  unlock3d,
  continueIn2d,
  upgradeTournament,
}

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
                'Watch in Cinematic Mode \u{1F3AC}',
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'Unlock 3D-lite broadcast angles for this match session without interrupting playback.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: Colors.white70,
                ),
              ),
              const SizedBox(height: 16),
              _PriceCard(
                title: 'Match unlock',
                subtitle: '3D for the current match session',
                priceLabel: '${matchUnlockPrice.toStringAsFixed(1)} coin',
                accentColor: const Color(0xFF53B1FD),
              ),
              if (tournamentBoostPrice != null) ...<Widget>[
                const SizedBox(height: 10),
                _PriceCard(
                  title: 'Upgrade Tournament Experience',
                  subtitle: '3D matches, cinematic intros, enhanced camera',
                  priceLabel:
                      '${tournamentBoostPrice!.toStringAsFixed(2)} coin',
                  accentColor: const Color(0xFFFDB022),
                ),
              ],
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () => Navigator.of(context).pop(
                    Match3dUpgradeAction.unlock3d,
                  ),
                  icon: const Icon(Icons.movie_filter_outlined),
                  label: const Text('Unlock & Watch'),
                ),
              ),
              if (tournamentBoostPrice != null) ...<Widget>[
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.tonalIcon(
                    onPressed: () => Navigator.of(context).pop(
                      Match3dUpgradeAction.upgradeTournament,
                    ),
                    icon: const Icon(Icons.workspace_premium_outlined),
                    label: const Text('Upgrade Tournament Experience'),
                  ),
                ),
              ],
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: TextButton(
                  onPressed: () => Navigator.of(context).pop(
                    Match3dUpgradeAction.continueIn2d,
                  ),
                  child: const Text('Continue in 2D'),
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
              style: theme.textTheme.bodySmall?.copyWith(
                color: Colors.white70,
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.tonal(
              onPressed: onPressed,
              child: Text(actionLabel),
            ),
          ],
        ),
      ),
    );
  }
}

class _PriceCard extends StatelessWidget {
  const _PriceCard({
    required this.title,
    required this.subtitle,
    required this.priceLabel,
    required this.accentColor,
  });

  final String title;
  final String subtitle;
  final String priceLabel;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: accentColor.withValues(alpha: 0.34)),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Colors.white70,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            priceLabel,
            style: theme.textTheme.titleSmall?.copyWith(
              color: accentColor,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

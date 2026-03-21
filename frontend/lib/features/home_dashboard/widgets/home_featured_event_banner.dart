import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class HomeFeaturedEventBanner extends StatelessWidget {
  const HomeFeaturedEventBanner({
    super.key,
    required this.label,
    required this.title,
    required this.summary,
    required this.body,
    required this.icon,
    required this.gradientColors,
    this.stats = const <MapEntry<String, String>>[],
    this.actionLabel,
    this.onPressed,
  });

  final String label;
  final String title;
  final String summary;
  final String body;
  final IconData icon;
  final List<Color> gradientColors;
  final List<MapEntry<String, String>> stats;
  final String? actionLabel;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);

    return GteSurfacePanel(
      emphasized: true,
      padding: EdgeInsets.zero,
      onTap: onPressed,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(tokens.radiusLarge),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: gradientColors,
          ),
        ),
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: <Widget>[
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(tokens.radiusMedium),
                    color: Colors.white.withValues(alpha: 0.08),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.14),
                    ),
                  ),
                  child: Icon(icon, color: GteShellTheme.accentWarm),
                ),
                _BannerTag(label: label, color: GteShellTheme.accentWarm),
                _BannerTag(label: 'Live lobby', color: GteShellTheme.accent),
              ],
            ),
            const SizedBox(height: 20),
            Text(title, style: Theme.of(context).textTheme.displaySmall),
            const SizedBox(height: 10),
            Text(
              summary,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 12),
            Text(
              body,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.textPrimary.withValues(alpha: 0.82),
                  ),
            ),
            if (stats.isNotEmpty) ...<Widget>[
              const SizedBox(height: 18),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: stats
                    .take(3)
                    .map(
                      (MapEntry<String, String> item) => _BannerStat(
                        label: item.key,
                        value: item.value,
                      ),
                    )
                    .toList(growable: false),
              ),
            ],
            if (actionLabel != null && onPressed != null) ...<Widget>[
              const SizedBox(height: 22),
              FilledButton.icon(
                onPressed: onPressed,
                icon: const Icon(Icons.bolt_outlined),
                label: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _BannerTag extends StatelessWidget {
  const _BannerTag({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.14),
        border: Border.all(
          color: color.withValues(alpha: 0.35),
        ),
      ),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: color,
              letterSpacing: 1.1,
            ),
      ),
    );
  }
}

class _BannerStat extends StatelessWidget {
  const _BannerStat({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: GteShellTheme.textPrimary.withValues(alpha: 0.72),
                  letterSpacing: 0.9,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: GteShellTheme.textPrimary,
                ),
          ),
        ],
      ),
    );
  }
}

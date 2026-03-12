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
    return GteSurfacePanel(
      emphasized: true,
      padding: EdgeInsets.zero,
      onTap: onPressed,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
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
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    color: Colors.white.withValues(alpha: 0.08),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.14),
                    ),
                  ),
                  child: Icon(icon, color: GteShellTheme.accentWarm),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: GteShellTheme.accentWarm.withValues(alpha: 0.14),
                    border: Border.all(
                      color: GteShellTheme.accentWarm.withValues(alpha: 0.35),
                    ),
                  ),
                  child: Text(
                    label.toUpperCase(),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: GteShellTheme.accentWarm,
                          letterSpacing: 1.2,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(title, style: Theme.of(context).textTheme.displaySmall),
            const SizedBox(height: 10),
            Text(summary, style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 14),
            Text(
              body,
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
              FilledButton.tonalIcon(
                onPressed: onPressed,
                icon: const Icon(Icons.open_in_new_outlined),
                label: Text(actionLabel!),
              ),
            ],
          ],
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
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GteShellTheme.textPrimary.withValues(alpha: 0.72),
                ),
          ),
          const SizedBox(height: 4),
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

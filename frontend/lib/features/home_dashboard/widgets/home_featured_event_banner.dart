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
    final theme = Theme.of(context);

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
        child: Stack(
          children: <Widget>[
            Positioned(
              right: -18,
              top: -18,
              child: Opacity(
                opacity: 0.16,
                child: Image.asset(
                  'assets/branding/gtex_logo.png',
                  width: 180,
                  fit: BoxFit.contain,
                ),
              ),
            ),
            Positioned(
              right: 24,
              bottom: 24,
              child: IgnorePointer(
                child: Container(
                  width: 170,
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(tokens.radiusMedium),
                    color: Colors.black.withValues(alpha: 0.22),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.14),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'MATCH SIGNAL',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: GteShellTheme.accentArena,
                        ),
                      ),
                      const SizedBox(height: 10),
                      _BannerSignalRow(
                        label: 'Board',
                        value: 'Live',
                        color: GteShellTheme.accent,
                      ),
                      const SizedBox(height: 10),
                      _BannerSignalRow(
                        label: 'Volume',
                        value: stats.isNotEmpty ? stats.first.value : 'Hot',
                        color: GteShellTheme.accentCapital,
                      ),
                      const SizedBox(height: 10),
                      _BannerSignalRow(
                        label: 'Story',
                        value: 'Active',
                        color: GteShellTheme.accentWarm,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 260),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: <Widget>[
                        Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(
                              tokens.radiusMedium,
                            ),
                            color: Colors.white.withValues(alpha: 0.08),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.14),
                            ),
                          ),
                          child: Icon(icon, color: GteShellTheme.accentWarm),
                        ),
                        _BannerTag(
                          label: label,
                          color: GteShellTheme.accentWarm,
                        ),
                        _BannerTag(
                          label: 'Breaking',
                          color: GteShellTheme.accentArena,
                        ),
                        _BannerTag(
                          label: 'GTEX TV',
                          color: GteShellTheme.accent,
                        ),
                      ],
                    ),
                    const SizedBox(height: 22),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 620),
                      child: Text(title, style: theme.textTheme.displaySmall),
                    ),
                    const SizedBox(height: 12),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 620),
                      child: Text(
                        summary,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: GteShellTheme.textPrimary.withValues(
                            alpha: 0.92,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 620),
                      child: Text(
                        body,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: GteShellTheme.textPrimary.withValues(
                            alpha: 0.78,
                          ),
                        ),
                      ),
                    ),
                    if (stats.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 22),
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
                        icon: const Icon(Icons.live_tv_rounded),
                        label: Text(actionLabel!),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BannerTag extends StatelessWidget {
  const _BannerTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(
          context,
        ).textTheme.labelLarge?.copyWith(color: color, letterSpacing: 1.1),
      ),
    );
  }
}

class _BannerStat extends StatelessWidget {
  const _BannerStat({required this.label, required this.value});

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
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: GteShellTheme.textPrimary),
          ),
        ],
      ),
    );
  }
}

class _BannerSignalRow extends StatelessWidget {
  const _BannerSignalRow({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GteShellTheme.textPrimary.withValues(alpha: 0.66),
              letterSpacing: 0.8,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          value,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: GteShellTheme.textPrimary,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}

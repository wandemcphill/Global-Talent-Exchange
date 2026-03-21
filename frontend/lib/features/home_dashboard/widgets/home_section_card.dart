import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class HomeSectionCard extends StatelessWidget {
  const HomeSectionCard({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.summary,
    required this.icon,
    required this.accent,
    this.detail,
    this.stats = const <MapEntry<String, String>>[],
    this.highlights = const <String>[],
    this.actionLabel,
    this.onTap,
  });

  final String eyebrow;
  final String title;
  final String summary;
  final String? detail;
  final IconData icon;
  final Color accent;
  final List<MapEntry<String, String>> stats;
  final List<String> highlights;
  final String? actionLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);

    return GteSurfacePanel(
      onTap: onTap,
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(tokens.radiusMedium - 2),
                  color: accent.withValues(alpha: 0.16),
                  border: Border.all(
                    color: accent.withValues(alpha: 0.28),
                  ),
                ),
                child: Icon(icon, color: accent),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(tokens.radiusPill),
                        color: accent.withValues(alpha: 0.14),
                        border: Border.all(
                          color: accent.withValues(alpha: 0.22),
                        ),
                      ),
                      child: Text(
                        eyebrow.toUpperCase(),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: accent,
                              letterSpacing: 1,
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ],
                ),
              ),
              if (actionLabel != null && onTap != null) ...<Widget>[
                const SizedBox(width: 10),
                Icon(
                  Icons.arrow_outward_rounded,
                  color: accent,
                  size: 20,
                ),
              ],
            ],
          ),
          const SizedBox(height: 18),
          Text(
            summary,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  height: 1.45,
                ),
          ),
          if (detail != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              detail!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
          if (stats.isNotEmpty) ...<Widget>[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: stats
                  .take(3)
                  .map(
                    (MapEntry<String, String> item) => _HomeStatChip(
                      label: item.key,
                      value: item.value,
                      accent: accent,
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
          if (highlights.isNotEmpty) ...<Widget>[
            const SizedBox(height: 16),
            Text(
              'Pitch notes',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: accent,
                    letterSpacing: 0.9,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 10),
            ...highlights.take(2).map(
                  (String line) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                          width: 22,
                          height: 22,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: accent.withValues(alpha: 0.14),
                          ),
                          child: Icon(
                            Icons.sports_soccer,
                            size: 12,
                            color: accent,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            line,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
          ],
          if (actionLabel != null && onTap != null) ...<Widget>[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onTap,
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(actionLabel!),
            ),
          ],
        ],
      ),
    );
  }
}

class _HomeStatChip extends StatelessWidget {
  const _HomeStatChip({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(tokens.radiusMedium - 4),
        color: tokens.panelStrong.withValues(alpha: 0.84),
        border: Border.all(color: tokens.stroke),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  letterSpacing: 0.9,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: accent,
                ),
          ),
        ],
      ),
    );
  }
}

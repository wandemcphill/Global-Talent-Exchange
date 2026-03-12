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
    return GteSurfacePanel(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: accent.withValues(alpha: 0.14),
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
                    Text(
                      eyebrow.toUpperCase(),
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: accent,
                            letterSpacing: 1.1,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(summary, style: Theme.of(context).textTheme.bodyLarge),
          if (detail != null) ...<Widget>[
            const SizedBox(height: 10),
            Text(detail!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          if (stats.isNotEmpty) ...<Widget>[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: stats
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
            ...highlights.take(3).map(
                  (String line) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Icon(
                            Icons.fiber_manual_record,
                            size: 10,
                            color: accent,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            line,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
          ],
          if (actionLabel != null && onTap != null) ...<Widget>[
            const SizedBox(height: 18),
            FilledButton.tonalIcon(
              onPressed: onTap,
              icon: const Icon(Icons.arrow_forward_outlined),
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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.84),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
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

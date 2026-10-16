import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class TrophyCountCard extends StatelessWidget {
  const TrophyCountCard({
    super.key,
    required this.label,
    required this.count,
    required this.caption,
    this.emphasized = false,
  });

  final String label;
  final int count;
  final String caption;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        emphasized ? GteShellTheme.accentWarm : GteShellTheme.accent;
    return SizedBox(
      width: 172,
      child: GteSurfacePanel(
        emphasized: emphasized,
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 10),
            Text(
              '$count',
              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    fontSize: 30,
                    color: accent,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              caption,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withValues(alpha: 0.82),
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

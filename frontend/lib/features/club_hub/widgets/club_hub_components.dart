import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubHubStatCard extends StatelessWidget {
  const ClubHubStatCard({
    super.key,
    required this.label,
    required this.value,
    required this.detail,
    required this.icon,
  });

  final String label;
  final String value;
  final String detail;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent = tokens.accentClub;

    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 220, maxWidth: 260),
      child: GteSurfacePanel(
        accentColor: accent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(tokens.radiusMedium - 2),
                color: accent.withValues(alpha: 0.14),
                border: Border.all(color: accent.withValues(alpha: 0.2)),
              ),
              child: Icon(icon, color: accent),
            ),
            const SizedBox(height: 14),
            Text(
              label.toUpperCase(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: accent,
                    letterSpacing: 0.9,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 10),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 6),
            Text(
              detail,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class ClubHubMetricRow extends StatelessWidget {
  const ClubHubMetricRow({
    super.key,
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Row(
              children: <Widget>[
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: GteShellTheme.accentClub,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class ClubHubPill extends StatelessWidget {
  const ClubHubPill({
    super.key,
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.accentClub.withValues(alpha: 0.14),
        border:
            Border.all(color: GteShellTheme.accentClub.withValues(alpha: 0.22)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: GteShellTheme.accentClub,
            ),
      ),
    );
  }
}

class ClubColorPill extends StatelessWidget {
  const ClubColorPill({
    super.key,
    required this.label,
    required this.colorHex,
  });

  final String label;
  final String colorHex;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
        color: GteShellTheme.panel.withValues(alpha: 0.86),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: identityColorFromHex(colorHex),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.labelLarge,
          ),
        ],
      ),
    );
  }
}

class TimelineListTile extends StatelessWidget {
  const TimelineListTile({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.valueColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String value;
  final Color valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: GteShellTheme.stroke),
        color: GteShellTheme.panel.withValues(alpha: 0.82),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: GteShellTheme.accent.withValues(alpha: 0.12),
            ),
            child: Icon(icon, size: 18, color: GteShellTheme.accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            value,
            style: Theme.of(context)
                .textTheme
                .labelLarge
                ?.copyWith(color: valueColor),
          ),
        ],
      ),
    );
  }
}

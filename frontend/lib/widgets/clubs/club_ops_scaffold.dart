import 'package:flutter/material.dart';

import '../gte_shell_theme.dart';
import '../gte_surface_panel.dart';

class ClubOpsScaffold extends StatelessWidget {
  const ClubOpsScaffold({
    super.key,
    required this.title,
    required this.body,
    this.subtitle,
    this.actions = const <Widget>[],
  });

  final String title;
  final String? subtitle;
  final Widget body;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
            ],
          ),
          actions: actions,
        ),
        body: body,
      ),
    );
  }
}

class ClubOpsSectionHeader extends StatelessWidget {
  const ClubOpsSectionHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.action,
  });

  final String title;
  final String subtitle;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        if (action != null) ...<Widget>[
          const SizedBox(width: 12),
          action!,
        ],
      ],
    );
  }
}

class ClubOpsStatTile extends StatelessWidget {
  const ClubOpsStatTile({
    super.key,
    required this.label,
    required this.value,
    required this.detail,
    this.icon = Icons.insights_outlined,
    this.highlight = false,
  });

  final String label;
  final String value;
  final String detail;
  final IconData icon;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final Color accent = highlight
        ? GteShellTheme.accentWarm
        : GteShellTheme.accent.withValues(alpha: 0.9);
    return SizedBox(
      width: 220,
      child: GteSurfacePanel(
        emphasized: highlight,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, color: accent),
            const SizedBox(height: 16),
            Text(
              value,
              style: Theme.of(context)
                  .textTheme
                  .headlineSmall
                  ?.copyWith(fontSize: 26, color: Colors.white),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              detail,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class ClubOpsMetricRow extends StatelessWidget {
  const ClubOpsMetricRow({
    super.key,
    required this.label,
    required this.value,
    this.valueColor,
  });

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          const SizedBox(width: 12),
          Text(
            value,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(color: valueColor),
          ),
        ],
      ),
    );
  }
}

class ClubOpsHeadlinePanel extends StatelessWidget {
  const ClubOpsHeadlinePanel({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          child,
        ],
      ),
    );
  }
}

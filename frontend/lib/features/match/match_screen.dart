import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class MatchScreen extends StatelessWidget {
  const MatchScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: 'Matches',
      subtitle:
          'The shipped match tab is now honest. Live spectating and local simulation are distinct routes with different truth states.',
      trailing: const DataSourceBadge(status: DataSourceStatus.live),
      children: <Widget>[
        _RouteCard(
          title: 'Spectate',
          subtitle:
              'Live path. Probes the real match-viewer contract before opening the existing 2D/Broadcast+/3D viewer.',
          statusLabel: 'LIVE when viewer session resolves',
          actionLabel: 'Open Spectate',
          onTap: () => context.push(AppRoutes.matchesSpectate),
        ),
        _RouteCard(
          title: 'Simulate',
          subtitle:
              'Explicitly local path. Uses the existing simulation engine and is labeled as simulation, not a backend feed.',
          statusLabel: 'LOCAL simulation',
          actionLabel: 'Open Simulate',
          onTap: () => context.push(AppRoutes.matchesSimulate),
        ),
      ],
    );
  }
}

class _RouteCard extends StatelessWidget {
  const _RouteCard({
    required this.title,
    required this.subtitle,
    required this.statusLabel,
    required this.actionLabel,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final String statusLabel;
  final String actionLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingXS),
            Text(subtitle),
            const SizedBox(height: spacingSM),
            Chip(label: Text(statusLabel)),
            const SizedBox(height: spacingMD),
            FilledButton(onPressed: onTap, child: Text(actionLabel)),
          ],
        ),
      ),
    );
  }
}

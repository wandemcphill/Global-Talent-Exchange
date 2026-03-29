import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import 'live_match_overview_provider.dart';
import 'match_viewer_capability.dart';

class MatchScreen extends ConsumerWidget {
  const MatchScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    final AsyncValue<LiveMatchOverview> overview = ref.watch(
      liveMatchOverviewProvider,
    );
    final DataSourceStatus status =
        !authenticated || overview.hasError
            ? DataSourceStatus.blocked
            : DataSourceStatus.live;

    return AppPageLayout(
      title: 'Matches',
      subtitle:
          'The shipped Matches tab now reads /api/broadcast/home for live match discovery, launches the existing 2D, pseudo-3D, and Flutter 3D viewers through the active shell, and keeps manual spectate and simulation explicitly labeled.',
      trailing: Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
        children: <Widget>[
          DataSourceBadge(status: status),
          const MatchViewerCapabilityBadge(
            capability: MatchViewerCapability.pseudo3d,
          ),
        ],
      ),
      children: <Widget>[
        overview.when(
          data: (LiveMatchOverview value) {
            if (value.isEmpty) {
              return _StatusCard(
                title: 'No live matches published',
                message:
                    '${value.sourcePath} responded successfully, but it did not publish any current live match programs.',
                footer:
                    value.generatedAt == null
                        ? null
                        : 'Generated ${value.generatedAt!.toIso8601String()}',
              );
            }
            return Column(
              children: <Widget>[
                for (final LiveMatchOverviewEntry entry
                    in value.entries) ...<Widget>[
                  _LiveMatchCard(entry: entry),
                  const SizedBox(height: spacingMD),
                ],
              ],
            );
          },
          loading:
              () => const _StatusCard(
                title: 'Loading live matches',
                message:
                    'The active shell is fetching /api/broadcast/home. No local match fixtures are used on this page.',
              ),
          error:
              (Object error, StackTrace stackTrace) => _StatusCard(
                title: 'Matches are blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
        _ActionCard(
          title: 'Open by match key',
          description:
              'Manual launch path. Probes the real match-viewer contract before opening the existing 2D viewer.',
          chips: const <String>['LIVE', '2D'],
          primaryLabel: 'Open spectate probe',
          onPrimaryTap: () => context.push(AppRoutes.matchesSpectate),
        ),
        _ActionCard(
          title: 'Native 3D status',
          description:
              'Truth label for the native bridge path. The active shell keeps native 3D blocked until the platform bridge is actually present.',
          chips: const <String>['BLOCKED', 'NATIVE_3D'],
          primaryLabel: 'See native 3D status',
          onPrimaryTap: () => context.push(AppRoutes.matchesNativeThreeD),
        ),
        _ActionCard(
          title: 'Simulate',
          description:
              'Explicit local simulation path. This is not presented as a live backend feed.',
          chips: const <String>['DEMO'],
          primaryLabel: 'Open simulate',
          onPrimaryTap: () => context.push(AppRoutes.matchesSimulate),
        ),
      ],
    );
  }
}

class _LiveMatchCard extends StatelessWidget {
  const _LiveMatchCard({required this.entry});

  final LiveMatchOverviewEntry entry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: <Widget>[
                if (entry.isFeatured) const Chip(label: Text('FEATURED')),
                Chip(label: Text(entry.isLive ? 'LIVE' : 'SCHEDULED')),
                Chip(label: Text(entry.channelLabel)),
              ],
            ),
            const SizedBox(height: spacingMD),
            Text(entry.title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingXS),
            Text(entry.subtitle),
            const SizedBox(height: spacingMD),
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: <Widget>[
                FilledButton(
                  onPressed:
                      () => context.push(
                        AppRoutes.matchesViewerLocation(entry.matchKey),
                      ),
                  child: const Text('Open 2D'),
                ),
                OutlinedButton(
                  onPressed:
                      () => context.push(
                        AppRoutes.matchesBroadcastLocation(entry.matchKey),
                      ),
                  child: const Text('Open Broadcast+'),
                ),
                OutlinedButton(
                  onPressed:
                      () => context.push(
                        AppRoutes.matchesThreeDLocation(entry.matchKey),
                      ),
                  child: const Text('Open 3D'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.title,
    required this.description,
    required this.chips,
    required this.primaryLabel,
    required this.onPrimaryTap,
  });

  final String title;
  final String description;
  final List<String> chips;
  final String primaryLabel;
  final VoidCallback onPrimaryTap;

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
            Text(description),
            const SizedBox(height: spacingSM),
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: chips
                  .map((String value) => Chip(label: Text(value)))
                  .toList(growable: false),
            ),
            const SizedBox(height: spacingMD),
            FilledButton(onPressed: onPrimaryTap, child: Text(primaryLabel)),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.title, required this.message, this.footer});

  final String title;
  final String message;
  final String? footer;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingSM),
            Text(message),
            if (footer != null) ...<Widget>[
              const SizedBox(height: spacingSM),
              Text(footer!, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}

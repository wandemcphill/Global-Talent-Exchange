import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
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
    final LiveMatchOverview? snapshot = overview.asData?.value;
    final DataSourceStatus status =
        !authenticated || overview.hasError
            ? DataSourceStatus.blocked
            : DataSourceStatus.live;

    return AppPageLayout(
      title: 'Fixtures',
      subtitle: 'Fixtures, live 2D match viewing, and results for matchday.',
      trailing: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          DataSourceBadge(status: status),
          const MatchViewerCapabilityBadge(
            capability: MatchViewerCapability.twoD,
          ),
        ],
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: authenticated ? 'MATCHDAY LIVE' : 'AUTH REQUIRED',
          title:
              authenticated
                  ? 'Open fixtures and follow matchday in 2D.'
                  : 'Sign in to follow live fixtures and results.',
          description:
              'The launch matchday view only renders backend-published fixtures, scores, realtime overlays, and blocked states when data is missing.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Fixtures',
              value: snapshot == null ? '...' : '${snapshot.entries.length}',
              support: 'Live fixture cards',
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Featured',
              value:
                  snapshot == null
                      ? '...'
                      : '${snapshot.entries.where((LiveMatchOverviewEntry item) => item.isFeatured).length}',
              support: 'Featured fixtures',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Capability',
              value: '2D',
              support: 'Manager matchday view',
              tone: GtexSurfaceTone.warning,
            ),
          ],
        ),
        overview.when(
          data: (LiveMatchOverview value) {
            if (value.isEmpty) {
              return GteStatePanel(
                title: 'No live matches published',
                message:
                    '${value.sourcePath} responded successfully, but it did not publish any current fixtures.',
                icon: Icons.tv_off_rounded,
                accentColor: Theme.of(context).colorScheme.tertiary,
              );
            }
            return Column(
              children: <Widget>[
                GtexSectionPanel(
                  eyebrow: 'LIVE FIXTURES',
                  title: 'Live fixtures',
                  subtitle:
                      value.generatedAt == null
                          ? 'Current fixtures from the matchday feed.'
                          : 'Generated ${value.generatedAt!.toIso8601String()}',
                  child: Column(
                    children: <Widget>[
                      for (final LiveMatchOverviewEntry entry in value.entries)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _LiveMatchCard(entry: entry),
                        ),
                    ],
                  ),
                ),
              ],
            );
          },
          loading:
              () => GteStatePanel(
                title: 'Loading live matches',
                message: 'The active shell is fetching live fixture cards.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => Column(
                children: <Widget>[
                  GteStatePanel(
                    title: 'Matches are blocked',
                    message: AppFeedback.messageFor(error),
                    icon: Icons.error_outline_rounded,
                    accentColor: Theme.of(context).colorScheme.error,
                  ),
                ],
              ),
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
    return GtexSectionPanel(
      eyebrow: entry.isLive ? 'LIVE FIXTURE' : 'SCHEDULED FIXTURE',
      title: entry.title,
      subtitle: entry.subtitle,
      emphasized: entry.isFeatured,
      accentColor:
          entry.isFeatured
              ? Theme.of(context).colorScheme.primary
              : Theme.of(context).colorScheme.secondary,
      trailing: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          if (entry.isFeatured)
            const GtexPill(label: 'FEATURED', tone: GtexSurfaceTone.warning),
          GtexPill(
            label: entry.isLive ? 'LIVE' : 'SCHEDULED',
            tone: entry.isLive ? GtexSurfaceTone.live : GtexSurfaceTone.warning,
          ),
          GtexPill(label: entry.channelLabel, tone: GtexSurfaceTone.info),
        ],
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          FilledButton(
            onPressed:
                () => context.push(
                  AppRoutes.matchesViewerLocation(entry.matchKey),
                ),
            child: const Text('Open Match'),
          ),
        ],
      ),
    );
  }
}

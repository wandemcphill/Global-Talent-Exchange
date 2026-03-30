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
      title: 'Matches',
      subtitle:
          'Premium live match hub for viewer launch, broadcast package entry, and honest separation between live and simulated routes.',
      trailing: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          DataSourceBadge(status: status),
          const MatchViewerCapabilityBadge(
            capability: MatchViewerCapability.pseudo3d,
          ),
        ],
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: authenticated ? 'MATCHDAY LIVE' : 'AUTH REQUIRED',
          title:
              authenticated
                  ? 'Launch the right viewer lane with broadcast-grade clarity.'
                  : 'Sign in before the live broadcast desk can mount match programs.',
          description:
              'The shipped Matches tab reads /api/broadcast/home for live discovery, then routes cleanly into 2D, Broadcast+, and 3D viewers without masking blocked backend truth.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Programs',
              value: snapshot == null ? '...' : '${snapshot.entries.length}',
              support: 'Live broadcast-home cards',
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Featured',
              value:
                  snapshot == null
                      ? '...'
                      : '${snapshot.entries.where((LiveMatchOverviewEntry item) => item.isFeatured).length}',
              support: 'Prime matchday packages',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Capability',
              value: '2D + Broadcast+ + 3D',
              support: 'Viewer lanes remain separate',
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
                    '${value.sourcePath} responded successfully, but it did not publish any current live match programs.',
                icon: Icons.tv_off_rounded,
                accentColor: Theme.of(context).colorScheme.tertiary,
              );
            }
            return Column(
              children: <Widget>[
                GtexSectionPanel(
                  eyebrow: 'LIVE PROGRAMS',
                  title: 'Live programs',
                  subtitle:
                      value.generatedAt == null
                          ? 'Current programs from the broadcast home endpoint.'
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
                const SizedBox(height: 24),
                const _ActionDeck(),
              ],
            );
          },
          loading:
              () => GteStatePanel(
                title: 'Loading live matches',
                message:
                    'The active shell is fetching /api/broadcast/home. No local match fixtures are used on this page.',
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
                  const SizedBox(height: 24),
                  const _ActionDeck(),
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
      eyebrow: entry.isLive ? 'LIVE PROGRAM' : 'SCHEDULED PROGRAM',
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
    );
  }
}

class _ActionDeck extends StatelessWidget {
  const _ActionDeck();

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      eyebrow: 'VIEWER LANES',
      title: 'Blocked probes and truth-preserving side routes',
      subtitle:
          'These routes stay explicit so live, blocked, and simulated states are never confused.',
      child: Column(
        children: <Widget>[
          _ActionCard(
            title: 'Open by match key',
            description:
                'Manual launch path. This route is addressable, but it stays visibly blocked until the live viewer session can be served without fabricated fallback state.',
            chips: const <String>['BLOCKED', '2D'],
            primaryLabel: 'Open spectate probe',
            onPrimaryTap: () => context.push(AppRoutes.matchesSpectate),
          ),
          const SizedBox(height: 12),
          _ActionCard(
            title: 'Native 3D preview',
            description:
                'Product visibility only. The active shell keeps native 3D unshipped until a verified platform bridge is present.',
            chips: const <String>['COMING SOON', 'NATIVE_3D'],
            primaryLabel: 'View coming soon note',
            onPrimaryTap: () => context.push(AppRoutes.matchesNativeThreeD),
          ),
          const SizedBox(height: 12),
          _ActionCard(
            title: 'Simulate',
            description:
                'Explicit local simulation path. This is not presented as a live backend feed.',
            chips: const <String>['DEMO'],
            primaryLabel: 'Open simulate',
            onPrimaryTap: () => context.push(AppRoutes.matchesSimulate),
          ),
        ],
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
    return GtexListTile(
      title: title,
      subtitle: description,
      leadingIcon: Icons.rocket_launch_rounded,
      tone: GtexSurfaceTone.info,
      trailing: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: <Widget>[
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: chips
                .map(
                  (String value) => GtexPill(
                    label: value,
                    tone:
                        value == 'COMING SOON'
                            ? GtexSurfaceTone.warning
                            : GtexSurfaceTone.info,
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: onPrimaryTap, child: Text(primaryLabel)),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../shared/widgets/route_surface_badge.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_world_provider.dart';

class WorldScreen extends ConsumerWidget {
  const WorldScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<WorldAggregateData> worldValue = ref.watch(
      worldAggregateProvider,
    );
    final WorldAggregateData? snapshot = worldValue.asData?.value;
    final AppRouteSurface worldSurface = appRouteSurfaceFor(AppRoutes.world)!;
    return AppPageLayout(
      title: 'World',
      subtitle:
          'Football-universe dashboard for standings, scouting, history, federations, and routed competition families.',
      trailing: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          DataSourceBadge(
            status:
                worldValue.hasError
                    ? DataSourceStatus.blocked
                    : DataSourceStatus.live,
          ),
          RouteSurfaceBadge(state: worldSurface.state),
        ],
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'WORLD OPS',
          title: 'Operate the football universe like a premium broadcast desk.',
          description:
              'World now behaves like a live discovery layer with routed federation and competition entry points rather than a flat placeholder list.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Rising stars',
              value:
                  snapshot == null ? '...' : '${snapshot.risingStars.length}',
              support: 'Live regen-universe prospects',
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Scouting',
              value:
                  snapshot == null ? '...' : '${snapshot.scoutingFeed.length}',
              support: 'Discovery feed items',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Federations',
              value:
                  snapshot == null ? '...' : '${snapshot.federations.length}',
              support: 'Mounted world hubs',
              tone: GtexSurfaceTone.success,
            ),
            GtexStatTile(
              label: 'Season phase',
              value:
                  snapshot == null
                      ? '...'
                      : '${snapshot.tracking['season_phase'] ?? snapshot.tracking['status'] ?? 'live'}',
              support: 'Tracking feed',
              tone: GtexSurfaceTone.warning,
            ),
          ],
          actions: <Widget>[
            FilledButton.icon(
              onPressed: () => context.push(AppRoutes.federations),
              icon: const Icon(Icons.account_tree_rounded),
              label: const Text('Open federations hub'),
            ),
            OutlinedButton.icon(
              onPressed: () => context.push(AppRoutes.nationalTeams),
              icon: const Icon(Icons.flag_circle_rounded),
              label: const Text('Open national teams'),
            ),
          ],
        ),
        _WorldSurfaceDisclosure(surface: worldSurface),
        worldValue.when(
          data:
              (WorldAggregateData world) => Column(
                children: <Widget>[
                  GtexSectionPanel(
                    eyebrow: 'COMPETITION FAMILIES',
                    title: 'Competition families',
                    subtitle:
                        'World is now a live discovery layer. Full lifecycle actions move into routed competition screens.',
                    child: Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        _FamilyButton(
                          label:
                              'GTEX hosted (${world.competitions.gtexCompetitions.length})',
                          onTap:
                              () => context.push(
                                '/competitions/${CompetitionFamilyRoute.gtex.pathSegment}',
                              ),
                        ),
                        _FamilyButton(
                          label:
                              'User hosted (${world.competitions.hostedCompetitions.length})',
                          onTap:
                              () => context.push(
                                '/competitions/${CompetitionFamilyRoute.hosted.pathSegment}',
                              ),
                        ),
                        _FamilyButton(
                          label:
                              'Creator tournaments (${world.competitions.streamerTournaments.length})',
                          onTap:
                              () => context.push(
                                '/competitions/${CompetitionFamilyRoute.streamer.pathSegment}',
                              ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  GtexSectionPanel(
                    eyebrow: 'RISING STARS',
                    title: 'Rising stars',
                    subtitle: 'Live regens from /regen-universe/rising-stars.',
                    child: Column(
                      children: world.risingStars
                          .take(8)
                          .map(
                            (JsonMap item) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: GtexListTile(
                                title: stringValue(
                                  item['player_name'],
                                  fallback: stringValue(item['name']),
                                ),
                                subtitle: item.entries
                                    .take(4)
                                    .map(
                                      (MapEntry<String, Object?> entry) =>
                                          '${entry.key}: ${entry.value}',
                                    )
                                    .join(' | '),
                                leadingIcon: Icons.auto_awesome_rounded,
                                tone: GtexSurfaceTone.live,
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                  const SizedBox(height: 24),
                  GtexSectionPanel(
                    eyebrow: 'SCOUTING',
                    title: 'Scouting feed',
                    subtitle:
                        'Live scouting feed from /regen-universe/scouting-feed.',
                    child: Column(
                      children: world.scoutingFeed
                          .take(6)
                          .map(
                            (JsonMap item) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: GtexListTile(
                                title: stringValue(
                                  item['headline'],
                                  fallback: stringValue(item['player_name']),
                                ),
                                subtitle: item.entries
                                    .take(4)
                                    .map(
                                      (MapEntry<String, Object?> entry) =>
                                          '${entry.key}: ${entry.value}',
                                    )
                                    .join(' | '),
                                leadingIcon: Icons.travel_explore_rounded,
                                tone: GtexSurfaceTone.info,
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                  const SizedBox(height: 24),
                  GtexSectionPanel(
                    eyebrow: 'HISTORY',
                    title: 'History',
                    subtitle:
                        'Seasons, awards, and hall of fame are read from live regen-universe endpoints.',
                    child: Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GtexStatTile(
                          label: 'Seasons',
                          value: '${world.seasons.length}',
                          support: 'Recorded world seasons',
                          tone: GtexSurfaceTone.live,
                        ),
                        GtexStatTile(
                          label: 'Awards',
                          value: '${world.awards.length}',
                          support: 'Tracked accolades',
                          tone: GtexSurfaceTone.warning,
                        ),
                        GtexStatTile(
                          label: 'Hall of fame',
                          value: '${world.hallOfFame.length}',
                          support: 'Legend entries',
                          tone: GtexSurfaceTone.success,
                        ),
                        GtexStatTile(
                          label: 'Tracking',
                          value:
                              '${world.tracking['season_phase'] ?? world.tracking['status'] ?? 'live'}',
                          support: 'Current simulation pulse',
                          tone: GtexSurfaceTone.info,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  GtexSectionPanel(
                    eyebrow: 'FEDERATIONS',
                    title: 'Federations',
                    subtitle:
                        'The world summary now links each federation into a live detail route. ${world.federationJoinReason}',
                    child: Column(
                      children: world.federations
                          .take(8)
                          .map(
                            (JsonMap item) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: GtexListTile(
                                title: stringValue(
                                  item['name'],
                                  fallback: stringValue(item['id']),
                                ),
                                subtitle: item.entries
                                    .take(4)
                                    .map(
                                      (MapEntry<String, Object?> entry) =>
                                          '${entry.key}: ${entry.value}',
                                    )
                                    .join(' | '),
                                leadingIcon: Icons.public_rounded,
                                tone: GtexSurfaceTone.success,
                                trailing: FilledButton(
                                  onPressed:
                                      () => context.push(
                                        AppRoutes.federationDetailLocation(
                                          stringValue(item['id']),
                                        ),
                                      ),
                                  child: const Text('Open'),
                                ),
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                ],
              ),
          loading:
              () => GteStatePanel(
                title: 'Loading world',
                message:
                    'The active shell is pulling live world-universe state.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                title: 'World is blocked',
                message: AppFeedback.messageFor(error),
                icon: Icons.error_outline_rounded,
                accentColor: Theme.of(context).colorScheme.error,
              ),
        ),
      ],
    );
  }
}

class _WorldSurfaceDisclosure extends StatelessWidget {
  const _WorldSurfaceDisclosure({required this.surface});

  final AppRouteSurface surface;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      eyebrow: 'ROUTE TRUTH',
      title: 'World route',
      subtitle: surface.summary,
      trailing: RouteSurfaceBadge(state: surface.state),
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: <Widget>[
          GtexPill(label: surface.label, tone: GtexSurfaceTone.info),
          GtexPill(
            label: surface.state.inventoryLabel,
            tone: GtexSurfaceTone.warning,
          ),
        ],
      ),
    );
  }
}

class _FamilyButton extends StatelessWidget {
  const _FamilyButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      onPressed: onTap,
      icon: const Icon(Icons.open_in_new_rounded),
      label: Text(label),
    );
  }
}

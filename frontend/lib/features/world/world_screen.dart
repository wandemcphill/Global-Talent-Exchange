import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/route_surface_badge.dart';
import 'live_world_provider.dart';

class WorldScreen extends ConsumerWidget {
  const WorldScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<WorldAggregateData> worldValue = ref.watch(
      worldAggregateProvider,
    );
    final AppRouteSurface worldSurface = appRouteSurfaceFor(AppRoutes.world)!;
    return AppPageLayout(
      title: 'World',
      subtitle:
          'World remains the discovery layer, but federations and national teams now route into live backend-backed module screens instead of stopping at placeholder cards.',
      trailing: Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
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
        _WorldSurfaceDisclosure(surface: worldSurface),
        worldValue.when(
          data:
              (WorldAggregateData world) => Column(
                children: <Widget>[
                  _SectionCard(
                    title: 'Competition families',
                    subtitle:
                        'World is now a live discovery layer. Full lifecycle actions move into routed competition screens.',
                    child: Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
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
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'World hubs',
                    subtitle:
                        'High-value world modules now open dedicated live routes from this screen.',
                    child: Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        _FamilyButton(
                          label: 'Federations hub',
                          onTap: () => context.push(AppRoutes.federations),
                        ),
                        _FamilyButton(
                          label: 'National teams',
                          onTap: () => context.push(AppRoutes.nationalTeams),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'Rising stars',
                    subtitle: 'Live regens from /regen-universe/rising-stars.',
                    child: Column(
                      children: world.risingStars
                          .take(8)
                          .map(
                            (JsonMap item) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                stringValue(
                                  item['player_name'],
                                  fallback: stringValue(item['name']),
                                ),
                              ),
                              subtitle: Text(
                                item.entries
                                    .take(4)
                                    .map(
                                      (MapEntry<String, Object?> entry) =>
                                          '${entry.key}: ${entry.value}',
                                    )
                                    .join(' | '),
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'Scouting feed',
                    subtitle:
                        'Live scouting feed from /regen-universe/scouting-feed.',
                    child: Column(
                      children: world.scoutingFeed
                          .take(6)
                          .map(
                            (JsonMap item) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                stringValue(
                                  item['headline'],
                                  fallback: stringValue(item['player_name']),
                                ),
                              ),
                              subtitle: Text(
                                item.entries
                                    .take(4)
                                    .map(
                                      (MapEntry<String, Object?> entry) =>
                                          '${entry.key}: ${entry.value}',
                                    )
                                    .join(' | '),
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'History',
                    subtitle:
                        'Seasons, awards, and hall of fame are read from live regen-universe endpoints.',
                    child: Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        Chip(label: Text('Seasons ${world.seasons.length}')),
                        Chip(label: Text('Awards ${world.awards.length}')),
                        Chip(
                          label: Text(
                            'Hall of fame ${world.hallOfFame.length}',
                          ),
                        ),
                        Chip(
                          label: Text(
                            'Tracking ${world.tracking['season_phase'] ?? world.tracking['status'] ?? 'live'}',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'Federations',
                    subtitle:
                        'The world summary now links each federation into a live detail route. ${world.federationJoinReason}',
                    child: Column(
                      children: world.federations
                          .take(8)
                          .map(
                            (JsonMap item) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                stringValue(
                                  item['name'],
                                  fallback: stringValue(item['id']),
                                ),
                              ),
                              subtitle: Text(
                                item.entries
                                    .take(4)
                                    .map(
                                      (MapEntry<String, Object?> entry) =>
                                          '${entry.key}: ${entry.value}',
                                    )
                                    .join(' | '),
                              ),
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
                          )
                          .toList(growable: false),
                    ),
                  ),
                ],
              ),
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'World is blocked',
                message: AppFeedback.messageFor(error),
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
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: <Widget>[
                Text(
                  '${surface.label} route',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                RouteSurfaceBadge(state: surface.state),
              ],
            ),
            const SizedBox(height: spacingSM),
            Text(surface.summary),
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

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
            const SizedBox(height: spacingMD),
            child,
          ],
        ),
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

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

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
          ],
        ),
      ),
    );
  }
}

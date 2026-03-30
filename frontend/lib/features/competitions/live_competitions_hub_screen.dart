import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../data/hosted_competition_api.dart';
import '../../features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import '../../models/competition_models.dart';
import '../../models/hosted_competition_models.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import 'live_competitions_provider.dart';

class LiveCompetitionsHubScreen extends ConsumerWidget {
  const LiveCompetitionsHubScreen({super.key, this.family});

  final CompetitionFamilyRoute? family;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<CompetitionHubData> hubValue = ref.watch(
      competitionHubProvider,
    );
    return AppPageLayout(
      title: family?.label ?? 'Competitions',
      subtitle:
          family == null
              ? 'The active shell now routes three competition families separately and keeps their backend contracts distinct.'
              : 'This family is sourced from one live backend flow. Deeper actions stay on dedicated detail screens.',
      trailing: DataSourceBadge(
        status:
            hubValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        hubValue.when(
          data:
              (CompetitionHubData hub) =>
                  family == null
                      ? _FamilyOverview(hub: hub)
                      : _FamilyList(family: family!, hub: hub),
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Competition discovery is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }
}

class LiveCompetitionDetailScreen extends ConsumerWidget {
  const LiveCompetitionDetailScreen({
    super.key,
    required this.family,
    required this.competitionId,
  });

  final CompetitionFamilyRoute family;
  final String competitionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppPageLayout(
      title: family.label,
      subtitle:
          'Live actions are only enabled when the session and backend route genuinely allow them.',
      trailing: const DataSourceBadge(status: DataSourceStatus.live),
      children: <Widget>[
        switch (family) {
          CompetitionFamilyRoute.gtex => _GtexDetail(id: competitionId),
          CompetitionFamilyRoute.hosted => _HostedDetail(id: competitionId),
          CompetitionFamilyRoute.streamer => _StreamerDetail(id: competitionId),
        },
      ],
    );
  }
}

class _FamilyOverview extends StatelessWidget {
  const _FamilyOverview({required this.hub});

  final CompetitionHubData hub;

  @override
  Widget build(BuildContext context) {
    final List<_FamilyCardData> cards = <_FamilyCardData>[
      _FamilyCardData(
        family: CompetitionFamilyRoute.gtex,
        count: hub.gtexCompetitions.length,
        description:
            'Platform-run football competitions from /api/competitions.',
      ),
      _FamilyCardData(
        family: CompetitionFamilyRoute.hosted,
        count: hub.hostedCompetitions.length,
        description:
            'User-hosted football competitions from /hosted-competitions.',
      ),
      _FamilyCardData(
        family: CompetitionFamilyRoute.streamer,
        count: hub.streamerTournaments.length,
        description:
            'Creator-hosted e-game tournaments from /streamer-tournaments.',
      ),
    ];

    return Wrap(
      spacing: spacingMD,
      runSpacing: spacingMD,
      children: cards
          .map(
            (_FamilyCardData card) => SizedBox(
              width: 360,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(spacingLG),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        card.family.label,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: spacingSM),
                      Text(card.description),
                      const SizedBox(height: spacingMD),
                      Text(
                        '${card.count} live item${card.count == 1 ? '' : 's'}',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: spacingMD),
                      Wrap(
                        spacing: spacingSM,
                        runSpacing: spacingSM,
                        children: <Widget>[
                          FilledButton.icon(
                            onPressed:
                                () => context.push(
                                  '/competitions/${card.family.pathSegment}',
                                ),
                            icon: const Icon(Icons.open_in_new_rounded),
                            label: const Text('Open family'),
                          ),
                          if (card.family == CompetitionFamilyRoute.streamer)
                            OutlinedButton.icon(
                              onPressed:
                                  () => context.push(AppRoutes.streamerEngine),
                              icon: const Icon(Icons.live_tv_rounded),
                              label: const Text('Open full engine'),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _FamilyList extends StatelessWidget {
  const _FamilyList({required this.family, required this.hub});

  final CompetitionFamilyRoute family;
  final CompetitionHubData hub;

  @override
  Widget build(BuildContext context) {
    final List<Widget> cards = switch (family) {
      CompetitionFamilyRoute.gtex => hub.gtexCompetitions
          .map(
            (CompetitionSummary item) => _competitionCard(
              context: context,
              title: item.name,
              subtitle:
                  '${item.creatorLabel} | ${item.status.name} | ${item.participantCount}/${item.capacity}',
              description: item.rulesSummary,
              path: '/competitions/${family.pathSegment}/${item.id}',
            ),
          )
          .toList(growable: false),
      CompetitionFamilyRoute.hosted => hub.hostedCompetitions
          .map(
            (HostedCompetition item) => _competitionCard(
              context: context,
              title: item.title,
              subtitle:
                  '${item.status} | host ${item.hostUserId} | cap ${item.maxParticipants}',
              description:
                  item.description.isEmpty
                      ? 'Hosted football competition'
                      : item.description,
              path: '/competitions/${family.pathSegment}/${item.id}',
            ),
          )
          .toList(growable: false),
      CompetitionFamilyRoute.streamer => hub.streamerTournaments
          .map(
            (StreamerTournament item) => _competitionCard(
              context: context,
              title: item.title,
              subtitle:
                  '${item.status} | ${item.approvalStatus} | ${item.entries.length}/${item.maxParticipants}',
              description:
                  item.description ?? 'Creator-hosted e-game tournament',
              path: '/competitions/${family.pathSegment}/${item.id}',
            ),
          )
          .toList(growable: false),
    };

    return Column(children: cards);
  }

  Widget _competitionCard({
    required BuildContext context,
    required String title,
    required String subtitle,
    required String description,
    required String path,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingMD),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(spacingLG),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: spacingXS),
              Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: spacingSM),
              Text(description),
              const SizedBox(height: spacingMD),
              FilledButton.icon(
                onPressed: () => context.push(path),
                icon: const Icon(Icons.open_in_new_rounded),
                label: const Text('View detail'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GtexDetail extends ConsumerWidget {
  const _GtexDetail({required this.id});

  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<GtexCompetitionDetailBundle> detail = ref.watch(
      gtexCompetitionDetailProvider(id),
    );
    final String? userId = ref.watch(currentUserIdProvider);
    final String? userName = ref.watch(currentUserNameProvider);
    final bool isAdmin = ref.watch(isAdminProvider);
    final bool canManageCompetitions = ref.watch(canManageCompetitionsProvider);

    return detail.when(
      data: (GtexCompetitionDetailBundle value) {
        final CompetitionSummary item = value.competition;
        return _DetailCard(
          title: item.name,
          description: item.rulesSummary,
          metrics: <String>[
            'Status ${item.status.name}',
            'Participants ${item.participantCount}/${item.capacity}',
            'Prize ${value.financials.prizePool.toStringAsFixed(0)} ${value.financials.currency.toUpperCase()}',
            'Standings ${value.standings.length}',
            'Fixtures ${value.fixtures.length}',
            if (isAdmin && !canManageCompetitions)
              'Publish blocked: manage_competitions required',
          ],
          actions: <Widget>[
            FilledButton(
              onPressed:
                  userId == null || !item.joinEligibility.eligible
                      ? null
                      : () async {
                        try {
                          await ref
                              .read(authedApiProvider)
                              .post(
                                '/api/competitions/${item.id}/join',
                                body: <String, Object?>{
                                  'user_id': userId,
                                  if (userName != null &&
                                      userName.trim().isNotEmpty)
                                    'user_name': userName.trim(),
                                },
                              );
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            gtexCompetitionDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Competition joined.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      },
              child: const Text('Join'),
            ),
            OutlinedButton(
              onPressed:
                  canManageCompetitions
                      ? () async {
                        try {
                          await ref
                              .read(authedApiProvider)
                              .post(
                                '/api/competitions/${item.id}/publish',
                                body: const <String, Object?>{
                                  'open_for_join': true,
                                },
                              );
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            gtexCompetitionDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Competition published.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      }
                      : null,
              child: const Text('Publish'),
            ),
            OutlinedButton(
              onPressed:
                  canManageCompetitions
                      ? () async {
                        try {
                          await ref
                              .read(authedApiProvider)
                              .post('/api/competitions/${item.id}/launch');
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            gtexCompetitionDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Competition launched.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      }
                      : null,
              child: const Text('Launch'),
            ),
          ],
        );
      },
      loading: _loading,
      error:
          (Object error, StackTrace stackTrace) => _BlockedCard(
            title: 'GTEX competition detail is blocked',
            message: AppFeedback.messageFor(error),
          ),
    );
  }
}

class _HostedDetail extends ConsumerWidget {
  const _HostedDetail({required this.id});

  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<HostedCompetitionDetailBundle> detail = ref.watch(
      hostedCompetitionDetailProvider(id),
    );
    final String? userId = ref.watch(currentUserIdProvider);
    final bool isAdmin = ref.watch(isAdminProvider);
    final HostedCompetitionApi api = ref.watch(hostedCompetitionApiProvider);

    return detail.when(
      data: (HostedCompetitionDetailBundle value) {
        final HostedCompetition item = value.detail.competition;
        return _DetailCard(
          title: item.title,
          description:
              item.description.isEmpty
                  ? 'Hosted football competition'
                  : item.description,
          metrics: <String>[
            'Status ${item.status}',
            'Participants ${value.detail.currentParticipants}/${item.maxParticipants}',
            'Reward ${value.finance.projectedRewardPool.toStringAsFixed(0)} ${value.finance.currency}',
            'Standings ${value.standings.length}',
          ],
          actions: <Widget>[
            FilledButton(
              onPressed:
                  userId == null || !value.detail.joinOpen
                      ? null
                      : () async {
                        try {
                          await api.joinCompetition(item.id);
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            hostedCompetitionDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Competition joined.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      },
              child: const Text('Join'),
            ),
            OutlinedButton(
              onPressed:
                  userId == item.hostUserId || isAdmin
                      ? () async {
                        try {
                          await api.launchCompetition(item.id);
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            hostedCompetitionDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Competition launched.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      }
                      : null,
              child: const Text('Launch'),
            ),
          ],
        );
      },
      loading: _loading,
      error:
          (Object error, StackTrace stackTrace) => _BlockedCard(
            title: 'Hosted competition detail is blocked',
            message: AppFeedback.messageFor(error),
          ),
    );
  }
}

class _StreamerDetail extends ConsumerWidget {
  const _StreamerDetail({required this.id});

  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<StreamerTournamentDetailBundle> detail = ref.watch(
      streamerTournamentDetailProvider(id),
    );
    final String? userId = ref.watch(currentUserIdProvider);
    final bool isAdmin = ref.watch(isAdminProvider);

    return detail.when(
      data: (StreamerTournamentDetailBundle value) {
        final StreamerTournament item = value.tournament;
        return _DetailCard(
          title: item.title,
          description: item.description ?? 'Creator-hosted e-game tournament',
          metrics: <String>[
            'Status ${item.status}',
            'Review ${item.approvalStatus}',
            'Entries ${item.entries.length}/${item.maxParticipants}',
            'Season ${value.currentSeason.status}',
          ],
          actions: <Widget>[
            FilledButton(
              onPressed:
                  userId == null
                      ? null
                      : () async {
                        try {
                          await ref
                              .read(streamerTournamentRepositoryProvider)
                              .joinTournament(
                                item.id,
                                const StreamerTournamentJoinRequest(),
                              );
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            streamerTournamentDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Tournament joined.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      },
              child: const Text('Join'),
            ),
            OutlinedButton(
              onPressed:
                  userId == item.hostUserId || isAdmin
                      ? () async {
                        try {
                          await ref
                              .read(streamerTournamentRepositoryProvider)
                              .publishTournament(
                                item.id,
                                const StreamerTournamentPublishRequest(),
                              );
                          ref.invalidate(competitionHubProvider);
                          ref.invalidate(
                            streamerTournamentDetailProvider(item.id),
                          );
                          if (context.mounted) {
                            AppFeedback.showSuccess(
                              context,
                              'Tournament published.',
                            );
                          }
                        } catch (error) {
                          if (context.mounted) {
                            AppFeedback.showError(context, error);
                          }
                        }
                      }
                      : null,
              child: const Text('Publish'),
            ),
          ],
        );
      },
      loading: _loading,
      error:
          (Object error, StackTrace stackTrace) => _BlockedCard(
            title: 'Streamer tournament detail is blocked',
            message: AppFeedback.messageFor(error),
          ),
    );
  }
}

Widget _loading() {
  return const Center(
    child: Padding(
      padding: EdgeInsets.all(spacingLG),
      child: CircularProgressIndicator(),
    ),
  );
}

class _DetailCard extends StatelessWidget {
  const _DetailCard({
    required this.title,
    required this.description,
    required this.metrics,
    required this.actions,
  });

  final String title;
  final String description;
  final List<String> metrics;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: spacingSM),
            Text(description),
            const SizedBox(height: spacingMD),
            Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: metrics
                  .map((String metric) => Chip(label: Text(metric)))
                  .toList(growable: false),
            ),
            const SizedBox(height: spacingMD),
            Wrap(spacing: spacingSM, runSpacing: spacingSM, children: actions),
          ],
        ),
      ),
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

class _FamilyCardData {
  const _FamilyCardData({
    required this.family,
    required this.count,
    required this.description,
  });

  final CompetitionFamilyRoute family;
  final int count;
  final String description;
}

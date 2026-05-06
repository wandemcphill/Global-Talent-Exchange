import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
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
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_competitions_provider.dart';

class LiveCompetitionsHubScreen extends ConsumerWidget {
  const LiveCompetitionsHubScreen({super.key, this.family});

  final CompetitionFamilyRoute? family;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<CompetitionHubData> hubValue = ref.watch(
      competitionHubProvider,
    );
    final CompetitionHubData? snapshot = hubValue.asData?.value;
    return AppPageLayout(
      title: family?.label ?? 'Arena',
      subtitle:
          family == null
              ? 'Live arena for cups, leagues, hosted competitions, and prize boards.'
              : 'Fixtures, standings, results, and prize pools stay in dedicated arena routes.',
      trailing: DataSourceBadge(
        status:
            hubValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: family == null ? 'ARENA' : 'ARENA DETAIL',
          title:
              family == null
                  ? 'Build your football calendar with leagues, cups, and hosted showpieces.'
                  : '${family!.label} arena routes are ready for matchday.',
          description:
              family == null
                  ? 'Create competitions, join live fixtures, track standings, and chase prize pools from one arena desk.'
                  : 'Join, manage, view fixtures, check standings, and review results when your session allows it.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Official',
              value:
                  snapshot == null
                      ? '...'
                      : '${snapshot.gtexCompetitions.length}',
              support: 'Platform-run football',
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Manager Cups',
              value:
                  snapshot == null
                      ? '...'
                      : '${snapshot.userCompetitions.length}',
              support: 'User-hosted football',
              tone: GtexSurfaceTone.info,
            ),
          ],
          actions:
              family == null
                  ? <Widget>[
                    FilledButton.icon(
                      onPressed:
                          () => context.push(AppRoutes.competitionsCreate),
                      icon: const Icon(Icons.add_circle_outline),
                      label: const Text('Create arena'),
                    ),
                  ]
                  : const <Widget>[],
        ),
        hubValue.when(
          data:
              (CompetitionHubData hub) =>
                  family == null
                      ? _FamilyOverview(hub: hub)
                      : _FamilyList(family: family!, hub: hub),
          loading:
              () => GteStatePanel(
                title: 'Loading competitions',
                message:
                    'The active shell is pulling live competition families.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                title: 'Competition discovery is blocked',
                message: AppFeedback.messageFor(error),
                icon: Icons.error_outline_rounded,
                accentColor: Theme.of(context).colorScheme.error,
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
          'Live arena actions are only enabled when the session and backend route genuinely allow them.',
      trailing: const DataSourceBadge(status: DataSourceStatus.live),
      children: <Widget>[
        switch (family) {
          CompetitionFamilyRoute.gtex => _GtexDetail(id: competitionId),
          CompetitionFamilyRoute.hosted => _GtexDetail(id: competitionId),
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
        description: 'Admin-hosted football competitions from /api/competitions.',
      ),
      _FamilyCardData(
        family: CompetitionFamilyRoute.hosted,
        count: hub.userCompetitions.length,
        description: 'Manager-created competitions using Fan Coin entry rules.',
      ),
    ];

    return Wrap(
      spacing: 16,
      runSpacing: 16,
      children: cards
          .map(
            (_FamilyCardData card) => SizedBox(
              width: 360,
              child: GtexSectionPanel(
                eyebrow: 'FAMILY',
                title: card.family.label,
                subtitle: card.description,
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    GtexStatTile(
                      label: 'Live competitions',
                      value: '${card.count}',
                      support:
                          card.count == 1
                              ? '1 competition'
                              : 'competition board',
                      tone: GtexSurfaceTone.live,
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                    FilledButton.icon(
                          onPressed:
                              () => context.push(
                                '/competitions/${card.family.pathSegment}',
                              ),
                          icon: const Icon(Icons.open_in_new_rounded),
                          label: const Text('Open arena'),
                        ),
                      ],
                    ),
                  ],
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
    if (family == CompetitionFamilyRoute.streamer) {
      return const GteStatePanel(
        eyebrow: 'COMING SOON',
        title: 'Streamer competitions coming soon',
        message:
            'This competition surface is blocked for launch while GTEX focuses on the 2D football manager experience.',
        icon: Icons.lock_clock_outlined,
      );
    }
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
              tone: GtexSurfaceTone.live,
            ),
          )
          .toList(growable: false),
      CompetitionFamilyRoute.hosted => hub.userCompetitions
          .map(
            (CompetitionSummary item) => _competitionCard(
              context: context,
              title: item.name,
              subtitle:
                  '${item.creatorLabel} | ${item.status.name} | ${item.participantCount}/${item.capacity}',
              description: item.rulesSummary,
              path: '/competitions/${family.pathSegment}/${item.id}',
              tone: GtexSurfaceTone.info,
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
              tone: GtexSurfaceTone.warning,
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
    required GtexSurfaceTone tone,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: GtexSectionPanel(
        eyebrow: 'EVENT CARD',
        title: title,
        subtitle: subtitle,
        accentColor:
            tone == GtexSurfaceTone.warning
                ? Theme.of(context).colorScheme.tertiary
                : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(description),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => context.push(path),
              icon: const Icon(Icons.open_in_new_rounded),
              label: const Text('View detail'),
            ),
          ],
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
            item.isGtexHosted
                ? 'Entry Free'
                : 'Entry ${item.entryFee.toStringAsFixed(0)} Fan Coin',
            if (item.scheduledStartAt != null)
              'Starts ${item.scheduledStartAt!.toLocal().toString().substring(0, 16)}',
            'Prize ${value.financials.prizePool.toStringAsFixed(0)} ${value.financials.currency.toUpperCase()}',
            'Standings ${value.standings.length}',
            'Fixtures ${value.fixtures.length}',
            if (isAdmin && !canManageCompetitions)
              'Publish blocked: manage_competitions required',
          ],
          actions: <Widget>[
            FilledButton(
              onPressed:
                  userId == null ||
                          (!item.joinEligibility.eligible &&
                              !item.requiresPasscode)
                      ? null
                      : () async {
                        try {
                          final String? passcode =
                              item.requiresPasscode
                                  ? await _promptForCompetitionPasscode(
                                    context,
                                    item.name,
                                  )
                                  : null;
                          if (item.requiresPasscode && passcode == null) {
                            return;
                          }
                          await ref
                              .read(authedApiProvider)
                              .post(
                                '/api/competitions/${item.id}/join',
                                body: <String, Object?>{
                                  'user_id': userId,
                                  if (userName != null &&
                                      userName.trim().isNotEmpty)
                                    'user_name': userName.trim(),
                                  if (passcode != null) 'passcode': passcode,
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
          (Object error, StackTrace stackTrace) => GteStatePanel(
            title: 'GTEX competition detail is blocked',
            message: AppFeedback.messageFor(error),
            icon: Icons.error_outline_rounded,
            accentColor: Theme.of(context).colorScheme.error,
          ),
    );
  }
}

Future<String?> _promptForCompetitionPasscode(
  BuildContext context,
  String competitionName,
) async {
  final TextEditingController controller = TextEditingController();
  final bool? submitted = await showDialog<bool>(
    context: context,
    builder: (BuildContext context) {
      return AlertDialog(
        title: Text('Join $competitionName'),
        content: TextField(
          controller: controller,
          autofocus: true,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'Competition passcode'),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Join'),
          ),
        ],
      );
    },
  );
  if (submitted != true) {
    return null;
  }
  final String value = controller.text.trim();
  return value.isEmpty ? null : value;
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
        HostedCompetitionInvite? pendingInvite;
        for (final HostedCompetitionInvite invite in value.invites) {
          if (invite.isPending && invite.recipientUserId == userId) {
            pendingInvite = invite;
            break;
          }
        }
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
            if (value.invites.isNotEmpty) 'Invites ${value.invites.length}',
          ],
          actions: <Widget>[
            if (pendingInvite != null)
              FilledButton(
                onPressed: () async {
                  try {
                    await api.acceptInvite(
                      competitionId: item.id,
                      inviteId: pendingInvite!.inviteId,
                    );
                    ref.invalidate(competitionHubProvider);
                    ref.invalidate(hostedCompetitionDetailProvider(item.id));
                    if (context.mounted) {
                      AppFeedback.showSuccess(context, 'Invite accepted.');
                    }
                  } catch (error) {
                    if (context.mounted) {
                      AppFeedback.showError(context, error);
                    }
                  }
                },
                child: const Text('Accept invite'),
              ),
            FilledButton(
              onPressed:
                  userId == null || !value.detail.joinOpen
                      ? null
                      : () async {
                        try {
                          final String? passcode =
                              item.requiresPasscode
                                  ? await _promptForPasscode(context, item)
                                  : null;
                          if (item.requiresPasscode && passcode == null) {
                            return;
                          }
                          await api.joinCompetition(
                            item.id,
                            passcode: passcode,
                          );
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
                      ? () =>
                          _inviteToHostedCompetition(context, ref, api, item)
                      : null,
              child: const Text('Invite'),
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
          (Object error, StackTrace stackTrace) => GteStatePanel(
            title: 'Hosted competition detail is blocked',
            message: AppFeedback.messageFor(error),
            icon: Icons.error_outline_rounded,
            accentColor: Theme.of(context).colorScheme.error,
          ),
    );
  }

  Future<String?> _promptForPasscode(
    BuildContext context,
    HostedCompetition competition,
  ) async {
    final TextEditingController controller = TextEditingController();
    final bool? submitted = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Join ${competition.title}'),
          content: TextField(
            controller: controller,
            autofocus: true,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Competition passcode',
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Join'),
            ),
          ],
        );
      },
    );
    if (submitted != true) {
      return null;
    }
    return controller.text.trim();
  }

  Future<void> _inviteToHostedCompetition(
    BuildContext context,
    WidgetRef ref,
    HostedCompetitionApi api,
    HostedCompetition competition,
  ) async {
    final TextEditingController recipientsController = TextEditingController();
    final TextEditingController messageController = TextEditingController();
    final bool? submitted = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Invite to ${competition.title}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: recipientsController,
                decoration: const InputDecoration(
                  labelText: 'User IDs or emails',
                  helperText: 'Separate multiple recipients with commas.',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: messageController,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Message'),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Send invites'),
            ),
          ],
        );
      },
    );
    if (submitted != true) {
      return;
    }
    final List<String> tokens = recipientsController.text
        .split(',')
        .map((String value) => value.trim())
        .where((String value) => value.isNotEmpty)
        .toList(growable: false);
    final List<String> userIds = tokens
        .where((String value) => !value.contains('@'))
        .toList(growable: false);
    final List<String> emails = tokens
        .where((String value) => value.contains('@'))
        .toList(growable: false);
    if (tokens.isEmpty) {
      if (context.mounted) {
        AppFeedback.showError(context, 'Add at least one invite recipient.');
      }
      return;
    }
    try {
      await api.createInvites(
        competitionId: competition.id,
        recipientUserIds: userIds,
        recipientEmails: emails,
        message: messageController.text.trim(),
      );
      ref.invalidate(hostedCompetitionDetailProvider(competition.id));
      if (context.mounted) {
        AppFeedback.showSuccess(context, 'Hosted competition invite sent.');
      }
    } catch (error) {
      if (context.mounted) {
        AppFeedback.showError(context, error);
      }
    }
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
          (Object error, StackTrace stackTrace) => GteStatePanel(
            title: 'Streamer tournament detail is blocked',
            message: AppFeedback.messageFor(error),
            icon: Icons.error_outline_rounded,
            accentColor: Theme.of(context).colorScheme.error,
          ),
    );
  }
}

Widget _loading() {
  return const GteStatePanel(
    title: 'Loading competition detail',
    message: 'Live event detail is syncing.',
    isLoading: true,
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
    return GtexSectionPanel(
      eyebrow: 'EVENT DETAIL',
      title: title,
      subtitle: description,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: metrics
                .map(
                  (String metric) =>
                      GtexPill(label: metric, tone: GtexSurfaceTone.info),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 16),
          Wrap(spacing: 8, runSpacing: 8, children: actions),
        ],
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

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../core/widgets/task_reward_pop.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_tasks_provider.dart';

class TasksScreen extends ConsumerWidget {
  const TasksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<LiveTasksData> tasksValue = ref.watch(liveTasksProvider);
    final LiveTasksData? snapshot = tasksValue.asData?.value;
    return AppPageLayout(
      title: 'Tasks',
      subtitle:
          'Premium seasonal engagement system powered by live daily challenges and login streak state.',
      trailing: DataSourceBadge(
        status:
            tasksValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'SEASONAL ENGAGEMENT',
          title: 'Turn daily progress into a premium reward loop.',
          description:
              'The shipped path uses live daily challenges and streak tracking. The fake season-pass loop stays removed.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Feature',
              value:
                  snapshot == null
                      ? '...'
                      : snapshot.featureEnabled
                      ? 'Enabled'
                      : 'Blocked',
              support: 'Backend flag',
              tone:
                  snapshot?.featureEnabled == true
                      ? GtexSurfaceTone.live
                      : GtexSurfaceTone.warning,
            ),
            GtexStatTile(
              label: 'Current streak',
              value: snapshot == null ? '...' : '${snapshot.currentStreak}',
              support: 'Live streak momentum',
              tone: GtexSurfaceTone.warning,
            ),
            GtexStatTile(
              label: 'Challenges',
              value: snapshot == null ? '...' : '${snapshot.challenges.length}',
              support: 'Daily challenge pool',
              tone: GtexSurfaceTone.info,
            ),
          ],
        ),
        tasksValue.when(
          data: (LiveTasksData tasks) => _TasksBody(tasks: tasks),
          loading:
              () => const GteStatePanel(
                title: 'Loading tasks',
                message:
                    'The active shell is pulling daily challenges and streak state.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                title: 'Tasks are blocked',
                message: AppFeedback.messageFor(error),
                icon: Icons.error_outline_rounded,
                accentColor: Theme.of(context).colorScheme.error,
              ),
        ),
      ],
    );
  }
}

class _TasksBody extends ConsumerWidget {
  const _TasksBody({required this.tasks});

  final LiveTasksData tasks;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: <Widget>[
        GtexSectionPanel(
          eyebrow: 'STREAK',
          title: 'Season progress',
          subtitle:
              'Live daily streak state with no local reward fiction layered on top.',
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexStatTile(
                label:
                    'Feature ${tasks.featureEnabled ? 'enabled' : 'blocked'}',
                value: tasks.featureEnabled ? 'Live' : 'Blocked',
                tone:
                    tasks.featureEnabled
                        ? GtexSurfaceTone.live
                        : GtexSurfaceTone.warning,
              ),
              GtexStatTile(
                label: 'Current streak',
                value: '${tasks.currentStreak}',
                tone: GtexSurfaceTone.warning,
              ),
              GtexStatTile(
                label: 'Longest streak',
                value: '${tasks.longestStreak}',
                tone: GtexSurfaceTone.success,
              ),
              GtexStatTile(
                label: 'Next bonus',
                value: tasks.nextBonusAmount.toStringAsFixed(0),
                support: 'Claims today ${tasks.claimsToday.length}',
                tone: GtexSurfaceTone.info,
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        GtexSectionPanel(
          eyebrow: 'DAILY CHALLENGES',
          title: 'Daily challenges',
          subtitle:
              'Challenge availability is driven by live entitlement and claim windows.',
          child: Column(
            children: tasks.challenges
                .map(
                  (DailyChallengeSummary item) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GtexListTile(
                      title: item.title,
                      subtitle:
                          '${item.description}\nReward: ${item.rewardSummary}\n${_challengeStatusLabel(item)}',
                      leadingIcon: Icons.flag_rounded,
                      tone:
                          item.claimedToday
                              ? GtexSurfaceTone.success
                              : item.availableToday
                              ? GtexSurfaceTone.live
                              : GtexSurfaceTone.warning,
                      trailing: FilledButton(
                        onPressed:
                            !tasks.authenticated ||
                                    item.claimedToday ||
                                    !item.availableToday
                                ? null
                                : () => _claimChallenge(
                                  context,
                                  ref,
                                  item.challengeKey,
                                ),
                        child: Text(_claimActionLabel(tasks, item)),
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
        if (tasks.claimsToday.isNotEmpty) ...<Widget>[
          const SizedBox(height: 24),
          GtexSectionPanel(
            eyebrow: 'CLAIMS TODAY',
            title: 'Settled rewards',
            subtitle:
                'These entries are rendered from live daily-challenge claim payloads.',
            child: Column(
              children: tasks.claimsToday
                  .map(
                    (DailyChallengeClaimSummary claim) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: GtexListTile(
                        title: claim.challengeTitle,
                        subtitle: claim.rewardDetail,
                        leadingIcon: Icons.task_alt_rounded,
                        tone: GtexSurfaceTone.success,
                        trailing: const Icon(Icons.verified_rounded, size: 18),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      ],
    );
  }

  String _challengeStatusLabel(DailyChallengeSummary item) {
    if (!tasks.authenticated) {
      return 'Sign in to claim this live challenge.';
    }
    if (item.claimedToday) {
      return 'Claim already settled today.';
    }
    if (item.availableToday) {
      return 'Available to claim now.';
    }
    return 'Unavailable right now.';
  }

  String _claimActionLabel(LiveTasksData tasks, DailyChallengeSummary item) {
    if (!tasks.authenticated) {
      return 'Sign in';
    }
    if (item.claimedToday) {
      return 'Claimed';
    }
    if (item.availableToday) {
      return 'Claim';
    }
    return 'Unavailable';
  }

  Future<void> _claimChallenge(
    BuildContext context,
    WidgetRef ref,
    String challengeKey,
  ) async {
    try {
      final Object? claimResponse = await ref
          .read(authedApiProvider)
          .post('/daily-challenges/$challengeKey/claim');
      final LiveTasksData refreshedTasks = await ref.refresh(
        liveTasksProvider.future,
      );
      final DailyChallengeClaimFeedback feedback =
          DailyChallengeClaimFeedback.fromResponse(
            claimResponse,
            refreshedTasks: refreshedTasks,
          );
      if (context.mounted) {
        await showTaskRewardCelebration(context, feedback);
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
      }
    }
  }
}

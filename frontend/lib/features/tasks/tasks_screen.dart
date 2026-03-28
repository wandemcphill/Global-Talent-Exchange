import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_motion.dart';
import '../../core/utils/app_formatters.dart';
import '../../core/widgets/app_hover_lift.dart';
import '../../core/widgets/app_press_scale.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../core/widgets/task_reward_pop.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/club.dart';
import '../../shared/models/daily_task.dart';
import '../../shared/models/season_pass.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/club_provider.dart';
import '../../shared/providers/tasks_provider.dart';
import '../../shared/widgets/app_background.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/metric_pill.dart';
import '../../shared/widgets/section_heading.dart';

class TasksScreen extends ConsumerWidget {
  const TasksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final TasksState state = ref.watch(tasksProvider);
    final Club club = ref.watch(clubProvider);
    final AuthSession auth = ref.watch(authProvider);

    void claimTask(DailyTask task) {
      final TaskClaimResult? result = ref
          .read(tasksProvider.notifier)
          .claimTask(task.id);
      if (result == null) {
        return;
      }

      showTaskRewardCelebration(context, result);
    }

    void claimSeasonReward(SeasonPassReward reward) {
      final SeasonRewardClaimResult? result = ref
          .read(tasksProvider.notifier)
          .claimSeasonReward(reward.id);
      if (result == null) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Level ${result.level} reward claimed: ${result.rewardLabel}.',
          ),
        ),
      );
    }

    return AppBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          leading: AppPressScale(
            child: IconButton(
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.arrow_back_rounded),
            ),
          ),
          titleSpacing: spacingMD,
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Text(
                'Tasks & Season',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(letterSpacing: 0.4),
              ),
              const SizedBox(height: spacingXS),
              Text(
                'Season journey, daily missions, and streak rewards.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        body: SafeArea(
          top: false,
          child: AppPageLayout(
            title: 'Tasks, Season & Streak',
            subtitle:
                '${auth.userName} is driving the retention loop for ${club.name}. Push the season track, clear missions, and keep the streak alive.',
            trailing: MetricPill(
              label: 'Claimable',
              value: '${state.totalClaimableRewardsCount}',
              highlight: state.totalClaimableRewardsCount > 0,
            ),
            children: <Widget>[
              _TasksOverviewCard(state: state, club: club, auth: auth),
              _SeasonJourneyCard(
                state: state,
                onClaimReward: claimSeasonReward,
              ),
              _SeasonMissionSection(seasonPass: state.seasonPass),
              _TaskSection(
                title: 'Daily Tasks',
                subtitle:
                    'Reset every day. Keep this lane active to protect the streak and stack quick rewards.',
                cadence: _TaskCadence.daily,
                tasks: state.dailyTasks,
                claimedTaskIds: state.claimedTaskIds,
                onClaim: claimTask,
              ),
              _TaskSection(
                title: 'Weekly Tasks',
                subtitle:
                    'Longer objectives with heavier payouts for sustained club activity.',
                cadence: _TaskCadence.weekly,
                tasks: state.weeklyTasks,
                claimedTaskIds: state.claimedTaskIds,
                onClaim: claimTask,
              ),
              _StreakTrackerCard(state: state),
            ],
          ),
        ),
      ),
    );
  }
}

enum _TaskCadence { daily, weekly }

extension on _TaskCadence {
  Color get accent =>
      this == _TaskCadence.daily ? AppColors.primary : AppColors.gold;

  String get label => this == _TaskCadence.daily ? 'Daily Loop' : 'Weekly Push';
}

class _TasksOverviewCard extends StatelessWidget {
  const _TasksOverviewCard({
    required this.state,
    required this.club,
    required this.auth,
  });

  final TasksState state;
  final Club club;
  final AuthSession auth;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor:
          state.totalClaimableRewardsCount > 0
              ? AppColors.primary
              : AppColors.gold,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
          final Widget summary = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Keep the season loop hot',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: spacingSM),
              Text(
                '${auth.role} focus for ${club.league}: climb ${state.seasonPass.title}, clear the mission board, stay on the weekly push, and hold the ${state.streakMultiplierLabel} streak multiplier.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingMD),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: <Widget>[
                  MetricPill(
                    label: 'Daily',
                    value:
                        '${state.completedDailyCount}/${state.dailyTasks.length}',
                    highlight: state.dailyProgress == 1,
                  ),
                  MetricPill(
                    label: 'Weekly',
                    value:
                        '${state.completedWeeklyCount}/${state.weeklyTasks.length}',
                    highlight: state.weeklyProgress == 1,
                  ),
                  MetricPill(
                    label: 'Season',
                    value:
                        'Lv ${state.seasonPass.currentLevel}/${state.seasonPass.levels}',
                    highlight: state.seasonPass.claimableRewardCount > 0,
                  ),
                  MetricPill(
                    label: 'Fans',
                    value: AppFormatters.compact(club.fans),
                  ),
                ],
              ),
            ],
          );

          final Widget highlights = Container(
            width: wide ? 300 : double.infinity,
            padding: const EdgeInsets.all(spacingMD),
            decoration: BoxDecoration(
              color: AppColors.background.withValues(alpha: 0.58),
              borderRadius: BorderRadius.circular(cardRadius),
              border: Border.all(color: AppColors.divider),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Lv ${state.seasonPass.currentLevel}',
                  style: Theme.of(
                    context,
                  ).textTheme.headlineLarge?.copyWith(color: AppColors.primary),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  '${state.seasonPass.title} is active',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: spacingMD),
                _OverviewMetricRow(
                  icon: Icons.redeem_rounded,
                  label: 'Ready to claim',
                  value: '${state.totalClaimableRewardsCount} rewards',
                ),
                const SizedBox(height: spacingSM),
                _OverviewMetricRow(
                  icon: Icons.rocket_launch_rounded,
                  label: 'XP to next level',
                  value: '${state.seasonPass.xpForNextLevel} XP',
                ),
                const SizedBox(height: spacingSM),
                _OverviewMetricRow(
                  icon: Icons.local_fire_department_rounded,
                  label: 'Current streak',
                  value:
                      '${state.currentStreak} days at ${state.streakMultiplierLabel}',
                ),
              ],
            ),
          );

          if (!wide) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                summary,
                const SizedBox(height: spacingMD),
                highlights,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(flex: 7, child: summary),
              const SizedBox(width: spacingLG),
              Expanded(flex: 4, child: highlights),
            ],
          );
        },
      ),
    );
  }
}

class _OverviewMetricRow extends StatelessWidget {
  const _OverviewMetricRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(icon, size: 18, color: AppColors.gold),
        const SizedBox(width: spacingSM),
        Expanded(
          child: Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
        ),
        const SizedBox(width: spacingSM),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
      ],
    );
  }
}

class _SeasonJourneyCard extends StatelessWidget {
  const _SeasonJourneyCard({required this.state, required this.onClaimReward});

  final TasksState state;
  final ValueChanged<SeasonPassReward> onClaimReward;

  @override
  Widget build(BuildContext context) {
    final SeasonPassState seasonPass = state.seasonPass;
    final SeasonPassReward? nextReward = seasonPass.nextReward;

    return GtexSurfaceCard(
      glowColor: AppColors.primary,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
              final Widget summary = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Wrap(
                    spacing: spacingSM,
                    runSpacing: spacingSM,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: <Widget>[
                      MetricPill(
                        label: 'Season',
                        value: seasonPass.seasonId,
                        highlight: true,
                      ),
                      MetricPill(
                        label: 'Level',
                        value: '${seasonPass.currentLevel}',
                        highlight: seasonPass.claimableRewardCount > 0,
                      ),
                      MetricPill(
                        label: 'Missions',
                        value:
                            '${seasonPass.completedMissionCount}/${seasonPass.dailyMissions.length}',
                        highlight:
                            seasonPass.completedMissionCount ==
                            seasonPass.dailyMissions.length,
                      ),
                    ],
                  ),
                  const SizedBox(height: spacingMD),
                  Text(
                    'Season Journey',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: spacingXS),
                  Text(
                    'Matches, wins, trades, and watch sessions all feed the pass. This is the long loop holding the daily loop together.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                  Text(
                    'Level ${seasonPass.currentLevel}',
                    style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                      color: AppColors.primary,
                    ),
                  ),
                  const SizedBox(height: spacingXS),
                  Text(
                    '${seasonPass.xpIntoCurrentLevel}/${seasonPass.xpPerLevel} XP in the current tier. ${seasonPass.xpForNextLevel} XP to the next level.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: spacingMD),
                  _ProgressTrack(
                    value: seasonPass.xpProgress,
                    color: AppColors.primary,
                    height: 10,
                  ),
                ],
              );

              final Widget spotlight = Container(
                width: wide ? 320 : double.infinity,
                padding: const EdgeInsets.all(spacingMD),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      AppColors.primary.withValues(alpha: 0.16),
                      AppColors.gold.withValues(alpha: 0.12),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(cardRadius),
                  border: Border.all(color: AppColors.divider),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      nextReward == null ? 'Track Complete' : 'Next Reward',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: spacingXS),
                    Text(
                      nextReward?.title ?? 'All rewards claimed',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: spacingSM),
                    Text(
                      nextReward == null
                          ? 'The current season track is fully cleared.'
                          : 'Level ${nextReward.level} unlocks ${nextReward.rewardLabel}.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: spacingMD),
                    _OverviewMetricRow(
                      icon: Icons.redeem_rounded,
                      label: 'Season rewards ready',
                      value: '${seasonPass.claimableRewardCount}',
                    ),
                    const SizedBox(height: spacingSM),
                    _OverviewMetricRow(
                      icon: Icons.workspace_premium_rounded,
                      label: 'Premium track',
                      value:
                          seasonPass.premiumEnabled
                              ? seasonPass.hasPremium
                                  ? 'Active'
                                  : 'Locked'
                              : 'Future',
                    ),
                  ],
                ),
              );

              if (!wide) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    summary,
                    const SizedBox(height: spacingMD),
                    spotlight,
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(flex: 7, child: summary),
                  const SizedBox(width: spacingLG),
                  Expanded(flex: 4, child: spotlight),
                ],
              );
            },
          ),
          const SizedBox(height: spacingLG),
          Text('Reward Track', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: spacingXS),
          Text(
            'Free-track milestones stay visible even before they unlock, so the chase feels tangible.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingMD),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final double width =
                  constraints.maxWidth >= AppBreakpoints.expanded
                      ? (constraints.maxWidth - (spacingMD * 3)) / 4
                      : constraints.maxWidth >= AppBreakpoints.compact
                      ? (constraints.maxWidth - spacingMD) / 2
                      : constraints.maxWidth;

              return Wrap(
                spacing: spacingMD,
                runSpacing: spacingMD,
                children: seasonPass.rewards
                    .map(
                      (SeasonPassReward reward) => SizedBox(
                        width: width,
                        child: _SeasonRewardCard(
                          reward: reward,
                          seasonPass: seasonPass,
                          onClaim: () => onClaimReward(reward),
                        ),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _SeasonMissionSection extends StatelessWidget {
  const _SeasonMissionSection({required this.seasonPass});

  final SeasonPassState seasonPass;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SectionHeading(
          title: 'Daily Missions',
          subtitle:
              'These feed the season track directly. Hit them every day to keep the pass moving.',
          trailing: MetricPill(
            label: 'Complete',
            value:
                '${seasonPass.completedMissionCount}/${seasonPass.dailyMissions.length}',
            highlight:
                seasonPass.completedMissionCount ==
                seasonPass.dailyMissions.length,
          ),
        ),
        const SizedBox(height: spacingMD),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double width =
                constraints.maxWidth >= AppBreakpoints.expanded
                    ? (constraints.maxWidth - (spacingMD * 2)) / 3
                    : constraints.maxWidth >= AppBreakpoints.compact
                    ? (constraints.maxWidth - spacingMD) / 2
                    : constraints.maxWidth;

            return Wrap(
              spacing: spacingMD,
              runSpacing: spacingMD,
              children: seasonPass.dailyMissions
                  .map(
                    (SeasonMission mission) => SizedBox(
                      width: width,
                      child: _SeasonMissionCard(mission: mission),
                    ),
                  )
                  .toList(growable: false),
            );
          },
        ),
      ],
    );
  }
}

class _TaskSection extends StatelessWidget {
  const _TaskSection({
    required this.title,
    required this.subtitle,
    required this.cadence,
    required this.tasks,
    required this.claimedTaskIds,
    required this.onClaim,
  });

  final String title;
  final String subtitle;
  final _TaskCadence cadence;
  final List<DailyTask> tasks;
  final Set<String> claimedTaskIds;
  final ValueChanged<DailyTask> onClaim;

  @override
  Widget build(BuildContext context) {
    final int claimableCount =
        tasks
            .where(
              (DailyTask task) =>
                  task.isComplete && !claimedTaskIds.contains(task.id),
            )
            .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SectionHeading(
          title: title,
          subtitle: subtitle,
          trailing: MetricPill(
            label: 'Ready',
            value: '$claimableCount',
            highlight: claimableCount > 0,
          ),
        ),
        const SizedBox(height: spacingMD),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double width =
                constraints.maxWidth >= AppBreakpoints.expanded
                    ? (constraints.maxWidth - (spacingMD * 2)) / 3
                    : constraints.maxWidth >= AppBreakpoints.compact
                    ? (constraints.maxWidth - spacingMD) / 2
                    : constraints.maxWidth;

            return Wrap(
              spacing: spacingMD,
              runSpacing: spacingMD,
              children: tasks
                  .map(
                    (DailyTask task) => SizedBox(
                      width: width,
                      child: _TaskCard(
                        task: task,
                        cadence: cadence,
                        claimed: claimedTaskIds.contains(task.id),
                        onClaim: () => onClaim(task),
                      ),
                    ),
                  )
                  .toList(growable: false),
            );
          },
        ),
      ],
    );
  }
}

class _TaskCard extends StatelessWidget {
  const _TaskCard({
    required this.task,
    required this.cadence,
    required this.claimed,
    required this.onClaim,
  });

  final DailyTask task;
  final _TaskCadence cadence;
  final bool claimed;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    final _TaskVisuals visuals = _visualsForTask(task, cadence);
    final bool canClaim = task.isComplete && !claimed;
    final Color accent = claimed ? AppColors.success : visuals.accent;

    return AppHoverLift(
      child: GtexSurfaceCard(
        glowColor: canClaim || claimed ? accent : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(visuals.icon, color: accent),
                ),
                const SizedBox(width: spacingMD),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        cadence.label,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: accent,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: spacingXS),
                      Text(
                        task.title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: spacingSM),
                MetricPill(
                  label: 'Progress',
                  value: '${task.current}/${task.target}',
                  highlight: task.isComplete,
                ),
              ],
            ),
            const SizedBox(height: spacingMD),
            Text(
              visuals.description,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: spacingMD),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: spacingSM,
                vertical: spacingSM,
              ),
              decoration: BoxDecoration(
                color: AppColors.background.withValues(alpha: 0.45),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppColors.gold.withValues(alpha: 0.28),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  const Icon(
                    Icons.workspace_premium_rounded,
                    size: 16,
                    color: AppColors.gold,
                  ),
                  const SizedBox(width: spacingXS),
                  Flexible(
                    child: Text(
                      claimed ? '${task.reward} banked' : task.reward,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.gold,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: spacingMD),
            _ProgressTrack(value: task.progress, color: accent),
            const SizedBox(height: spacingSM),
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    claimed
                        ? 'Reward claimed'
                        : task.isComplete
                        ? 'Ready for payout'
                        : '${task.target - task.current} steps left',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
                Text(
                  '${(task.progress * 100).round()}%',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: accent,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: spacingMD),
            SizedBox(
              width: double.infinity,
              child: _TaskActionButton(
                canClaim: canClaim,
                claimed: claimed,
                onClaim: onClaim,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TaskActionButton extends StatelessWidget {
  const _TaskActionButton({
    required this.canClaim,
    required this.claimed,
    required this.onClaim,
  });

  final bool canClaim;
  final bool claimed;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    if (claimed) {
      return AppPressScale(
        enabled: false,
        child: FilledButton.icon(
          onPressed: null,
          icon: const Icon(Icons.check_circle_rounded),
          label: const Text('Claimed'),
        ),
      );
    }

    if (canClaim) {
      return AppPressScale(
        child: FilledButton.icon(
          onPressed: onClaim,
          icon: const Icon(Icons.redeem_rounded),
          label: const Text('Claim Reward'),
        ),
      );
    }

    return AppPressScale(
      enabled: false,
      child: OutlinedButton.icon(
        onPressed: null,
        icon: const Icon(Icons.schedule_rounded),
        label: const Text('In Progress'),
      ),
    );
  }
}

class _SeasonRewardCard extends StatelessWidget {
  const _SeasonRewardCard({
    required this.reward,
    required this.seasonPass,
    required this.onClaim,
  });

  final SeasonPassReward reward;
  final SeasonPassState seasonPass;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    final bool unlocked = reward.isUnlocked(seasonPass.currentLevel);
    final bool claimable = reward.isClaimable(
      seasonPass.currentLevel,
      seasonPass.hasPremium,
    );
    final Color accent =
        reward.claimed
            ? AppColors.success
            : claimable
            ? AppColors.gold
            : unlocked
            ? AppColors.primary
            : AppColors.divider;

    return AppHoverLift(
      child: GtexSurfaceCard(
        glowColor: reward.claimed || claimable ? accent : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: accent.withValues(alpha: 0.32)),
                  ),
                  child: Icon(
                    reward.claimed
                        ? Icons.check_circle_rounded
                        : unlocked
                        ? Icons.workspace_premium_rounded
                        : Icons.lock_clock_rounded,
                    color: accent,
                  ),
                ),
                const SizedBox(width: spacingMD),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Level ${reward.level}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: accent,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: spacingXS),
                      Text(
                        reward.title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: spacingMD),
            Text(
              reward.description,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: spacingMD),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: spacingSM,
                vertical: spacingSM,
              ),
              decoration: BoxDecoration(
                color: AppColors.background.withValues(alpha: 0.42),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: accent.withValues(alpha: 0.28)),
              ),
              child: Text(
                reward.rewardLabel,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(height: spacingMD),
            Text(
              reward.claimed
                  ? 'Reward banked'
                  : claimable
                  ? 'Ready to claim'
                  : unlocked
                  ? 'Unlocked'
                  : '${reward.level - seasonPass.currentLevel} levels left',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: spacingMD),
            SizedBox(
              width: double.infinity,
              child:
                  reward.claimed
                      ? AppPressScale(
                        enabled: false,
                        child: FilledButton.icon(
                          onPressed: null,
                          icon: const Icon(Icons.check_circle_rounded),
                          label: const Text('Claimed'),
                        ),
                      )
                      : claimable
                      ? AppPressScale(
                        child: FilledButton.icon(
                          onPressed: onClaim,
                          icon: const Icon(Icons.redeem_rounded),
                          label: const Text('Claim Reward'),
                        ),
                      )
                      : AppPressScale(
                        enabled: false,
                        child: OutlinedButton.icon(
                          onPressed: null,
                          icon: const Icon(Icons.lock_outline_rounded),
                          label: const Text('Locked'),
                        ),
                      ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SeasonMissionCard extends StatelessWidget {
  const _SeasonMissionCard({required this.mission});

  final SeasonMission mission;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        mission.isComplete ? AppColors.success : AppColors.primary;

    return AppHoverLift(
      child: GtexSurfaceCard(
        glowColor: mission.isComplete ? AppColors.success : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    mission.isComplete
                        ? Icons.bolt_rounded
                        : Icons.flag_circle_rounded,
                    color: accent,
                  ),
                ),
                const SizedBox(width: spacingMD),
                Expanded(
                  child: Text(
                    mission.title,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                const SizedBox(width: spacingSM),
                MetricPill(
                  label: 'Progress',
                  value: '${mission.current}/${mission.target}',
                  highlight: mission.isComplete,
                ),
              ],
            ),
            const SizedBox(height: spacingMD),
            Text(
              mission.rewardLabel,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: AppColors.gold,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: spacingSM),
            _ProgressTrack(value: mission.progress, color: accent),
            const SizedBox(height: spacingSM),
            Text(
              mission.isComplete
                  ? 'Mission complete. Season XP is already flowing.'
                  : '${mission.target - mission.current} steps left on this mission.',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}

class _StreakTrackerCard extends StatelessWidget {
  const _StreakTrackerCard({required this.state});

  final TasksState state;

  @override
  Widget build(BuildContext context) {
    return GtexSurfaceCard(
      glowColor: AppColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _StreakFlameBadge(currentStreak: state.currentStreak),
              const SizedBox(width: spacingMD),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Streak Tracker',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: spacingXS),
                    Text(
                      'Clear the daily loop consistently to scale the payout multiplier and keep the club momentum compounding.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: spacingMD),
              MetricPill(
                label: 'Multiplier',
                value: state.streakMultiplierLabel,
                highlight: true,
              ),
            ],
          ),
          const SizedBox(height: spacingLG),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
              final Widget summary = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '${state.currentStreak} days',
                    style: Theme.of(
                      context,
                    ).textTheme.headlineLarge?.copyWith(color: AppColors.gold),
                  ),
                  const SizedBox(height: spacingXS),
                  Text(
                    'Best run ${state.bestStreak} days',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                  _ProgressTrack(
                    value: state.streakTierProgress,
                    color: AppColors.gold,
                    height: 10,
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    'Next multiplier boost lands at ${state.nextStreakMilestone} days for ${state.nextMultiplierLabel}.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              );

              final Widget milestones = Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children: TasksState.streakMilestones
                    .map(
                      (int milestone) => _StreakMilestoneChip(
                        days: milestone,
                        multiplierLabel: _multiplierLabelForMilestone(
                          milestone,
                        ),
                        active: state.currentStreak >= milestone,
                        next:
                            state.currentStreak < milestone &&
                            milestone == state.nextStreakMilestone,
                      ),
                    )
                    .toList(growable: false),
              );

              if (!wide) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    summary,
                    const SizedBox(height: spacingLG),
                    milestones,
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(child: summary),
                  const SizedBox(width: spacingLG),
                  Expanded(child: milestones),
                ],
              );
            },
          ),
          const SizedBox(height: spacingLG),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final double width =
                  constraints.maxWidth >= AppBreakpoints.expanded
                      ? (constraints.maxWidth - (spacingMD * 2)) / 3
                      : constraints.maxWidth >= AppBreakpoints.compact
                      ? (constraints.maxWidth - spacingMD) / 2
                      : constraints.maxWidth;

              return Wrap(
                spacing: spacingMD,
                runSpacing: spacingMD,
                children: <Widget>[
                  SizedBox(
                    width: width,
                    child: _TrackerStatCard(
                      label: 'Daily Rewards Claimed',
                      value:
                          '${state.claimedDailyCount}/${state.dailyTasks.length}',
                      accent: AppColors.primary,
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: _TrackerStatCard(
                      label: 'Weekly Rewards Claimed',
                      value:
                          '${state.claimedWeeklyCount}/${state.weeklyTasks.length}',
                      accent: AppColors.gold,
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: _TrackerStatCard(
                      label: 'Best Streak',
                      value: '${state.bestStreak} days',
                      accent: AppColors.success,
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _StreakMilestoneChip extends StatelessWidget {
  const _StreakMilestoneChip({
    required this.days,
    required this.multiplierLabel,
    required this.active,
    required this.next,
  });

  final int days;
  final String multiplierLabel;
  final bool active;
  final bool next;

  @override
  Widget build(BuildContext context) {
    final Color borderColor =
        active
            ? AppColors.gold
            : next
            ? AppColors.primary
            : AppColors.divider;
    final Color background =
        active
            ? AppColors.gold.withValues(alpha: 0.14)
            : next
            ? AppColors.primary.withValues(alpha: 0.12)
            : AppColors.background.withValues(alpha: 0.38);

    return AnimatedContainer(
      duration: AppMotion.medium,
      curve: AppMotion.easeOut,
      padding: const EdgeInsets.symmetric(
        horizontal: spacingMD,
        vertical: spacingSM,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '$days days',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
              color: active ? AppColors.gold : AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: spacingXS),
          Text(
            multiplierLabel,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: next ? AppColors.primary : AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _StreakFlameBadge extends StatefulWidget {
  const _StreakFlameBadge({required this.currentStreak});

  final int currentStreak;

  @override
  State<_StreakFlameBadge> createState() => _StreakFlameBadgeState();
}

class _StreakFlameBadgeState extends State<_StreakFlameBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController = AnimationController(
    vsync: this,
    duration: AppMotion.slow,
  )..repeat(reverse: true);

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final double growth =
        (widget.currentStreak / TasksState.streakMilestones.last)
            .clamp(0, 1)
            .toDouble();
    final double size = 56 + (growth * 10);
    final double iconSize = 30 + (growth * 6);

    return AnimatedBuilder(
      animation: _pulseController,
      builder: (BuildContext context, Widget? child) {
        final double pulse =
            1 + ((0.04 + (growth * 0.05)) * _pulseController.value);

        return Transform.scale(
          scale: pulse,
          child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  AppColors.gold.withValues(alpha: 0.28),
                  AppColors.primary.withValues(alpha: 0.18),
                ],
              ),
              border: Border.all(color: AppColors.gold.withValues(alpha: 0.44)),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: AppColors.gold.withValues(
                    alpha: 0.14 + (_pulseController.value * 0.18),
                  ),
                  blurRadius: 18 + (_pulseController.value * 10),
                  spreadRadius: growth * 2,
                ),
              ],
            ),
            child: Icon(
              Icons.local_fire_department_rounded,
              color: AppColors.gold,
              size: iconSize,
            ),
          ),
        );
      },
    );
  }
}

class _TrackerStatCard extends StatelessWidget {
  const _TrackerStatCard({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(cardRadius),
        border: Border.all(color: accent.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingSM),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(color: accent),
          ),
        ],
      ),
    );
  }
}

class _ProgressTrack extends StatelessWidget {
  const _ProgressTrack({
    required this.value,
    required this.color,
    this.height = 8,
  });

  final double value;
  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: LinearProgressIndicator(
        value: value.clamp(0, 1).toDouble(),
        minHeight: height,
        backgroundColor: AppColors.surfaceMuted,
        valueColor: AlwaysStoppedAnimation<Color>(color),
      ),
    );
  }
}

class _TaskVisuals {
  const _TaskVisuals({
    required this.icon,
    required this.description,
    required this.accent,
  });

  final IconData icon;
  final String description;
  final Color accent;
}

_TaskVisuals _visualsForTask(DailyTask task, _TaskCadence cadence) {
  switch (task.id) {
    case 'task-scout':
      return const _TaskVisuals(
        icon: Icons.radar_rounded,
        description:
            'Keep academy discovery flowing and surface the next high-upside talent before rivals move first.',
        accent: AppColors.primary,
      );
    case 'task-fans':
      return const _TaskVisuals(
        icon: Icons.campaign_rounded,
        description:
            'Drive fan momentum between fixtures and keep the badge visible across the GTEX social loop.',
        accent: AppColors.primary,
      );
    case 'task-revenue':
      return const _TaskVisuals(
        icon: Icons.currency_exchange_rounded,
        description:
            'Trim squad drag and open new budget room by moving one outgoing loan cleanly.',
        accent: AppColors.primary,
      );
    case 'weekly-predictions':
      return const _TaskVisuals(
        icon: Icons.insights_rounded,
        description:
            'Stay sharp on match narratives and convert club knowledge into prediction wins.',
        accent: AppColors.gold,
      );
    case 'weekly-commerce':
      return const _TaskVisuals(
        icon: Icons.payments_rounded,
        description:
            'Push sponsor and matchday revenue hard enough to lift the weekly commercial floor.',
        accent: AppColors.gold,
      );
    case 'weekly-training':
      return const _TaskVisuals(
        icon: Icons.fitness_center_rounded,
        description:
            'Finish the full training rhythm so development gains carry through the next fixture block.',
        accent: AppColors.gold,
      );
    default:
      return _TaskVisuals(
        icon:
            cadence == _TaskCadence.daily
                ? Icons.task_alt_rounded
                : Icons.assignment_turned_in_rounded,
        description:
            'Keep this objective moving to stay inside the active reward loop.',
        accent: cadence.accent,
      );
  }
}

String _multiplierLabelForMilestone(int streak) {
  if (streak >= 30) {
    return '3x';
  }
  if (streak >= 21) {
    return '2.5x';
  }
  if (streak >= 14) {
    return '2x';
  }
  if (streak >= 7) {
    return '1.6x';
  }
  if (streak >= 3) {
    return '1.3x';
  }
  return '1x';
}

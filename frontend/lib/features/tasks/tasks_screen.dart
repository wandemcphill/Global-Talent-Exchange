import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_shell_theme.dart';
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
                          '${item.description}\nReward: ${item.rewardSummary}',
                      leadingIcon: Icons.flag_rounded,
                      tone:
                          item.availableToday
                              ? GtexSurfaceTone.live
                              : GtexSurfaceTone.warning,
                      trailing: FilledButton(
                        onPressed:
                            !tasks.authenticated || !item.availableToday
                                ? null
                                : () => _claimChallenge(
                                  context,
                                  ref,
                                  item.challengeKey,
                                  item.rewardSummary,
                                ),
                        child: Text(item.availableToday ? 'Claim' : 'Blocked'),
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
      ],
    );
  }

  Future<void> _claimChallenge(
    BuildContext context,
    WidgetRef ref,
    String challengeKey,
    String rewardSummary,
  ) async {
    try {
      await ref
          .read(authedApiProvider)
          .post('/daily-challenges/$challengeKey/claim');
      ref.invalidate(liveTasksProvider);
      if (context.mounted) {
        await _showClaimCelebration(context, rewardSummary);
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
      }
    }
  }

  Future<void> _showClaimCelebration(
    BuildContext context,
    String rewardSummary,
  ) {
    final tokens = GteShellTheme.tokensOf(context);
    final theme = GteShellTheme.definitionOf(context);
    return showGeneralDialog<void>(
      context: context,
      barrierLabel: 'Dismiss reward',
      barrierDismissible: true,
      barrierColor: Colors.black.withValues(alpha: 0.56),
      transitionDuration: const Duration(milliseconds: 240),
      pageBuilder: (
        BuildContext context,
        Animation<double> animation,
        Animation<double> secondaryAnimation,
      ) {
        return Center(
          child: Material(
            color: Colors.transparent,
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0.92, end: 1),
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOutCubic,
              builder:
                  (BuildContext context, double value, Widget? child) =>
                      Transform.scale(scale: value, child: child),
              child: Container(
                constraints: const BoxConstraints(maxWidth: 360),
                padding: EdgeInsets.all(tokens.spaceLg),
                decoration: BoxDecoration(
                  color: theme.tokens.panel,
                  borderRadius: BorderRadius.circular(tokens.radiusLarge),
                  border: Border.all(
                    color: theme.primaryColor.withValues(alpha: 0.38),
                  ),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: theme.primaryColor.withValues(alpha: 0.24),
                      blurRadius: 30,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Icon(
                      Icons.emoji_events_rounded,
                      color: theme.primaryColor,
                      size: 40,
                    ),
                    SizedBox(height: tokens.spaceMd),
                    Text(
                      'Challenge claimed.',
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: tokens.spaceXs),
                    Text(
                      rewardSummary,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: theme.secondaryColor,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
      transitionBuilder: (
        BuildContext context,
        Animation<double> animation,
        Animation<double> secondaryAnimation,
        Widget child,
      ) {
        return FadeTransition(opacity: animation, child: child);
      },
    ).then((_) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Challenge claimed.')));
      }
    });
  }
}

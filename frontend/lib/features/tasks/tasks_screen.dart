import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import 'live_tasks_provider.dart';

class TasksScreen extends ConsumerWidget {
  const TasksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<LiveTasksData> tasksValue = ref.watch(liveTasksProvider);
    return AppPageLayout(
      title: 'Tasks',
      subtitle:
          'The shipped path now uses daily challenges and login streaks from the backend. The fake season-pass loop has been removed from this screen.',
      trailing: DataSourceBadge(
        status:
            tasksValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        tasksValue.when(
          data: (LiveTasksData tasks) => _TasksBody(tasks: tasks),
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Tasks are blocked',
                message: AppFeedback.messageFor(error),
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
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Wrap(
              spacing: spacingSM,
              runSpacing: spacingSM,
              children: <Widget>[
                Chip(
                  label: Text(
                    'Feature ${tasks.featureEnabled ? 'enabled' : 'blocked'}',
                  ),
                ),
                Chip(label: Text('Current streak ${tasks.currentStreak}')),
                Chip(label: Text('Longest streak ${tasks.longestStreak}')),
                Chip(
                  label: Text(
                    'Next bonus ${tasks.nextBonusAmount.toStringAsFixed(0)}',
                  ),
                ),
                Chip(label: Text('Claims today ${tasks.claimsToday.length}')),
              ],
            ),
          ),
        ),
        const SizedBox(height: spacingMD),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Daily challenges',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingSM),
                ...tasks.challenges.map(
                  (DailyChallengeSummary item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(item.title),
                    subtitle: Text(
                      '${item.description}\nReward: ${item.rewardSummary}',
                    ),
                    trailing: FilledButton(
                      onPressed:
                          !tasks.authenticated || !item.availableToday
                              ? null
                              : () => _claimChallenge(
                                context,
                                ref,
                                item.challengeKey,
                              ),
                      child: Text(item.availableToday ? 'Claim' : 'Blocked'),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _claimChallenge(
    BuildContext context,
    WidgetRef ref,
    String challengeKey,
  ) async {
    try {
      await ref
          .read(authedApiProvider)
          .post('/daily-challenges/$challengeKey/claim');
      ref.invalidate(liveTasksProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Challenge claimed.')));
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

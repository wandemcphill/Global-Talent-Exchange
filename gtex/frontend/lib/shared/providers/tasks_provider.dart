import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/daily_task.dart';
import '../models/season_pass.dart';

final NotifierProvider<TasksNotifier, TasksState> tasksProvider =
    NotifierProvider<TasksNotifier, TasksState>(TasksNotifier.new);

class TasksState {
  const TasksState({
    required this.dailyTasks,
    required this.weeklyTasks,
    required this.claimedTaskIds,
    required this.currentStreak,
    required this.bestStreak,
    required this.seasonPass,
  });

  static const List<int> streakMilestones = <int>[3, 7, 14, 21, 30];

  final List<DailyTask> dailyTasks;
  final List<DailyTask> weeklyTasks;
  final Set<String> claimedTaskIds;
  final int currentStreak;
  final int bestStreak;
  final SeasonPassState seasonPass;

  List<DailyTask> get allTasks => <DailyTask>[...dailyTasks, ...weeklyTasks];

  int get claimableRewardsCount {
    return allTasks
        .where((DailyTask task) => task.isComplete && !isClaimed(task.id))
        .length;
  }

  int get totalClaimableRewardsCount {
    return claimableRewardsCount + seasonPass.claimableRewardCount;
  }

  int get completedDailyCount {
    return dailyTasks.where((DailyTask task) => task.isComplete).length;
  }

  int get completedWeeklyCount {
    return weeklyTasks.where((DailyTask task) => task.isComplete).length;
  }

  int get claimedDailyCount {
    return dailyTasks.where((DailyTask task) => isClaimed(task.id)).length;
  }

  int get claimedWeeklyCount {
    return weeklyTasks.where((DailyTask task) => isClaimed(task.id)).length;
  }

  double get dailyProgress {
    if (dailyTasks.isEmpty) {
      return 0;
    }
    return completedDailyCount / dailyTasks.length;
  }

  double get weeklyProgress {
    if (weeklyTasks.isEmpty) {
      return 0;
    }
    return completedWeeklyCount / weeklyTasks.length;
  }

  double get streakMultiplier => _streakMultiplierFor(currentStreak);

  String get streakMultiplierLabel => _formatMultiplier(streakMultiplier);

  int get previousStreakMilestone {
    int previous = 0;
    for (final int milestone in streakMilestones) {
      if (currentStreak < milestone) {
        break;
      }
      previous = milestone;
    }
    return previous;
  }

  int get nextStreakMilestone {
    for (final int milestone in streakMilestones) {
      if (currentStreak < milestone) {
        return milestone;
      }
    }
    return streakMilestones.last;
  }

  double get streakTierProgress {
    final int previous = previousStreakMilestone;
    final int next = nextStreakMilestone;
    if (next == previous) {
      return 1;
    }
    return ((currentStreak - previous) / (next - previous))
        .clamp(0, 1)
        .toDouble();
  }

  String get nextMultiplierLabel {
    return _formatMultiplier(_streakMultiplierFor(nextStreakMilestone));
  }

  bool isClaimed(String taskId) => claimedTaskIds.contains(taskId);

  bool isDailyTask(String taskId) {
    return dailyTasks.any((DailyTask task) => task.id == taskId);
  }

  DailyTask? taskById(String taskId) {
    for (final DailyTask task in allTasks) {
      if (task.id == taskId) {
        return task;
      }
    }
    return null;
  }

  TasksState copyWith({
    List<DailyTask>? dailyTasks,
    List<DailyTask>? weeklyTasks,
    Set<String>? claimedTaskIds,
    int? currentStreak,
    int? bestStreak,
    SeasonPassState? seasonPass,
  }) {
    return TasksState(
      dailyTasks: dailyTasks ?? this.dailyTasks,
      weeklyTasks: weeklyTasks ?? this.weeklyTasks,
      claimedTaskIds: claimedTaskIds ?? this.claimedTaskIds,
      currentStreak: currentStreak ?? this.currentStreak,
      bestStreak: bestStreak ?? this.bestStreak,
      seasonPass: seasonPass ?? this.seasonPass,
    );
  }
}

class TaskClaimResult {
  const TaskClaimResult({
    required this.title,
    required this.reward,
    required this.currentStreak,
    required this.multiplierLabel,
    required this.streakAdvanced,
    required this.multiplierIncreased,
  });

  final String title;
  final String reward;
  final int currentStreak;
  final String multiplierLabel;
  final bool streakAdvanced;
  final bool multiplierIncreased;

  String get message {
    final StringBuffer buffer = StringBuffer('Claimed $reward from "$title".');
    if (!streakAdvanced) {
      return buffer.toString();
    }

    buffer.write(' Streak moved to $currentStreak days');
    if (multiplierIncreased) {
      buffer.write(' and the multiplier is now $multiplierLabel');
    }
    buffer.write('.');
    return buffer.toString();
  }
}

class TasksNotifier extends Notifier<TasksState> {
  @override
  TasksState build() {
    return const TasksState(
      dailyTasks: <DailyTask>[
        DailyTask(
          id: 'task-scout',
          title: 'Scout two U-18 prospects',
          reward: '+120 XP',
          current: 1,
          target: 2,
        ),
        DailyTask(
          id: 'task-fans',
          title: 'Post a social teaser',
          reward: '+8K fans',
          current: 1,
          target: 1,
        ),
        DailyTask(
          id: 'task-revenue',
          title: 'Close one outgoing loan',
          reward: '+\$1.5M',
          current: 0,
          target: 1,
        ),
      ],
      weeklyTasks: <DailyTask>[
        DailyTask(
          id: 'weekly-predictions',
          title: 'Win three fan prediction battles',
          reward: '+450 XP',
          current: 2,
          target: 3,
        ),
        DailyTask(
          id: 'weekly-commerce',
          title: 'Generate \$8M in commercial income',
          reward: '+\$3.2M',
          current: 6,
          target: 8,
        ),
        DailyTask(
          id: 'weekly-training',
          title: 'Finish five training cycles',
          reward: '+1 academy wildcard',
          current: 5,
          target: 5,
        ),
      ],
      claimedTaskIds: <String>{},
      currentStreak: 9,
      bestStreak: 17,
      seasonPass: SeasonPassState(
        seasonId: 'S1',
        title: 'Opening Exchange',
        currentLevel: 12,
        currentXp: 1145,
        levels: 50,
        xpPerLevel: 100,
        hasPremium: false,
        premiumEnabled: false,
        rewards: <SeasonPassReward>[
          SeasonPassReward(
            id: 'season-reward-5',
            level: 5,
            title: '5 GTex',
            description: 'A quick GTex drop for staying active.',
            rewardLabel: '5 GTex',
            claimed: true,
          ),
          SeasonPassReward(
            id: 'season-reward-10',
            level: 10,
            title: 'Player Pack',
            description: 'Open a new player pack for the market push.',
            rewardLabel: 'Player Pack',
          ),
          SeasonPassReward(
            id: 'season-reward-20',
            level: 20,
            title: '20 GTex',
            description: 'A bigger GTex release for the mid-season climb.',
            rewardLabel: '20 GTex',
          ),
          SeasonPassReward(
            id: 'season-reward-50',
            level: 50,
            title: 'Rare Player',
            description: 'A rare player unlock at the end of the pass.',
            rewardLabel: 'Rare Player',
          ),
        ],
        dailyMissions: <SeasonMission>[
          SeasonMission(
            id: 'season-mission-play',
            title: 'Play 2 matches',
            rewardLabel: '+20 XP',
            current: 2,
            target: 2,
          ),
          SeasonMission(
            id: 'season-mission-win',
            title: 'Win 1 match',
            rewardLabel: '+25 XP',
            current: 1,
            target: 1,
          ),
          SeasonMission(
            id: 'season-mission-buy',
            title: 'Buy 1 player',
            rewardLabel: '+15 XP',
            current: 0,
            target: 1,
          ),
        ],
      ),
    );
  }

  TaskClaimResult? claimTask(String taskId) {
    final DailyTask? task = state.taskById(taskId);
    if (task == null || !task.isComplete || state.isClaimed(taskId)) {
      return null;
    }

    final Set<String> claimedTaskIds = <String>{
      ...state.claimedTaskIds,
      taskId,
    };
    final double previousMultiplier = state.streakMultiplier;
    int currentStreak = state.currentStreak;
    int bestStreak = state.bestStreak;
    bool streakAdvanced = false;

    if (state.isDailyTask(taskId)) {
      final bool allDailyClaimedBefore = state.dailyTasks.every(
        (DailyTask dailyTask) => state.claimedTaskIds.contains(dailyTask.id),
      );
      final bool allDailyClaimedNow = state.dailyTasks.every(
        (DailyTask dailyTask) => claimedTaskIds.contains(dailyTask.id),
      );

      if (!allDailyClaimedBefore && allDailyClaimedNow) {
        currentStreak += 1;
        bestStreak = math.max(bestStreak, currentStreak);
        streakAdvanced = true;
      }
    }

    final double nextMultiplier = _streakMultiplierFor(currentStreak);
    final TasksState nextState = state.copyWith(
      claimedTaskIds: claimedTaskIds,
      currentStreak: currentStreak,
      bestStreak: bestStreak,
    );
    state = nextState;

    return TaskClaimResult(
      title: task.title,
      reward: task.reward,
      currentStreak: nextState.currentStreak,
      multiplierLabel: nextState.streakMultiplierLabel,
      streakAdvanced: streakAdvanced,
      multiplierIncreased: nextMultiplier > previousMultiplier,
    );
  }

  SeasonRewardClaimResult? claimSeasonReward(String rewardId) {
    SeasonPassReward? reward;
    for (final SeasonPassReward candidate in state.seasonPass.rewards) {
      if (candidate.id == rewardId) {
        reward = candidate;
        break;
      }
    }
    if (reward == null ||
        !reward.isClaimable(
          state.seasonPass.currentLevel,
          state.seasonPass.hasPremium,
        )) {
      return null;
    }

    final List<SeasonPassReward> updatedRewards = state.seasonPass.rewards
        .map(
          (SeasonPassReward item) =>
              item.id == rewardId ? item.copyWith(claimed: true) : item,
        )
        .toList(growable: false);
    state = state.copyWith(
      seasonPass: state.seasonPass.copyWith(rewards: updatedRewards),
    );
    return SeasonRewardClaimResult(
      level: reward.level,
      title: reward.title,
      rewardLabel: reward.rewardLabel,
    );
  }
}

double _streakMultiplierFor(int streak) {
  if (streak >= 30) {
    return 3;
  }
  if (streak >= 21) {
    return 2.5;
  }
  if (streak >= 14) {
    return 2;
  }
  if (streak >= 7) {
    return 1.6;
  }
  if (streak >= 3) {
    return 1.3;
  }
  return 1;
}

String _formatMultiplier(double value) {
  final bool wholeNumber = value == value.roundToDouble();
  return '${value.toStringAsFixed(wholeNumber ? 0 : 1)}x';
}

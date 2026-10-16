class SeasonPassReward {
  const SeasonPassReward({
    required this.id,
    required this.level,
    required this.title,
    required this.description,
    required this.rewardLabel,
    this.premiumOnly = false,
    this.claimed = false,
  });

  final String id;
  final int level;
  final String title;
  final String description;
  final String rewardLabel;
  final bool premiumOnly;
  final bool claimed;

  bool isUnlocked(int currentLevel) => currentLevel >= level;

  bool isClaimable(int currentLevel, bool hasPremium) {
    if (claimed || !isUnlocked(currentLevel)) {
      return false;
    }
    return !premiumOnly || hasPremium;
  }

  SeasonPassReward copyWith({
    String? id,
    int? level,
    String? title,
    String? description,
    String? rewardLabel,
    bool? premiumOnly,
    bool? claimed,
  }) {
    return SeasonPassReward(
      id: id ?? this.id,
      level: level ?? this.level,
      title: title ?? this.title,
      description: description ?? this.description,
      rewardLabel: rewardLabel ?? this.rewardLabel,
      premiumOnly: premiumOnly ?? this.premiumOnly,
      claimed: claimed ?? this.claimed,
    );
  }
}

class SeasonMission {
  const SeasonMission({
    required this.id,
    required this.title,
    required this.rewardLabel,
    required this.current,
    required this.target,
  });

  final String id;
  final String title;
  final String rewardLabel;
  final int current;
  final int target;

  bool get isComplete => current >= target;

  double get progress => target == 0 ? 0 : current / target;
}

class SeasonPassState {
  const SeasonPassState({
    required this.seasonId,
    required this.title,
    required this.currentLevel,
    required this.currentXp,
    required this.levels,
    required this.xpPerLevel,
    required this.hasPremium,
    required this.premiumEnabled,
    required this.rewards,
    required this.dailyMissions,
  });

  final String seasonId;
  final String title;
  final int currentLevel;
  final int currentXp;
  final int levels;
  final int xpPerLevel;
  final bool hasPremium;
  final bool premiumEnabled;
  final List<SeasonPassReward> rewards;
  final List<SeasonMission> dailyMissions;

  int get xpIntoCurrentLevel {
    if (currentLevel >= levels) {
      return xpPerLevel;
    }
    return currentXp - ((currentLevel - 1) * xpPerLevel);
  }

  int get xpForNextLevel {
    if (currentLevel >= levels) {
      return 0;
    }
    return xpPerLevel - xpIntoCurrentLevel;
  }

  double get xpProgress {
    if (currentLevel >= levels) {
      return 1;
    }
    return (xpIntoCurrentLevel / xpPerLevel).clamp(0, 1).toDouble();
  }

  int get claimableRewardCount {
    return rewards
        .where(
          (SeasonPassReward reward) =>
              reward.isClaimable(currentLevel, hasPremium),
        )
        .length;
  }

  int get completedMissionCount {
    return dailyMissions
        .where((SeasonMission mission) => mission.isComplete)
        .length;
  }

  SeasonPassReward? get nextReward {
    for (final SeasonPassReward reward in rewards) {
      if (!reward.isUnlocked(currentLevel) || !reward.claimed) {
        return reward;
      }
    }
    return rewards.isEmpty ? null : rewards.last;
  }

  SeasonPassState copyWith({
    String? seasonId,
    String? title,
    int? currentLevel,
    int? currentXp,
    int? levels,
    int? xpPerLevel,
    bool? hasPremium,
    bool? premiumEnabled,
    List<SeasonPassReward>? rewards,
    List<SeasonMission>? dailyMissions,
  }) {
    return SeasonPassState(
      seasonId: seasonId ?? this.seasonId,
      title: title ?? this.title,
      currentLevel: currentLevel ?? this.currentLevel,
      currentXp: currentXp ?? this.currentXp,
      levels: levels ?? this.levels,
      xpPerLevel: xpPerLevel ?? this.xpPerLevel,
      hasPremium: hasPremium ?? this.hasPremium,
      premiumEnabled: premiumEnabled ?? this.premiumEnabled,
      rewards: rewards ?? this.rewards,
      dailyMissions: dailyMissions ?? this.dailyMissions,
    );
  }
}

class SeasonRewardClaimResult {
  const SeasonRewardClaimResult({
    required this.level,
    required this.title,
    required this.rewardLabel,
  });

  final int level;
  final String title;
  final String rewardLabel;
}

class CreatorProfile {
  const CreatorProfile({
    required this.creatorId,
    required this.userId,
    required this.displayName,
    required this.handle,
    required this.shareCode,
    required this.tier,
    required this.status,
    required this.revenueSharePercent,
    required this.headline,
    required this.bio,
    required this.communityTag,
    required this.profileLink,
    required this.stats,
    required this.growthSummary,
    required this.rewardSummary,
    required this.financeSummary,
    required this.competitions,
  });

  final String creatorId;
  final String userId;
  final String displayName;
  final String handle;
  final String shareCode;
  final String tier;
  final String status;
  final double? revenueSharePercent;
  final String headline;
  final String bio;
  final String communityTag;
  final String profileLink;
  final CreatorStats stats;
  final CreatorGrowthSummary growthSummary;
  final CreatorRewardSummary rewardSummary;
  final CreatorFinanceSummary financeSummary;
  final List<CreatorCompetition> competitions;

  String get handleLabel => '@$handle';
}

class CreatorStats {
  const CreatorStats({
    required this.communityInvites,
    required this.qualifiedReferrals,
    required this.creatorCompetitions,
    required this.contestParticipants,
  });

  final int communityInvites;
  final int qualifiedReferrals;
  final int creatorCompetitions;
  final int contestParticipants;
}

class CreatorGrowthSummary {
  const CreatorGrowthSummary({
    required this.growthHeadline,
    required this.growthDetail,
    required this.weeklyInviteLift,
    required this.topChannel,
    required this.inviteAttributionRate,
  });

  final String growthHeadline;
  final String growthDetail;
  final String weeklyInviteLift;
  final String topChannel;
  final String inviteAttributionRate;
}

class CreatorRewardSummary {
  const CreatorRewardSummary({
    required this.pendingCommunityRewards,
    required this.lifetimeMilestoneRewards,
    required this.competitionEntryCredits,
    required this.ledgerStatus,
  });

  final String pendingCommunityRewards;
  final String lifetimeMilestoneRewards;
  final String competitionEntryCredits;
  final String ledgerStatus;
}

class CreatorFinanceSummary {
  const CreatorFinanceSummary({
    required this.currency,
    required this.totalGiftIncome,
    required this.totalRewardIncome,
    required this.totalClipIncome,
    required this.totalClipViews,
    required this.monetizedClips,
    required this.viralClipCount,
    required this.totalViralBonus,
    required this.totalReferralBonus,
    required this.totalWeeklyTopCreatorBonus,
    required this.totalWithdrawnGross,
    required this.totalWithdrawalFees,
    required this.totalWithdrawnNet,
    required this.pendingWithdrawals,
    required this.walletBalance,
    required this.walletAvailableBalance,
    required this.walletCurrency,
    required this.activeCompetitions,
    required this.attributedSignups,
    required this.qualifiedJoins,
    required this.insights,
  });

  final String currency;
  final double totalGiftIncome;
  final double totalRewardIncome;
  final double totalClipIncome;
  final int totalClipViews;
  final int monetizedClips;
  final int viralClipCount;
  final double totalViralBonus;
  final double totalReferralBonus;
  final double totalWeeklyTopCreatorBonus;
  final double totalWithdrawnGross;
  final double totalWithdrawalFees;
  final double totalWithdrawnNet;
  final double pendingWithdrawals;
  final double walletBalance;
  final double walletAvailableBalance;
  final String walletCurrency;
  final int activeCompetitions;
  final int attributedSignups;
  final int qualifiedJoins;
  final List<String> insights;
}

class CreatorCompetition {
  const CreatorCompetition({
    required this.competitionId,
    required this.title,
    required this.seasonLabel,
    required this.inviteWindow,
    required this.inviteAttributionLabel,
    required this.participationLabel,
    required this.rewardLabel,
    required this.isLive,
  });

  final String competitionId;
  final String title;
  final String seasonLabel;
  final String inviteWindow;
  final String inviteAttributionLabel;
  final String participationLabel;
  final String rewardLabel;
  final bool isLive;
}

class CreatorCompetitionShareData {
  const CreatorCompetitionShareData({
    required this.competition,
    required this.shareCode,
    required this.shareUrl,
    required this.headline,
    required this.supportingText,
    required this.attributionNote,
  });

  final CreatorCompetition competition;
  final String shareCode;
  final String shareUrl;
  final String headline;
  final String supportingText;
  final String attributionNote;
}

class CreatorLeaderboardSnapshot {
  const CreatorLeaderboardSnapshot({
    required this.growthHeadline,
    required this.growthDetail,
    required this.topCreatorLabel,
    required this.strongestCompetitionLabel,
    required this.highestQualifiedParticipationLabel,
    required this.entries,
  });

  final String growthHeadline;
  final String growthDetail;
  final String topCreatorLabel;
  final String strongestCompetitionLabel;
  final String highestQualifiedParticipationLabel;
  final List<CreatorLeaderboardEntry> entries;
}

class CreatorLeaderboardEntry {
  const CreatorLeaderboardEntry({
    required this.rank,
    required this.creatorId,
    required this.displayName,
    required this.handle,
    required this.shareCode,
    required this.communityInvites,
    required this.qualifiedParticipation,
    required this.creatorCompetitions,
    required this.communityRewardLabel,
    required this.highlightLabel,
    required this.flaggedForReview,
  });

  final int rank;
  final String creatorId;
  final String displayName;
  final String handle;
  final String shareCode;
  final int communityInvites;
  final int qualifiedParticipation;
  final int creatorCompetitions;
  final String communityRewardLabel;
  final String highlightLabel;
  final bool flaggedForReview;
}

class CreatorCopilotDraft {
  const CreatorCopilotDraft({
    required this.title,
    required this.durationSeconds,
    required this.eventType,
    required this.tags,
    required this.preferredFormat,
    required this.introSeconds,
    required this.visualIntensity,
    required this.eventDensity,
    required this.audienceCluster,
    required this.hasReactionOverlay,
  });

  final String title;
  final double durationSeconds;
  final String eventType;
  final List<String> tags;
  final String preferredFormat;
  final double introSeconds;
  final double visualIntensity;
  final double eventDensity;
  final String audienceCluster;
  final bool hasReactionOverlay;

  CreatorCopilotDraft copyWith({
    String? title,
    double? durationSeconds,
    String? eventType,
    List<String>? tags,
    String? preferredFormat,
    double? introSeconds,
    double? visualIntensity,
    double? eventDensity,
    String? audienceCluster,
    bool? hasReactionOverlay,
  }) {
    return CreatorCopilotDraft(
      title: title ?? this.title,
      durationSeconds: durationSeconds ?? this.durationSeconds,
      eventType: eventType ?? this.eventType,
      tags: tags ?? this.tags,
      preferredFormat: preferredFormat ?? this.preferredFormat,
      introSeconds: introSeconds ?? this.introSeconds,
      visualIntensity: visualIntensity ?? this.visualIntensity,
      eventDensity: eventDensity ?? this.eventDensity,
      audienceCluster: audienceCluster ?? this.audienceCluster,
      hasReactionOverlay: hasReactionOverlay ?? this.hasReactionOverlay,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'title': title,
      'duration_seconds': durationSeconds,
      'event_type': eventType,
      'tags': tags,
      'preferred_format': preferredFormat,
      'intro_seconds': introSeconds,
      'visual_intensity': visualIntensity,
      'event_density': eventDensity,
      'audience_cluster': audienceCluster,
      'has_reaction_overlay': hasReactionOverlay,
    };
  }
}

class CreatorCopilotPrediction {
  const CreatorCopilotPrediction({
    required this.viralProbability,
    required this.expectedViews,
    required this.bestFormat,
    required this.riskFlags,
  });

  final double viralProbability;
  final int expectedViews;
  final String bestFormat;
  final List<String> riskFlags;

  int get viralScorePercent => (viralProbability * 100).round();
}

class CreatorCopilotVariantRecommendation {
  const CreatorCopilotVariantRecommendation({
    required this.type,
    required this.confidence,
    required this.reason,
    required this.exploratory,
  });

  final String type;
  final double confidence;
  final String reason;
  final bool exploratory;
}

class CreatorCopilotVariantStrategy {
  const CreatorCopilotVariantStrategy({
    required this.recommendedVariants,
    required this.explorationFactor,
    required this.rationale,
  });

  final List<CreatorCopilotVariantRecommendation> recommendedVariants;
  final double explorationFactor;
  final List<String> rationale;
}

class CreatorCopilotTiming {
  const CreatorCopilotTiming({
    required this.postNow,
    required this.bestTimeInMinutes,
    required this.reason,
    required this.competitionDensity,
    required this.audienceActivity,
  });

  final bool postNow;
  final int bestTimeInMinutes;
  final String reason;
  final double competitionDensity;
  final double audienceActivity;
}

class CreatorCopilotHookAnalysis {
  const CreatorCopilotHookAnalysis({
    required this.hookScore,
    required this.suggestion,
    required this.introStrength,
    required this.eventDensity,
    required this.visualIntensity,
  });

  final double hookScore;
  final String suggestion;
  final String introStrength;
  final double eventDensity;
  final double visualIntensity;

  int get hookScorePercent => (hookScore * 100).round();
}

class CreatorCopilotStrategyProfile {
  const CreatorCopilotStrategyProfile({
    required this.profileKey,
    required this.archetype,
    required this.summary,
    required this.confidence,
    required this.winningFormats,
    required this.winningDuration,
    required this.audienceCluster,
  });

  final String profileKey;
  final String archetype;
  final String summary;
  final double confidence;
  final List<String> winningFormats;
  final String? winningDuration;
  final String? audienceCluster;
}

class CreatorCopilotLiveCoaching {
  const CreatorCopilotLiveCoaching({
    required this.eventName,
    required this.headline,
    required this.message,
    required this.recommendedAction,
  });

  final String eventName;
  final String headline;
  final String message;
  final String recommendedAction;
}

class CreatorCopilotAnalysis {
  const CreatorCopilotAnalysis({
    required this.creatorId,
    required this.draft,
    required this.prediction,
    required this.variantStrategy,
    required this.timing,
    required this.hookAnalysis,
    required this.strategyProfile,
    required this.liveCoaching,
    required this.actionPlan,
  });

  final String creatorId;
  final CreatorCopilotDraft draft;
  final CreatorCopilotPrediction prediction;
  final CreatorCopilotVariantStrategy variantStrategy;
  final CreatorCopilotTiming timing;
  final CreatorCopilotHookAnalysis hookAnalysis;
  final CreatorCopilotStrategyProfile strategyProfile;
  final CreatorCopilotLiveCoaching liveCoaching;
  final List<String> actionPlan;
}

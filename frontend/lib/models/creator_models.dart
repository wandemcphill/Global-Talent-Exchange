class CreatorProfile {
  const CreatorProfile({
    required this.creatorId,
    required this.displayName,
    required this.handle,
    required this.shareCode,
    required this.headline,
    required this.bio,
    required this.communityTag,
    required this.profileLink,
    required this.stats,
    required this.growthSummary,
    required this.rewardSummary,
    required this.competitions,
  });

  final String creatorId;
  final String displayName;
  final String handle;
  final String shareCode;
  final String headline;
  final String bio;
  final String communityTag;
  final String profileLink;
  final CreatorStats stats;
  final CreatorGrowthSummary growthSummary;
  final CreatorRewardSummary rewardSummary;
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

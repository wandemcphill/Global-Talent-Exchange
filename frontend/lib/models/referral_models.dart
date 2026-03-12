enum InviteChannel {
  copyCode,
  copyLink,
  whatsApp,
  telegram,
  systemShare,
}

extension InviteChannelCopy on InviteChannel {
  String get label {
    switch (this) {
      case InviteChannel.copyCode:
        return 'Copy code';
      case InviteChannel.copyLink:
        return 'Copy link';
      case InviteChannel.whatsApp:
        return 'WhatsApp';
      case InviteChannel.telegram:
        return 'Telegram';
      case InviteChannel.systemShare:
        return 'System share';
    }
  }

  String get helperText {
    switch (this) {
      case InviteChannel.copyCode:
        return 'Copies your personal share code.';
      case InviteChannel.copyLink:
        return 'Copies a creator competition invite link.';
      case InviteChannel.whatsApp:
        return 'Prepares a WhatsApp-ready invite.';
      case InviteChannel.telegram:
        return 'Prepares a Telegram-ready invite.';
      case InviteChannel.systemShare:
        return 'Uses the generic device share flow when connected.';
    }
  }
}

enum ReferralRewardCategory {
  welcomeBonus,
  participationCredit,
  milestoneReward,
  badgeUnlock,
  creatorCommunityReward,
}

extension ReferralRewardCategoryCopy on ReferralRewardCategory {
  String get label {
    switch (this) {
      case ReferralRewardCategory.welcomeBonus:
        return 'Welcome bonus';
      case ReferralRewardCategory.participationCredit:
        return 'Participation credit';
      case ReferralRewardCategory.milestoneReward:
        return 'Milestone reward';
      case ReferralRewardCategory.badgeUnlock:
        return 'Badge unlock';
      case ReferralRewardCategory.creatorCommunityReward:
        return 'Creator community reward';
    }
  }
}

class ReferralSummary {
  const ReferralSummary({
    required this.invitesSent,
    required this.qualifiedReferrals,
    required this.inviteAttributions,
    required this.rewardBalanceLabel,
    required this.rewardDetail,
  });

  final int invitesSent;
  final int qualifiedReferrals;
  final int inviteAttributions;
  final String rewardBalanceLabel;
  final String rewardDetail;
}

class MilestoneProgress {
  const MilestoneProgress({
    required this.title,
    required this.detail,
    required this.currentValue,
    required this.targetValue,
    required this.rewardLabel,
    required this.unlocked,
  });

  final String title;
  final String detail;
  final int currentValue;
  final int targetValue;
  final String rewardLabel;
  final bool unlocked;

  double get progress {
    if (targetValue <= 0) {
      return 0;
    }
    return (currentValue / targetValue).clamp(0, 1);
  }
}

class RewardHistoryEntry {
  const RewardHistoryEntry({
    required this.rewardId,
    required this.title,
    required this.detail,
    required this.category,
    required this.rewardLabel,
    required this.issuedAt,
    required this.ledgerNote,
  });

  final String rewardId;
  final String title;
  final String detail;
  final ReferralRewardCategory category;
  final String rewardLabel;
  final DateTime issuedAt;
  final String ledgerNote;
}

class ReferralInviteEntry {
  const ReferralInviteEntry({
    required this.inviteeLabel,
    required this.competitionLabel,
    required this.channel,
    required this.sentAt,
    required this.statusLabel,
    required this.inviteAttributionLabel,
    required this.isQualified,
  });

  final String inviteeLabel;
  final String competitionLabel;
  final InviteChannel channel;
  final DateTime sentAt;
  final String statusLabel;
  final String inviteAttributionLabel;
  final bool isQualified;
}

class ReferralHubData {
  const ReferralHubData({
    required this.shareCode,
    required this.shareUrl,
    required this.creatorHandle,
    required this.welcomeTitle,
    required this.welcomeDetail,
    required this.summary,
    required this.milestones,
    required this.rewardHistory,
    required this.invites,
  });

  final String shareCode;
  final String shareUrl;
  final String creatorHandle;
  final String welcomeTitle;
  final String welcomeDetail;
  final ReferralSummary summary;
  final List<MilestoneProgress> milestones;
  final List<RewardHistoryEntry> rewardHistory;
  final List<ReferralInviteEntry> invites;
}

enum ReferralRiskSeverity {
  low,
  medium,
  high,
}

extension ReferralRiskSeverityCopy on ReferralRiskSeverity {
  String get label {
    switch (this) {
      case ReferralRiskSeverity.low:
        return 'Low review signal';
      case ReferralRiskSeverity.medium:
        return 'Moderate review signal';
      case ReferralRiskSeverity.high:
        return 'High review signal';
    }
  }
}

class ReferralAnalyticsSnapshot {
  const ReferralAnalyticsSnapshot({
    required this.growthHeadline,
    required this.growthDetail,
    required this.activeShareCodes,
    required this.qualifiedParticipationLabel,
    required this.communityRewardReviewLabel,
    required this.topChannelLabel,
    required this.flags,
  });

  final String growthHeadline;
  final String growthDetail;
  final String activeShareCodes;
  final String qualifiedParticipationLabel;
  final String communityRewardReviewLabel;
  final String topChannelLabel;
  final List<ReferralFlagEntry> flags;
}

class ReferralFlagEntry {
  const ReferralFlagEntry({
    required this.flagId,
    required this.creatorHandle,
    required this.shareCode,
    required this.issueLabel,
    required this.riskSignal,
    required this.reviewStatus,
    required this.recommendedAction,
    required this.qualifiedParticipationLabel,
    required this.severity,
  });

  final String flagId;
  final String creatorHandle;
  final String shareCode;
  final String issueLabel;
  final String riskSignal;
  final String reviewStatus;
  final String recommendedAction;
  final String qualifiedParticipationLabel;
  final ReferralRiskSeverity severity;
}

import '../data/gte_api_repository.dart';
import '../models/referral_models.dart';

class ReferralApi {
  ReferralApi._({
    required this.baseUrl,
    required this.mode,
    required this.latency,
  });

  final String baseUrl;
  final GteBackendMode mode;
  final Duration latency;

  factory ReferralApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return ReferralApi._(
      baseUrl: baseUrl,
      mode: mode,
      latency: const Duration(milliseconds: 180),
    );
  }

  factory ReferralApi.fixture({
    String baseUrl = 'https://community.gte.local',
    Duration latency = Duration.zero,
  }) {
    return ReferralApi._(
      baseUrl: baseUrl,
      mode: GteBackendMode.fixture,
      latency: latency,
    );
  }

  Future<ReferralHubData> fetchReferralHub() async {
    await Future<void>.delayed(latency);
    return ReferralHubData(
      shareCode: 'MAYA-GROWTH',
      shareUrl: '${_normalizedBase(baseUrl)}/community/invite/MAYA-GROWTH',
      creatorHandle: '@maya_scout',
      welcomeTitle: 'Invite friends into creator competitions',
      welcomeDetail:
          'Share your code, grow your circle, and unlock milestone rewards when invited managers join community contests and complete qualified participation.',
      summary: const ReferralSummary(
        invitesSent: 184,
        qualifiedReferrals: 72,
        inviteAttributions: 54,
        rewardBalanceLabel: '420 competition credits',
        rewardDetail: 'Reviewable community rewards and participation credits',
      ),
      milestones: const <MilestoneProgress>[
        MilestoneProgress(
          title: 'Welcome milestone',
          detail: 'First 10 qualified joins',
          currentValue: 10,
          targetValue: 10,
          rewardLabel: 'Unlocked welcome bonus',
          unlocked: true,
        ),
        MilestoneProgress(
          title: 'Contest participation milestone',
          detail: '50 invited managers enter a creator competition',
          currentValue: 41,
          targetValue: 50,
          rewardLabel: '120 competition entry credits',
          unlocked: false,
        ),
        MilestoneProgress(
          title: 'Community growth milestone',
          detail: '75 qualified referrals complete invite attribution',
          currentValue: 72,
          targetValue: 75,
          rewardLabel: 'Creator community reward badge',
          unlocked: false,
        ),
      ],
      rewardHistory: <RewardHistoryEntry>[
        RewardHistoryEntry(
          rewardId: 'reward-1',
          title: 'Welcome bonus confirmed',
          detail:
              'First 10 invited managers completed qualified joining steps.',
          category: ReferralRewardCategory.welcomeBonus,
          rewardLabel: '80 competition credits',
          issuedAt: DateTime.utc(2026, 3, 8, 11, 0),
          ledgerNote: 'Ledger reviewed',
        ),
        RewardHistoryEntry(
          rewardId: 'reward-2',
          title: 'Participation credit batch',
          detail:
              'Spring Scout Sprint entrants completed their opening contest.',
          category: ReferralRewardCategory.participationCredit,
          rewardLabel: '120 competition credits',
          issuedAt: DateTime.utc(2026, 3, 6, 15, 30),
          ledgerNote: 'Fraud-aware review passed',
        ),
        RewardHistoryEntry(
          rewardId: 'reward-3',
          title: 'Creator community reward',
          detail:
              'Invite attribution stayed above the community growth threshold.',
          category: ReferralRewardCategory.creatorCommunityReward,
          rewardLabel: '220 competition credits',
          issuedAt: DateTime.utc(2026, 3, 4, 9, 45),
          ledgerNote: 'Community milestone approved',
        ),
        RewardHistoryEntry(
          rewardId: 'reward-4',
          title: 'Badge unlock',
          detail: 'Reached 25 qualified referrals in creator competitions.',
          category: ReferralRewardCategory.badgeUnlock,
          rewardLabel: 'Community badge unlocked',
          issuedAt: DateTime.utc(2026, 3, 1, 8, 0),
          ledgerNote: 'Profile badge synced',
        ),
      ],
      invites: <ReferralInviteEntry>[
        ReferralInviteEntry(
          inviteeLabel: 'Coach Ada',
          competitionLabel: 'Spring Scout Sprint',
          channel: InviteChannel.whatsApp,
          sentAt: DateTime.utc(2026, 3, 10, 16, 0),
          statusLabel: 'Qualified join complete',
          inviteAttributionLabel: 'Invite attribution locked',
          isQualified: true,
        ),
        ReferralInviteEntry(
          inviteeLabel: 'Tobi Drafts',
          competitionLabel: 'Spring Scout Sprint',
          channel: InviteChannel.telegram,
          sentAt: DateTime.utc(2026, 3, 10, 12, 30),
          statusLabel: 'Contest entry pending',
          inviteAttributionLabel: 'Waiting for qualified participation',
          isQualified: false,
        ),
        ReferralInviteEntry(
          inviteeLabel: 'Rina XI',
          competitionLabel: 'Creator Captains Cup',
          channel: InviteChannel.copyLink,
          sentAt: DateTime.utc(2026, 3, 9, 18, 10),
          statusLabel: 'Qualified join complete',
          inviteAttributionLabel: 'Milestone reward counted',
          isQualified: true,
        ),
      ],
    );
  }

  Future<ReferralAnalyticsSnapshot> fetchReferralAnalytics() async {
    await Future<void>.delayed(latency);
    return const ReferralAnalyticsSnapshot(
      growthHeadline: 'Community growth analytics',
      growthDetail:
          'Reviewable invite attribution, qualified participation, and milestone rewards are summarized here for creator program operations.',
      activeShareCodes: '148 active share codes',
      qualifiedParticipationLabel:
          '612 qualified participation events this week',
      communityRewardReviewLabel: '34 community reward reviews in progress',
      topChannelLabel:
          'WhatsApp is driving the strongest invite-to-entry conversion',
      flags: <ReferralFlagEntry>[
        ReferralFlagEntry(
          flagId: 'flag-1',
          creatorHandle: '@rina_xi',
          shareCode: 'RINA-XI',
          issueLabel: 'Invite attribution spike',
          riskSignal: 'Rapid code reuse across low-quality device clusters',
          reviewStatus: 'Queued for fraud-aware review',
          recommendedAction:
              'Hold new milestone rewards until participation quality clears review',
          qualifiedParticipationLabel:
              '18 qualified joins still pending review',
          severity: ReferralRiskSeverity.high,
        ),
        ReferralFlagEntry(
          flagId: 'flag-2',
          creatorHandle: '@coach_ada',
          shareCode: 'ADA-BUILD',
          issueLabel: 'Milestone review mismatch',
          riskSignal:
              'Manual correction needed for two duplicate invite attributions',
          reviewStatus: 'Analyst review in progress',
          recommendedAction:
              'Confirm ledger entries before community rewards are released',
          qualifiedParticipationLabel: '9 qualified joins unaffected',
          severity: ReferralRiskSeverity.medium,
        ),
        ReferralFlagEntry(
          flagId: 'flag-3',
          creatorHandle: '@maya_scout',
          shareCode: 'MAYA-GROWTH',
          issueLabel: 'Healthy growth watch',
          riskSignal:
              'Strong performance with normal invite channel distribution',
          reviewStatus: 'Routine monitoring only',
          recommendedAction: 'No action required',
          qualifiedParticipationLabel: '72 qualified joins verified',
          severity: ReferralRiskSeverity.low,
        ),
      ],
    );
  }
}

String _normalizedBase(String baseUrl) {
  return baseUrl.endsWith('/')
      ? baseUrl.substring(0, baseUrl.length - 1)
      : baseUrl;
}

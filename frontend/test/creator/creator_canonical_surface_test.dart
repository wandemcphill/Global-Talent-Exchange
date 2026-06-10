import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/creator/creator.dart';
import 'package:gte_frontend/models/creator_models.dart';

void main() {
  testWidgets('creator surface blocks unauthenticated studio access', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CreatorCanonicalSurface(
            profile: _profile(),
            finance: null,
            isAuthenticated: false,
            hasApprovedCreatorAccess: false,
          ),
        ),
      ),
    );

    expect(find.text('Sign in to open creator studio'), findsOneWidget);
    expect(
      find.textContaining('authenticated creator session'),
      findsOneWidget,
    );
  });

  testWidgets('creator surface renders backend finance and audience readiness', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CreatorCanonicalSurface(
            profile: _profile(),
            finance: _finance(),
            isAuthenticated: true,
            hasApprovedCreatorAccess: true,
            syncedAt: DateTime.utc(2026, 6),
          ),
        ),
      ),
    );

    expect(find.text('Creator canonical surface'), findsOneWidget);
    expect(find.text('Wallet'), findsOneWidget);
    expect(find.textContaining('Wallet balances are sourced'), findsOneWidget);
    expect(find.textContaining('250 GTC'), findsOneWidget);
    expect(find.text('Sponsored clips'), findsOneWidget);
    expect(
      find.textContaining('3 monetized clips, 1200 views'),
      findsOneWidget,
    );
    expect(find.text('Settlements'), findsOneWidget);
    expect(find.textContaining('Net withdrawn 195 GTC'), findsOneWidget);
    expect(find.text('Audience'), findsOneWidget);
    expect(
      find.textContaining(
        'Audience stats are backed by creator summary fields: 12 community invites, 5 qualified referrals, 44 contest participants.',
      ),
      findsOneWidget,
    );
    expect(find.text('Referrals'), findsOneWidget);
    expect(find.textContaining('5 qualified referrals'), findsOneWidget);
    expect(find.text('Moderation'), findsOneWidget);
    expect(find.textContaining('Pending withdrawals 40 GTC'), findsOneWidget);
  });

  testWidgets(
    'creator surface marks missing finance payload without local values',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CreatorCanonicalSurface(
              profile: _profile(shareCode: ''),
              finance: const CreatorFinanceSummary(
                currency: 'GTC',
                totalGiftIncome: 0,
                totalRewardIncome: 0,
                totalClipIncome: 0,
                totalClipViews: 0,
                monetizedClips: 0,
                viralClipCount: 0,
                totalViralBonus: 0,
                totalReferralBonus: 0,
                totalWeeklyTopCreatorBonus: 0,
                totalWithdrawnGross: 0,
                totalWithdrawalFees: 0,
                totalWithdrawnNet: 0,
                pendingWithdrawals: 0,
                walletBalance: 0,
                walletAvailableBalance: 0,
                walletCurrency: '',
                activeCompetitions: 0,
                attributedSignups: 0,
                qualifiedJoins: 0,
                insights: <String>[],
                hasCompleteBackendPayload: false,
                hasWalletPayload: false,
                hasClipEarningsPayload: false,
              ),
              isAuthenticated: true,
              hasApprovedCreatorAccess: true,
            ),
          ),
        ),
      );

      expect(
        find.textContaining(
          'Profile payload is present, but the backend share code field is empty.',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('Finance payload is partial'), findsOneWidget);
      expect(find.text('Wallet payload missing'), findsOneWidget);
      expect(find.text('Clip metrics missing'), findsOneWidget);
      expect(
        find.textContaining('Settlement totals stay degraded'),
        findsOneWidget,
      );
    },
  );

  testWidgets('creator surface keeps zero audience counts as backend truth', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CreatorCanonicalSurface(
            profile: _profile(
              shareCode: '',
              stats: const CreatorStats(
                communityInvites: 0,
                qualifiedReferrals: 0,
                creatorCompetitions: 0,
                contestParticipants: 0,
              ),
            ),
            finance: null,
            isAuthenticated: true,
            hasApprovedCreatorAccess: true,
          ),
        ),
      ),
    );

    expect(
      find.textContaining(
        '0 community invites, 0 qualified referrals, 0 contest participants.',
      ),
      findsOneWidget,
    );
    expect(
      find.textContaining(
        'Referral attribution is visible from creator stats, but finance attribution payload is still missing.',
      ),
      findsOneWidget,
    );
    expect(
      find.text('qualifiedReferrals=0; finance payload missing'),
      findsOneWidget,
    );
  });
}

CreatorProfile _profile({
  String shareCode = 'LAGOS',
  CreatorStats stats = const CreatorStats(
    communityInvites: 12,
    qualifiedReferrals: 5,
    creatorCompetitions: 2,
    contestParticipants: 44,
  ),
}) {
  return CreatorProfile(
    creatorId: 'creator-1',
    userId: 'user-1',
    displayName: 'Lagos Creator',
    handle: 'lagoscreator',
    shareCode: shareCode,
    tier: 'gold',
    status: 'approved',
    revenueSharePercent: 12,
    headline: 'Matchday stories',
    bio: 'Creator studio profile',
    communityTag: 'lagos',
    profileLink: 'https://gtex.test/creator/lagos',
    stats: stats,
    growthSummary: const CreatorGrowthSummary(
      growthHeadline: 'Growing',
      growthDetail: 'Backend growth payload',
      weeklyInviteLift: '+4',
      topChannel: 'community',
      inviteAttributionRate: '42%',
    ),
    rewardSummary: const CreatorRewardSummary(
      pendingCommunityRewards: 'GTC 20',
      lifetimeMilestoneRewards: 'GTC 400',
      competitionEntryCredits: '3',
      ledgerStatus: 'synced',
    ),
    financeSummary: _finance(),
    competitions: const <CreatorCompetition>[
      CreatorCompetition(
        competitionId: 'comp-1',
        title: 'Sunday Cup',
        seasonLabel: 'Season 1',
        inviteWindow: 'Open',
        inviteAttributionLabel: 'Backend attributed',
        participationLabel: '44 players',
        rewardLabel: 'GTC rewards',
        isLive: true,
      ),
    ],
  );
}

CreatorFinanceSummary _finance() {
  return const CreatorFinanceSummary(
    currency: 'GTC',
    totalGiftIncome: 80,
    totalRewardIncome: 100,
    totalClipIncome: 60,
    totalClipViews: 1200,
    monetizedClips: 3,
    viralClipCount: 2,
    totalViralBonus: 15,
    totalReferralBonus: 25,
    totalWeeklyTopCreatorBonus: 10,
    totalWithdrawnGross: 200,
    totalWithdrawalFees: 5,
    totalWithdrawnNet: 195,
    pendingWithdrawals: 40,
    walletBalance: 300,
    walletAvailableBalance: 250,
    walletCurrency: 'GTC',
    activeCompetitions: 2,
    attributedSignups: 16,
    qualifiedJoins: 5,
    insights: <String>['Backend insight'],
  );
}

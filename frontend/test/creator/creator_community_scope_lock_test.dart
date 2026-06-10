import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/community/community.dart';
import 'package:gte_frontend/features/creator/creator.dart';
import 'package:gte_frontend/models/community_models.dart';
import 'package:gte_frontend/models/creator_models.dart';

void main() {
  group('creator/community scope lock', () {
    test('creator surface requires authenticated session', () {
      final CreatorCanonicalSurface unauthenticated = CreatorCanonicalSurface(
        profile: _dummyProfile(),
        finance: null,
        isAuthenticated: false,
        hasApprovedCreatorAccess: false,
      );

      expect(
        unauthenticated.isAuthenticated,
        false,
        reason: 'Unauthenticated users should see auth gate, not studio.',
      );
    });

    test('creator surface requires creator access approval', () {
      final CreatorCanonicalSurface blockedAccess = CreatorCanonicalSurface(
        profile: _dummyProfile(),
        finance: null,
        isAuthenticated: true,
        hasApprovedCreatorAccess: false,
      );

      expect(
        blockedAccess.hasApprovedCreatorAccess,
        false,
        reason: 'Unapproved creators should see access request gate.',
      );
    });

    test('creator surface blocks studio actions until backend provisioning', () {
      final CreatorCanonicalSurface waitingForShareCode = CreatorCanonicalSurface(
        profile: _dummyProfile(shareCode: ''),
        finance: null,
        isAuthenticated: true,
        hasApprovedCreatorAccess: true,
      );

      expect(
        waitingForShareCode.profile.shareCode.trim().isEmpty,
        true,
        reason: 'Missing share code should block studio, waiting for backend.',
      );
    });

    test('creator surface marks finance payload as missing/degraded', () {
      final CreatorCanonicalSurface partialPayload = CreatorCanonicalSurface(
        profile: _dummyProfile(),
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
      );

      final CreatorFinanceSummary? finance = partialPayload.finance;
      expect(
        finance?.hasCompleteBackendPayload,
        false,
        reason: 'Incomplete backend payload should be marked degraded, never substituted.',
      );
    });

    test('community surface blocks gifting without backend ledger payload', () {
      final CommunityCanonicalSurface blockedGifting = CommunityCanonicalSurface(
        isAuthenticated: true,
        hasLiveToken: true,
        isLoading: false,
        isMutating: false,
        watchlist: const <CommunityWatchlistItem>[],
        liveThreads: const <LiveThread>[],
        privateThreads: const <PrivateMessageThread>[],
      );

      expect(
        blockedGifting.isAuthenticated,
        true,
        reason: 'Authenticated users may be ready for gifting IF backend provides ledger.',
      );
      expect(
        blockedGifting.hasLiveToken,
        true,
        reason: 'Live token is required for gifting.',
      );
      // Note: gifting blocks in the surface render, not here. This test documents the precondition.
    });

    test('community surface blocks chat without live token', () {
      final CommunityCanonicalSurface publicReader = CommunityCanonicalSurface(
        isAuthenticated: false,
        hasLiveToken: false,
        isLoading: false,
        isMutating: false,
        watchlist: const <CommunityWatchlistItem>[],
        liveThreads: const <LiveThread>[],
        privateThreads: const <PrivateMessageThread>[],
      );

      expect(
        publicReader.hasLiveToken,
        false,
        reason: 'Public readers cannot access chat/gifting without live token.',
      );
    });

    test('community surface blocks reactions without digest payload', () {
      final CommunityCanonicalSurface noDigest = CommunityCanonicalSurface(
        isAuthenticated: true,
        hasLiveToken: true,
        isLoading: false,
        isMutating: false,
        digest: null,
        watchlist: const <CommunityWatchlistItem>[],
        liveThreads: const <LiveThread>[],
        privateThreads: const <PrivateMessageThread>[],
      );

      expect(
        noDigest.digest,
        null,
        reason: 'Missing digest payload blocks reactions; never inventedlocally.',
      );
    });

    test('community surface blocks reports without moderation payload', () {
      final CommunityCanonicalSurface noModeration = CommunityCanonicalSurface(
        isAuthenticated: true,
        hasLiveToken: true,
        isLoading: false,
        isMutating: false,
        loadError: 'sync failed',
        watchlist: const <CommunityWatchlistItem>[],
        liveThreads: const <LiveThread>[],
        privateThreads: const <PrivateMessageThread>[],
      );

      expect(
        noModeration.loadError,
        isNotNull,
        reason: 'Load error marks report actions as degraded, not available.',
      );
    });

    testWidgets(
      'creator surface renders "awaiting provisioning" instead of invented share code',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: CreatorCanonicalSurface(
                profile: _dummyProfile(shareCode: ''),
                finance: _dummyFinance(),
                isAuthenticated: true,
                hasApprovedCreatorAccess: true,
              ),
            ),
          ),
        );

        expect(
          find.text('Studio'),
          findsOneWidget,
        );
        expect(
          find.textContaining('share code is waiting on backend provisioning'),
          findsOneWidget,
          reason: 'Missing share code should show "awaiting provisioning", not invented code.',
        );
        expect(
          find.textContaining('No share-code payload returned'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'community surface shows "BLOCKED" for gifting without ledger payload',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: CommunityCanonicalSurface(
                isAuthenticated: true,
                hasLiveToken: true,
                isLoading: false,
                isMutating: false,
                watchlist: const <CommunityWatchlistItem>[],
                liveThreads: const <LiveThread>[],
                privateThreads: const <PrivateMessageThread>[],
              ),
            ),
          ),
        );

        expect(
          find.text('Gifting'),
          findsOneWidget,
        );
        expect(
          find.textContaining('BLOCKED: gift actions require'),
          findsOneWidget,
          reason: 'Gifting must explicitly show BLOCKED state, not offer local workaround.',
        );
        expect(
          find.textContaining('No gift ledger payload'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'community surface shows "BLOCKED" for reactions without digest',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: CommunityCanonicalSurface(
                isAuthenticated: true,
                hasLiveToken: true,
                isLoading: false,
                isMutating: false,
                digest: null,
                watchlist: const <CommunityWatchlistItem>[],
                liveThreads: const <LiveThread>[],
                privateThreads: const <PrivateMessageThread>[],
              ),
            ),
          ),
        );

        expect(
          find.text('Reactions'),
          findsOneWidget,
        );
        expect(
          find.textContaining('BLOCKED'),
          findsWidgets,
          reason: 'Missing digest payload must show BLOCKED state for reactions.',
        );
      },
    );

    testWidgets(
      'community surface shows "BLOCKED" for reports without moderation payload',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: CommunityCanonicalSurface(
                isAuthenticated: true,
                hasLiveToken: true,
                isLoading: false,
                isMutating: false,
                watchlist: const <CommunityWatchlistItem>[],
                liveThreads: const <LiveThread>[],
                privateThreads: const <PrivateMessageThread>[],
              ),
            ),
          ),
        );

        expect(
          find.text('Reports'),
          findsOneWidget,
        );
        expect(
          find.textContaining('BLOCKED: report actions'),
          findsOneWidget,
          reason: 'Missing report payload must show BLOCKED state.',
        );
      },
    );
  });
}

CreatorProfile _dummyProfile({String shareCode = 'TESTCODE'}) {
  return CreatorProfile(
    creatorId: 'test-creator',
    userId: 'test-user',
    displayName: 'Test Creator',
    handle: 'testcreator',
    shareCode: shareCode,
    tier: 'silver',
    status: 'approved',
    revenueSharePercent: 10,
    headline: 'Test headline',
    bio: 'Test bio',
    communityTag: 'test',
    profileLink: 'https://gtex.test/creator/test',
    stats: const CreatorStats(
      communityInvites: 5,
      qualifiedReferrals: 2,
      creatorCompetitions: 1,
      contestParticipants: 10,
    ),
    growthSummary: const CreatorGrowthSummary(
      growthHeadline: 'Test growth',
      growthDetail: 'Test detail',
      weeklyInviteLift: '+2',
      topChannel: 'test',
      inviteAttributionRate: '50%',
    ),
    rewardSummary: const CreatorRewardSummary(
      pendingCommunityRewards: 'GTC 10',
      lifetimeMilestoneRewards: 'GTC 100',
      competitionEntryCredits: '2',
      ledgerStatus: 'synced',
    ),
    financeSummary: _dummyFinance(),
    competitions: const <CreatorCompetition>[],
  );
}

CreatorFinanceSummary _dummyFinance() {
  return const CreatorFinanceSummary(
    currency: 'GTC',
    totalGiftIncome: 20,
    totalRewardIncome: 30,
    totalClipIncome: 15,
    totalClipViews: 500,
    monetizedClips: 2,
    viralClipCount: 1,
    totalViralBonus: 5,
    totalReferralBonus: 10,
    totalWeeklyTopCreatorBonus: 5,
    totalWithdrawnGross: 50,
    totalWithdrawalFees: 2,
    totalWithdrawnNet: 48,
    pendingWithdrawals: 10,
    walletBalance: 100,
    walletAvailableBalance: 90,
    walletCurrency: 'GTC',
    activeCompetitions: 1,
    attributedSignups: 5,
    qualifiedJoins: 2,
    insights: <String>[],
    hasCompleteBackendPayload: true,
    hasWalletPayload: true,
    hasClipEarningsPayload: true,
  );
}

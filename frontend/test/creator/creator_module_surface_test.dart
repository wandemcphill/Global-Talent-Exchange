import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/creator/creator.dart';
import 'package:gte_frontend/features/shell/domain/gtex_surface_state.dart';

void main() {
  testWidgets('creator wallet card blocks null backend balance', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: CreatorWalletCard(
            wallet: CreatorSurfaceState<CreatorWalletDto>(
              state: GtexSurfaceState.blocked,
              message: 'Backend available balance is missing.',
              blockedReason: 'creator.wallet.available_balance_missing',
            ),
          ),
        ),
      ),
    );

    expect(find.text('Creator wallet blocked'), findsOneWidget);
    expect(find.text('Balance blocked'), findsOneWidget);
    expect(
      find.text('creator.wallet.available_balance_missing'),
      findsOneWidget,
    );
  });

  testWidgets('clip moderation status card renders all moderation states', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: const <Widget>[
              ClipModerationStatusCard(clip: _pendingClip),
              ClipModerationStatusCard(clip: _approvedClip),
              ClipModerationStatusCard(clip: _flaggedClip),
              ClipModerationStatusCard(clip: _rejectedClip),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Under review'), findsOneWidget);
    expect(find.text('No creator action available'), findsOneWidget);
    expect(find.text('Live'), findsOneWidget);
    expect(find.text('View analytics'), findsOneWidget);
    expect(find.text('Flagged'), findsOneWidget);
    expect(find.text('Respond'), findsOneWidget);
    expect(find.text('Rejected'), findsOneWidget);
    expect(find.text('Appeal'), findsOneWidget);
  });

  testWidgets('creator studio surfaces degraded missing module contracts', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CreatorStudioScreen(
            profile: CreatorSurfaceState<CreatorProfileDto>.confirmed(
              const CreatorProfileDto(
                id: 'creator-1',
                displayName: 'Creator One',
                verificationStatus: CreatorVerificationStatus.verified,
              ),
            ),
            campaigns: CreatorSurfaceState<List<CampaignDto>>.degraded(
              data: const <CampaignDto>[
                CampaignDto(
                  id: 'competition-1',
                  title: 'Sunday Cup',
                  status: CampaignStatus.unknown,
                ),
              ],
              message: 'Module 7 campaign contract is not mounted.',
            ),
            clips: CreatorSurfaceState<List<SponsoredClipDto>>.degraded(
              data: const <SponsoredClipDto>[],
              message: 'Sponsored clips contract is not mounted.',
            ),
            analytics: CreatorSurfaceState<CreatorAnalyticsDto>.degraded(
              data: const CreatorAnalyticsDto(period: AnalyticsPeriod.week),
              message: 'Audience analytics fields are not present.',
            ),
            wallet: CreatorSurfaceState<CreatorWalletDto>.blocked(
              data: const CreatorWalletDto(
                balance: null,
                pendingSettlements: 0,
              ),
              message: 'Backend available balance is missing.',
              blockedReason: 'creator.wallet.available_balance_missing',
            ),
            moderation:
                CreatorSurfaceState<List<ModerationInboxItemDto>>.degraded(
                  data: const <ModerationInboxItemDto>[],
                  message: 'Creator moderation contract is not mounted.',
                ),
          ),
        ),
      ),
    );

    expect(find.text('Creator studio'), findsOneWidget);
    expect(find.text('Creator wallet blocked'), findsOneWidget);
    expect(find.text('Campaigns'), findsOneWidget);
    expect(find.text('Degraded'), findsWidgets);
    expect(find.text('Sponsored clips'), findsOneWidget);
    expect(find.text('Moderation inbox'), findsOneWidget);
  });
}

const SponsoredClipDto _pendingClip = SponsoredClipDto(
  id: 'clip-pending',
  campaignId: 'campaign-1',
  title: 'Pending clip',
  status: ClipModerationStatus.pending,
);

const SponsoredClipDto _approvedClip = SponsoredClipDto(
  id: 'clip-approved',
  campaignId: 'campaign-1',
  title: 'Approved clip',
  status: ClipModerationStatus.approved,
  viewCount: 400,
);

const SponsoredClipDto _flaggedClip = SponsoredClipDto(
  id: 'clip-flagged',
  campaignId: 'campaign-1',
  title: 'Flagged clip',
  status: ClipModerationStatus.flagged,
  moderationNote: 'Add usage proof.',
);

const SponsoredClipDto _rejectedClip = SponsoredClipDto(
  id: 'clip-rejected',
  campaignId: 'campaign-1',
  title: 'Rejected clip',
  status: ClipModerationStatus.rejected,
  moderationNote: 'Rights could not be verified.',
);

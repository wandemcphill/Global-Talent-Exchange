import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_viewer_presentation.dart';
import 'package:gte_frontend/features/3d/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/monetization/gifting_overlay.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/monetization/premium_controls.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  const Match3dMatchContext baseContext = Match3dMatchContext(
    matchId: 'backend-authored-match-1',
    competitionId: 'competition-1',
    isFinal: true,
    isMajorMatch: true,
    isSpectator: false,
    presentationMode: MatchViewerPresentationMode.replay,
  );

  test('legacy immersive access is quarantined for every entitlement', () {
    final Match3dMonetizationService service = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement.proManager(
        availableCoins: 2,
        unlockedMatchIds: <String>{'backend-authored-match-1'},
        tournamentBoostCompetitionIds: <String>{'competition-1'},
      ),
      initialRenderMode: RenderMode.auto,
    );

    expect(canAccess3D(baseContext, service.effectiveEntitlement), isFalse);
    expect(service.canUsePremiumCamera(baseContext), isFalse);
    expect(service.canUseFastReplay(baseContext), isFalse);
    expect(service.hasTournamentBoost(baseContext), isFalse);
    expect(service.effectiveRenderModeFor(baseContext), RenderMode.twoD);
    expect(service.wantsThreeD(baseContext), isFalse);
    expect(service.needsThreeDUnlock(baseContext), isFalse);

    service.selectRenderMode(RenderMode.threeD);

    expect(service.selectedRenderMode, RenderMode.twoD);
    expect(
      service.shouldOfferPrompt(
        moment: Match3dPromptMoment.bigMoment,
        context: baseContext,
        dedupeKey: 'goal-1',
      ),
      isFalse,
    );
  });

  test('legacy paid and rewarded actions are inert in quarantine', () async {
    final Match3dMonetizationService service = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement(availableCoins: 2),
      tournamentBoostPrice: 0.4,
    );

    final List<Match3dActionResult> results = <Match3dActionResult>[
      await service.unlockThreeDForMatch(baseContext),
      await service.upgradeTournamentExperience(baseContext),
      await service.unlockInteraction(
        Match3dPaidInteraction.slowMotionReplay,
        baseContext,
      ),
      await service.unlockInteraction(
        Match3dPaidInteraction.alternateCameraAngle,
        baseContext,
      ),
      await service.unlockInteraction(
        Match3dPaidInteraction.highlightNextAttack,
        baseContext,
      ),
      await service.sendCoinGift(0.1, baseContext),
      await service.claimRewardedAd(
        adId: 'rewarded-1',
        rewardCoins: 50,
        brand: 'brand-partner',
      ),
      service.sendReaction(Match3dReaction.fire, baseContext),
    ];

    for (final Match3dActionResult result in results) {
      expect(result.success, isFalse);
      expect(result.failureReason, Match3dFailureReason.unavailable);
      expect(result.message, contains('quarantined'));
    }
    expect(service.availableCoinBalance, closeTo(2, 0.0001));
    expect(service.hasClaimedRewardedAd('rewarded-1'), isFalse);
    expect(service.hasTournamentBoost(baseContext), isFalse);
    expect(
      service.hasInteraction(
        baseContext.matchId,
        Match3dPaidInteraction.slowMotionReplay,
      ),
      isFalse,
    );
    expect(service.shouldHighlightNextAttack(baseContext.matchId), isFalse);
    expect(
      service.speedOptionsFor(baseContext),
      Match3dMonetizationService.standardSpeedOptions,
    );
  });

  testWidgets('quarantined widgets expose no paid action CTAs', (
    WidgetTester tester,
  ) async {
    int actionCount = 0;

    await tester.pumpWidget(
      _app(
        PremiumControls(
          entitlement: const Match3dUserEntitlement.proManager(
            availableCoins: 10,
          ),
          selectedRenderMode: RenderMode.threeD,
          effectiveRenderMode: RenderMode.twoD,
          threeDAvailable: false,
          availableCoins: 10,
          cameraPreset: Match3dCameraPreset.broadcast,
          canUsePremiumCamera: true,
          canUseFastReplay: true,
          onRenderModeSelected: (_) => actionCount += 1,
          onCameraPresetSelected: (_) => actionCount += 1,
          onUnlockSlowMotion: () => actionCount += 1,
          onUnlockAlternateCamera: () => actionCount += 1,
          onUnlockHighlightAttack: () => actionCount += 1,
          onUpgradeTournament: () => actionCount += 1,
        ),
      ),
    );

    expect(find.text('Match center controls'), findsOneWidget);
    expect(find.byType(FilledButton), findsNothing);
    expect(find.textContaining(_paidCtaText), findsNothing);
    expect(actionCount, 0);

    await tester.pumpWidget(
      _app(
        GiftingOverlay(
          activeBursts: const <Match3dOverlayBurst>[],
          availableCoins: 10,
          onSendGift: (_) async => actionCount += 1,
          onSendReaction: (_) async => actionCount += 1,
        ),
      ),
    );

    expect(find.byType(FilledButton), findsNothing);
    expect(find.textContaining(_giftCtaText), findsNothing);
    expect(actionCount, 0);
  });
}

final RegExp _paidCtaText = RegExp(
  r'\b(?:Unlock|Tournament boost|Slow motion|Highlight next attack|Gift|React|coin)\b',
  caseSensitive: false,
);

final RegExp _giftCtaText = RegExp(
  r'\b(?:Gift|React|coin)\b',
  caseSensitive: false,
);

Widget _app(Widget child) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: Scaffold(body: Center(child: child)),
  );
}

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';

void main() {
  const Match3dMatchContext baseContext = Match3dMatchContext(
    matchId: 'match-1',
    competitionId: 'competition-1',
    isFinal: false,
    isMajorMatch: false,
    isSpectator: false,
    presentationMode: MatchViewerPresentationMode.replay,
  );

  test('canAccess3D allows premium, tournament boost, and match unlock', () {
    expect(
      canAccess3D(
        baseContext,
        const Match3dUserEntitlement.proManager(),
      ),
      isTrue,
    );
    expect(
      canAccess3D(
        baseContext,
        const Match3dUserEntitlement(
          tournamentBoostCompetitionIds: <String>{'competition-1'},
        ),
      ),
      isTrue,
    );
    expect(
      canAccess3D(
        baseContext,
        const Match3dUserEntitlement(
          unlockedMatchIds: <String>{'match-1'},
        ),
      ),
      isTrue,
    );
    expect(
      canAccess3D(
        baseContext,
        const Match3dUserEntitlement(),
      ),
      isFalse,
    );
  });

  test('unlockThreeDForMatch persists for that match session only', () async {
    final Match3dMonetizationService service = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement(availableCoins: 1),
    );

    final Match3dActionResult result = await service.unlockThreeDForMatch(
      baseContext,
    );

    expect(result.success, isTrue);
    expect(
      canAccess3D(baseContext, service.effectiveEntitlement),
      isTrue,
    );
    expect(
      canAccess3D(
        const Match3dMatchContext(
          matchId: 'match-2',
          competitionId: 'competition-1',
          isFinal: false,
          isMajorMatch: false,
          isSpectator: false,
          presentationMode: MatchViewerPresentationMode.replay,
        ),
        service.effectiveEntitlement,
      ),
      isFalse,
    );
    expect(service.availableCoinBalance, closeTo(0.8, 0.0001));
  });

  test('tournament boost only applies to the configured competition', () async {
    final Match3dMonetizationService service = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement(availableCoins: 2),
      tournamentBoostPrice: 0.4,
    );

    final Match3dActionResult result =
        await service.upgradeTournamentExperience(baseContext);

    expect(result.success, isTrue);
    expect(service.hasTournamentBoost(baseContext), isTrue);
    expect(
      service.hasTournamentBoost(
        const Match3dMatchContext(
          matchId: 'match-3',
          competitionId: 'competition-2',
          isFinal: false,
          isMajorMatch: false,
          isSpectator: false,
          presentationMode: MatchViewerPresentationMode.replay,
        ),
      ),
      isFalse,
    );
  });

  test('speed options follow standard, premium, and slow motion rules',
      () async {
    final Match3dMonetizationService standard = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement(availableCoins: 1),
    );
    expect(standard.speedOptionsFor(baseContext), <double>[1, 2, 4]);

    final Match3dMonetizationService premium = Match3dMonetizationService(
      entitlement: const Match3dUserEntitlement.proManager(availableCoins: 1),
    );
    expect(premium.speedOptionsFor(baseContext), <double>[1, 2, 4, 6]);

    await standard.unlockInteraction(
      Match3dPaidInteraction.slowMotionReplay,
      baseContext,
    );
    expect(standard.speedOptionsFor(baseContext), <double>[0.5, 1, 2, 4]);
  });

  test('prompt offers are throttled per match and moment', () {
    final Match3dMonetizationService service = Match3dMonetizationService();
    service.selectRenderMode(RenderMode.threeD);

    expect(
      service.shouldOfferPrompt(
        moment: Match3dPromptMoment.preMatch,
        context: baseContext,
      ),
      isTrue,
    );
    expect(
      service.shouldOfferPrompt(
        moment: Match3dPromptMoment.preMatch,
        context: baseContext,
      ),
      isFalse,
    );
    expect(
      service.shouldOfferPrompt(
        moment: Match3dPromptMoment.bigMoment,
        context: baseContext,
        dedupeKey: 'goal-1',
      ),
      isTrue,
    );
    expect(
      service.shouldOfferPrompt(
        moment: Match3dPromptMoment.bigMoment,
        context: baseContext,
        dedupeKey: 'goal-1',
      ),
      isFalse,
    );
  });
}

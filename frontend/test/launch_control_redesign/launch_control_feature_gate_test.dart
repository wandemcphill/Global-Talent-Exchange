import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';

void main() {
  test('feature gate maps canonical Batch 34 route families', () {
    expect(
      GtexLaunchControlFeatureGate.featureKeyForRouteData(
        const PlayerCardsBrowseRouteData(),
      ),
      'player_card_marketplace',
    );
    expect(
      GtexLaunchControlFeatureGate.featureKeyForRouteData(
        const FootballTransferCenterRouteData(),
      ),
      'transfer_hub',
    );
    expect(
      GtexLaunchControlFeatureGate.featureKeyForPath(
        '/creator-stadium/matches/match-lagos-final',
      ),
      'ticketing',
    );
    expect(
      GtexLaunchControlFeatureGate.featureKeyForPath('/app/coin-traders'),
      'coin_traders',
    );
    expect(
      GtexLaunchControlFeatureGate.featureKeyForPath(
        '/app/market?player=player-jude',
      ),
      isNull,
    );
  });

  test('feature gate blocks maintenance and internal launch states', () async {
    final GtexFeatureGateDecision broadcast =
        await GtexLaunchControlFeatureGate.resolveRoutePath(
          route: '/broadcast/live',
          baseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          accessToken: 'fixture-token',
          isAdmin: false,
        );

    expect(broadcast.allowed, isFalse);
    expect(broadcast.reason, GtexFeatureGateBlockReason.maintenance);
    expect(broadcast.message, contains('Rights worker paused'));

    final GtexFeatureGateDecision transfer =
        await GtexLaunchControlFeatureGate.resolveRouteData(
          route: const FootballTransferCenterRouteData(),
          baseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          accessToken: 'fixture-token',
          isAdmin: false,
        );

    expect(transfer.allowed, isFalse);
    expect(transfer.reason, GtexFeatureGateBlockReason.hidden);

    final GtexFeatureGateDecision adminPreview =
        await GtexLaunchControlFeatureGate.resolveRouteData(
          route: const FootballTransferCenterRouteData(),
          baseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          accessToken: 'fixture-token',
          isAdmin: true,
        );

    expect(adminPreview.allowed, isTrue);
  });

  test(
    'navigation guard applies launch-control blocks before rendering',
    () async {
      final GteGuardResolution resolution = await GteNavigationGuardResolver(
        dependencies: const GteNavigationDependencies(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          accessToken: 'fixture-token',
          currentUserRole: 'user',
        ),
      ).resolve(const BroadcastDeskRouteData());

      expect(resolution.blockedByFeatureGate, isTrue);
      expect(
        resolution.fallbackReason,
        GteNavigationFallbackReason.featureFlagBlocked,
      );
      expect(resolution.featureGateDecision?.featureKey, 'broadcast');
    },
  );
}

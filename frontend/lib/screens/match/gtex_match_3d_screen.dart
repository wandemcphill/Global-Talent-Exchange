import 'package:flutter/material.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/features/match/live_match_viewer_route_support.dart';

import 'gtex_match_viewer_screen.dart'
    show MatchViewContinuationLoader, MatchViewStateLoader;

class GtexMatch3dScreen extends StatelessWidget {
  const GtexMatch3dScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.fallbackSnapshot,
    this.preferFallback = false,
    this.viewStateLoader,
    this.continuationLoader,
    this.entitlement = const Match3dUserEntitlement(),
    this.giftClient,
    this.engineBridge,
    this.androidLiveBootstrapProvisioner,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final Match3dUserEntitlement entitlement;
  final MatchGiftClient? giftClient;
  final Match3DBridge? engineBridge;
  final Match3dAndroidLiveBootstrapProvisioner? androidLiveBootstrapProvisioner;

  @override
  Widget build(BuildContext context) {
    return const MatchRouteBlockedScreen(
      title: 'Coming soon',
      subtitle:
          'Advanced match viewing is coming soon. The launch matchday experience is the 2D tactical viewer.',
      reason:
          'This route is blocked for launch while managers use the 2D match viewer.',
      detailTitle: 'Coming soon',
      detailSubtitle:
          'Open fixtures and use the 2D match viewer for launch matchday.',
    );
  }
}

import 'package:flutter/material.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

typedef MatchViewStateLoader = Future<MatchViewState> Function();
typedef MatchViewContinuationLoader =
    Future<MatchViewState> Function({
      required String matchKey,
      required String continuationToken,
    });

class GtexMatchViewerScreen extends StatelessWidget {
  const GtexMatchViewerScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.fallbackSnapshot,
    this.preferFallback = false,
    this.presentationMode = MatchViewerPresentationMode.replay,
    this.viewStateLoader,
    this.continuationLoader,
    this.renderMode = RenderMode.twoD,
    this.isSpectator = false,
    this.isMajorMatch = false,
    this.entitlement,
    this.monetizationService,
    this.onPurchaseIntent,
    this.tournamentBoostPrice,
    this.titleOverride,
    this.engineBridge,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;
  final MatchViewerPresentationMode presentationMode;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final RenderMode renderMode;
  final bool isSpectator;
  final bool isMajorMatch;
  final Match3dUserEntitlement? entitlement;
  final Match3dMonetizationService? monetizationService;
  final Match3dPurchaseIntentHandler? onPurchaseIntent;
  final double? tournamentBoostPrice;
  final String? titleOverride;
  final Match3DBridge? engineBridge;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Match viewer unavailable',
      message:
          'Deep match viewer routes are blocked until live sessions, commentary, and event streams come from the real backend without fabricated fallback state.',
      icon: Icons.live_tv_outlined,
    );
  }
}

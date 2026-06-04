import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/data/match_gift_api.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/live_match_viewer_route_support.dart';

import 'gtex_match_viewer_screen.dart'
    show MatchViewContinuationLoader, MatchViewStateLoader;

class GtexMatchRuntimeBlockedScreen extends StatelessWidget {
  const GtexMatchRuntimeBlockedScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.viewStateLoader,
    this.continuationLoader,
    Object? entitlement,
    this.giftClient,
    Object? engineBridge,
    Object? androidLiveBootstrapProvisioner,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final MatchGiftClient? giftClient;

  @override
  Widget build(BuildContext context) {
    return const MatchRouteBlockedScreen(
      title: 'Route blocked',
      subtitle:
          'This match viewing lane is quarantined. The canonical matchday experience is the backend-authoritative 2D tactical viewer.',
      reason:
          'This route is blocked for launch while managers use the 2D match viewer.',
      detailTitle: 'Backend route required',
      detailSubtitle:
          'Use the live match center route and wait for backend score, clock, timeline, and overlay payloads.',
    );
  }
}

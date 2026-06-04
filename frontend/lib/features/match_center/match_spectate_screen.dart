import 'package:flutter/material.dart';

import 'live_match_viewer_route_support.dart';

class MatchSpectateScreen extends StatelessWidget {
  const MatchSpectateScreen({super.key});

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

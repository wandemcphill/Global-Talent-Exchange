import 'package:flutter/material.dart';

import 'live_match_viewer_route_support.dart';

class Match3dRouteScreen extends StatelessWidget {
  const Match3dRouteScreen({super.key, required this.matchKey});

  final String matchKey;

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

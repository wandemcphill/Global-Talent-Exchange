import 'package:flutter/material.dart';

import 'live_match_viewer_route_support.dart';

class Match3dRouteScreen extends StatelessWidget {
  const Match3dRouteScreen({super.key, required this.matchKey});

  final String matchKey;

  @override
  Widget build(BuildContext context) {
    return const MatchRouteBlockedScreen(
      title: '3D Match Viewer',
      subtitle:
          'This deep route stays blocked until live viewer sessions, commentary, and event streams are available without fabricated fallback state.',
      reason:
          '3D viewer routes are unavailable until the real backend can serve the full live match-viewer session without fallback substitution.',
    );
  }
}

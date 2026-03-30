import 'package:flutter/material.dart';

import 'live_match_viewer_route_support.dart';

class MatchSpectateScreen extends StatelessWidget {
  const MatchSpectateScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const MatchRouteBlockedScreen(
      title: '2D Spectate Probe',
      subtitle:
          'This manual probe route stays blocked until live viewer sessions, commentary, and event streams are available without fabricated fallback state.',
      reason:
          'The 2D spectate probe is unavailable until the real backend can serve the full live match-viewer session without fallback substitution.',
    );
  }
}

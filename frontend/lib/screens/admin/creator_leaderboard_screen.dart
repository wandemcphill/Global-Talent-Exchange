import 'package:flutter/material.dart';

import '../../data/creator_api.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class CreatorLeaderboardScreen extends StatelessWidget {
  const CreatorLeaderboardScreen({super.key, required this.api});

  final CreatorApi api;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Creator leaderboard unavailable',
      message:
          'Creator leaderboard routes are blocked until creator rankings come from the real backend without fixture substitution.',
      icon: Icons.leaderboard_outlined,
    );
  }
}

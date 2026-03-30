import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

class GteMatchHighlightsScreen extends StatelessWidget {
  const GteMatchHighlightsScreen({
    super.key,
    required this.competition,
    this.isAuthenticated = false,
  });

  final CompetitionSummary competition;
  final bool isAuthenticated;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Match highlights unavailable',
      message:
          'Match highlights routes are blocked until clip archives and match recaps come from the real backend without fabricated fallback snapshots.',
      icon: Icons.play_circle_outline,
    );
  }
}

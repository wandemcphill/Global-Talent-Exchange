import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

class GteHalftimeAnalyticsScreen extends StatelessWidget {
  const GteHalftimeAnalyticsScreen({super.key, required this.competition});

  final CompetitionSummary competition;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Halftime analytics unavailable',
      message:
          'Halftime analytics routes are blocked until tactical summaries and match analytics come from the real backend only.',
      icon: Icons.analytics_outlined,
    );
  }
}

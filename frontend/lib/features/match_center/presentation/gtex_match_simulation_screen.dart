import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/live_match_viewer_route_support.dart';

class GtexMatchSimulationScreen extends StatelessWidget {
  const GtexMatchSimulationScreen({
    super.key,
    required this.result,
    this.title,
    this.competitionLabel,
  });

  final Object result;
  final String? title;
  final String? competitionLabel;

  @override
  Widget build(BuildContext context) {
    return MatchRouteBlockedScreen(
      title: title ?? 'Backend route blocked',
      subtitle:
          'Local match playback is quarantined for the canonical GTEX match center.',
      reason:
          'GTEX match state must come from backend-authored realtime events, not local autoplay timelines.',
      detailTitle: competitionLabel ?? '2D realtime match center only',
      detailSubtitle:
          'Open a backend-published fixture to watch the canonical 2D broadcast match center.',
    );
  }
}

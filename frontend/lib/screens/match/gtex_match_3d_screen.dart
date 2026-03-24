import 'package:flutter/material.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/screens/match/gtex_match_viewer_screen.dart';

class GtexMatch3dScreen extends StatelessWidget {
  const GtexMatch3dScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.fallbackSnapshot,
    this.preferFallback = false,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;

  @override
  Widget build(BuildContext context) {
    return GtexMatchViewerScreen(
      competition: competition,
      matchKey: matchKey,
      fallbackSnapshot: fallbackSnapshot,
      preferFallback: preferFallback,
      presentationMode: MatchViewerPresentationMode.replay,
      renderMode: RenderMode.threeD,
      titleOverride: '3D Match Viewer',
    );
  }
}

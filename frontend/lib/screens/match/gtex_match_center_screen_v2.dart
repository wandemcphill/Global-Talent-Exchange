import 'package:flutter/material.dart';

import '../../features/match_redesign/presentation/gtex_match_center_screen_v2.dart' as redesign;
import '../../features/match_redesign/data/gtex_match_demo_repository.dart';

/// Route-compatible wrapper for the GTEX V2 2D Match Center.
///
/// Codex should mount this from the existing match route instead of creating
/// a second router. Pass the real match id from route params where available.
class GtexMatchCenterScreenV2 extends StatelessWidget {
  const GtexMatchCenterScreenV2({
    super.key,
    this.matchId = 'demo-live-match',
    this.repository,
  });

  final String matchId;
  final GtexMatchRepository? repository;

  @override
  Widget build(BuildContext context) {
    return redesign.GtexMatchCenterScreenV2(
      matchId: matchId,
      repository: repository,
    );
  }
}

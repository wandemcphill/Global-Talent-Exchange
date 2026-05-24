import 'package:flutter/material.dart';

import '../../features/match_redesign/match_redesign.dart' as redesign;

/// Route-compatible wrapper for the GTEX V2 2D Match Center.
///
/// Mounted from the existing match route so the 2D match center keeps one
/// canonical router. Pass the real match id from route params where available.
class GtexMatchCenterScreenV2 extends StatelessWidget {
  const GtexMatchCenterScreenV2({
    super.key,
    required this.matchId,
    this.repository,
  });

  final String matchId;
  final redesign.GtexMatchRepository? repository;

  @override
  Widget build(BuildContext context) {
    return redesign.GtexMatchCenterScreenV2(
      matchId: matchId,
      repository: repository,
    );
  }
}

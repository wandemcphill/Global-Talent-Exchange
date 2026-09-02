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
    this.onOpenReplay,
    this.onExit,
  });

  final String matchId;
  final redesign.GtexMatchRepository? repository;

  /// Forwarded to the match centre so full time can hand off to the replay
  /// archive instead of terminating the journey.
  final ValueChanged<String>? onOpenReplay;

  /// Forwarded so error and empty states can offer a real way back.
  final VoidCallback? onExit;

  @override
  Widget build(BuildContext context) {
    return redesign.GtexMatchCenterScreenV2(
      matchId: matchId,
      repository: repository,
      onOpenReplay: onOpenReplay,
      onExit: onExit,
    );
  }
}

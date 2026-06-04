import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_event.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';

class GtexBroadcastHudState {
  const GtexBroadcastHudState({
    required this.clockLabel,
    required this.statusLabel,
    required this.scoreMasked,
    required this.controlsVisible,
    required this.isPaused,
    required this.speedLabel,
    required this.mode,
    required this.viewType,
    this.homeScore,
    this.awayScore,
    this.eventOverlay,
    this.commentary,
    this.commentaryDetail,
    this.varOverlay,
    this.socialReactions = const <String>[],
    this.showIntroOverlay = false,
    this.showFullTimeOverlay = false,
    this.showSocialRail = false,
    this.canGift = false,
  });

  final String clockLabel;
  final String statusLabel;
  final int? homeScore;
  final int? awayScore;
  final bool scoreMasked;
  final bool controlsVisible;
  final bool isPaused;
  final String speedLabel;
  final GtexMatchRenderMode mode;
  final GtexMatchViewType viewType;
  final GtexBroadcastEvent? eventOverlay;
  final String? commentary;
  final String? commentaryDetail;
  final GtexBroadcastEvent? varOverlay;
  final List<String> socialReactions;
  final bool showIntroOverlay;
  final bool showFullTimeOverlay;
  final bool showSocialRail;
  final bool canGift;
}

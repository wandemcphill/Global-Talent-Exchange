import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_commentary_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_event_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_fulltime_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_hidden_controls_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_match_intro_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_scoreboard_overlay.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_social_reactions_rail.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_var_overlay.dart';

class GtexBroadcastHudLayer extends StatelessWidget {
  const GtexBroadcastHudLayer({
    super.key,
    required this.viewState,
    required this.hudState,
    required this.platformMode,
    required this.matchTitle,
    required this.competitionLabel,
    required this.onTogglePause,
    required this.onCycleSpeed,
    required this.onReplay,
    required this.onGiftTap,
    required this.onOpenHighlights,
  });

  final MatchViewState viewState;
  final GtexBroadcastHudState hudState;
  final GtexPlatformMode platformMode;
  final String matchTitle;
  final String competitionLabel;
  final VoidCallback onTogglePause;
  final VoidCallback onCycleSpeed;
  final VoidCallback onReplay;
  final VoidCallback onGiftTap;
  final VoidCallback? onOpenHighlights;

  @override
  Widget build(BuildContext context) {
    final bool tvMode = platformMode == GtexPlatformMode.tv;
    return Stack(
      fit: StackFit.expand,
      children: <Widget>[
        GtexScoreboardOverlay(viewState: viewState, hudState: hudState),
        GtexEventOverlay(event: hudState.eventOverlay),
        GtexCommentaryOverlay(
          commentary: hudState.commentary,
          detail: hudState.commentaryDetail,
        ),
        if (!tvMode)
          GtexSocialReactionsRail(
            visible: hudState.showSocialRail,
            reactions: hudState.socialReactions,
            showGiftAction: hudState.canGift,
            onGiftTap: onGiftTap,
          ),
        if (!tvMode)
          GtexHiddenControlsOverlay(
            visible: hudState.controlsVisible,
            isPaused: hudState.isPaused,
            speedLabel: hudState.speedLabel,
            onTogglePause: onTogglePause,
            onCycleSpeed: onCycleSpeed,
            onReplay: onReplay,
          ),
        GtexMatchIntroOverlay(
          visible: hudState.showIntroOverlay,
          competitionLabel: competitionLabel,
          matchTitle: matchTitle,
        ),
        GtexVarOverlay(event: hudState.varOverlay),
        GtexFulltimeOverlay(
          visible: hudState.showFullTimeOverlay,
          viewState: viewState,
          onOpenHighlights: onOpenHighlights,
        ),
      ],
    );
  }
}

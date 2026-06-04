import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_commentary_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_event_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_fulltime_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_hidden_controls_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_match_intro_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_scoreboard_overlay.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_social_reactions_rail.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_var_overlay.dart';

class GtexBroadcastHudLayer extends StatelessWidget {
  const GtexBroadcastHudLayer({
    super.key,
    required this.viewState,
    required this.hudState,
    required this.platformMode,
    required this.matchTitle,
    required this.competitionLabel,
    required this.onSyncFrame,
    required this.onGiftTap,
    required this.onOpenHighlights,
  });

  final MatchViewState viewState;
  final GtexBroadcastHudState hudState;
  final GtexPlatformMode platformMode;
  final String matchTitle;
  final String competitionLabel;
  final VoidCallback onSyncFrame;
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
            onSyncFrame: onSyncFrame,
            onOpenHighlights: onOpenHighlights,
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

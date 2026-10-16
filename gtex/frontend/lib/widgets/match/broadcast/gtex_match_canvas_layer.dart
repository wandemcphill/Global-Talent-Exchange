import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_match_canvas.dart';

class GtexMatchCanvasLayer extends StatelessWidget {
  const GtexMatchCanvasLayer({
    super.key,
    required this.viewState,
    required this.frame,
    required this.hudState,
    required this.viewType,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final GtexBroadcastHudState hudState;
  final GtexMatchViewType viewType;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      child: viewType == GtexMatchViewType.pseudo3D
          ? GtexPseudo3DMatchCanvas(
              key: const ValueKey<String>('pseudo3d-canvas'),
              viewState: viewState,
              frame: frame,
              hudState: hudState,
            )
          : Pitch2dWidget(
              key: const ValueKey<String>('2d-canvas'),
              viewState: viewState,
              frame: frame,
              showFormationOverlay: false,
            ),
    );
  }
}

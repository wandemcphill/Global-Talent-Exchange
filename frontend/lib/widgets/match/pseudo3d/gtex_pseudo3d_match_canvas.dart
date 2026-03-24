import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_camera_viewport.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_pitch.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_players_layer.dart';

class GtexPseudo3DMatchCanvas extends StatelessWidget {
  const GtexPseudo3DMatchCanvas({
    super.key,
    required this.viewState,
    required this.frame,
    required this.hudState,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final GtexBroadcastHudState hudState;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: AspectRatio(
        aspectRatio: 105 / 68,
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
            gradient: const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[
                Color(0xFF102433),
                Color(0xFF07131D),
              ],
            ),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final GtexPseudo3DPitchProjection projection =
                    GtexPseudo3DPitchProjection.forSize(constraints.biggest);
                final double normalizedX =
                    ((frame.ball.position.x - 50) / 50).clamp(-1, 1).toDouble();
                final double normalizedY =
                    ((frame.ball.position.y - 50) / 50).clamp(-1, 1).toDouble();
                final double zoom = (1.01 +
                        hudState.mode.cameraZoomBias +
                        (hudState.varOverlay != null ? 0.05 : 0) +
                        (hudState.eventOverlay != null ? 0.03 : 0))
                    .clamp(1.01, 1.18);
                final Offset pan = Offset(
                  -normalizedX * constraints.maxWidth * 0.07,
                  -normalizedY * constraints.maxHeight * 0.04,
                );
                return GtexPseudo3DCameraViewport(
                  zoom: zoom,
                  pan: pan,
                  child: Stack(
                    fit: StackFit.expand,
                    children: <Widget>[
                      GtexPseudo3DPitch(projection: projection),
                      IgnorePointer(
                        child: GtexPseudo3DPlayersLayer(
                          viewState: viewState,
                          frame: frame,
                          projection: projection,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

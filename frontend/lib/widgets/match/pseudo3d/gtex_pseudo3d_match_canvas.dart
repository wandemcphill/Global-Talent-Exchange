import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_camera_viewport.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_pitch.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_players_layer.dart';
import 'package:gte_frontend/widgets/match/pseudo3d/gtex_pseudo3d_telemetry.dart';

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

  static GtexPseudo3DTelemetryStyle describeTelemetryStyle({
    required MatchTimelineFrame frame,
    required GtexMatchRenderMode mode,
  }) {
    return GtexPseudo3DTelemetryStyle.fromFrame(frame: frame, mode: mode);
  }

  @override
  Widget build(BuildContext context) {
    final GtexPseudo3DTelemetryStyle telemetryStyle = describeTelemetryStyle(
      frame: frame,
      mode: hudState.mode,
    );
    return RepaintBoundary(
      child: AspectRatio(
        aspectRatio: 105 / 68,
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: Colors.white.withValues(alpha: telemetryStyle.borderAlpha),
            ),
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: telemetryStyle.stadiumGradient,
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
                        telemetryStyle.cameraZoomBias +
                        (hudState.varOverlay != null ? 0.05 : 0) +
                        (hudState.eventOverlay != null ? 0.03 : 0))
                    .clamp(1.01, 1.18);
                final Offset pan = Offset(
                  ((-normalizedX * 0.06) - telemetryStyle.cameraLeadX * 0.22) *
                      constraints.maxWidth,
                  ((-normalizedY * 0.03) - telemetryStyle.cameraLeadY * 0.16) *
                      constraints.maxHeight,
                );
                return GtexPseudo3DCameraViewport(
                  zoom: zoom,
                  pan: pan,
                  child: Stack(
                    fit: StackFit.expand,
                    children: <Widget>[
                      GtexPseudo3DPitch(
                        projection: projection,
                        telemetryStyle: telemetryStyle,
                        frame: frame,
                      ),
                      IgnorePointer(
                        child: GtexPseudo3DPlayersLayer(
                          viewState: viewState,
                          frame: frame,
                          projection: projection,
                          telemetryStyle: telemetryStyle,
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

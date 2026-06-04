import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';

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
    final GtexMatchViewType canonicalViewType = viewType.canonical;
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      child: Pitch2dWidget(
        key: ValueKey<String>('${canonicalViewType.name}-canvas'),
        viewState: viewState,
        frame: frame,
        showFormationOverlay: false,
      ),
    );
  }
}

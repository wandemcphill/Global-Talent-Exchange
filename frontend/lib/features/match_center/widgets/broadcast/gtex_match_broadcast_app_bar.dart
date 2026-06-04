import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_mode_selector_button.dart';

class GtexMatchBroadcastAppBar extends StatelessWidget
    implements PreferredSizeWidget {
  const GtexMatchBroadcastAppBar({
    super.key,
    required this.title,
    required this.competitionLabel,
    required this.mode,
    required this.onModeSelected,
  });

  final String title;
  final String competitionLabel;
  final GtexMatchRenderMode mode;
  final ValueChanged<GtexMatchRenderMode> onModeSelected;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight + 10);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: const Color(0xFF09131E),
      surfaceTintColor: Colors.transparent,
      titleSpacing: 0,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(title, maxLines: 1, overflow: TextOverflow.ellipsis),
          Text(
            competitionLabel,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: Colors.white70),
          ),
        ],
      ),
      actions: <Widget>[
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: Center(
            child: GtexModeSelectorButton(
              currentMode: mode,
              onSelected: onModeSelected,
            ),
          ),
        ),
      ],
    );
  }
}

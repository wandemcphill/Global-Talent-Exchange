import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';

class GtexModeSelectorButton extends StatelessWidget {
  const GtexModeSelectorButton({
    super.key,
    required this.currentMode,
    required this.onSelected,
  });

  static const Key buttonKey = Key('gtex_mode_selector_button');

  final GtexMatchRenderMode currentMode;
  final ValueChanged<GtexMatchRenderMode> onSelected;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<GtexMatchRenderMode>(
      key: buttonKey,
      tooltip: 'Viewing mode',
      initialValue: currentMode,
      onSelected: onSelected,
      itemBuilder: (BuildContext context) {
        return GtexMatchRenderMode.values.map((GtexMatchRenderMode mode) {
          return PopupMenuItem<GtexMatchRenderMode>(
            value: mode,
            child: Row(
              children: <Widget>[
                Expanded(
                  child: Text(mode.label),
                ),
                Text(
                  _durationLabel(mode),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          );
        }).toList(growable: false);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(
              currentMode.label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(width: 6),
            const Icon(
              Icons.keyboard_arrow_down_rounded,
              color: Colors.white,
            ),
          ],
        ),
      ),
    );
  }

  String _durationLabel(GtexMatchRenderMode mode) {
    switch (mode) {
      case GtexMatchRenderMode.quick:
        return '3-5m';
      case GtexMatchRenderMode.standard:
        return '7-10m';
      case GtexMatchRenderMode.cinematic:
        return '10-15m';
    }
  }
}

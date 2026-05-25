import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';
import 'gtex_live_status_chip.dart';

enum GtexValueState { live, recent, estimated, locked, unavailable }

enum GtexValueDisplaySize { small, standard, large }

class GtexValueDisplay extends StatelessWidget {
  const GtexValueDisplay({
    super.key,
    required this.valueLabel,
    this.deltaLabel,
    this.state = GtexValueState.recent,
    this.size = GtexValueDisplaySize.standard,
    this.showDelta = true,
    this.showStateIndicator = true,
    this.updatedLabel,
  });

  final String valueLabel;
  final String? deltaLabel;
  final GtexValueState state;
  final GtexValueDisplaySize size;
  final bool showDelta;
  final bool showStateIndicator;
  final String? updatedLabel;

  @override
  Widget build(BuildContext context) {
    final TextStyle baseStyle = _valueStyle(context, size);
    final bool locked =
        state == GtexValueState.locked || state == GtexValueState.unavailable;
    final String displayValue =
        locked
            ? '-'
            : state == GtexValueState.estimated
            ? '~$valueLabel'
            : valueLabel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Flexible(
              child: Text(
                displayValue,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: baseStyle.copyWith(
                  color:
                      locked ? GtexColors.textTertiary : GtexColors.textPrimary,
                ),
              ),
            ),
            if (showDelta &&
                deltaLabel != null &&
                deltaLabel!.trim().isNotEmpty) ...<Widget>[
              const SizedBox(width: GtexSpacing.xs),
              Text(
                deltaLabel!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: _deltaColor(deltaLabel!),
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ],
        ),
        if (showStateIndicator || updatedLabel != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.xxs),
          Wrap(
            spacing: GtexSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              if (showStateIndicator)
                GtexLiveStatusChip(
                  status: _liveStatusFor(state),
                  label: _labelFor(state),
                  compact: true,
                  pulse: state == GtexValueState.live,
                ),
              if (updatedLabel != null)
                Text(
                  updatedLabel!,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.textSecondary,
                    fontFeatures: const <FontFeature>[
                      FontFeature.tabularFigures(),
                    ],
                  ),
                ),
            ],
          ),
        ],
      ],
    );
  }

  TextStyle _valueStyle(BuildContext context, GtexValueDisplaySize size) {
    final double fontSize = switch (size) {
      GtexValueDisplaySize.small => 13,
      GtexValueDisplaySize.standard => 16,
      GtexValueDisplaySize.large => 22,
    };
    return Theme.of(context).textTheme.titleMedium?.copyWith(
          fontFamily: GtexText.monoFamily,
          fontSize: fontSize,
          fontWeight: FontWeight.w800,
          height: 1,
          fontFeatures: const <FontFeature>[FontFeature.tabularFigures()],
        ) ??
        TextStyle(
          fontFamily: GtexText.monoFamily,
          fontSize: fontSize,
          fontWeight: FontWeight.w800,
          height: 1,
          color: GtexColors.textPrimary,
          fontFeatures: const <FontFeature>[FontFeature.tabularFigures()],
        );
  }

  Color _deltaColor(String delta) {
    final String trimmed = delta.trim();
    if (trimmed.startsWith('-') || trimmed.contains('down')) {
      return GtexColors.accentRed;
    }
    if (trimmed.startsWith('+') || trimmed.contains('up')) {
      return GtexColors.accentPrimary;
    }
    return GtexColors.textSecondary;
  }

  GtexLiveStatus _liveStatusFor(GtexValueState state) {
    return switch (state) {
      GtexValueState.live => GtexLiveStatus.live,
      GtexValueState.recent => GtexLiveStatus.recent,
      GtexValueState.estimated => GtexLiveStatus.pending,
      GtexValueState.locked => GtexLiveStatus.locked,
      GtexValueState.unavailable => GtexLiveStatus.blocked,
    };
  }

  String _labelFor(GtexValueState state) {
    return switch (state) {
      GtexValueState.live => 'Live',
      GtexValueState.recent => 'Recent',
      GtexValueState.estimated => 'Estimated',
      GtexValueState.locked => 'Locked',
      GtexValueState.unavailable => 'Unavailable',
    };
  }
}

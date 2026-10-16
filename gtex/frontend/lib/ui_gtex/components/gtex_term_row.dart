import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';

/// One label/value line in a terms block.
///
/// The market panel and the canonical player detail were each rendering
/// their own private version of this row against the same kind of data, so
/// the two surfaces drifted apart. They now share one.
class GtexTermRow {
  const GtexTermRow(this.label, this.value, {this.valueColor});

  /// A row whose value the backend did not supply. Renders as an em dash so
  /// absence never reads as a figure.
  const GtexTermRow.unknown(this.label)
    : value = '—',
      valueColor = GtexColors.textTertiary;

  final String label;
  final String value;
  final Color? valueColor;

  /// Builds a row from a nullable value, falling back to the unknown state.
  factory GtexTermRow.orUnknown(
    String label,
    String? value, {
    Color? valueColor,
  }) {
    final String? trimmed = value?.trim();
    if (trimmed == null || trimmed.isEmpty) {
      return GtexTermRow.unknown(label);
    }
    return GtexTermRow(label, trimmed, valueColor: valueColor);
  }
}

class GtexTermsList extends StatelessWidget {
  const GtexTermsList({super.key, required this.rows, this.dense = false});

  final List<GtexTermRow> rows;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        for (final GtexTermRow row in rows)
          Padding(
            padding: EdgeInsets.symmetric(vertical: dense ? 3 : 5),
            child: Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    row.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: GtexColors.textMuted,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    row.value,
                    textAlign: TextAlign.end,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: row.valueColor ?? GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';

class GteMetricChip extends StatelessWidget {
  const GteMetricChip({
    super.key,
    required this.label,
    required this.value,
    this.positive = true,
  });

  final String label;
  final String value;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    final Color tone = positive ? GteShellTheme.positive : GteShellTheme.negative;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.09),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: tone.withOpacity(0.28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: tone),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../providers/gte_mock_api.dart';
import 'gte_shell_theme.dart';

class GteTrendStrip extends StatelessWidget {
  const GteTrendStrip({
    super.key,
    required this.points,
    this.height = 68,
  });

  final List<TrendPoint> points;
  final double height;

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return const SizedBox.shrink();
    }

    final double minValue = points
        .map((TrendPoint point) => point.value)
        .reduce((double a, double b) => a < b ? a : b);
    final double maxValue = points
        .map((TrendPoint point) => point.value)
        .reduce((double a, double b) => a > b ? a : b);
    final double spread = (maxValue - minValue).abs() < 0.001 ? 1 : maxValue - minValue;

    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: points.map((TrendPoint point) {
          final double normalized = (point.value - minValue) / spread;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: <Widget>[
                  Expanded(
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 260),
                        height: 18 + (normalized * (height - 26)),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(999),
                          gradient: const LinearGradient(
                            begin: Alignment.bottomCenter,
                            end: Alignment.topCenter,
                            colors: <Color>[
                              GteShellTheme.accent,
                              GteShellTheme.accentWarm,
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    point.label,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontSize: 11),
                  ),
                ],
              ),
            ),
          );
        }).toList(growable: false),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ReputationLoadingSkeleton extends StatelessWidget {
  const ReputationLoadingSkeleton({
    super.key,
    this.lines = 4,
    this.emphasized = false,
  });

  final int lines;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: emphasized,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _SkeletonBar(widthFactor: 0.34, height: 16),
          const SizedBox(height: 14),
          _SkeletonBar(widthFactor: 0.56, height: 36),
          const SizedBox(height: 18),
          for (int index = 0; index < lines; index += 1) ...<Widget>[
            _SkeletonBar(
              widthFactor: index.isEven ? 0.92 : 0.72,
              height: 12,
            ),
            if (index < lines - 1) const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _SkeletonBar extends StatelessWidget {
  const _SkeletonBar({
    required this.widthFactor,
    required this.height,
  });

  final double widthFactor;
  final double height;

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      child: Container(
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: GteShellTheme.textMuted.withValues(alpha: 0.14),
        ),
      ),
    );
  }
}

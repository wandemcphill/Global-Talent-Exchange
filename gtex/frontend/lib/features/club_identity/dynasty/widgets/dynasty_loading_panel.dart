import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';

class DynastyLoadingPanel extends StatelessWidget {
  const DynastyLoadingPanel({
    super.key,
    this.lines = 3,
    this.height = 160,
  });

  final int lines;
  final double height;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: SizedBox(
        height: height,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const _LoadingBar(width: 160),
            const SizedBox(height: 18),
            for (int index = 0; index < lines; index++) ...<Widget>[
              _LoadingBar(width: index == lines - 1 ? 180 : double.infinity),
              const SizedBox(height: 10),
            ],
          ],
        ),
      ),
    );
  }
}

class _LoadingBar extends StatelessWidget {
  const _LoadingBar({
    required this.width,
  });

  final double width;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: 14,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.stroke.withValues(alpha: 0.55),
      ),
    );
  }
}

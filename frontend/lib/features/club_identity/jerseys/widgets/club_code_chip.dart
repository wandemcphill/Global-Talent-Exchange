import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';

class ClubCodeChip extends StatelessWidget {
  const ClubCodeChip({
    super.key,
    required this.code,
  });

  final String code;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: GteShellTheme.panelStrong,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Text(
        code,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              letterSpacing: 1.1,
            ),
      ),
    );
  }
}

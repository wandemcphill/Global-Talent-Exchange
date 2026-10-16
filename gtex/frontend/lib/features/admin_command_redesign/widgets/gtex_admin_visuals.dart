import 'package:flutter/material.dart';

import '../models/gtex_admin_command_models.dart';

Color gtexAdminSeverityColor(GtexAdminSeverity severity) {
  switch (severity) {
    case GtexAdminSeverity.calm:
      return const Color(0xFF2DFF87);
    case GtexAdminSeverity.watch:
      return const Color(0xFFFFD166);
    case GtexAdminSeverity.warning:
      return const Color(0xFFFF8A3D);
    case GtexAdminSeverity.critical:
      return const Color(0xFFFF4D6D);
  }
}

class GtexAdminPanel extends StatelessWidget {
  const GtexAdminPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(18),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: const Color(0xFF0E1624),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(.08)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.24),
            blurRadius: 28,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: child,
    );
  }
}

class GtexAdminSectionHeader extends StatelessWidget {
  const GtexAdminSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
  });

  final String title;
  final String? subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
              if (subtitle != null) ...[
                const SizedBox(height: 4),
                Text(subtitle!, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.white70)),
              ],
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class GtexAdminStatusPill extends StatelessWidget {
  const GtexAdminStatusPill({
    super.key,
    required this.label,
    this.severity = GtexAdminSeverity.calm,
  });

  final String label;
  final GtexAdminSeverity severity;

  @override
  Widget build(BuildContext context) {
    final color = gtexAdminSeverityColor(severity);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withOpacity(.35)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 12),
      ),
    );
  }
}

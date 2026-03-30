import 'package:flutter/material.dart';

import '../../widgets/gte_shell_theme.dart';

class SectionHeading extends StatelessWidget {
  const SectionHeading({
    super.key,
    required this.title,
    required this.subtitle,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = GteShellTheme.definitionOf(context);
    final tokens = GteShellTheme.tokensOf(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'GTEX SURFACE',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: theme.primaryColor,
                  letterSpacing: 1.2,
                ),
              ),
              SizedBox(height: tokens.spaceXs),
              Text(title, style: Theme.of(context).textTheme.displaySmall),
              SizedBox(height: tokens.spaceXs),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 920),
                child: Text(
                  subtitle,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) ...<Widget>[
          SizedBox(width: tokens.spaceMd),
          trailing!,
        ],
      ],
    );
  }
}

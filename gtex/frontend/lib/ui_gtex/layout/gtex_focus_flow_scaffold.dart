import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexFocusFlowScaffold extends StatelessWidget {
  const GtexFocusFlowScaffold({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.leading,
    this.footer,
    this.maxWidth = 760,
    this.accent = GtexColors.pitch,
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final Widget? leading;
  final Widget? footer;
  final double maxWidth;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[GtexColors.midnight, GtexColors.stadiumBlack],
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(GtexSpacing.xl),
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxWidth),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    if (leading != null) leading!,
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                          width: 5,
                          height: 58,
                          decoration: BoxDecoration(
                            color: accent,
                            borderRadius: BorderRadius.circular(
                              GtexSpacing.radiusPill,
                            ),
                          ),
                        ),
                        const SizedBox(width: GtexSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                title,
                                style: Theme.of(
                                  context,
                                ).textTheme.headlineMedium?.copyWith(
                                  color: GtexColors.text,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              if (subtitle != null) ...<Widget>[
                                const SizedBox(height: GtexSpacing.xs),
                                Text(
                                  subtitle!,
                                  style: Theme.of(
                                    context,
                                  ).textTheme.bodyLarge?.copyWith(
                                    color: GtexColors.textSecondary,
                                    height: 1.45,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: GtexSpacing.xl),
                    Container(
                      padding: const EdgeInsets.all(GtexSpacing.xl),
                      decoration: BoxDecoration(
                        color: GtexColors.panel.withValues(alpha: 0.88),
                        borderRadius: BorderRadius.circular(
                          GtexSpacing.radiusXl,
                        ),
                        border: Border.all(
                          color: GtexColors.line.withValues(alpha: 0.8),
                        ),
                        boxShadow: <BoxShadow>[
                          GtexColors.glow(accent, opacity: 0.12),
                        ],
                      ),
                      child: child,
                    ),
                    if (footer != null) ...<Widget>[
                      const SizedBox(height: GtexSpacing.md),
                      footer!,
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

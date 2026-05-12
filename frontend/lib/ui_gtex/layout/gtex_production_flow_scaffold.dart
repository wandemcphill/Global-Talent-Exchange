import 'package:flutter/material.dart';

import '../components/gtex_status_chip.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexProductionFlowScaffold extends StatelessWidget {
  const GtexProductionFlowScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.actions = const <Widget>[],
    this.floatingActionButton,
    this.icon = Icons.dashboard_outlined,
    this.accent = GtexColors.pitch,
    this.statusLabel,
    this.appBarTitle,
    this.header,
    this.padding = const EdgeInsets.fromLTRB(
      GtexSpacing.lg,
      GtexSpacing.sm,
      GtexSpacing.lg,
      GtexSpacing.md,
    ),
  });

  final String title;
  final String subtitle;
  final Widget child;
  final List<Widget> actions;
  final Widget? floatingActionButton;
  final IconData icon;
  final Color accent;
  final String? statusLabel;
  final String? appBarTitle;
  final Widget? header;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.stadiumBlack,
      appBar: AppBar(
        backgroundColor: GtexColors.stadiumBlack,
        surfaceTintColor: Colors.transparent,
        foregroundColor: GtexColors.text,
        title: Text(appBarTitle ?? statusLabel ?? title),
        actions: actions,
      ),
      floatingActionButton: floatingActionButton,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[GtexColors.midnight, GtexColors.stadiumBlack],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Padding(
              padding: padding,
              child:
                  header ??
                  _ProductionHeader(
                    title: title,
                    subtitle: subtitle,
                    icon: icon,
                    accent: accent,
                    statusLabel: statusLabel,
                  ),
            ),
            Expanded(child: child),
          ],
        ),
      ),
    );
  }
}

class _ProductionHeader extends StatelessWidget {
  const _ProductionHeader({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.statusLabel,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final String? statusLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      decoration: BoxDecoration(
        gradient: GtexColors.panelGlow(accent: accent),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: accent.withValues(alpha: 0.34)),
        boxShadow: <BoxShadow>[GtexColors.glow(accent, opacity: 0.11)],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(color: accent.withValues(alpha: 0.42)),
            ),
            child: Icon(icon, color: accent),
          ),
          const SizedBox(width: GtexSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (statusLabel != null) ...<Widget>[
                  GtexStatusChip(
                    label: statusLabel!,
                    icon: Icons.verified_user_outlined,
                    color: accent,
                    compact: true,
                  ),
                  const SizedBox(height: GtexSpacing.xs),
                ],
                Text(
                  title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GtexColors.textSecondary,
                    height: 1.42,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

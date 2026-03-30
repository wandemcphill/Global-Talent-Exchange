import 'package:flutter/material.dart';

import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_surface_panel.dart';

class GtexActionDialog extends StatelessWidget {
  const GtexActionDialog({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.content,
    this.actions = const <Widget>[],
    this.leadingIcon = Icons.tune_rounded,
    this.accentColor,
    this.maxWidth = 620,
  });

  final String eyebrow;
  final String title;
  final String description;
  final Widget content;
  final List<Widget> actions;
  final IconData leadingIcon;
  final Color? accentColor;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final EdgeInsets viewInsets = MediaQuery.of(context).viewInsets;
    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      insetPadding: EdgeInsets.fromLTRB(
        tokens.spaceLg,
        tokens.spaceLg,
        tokens.spaceLg,
        tokens.spaceLg + viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: _GtexActionSurface(
            eyebrow: eyebrow,
            title: title,
            description: description,
            content: content,
            actions: actions,
            leadingIcon: leadingIcon,
            accentColor: accentColor,
          ),
        ),
      ),
    );
  }
}

class GtexActionSheetFrame extends StatelessWidget {
  const GtexActionSheetFrame({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.content,
    this.actions = const <Widget>[],
    this.leadingIcon = Icons.insights_rounded,
    this.accentColor,
    this.maxWidth = 760,
  });

  final String eyebrow;
  final String title;
  final String description;
  final Widget content;
  final List<Widget> actions;
  final IconData leadingIcon;
  final Color? accentColor;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final EdgeInsets viewInsets = MediaQuery.of(context).viewInsets;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          tokens.spaceLg,
          tokens.spaceMd,
          tokens.spaceLg,
          tokens.spaceLg + viewInsets.bottom,
        ),
        child: Align(
          alignment: Alignment.bottomCenter,
          child: SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: maxWidth),
              child: _GtexActionSurface(
                eyebrow: eyebrow,
                title: title,
                description: description,
                content: content,
                actions: actions,
                leadingIcon: leadingIcon,
                accentColor: accentColor,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GtexActionSurface extends StatelessWidget {
  const _GtexActionSurface({
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.content,
    required this.actions,
    required this.leadingIcon,
    required this.accentColor,
  });

  final String eyebrow;
  final String title;
  final String description;
  final Widget content;
  final List<Widget> actions;
  final IconData leadingIcon;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    final Color accent = accentColor ?? visuals.heroAccent;
    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      padding: EdgeInsets.all(tokens.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(tokens.radiusMedium),
                  border: Border.all(color: accent.withValues(alpha: 0.24)),
                ),
                child: Icon(leadingIcon, color: accent),
              ),
              SizedBox(width: tokens.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      eyebrow,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: accent,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: tokens.spaceXs),
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    SizedBox(height: tokens.spaceXs),
                    Text(
                      description,
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
                    ),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: tokens.spaceLg),
          content,
          if (actions.isNotEmpty) ...<Widget>[
            SizedBox(height: tokens.spaceLg),
            Align(
              alignment: Alignment.centerRight,
              child: Wrap(
                spacing: tokens.spaceSm,
                runSpacing: tokens.spaceSm,
                alignment: WrapAlignment.end,
                children: actions,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

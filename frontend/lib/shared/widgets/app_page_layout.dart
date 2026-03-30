import 'package:flutter/material.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_surface_panel.dart';
import 'section_heading.dart';

class AppPageLayout extends StatelessWidget {
  const AppPageLayout({
    super.key,
    required this.title,
    required this.subtitle,
    required this.children,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final List<Widget> children;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double horizontalPadding =
            constraints.maxWidth >= AppBreakpoints.medium
                ? tokens.spaceLg
                : tokens.spaceMd;
        final double bottomPadding =
            MediaQuery.viewPaddingOf(context).bottom + 112;

        final List<Widget> content = <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.definitionOf(context).primaryColor,
            padding: EdgeInsets.all(tokens.spaceLg),
            child: SectionHeading(
              title: title,
              subtitle: subtitle,
              trailing: trailing,
            ),
          ),
        ];

        for (final Widget child in children) {
          content
            ..add(SizedBox(height: tokens.spaceLg))
            ..add(child);
        }

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1500),
            child: ListView(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                tokens.spaceLg,
                horizontalPadding,
                bottomPadding,
              ),
              children: content,
            ),
          ),
        );
      },
    );
  }
}

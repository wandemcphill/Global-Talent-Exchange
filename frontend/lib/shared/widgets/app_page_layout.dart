import 'package:flutter/material.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
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
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double horizontalPadding =
            constraints.maxWidth >= AppBreakpoints.medium
                ? spacingLG
                : spacingMD;
        final double bottomPadding =
            MediaQuery.viewPaddingOf(context).bottom + 96;

        final List<Widget> content = <Widget>[
          SectionHeading(title: title, subtitle: subtitle, trailing: trailing),
        ];

        for (final Widget child in children) {
          content
            ..add(const SizedBox(height: spacingLG))
            ..add(child);
        }

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: ListView(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                spacingLG,
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

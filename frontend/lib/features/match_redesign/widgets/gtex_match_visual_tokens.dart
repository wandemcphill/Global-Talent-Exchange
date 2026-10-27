import 'package:flutter/material.dart';

import '../../../ui_gtex/theme/gtex_colors.dart';

class GtexMatchVisualTokens {
  const GtexMatchVisualTokens._();

  static const Color surfaceBase = GtexNavyColors.bgBase;
  static const Color surfaceRaised = GtexNavyColors.bgRaised;
  static const Color surfaceOverlay = GtexNavyColors.bgOverlay;
  static const Color surfaceHover = GtexNavyColors.bgOverlay;
  static const Color border = GtexNavyColors.lineSubtle;
  static const Color borderStrong = GtexNavyColors.lineStrong;
  static const Color textPrimary = GtexNavyColors.textPrimary;
  static const Color textSecondary = GtexNavyColors.textSecondary;
  static const Color textTertiary = GtexNavyColors.textTertiary;
  static const Color live = GtexNavyColors.success;
  static const Color amber = GtexNavyColors.warning;
  static const Color red = GtexNavyColors.danger;
  static const Color blue = GtexNavyColors.info;
  static const Color regen = GtexNavyColors.gold300;

  static BoxDecoration panelDecoration({
    Color? borderColor,
    Color? background,
    double radius = 8,
  }) {
    return BoxDecoration(
      color: background ?? surfaceRaised,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: borderColor ?? border),
      boxShadow: const [
        BoxShadow(
          color: GtexNavyColors.scrim,
          blurRadius: 12,
          offset: Offset(0, 6),
        ),
      ],
    );
  }

  static TextStyle get labelStyle => const TextStyle(
    color: textSecondary,
    fontSize: 11,
    fontWeight: FontWeight.w800,
    letterSpacing: .8,
  );

  static TextStyle get dataStyle => const TextStyle(
    color: textPrimary,
    fontFamily: 'JetBrains Mono',
    fontWeight: FontWeight.w800,
  );
}

class GtexMatchEmptyFeed extends StatelessWidget {
  const GtexMatchEmptyFeed({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.sensors_off_rounded,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    // These panels are dropped into tightly-bounded slots (a ~100px timeline
    // rail, the pitch square). At full size the icon-plus-two-paragraphs
    // layout overflowed, so the empty state itself rendered broken. Adapt to
    // the box instead: shed the icon when short, and always allow scrolling
    // as a last resort.
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool bounded = constraints.hasBoundedHeight;
        final double available =
            bounded ? constraints.maxHeight : double.infinity;
        final bool compact = bounded && available < 150;
        final double outerPad = compact ? 8 : 18;
        final double innerPad = compact ? 10 : 16;

        final Widget content = Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (!compact) ...<Widget>[
              Icon(icon, color: GtexMatchVisualTokens.textSecondary, size: 28),
              const SizedBox(height: 10),
            ],
            Text(
              title.toUpperCase(),
              textAlign: TextAlign.center,
              maxLines: compact ? 1 : 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: GtexMatchVisualTokens.textPrimary,
                fontWeight: FontWeight.w900,
                fontSize: 12,
                letterSpacing: .8,
              ),
            ),
            SizedBox(height: compact ? 4 : 6),
            Text(
              message,
              textAlign: TextAlign.center,
              maxLines: compact ? 2 : 4,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: compact ? 11 : null,
                height: 1.35,
              ),
            ),
          ],
        );

        return Center(
          child: Padding(
            padding: EdgeInsets.all(outerPad),
            child: Container(
              width: double.infinity,
              padding: EdgeInsets.all(innerPad),
              decoration: GtexMatchVisualTokens.panelDecoration(
                background: GtexMatchVisualTokens.surfaceOverlay,
                borderColor: GtexMatchVisualTokens.borderStrong,
              ),
              child:
                  bounded
                      ? SingleChildScrollView(
                        physics: const ClampingScrollPhysics(),
                        child: content,
                      )
                      : content,
            ),
          ),
        );
      },
    );
  }
}

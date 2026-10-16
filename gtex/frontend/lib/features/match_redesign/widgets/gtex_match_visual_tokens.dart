import 'package:flutter/material.dart';

class GtexMatchVisualTokens {
  const GtexMatchVisualTokens._();

  static const Color surfaceBase = Color(0xFF0A0C0F);
  static const Color surfaceRaised = Color(0xFF111418);
  static const Color surfaceOverlay = Color(0xFF181C22);
  static const Color surfaceHover = Color(0xFF1E2530);
  static const Color border = Color(0xFF252D38);
  static const Color borderStrong = Color(0xFF2E3A48);
  static const Color textPrimary = Color(0xFFE8EDF4);
  static const Color textSecondary = Color(0xFF8A97A8);
  static const Color textTertiary = Color(0xFF4D5D6E);
  static const Color live = Color(0xFF00E87A);
  static const Color amber = Color(0xFFFFB800);
  static const Color red = Color(0xFFFF3D3D);
  static const Color blue = Color(0xFF2F80ED);
  static const Color regen = Color(0xFF9B5FFF);

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
          color: Color(0x40000000),
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

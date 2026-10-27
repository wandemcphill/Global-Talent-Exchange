import 'package:flutter/material.dart';

import '../../../ui_gtex/theme/gtex_colors.dart';

const Color kNavyBase = GtexNavyColors.bgBase; // #0B1626
const Color kNavyRaised = GtexNavyColors.bgRaised; // #13233A
const Color kNavyOverlay = GtexNavyColors.bgOverlay; // #1A2E4A
const Color kNavyInset = GtexNavyColors.bgInset; // #081120
const Color kNavyLine = GtexNavyColors.lineSubtle; // #22385A
const Color kNavyLineStrong = GtexNavyColors.lineStrong; // #2F4C75

const Color kGoldPrimary = GtexNavyColors.gold500; // #D4AF37
const Color kGoldLight = GtexNavyColors.gold300; // #E8C766
const Color kPitchGreen = Color(0xFF22C55E);
const Color kPitchGreenBright = Color(0xFF36E38A);
const Color kSkyBlue = Color(0xFF38BDF8);

const Color kTextPrimary = GtexNavyColors.textPrimary; // #F2F4F8
const Color kTextSecondary = GtexNavyColors.textSecondary; // #9AA7BD
const Color kTextTertiary = GtexNavyColors.textTertiary; // #6B7A93

const String kFontCondensed = 'BarlowCondensed';
const String kFontMono = 'DMMono';

class GtexSectionHeader extends StatelessWidget {
  const GtexSectionHeader({
    super.key,
    required this.eyebrow,
    required this.title,
    this.subtitle,
    this.accentColor = kPitchGreenBright,
    this.crossAxisAlignment = CrossAxisAlignment.start,
  });

  final String eyebrow;
  final String title;
  final String? subtitle;
  final Color accentColor;
  final CrossAxisAlignment crossAxisAlignment;

  @override
  Widget build(BuildContext context) {
    final bool isNarrow = MediaQuery.sizeOf(context).width < 760;
    return Column(
      crossAxisAlignment: crossAxisAlignment,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: accentColor,
                shape: BoxShape.circle,
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: accentColor.withValues(alpha: 0.6),
                    blurRadius: 8,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Flexible(
              child: Text(
                eyebrow.toUpperCase(),
                style: TextStyle(
                  color: accentColor,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2.2,
                  fontFamily: kFontCondensed,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Text(
          title,
          style: TextStyle(
            color: kTextPrimary,
            fontSize: isNarrow ? 30 : 48,
            fontWeight: FontWeight.w900,
            letterSpacing: -1,
            height: 1.05,
            fontFamily: kFontCondensed,
          ),
        ),
        if (subtitle != null) ...<Widget>[
          const SizedBox(height: 14),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Text(
              subtitle!,
              style: const TextStyle(
                color: kTextSecondary,
                fontSize: 15,
                height: 1.5,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class GtexGlowButton extends StatefulWidget {
  const GtexGlowButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.large = false,
    this.glowColor = kGoldPrimary,
    this.textColor = const Color(0xFF0B1626),
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool large;
  final Color glowColor;
  final Color textColor;

  @override
  State<GtexGlowButton> createState() => _GtexGlowButtonState();
}

class _GtexGlowButtonState extends State<GtexGlowButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: EdgeInsets.symmetric(
            horizontal: widget.large ? 24 : 16,
            vertical: widget.large ? 14 : 10,
          ),
          decoration: BoxDecoration(
            color: _hovered ? widget.glowColor : widget.glowColor.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(10),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: widget.glowColor.withValues(alpha: _hovered ? 0.5 : 0.25),
                blurRadius: _hovered ? 20 : 12,
                spreadRadius: _hovered ? 2 : 0,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              if (widget.icon != null) ...<Widget>[
                Icon(widget.icon, size: widget.large ? 18 : 15, color: widget.textColor),
                const SizedBox(width: 8),
              ],
              Flexible(
                child: Text(
                  widget.label,
                  textAlign: TextAlign.center,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: widget.textColor,
                    fontSize: widget.large ? 15 : 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class GtexGhostButton extends StatefulWidget {
  const GtexGhostButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.borderColor = kNavyLineStrong,
    this.textColor = kTextPrimary,
    this.large = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final Color borderColor;
  final Color textColor;
  final bool large;

  @override
  State<GtexGhostButton> createState() => _GtexGhostButtonState();
}

class _GtexGhostButtonState extends State<GtexGhostButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: EdgeInsets.symmetric(
            horizontal: widget.large ? 20 : 14,
            vertical: widget.large ? 14 : 10,
          ),
          decoration: BoxDecoration(
            color: _hovered ? kNavyOverlay : kNavyRaised.withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: _hovered ? kGoldPrimary : widget.borderColor,
              width: 1.2,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              if (widget.icon != null) ...<Widget>[
                Icon(widget.icon, size: widget.large ? 17 : 14, color: widget.textColor),
                const SizedBox(width: 6),
              ],
              Flexible(
                child: Text(
                  widget.label,
                  textAlign: TextAlign.center,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: widget.textColor,
                    fontSize: widget.large ? 14 : 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.3,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class GtexCardPanel extends StatelessWidget {
  const GtexCardPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(22),
    this.borderColor = kNavyLine,
    this.backgroundColor = kNavyRaised,
    this.borderRadius = 16,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color borderColor;
  final Color backgroundColor;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(color: borderColor, width: 1),
        boxShadow: const <BoxShadow>[
          BoxShadow(
            color: Color(0x33000000),
            blurRadius: 16,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }
}

class GtexTagPill extends StatelessWidget {
  const GtexTagPill({
    super.key,
    required this.label,
    required this.color,
    this.icon,
  });

  final String label;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 5),
          ],
          Flexible(
            child: Text(
              label.toUpperCase(),
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w800,
                letterSpacing: 1,
                fontFamily: kFontCondensed,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../ui_gtex/theme/gtex_colors.dart';
import '../ui_gtex/theme/gtex_spacing.dart';

class GteSurfacePanel extends StatefulWidget {
  const GteSurfacePanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.emphasized = false,
    this.onTap,
    this.accentColor,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final bool emphasized;
  final VoidCallback? onTap;
  final Color? accentColor;

  @override
  State<GteSurfacePanel> createState() => _GteSurfacePanelState();
}

class _GteSurfacePanelState extends State<GteSurfacePanel> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final Color glow =
        widget.accentColor ??
        (widget.emphasized ? GtexColors.pitch : GtexColors.cyan);
    final BorderRadius radius = BorderRadius.circular(GtexSpacing.radiusLg);
    final Widget content = Container(
      constraints: const BoxConstraints(minWidth: 1, minHeight: 1),
      padding: widget.padding,
      decoration: BoxDecoration(
        borderRadius: radius,
        border: Border.all(
          color: _hovered
              ? glow.withValues(alpha: 0.62)
              : GtexColors.line.withValues(alpha: 0.82),
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color.alphaBlend(
              glow.withValues(alpha: widget.emphasized ? 0.13 : 0.06),
              widget.emphasized ? GtexColors.panelStrong : GtexColors.panel,
            ),
            GtexColors.panel.withValues(alpha: 0.96),
            GtexColors.stadiumBlack.withValues(alpha: 0.98),
          ],
          stops: const <double>[0, 0.72, 1],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.34),
            blurRadius: 28,
            offset: const Offset(0, 16),
          ),
          BoxShadow(
            color: glow.withValues(
              alpha: _hovered ? 0.14 : (widget.emphasized ? 0.08 : 0.035),
            ),
            blurRadius: _hovered ? 30 : 18,
            spreadRadius: -8,
          ),
        ],
      ),
      child: Stack(
        children: <Widget>[
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 3,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(GtexSpacing.radiusLg),
                ),
                gradient: LinearGradient(
                  colors: <Color>[
                    glow.withValues(alpha: _hovered ? 1 : 0.95),
                    GtexColors.gold.withValues(alpha: 0.34),
                    GtexColors.line.withValues(alpha: 0.18),
                  ],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: AnimatedOpacity(
                duration: const Duration(milliseconds: 240),
                opacity: _hovered ? 1 : 0,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: radius,
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: <Color>[
                        Colors.white.withValues(alpha: 0.055),
                        Colors.transparent,
                        glow.withValues(alpha: 0.05),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          Material(type: MaterialType.transparency, child: widget.child),
        ],
      ),
    );

    final Widget animatedBody = AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      transform: Matrix4.identity()
        ..translate(0.0, _hovered ? -4.0 : 0.0)
        ..scale(_hovered ? 1.006 : 1.0),
      transformAlignment: Alignment.center,
      child: content,
    );

    if (widget.onTap == null) {
      return MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: Material(color: Colors.transparent, child: animatedBody),
      );
    }

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: radius,
          onTap: widget.onTap,
          child: animatedBody,
        ),
      ),
    );
  }
}

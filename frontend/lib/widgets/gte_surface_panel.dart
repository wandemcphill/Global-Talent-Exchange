import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';

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
    final tokens = GteShellTheme.tokensOf(context);
    final visuals = GteShellTheme.visualsOf(context);
    final Color glow =
        widget.accentColor ??
        (widget.emphasized ? tokens.accent : tokens.accentWarm);
    final BorderRadius radius = BorderRadius.circular(tokens.radiusLarge);
    final Widget content = Container(
      constraints: const BoxConstraints(minWidth: 1, minHeight: 1),
      padding: widget.padding,
      decoration: BoxDecoration(
        borderRadius: radius,
        border: Border.all(
          color: (visuals.glass ? visuals.shellBorder : tokens.stroke)
              .withValues(alpha: _hovered ? 1 : 0.92),
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color.alphaBlend(
              glow.withValues(alpha: widget.emphasized ? 0.12 : 0.05),
              (widget.emphasized ? tokens.panelElevated : tokens.panelStrong)
                  .withValues(alpha: visuals.surfaceOpacity),
            ),
            tokens.panel.withValues(alpha: visuals.surfaceOpacity),
            tokens.surfaceHighlight.withValues(
              alpha: widget.emphasized ? 0.06 : 0.03,
            ),
          ],
          stops: const <double>[0, 0.65, 1],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: tokens.shadow.withValues(alpha: 0.34),
            blurRadius: 34,
            offset: const Offset(0, 18),
          ),
          BoxShadow(
            color: glow.withValues(
              alpha: _hovered ? 0.16 : (widget.emphasized ? 0.08 : 0.04),
            ),
            blurRadius: _hovered ? 34 : 24,
            spreadRadius: _hovered ? 2 : 1,
          ),
        ],
      ),
      child: Stack(
        children: <Widget>[
          Positioned(
            top: -54,
            right: -30,
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: <Color>[
                      glow.withValues(alpha: widget.emphasized ? 0.24 : 0.16),
                      glow.withValues(alpha: 0),
                    ],
                  ),
                ),
                child: const SizedBox(width: 180, height: 180),
              ),
            ),
          ),
          Positioned(
            bottom: -26,
            left: -12,
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(tokens.radiusLarge + 14),
                  gradient: LinearGradient(
                    colors: <Color>[
                      tokens.surfaceHighlight.withValues(alpha: 0.08),
                      tokens.surfaceHighlight.withValues(alpha: 0),
                    ],
                  ),
                ),
                child: const SizedBox(width: 160, height: 96),
              ),
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 3,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(tokens.radiusLarge),
                ),
                gradient: LinearGradient(
                  colors: <Color>[
                    glow.withValues(alpha: _hovered ? 1 : 0.95),
                    tokens.surfaceHighlight.withValues(alpha: 0.16),
                    tokens.accentWarm.withValues(alpha: 0.35),
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
                        Colors.white.withValues(alpha: 0.08),
                        Colors.transparent,
                        glow.withValues(alpha: 0.06),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            top: 22,
            right: 22,
            child: IgnorePointer(
              child: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: tokens.surfaceHighlight.withValues(alpha: 0.08),
                  ),
                ),
              ),
            ),
          ),
          widget.child,
        ],
      ),
    );

    final Widget layeredContent =
        visuals.glass
            ? ClipRRect(
              borderRadius: radius,
              child: BackdropFilter(
                filter: gtePanelBlur(visuals.surfaceBlurSigma),
                child: content,
              ),
            )
            : content;

    final Widget animatedBody = AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      transform:
          Matrix4.identity()
            ..translate(0.0, _hovered ? -4.0 : 0.0)
            ..scale(_hovered ? 1.006 : 1.0),
      transformAlignment: Alignment.center,
      child: layeredContent,
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

import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/jersey_variant_dto.dart';
import 'identity_color_utils.dart';

class JerseyPreviewCard extends StatelessWidget {
  const JerseyPreviewCard({
    super.key,
    required this.variant,
    this.onTap,
    this.selected = false,
    this.compact = false,
  });

  final JerseyVariantDto variant;
  final VoidCallback? onTap;
  final bool selected;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onTap,
      emphasized: selected,
      padding: EdgeInsets.all(compact ? 14 : 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(
                variant.label,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const Spacer(),
              if (selected)
                const Icon(
                  Icons.check_circle_rounded,
                  color: GteShellTheme.accent,
                  size: 18,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Center(
            child: _ShirtPreview(
              variant: variant,
              size: compact ? 92 : 132,
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _SwatchPill(label: 'Body', colorHex: variant.primaryColor),
              _SwatchPill(label: 'Trim', colorHex: variant.secondaryColor),
              _SwatchPill(label: 'Accent', colorHex: variant.accentColor),
            ],
          ),
          if (!compact) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              '${_patternLabel(variant.patternType)} pattern | ${_collarLabel(variant.collarStyle)} collar | ${_sleeveLabel(variant.sleeveStyle)} sleeves',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }
}

class _ShirtPreview extends StatelessWidget {
  const _ShirtPreview({
    required this.variant,
    required this.size,
  });

  final JerseyVariantDto variant;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        SizedBox(
          width: size,
          height: size * 1.05,
          child: Stack(
            clipBehavior: Clip.none,
            children: <Widget>[
              ClipPath(
                clipper: _ShirtClipper(),
                child: Container(
                  decoration: BoxDecoration(
                    color: identityColorFromHex(variant.primaryColor),
                  ),
                  child: Stack(
                    fit: StackFit.expand,
                    children: <Widget>[
                      _PatternOverlay(variant: variant),
                      Align(
                        alignment: Alignment.topCenter,
                        child: Container(
                          width: size * 0.3,
                          height: size * 0.16,
                          decoration: BoxDecoration(
                            color: identityColorFromHex(variant.secondaryColor),
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                      Align(
                        alignment: Alignment.topLeft,
                        child: Padding(
                          padding: EdgeInsets.only(
                            left: size * 0.19,
                            top: size * 0.22,
                          ),
                          child: Container(
                            width: size * 0.13,
                            height: size * 0.13,
                            decoration: BoxDecoration(
                              color: identityColorFromHex(variant.accentColor),
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.5),
                              ),
                            ),
                          ),
                        ),
                      ),
                      Align(
                        alignment: Alignment.center,
                        child: Text(
                          variant.frontText,
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(
                                color: identityReadableOn(
                                  identityColorFromHex(variant.primaryColor),
                                ),
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.4,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Container(
          width: size * 0.44,
          height: size * 0.15,
          decoration: BoxDecoration(
            color: identityColorFromHex(variant.shortsColor),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.12),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List<Widget>.generate(
            2,
            (int index) => Container(
              margin: const EdgeInsets.symmetric(horizontal: 5),
              width: size * 0.11,
              height: size * 0.24,
              decoration: BoxDecoration(
                color: identityColorFromHex(variant.socksColor),
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _PatternOverlay extends StatelessWidget {
  const _PatternOverlay({
    required this.variant,
  });

  final JerseyVariantDto variant;

  @override
  Widget build(BuildContext context) {
    final Color secondary = identityColorFromHex(variant.secondaryColor);
    switch (variant.patternType) {
      case PatternType.solid:
        return const SizedBox.shrink();
      case PatternType.stripes:
        return Row(
          children: List<Widget>.generate(
            5,
            (int index) => Expanded(
              child: Container(
                color: index.isEven
                    ? secondary.withValues(alpha: 0.25)
                    : Colors.transparent,
              ),
            ),
          ),
        );
      case PatternType.hoops:
        return Column(
          children: List<Widget>.generate(
            5,
            (int index) => Expanded(
              child: Container(
                color: index.isEven
                    ? secondary.withValues(alpha: 0.22)
                    : Colors.transparent,
              ),
            ),
          ),
        );
      case PatternType.sash:
        return Transform.rotate(
          angle: -0.55,
          child: Align(
            alignment: Alignment.center,
            child: Container(
              width: 30,
              height: 220,
              color: secondary.withValues(alpha: 0.28),
            ),
          ),
        );
      case PatternType.chevron:
        return Stack(
          children: <Widget>[
            Positioned.fill(
              child: Align(
                alignment: Alignment.topCenter,
                child: Container(
                  margin: const EdgeInsets.only(top: 16),
                  width: 84,
                  height: 18,
                  decoration: BoxDecoration(
                    border: Border(
                      left: BorderSide(
                        color: secondary.withValues(alpha: 0.32),
                        width: 8,
                      ),
                      right: BorderSide(
                        color: secondary.withValues(alpha: 0.32),
                        width: 8,
                      ),
                    ),
                  ),
                  transform: Matrix4.rotationZ(0.55),
                ),
              ),
            ),
          ],
        );
      case PatternType.gradient:
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[
                secondary.withValues(alpha: 0.08),
                secondary.withValues(alpha: 0.34),
              ],
            ),
          ),
        );
    }
  }
}

class _SwatchPill extends StatelessWidget {
  const _SwatchPill({
    required this.label,
    required this.colorHex,
  });

  final String label;
  final String colorHex;

  @override
  Widget build(BuildContext context) {
    final Color color = identityColorFromHex(colorHex);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.2),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GteShellTheme.textPrimary,
                ),
          ),
        ],
      ),
    );
  }
}

class _ShirtClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final Path path = Path()
      ..moveTo(size.width * 0.22, size.height * 0.06)
      ..lineTo(size.width * 0.08, size.height * 0.22)
      ..lineTo(size.width * 0.18, size.height * 0.4)
      ..lineTo(size.width * 0.26, size.height * 0.3)
      ..lineTo(size.width * 0.26, size.height)
      ..lineTo(size.width * 0.74, size.height)
      ..lineTo(size.width * 0.74, size.height * 0.3)
      ..lineTo(size.width * 0.82, size.height * 0.4)
      ..lineTo(size.width * 0.92, size.height * 0.22)
      ..lineTo(size.width * 0.78, size.height * 0.06)
      ..quadraticBezierTo(
        size.width * 0.65,
        size.height * 0.16,
        size.width * 0.5,
        size.height * 0.14,
      )
      ..quadraticBezierTo(
        size.width * 0.35,
        size.height * 0.16,
        size.width * 0.22,
        size.height * 0.06,
      )
      ..close();
    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}

String _patternLabel(PatternType type) {
  switch (type) {
    case PatternType.solid:
      return 'Solid';
    case PatternType.stripes:
      return 'Stripes';
    case PatternType.hoops:
      return 'Hoops';
    case PatternType.sash:
      return 'Sash';
    case PatternType.chevron:
      return 'Chevron';
    case PatternType.gradient:
      return 'Gradient';
  }
}

String _collarLabel(CollarStyle style) {
  switch (style) {
    case CollarStyle.crew:
      return 'Crew';
    case CollarStyle.vNeck:
      return 'V-neck';
    case CollarStyle.polo:
      return 'Polo';
    case CollarStyle.wrap:
      return 'Wrap';
  }
}

String _sleeveLabel(SleeveStyle style) {
  switch (style) {
    case SleeveStyle.short:
      return 'Short';
    case SleeveStyle.long:
      return 'Long';
    case SleeveStyle.raglan:
      return 'Raglan';
    case SleeveStyle.cuffed:
      return 'Cuffed';
  }
}

import 'package:flutter/material.dart';

import '../theme/gtex_spacing.dart';
import 'gtex_regen_portrait.dart';

/// Supported portrait sizes in logical pixels (Document F8).
enum GtexPortraitSize {
  xs32(32),
  sm48(48),
  md72(72),
  lg120(120),
  xl240(240);

  const GtexPortraitSize(this.dimension);
  final double dimension;
}

/// Supported portrait aspect ratios (Document F8).
enum GtexPortraitAspect {
  square(1.0),
  hero4x5(0.8);

  const GtexPortraitAspect(this.aspectRatio);
  final double aspectRatio;
}

/// Canonical portrait component (Master Plan Document F8 & F9).
///
/// Always delegates URL verification to [GtexRegenPortrait] policy and supplies
/// DPR-scaled `cacheWidth` and `cacheHeight` hints to prevent oversize decoded
/// bitmaps in squad and market lists.
class GtexPortrait extends StatelessWidget {
  const GtexPortrait({
    super.key,
    this.portraitUrl,
    required this.seed,
    required this.position,
    required this.nationalityCode,
    this.playerName,
    this.jerseyColor,
    this.size = GtexPortraitSize.sm48,
    this.aspect = GtexPortraitAspect.square,
    this.borderRadius,
  });

  final String? portraitUrl;
  final String seed;
  final String position;
  final String nationalityCode;
  final String? playerName;
  final Color? jerseyColor;
  final GtexPortraitSize size;
  final GtexPortraitAspect aspect;
  final double? borderRadius;

  @override
  Widget build(BuildContext context) {
    final double width = size.dimension;
    final double height =
        aspect == GtexPortraitAspect.square
            ? width
            : width / aspect.aspectRatio;
    final double dpr = MediaQuery.maybeDevicePixelRatioOf(context) ?? 1.0;
    final int cacheWidth = (width * dpr).round().clamp(32, 1024);
    final int cacheHeight = (height * dpr).round().clamp(32, 1280);
    final double effectiveRadius =
        borderRadius ??
        (width <= 48 ? GtexRadius.chip : GtexRadius.card);
    final String semanticsLabel =
        (playerName ?? '').trim().isNotEmpty
            ? 'Portrait of ${playerName!.trim()}'
            : 'Portrait of ${position.toUpperCase()} (${nationalityCode.toUpperCase()})';

    return Semantics(
      image: true,
      label: semanticsLabel,
      child: SizedBox(
        width: width,
        height: height,
        child: GtexRegenPortrait(
          portraitUrl: portraitUrl,
          seed: seed,
          position: position,
          nationalityCode: nationalityCode,
          jerseyColor: jerseyColor,
          borderRadius: effectiveRadius,
          aspectRatio: aspect.aspectRatio,
          cacheWidth: cacheWidth,
          cacheHeight: cacheHeight,
        ),
      ),
    );
  }
}

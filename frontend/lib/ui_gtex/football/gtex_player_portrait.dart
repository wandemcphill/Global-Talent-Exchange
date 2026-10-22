import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

/// A footballer's portrait: the real photograph when GTEX has one, and a
/// typographic identity plate when it does not.
///
/// The fallback is deliberately not a face. GTEX shows real newgen faces or
/// no face at all - a drawn silhouette reads as a stand-in for a person who
/// does not exist, which is exactly the impression an ownership product
/// cannot afford to give.
class GtexPlayerPortrait extends StatelessWidget {
  const GtexPlayerPortrait({
    super.key,
    required this.name,
    this.imageUrl,
    this.position,
    this.nationalityCode,
    this.accent = GtexColors.accentBlue,
    this.size = 96,
    this.width,
    this.height,
    this.borderRadius = GtexSpacing.radiusLg,
  });

  final String name;
  final String? imageUrl;
  final String? position;
  final String? nationalityCode;
  final Color accent;
  final double size;

  /// Optional non-square plate. When null, [size] is used for both axes.
  final double? width;
  final double? height;
  final double borderRadius;

  String get _initials {
    final List<String> parts = name
        .trim()
        .split(RegExp(r'[\s-]+'))
        .where((String part) => part.isNotEmpty)
        .toList(growable: false);
    if (parts.isEmpty) {
      return '?';
    }
    if (parts.length == 1) {
      return parts.first.characters.first.toUpperCase();
    }
    return '${parts.first.characters.first}'
            '${parts.last.characters.first}'
        .toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final String? url = imageUrl?.trim();
    final double plateWidth = width ?? size;
    final double plateHeight = height ?? size;
    final double typeScale = plateHeight < plateWidth ? plateHeight : plateWidth;
    final Widget plate = _IdentityPlate(
      initials: _initials,
      position: position,
      nationalityCode: nationalityCode,
      accent: accent,
      size: typeScale,
    );
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: SizedBox(
        width: plateWidth,
        height: plateHeight,
        child:
            url == null || url.isEmpty
                ? plate
                : Image.network(
                  url,
                  key: const Key('gtex-player-portrait-image'),
                  fit: BoxFit.cover,
                  width: plateWidth,
                  height: plateHeight,
                  gaplessPlayback: true,
                  filterQuality: FilterQuality.medium,
                  // While the photograph is in flight the plate would flash
                  // and then be replaced, so a neutral hold sits in for it.
                  loadingBuilder: (
                    BuildContext context,
                    Widget child,
                    ImageChunkEvent? progress,
                  ) {
                    if (progress == null) {
                      return child;
                    }
                    return const _PortraitLoadingPlate();
                  },
                  errorBuilder: (_, __, ___) => plate,
                ),
      ),
    );
  }
}

class _IdentityPlate extends StatelessWidget {
  const _IdentityPlate({
    required this.initials,
    required this.position,
    required this.nationalityCode,
    required this.accent,
    required this.size,
  });

  final String initials;
  final String? position;
  final String? nationalityCode;
  final Color accent;
  final double size;

  String _resolveSilhouetteAsset(String? pos) {
    final String p = (pos ?? '').trim().toUpperCase();
    if (p == 'GK') return 'assets/media/players/keeper.png';
    if (p == 'CB' || p == 'LB' || p == 'RB' || p == 'LWB' || p == 'RWB' || p == 'DEF') {
      return 'assets/media/players/defender.png';
    }
    if (p == 'CM' || p == 'CDM' || p == 'CAM' || p == 'LM' || p == 'RM' || p == 'MID') {
      return 'assets/media/players/midfielder.png';
    }
    if (p == 'ST' || p == 'CF' || p == 'LW' || p == 'RW' || p == 'FWD') {
      return 'assets/media/players/striker.png';
    }
    return 'assets/media/players/striker.png';
  }

  @override
  Widget build(BuildContext context) {
    final String? support = <String?>[
      position?.trim(),
      nationalityCode?.trim(),
    ].where((String? part) => part != null && part.isNotEmpty).join(' / ');
    final String silhouetteAsset = _resolveSilhouetteAsset(position);

    return Container(
      key: const Key('gtex-player-portrait-plate'),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            const Color(0xFF0D1522),
            accent.withValues(alpha: 0.22),
          ],
        ),
        border: Border.all(color: accent.withValues(alpha: 0.45)),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          // Position silhouette fallback art
          Opacity(
            opacity: 0.42,
            child: Image.asset(
              silhouetteAsset,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
          // Subtle radial dark gradient for typography contrast
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: <Color>[
                  Colors.transparent,
                  const Color(0xFF090E17).withValues(alpha: 0.85),
                ],
              ),
            ),
          ),
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  initials,
                  maxLines: 1,
                  style: TextStyle(
                    color: GtexColors.textPrimary,
                    fontFamily: 'BarlowCondensed',
                    fontSize: size * 0.38,
                    fontWeight: FontWeight.w900,
                    height: 1,
                    letterSpacing: 1,
                    shadows: const <Shadow>[
                      Shadow(
                        color: Colors.black,
                        blurRadius: 8,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                ),
                if (support != null && support.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 2),
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: GtexSpacing.xxs,
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.6),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: accent.withValues(alpha: 0.4), width: 0.8),
                      ),
                      child: Text(
                        support,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: accent,
                          fontFamily: 'Barlow',
                          fontSize: (size * 0.11).clamp(9, 13),
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.6,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PortraitLoadingPlate extends StatelessWidget {
  const _PortraitLoadingPlate();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(color: GtexColors.surfaceHover),
      child: Center(
        child: SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: GtexColors.textTertiary,
          ),
        ),
      ),
    );
  }
}

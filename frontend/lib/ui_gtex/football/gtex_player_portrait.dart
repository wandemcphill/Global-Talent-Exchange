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
    this.borderRadius = GtexSpacing.radiusLg,
  });

  final String name;
  final String? imageUrl;
  final String? position;
  final String? nationalityCode;
  final Color accent;
  final double size;
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
    final Widget plate = _IdentityPlate(
      initials: _initials,
      position: position,
      nationalityCode: nationalityCode,
      accent: accent,
      size: size,
    );
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: SizedBox(
        width: size,
        height: size,
        child:
            url == null || url.isEmpty
                ? plate
                : Image.network(
                  url,
                  key: const Key('gtex-player-portrait-image'),
                  fit: BoxFit.cover,
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

  @override
  Widget build(BuildContext context) {
    final String? support = <String?>[
      position?.trim(),
      nationalityCode?.trim(),
    ].where((String? part) => part != null && part.isNotEmpty).join(' / ');
    return Container(
      key: const Key('gtex-player-portrait-plate'),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.surfaceRaised,
            accent.withValues(alpha: 0.16),
          ],
        ),
        border: Border.all(color: accent.withValues(alpha: 0.42)),
      ),
      child: Center(
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
              ),
            ),
            if (support != null && support.isNotEmpty) ...<Widget>[
              const SizedBox(height: 2),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: GtexSpacing.xxs,
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
            ],
          ],
        ),
      ),
    );
  }
}

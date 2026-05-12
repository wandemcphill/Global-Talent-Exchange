import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';

class GtexRegenPortrait extends StatelessWidget {
  const GtexRegenPortrait({
    super.key,
    this.portraitUrl,
    required this.seed,
    required this.position,
    required this.nationalityCode,
    this.jerseyColor,
    this.borderRadius = 8,
  });

  final String? portraitUrl;
  final String seed;
  final String position;
  final String nationalityCode;
  final Color? jerseyColor;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    final String? resolvedUrl =
        (portraitUrl ?? '').trim().isEmpty
            ? null
            : _resolveMediaUrl(portraitUrl!.trim());
    final Widget pendingState = _PortraitPendingState(
      position: position,
      nationalityCode: nationalityCode,
      jerseyColor: jerseyColor,
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: AspectRatio(
        aspectRatio: 1,
        child:
            resolvedUrl == null || !_isApprovedRegenPortraitUrl(resolvedUrl)
                ? pendingState
                : Image.network(
                  resolvedUrl,
                  key: const Key('gtex-regen-bank-portrait'),
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => pendingState,
                ),
      ),
    );
  }

  bool _isApprovedRegenPortraitUrl(String url) {
    final String lowerPath =
        Uri.tryParse(url)?.path.toLowerCase() ?? url.toLowerCase();
    final bool isRaster =
        lowerPath.endsWith('.png') ||
        lowerPath.endsWith('.jpg') ||
        lowerPath.endsWith('.jpeg') ||
        lowerPath.endsWith('.webp');
    return isRaster &&
        lowerPath.contains(
          '/generated-media/regen_newgen_faces/script_skin_hair/',
        );
  }

  String _resolveMediaUrl(String url) {
    final Uri? parsed = Uri.tryParse(url);
    final String? generatedPath = _generatedMediaPath(parsed, url);
    if (generatedPath == null) return url;
    const String apiBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
    final String trimmedBase = apiBaseUrl.trim();
    if (trimmedBase.isEmpty) return url;
    final Uri? base = Uri.tryParse(trimmedBase);
    if (parsed != null &&
        parsed.hasScheme &&
        base != null &&
        parsed.host == base.host) {
      return url;
    }
    return '${trimmedBase.replaceFirst(RegExp(r'/+$'), '')}$generatedPath';
  }

  String? _generatedMediaPath(Uri? parsed, String rawUrl) {
    if (rawUrl.startsWith('/generated-media/')) {
      return rawUrl;
    }
    final String path = parsed?.path ?? rawUrl;
    final int marker = path.indexOf('/generated-media/');
    if (marker < 0) {
      return null;
    }
    return path.substring(marker);
  }
}

class _PortraitPendingState extends StatelessWidget {
  const _PortraitPendingState({
    required this.position,
    required this.nationalityCode,
    this.jerseyColor,
  });

  final String position;
  final String nationalityCode;
  final Color? jerseyColor;

  @override
  Widget build(BuildContext context) {
    final Color accent = jerseyColor ?? GtexColors.gold;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFF171B1F),
            Color(0xFF070A0D),
            Color(0xFF111307),
          ],
        ),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.58)),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                border: Border.all(
                  color: GtexColors.electricGreen.withValues(alpha: 0.22),
                ),
              ),
            ),
          ),
          Positioned(
            left: 18,
            top: 16,
            child: Text(
              position.toUpperCase(),
              style: const TextStyle(
                color: GtexColors.gold,
                fontSize: 20,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
          Positioned(
            right: 16,
            top: 16,
            child: Text(
              nationalityCode.toUpperCase(),
              style: TextStyle(
                color: GtexColors.textMuted.withValues(alpha: 0.86),
                fontSize: 12,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
          Center(
            child: Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: accent.withValues(alpha: 0.16),
                border: Border.all(
                  color: GtexColors.gold.withValues(alpha: 0.5),
                ),
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.person_outline,
                color: GtexColors.gold,
                size: 34,
              ),
            ),
          ),
          const Positioned(
            left: 12,
            right: 12,
            bottom: 16,
            child: Text(
              'PORTRAIT PENDING',
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: GtexColors.electricGreen,
                fontSize: 11,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

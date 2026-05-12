import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../models/player_avatar.dart';

class PlayerCardAvatar extends StatelessWidget {
  const PlayerCardAvatar({
    super.key,
    required this.avatar,
    this.imageUrl,
    this.size = 56,
    this.mode = AvatarMode.card,
  });

  final PlayerAvatar? avatar;
  final String? imageUrl;
  final double size;
  final AvatarMode mode;

  @override
  Widget build(BuildContext context) {
    final String? resolvedImage = imageUrl?.trim();
    if (resolvedImage != null && resolvedImage.isNotEmpty) {
      return _PortraitImage(url: resolvedImage, size: size);
    }
    return _FootballSilhouette(size: size);
  }
}

class _PortraitImage extends StatelessWidget {
  const _PortraitImage({required this.url, required this.size});

  final String url;
  final double size;

  @override
  Widget build(BuildContext context) {
    final BorderRadius radius = BorderRadius.circular(size * 0.18);
    final Widget fallback = _FootballSilhouette(size: size);
    final String resolvedUrl = _resolveMediaUrl(url);
    final bool isRemote =
        resolvedUrl.startsWith('http://') || resolvedUrl.startsWith('https://');
    final bool isAsset = resolvedUrl.startsWith('assets/');
    final bool isDataImage = resolvedUrl.startsWith('data:image/');
    final bool isRelativeMedia = resolvedUrl.startsWith('/generated-media/');
    if (_isSvgImage(resolvedUrl) ||
        _isDisallowedGeneratedRegenPortrait(resolvedUrl)) {
      return fallback;
    }
    if (!isRemote && !isAsset && !isDataImage && !isRelativeMedia) {
      return fallback;
    }
    final Widget image;
    if (isDataImage) {
      final int commaIndex = resolvedUrl.indexOf(',');
      if (commaIndex < 0) {
        return fallback;
      }
      late final Uint8List bytes;
      try {
        bytes = base64Decode(resolvedUrl.substring(commaIndex + 1));
      } on FormatException {
        return fallback;
      }
      image = Image.memory(
        bytes,
        key: const Key('player-card-real-image'),
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => fallback,
      );
    } else if (isRemote || isRelativeMedia) {
      image = Image.network(
        resolvedUrl,
        key: const Key('player-card-real-image'),
        width: size,
        height: size,
        fit: BoxFit.cover,
        gaplessPlayback: true,
        filterQuality: FilterQuality.medium,
        errorBuilder: (_, __, ___) => fallback,
      );
    } else {
      image = Image.asset(
        resolvedUrl,
        key: const Key('player-card-real-image'),
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => fallback,
      );
    }
    return ClipRRect(
      borderRadius: radius,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: radius,
          border: Border.all(
            color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.2),
          ),
        ),
        child: image,
      ),
    );
  }

  bool _isSvgImage(String resolvedUrl) {
    final String lower = resolvedUrl.toLowerCase();
    return lower.startsWith('data:image/svg+xml') ||
        lower.contains('.svg?') ||
        lower.contains('.svg#') ||
        lower.endsWith('.svg');
  }

  bool _isDisallowedGeneratedRegenPortrait(String resolvedUrl) {
    final String lowerPath =
        Uri.tryParse(resolvedUrl)?.path.toLowerCase() ??
        resolvedUrl.toLowerCase();
    if (!lowerPath.contains('/regen_newgen_faces/') &&
        !lowerPath.contains('/regen_portraits/') &&
        !lowerPath.contains('/national_regen_portraits/') &&
        !lowerPath.contains('/regen_portrait_overrides/')) {
      return false;
    }
    final bool approvedBank = lowerPath.contains(
      '/generated-media/regen_newgen_faces/script_skin_hair/',
    );
    final bool raster =
        lowerPath.endsWith('.png') ||
        lowerPath.endsWith('.jpg') ||
        lowerPath.endsWith('.jpeg') ||
        lowerPath.endsWith('.webp');
    return !approvedBank || !raster;
  }

  String _resolveMediaUrl(String rawUrl) {
    if (!rawUrl.startsWith('/generated-media/')) return rawUrl;
    const String apiBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
    final String trimmedBase = apiBaseUrl.trim();
    if (trimmedBase.isEmpty) return rawUrl;
    return '${trimmedBase.replaceFirst(RegExp(r'/+$'), '')}$rawUrl';
  }
}

class _FootballSilhouette extends StatelessWidget {
  const _FootballSilhouette({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
      key: const Key('player-card-fallback-silhouette'),
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.18),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            colorScheme.primaryContainer.withValues(alpha: 0.95),
            colorScheme.surfaceContainerHighest,
          ],
        ),
        border: Border.all(color: colorScheme.primary.withValues(alpha: 0.2)),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: <Widget>[
          Positioned(
            bottom: size * 0.12,
            child: Icon(
              Icons.shield_outlined,
              size: size * 0.42,
              color: colorScheme.onPrimaryContainer.withValues(alpha: 0.24),
            ),
          ),
          Icon(
            Icons.person,
            size: size * 0.58,
            color: colorScheme.onPrimaryContainer.withValues(alpha: 0.82),
          ),
        ],
      ),
    );
  }
}

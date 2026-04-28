import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../models/player_avatar.dart';
import 'player_avatar_widget.dart';

class PlayerCardAvatar extends StatelessWidget {
  const PlayerCardAvatar({
    super.key,
    required this.avatar,
    this.imageUrl,
    this.size = 56,
    this.mode = AvatarMode.card,
    this.preferGeneratedAvatar = false,
  });

  final PlayerAvatar? avatar;
  final String? imageUrl;
  final double size;
  final AvatarMode mode;
  final bool preferGeneratedAvatar;

  @override
  Widget build(BuildContext context) {
    final String? resolvedImage = imageUrl?.trim();
    if (resolvedImage != null && resolvedImage.isNotEmpty) {
      return _PortraitImage(url: resolvedImage, size: size);
    }
    if (preferGeneratedAvatar && avatar != null) {
      return PlayerAvatarWidget(
        avatar: avatar!,
        size: size,
        mode: mode,
        withShadow: true,
      );
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
    final bool isRemote =
        url.startsWith('http://') || url.startsWith('https://');
    final bool isAsset = url.startsWith('assets/');
    final bool isDataImage = url.startsWith('data:image/');
    final bool isRelativeMedia = url.startsWith('/generated-media/');
    if (!isRemote && !isAsset && !isDataImage && !isRelativeMedia) {
      return fallback;
    }
    final Widget image;
    if (isDataImage) {
      final int commaIndex = url.indexOf(',');
      if (commaIndex < 0) {
        return fallback;
      }
      late final Uint8List bytes;
      try {
        bytes = base64Decode(url.substring(commaIndex + 1));
      } on FormatException {
        return fallback;
      }
      image = Image.memory(
        bytes,
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => fallback,
      );
    } else if (isRemote || isRelativeMedia) {
      image = Image.network(
        url,
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => fallback,
      );
    } else {
      image = Image.asset(
        url,
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
}

class _FootballSilhouette extends StatelessWidget {
  const _FootballSilhouette({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
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

import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../data/badge_profile_dto.dart';
import 'identity_color_utils.dart';

class BadgePreviewWidget extends StatelessWidget {
  const BadgePreviewWidget({
    super.key,
    required this.badge,
    this.size = 112,
  });

  final BadgeProfileDto badge;
  final double size;

  @override
  Widget build(BuildContext context) {
    final Color primary = identityColorFromHex(badge.primaryColor);
    final Color secondary = identityColorFromHex(badge.secondaryColor);
    final Color accent = identityColorFromHex(badge.accentColor);
    final Widget content = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[primary, accent],
        ),
        border: Border.all(color: secondary, width: 3),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.26),
            blurRadius: 20,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Opacity(
            opacity: 0.2,
            child: Icon(
              _iconForFamily(badge.iconFamily),
              size: size * 0.6,
              color: secondary,
            ),
          ),
          Center(
            child: Text(
              badge.initials,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: identityReadableOn(primary),
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.0,
                  ),
            ),
          ),
          if (badge.commemorativePatch != null)
            Positioned(
              bottom: 8,
              right: 8,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: secondary.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  badge.commemorativePatch!,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: GteShellTheme.background,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ),
        ],
      ),
    );

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        if (badge.trophyStarCount > 0)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List<Widget>.generate(
                badge.trophyStarCount,
                (int index) => const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 2),
                  child: Icon(
                    Icons.star_rounded,
                    size: 16,
                    color: GteShellTheme.accentWarm,
                  ),
                ),
              ),
            ),
          ),
        _clipForShape(child: content),
      ],
    );
  }

  Widget _clipForShape({required Widget child}) {
    switch (badge.shape) {
      case BadgeShape.shield:
        return ClipPath(clipper: _ShieldClipper(), child: child);
      case BadgeShape.round:
        return ClipOval(child: child);
      case BadgeShape.diamond:
        return Transform.rotate(angle: 0.785398, child: child);
      case BadgeShape.pennant:
        return ClipPath(clipper: _PennantClipper(), child: child);
    }
  }

  IconData _iconForFamily(BadgeIconFamily family) {
    switch (family) {
      case BadgeIconFamily.star:
        return Icons.auto_awesome_rounded;
      case BadgeIconFamily.lion:
        return Icons.pets_rounded;
      case BadgeIconFamily.eagle:
        return Icons.flight_rounded;
      case BadgeIconFamily.crown:
        return Icons.workspace_premium_rounded;
      case BadgeIconFamily.oak:
        return Icons.park_rounded;
      case BadgeIconFamily.bolt:
        return Icons.bolt_rounded;
    }
  }
}

class _ShieldClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final Path path = Path()
      ..moveTo(size.width * 0.15, 0)
      ..lineTo(size.width * 0.85, 0)
      ..quadraticBezierTo(
          size.width, size.height * 0.1, size.width, size.height * 0.28)
      ..lineTo(size.width, size.height * 0.56)
      ..quadraticBezierTo(
          size.width * 0.84, size.height * 0.9, size.width * 0.5, size.height)
      ..quadraticBezierTo(
          size.width * 0.16, size.height * 0.9, 0, size.height * 0.56)
      ..lineTo(0, size.height * 0.28)
      ..quadraticBezierTo(0, size.height * 0.1, size.width * 0.15, 0)
      ..close();
    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}

class _PennantClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final Path path = Path()
      ..moveTo(size.width * 0.08, 0)
      ..lineTo(size.width * 0.9, 0)
      ..lineTo(size.width * 0.82, size.height * 0.78)
      ..lineTo(size.width * 0.48, size.height)
      ..lineTo(size.width * 0.12, size.height * 0.78)
      ..close();
    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}

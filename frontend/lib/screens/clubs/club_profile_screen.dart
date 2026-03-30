import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

class ClubProfileScreen extends StatelessWidget {
  const ClubProfileScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    return GteRouteIntegrityScreen.blocked(
      title: 'Club profile unavailable',
      message:
          'Club profile routes are blocked until the club backend can load and persist real club state without fixture, mock, or local-only fallback.',
      icon: Icons.shield_outlined,
      actionLabel: !isAuthenticated && onOpenLogin != null ? 'Sign in' : null,
      onAction: !isAuthenticated ? onOpenLogin : null,
    );
  }
}

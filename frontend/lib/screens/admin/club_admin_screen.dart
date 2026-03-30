import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

class ClubAdminScreen extends StatelessWidget {
  const ClubAdminScreen({
    super.key,
    this.controller,
    this.clubId = 'royal-lagos-fc',
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
  });

  final ClubController? controller;
  final String clubId;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Club admin unavailable',
      message:
          'Club admin and club analytics routes are blocked until they are backed by the real club backend only.',
      icon: Icons.admin_panel_settings_outlined,
    );
  }
}

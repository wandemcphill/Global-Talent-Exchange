import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

import '../data/club_identity_repository.dart';
import 'club_identity_controller.dart';

class ClubIdentityScreen extends StatelessWidget {
  const ClubIdentityScreen({
    super.key,
    required this.clubId,
    this.initialClubName,
    this.apiBaseUrl,
    this.backendMode,
    this.controller,
    this.repository,
  });

  final String clubId;
  final String? initialClubName;
  final String? apiBaseUrl;
  final GteBackendMode? backendMode;
  final ClubIdentityController? controller;
  final ClubIdentityRepository? repository;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.preview(
      title: 'Club identity preview',
      message:
          'Club identity is preview-only right now. The route is not connected to a real backend profile service, and mock or local-only identity data are disabled.',
      icon: Icons.shield_outlined,
    );
  }
}

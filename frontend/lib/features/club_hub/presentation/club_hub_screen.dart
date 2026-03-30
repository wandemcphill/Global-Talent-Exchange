import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

class ClubHubScreen extends StatelessWidget {
  const ClubHubScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
    this.isAuthenticated = true,
    this.onOpenLogin,
    this.initialTab = ClubNavigationTab.squad,
    this.navigationDependencies,
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final ClubNavigationTab initialTab;
  final GteNavigationDependencies? navigationDependencies;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.hidden(
      title: 'Club hub removed from active shell',
      message:
          'Club hub routes are hidden until the club backend replaces the mock, stub, and local-only fallback stack.',
      icon: Icons.shield_outlined,
    );
  }
}

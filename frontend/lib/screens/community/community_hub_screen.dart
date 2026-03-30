import 'package:flutter/material.dart';

import '../../providers/gte_exchange_controller.dart';
import '../../data/gte_api_repository.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class CommunityHubScreen extends StatelessWidget {
  const CommunityHubScreen({
    super.key,
    required this.controller,
    required this.baseUrl,
    required this.backendMode,
    this.onOpenAdmin,
  });

  final GteExchangeController controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final VoidCallback? onOpenAdmin;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.hidden(
      title: 'Community removed from active shell',
      message:
          'Community, discovery, governance, moderation, and story routes are hidden until the real backend replaces the seeded fallback rails.',
      icon: Icons.forum_outlined,
    );
  }
}

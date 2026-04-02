import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class AdminCommandCenterScreen extends StatelessWidget {
  const AdminCommandCenterScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.hidden(
      title: 'Admin command center removed from active shell',
      message:
          'Admin command center routes stay hidden until policy, finance, and admin engine surfaces are backed by the real backend only.',
      icon: Icons.dashboard_customize_outlined,
    );
  }
}

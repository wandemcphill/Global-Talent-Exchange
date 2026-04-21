import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../data/gte_api_repository.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class GodModeAdminScreen extends StatelessWidget {
  const GodModeAdminScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.hidden(
      title: 'God Mode removed from active shell',
      message:
          'God Mode stays hidden until treasury and admin controls can be served from the real backend without fallback behavior.',
      icon: Icons.admin_panel_settings_outlined,
    );
  }
}

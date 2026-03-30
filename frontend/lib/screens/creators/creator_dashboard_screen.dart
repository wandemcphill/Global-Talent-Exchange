import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class CreatorDashboardScreen extends StatelessWidget {
  const CreatorDashboardScreen({super.key, required this.controller});

  final CreatorController controller;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.preview(
      title: 'Creator dashboard preview',
      message:
          'Creator dashboard routes remain preview-only until creator profile, finance, and reward data are connected to the real backend.',
      icon: Icons.auto_graph_outlined,
    );
  }
}

import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../widgets/gte_route_integrity_screen.dart';

class CreatorProfileScreen extends StatelessWidget {
  const CreatorProfileScreen({super.key, required this.controller});

  final CreatorController controller;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.preview(
      title: 'Creator profile preview',
      message:
          'Creator profile routes remain preview-only until public profile, growth, and finance data are backed by the real backend only.',
      icon: Icons.person_pin_circle_outlined,
    );
  }
}

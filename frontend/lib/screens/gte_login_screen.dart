import 'package:flutter/material.dart';

import '../providers/gte_exchange_controller.dart';
import 'auth/gtex_22_auth_gateway.dart';

/// Route-compatible GTEX sign-in surface. Authentication remains owned by the
/// existing exchange controller; the presentation is now the GTEX 22 identity
/// experience.
class GteLoginScreen extends StatelessWidget {
  const GteLoginScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  Widget build(BuildContext context) {
    return Gtex22LoginScreen(controller: controller);
  }
}

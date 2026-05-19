import 'package:flutter/material.dart';

import '../providers/gte_exchange_controller.dart';
import 'auth/gtex_account_signup_screens.dart';

class GteSignupScreen extends StatelessWidget {
  const GteSignupScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  Widget build(BuildContext context) {
    return const GtexAccountSelectorScreen();
  }
}

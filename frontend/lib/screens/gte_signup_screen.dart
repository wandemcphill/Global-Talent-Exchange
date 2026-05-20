import 'package:flutter/material.dart';

import '../providers/gte_exchange_controller.dart';
import 'auth/gtex_account_signup_screens.dart';
import 'creators/creator_access_request_screen.dart';

class GteSignupScreen extends StatelessWidget {
  const GteSignupScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  Widget build(BuildContext context) {
    return GtexAccountSelectorScreen(
      onOpenCreatorAccessRequest: () {
        Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (BuildContext context) =>
                CreatorAccessRequestScreen(exchangeController: controller),
          ),
        );
      },
    );
  }
}

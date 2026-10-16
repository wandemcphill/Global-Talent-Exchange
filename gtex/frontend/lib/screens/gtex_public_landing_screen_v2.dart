import 'package:flutter/material.dart';

import '../features/onboarding_redesign/gtex_22_home_screen.dart';

class GtexPublicLandingRouteScreenV2 extends StatelessWidget {
  const GtexPublicLandingRouteScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onTraderSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onTraderSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    return Gtex22HomeScreen(
      onSignup: onSignup,
      onLogin: onLogin,
      onCreatorSignup: onCreatorSignup,
      onTraderSignup: onTraderSignup,
      onExploreMarket: onExploreMarket,
    );
  }
}

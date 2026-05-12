import 'package:flutter/material.dart';

import '../features/onboarding_redesign/gtex_public_landing_screen_v2.dart';

class GtexPublicLandingRouteScreenV2 extends StatelessWidget {
  const GtexPublicLandingRouteScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onExploreMarket,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onExploreMarket;

  @override
  Widget build(BuildContext context) {
    return GtexPublicLandingScreenV2(
      onSignup: onSignup,
      onLogin: onLogin,
      onCreatorSignup: onCreatorSignup,
      onExploreMarket: onExploreMarket,
    );
  }
}

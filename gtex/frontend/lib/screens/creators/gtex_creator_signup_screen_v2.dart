import 'package:flutter/material.dart';

import '../../features/onboarding_redesign/gtex_auth_shell_v2.dart';

class GtexCreatorSignupScreenV2 extends StatelessWidget {
  const GtexCreatorSignupScreenV2({
    super.key,
    this.onSubmit,
    this.onLogin,
  });

  final Future<void> Function(Map<String, String> values)? onSubmit;
  final VoidCallback? onLogin;

  @override
  Widget build(BuildContext context) {
    return GtexAuthShellV2(
      mode: GtexAuthMode.creatorSignup,
      onSubmit: onSubmit,
      onSwitchToLogin: onLogin,
    );
  }
}

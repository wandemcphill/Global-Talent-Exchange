import 'package:flutter/material.dart';

import '../features/onboarding_redesign/gtex_auth_shell_v2.dart';

class GteSignupScreenV2 extends StatelessWidget {
  const GteSignupScreenV2({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
  });

  final Future<void> Function(Map<String, String> values)? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;

  @override
  Widget build(BuildContext context) {
    return GtexAuthShellV2(
      mode: GtexAuthMode.userSignup,
      onSubmit: onSignup,
      onSwitchToLogin: onLogin,
      onCreatorSignup: onCreatorSignup,
    );
  }
}

import 'package:flutter/material.dart';

import '../features/onboarding_redesign/gtex_auth_shell_v2.dart';

class GteLoginScreenV2 extends StatelessWidget {
  const GteLoginScreenV2({
    super.key,
    this.onLogin,
    this.onSignup,
  });

  final Future<void> Function(Map<String, String> values)? onLogin;
  final VoidCallback? onSignup;

  @override
  Widget build(BuildContext context) {
    return GtexAuthShellV2(
      mode: GtexAuthMode.login,
      onSubmit: onLogin,
      onSwitchToSignup: onSignup,
    );
  }
}

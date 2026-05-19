import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../screens/auth/gtex_account_signup_screens.dart';

class ProfileSignupScreen extends ConsumerWidget {
  const ProfileSignupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const GtexAccountSelectorScreen();
  }
}

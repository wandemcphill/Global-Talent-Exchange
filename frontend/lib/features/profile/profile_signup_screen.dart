import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_surface_panel.dart';

class ProfileSignupScreen extends ConsumerWidget {
  const ProfileSignupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      body: Container(
        decoration: gteBackdropDecoration(),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: GteSurfacePanel(
              emphasized: true,
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  Icon(
                    Icons.how_to_reg_outlined,
                    color: Theme.of(context).colorScheme.primary,
                    size: 34,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Create GTEX account',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 18),
                  FilledButton.icon(
                    onPressed: () => context.go('/auth/signup'),
                    icon: const Icon(Icons.person_add_alt_1),
                    label: const Text('Continue'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

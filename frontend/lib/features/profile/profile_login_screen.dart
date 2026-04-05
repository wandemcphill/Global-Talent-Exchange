import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class ProfileLoginScreen extends ConsumerStatefulWidget {
  const ProfileLoginScreen({super.key});

  @override
  ConsumerState<ProfileLoginScreen> createState() => _ProfileLoginScreenState();
}

class _ProfileLoginScreenState extends ConsumerState<ProfileLoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    return AppPageLayout(
      title: 'Sign In',
      subtitle:
          'Sign in to sync your club, save progress, and unlock live actions.',
      trailing: const DataSourceBadge(status: DataSourceStatus.live),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (authenticated)
                  const Text(
                    'You are already signed in. Return to Profile, or sign out first to switch accounts.',
                  )
                else ...<Widget>[
                  TextField(
                    controller: _emailController,
                    enabled: !_submitting,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'Email'),
                  ),
                  const SizedBox(height: spacingMD),
                  TextField(
                    controller: _passwordController,
                    enabled: !_submitting,
                    obscureText: true,
                    decoration: const InputDecoration(labelText: 'Password'),
                  ),
                ],
                if (_error != null) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    FilledButton(
                      onPressed: authenticated || _submitting ? null : _submit,
                      child: Text(_submitting ? 'Signing in...' : 'Sign in'),
                    ),
                    OutlinedButton(
                      onPressed:
                          _submitting
                              ? null
                              : () => context.push(AppRoutes.profileSignup),
                      child: const Text('Create account'),
                    ),
                    TextButton(
                      onPressed:
                          _submitting
                              ? null
                              : () => context.go(AppRoutes.profile),
                      child: const Text('Back to Profile'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref
          .read(exchangeApiClientProvider)
          .login(
            email: _emailController.text.trim(),
            password: _passwordController.text,
          );
      final AuthSession? session =
          await ref.read(authSessionStoreProvider).readSession();
      await ref
          .read(appSessionControllerProvider.notifier)
          .updateSession(session);
      if (mounted) {
        context.go(AppRoutes.profile);
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = AppFeedback.messageFor(error);
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }
}

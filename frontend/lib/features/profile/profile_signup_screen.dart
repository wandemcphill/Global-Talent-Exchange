import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/utils/region_code_resolver.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class ProfileSignupScreen extends ConsumerStatefulWidget {
  const ProfileSignupScreen({super.key});

  @override
  ConsumerState<ProfileSignupScreen> createState() =>
      _ProfileSignupScreenState();
}

class _ProfileSignupScreenState extends ConsumerState<ProfileSignupScreen> {
  final TextEditingController _fullNameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  bool _submitting = false;
  bool _isOver18 = false;
  String? _error;

  @override
  void dispose() {
    _fullNameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: 'Create Account',
      subtitle:
          'Create an account to save your club, join competitions, and keep your progress.',
      trailing: const DataSourceBadge(status: DataSourceStatus.live),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                TextField(
                  controller: _fullNameController,
                  enabled: !_submitting,
                  decoration: const InputDecoration(labelText: 'Full name'),
                ),
                const SizedBox(height: spacingMD),
                TextField(
                  controller: _phoneController,
                  enabled: !_submitting,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Phone number'),
                ),
                const SizedBox(height: spacingMD),
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
                const SizedBox(height: spacingMD),
                CheckboxListTile(
                  value: _isOver18,
                  onChanged:
                      _submitting
                          ? null
                          : (bool? value) {
                            setState(() {
                              _isOver18 = value ?? false;
                            });
                          },
                  contentPadding: EdgeInsets.zero,
                  title: const Text('I confirm that I am 18 or older.'),
                ),
                if (_error != null) ...<Widget>[
                  const SizedBox(height: spacingSM),
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
                      onPressed: _submitting ? null : _submit,
                      child: Text(
                        _submitting ? 'Creating...' : 'Create account',
                      ),
                    ),
                    TextButton(
                      onPressed:
                          _submitting
                              ? null
                              : () => context.go(AppRoutes.profileLogin),
                      child: const Text('I already have an account'),
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
    if (!_isOver18) {
      setState(() {
        _error = 'You must confirm that you are 18 or older.';
      });
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref
          .read(exchangeApiClientProvider)
          .register(
            fullName: _fullNameController.text.trim(),
            phoneNumber: _phoneController.text.trim(),
            email: _emailController.text.trim(),
            password: _passwordController.text,
            isOver18: _isOver18,
            regionCode: resolveRegionCodeForContext(context),
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

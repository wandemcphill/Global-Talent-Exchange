import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gtex_branding.dart';
import 'wallet/gte_policy_compliance_center_screen.dart';

class GteSignupScreen extends StatefulWidget {
  const GteSignupScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteSignupScreen> createState() => _GteSignupScreenState();
}

class _GteSignupScreenState extends State<GteSignupScreen> {
  late final TextEditingController _fullNameController;
  late final TextEditingController _phoneController;
  late final TextEditingController _emailController;
  late final TextEditingController _passwordController;
  bool _isOver18 = false;
  String? _localError;

  @override
  void initState() {
    super.initState();
    _fullNameController = TextEditingController();
    _phoneController = TextEditingController();
    _emailController = TextEditingController();
    _passwordController = TextEditingController();
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final String fullName = _fullNameController.text.trim();
    final String phone = _phoneController.text.trim();
    final String email = _emailController.text.trim();
    final String password = _passwordController.text;
    setState(() {
      _localError = null;
    });

    if (!_isOver18) {
      await widget.controller.api.trackAnalyticsEvent('underage_signup_blocked');
      setState(() {
        _localError =
            'You must confirm that you are 18 or older to create an account.';
      });
      return;
    }
    if (fullName.isEmpty ||
        phone.isEmpty ||
        email.isEmpty ||
        password.isEmpty) {
      setState(() {
        _localError = 'Please complete all fields to continue.';
      });
      return;
    }

    await widget.controller.api.trackAnalyticsEvent('signup_started');
    await widget.controller.register(
      fullName: fullName,
      phoneNumber: phone,
      email: email,
      password: password,
      isOver18: _isOver18,
    );
    if (!mounted) {
      return;
    }
    if (widget.controller.authError != null) {
      setState(() {
        _localError = widget.controller.authError;
      });
      return;
    }
    final GteComplianceStatus? compliance =
        widget.controller.complianceStatus;
    if (compliance != null && compliance.hasMissingRequiredPolicies) {
      final bool? openCompliance = await showDialog<bool>(
        context: context,
        builder: (BuildContext context) {
          return AlertDialog(
            title: const Text('Compliance step required'),
            content: Text(
              'You have ${compliance.requiredPolicyAcceptancesMissing} policy items to accept before deposits, withdrawals, and trading are enabled.',
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Later'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Review now'),
              ),
            ],
          );
        },
      );
      if (openCompliance == true && mounted) {
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => GtePolicyComplianceCenterScreen(
              controller: widget.controller,
            ),
          ),
        );
      }
    }
    await widget.controller.api.trackAnalyticsEvent('signup_completed');
    Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1080),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: AnimatedBuilder(
                  animation: widget.controller,
                  builder: (BuildContext context, Widget? child) {
                    final bool isSubmitting = widget.controller.isSigningIn;
                    final String? error = _localError ??
                        (widget.controller.authError == null
                            ? null
                            : AppFeedback.messageFor(
                                widget.controller.authError));
                    return LayoutBuilder(
                      builder:
                          (BuildContext context, BoxConstraints constraints) {
                        final bool stacked = constraints.maxWidth < 900;
                        final Widget story = Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const GtexWordmark(showTagline: false),
                            const SizedBox(height: 20),
                            Text(
                              'Open your GTEX wallet.',
                              style: Theme.of(context).textTheme.displaySmall,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'Sign up in under two minutes. Wallets are provisioned instantly. Deposits run through manual bank transfer with precise tracking.',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                            const SizedBox(height: 18),
                            const GteSurfacePanel(
                              padding: EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text('What you unlock'),
                                  SizedBox(height: 10),
                                  _BulletLine(
                                      icon: Icons.account_balance_wallet_outlined,
                                      text: 'Smart wallet balances, deposit tracking, and withdrawal eligibility.'),
                                  _BulletLine(
                                      icon: Icons.receipt_long_outlined,
                                      text: 'Manual bank transfer funding with exact references.'),
                                  _BulletLine(
                                      icon: Icons.support_agent_outlined,
                                      text: 'In-app dispute chat and WhatsApp escalation.'),
                                ],
                              ),
                            ),
                          ],
                        );

                        final Widget form = GteSurfacePanel(
                          emphasized: true,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Row(
                                children: <Widget>[
                                  const GtexLogoMark(size: 46, compact: true),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: <Widget>[
                                        Text('Create account',
                                            style: Theme.of(context)
                                                .textTheme
                                                .headlineSmall),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Use your real name. Wallets are created automatically.',
                                          style: Theme.of(context)
                                              .textTheme
                                              .bodyMedium,
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 20),
                              TextField(
                                controller: _fullNameController,
                                enabled: !isSubmitting,
                                textInputAction: TextInputAction.next,
                                decoration: const InputDecoration(
                                  labelText: 'Full name',
                                  prefixIcon: Icon(Icons.person_outline),
                                ),
                              ),
                              const SizedBox(height: 14),
                              TextField(
                                controller: _phoneController,
                                enabled: !isSubmitting,
                                textInputAction: TextInputAction.next,
                                keyboardType: TextInputType.phone,
                                decoration: const InputDecoration(
                                  labelText: 'Phone number',
                                  prefixIcon: Icon(Icons.phone_outlined),
                                ),
                              ),
                              const SizedBox(height: 14),
                              TextField(
                                controller: _emailController,
                                enabled: !isSubmitting,
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.next,
                                decoration: const InputDecoration(
                                  labelText: 'Email',
                                  prefixIcon: Icon(Icons.alternate_email),
                                ),
                              ),
                              const SizedBox(height: 14),
                              TextField(
                                controller: _passwordController,
                                enabled: !isSubmitting,
                                obscureText: true,
                                textInputAction: TextInputAction.done,
                                onSubmitted: (_) => _submit(),
                                decoration: const InputDecoration(
                                  labelText: 'Password',
                                  prefixIcon: Icon(Icons.lock_outline),
                                ),
                              ),
                              const SizedBox(height: 16),
                              Container(
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(16),
                                  color: Colors.white.withValues(alpha: 0.04),
                                  border: Border.all(
                                    color: Colors.white.withValues(alpha: 0.08),
                                  ),
                                ),
                                child: Row(
                                  children: <Widget>[
                                    Checkbox(
                                      value: _isOver18,
                                      onChanged: isSubmitting
                                          ? null
                                          : (bool? value) {
                                              setState(() {
                                                _isOver18 = value ?? false;
                                              });
                                            },
                                    ),
                                    const Expanded(
                                      child: Text(
                                          'I confirm that I am 18 or older.'),
                                    ),
                                  ],
                                ),
                              ),
                              if (isSubmitting) ...<Widget>[
                                const SizedBox(height: 16),
                                const LinearProgressIndicator(),
                              ],
                              if (error != null) ...<Widget>[
                                const SizedBox(height: 16),
                                GteStatePanel(
                                  title: 'Signup blocked',
                                  message: error,
                                  icon: Icons.warning_amber_rounded,
                                ),
                              ],
                              const SizedBox(height: 20),
                              Row(
                                children: <Widget>[
                                  Expanded(
                                    child: FilledButton(
                                      onPressed: isSubmitting ? null : _submit,
                                      child: const Text('Create account'),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              TextButton(
                                onPressed: isSubmitting
                                    ? null
                                    : () {
                                        Navigator.of(context).pop();
                                      },
                                child: const Text('I already have a login'),
                              ),
                            ],
                          ),
                        );

                        if (stacked) {
                          return ListView(
                            padding: const EdgeInsets.only(bottom: 40),
                            children: <Widget>[
                              story,
                              const SizedBox(height: 20),
                              form,
                            ],
                          );
                        }

                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(child: story),
                            const SizedBox(width: 24),
                            Expanded(child: form),
                          ],
                        );
                      },
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BulletLine extends StatelessWidget {
  const _BulletLine({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 18, color: GteShellTheme.accentCapital),
          const SizedBox(width: 8),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

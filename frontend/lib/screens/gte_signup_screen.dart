import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../core/utils/region_code_resolver.dart';
import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../ui_gtex/components/gtex_button.dart';
import '../ui_gtex/components/gtex_panel.dart';
import '../ui_gtex/components/gtex_status_chip.dart';
import '../ui_gtex/layout/gtex_focus_flow_scaffold.dart';
import '../ui_gtex/theme/gtex_colors.dart';
import '../ui_gtex/theme/gtex_spacing.dart';
import 'creators/creator_access_request_screen.dart';
import 'wallet/gte_policy_compliance_center_screen.dart';

class GteSignupScreen extends StatefulWidget {
  const GteSignupScreen({super.key, required this.controller});

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

  Future<void> _trackAnalyticsEventSafely(
    String name, {
    Map<String, Object?> metadata = const <String, Object?>{},
  }) async {
    try {
      await widget.controller.api.trackAnalyticsEvent(name, metadata: metadata);
    } catch (_) {
      // Analytics must not block signup on pre-auth screens.
    }
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
      await _trackAnalyticsEventSafely('underage_signup_blocked');
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

    final String regionCode = resolveRegionCodeForContext(context);
    await _trackAnalyticsEventSafely('signup_started');
    await widget.controller.register(
      fullName: fullName,
      phoneNumber: phone,
      email: email,
      password: password,
      isOver18: _isOver18,
      regionCode: regionCode,
    );
    if (!context.mounted) {
      return;
    }
    final BuildContext currentContext = context;
    final NavigatorState navigator = Navigator.of(currentContext);
    if (widget.controller.authError != null) {
      setState(() {
        _localError = widget.controller.authError;
      });
      return;
    }
    final GteComplianceStatus? compliance = widget.controller.complianceStatus;
    if (compliance != null && compliance.hasMissingRequiredPolicies) {
      final bool? openCompliance = await showDialog<bool>(
        context: currentContext,
        builder: (BuildContext context) {
          return AlertDialog(
            backgroundColor: GtexColors.panelStrong,
            title: const Text(
              'Compliance step required',
              style: TextStyle(color: GtexColors.text),
            ),
            content: Text(
              'You have ${compliance.requiredPolicyAcceptancesMissing} policy items to review in the compliance center.',
              style: const TextStyle(color: GtexColors.textSecondary),
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
      if (openCompliance == true) {
        if (!currentContext.mounted) {
          return;
        }
        await navigator.push(
          MaterialPageRoute<void>(
            builder:
                (_) => GtePolicyComplianceCenterScreen(
                  controller: widget.controller,
                ),
          ),
        );
        if (!currentContext.mounted) {
          return;
        }
      }
    }
    await _trackAnalyticsEventSafely('signup_completed');
    if (!currentContext.mounted) {
      return;
    }
    navigator.pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final bool isSubmitting = widget.controller.isSigningIn;
        final String? authError = widget.controller.authError;
        final String? error =
            _localError ??
            (authError == null ? null : AppFeedback.messageFor(authError));

        return GtexFocusFlowScaffold(
          title: 'Create your GTEX account',
          subtitle:
              'Start with a verified football profile, instant wallet provisioning, regional compliance, and a clear route into club ownership.',
          maxWidth: 1120,
          accent: GtexColors.gold,
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool stacked = constraints.maxWidth < 860;
              final Widget story = _SignupStory(stacked: stacked);
              final Widget form = _SignupForm(
                fullNameController: _fullNameController,
                phoneController: _phoneController,
                emailController: _emailController,
                passwordController: _passwordController,
                isSubmitting: isSubmitting,
                isOver18: _isOver18,
                error: error,
                onOver18Changed: (bool? value) {
                  setState(() {
                    _isOver18 = value ?? false;
                  });
                },
                onSubmit: _submit,
                controller: widget.controller,
              );

              if (stacked) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    story,
                    const SizedBox(height: GtexSpacing.lg),
                    form,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(flex: 5, child: story),
                  const SizedBox(width: GtexSpacing.lg),
                  Expanded(flex: 5, child: form),
                ],
              );
            },
          ),
        );
      },
    );
  }
}

class _SignupStory extends StatelessWidget {
  const _SignupStory({required this.stacked});

  final bool stacked;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const GtexStatusChip(
          label: 'NEW GTEX ACCOUNT',
          icon: Icons.person_add_alt_1_outlined,
          tone: GtexStatusTone.premium,
        ),
        const SizedBox(height: GtexSpacing.lg),
        Text(
          'Your first account should feel like opening a football institution.',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
            height: 1.08,
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Text(
          'Signup keeps the existing GTEX wallet and compliance logic, but the experience now belongs to the same dark command-center system as the market and club cockpit.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: GtexColors.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: GtexSpacing.lg),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            _SignupLane(
              width: stacked ? double.infinity : 235,
              title: 'Profile',
              body: 'Name, phone, email, and regional setup.',
              icon: Icons.badge_outlined,
              accent: GtexColors.cyan,
            ),
            _SignupLane(
              width: stacked ? double.infinity : 235,
              title: 'Compliance',
              body: 'Age confirmation and policy review stay intact.',
              icon: Icons.verified_user_outlined,
              accent: GtexColors.gold,
            ),
            _SignupLane(
              width: stacked ? double.infinity : 235,
              title: 'Wallet',
              body: 'Funding and withdrawals stay tied to live account logic.',
              icon: Icons.account_balance_wallet_outlined,
              accent: GtexColors.pitch,
            ),
          ],
        ),
      ],
    );
  }
}

class _SignupForm extends StatelessWidget {
  const _SignupForm({
    required this.fullNameController,
    required this.phoneController,
    required this.emailController,
    required this.passwordController,
    required this.isSubmitting,
    required this.isOver18,
    required this.error,
    required this.onOver18Changed,
    required this.onSubmit,
    required this.controller,
  });

  final TextEditingController fullNameController;
  final TextEditingController phoneController;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final bool isSubmitting;
  final bool isOver18;
  final String? error;
  final ValueChanged<bool?> onOver18Changed;
  final Future<void> Function() onSubmit;
  final GteExchangeController controller;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Account setup',
      subtitle:
          'Use real details so wallet, KYC, orders, and support remain aligned.',
      accent: GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          TextField(
            controller: fullNameController,
            enabled: !isSubmitting,
            textInputAction: TextInputAction.next,
            style: const TextStyle(color: GtexColors.text),
            decoration: _gtexInputDecoration(
              label: 'Full name',
              icon: Icons.person_outline,
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          TextField(
            controller: phoneController,
            enabled: !isSubmitting,
            textInputAction: TextInputAction.next,
            keyboardType: TextInputType.phone,
            style: const TextStyle(color: GtexColors.text),
            decoration: _gtexInputDecoration(
              label: 'Phone number',
              icon: Icons.phone_outlined,
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          TextField(
            controller: emailController,
            enabled: !isSubmitting,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            style: const TextStyle(color: GtexColors.text),
            decoration: _gtexInputDecoration(
              label: 'Email',
              icon: Icons.alternate_email,
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          TextField(
            controller: passwordController,
            enabled: !isSubmitting,
            obscureText: true,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => onSubmit(),
            style: const TextStyle(color: GtexColors.text),
            decoration: _gtexInputDecoration(
              label: 'Password',
              icon: Icons.lock_outline,
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          Container(
            padding: const EdgeInsets.all(GtexSpacing.md),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(
                color:
                    isOver18
                        ? GtexColors.pitch.withValues(alpha: 0.42)
                        : GtexColors.line.withValues(alpha: 0.9),
              ),
            ),
            child: Row(
              children: <Widget>[
                Checkbox(
                  value: isOver18,
                  onChanged: isSubmitting ? null : onOver18Changed,
                  activeColor: GtexColors.pitch,
                  checkColor: Colors.black,
                ),
                const Expanded(
                  child: Text(
                    'I confirm that I am 18 or older.',
                    style: TextStyle(color: GtexColors.textSecondary),
                  ),
                ),
              ],
            ),
          ),
          if (isSubmitting) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            const LinearProgressIndicator(color: GtexColors.gold),
          ],
          if (error != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            _InlineAlert(message: error!),
          ],
          const SizedBox(height: GtexSpacing.lg),
          GtexButton(
            label: isSubmitting ? 'Creating account...' : 'Create account',
            icon: Icons.person_add_alt_1_outlined,
            onPressed: isSubmitting ? null : () => onSubmit(),
          ),
          const SizedBox(height: GtexSpacing.sm),
          GtexButton(
            label: 'I already have a login',
            icon: Icons.login,
            variant: GtexButtonVariant.secondary,
            onPressed:
                isSubmitting
                    ? null
                    : () {
                      Navigator.of(context).pop();
                    },
          ),
          const SizedBox(height: GtexSpacing.xs),
          TextButton.icon(
            onPressed:
                isSubmitting
                    ? null
                    : () async {
                      await Navigator.of(context).push<void>(
                        MaterialPageRoute<void>(
                          builder:
                              (BuildContext context) =>
                                  CreatorAccessRequestScreen(
                                    exchangeController: controller,
                                  ),
                        ),
                      );
                    },
            icon: const Icon(Icons.video_camera_front_outlined),
            label: const Text('Apply for creator access'),
          ),
        ],
      ),
    );
  }
}

class _SignupLane extends StatelessWidget {
  const _SignupLane({
    required this.width,
    required this.title,
    required this.body,
    required this.icon,
    required this.accent,
  });

  final double width;
  final String title;
  final String body;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: GtexPanel(
        title: title,
        subtitle: body,
        accent: accent,
        trailing: Icon(icon, color: accent),
        child: const SizedBox.shrink(),
      ),
    );
  }
}

class _InlineAlert extends StatelessWidget {
  const _InlineAlert({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.red.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.red.withValues(alpha: 0.38)),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.error_outline, color: GtexColors.red),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: GtexColors.text,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

InputDecoration _gtexInputDecoration({
  required String label,
  required IconData icon,
}) {
  final OutlineInputBorder border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
    borderSide: BorderSide(color: GtexColors.line.withValues(alpha: 0.9)),
  );
  return InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(color: GtexColors.textMuted),
    prefixIcon: Icon(icon, color: GtexColors.gold),
    filled: true,
    fillColor: Colors.white.withValues(alpha: 0.045),
    border: border,
    enabledBorder: border,
    focusedBorder: border.copyWith(
      borderSide: const BorderSide(color: GtexColors.gold),
    ),
  );
}

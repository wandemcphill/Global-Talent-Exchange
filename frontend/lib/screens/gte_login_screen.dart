import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../ui_gtex/components/gtex_button.dart';
import '../ui_gtex/components/gtex_panel.dart';
import '../ui_gtex/components/gtex_status_chip.dart';
import '../ui_gtex/layout/gtex_focus_flow_scaffold.dart';
import '../ui_gtex/theme/gtex_colors.dart';
import '../ui_gtex/theme/gtex_spacing.dart';
import 'creators/creator_access_request_screen.dart';
import 'gte_signup_screen.dart';
import 'wallet/gte_policy_compliance_center_screen.dart';

class GteLoginScreen extends StatefulWidget {
  const GteLoginScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteLoginScreen> createState() => _GteLoginScreenState();
}

class _GteLoginScreenState extends State<GteLoginScreen> {
  late final TextEditingController _emailController;
  late final TextEditingController _passwordController;

  @override
  void initState() {
    super.initState();
    _emailController = TextEditingController();
    _passwordController = TextEditingController();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        return GtexFocusFlowScaffold(
          title:
              widget.controller.isAuthenticated
                  ? "You're signed in"
                  : 'Welcome back',
          subtitle:
              widget.controller.isAuthenticated
                  ? "You're signed in. Jump back into your club, the market, your wallet, and competitions."
                  : 'One sign-in for your club, transfers, national rentals, creator tools, and wallet.',
          maxWidth: 1180,
          accent: GtexColors.pitch,
          child:
              widget.controller.isAuthenticated
                  ? _AuthenticatedPanel(controller: widget.controller)
                  : _LoginContent(
                    controller: widget.controller,
                    emailController: _emailController,
                    passwordController: _passwordController,
                    onSubmit: _submit,
                  ),
        );
      },
    );
  }

  Future<void> _submit() async {
    await widget.controller.signIn(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
    if (!mounted) {
      return;
    }
    if (widget.controller.isAuthenticated) {
      Navigator.of(context).pop(true);
    }
  }
}

class _LoginContent extends StatelessWidget {
  const _LoginContent({
    required this.controller,
    required this.emailController,
    required this.passwordController,
    required this.onSubmit,
  });

  final GteExchangeController controller;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final Future<void> Function() onSubmit;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 860;
        final Widget story = _AuthStory(stacked: stacked);
        final Widget form = _LoginForm(
          controller: controller,
          emailController: emailController,
          passwordController: passwordController,
          onSubmit: onSubmit,
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
            Expanded(flex: 6, child: story),
            const SizedBox(width: GtexSpacing.lg),
            Expanded(flex: 5, child: form),
          ],
        );
      },
    );
  }
}

class _AuthStory extends StatelessWidget {
  const _AuthStory({required this.stacked});

  final bool stacked;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: GtexColors.pitch,
                borderRadius: BorderRadius.circular(16),
                boxShadow: <BoxShadow>[
                  GtexColors.glow(GtexColors.pitch, opacity: 0.2),
                ],
              ),
              alignment: Alignment.center,
              child: const Text(
                'GT',
                style: TextStyle(
                  color: Colors.black,
                  fontWeight: FontWeight.w900,
                  fontSize: 18,
                ),
              ),
            ),
            const SizedBox(width: GtexSpacing.md),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'GTEX',
                    style: TextStyle(
                      color: GtexColors.text,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.8,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Global Football Talent Marketplace',
                    style: TextStyle(color: GtexColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.xl),
        Text(
          'Own a club. Sign the stars. Win it all.',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
            height: 1.05,
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Text(
          'Your club, transfers, wallet, competitions, regens, and news — all from one account.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: GtexColors.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: GtexSpacing.lg),
        Wrap(
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.sm,
          children: const <Widget>[
            GtexStatusChip(
              label: '17K+ player market',
              icon: Icons.groups_2_outlined,
              tone: GtexStatusTone.success,
            ),
            GtexStatusChip(
              label: 'Club ownership',
              icon: Icons.shield_outlined,
              tone: GtexStatusTone.premium,
            ),
            GtexStatusChip(
              label: 'Wallet protected',
              icon: Icons.account_balance_wallet_outlined,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.lg),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            _AuthLane(
              width: stacked ? double.infinity : 240,
              title: 'Transfer room',
              body: 'Country, league, division, club, player.',
              icon: Icons.account_tree_outlined,
              accent: GtexColors.pitch,
            ),
            _AuthLane(
              width: stacked ? double.infinity : 240,
              title: 'Club cockpit',
              body: 'Squad, identity, finances, trophies.',
              icon: Icons.stadium_outlined,
              accent: GtexColors.gold,
            ),
            _AuthLane(
              width: stacked ? double.infinity : 240,
              title: 'Live world',
              body: 'Regens, news, tournaments, alerts.',
              icon: Icons.public_outlined,
              accent: GtexColors.cyan,
            ),
          ],
        ),
      ],
    );
  }
}

class _LoginForm extends StatelessWidget {
  const _LoginForm({
    required this.controller,
    required this.emailController,
    required this.passwordController,
    required this.onSubmit,
  });

  final GteExchangeController controller;
  final TextEditingController emailController;
  final TextEditingController passwordController;
  final Future<void> Function() onSubmit;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Sign in',
      subtitle: 'Sign in to your club, market, and wallet.',
      accent: GtexColors.pitch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          TextField(
            controller: emailController,
            enabled: !controller.isSigningIn,
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
            enabled: !controller.isSigningIn,
            obscureText: true,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => onSubmit(),
            style: const TextStyle(color: GtexColors.text),
            decoration: _gtexInputDecoration(
              label: 'Password',
              icon: Icons.lock_outline,
            ),
          ),
          if (controller.isSigningIn) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            const LinearProgressIndicator(color: GtexColors.pitch),
          ],
          if (controller.authError != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            _InlineAlert(message: controller.authError!),
          ],
          const SizedBox(height: GtexSpacing.lg),
          GtexButton(
            label: controller.isSigningIn ? 'Opening GTEX...' : 'Enter GTEX',
            icon: Icons.login,
            onPressed: controller.isSigningIn ? null : () => onSubmit(),
          ),
          const SizedBox(height: GtexSpacing.sm),
          GtexButton(
            label: 'Create account',
            icon: Icons.person_add_alt_1_outlined,
            variant: GtexButtonVariant.secondary,
            onPressed:
                controller.isSigningIn
                    ? null
                    : () async {
                      await Navigator.of(context).push<void>(
                        MaterialPageRoute<void>(
                          builder:
                              (BuildContext context) =>
                                  GteSignupScreen(controller: controller),
                        ),
                      );
                    },
          ),
          const SizedBox(height: GtexSpacing.xs),
          TextButton.icon(
            onPressed:
                controller.isSigningIn
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

class _AuthenticatedPanel extends StatelessWidget {
  const _AuthenticatedPanel({required this.controller});

  final GteExchangeController controller;

  @override
  Widget build(BuildContext context) {
    final GteComplianceStatus? compliance = controller.complianceStatus;
    final bool requiresPolicyAction =
        compliance?.hasMissingRequiredPolicies ?? false;
    final bool hasRestrictedAccess =
        compliance != null &&
        (!compliance.canDeposit ||
            !compliance.canTradeMarket ||
            !compliance.canWithdrawPlatformRewards);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        GtexPanel(
          title: hasRestrictedAccess ? 'Session active' : 'You are in',
          subtitle:
              hasRestrictedAccess
                  ? 'Signed in as ${controller.session!.user.username}. Some actions remain limited until compliance review is complete.'
                  : 'Signed in as ${controller.session!.user.username}. Your club, market, wallet, and matchday spaces are ready.',
          accent: hasRestrictedAccess ? GtexColors.orange : GtexColors.pitch,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexButton(
                label: 'Enter GTEX',
                icon: Icons.arrow_forward,
                onPressed: () => Navigator.of(context).pop(true),
              ),
              if (requiresPolicyAction)
                GtexButton(
                  label: 'Open compliance',
                  icon: Icons.gavel_outlined,
                  variant: GtexButtonVariant.secondary,
                  onPressed: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder:
                            (_) => GtePolicyComplianceCenterScreen(
                              controller: controller,
                            ),
                      ),
                    );
                  },
                ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        if (controller.isLoadingCompliance)
          const GtexPanel(
            accent: GtexColors.cyan,
            child: Text(
              'Loading compliance status...',
              style: TextStyle(color: GtexColors.textSecondary),
            ),
          )
        else if (controller.complianceError != null)
          GtexPanel(
            title: 'Compliance status unavailable',
            subtitle: controller.complianceError,
            accent: GtexColors.red,
            child: GtexButton(
              label: 'Retry',
              icon: Icons.refresh,
              variant: GtexButtonVariant.secondary,
              onPressed: controller.refreshCompliance,
            ),
          )
        else if (compliance != null)
          GtexPanel(
            title:
                requiresPolicyAction
                    ? 'Compliance action required'
                    : hasRestrictedAccess
                    ? 'Access restrictions active'
                    : 'Compliance status',
            subtitle:
                requiresPolicyAction
                    ? 'Complete required policy acceptances to unlock deposits, withdrawals, and player-market actions.'
                    : hasRestrictedAccess
                    ? 'This session is active, but some account actions are limited for this region or review state.'
                    : 'All required policies are accepted. Account actions are ready.',
            accent: hasRestrictedAccess ? GtexColors.orange : GtexColors.pitch,
            child: Wrap(
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.sm,
              children: <Widget>[
                GtexStatusChip(label: 'Country ${compliance.countryCode}'),
                GtexStatusChip(
                  label:
                      compliance.canTradeMarket
                          ? 'Player moves enabled'
                          : 'Player moves limited',
                  tone:
                      compliance.canTradeMarket
                          ? GtexStatusTone.success
                          : GtexStatusTone.warning,
                ),
                GtexStatusChip(
                  label:
                      compliance.canDeposit
                          ? 'Add funds enabled'
                          : 'Add funds limited',
                  tone:
                      compliance.canDeposit
                          ? GtexStatusTone.success
                          : GtexStatusTone.warning,
                ),
                GtexStatusChip(
                  label: 'Compliance ${compliance.complianceStatus}',
                  tone:
                      hasRestrictedAccess
                          ? GtexStatusTone.warning
                          : GtexStatusTone.success,
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _AuthLane extends StatelessWidget {
  const _AuthLane({
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
    prefixIcon: Icon(icon, color: GtexColors.pitch),
    filled: true,
    fillColor: Colors.white.withValues(alpha: 0.045),
    border: border,
    enabledBorder: border,
    focusedBorder: border.copyWith(
      borderSide: const BorderSide(color: GtexColors.pitch),
    ),
  );
}

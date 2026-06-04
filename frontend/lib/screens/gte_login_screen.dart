import 'package:flutter/material.dart';
import 'package:gte_frontend/features/capital/wallet/presentation/gte_policy_compliance_center_screen.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../shared/auth/biometric_unlock_service.dart';
import '../shared/models/auth_session.dart';
import 'creators/creator_access_request_screen.dart';
import 'gte_recovery_screen.dart';
import 'gte_signup_screen.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gtex_branding.dart';

class GteLoginScreen extends StatefulWidget {
  const GteLoginScreen({
    super.key,
    required this.controller,
    this.biometricUnlockController,
  });

  final GteExchangeController controller;
  final TrustedDeviceBiometricUnlockController? biometricUnlockController;

  @override
  State<GteLoginScreen> createState() => _GteLoginScreenState();
}

class _GteLoginScreenState extends State<GteLoginScreen> {
  late final TextEditingController _emailController;
  late final TextEditingController _passwordController;
  bool _canUseBiometricUnlock = false;
  bool _isBiometricUnlocking = false;
  String? _biometricError;

  @override
  void initState() {
    super.initState();
    _emailController = TextEditingController();
    _passwordController = TextEditingController();
    _refreshBiometricOffer();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
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
              constraints: const BoxConstraints(maxWidth: 1220),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: AnimatedBuilder(
                  animation: widget.controller,
                  builder: (BuildContext context, Widget? child) {
                    if (widget.controller.isAuthenticated) {
                      final GteComplianceStatus? compliance =
                          widget.controller.complianceStatus;
                      final bool requiresPolicyAction =
                          compliance?.hasMissingRequiredPolicies ?? false;
                      final bool hasRestrictedAccess =
                          compliance != null &&
                          (!compliance.canDeposit ||
                              !compliance.canTradeMarket ||
                              !compliance.canWithdrawPlatformRewards);
                      return SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: <Widget>[
                            GteStatePanel(
                              title:
                                  hasRestrictedAccess
                                      ? 'Session active'
                                      : 'You are in',
                              message:
                                  hasRestrictedAccess
                                      ? 'You are signed in as ${widget.controller.session!.user.username}. Some account actions are still limited until compliance review finishes.'
                                      : 'You are signed in as ${widget.controller.session!.user.username}. Your club, matchday, and scouting spaces are ready.',
                              actionLabel: 'Enter GTEX',
                              onAction: () {
                                Navigator.of(context).pop(true);
                              },
                              icon: Icons.verified_user_outlined,
                            ),
                            const SizedBox(height: 16),
                            if (widget.controller.isLoadingCompliance)
                              const GteSurfacePanel(
                                child: Text('Loading compliance status...'),
                              )
                            else if (widget.controller.complianceError != null)
                              GteStatePanel(
                                title: 'Compliance status unavailable',
                                message: widget.controller.complianceError!,
                                icon: Icons.warning_amber_outlined,
                                actionLabel: 'Retry',
                                onAction: widget.controller.refreshCompliance,
                              )
                            else if (compliance != null)
                              GteSurfacePanel(
                                accentColor:
                                    hasRestrictedAccess
                                        ? GteShellTheme.accentWarm
                                        : GteShellTheme.accentCapital,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(
                                      requiresPolicyAction
                                          ? 'Compliance action required'
                                          : hasRestrictedAccess
                                          ? 'Access restrictions active'
                                          : 'Compliance status',
                                      style:
                                          Theme.of(
                                            context,
                                          ).textTheme.titleMedium,
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      requiresPolicyAction
                                          ? 'Complete the required policy acceptances to restore eligible account actions.'
                                          : hasRestrictedAccess
                                          ? 'This session is active, but some account actions are limited for this region or review state.'
                                          : 'All required policies are accepted. Account actions are ready.',
                                    ),
                                    const SizedBox(height: 12),
                                    Wrap(
                                      spacing: 10,
                                      runSpacing: 10,
                                      children: <Widget>[
                                        _SignalPill(
                                          label:
                                              'Country ${compliance.countryCode}',
                                        ),
                                        _SignalPill(
                                          label:
                                              compliance.canTradeMarket
                                                  ? 'Player moves enabled'
                                                  : 'Player moves limited',
                                        ),
                                        _SignalPill(
                                          label:
                                              compliance.canDeposit
                                                  ? 'Account actions enabled'
                                                  : 'Account actions limited',
                                        ),
                                        _SignalPill(
                                          label:
                                              'Compliance ${compliance.complianceStatus}',
                                        ),
                                      ],
                                    ),
                                    if (hasRestrictedAccess) ...<Widget>[
                                      const SizedBox(height: 12),
                                      if (requiresPolicyAction) ...<Widget>[
                                        Text(
                                          'Missing: ${compliance.requiredPolicyAcceptancesMissing} item(s)',
                                          style:
                                              Theme.of(
                                                context,
                                              ).textTheme.bodyMedium,
                                        ),
                                        const SizedBox(height: 10),
                                      ],
                                      FilledButton.tonalIcon(
                                        onPressed: () async {
                                          await Navigator.of(context).push(
                                            MaterialPageRoute<void>(
                                              builder:
                                                  (_) =>
                                                      GtePolicyComplianceCenterScreen(
                                                        controller:
                                                            widget.controller,
                                                      ),
                                            ),
                                          );
                                        },
                                        icon: const Icon(Icons.gavel_outlined),
                                        label: const Text(
                                          'Open compliance center',
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                          ],
                        ),
                      );
                    }

                    return LayoutBuilder(
                      builder: (
                        BuildContext context,
                        BoxConstraints constraints,
                      ) {
                        final bool stacked = constraints.maxWidth < 900;
                        final Widget story = Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const GtexWordmark(showTagline: false),
                            const SizedBox(height: 22),
                            Text(
                              'Build your club. Scout the world. Step into matchday.',
                              style: Theme.of(context).textTheme.displaySmall,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'GTEX brings club management, player discovery, competitions, creator access, and verified market workflows into one account. Guest access only shows confirmed public context.',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                            const SizedBox(height: 22),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: const <Widget>[
                                _SignalPill(label: 'Build your club'),
                                _SignalPill(label: 'Scout new talent'),
                                _SignalPill(label: 'Play live matchday'),
                                _SignalPill(label: 'Follow rising stars'),
                              ],
                            ),
                            const SizedBox(height: 22),
                            const GteSurfacePanel(
                              padding: EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text('Choose your starting point'),
                                  SizedBox(height: 10),
                                  Wrap(
                                    spacing: 10,
                                    runSpacing: 10,
                                    children: <Widget>[
                                      _OpeningMoveChip(
                                        label:
                                            '1. Create account and choose a role',
                                        accent: GteShellTheme.accent,
                                      ),
                                      _OpeningMoveChip(
                                        label:
                                            '2. Sign in and return to your club',
                                        accent: GteShellTheme.accentArena,
                                      ),
                                      _OpeningMoveChip(
                                        label:
                                            '3. Check matchday and player context',
                                        accent: GteShellTheme.accentCapital,
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 22),
                            const GtexSignalStrip(
                              title: 'One football product, role-gated tools',
                              subtitle:
                                  'Club, creator, and verified trader workflows open according to account role and compliance state.',
                              tiles: <Widget>[
                                GtexSignalTile(
                                  label: 'Club',
                                  value: 'YOUR CREST',
                                  caption:
                                      'Identity, progression, and your home base.',
                                  icon: Icons.show_chart,
                                  color: GteShellTheme.accent,
                                ),
                                GtexSignalTile(
                                  label: 'Matchday',
                                  value: 'LIVE STATUS',
                                  caption:
                                      'Fixtures, highlights, and bracket energy.',
                                  icon: Icons.stadium_outlined,
                                  color: GteShellTheme.accentArena,
                                ),
                                GtexSignalTile(
                                  label: 'Account',
                                  value: 'REVIEWED ACCESS',
                                  caption:
                                      'Policy checks and role limits keep tools clear.',
                                  icon: Icons.verified_user_outlined,
                                  color: GteShellTheme.accentCapital,
                                ),
                              ],
                            ),
                            const SizedBox(height: 22),
                            const GteSurfacePanel(
                              padding: EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text('What opens after login'),
                                  SizedBox(height: 10),
                                  _BulletLine(
                                    icon: Icons.shield_outlined,
                                    text:
                                        'Club HQ with your badge, schedule, and progression.',
                                  ),
                                  _BulletLine(
                                    icon: Icons.person_search_outlined,
                                    text:
                                        'A player board for scouting, comparing, and making moves.',
                                  ),
                                  _BulletLine(
                                    icon: Icons.stadium_outlined,
                                    text:
                                        'Matchday and highlights that keep the season alive.',
                                  ),
                                  _BulletLine(
                                    icon: Icons.admin_panel_settings_outlined,
                                    text:
                                        'If your role allows it, creator, trader, and admin tools appear automatically.',
                                  ),
                                ],
                              ),
                            ),
                          ],
                        );

                        final Widget authCard = GteSurfacePanel(
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
                                        Text(
                                          'Sign in',
                                          style:
                                              Theme.of(
                                                context,
                                              ).textTheme.headlineSmall,
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'One sign-in for football users, creators, verified traders, and admins. The app reveals only what this account can use.',
                                          style:
                                              Theme.of(
                                                context,
                                              ).textTheme.bodyMedium,
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 20),
                              TextField(
                                controller: _emailController,
                                enabled: !widget.controller.isSigningIn,
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.next,
                                decoration: const InputDecoration(
                                  labelText: 'Email',
                                  prefixIcon: Icon(Icons.alternate_email),
                                ),
                              ),
                              const SizedBox(height: 16),
                              TextField(
                                controller: _passwordController,
                                enabled: !widget.controller.isSigningIn,
                                obscureText: true,
                                textInputAction: TextInputAction.done,
                                onSubmitted: (_) => _submit(),
                                decoration: const InputDecoration(
                                  labelText: 'Password',
                                  prefixIcon: Icon(Icons.lock_outline),
                                ),
                              ),
                              if (widget.controller.isSigningIn) ...<Widget>[
                                const SizedBox(height: 16),
                                const LinearProgressIndicator(),
                                const SizedBox(height: 8),
                                Text(
                                  'Checking your account and eligible GTEX tools...',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                              if (widget.controller.authError !=
                                  null) ...<Widget>[
                                const SizedBox(height: 14),
                                Container(
                                  padding: const EdgeInsets.all(14),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(18),
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.error.withValues(alpha: 0.12),
                                    border: Border.all(
                                      color: Theme.of(context).colorScheme.error
                                          .withValues(alpha: 0.32),
                                    ),
                                  ),
                                  child: Row(
                                    children: <Widget>[
                                      Icon(
                                        Icons.error_outline,
                                        color:
                                            Theme.of(context).colorScheme.error,
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          widget.controller.authError!,
                                          style: TextStyle(
                                            color:
                                                Theme.of(
                                                  context,
                                                ).colorScheme.error,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                              const SizedBox(height: 18),
                              if (_canUseBiometricUnlock) ...<Widget>[
                                SizedBox(
                                  width: double.infinity,
                                  child: OutlinedButton.icon(
                                    onPressed:
                                        widget.controller.isSigningIn ||
                                                _isBiometricUnlocking
                                            ? null
                                            : _unlockWithBiometrics,
                                    icon: const Icon(Icons.fingerprint),
                                    label: Text(
                                      _isBiometricUnlocking
                                          ? 'Unlocking...'
                                          : 'Unlock trusted device',
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 12),
                              ],
                              if (_biometricError != null) ...<Widget>[
                                Text(
                                  _biometricError!,
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                                ),
                                const SizedBox(height: 12),
                              ],
                              SizedBox(
                                width: double.infinity,
                                child: FilledButton.icon(
                                  onPressed:
                                      widget.controller.isSigningIn
                                          ? null
                                          : _submit,
                                  icon: const Icon(Icons.login),
                                  label: Text(
                                    widget.controller.isSigningIn
                                        ? 'Signing in...'
                                        : 'Sign in to GTEX',
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextButton(
                                onPressed:
                                    widget.controller.isSigningIn
                                        ? null
                                        : () async {
                                          await Navigator.of(
                                            context,
                                          ).push<void>(
                                            MaterialPageRoute<void>(
                                              builder:
                                                  (BuildContext context) =>
                                                      GteSignupScreen(
                                                        controller:
                                                            widget.controller,
                                                      ),
                                            ),
                                          );
                                        },
                                child: const Text('Create account'),
                              ),
                              TextButton(
                                onPressed:
                                    widget.controller.isSigningIn
                                        ? null
                                        : () async {
                                          await Navigator.of(
                                            context,
                                          ).push<void>(
                                            MaterialPageRoute<void>(
                                              builder:
                                                  (BuildContext context) =>
                                                      GteRecoveryScreen(
                                                        controller:
                                                            widget.controller,
                                                      ),
                                            ),
                                          );
                                        },
                                child: const Text('Recover account'),
                              ),
                              TextButton(
                                onPressed:
                                    widget.controller.isSigningIn
                                        ? null
                                        : () async {
                                          await Navigator.of(
                                            context,
                                          ).push<void>(
                                            MaterialPageRoute<void>(
                                              builder:
                                                  (BuildContext context) =>
                                                      CreatorAccessRequestScreen(
                                                        exchangeController:
                                                            widget.controller,
                                                      ),
                                            ),
                                          );
                                        },
                                child: const Text('Apply for creator access'),
                              ),
                            ],
                          ),
                        );

                        if (stacked) {
                          return ListView(
                            children: <Widget>[
                              story,
                              const SizedBox(height: 20),
                              authCard,
                            ],
                          );
                        }
                        return SingleChildScrollView(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Expanded(flex: 6, child: story),
                              const SizedBox(width: 20),
                              Expanded(flex: 4, child: authCard),
                            ],
                          ),
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

  Future<void> _submit() async {
    await widget.controller.signIn(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );
    if (!mounted) {
      return;
    }
    if (widget.controller.isAuthenticated) {
      await _offerBiometricEnrollmentIfAvailable();
    }
    await _refreshBiometricOffer();
    if (!mounted) {
      return;
    }
    if (widget.controller.isAuthenticated) {
      Navigator.of(context).pop(true);
    }
  }

  Future<void> _offerBiometricEnrollmentIfAvailable() async {
    final TrustedDeviceBiometricUnlockController? controller =
        widget.biometricUnlockController;
    if (controller == null) {
      return;
    }
    bool canEnroll = false;
    try {
      canEnroll = await controller.canOfferBiometricEnrollment();
    } catch (_) {
      canEnroll = false;
    }
    if (!canEnroll || !mounted) {
      return;
    }
    final bool enable =
        await showDialog<bool>(
          context: context,
          builder:
              (BuildContext context) => AlertDialog(
                title: const Text('Enable biometric unlock?'),
                content: const Text(
                  'Use Face ID or fingerprint unlock on this trusted device.',
                ),
                actions: <Widget>[
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Not now'),
                  ),
                  FilledButton.icon(
                    onPressed: () => Navigator.of(context).pop(true),
                    icon: const Icon(Icons.fingerprint),
                    label: const Text('Enable'),
                  ),
                ],
              ),
        ) ??
        false;
    if (!enable) {
      return;
    }
    bool enrolled = false;
    try {
      enrolled = await controller.enableBiometricUnlockForCurrentSession(
        reason: 'Enable biometric unlock for your GTEX trusted device',
      );
    } catch (_) {
      enrolled = false;
    }
    if (!enrolled && mounted) {
      setState(() {
        _biometricError = 'Biometric setup was not completed.';
      });
    }
  }

  Future<void> _refreshBiometricOffer() async {
    final TrustedDeviceBiometricUnlockController? controller =
        widget.biometricUnlockController;
    if (controller == null) {
      return;
    }
    bool available = false;
    try {
      available = await controller.canOfferBiometricUnlock();
    } catch (_) {
      available = false;
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _canUseBiometricUnlock = available;
    });
  }

  Future<void> _unlockWithBiometrics() async {
    final TrustedDeviceBiometricUnlockController? biometricController =
        widget.biometricUnlockController;
    if (biometricController == null) {
      return;
    }
    setState(() {
      _isBiometricUnlocking = true;
      _biometricError = null;
    });
    try {
      final AuthSession? session = await biometricController
          .unlockPersistedSession(reason: 'Unlock your GTEX trusted device');
      if (!mounted) {
        return;
      }
      if (session == null) {
        setState(() {
          _biometricError = 'Biometric unlock was not completed.';
        });
        return;
      }
      widget.controller.syncSession(
        GteAuthSession.fromJson(
          session.rawJson.isNotEmpty ? session.rawJson : session.toJson(),
        ),
      );
      await widget.controller.refreshAccount();
      if (!mounted) {
        return;
      }
      if (widget.controller.isAuthenticated) {
        Navigator.of(context).pop(true);
      }
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _biometricError = 'Biometric unlock is unavailable on this device.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isBiometricUnlocking = false;
        });
      }
    }
  }
}

class _SignalPill extends StatelessWidget {
  const _SignalPill({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(label, style: Theme.of(context).textTheme.labelLarge),
    );
  }
}

class _OpeningMoveChip extends StatelessWidget {
  const _OpeningMoveChip({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.12),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: accent),
      ),
    );
  }
}

class _BulletLine extends StatelessWidget {
  const _BulletLine({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: GteShellTheme.accent.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, size: 16, color: GteShellTheme.accent),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

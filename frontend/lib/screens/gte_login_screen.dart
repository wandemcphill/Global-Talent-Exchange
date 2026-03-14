import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import 'gte_signup_screen.dart';
import 'wallet/gte_policy_compliance_center_screen.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gtex_branding.dart';

class GteLoginScreen extends StatefulWidget {
  const GteLoginScreen({
    super.key,
    required this.controller,
  });

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
    _emailController = TextEditingController(text: 'fan@demo.gte.local');
    _passwordController = TextEditingController(text: 'DemoPass123');
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
                      final bool blocked =
                          compliance?.hasMissingRequiredPolicies ?? false;
                      return SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: <Widget>[
                            GteStatePanel(
                              title: 'Mission confirmed',
                              message:
                                  'Active session for ${widget.controller.session!.user.username}. The exchange floor, e-game arena, and control tower are now unlocked for this account.',
                              actionLabel: 'Enter GTEX',
                              onAction: () {
                                Navigator.of(context).pop(true);
                              },
                              icon: Icons.verified_user_outlined,
                            ),
                            const SizedBox(height: 16),
                            if (widget.controller.isLoadingCompliance)
                              const GteSurfacePanel(
                                child: Text(
                                  'Loading compliance status...',
                                ),
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
                                accentColor: blocked
                                    ? GteShellTheme.accentWarm
                                    : GteShellTheme.accentCapital,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(
                                      blocked
                                          ? 'Compliance action required'
                                          : 'Compliance status',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium,
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      blocked
                                          ? 'Complete the required policy acceptances to unlock deposits, withdrawals, and trading.'
                                          : 'All required policies are accepted. Wallet actions are cleared to proceed.',
                                    ),
                                    const SizedBox(height: 12),
                                    Wrap(
                                      spacing: 10,
                                      runSpacing: 10,
                                      children: <Widget>[
                                        _SignalPill(
                                          label: 'Country ${compliance.countryCode}',
                                        ),
                                        _SignalPill(
                                          label: compliance.marketTradingEnabled
                                              ? 'Trading enabled'
                                              : 'Trading blocked',
                                        ),
                                        _SignalPill(
                                          label: compliance.depositsEnabled
                                              ? 'Deposits enabled'
                                              : 'Deposits blocked',
                                        ),
                                      ],
                                    ),
                                    if (blocked) ...<Widget>[
                                      const SizedBox(height: 12),
                                      Text(
                                        'Missing: ${compliance.requiredPolicyAcceptancesMissing} item(s)',
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyMedium,
                                      ),
                                      const SizedBox(height: 10),
                                      FilledButton.tonalIcon(
                                        onPressed: () async {
                                          await Navigator.of(context).push(
                                            MaterialPageRoute<void>(
                                              builder: (_) =>
                                                  GtePolicyComplianceCenterScreen(
                                                controller: widget.controller,
                                              ),
                                            ),
                                          );
                                        },
                                        icon: const Icon(Icons.gavel_outlined),
                                        label: const Text('Open compliance center'),
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
                      builder: (BuildContext context, BoxConstraints constraints) {
                        final bool stacked = constraints.maxWidth < 900;
                        final Widget story = Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const GtexWordmark(showTagline: false),
                            const SizedBox(height: 22),
                            Text(
                              'Own the market. Run the matchday universe.',
                              style: Theme.of(context).textTheme.displaySmall,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'GTEX is where football talent trading, squad building, manager scarcity, and cinematic e-game competition meet in one seamless app. Users should know the point instantly. This screen now says it with a floodlight, not a whisper.',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                            const SizedBox(height: 22),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: const <Widget>[
                                _SignalPill(label: 'Trade player upside'),
                                _SignalPill(label: 'Hire scarce managers'),
                                _SignalPill(label: 'Run adaptive competitions'),
                                _SignalPill(label: 'Watch 3-5 min match stories'),
                              ],
                            ),
                            const SizedBox(height: 22),
                            const GteSurfacePanel(
                              padding: EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text('Choose your opening move'),
                                  SizedBox(height: 10),
                                  Wrap(
                                    spacing: 10,
                                    runSpacing: 10,
                                    children: <Widget>[
                                      _OpeningMoveChip(label: '1. Sign in and trade instantly', accent: GteShellTheme.accent),
                                      _OpeningMoveChip(label: '2. Preview the live match center', accent: GteShellTheme.accentArena),
                                      _OpeningMoveChip(label: '3. Unlock wallet + portfolio control', accent: GteShellTheme.accentCapital),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 22),
                            const GtexSignalStrip(
                              title: 'Three product lanes, one brand spine',
                              subtitle: 'GTEX should feel premium from the first frame. The market reads like a terminal, the arena reads like match night, and the wallet reads like a control room.',
                              tiles: <Widget>[
                                GtexSignalTile(label: 'Trade', value: 'FAST TAPE', caption: 'Dense, analytical, and execution-led.', icon: Icons.show_chart, color: GteShellTheme.accent),
                                GtexSignalTile(label: 'Arena', value: 'LIVE STORY', caption: 'Fixtures, highlights, and bracket energy.', icon: Icons.stadium_outlined, color: GteShellTheme.accentArena),
                                GtexSignalTile(label: 'Capital', value: 'TRUST LAYER', caption: 'Balances, orders, and control signals.', icon: Icons.account_balance_wallet_outlined, color: GteShellTheme.accentCapital),
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
                                  _BulletLine(icon: Icons.show_chart, text: 'A high-speed trading floor for player assets and market depth.'),
                                  _BulletLine(icon: Icons.stadium_outlined, text: 'A separate e-game arena built for fixtures, highlights, and competitive tension.'),
                                  _BulletLine(icon: Icons.psychology_alt_outlined, text: 'Managers and coaches with real tactical fingerprints, not cardboard cut-outs.'),
                                  _BulletLine(icon: Icons.admin_panel_settings_outlined, text: 'Admins use this same login. Role assignment happens invisibly and securely on the backend.'),
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
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: <Widget>[
                                        Text('Sign in', style: Theme.of(context).textTheme.headlineSmall),
                                        const SizedBox(height: 4),
                                        Text(
                                          'One doorway for users, managers, admins, and super admins. Access unfolds after authentication.',
                                          style: Theme.of(context).textTheme.bodyMedium,
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
                              ],
                              if (widget.controller.authError != null) ...<Widget>[
                                const SizedBox(height: 14),
                                Container(
                                  padding: const EdgeInsets.all(14),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(18),
                                    color: Theme.of(context).colorScheme.error.withValues(alpha: 0.12),
                                    border: Border.all(
                                      color: Theme.of(context).colorScheme.error.withValues(alpha: 0.32),
                                    ),
                                  ),
                                  child: Row(
                                    children: <Widget>[
                                      Icon(Icons.error_outline, color: Theme.of(context).colorScheme.error),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          widget.controller.authError!,
                                          style: TextStyle(color: Theme.of(context).colorScheme.error),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                              const SizedBox(height: 16),
                              Wrap(
                                spacing: 12,
                                runSpacing: 12,
                                children: <Widget>[
                                  OutlinedButton.icon(
                                    onPressed: widget.controller.isSigningIn
                                        ? null
                                        : () {
                                            _emailController.text = 'fan@demo.gte.local';
                                            _passwordController.text = 'DemoPass123';
                                          },
                                    icon: const Icon(Icons.rocket_launch_outlined),
                                    label: const Text('Use demo credentials'),
                                  ),
                                  OutlinedButton.icon(
                                    onPressed: widget.controller.isSigningIn
                                        ? null
                                        : () {
                                            _emailController.text = 'vidvimedialtd@gmail.com';
                                            _passwordController.text = 'NewPass1234!';
                                          },
                                    icon: const Icon(Icons.security_outlined),
                                    label: const Text('Use admin credentials'),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 18),
                              Container(
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(18),
                                  color: Colors.white.withValues(alpha: 0.04),
                                  border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                                ),
                                child: const Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text('Guest preview'),
                                    SizedBox(height: 8),
                                    Text('You can explore the shell before login, but order entry, wallet actions, and protected creator or admin controls stay locked until authentication succeeds.'),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 20),
                              SizedBox(
                                width: double.infinity,
                                child: FilledButton.icon(
                                  onPressed: widget.controller.isSigningIn ? null : _submit,
                                  icon: const Icon(Icons.login),
                                  label: Text(
                                    widget.controller.isSigningIn ? 'Opening the gate...' : 'Enter GTEX now',
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextButton(
                                onPressed: widget.controller.isSigningIn
                                    ? null
                                    : () async {
                                        await Navigator.of(context).push<void>(
                                          MaterialPageRoute<void>(
                                            builder: (BuildContext context) =>
                                                GteSignupScreen(
                                              controller: widget.controller,
                                            ),
                                          ),
                                        );
                                      },
                                child: const Text('Create a new account'),
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
                        return Row(
                          children: <Widget>[
                            Expanded(flex: 6, child: story),
                            const SizedBox(width: 20),
                            Expanded(flex: 4, child: authCard),
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
          Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

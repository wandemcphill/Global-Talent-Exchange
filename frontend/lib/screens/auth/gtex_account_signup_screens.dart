import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

final String _totpSetupAlphabet = String.fromCharCodes(<int>[
  for (var code = 65; code <= 90; code += 1) code,
  for (var code = 50; code <= 55; code += 1) code,
]);

String _generateTotpSetupSecret({int length = 32}) {
  final random = math.Random.secure();
  return String.fromCharCodes(
    List<int>.generate(
      length,
      (_) => _totpSetupAlphabet.codeUnitAt(
        random.nextInt(_totpSetupAlphabet.length),
      ),
    ),
  );
}

enum _SignupLane { general, creator, trader }

class GtexAccountSelectorScreen extends StatelessWidget {
  const GtexAccountSelectorScreen({super.key, this.onOpenCreatorAccessRequest});

  // Kept for compatibility with existing callers. Creator access is now requested
  // after authentication, so the public selector never bypasses normal signup.
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050709),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 920),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      SvgPicture.asset(
                        'assets/branding/gtex_wordmark_22.svg',
                        width: 178,
                        height: 42,
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: () => context.go('/auth/login'),
                        icon: const Icon(Icons.login_rounded, size: 17),
                        label: const Text('Already have an account? Sign in'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 54),
                  const Text(
                    'CREATE YOUR\nGTEX ID.',
                    style: TextStyle(
                      fontFamily: 'BarlowCondensed',
                      color: Color(0xFFF4F7F8),
                      fontSize: 70,
                      height: .83,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 16),
                  const SizedBox(
                    width: 690,
                    child: Text(
                      'One account. One GTEX ID. Clubs, creator tools, coin trading and the wider football universe come after you sign in.',
                      style: TextStyle(
                        color: Color(0xFF93A0AA),
                        fontSize: 16,
                        height: 1.55,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  InkWell(
                    onTap: () => context.go('/auth/signup/user'),
                    borderRadius: BorderRadius.circular(22),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(26),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0A0F13),
                        borderRadius: BorderRadius.circular(22),
                        border: Border.all(
                          color: const Color(0xFFB9FF3D).withValues(alpha: .34),
                        ),
                      ),
                      child: const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Icon(
                            Icons.person_add_alt_1_rounded,
                            color: Color(0xFFB9FF3D),
                            size: 34,
                          ),
                          SizedBox(height: 18),
                          Text(
                            'NORMAL GTEX ACCOUNT',
                            style: TextStyle(
                              fontFamily: 'DMMono',
                              color: Color(0xFFB9FF3D),
                              fontSize: 10,
                              letterSpacing: 1.3,
                            ),
                          ),
                          SizedBox(height: 7),
                          Text(
                            'Create your GTEX ID',
                            style: TextStyle(
                              fontFamily: 'BarlowCondensed',
                              color: Color(0xFFF4F7F8),
                              fontSize: 34,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Start with your account identity only. After sign-in, create a club, recruit players, request creator access, or activate coin-trading capabilities.',
                            style: TextStyle(
                              color: Color(0xFF93A0AA),
                              fontSize: 13,
                              height: 1.5,
                            ),
                          ),
                          SizedBox(height: 18),
                          Row(
                            children: <Widget>[
                              Text(
                                'CONTINUE',
                                style: TextStyle(
                                  color: Color(0xFF93A0AA),
                                  fontFamily: 'DMMono',
                                  fontSize: 9,
                                  letterSpacing: 1,
                                ),
                              ),
                              Spacer(),
                              Icon(
                                Icons.arrow_forward_rounded,
                                color: Color(0xFFB9FF3D),
                                size: 18,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  const Row(
                    children: <Widget>[
                      Expanded(
                        child: _SignupCapabilityNote(
                          icon: Icons.shield_outlined,
                          title: 'Your identity',
                          body: 'GTEX ID belongs to the person, not to a club or trading profile.',
                        ),
                      ),
                      SizedBox(width: 14),
                      Expanded(
                        child: _SignupCapabilityNote(
                          icon: Icons.groups_rounded,
                          title: 'Club later',
                          body: 'Create the club after login. That separate action creates the Club ID.',
                        ),
                      ),
                      SizedBox(width: 14),
                      Expanded(
                        child: _SignupCapabilityNote(
                          icon: Icons.account_balance_wallet_outlined,
                          title: 'Capabilities later',
                          body: 'Creator and coin-trader tools are activated inside the authenticated account.',
                        ),
                      ),
                    ],
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

class _SignupCapabilityNote extends StatelessWidget {
  const _SignupCapabilityNote({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: const Color(0xFF0A0F13),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1C2830)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: const Color(0xFF93A0AA), size: 20),
          const SizedBox(height: 12),
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFFF4F7F8),
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            body,
            style: const TextStyle(
              color: Color(0xFF66737D),
              fontSize: 11,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

class GtexUserSignupScreen extends StatelessWidget {
  const GtexUserSignupScreen({
    super.key,
    required this.controller,
    required this.config,
  });

  final GteExchangeController controller;
  final GteAppConfig config;

  @override
  Widget build(BuildContext context) => _GtexUnifiedSignupScreen(
    controller: controller,
    config: config,
    lane: _SignupLane.general,
  );
}

class GtexCreatorSignupScreen extends StatelessWidget {
  const GtexCreatorSignupScreen({
    super.key,
    required this.controller,
    required this.config,
  });

  final GteExchangeController controller;
  final GteAppConfig config;

  @override
  Widget build(BuildContext context) => _GtexUnifiedSignupScreen(
    controller: controller,
    config: config,
    lane: _SignupLane.creator,
  );
}

class GtexTraderSignupScreen extends StatelessWidget {
  const GtexTraderSignupScreen({
    super.key,
    required this.controller,
    required this.config,
  });

  final GteExchangeController controller;
  final GteAppConfig config;

  @override
  Widget build(BuildContext context) => _GtexUnifiedSignupScreen(
    controller: controller,
    config: config,
    lane: _SignupLane.trader,
  );
}

class _GtexUnifiedSignupScreen extends StatefulWidget {
  const _GtexUnifiedSignupScreen({
    required this.controller,
    required this.config,
    required this.lane,
  });

  final GteExchangeController controller;
  final GteAppConfig config;
  final _SignupLane lane;

  @override
  State<_GtexUnifiedSignupScreen> createState() => _GtexUnifiedSignupScreenState();
}

class _GtexUnifiedSignupScreenState extends State<_GtexUnifiedSignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  String? _error;
  bool _submitting = false;

  @override
  void dispose() {
    _name.dispose();
    _username.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  String get _title => switch (widget.lane) {
    _SignupLane.general => 'Create your GTEX ID',
    _SignupLane.creator => 'Create your GTEX ID',
    _SignupLane.trader => 'Create your GTEX ID',
  };

  String get _subtitle => switch (widget.lane) {
    _SignupLane.general =>
      'Start with one normal GTEX account. Create your club and unlock the rest after sign-in.',
    _SignupLane.creator =>
      'This is still a normal GTEX account. Creator access is activated from your signed-in account.',
    _SignupLane.trader =>
      'This is still a normal GTEX account. Coin trading is activated from your signed-in account when you are ready.',
  };

  String get _contextLine => switch (widget.lane) {
    _SignupLane.general =>
      'No club, nationality, trading currency, or role declaration is required to create the account.',
    _SignupLane.creator =>
      'Do not create a creator profile here. Finish your account first, then request creator access.',
    _SignupLane.trader =>
      'Do not choose a nationality or preferred currency here. Your available payment options and coin transaction details appear when you transact.',
  };

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final client = GteExchangeApiClient.standard(
        baseUrl: widget.config.apiBaseUrl,
        mode: widget.config.backendMode,
      );
      final session = await client.signupUser(
        GteUserSignupRequest(
          fullName: _name.text.trim(),
          username: _username.text.trim(),
          email: _email.text.trim(),
          password: _password.text,
        ),
      );
      widget.controller.syncSession(session);
      if (!mounted) {
        return;
      }
      Navigator.of(context).pushReplacement<void, void>(
        MaterialPageRoute<void>(
          builder: (_) => GtexSignupSuccessScreen(
            controller: widget.controller,
            session: session,
          ),
        ),
      );
    } catch (error) {
      if (mounted) {
        setState(() => _error = error.toString());
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return _SignupScaffold(
      title: _title,
      subtitle: _subtitle,
      icon: Icons.person_add_alt_1_rounded,
      error: _error,
      submitting: _submitting,
      formKey: _formKey,
      onSubmit: _submit,
      children: <Widget>[
        _sectionLabel(context, '01', 'Account identity'),
        _field(_name, 'Full Name'),
        _field(_username, 'Username'),
        _field(_email, 'Email'),
        _field(_password, 'Password', obscure: true),
        _sectionLabel(context, '02', 'What happens next'),
        Text(
          _contextLine,
          style: const TextStyle(
            color: Color(0xFF93A0AA),
            fontSize: 12,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'You will receive your GTEX ID immediately after a successful registration and stay signed in.',
          style: TextStyle(
            color: Color(0xFF66737D),
            fontSize: 11,
            height: 1.5,
          ),
        ),
      ],
    );
  }
}

class GtexSignupSuccessScreen extends StatelessWidget {
  const GtexSignupSuccessScreen({
    super.key,
    required this.controller,
    required this.session,
  });

  final GteExchangeController controller;
  final GteAuthSession session;

  @override
  Widget build(BuildContext context) {
    final String gtexId = session.user.id;
    return Scaffold(
      backgroundColor: const Color(0xFF050709),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(22),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Container(
                padding: const EdgeInsets.all(28),
                decoration: BoxDecoration(
                  color: const Color(0xFF0A0F13),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: const Color(0xFFB9FF3D).withValues(alpha: .3),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Icon(
                      Icons.verified_rounded,
                      color: Color(0xFFB9FF3D),
                      size: 44,
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'GTEX ID CREATED',
                      style: TextStyle(
                        fontFamily: 'DMMono',
                        color: Color(0xFFB9FF3D),
                        fontSize: 11,
                        letterSpacing: 1.4,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Welcome to GTEX.',
                      style: TextStyle(
                        fontFamily: 'BarlowCondensed',
                        color: Color(0xFFF4F7F8),
                        fontSize: 46,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Your account identity is ready. This GTEX ID belongs to you and is separate from any club you create later.',
                      style: const TextStyle(
                        color: Color(0xFF93A0AA),
                        fontSize: 13,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 20),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: const Color(0xFF070B0F),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: const Color(0xFF1C2830)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          const Text(
                            'YOUR GTEX ID',
                            style: TextStyle(
                              color: Color(0xFF66737D),
                              fontFamily: 'DMMono',
                              fontSize: 9,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(height: 8),
                          SelectableText(
                            gtexId,
                            style: const TextStyle(
                              color: Color(0xFFF4F7F8),
                              fontFamily: 'DMMono',
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Next: enter GTEX, create your club from the authenticated workspace when you are ready, and activate any additional capabilities from inside your account.',
                      style: TextStyle(
                        color: Color(0xFF93A0AA),
                        fontSize: 12,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 22),
                    FilledButton.icon(
                      onPressed: () => context.go('/app/home'),
                      icon: const Icon(Icons.arrow_forward_rounded, size: 17),
                      label: const Text('ENTER GTEX'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFB9FF3D),
                        foregroundColor: const Color(0xFF08100A),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 16,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SignupScaffold extends StatelessWidget {
  const _SignupScaffold({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.error,
    required this.submitting,
    required this.formKey,
    required this.onSubmit,
    required this.children,
  });
  final String title, subtitle;
  final IconData icon;
  final String? error;
  final bool submitting;
  final GlobalKey<FormState> formKey;
  final VoidCallback onSubmit;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFF050709),
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(22),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 920),
            child: Form(
              key: formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      SvgPicture.asset(
                        'assets/branding/gtex_wordmark_22.svg',
                        width: 175,
                        height: 42,
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: () => context.go('/auth/login'),
                        icon: const Icon(Icons.login_rounded, size: 16),
                        label: const Text('Sign in'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 34),
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0A0F13),
                      borderRadius: BorderRadius.circular(22),
                      border: Border.all(color: const Color(0xFF1C2830)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                color: const Color(
                                  0xFFB9FF3D,
                                ).withValues(alpha: .1),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Icon(icon, color: const Color(0xFFB9FF3D)),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    title,
                                    style: const TextStyle(
                                      fontFamily: 'BarlowCondensed',
                                      color: Color(0xFFF4F7F8),
                                      fontSize: 34,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    subtitle,
                                    style: const TextStyle(
                                      color: Color(0xFF93A0AA),
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        if (error != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 16),
                            child: Text(
                              error!,
                              style: const TextStyle(
                                color: Color(0xFFFF6B7A),
                                fontSize: 11,
                              ),
                            ),
                          ),
                        const SizedBox(height: 20),
                        ...children.map(
                          (Widget child) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: child,
                          ),
                        ),
                        const SizedBox(height: 8),
                        FilledButton.icon(
                          onPressed: submitting ? null : onSubmit,
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFFB9FF3D),
                            foregroundColor: const Color(0xFF08100A),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 20,
                              vertical: 16,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                          icon:
                              submitting
                                  ? const SizedBox(
                                    width: 17,
                                    height: 17,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                  : const Icon(
                                    Icons.arrow_forward_rounded,
                                    size: 17,
                                  ),
                          label: Text(
                            submitting ? 'CREATING GTEX ID' : 'CREATE GTEX ID',
                            style: const TextStyle(
                              fontWeight: FontWeight.w900,
                              fontSize: 11,
                              letterSpacing: .8,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

Widget _field(
  TextEditingController controller,
  String label, {
  bool obscure = false,
}) => TextFormField(
  controller: controller,
  obscureText: obscure,
  style: const TextStyle(color: Color(0xFFF4F7F8), fontSize: 13),
  decoration: InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(color: Color(0xFF66737D), fontSize: 12),
    filled: true,
    fillColor: const Color(0xFF070B0F),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFF1C2830)),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFF1C2830)),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFF36E38A)),
    ),
  ),
  validator:
      (String? value) =>
          value == null || value.trim().isEmpty ? '$label is required' : null,
);

Widget _sectionLabel(BuildContext context, String label, String title) =>
    Padding(
      padding: const EdgeInsets.only(top: 10, bottom: 3),
      child: Row(
        children: <Widget>[
          Text(
            label,
            style: const TextStyle(
              fontFamily: 'DMMono',
              color: Color(0xFFB9FF3D),
              fontSize: 9,
              letterSpacing: 1.3,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                fontFamily: 'BarlowCondensed',
                color: Color(0xFFF4F7F8),
                fontSize: 21,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );

Widget _dropdown(
  String label,
  String value,
  List<String> options,
  ValueChanged<String> onChanged,
) => DropdownButtonFormField<String>(
  value: value,
  dropdownColor: const Color(0xFF0A0F13),
  style: const TextStyle(color: Color(0xFFF4F7F8), fontSize: 13),
  decoration: InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(color: Color(0xFF66737D), fontSize: 12),
    filled: true,
    fillColor: const Color(0xFF070B0F),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFF1C2830)),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFF1C2830)),
    ),
  ),
  items:
      options
          .map(
            (item) => DropdownMenuItem<String>(value: item, child: Text(item)),
          )
          .toList(),
  onChanged: (String? next) {
    if (next != null) onChanged(next);
  },
);

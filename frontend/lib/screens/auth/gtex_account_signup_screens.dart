import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/turnstile_challenge.dart';

const String _gtexTurnstileSiteKey =
    String.fromEnvironment('GTE_TURNSTILE_SITE_KEY');

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

class GtexAccountSelectorScreen extends StatelessWidget {
  const GtexAccountSelectorScreen({super.key, this.onOpenCreatorAccessRequest});
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  Widget build(BuildContext context) {
    final roles = <_AccountRole>[
      const _AccountRole(
        'USER ACCOUNT',
        'Create a normal GTEX member account. You can create a club any time after signing in. Creator promotion is available only when you no longer own any clubs; sell or transfer every club you still own first.',
        Icons.person_outline_rounded,
        Color(0xFFB9FF3D),
        '/auth/signup/user',
      ),
      const _AccountRole(
        'CREATOR ACCOUNT',
        'Register directly into a dedicated Creator account for publishing and creator tools. Creator accounts cannot switch back to User or Club Owner.',
        Icons.campaign_outlined,
        Color(0xFFFF7BC5),
        '/auth/signup/creator',
      ),
      const _AccountRole(
        'COIN TRADER ACCOUNT',
        'A dedicated lane for Coin Trader desk activity using this account. It cannot switch to User, Club Owner, or Creator.',
        Icons.candlestick_chart_rounded,
        Color(0xFFFFD166),
        '/auth/signup/trader',
      ),
    ];
    return Scaffold(
      backgroundColor: const Color(0xFF050709),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1160),
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
                        label: Text(
                          MediaQuery.sizeOf(context).width < 560
                              ? 'Sign in'
                              : 'Already have an account? Sign in',
                        ),
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
                      'Choose one dedicated account type: User, Creator, or Coin Trader. User accounts may create clubs after signing in. Creator promotion from an existing User account is only allowed when no club remains under that account\'s ownership.',
                      style: TextStyle(
                        color: Color(0xFF93A0AA),
                        fontSize: 16,
                        height: 1.55,
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),
                  LayoutBuilder(
                    builder: (_, c) {
                      final columns =
                          c.maxWidth > 920
                              ? 3
                              : c.maxWidth > 580
                              ? 2
                              : 1;
                      return GridView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: roles.length,
                        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: columns,
                          crossAxisSpacing: 14,
                          mainAxisSpacing: 14,
                          // Keep all role copy visible at phone and desktop
                          // widths; these cards contain the account restrictions
                          // users need to read before choosing a dedicated lane.
                          mainAxisExtent: columns == 1 ? 340 : 330,
                        ),
                        itemBuilder: (_, i) => _AccountRoleCard(role: roles[i]),
                      );
                    },
                  ),
                  if (onOpenCreatorAccessRequest != null) ...<Widget>[
                    const SizedBox(height: 18),
                    OutlinedButton.icon(
                      onPressed: onOpenCreatorAccessRequest,
                      icon: const Icon(Icons.how_to_reg_outlined),
                      label: const Text('Have a GTEX ID? Apply for creator access'),
                    ),
                  ],
                  const SizedBox(height: 24),
                  Container(
                    padding: const EdgeInsets.all(17),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0A0F13),
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(color: const Color(0xFF1C2830)),
                    ),
                    child: const Row(
                      children: <Widget>[
                        Icon(
                          Icons.verified_user_rounded,
                          color: Color(0xFF36E38A),
                          size: 19,
                        ),
                        SizedBox(width: 11),
                        Expanded(
                          child: Text(
                            'Secure identity, protected sessions and role-aware onboarding. KYC is requested where the platform actually needs it.',
                            style: TextStyle(
                              color: Color(0xFF93A0AA),
                              fontSize: 12,
                              height: 1.45,
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
    );
  }
}

class _AccountRole {
  const _AccountRole(this.title, this.body, this.icon, this.accent, this.route);
  final String title, body, route;
  final IconData icon;
  final Color accent;
}

class _AccountRoleCard extends StatelessWidget {
  const _AccountRoleCard({required this.role});
  final _AccountRole role;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: () => context.go(role.route),
    borderRadius: BorderRadius.circular(20),
    child: Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF0A0F13),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: role.accent.withValues(alpha: .28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: role.accent.withValues(alpha: .1),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(role.icon, color: role.accent),
          ),
          const Spacer(),
          Text(
            role.title,
            style: TextStyle(
              fontFamily: 'DMMono',
              color: role.accent,
              fontSize: 10,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 7),
          Text(
            role.body,
            style: const TextStyle(
              color: Color(0xFFF4F7F8),
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 15),
          const Row(
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
                color: Color(0xFF93A0AA),
                size: 17,
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class GtexUserSignupScreen extends StatefulWidget {
  const GtexUserSignupScreen({
    super.key,
    required this.controller,
    this.config,
  });
  final GteExchangeController controller;
  final GteAppConfig? config;
  @override
  State<GtexUserSignupScreen> createState() => _GtexUserSignupScreenState();
}

class _GtexUserSignupScreenState extends State<GtexUserSignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  int _birthYear = 2000;
  int _birthMonth = 1;
  int _birthDay = 15;
  bool _isOver18 = false;
  bool _submitting = false;
  String? _error;
  String? _turnstileToken;
  @override
  Widget build(BuildContext context) => _SignupScaffold(
    title: 'Join GTEX',
    subtitle: 'Display name, @username, password — create your GTEX ID.',
    icon: Icons.sports_soccer_rounded,
    error: _error,
    submitting: _submitting,
    formKey: _formKey,
    onSubmit: _submit,
    children: <Widget>[
      _sectionLabel(context, '01', 'Your identity'),
      _field(_name, 'Display name'),
      _field(_username, '@username'),
      _field(_email, 'Email (optional)'),
      _field(_password, 'Password (at least 8 characters)', obscure: true),
      _sectionLabel(context, '02', 'Age check'),
      Row(
        children: <Widget>[
          Expanded(
            child: _dropdown(
              'Year',
              '$_birthYear',
              List<String>.generate(60, (int i) => '${DateTime.now().year - 18 - i}'),
              (value) => setState(() => _birthYear = int.parse(value)),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _dropdown(
              'Month',
              '$_birthMonth',
              List<String>.generate(12, (int i) => '${i + 1}'),
              (value) => setState(() => _birthMonth = int.parse(value)),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _dropdown(
              'Day',
              '$_birthDay',
              List<String>.generate(31, (int i) => '${i + 1}'),
              (value) => setState(() => _birthDay = int.parse(value)),
            ),
          ),
        ],
      ),
      Material(
        // ListTile ink/background need a Material ancestor; the signup card
        // is a DecoratedBox, so give the checkbox its own transparent Material.
        color: Colors.transparent,
        child: CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: _isOver18,
          onChanged: (bool? value) => setState(() => _isOver18 = value ?? false),
          title: const Text('I confirm I am 18 or older'),
          controlAffinity: ListTileControlAffinity.leading,
        ),
      ),
      TurnstileChallenge(
        siteKey: _gtexTurnstileSiteKey,
        onTokenChanged: (String? token) {
          if (mounted) setState(() => _turnstileToken = token);
        },
      ),
    ],
  );
  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_isOver18) {
      setState(() => _error = 'Confirm you are 18 or older to continue.');
      return;
    }
    if (_gtexTurnstileSiteKey.isNotEmpty && _turnstileToken?.isNotEmpty != true) {
      setState(() => _error = 'Complete the security check to continue.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final GteAppConfig activeConfig = widget.config ??
          GteAppConfig(
            apiBaseUrl: widget.controller.api.config.baseUrl,
            backendMode: widget.controller.api.config.mode,
          );
      final client = GteExchangeApiClient.standard(
        baseUrl: activeConfig.apiBaseUrl,
        mode: activeConfig.backendMode,
      );
      final String dob =
          '$_birthYear-${_birthMonth.toString().padLeft(2, '0')}-${_birthDay.toString().padLeft(2, '0')}';
      final session = await client.signupUser(
        GteUserSignupRequest(
          fullName: _name.text.trim(),
          username: _username.text.trim(),
          email: _email.text.trim().isEmpty ? null : _email.text.trim(),
          password: _password.text,
          isOver18: _isOver18,
          dateOfBirth: dob,
          turnstileToken: _turnstileToken,
        ),
      );
      widget.controller.syncSession(session);
      if (mounted) context.go('/app/home');
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class GtexCreatorSignupScreen extends StatefulWidget {
  const GtexCreatorSignupScreen({
    super.key,
    required this.controller,
    required this.config,
  });
  final GteExchangeController controller;
  final GteAppConfig config;
  @override
  State<GtexCreatorSignupScreen> createState() =>
      _GtexCreatorSignupScreenState();
}

class _GtexCreatorSignupScreenState extends State<GtexCreatorSignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _country = TextEditingController(text: 'NG');
  final _club = TextEditingController();
  final _language = TextEditingController(text: 'English');
  final _clubName = TextEditingController();
  final _clubTag = TextEditingController();
  String _category = 'Football News';
  bool _submitting = false;
  String? _error;
  String? _turnstileToken;
  @override
  Widget build(BuildContext context) => _SignupScaffold(
    title: 'Creator',
    subtitle: 'Publish football stories. Grow a following. Build community.',
    icon: Icons.campaign_rounded,
    error: _error,
    submitting: _submitting,
    formKey: _formKey,
    onSubmit: _submit,
    children: <Widget>[
      _sectionLabel(context, '01', 'Creator profile'),
      _field(_name, 'Creator Name'),
      _field(_username, 'Username'),
      _field(_email, 'Email'),
      _field(_password, 'Password', obscure: true),
      _field(_country, 'Country'),
      _dropdown('Category', _category, const <String>[
        'Football News',
        'Match Reactions',
        'Tactical Analysis',
        'Comedy',
        'Watchalong',
        'Transfer News',
      ], (value) => setState(() => _category = value)),
      _field(_club, 'Main Club Supported'),
      _field(_language, 'Primary Language'),
      _sectionLabel(context, '02', 'Creator Club (Optional)'),
      _field(_clubName, 'Club Name (optional - start your club now)', required: false),
      _field(_clubTag, 'Club Short Tag (e.g. CFC)', required: false),
      _sectionLabel(context, '03', 'Monetization'),
      const Text(
        'Donations • Fan Coin Revenue • Paid Streams • Sponsorships',
        style: TextStyle(color: Color(0xFF93A0AA), fontSize: 12),
      ),
      const SizedBox(height: 8),
      TurnstileChallenge(
        siteKey: _gtexTurnstileSiteKey,
        onTokenChanged: (String? token) {
          if (mounted) setState(() => _turnstileToken = token);
        },
      ),
    ],
  );
  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_gtexTurnstileSiteKey.isNotEmpty && _turnstileToken?.isNotEmpty != true) {
      setState(() => _error = 'Complete the security check to continue.');
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
      final session = await client.signupCreator(
        GteCreatorSignupRequest(
          creatorName: _name.text,
          username: _username.text,
          email: _email.text,
          password: _password.text,
          country: _country.text,
          category: _category,
          mainClubSupported: _club.text,
          primaryLanguage: _language.text,
          clubName: _clubName.text.trim().isNotEmpty ? _clubName.text.trim() : null,
          clubShortTag: _clubTag.text.trim().isNotEmpty ? _clubTag.text.trim() : null,
          monetization: const <String>[
            'donations',
            'fan_coin_revenue',
            'paid_streams',
            'sponsorships',
          ],
          turnstileToken: _turnstileToken,
        ),
      );
      widget.controller.syncSession(session);
      if (mounted) context.go('/app/hub');
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class GtexTraderSignupScreen extends StatefulWidget {
  const GtexTraderSignupScreen({
    super.key,
    required this.controller,
    required this.config,
  });
  final GteExchangeController controller;
  final GteAppConfig config;
  @override
  State<GtexTraderSignupScreen> createState() => _GtexTraderSignupScreenState();
}

class _GtexTraderSignupScreenState extends State<GtexTraderSignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _alias = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _phone = TextEditingController();
  final _country = TextEditingController(text: 'NG');
  final _currency = TextEditingController(text: 'USD');
  final _totpCode = TextEditingController();
  String _experience = 'beginner';
  bool _submitting = false;
  String? _error;
  String? _turnstileToken;
  late final String _setupSecret = _generateTotpSetupSecret();
  @override
  Widget build(BuildContext context) => _SignupScaffold(
    title: 'Trader',
    subtitle:
        'Enter the GTEX economy with dedicated trading and wallet security.',
    icon: Icons.candlestick_chart_rounded,
    error: _error,
    submitting: _submitting,
    formKey: _formKey,
    onSubmit: _submit,
    children: <Widget>[
      _sectionLabel(context, '01', 'Account'),
      _field(_name, 'Full Name'),
      _field(_alias, 'Trading Alias'),
      _field(_email, 'Email'),
      _field(_password, 'Password', obscure: true),
      _field(_phone, 'Phone Number'),
      _field(_country, 'Country'),
      _sectionLabel(context, '02', 'Trading profile'),
      _field(_currency, 'Preferred Currency'),
      _dropdown(
        'Trading Experience',
        _experience,
        const <String>['beginner', 'intermediate', 'professional'],
        (value) => setState(() => _experience = value),
      ),
      _sectionLabel(context, '03', 'Wallet security'),
      SelectableText(
        'Authenticator setup secret: $_setupSecret',
        style: const TextStyle(color: Color(0xFF93A0AA), fontSize: 11),
      ),
      _field(_totpCode, '2FA Authenticator Code'),
      const SizedBox(height: 8),
      TurnstileChallenge(
        siteKey: _gtexTurnstileSiteKey,
        onTokenChanged: (String? token) {
          if (mounted) setState(() => _turnstileToken = token);
        },
      ),
    ],
  );
  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_gtexTurnstileSiteKey.isNotEmpty && _turnstileToken?.isNotEmpty != true) {
      setState(() => _error = 'Complete the security check to continue.');
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
      final session = await client.signupTrader(
        GteTraderSignupRequest(
          fullName: _name.text,
          tradingAlias: _alias.text,
          email: _email.text,
          password: _password.text,
          phoneNumber: _phone.text,
          country: _country.text,
          preferredCurrency: _currency.text,
          tradingExperience: _experience,
          interests: const <String>['GTEX Coin', 'Fan Coins', 'P2P'],
          totpSecret: _setupSecret,
          totpCode: _totpCode.text,
          recoveryPhraseHash: 'client-confirmed-recovery-phrase-hash',
          securityPinHash: 'client-confirmed-security-pin-hash',
          turnstileToken: _turnstileToken,
        ),
      );
      widget.controller.syncSession(session);
      if (mounted) context.go('/trader');
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
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
  bool required = true,
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
          required && (value == null || value.trim().isEmpty) ? '$label is required' : null,
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

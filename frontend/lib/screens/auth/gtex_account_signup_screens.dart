import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
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

Uint8List _decodeBase32Secret(String input) {
  const String alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  final List<int> bytes = <int>[];
  int buffer = 0;
  int bits = 0;
  for (final String character in input.replaceAll('=', '').toUpperCase().split('')) {
    final int value = alphabet.indexOf(character);
    if (value < 0) throw const FormatException('Invalid authenticator setup key.');
    buffer = (buffer << 5) | value;
    bits += 5;
    if (bits >= 8) {
      bits -= 8;
      bytes.add((buffer >> bits) & 0xff);
    }
  }
  return Uint8List.fromList(bytes);
}

bool _verifyTraderTotp(String secret, String code, {DateTime? now}) {
  final String candidate = code.trim();
  if (!RegExp(r'^\d{6}$').hasMatch(candidate)) return false;
  final Uint8List key = _decodeBase32Secret(secret);
  final int counter = (now ?? DateTime.now()).millisecondsSinceEpoch ~/ 30000;
  for (int drift = -1; drift <= 1; drift += 1) {
    final ByteData counterBytes = ByteData(8)..setUint64(0, counter + drift, Endian.big);
    final List<int> digest = crypto.Hmac(crypto.sha1, key)
        .convert(counterBytes.buffer.asUint8List())
        .bytes;
    final int offset = digest.last & 0x0f;
    final int binary = ((digest[offset] & 0x7f) << 24) |
        ((digest[offset + 1] & 0xff) << 16) |
        ((digest[offset + 2] & 0xff) << 8) |
        (digest[offset + 3] & 0xff);
    final String expected = (binary % 1000000).toString().padLeft(6, '0');
    if (expected == candidate) return true;
  }
  return false;
}

String _formatSignupApiError(Object error) {
  if (error is GteApiException) {
    final String message = error.message.trim();
    if (message.isNotEmpty && !message.startsWith('[')) {
      return message;
    }
    return 'Please check all highlighted details and try again.';
  }
  return AppFeedback.messageFor(error);
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
      setState(() => _error = _formatSignupApiError(error));
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
      setState(() => _error = _formatSignupApiError(error));
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
  final _currency = TextEditingController(text: 'NGN');
  final _totpCode = TextEditingController();
  final _walletLabel = TextEditingController(text: 'GTEX Trading Wallet');
  String _experience = 'beginner';
  bool _submitting = false;
  bool _totpVerified = false;
  String? _error;
  String? _turnstileToken;
  late final String _setupSecret = _generateTotpSetupSecret();

  @override
  void initState() {
    super.initState();
    _totpCode.addListener(_handleTotpCodeChanged);
  }

  void _handleTotpCodeChanged() {
    if (!mounted || (!_totpVerified && _error == null)) return;
    setState(() {
      _totpVerified = false;
      _error = null;
    });
  }

  @override
  void dispose() {
    _name.dispose();
    _alias.dispose();
    _email.dispose();
    _password.dispose();
    _phone.dispose();
    _country.dispose();
    _currency.dispose();
    _totpCode.removeListener(_handleTotpCodeChanged);
    _totpCode.dispose();
    _walletLabel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => _SignupScaffold(
    title: 'Trader',
    subtitle: 'Create your trading desk with a verified authenticator.',
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
      _sectionLabel(context, '03', 'Authenticator setup'),
      SelectableText(
        'GTEX setup key: $_setupSecret',
        style: const TextStyle(color: Color(0xFF93A0AA), fontSize: 11),
      ),
      _field(
        _totpCode,
        'Current 6-digit authenticator code',
        keyboardType: TextInputType.number,
        validator: (String? value) {
          return RegExp(r'^\d{6}$').hasMatch((value ?? '').trim())
              ? null
              : 'Enter the current 6-digit authenticator code';
        },
      ),
      OutlinedButton.icon(
        onPressed: _totpVerified || !RegExp(r'^\d{6}$').hasMatch(_totpCode.text.trim())
            ? null
            : _verifyAuthenticator,
        icon: Icon(_totpVerified ? Icons.verified_rounded : Icons.verified_user_outlined),
        label: Text(_totpVerified ? 'Authenticator verified' : 'Verify authenticator'),
      ),
      if (_totpVerified)
        const Text(
          'Authenticator verified. GTEX will check the code again during registration.',
          style: TextStyle(color: Color(0xFF36E38A), fontSize: 11),
        ),
      _field(_walletLabel, 'Wallet Label'),
      const SizedBox(height: 8),
      TurnstileChallenge(
        siteKey: _gtexTurnstileSiteKey,
        onTokenChanged: (String? token) {
          if (mounted) setState(() => _turnstileToken = token);
        },
      ),
    ],
  );

  void _verifyAuthenticator() {
    try {
      final bool valid = _verifyTraderTotp(_setupSecret, _totpCode.text.trim());
      setState(() {
        _totpVerified = valid;
        _error = valid
            ? null
            : 'That code does not match the GTEX setup key. Check your phone time and try the latest code.';
      });
    } catch (_) {
      setState(() {
        _totpVerified = false;
        _error = 'The authenticator code could not be checked. Review the setup key and try again.';
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_totpVerified) {
      setState(() => _error = 'Verify your authenticator code before creating your Coin Trader account.');
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
      final client = GteExchangeApiClient.standard(
        baseUrl: widget.config.apiBaseUrl,
        mode: widget.config.backendMode,
      );
      final session = await client.signupTrader(
        GteTraderSignupRequest(
          fullName: _name.text.trim(),
          tradingAlias: _alias.text.trim(),
          email: _email.text.trim(),
          password: _password.text,
          phoneNumber: _phone.text.trim(),
          country: _country.text.trim(),
          preferredCurrency: _currency.text.trim(),
          tradingExperience: _experience,
          interests: const <String>['GTEX Coin', 'Fan Coins', 'P2P'],
          walletLabel: _walletLabel.text.trim().isEmpty
              ? 'GTEX Trading Wallet'
              : _walletLabel.text.trim(),
          totpSecret: _setupSecret,
          totpCode: _totpCode.text.trim(),
          turnstileToken: _turnstileToken,
        ),
      );
      widget.controller.syncSession(session);
      if (mounted) context.go('/trader');
    } catch (error) {
      setState(() => _error = _formatSignupApiError(error));
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
  TextInputType? keyboardType,
  String? Function(String?)? validator,
}) => TextFormField(
  controller: controller,
  obscureText: obscure,
  keyboardType: keyboardType,
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
  validator: (String? value) {
    if (required && (value == null || value.trim().isEmpty)) {
      return '$label is required';
    }
    if (validator != null) {
      return validator(value);
    }
    return null;
  },
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
).hasMatch((value ?? '').trim())
              ? null
              : 'Enter the current 6-digit authenticator code';
        },
      ),
      OutlinedButton.icon(
        onPressed: _totpVerified ? null : _verifyAuthenticator,
        icon: Icon(_totpVerified ? Icons.verified_rounded : Icons.verified_user_outlined),
        label: Text(_totpVerified ? 'Authenticator verified' : 'Verify authenticator'),
      ),
      Text(
        'The code is checked here and verified again by GTEX when your account is created.',
        style: const TextStyle(color: Color(0xFF93A0AA), fontSize: 11, height: 1.4),
      ),
      _field(_walletLabel, 'Wallet Label'),
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
          walletLabel: _walletLabel.text.trim().isEmpty
              ? 'GTEX Trading Wallet'
              : _walletLabel.text.trim(),
          totpSecret: _setupSecret,
          totpCode: _totpCode.text.trim(),
          recoveryPhraseHash: _deriveTraderCredentialHash(
            'recovery',
            _recoveryPhrase.text.trim(),
          ),
          securityPinHash: _deriveTraderCredentialHash(
            'pin',
            _securityPin.text.trim(),
          ),
          turnstileToken: _turnstileToken,
        ),
      );
      widget.controller.syncSession(session);
      if (mounted) context.go('/trader');
    } catch (error) {
      setState(() => _error = _formatSignupApiError(error));
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
  TextInputType? keyboardType,
  String? Function(String?)? validator,
}) => TextFormField(
  controller: controller,
  obscureText: obscure,
  keyboardType: keyboardType,
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
  validator: (String? value) {
    if (required && (value == null || value.trim().isEmpty)) {
      return '$label is required';
    }
    if (validator != null) {
      return validator(value);
    }
    return null;
  },
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
).hasMatch(candidate)) return false;
  final Uint8List key = _decodeBase32Secret(secret);
  final int counter = (now ?? DateTime.now()).millisecondsSinceEpoch ~/ 30000;
  for (int drift = -1; drift <= 1; drift += 1) {
    final ByteData counterBytes = ByteData(8)..setUint64(0, counter + drift, Endian.big);
    final List<int> digest = crypto.Hmac(crypto.sha1, key)
        .convert(counterBytes.buffer.asUint8List())
        .bytes;
    final int offset = digest.last & 0x0f;
    final int binary = ((digest[offset] & 0x7f) << 24) |
        ((digest[offset + 1] & 0xff) << 16) |
        ((digest[offset + 2] & 0xff) << 8) |
        (digest[offset + 3] & 0xff);
    final String expected = (binary % 1000000).toString().padLeft(6, '0');
    if (expected == candidate) return true;
  }
  return false;
}

String _formatSignupApiError(Object error) {
  if (error is GteApiException) {
    final String message = error.message.trim();
    if (message.isNotEmpty && !message.startsWith('[')) {
      return message;
    }
    return 'Please check all highlighted details and try again.';
  }
  return AppFeedback.messageFor(error);
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
      setState(() => _error = _formatSignupApiError(error));
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
      setState(() => _error = _formatSignupApiError(error));
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
  final _recoveryPhrase = TextEditingController();
  final _securityPin = TextEditingController();
  final _walletLabel = TextEditingController(text: 'GTEX Trading Wallet');
  String _experience = 'beginner';
  bool _submitting = false;
  String? _error;
  String? _turnstileToken;
  late final String _setupSecret = _generateTotpSetupSecret();

  @override
  void dispose() {
    _name.dispose();
    _alias.dispose();
    _email.dispose();
    _password.dispose();
    _phone.dispose();
    _country.dispose();
    _currency.dispose();
    _totpCode.dispose();
    _recoveryPhrase.dispose();
    _securityPin.dispose();
    _walletLabel.dispose();
    super.dispose();
  }

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
      _field(
        _totpCode,
        '2FA Authenticator Code',
        keyboardType: TextInputType.number,
        validator: (String? value) {
          final String code = (value ?? '').trim();
          final bool validDigits = code.codeUnits.every(
            (int unit) => unit >= 48 && unit <= 57,
          );
          return code.length >= 6 && code.length <= 12 && validDigits
              ? null
              : 'Enter the current 6–12 digit authenticator code';
        },
      ),
      _field(
        _recoveryPhrase,
        'Recovery Phrase (at least 8 words)',
        obscure: true,
        validator: (String? value) {
          final List<String> words =
              (value ?? '').trim().split(RegExp(r'\s+'));
          return words.where((String word) => word.isNotEmpty).length >= 8
              ? null
              : 'Use a recovery phrase containing at least 8 words';
        },
      ),
      _field(
        _securityPin,
        'Security PIN (6–12 digits)',
        obscure: true,
        keyboardType: TextInputType.number,
        validator: (String? value) {
          final String pin = (value ?? '').trim();
          final bool validDigits = pin.codeUnits.every(
            (int unit) => unit >= 48 && unit <= 57,
          );
          return pin.length >= 6 && pin.length <= 12 && validDigits
              ? null
              : 'Use a security PIN containing 6–12 digits';
        },
      ),
      _field(_walletLabel, 'Wallet Label'),
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
          walletLabel: _walletLabel.text.trim().isEmpty
              ? 'GTEX Trading Wallet'
              : _walletLabel.text.trim(),
          totpSecret: _setupSecret,
          totpCode: _totpCode.text.trim(),
          recoveryPhraseHash: _deriveTraderCredentialHash(
            'recovery',
            _recoveryPhrase.text.trim(),
          ),
          securityPinHash: _deriveTraderCredentialHash(
            'pin',
            _securityPin.text.trim(),
          ),
          turnstileToken: _turnstileToken,
        ),
      );
      widget.controller.syncSession(session);
      if (mounted) context.go('/trader');
    } catch (error) {
      setState(() => _error = _formatSignupApiError(error));
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
  TextInputType? keyboardType,
  String? Function(String?)? validator,
}) => TextFormField(
  controller: controller,
  obscureText: obscure,
  keyboardType: keyboardType,
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
  validator: (String? value) {
    if (required && (value == null || value.trim().isEmpty)) {
      return '$label is required';
    }
    if (validator != null) {
      return validator(value);
    }
    return null;
  },
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

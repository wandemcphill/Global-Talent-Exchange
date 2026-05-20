import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class GtexAccountSelectorScreen extends StatelessWidget {
  const GtexAccountSelectorScreen({super.key, this.onOpenCreatorAccessRequest});

  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: gteBackdropDecoration(),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1180),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool narrow = constraints.maxWidth < 860;
                    final cards = <Widget>[
                      _AccountTypeCard(
                        icon: Icons.sports_soccer,
                        title: 'Football User',
                        body:
                            'Create clubs, scout players, build squads, and compete.',
                        accent: const Color(0xFF4BE4A6),
                        onTap: () => context.go('/auth/signup/user'),
                      ),
                      _AccountTypeCard(
                        icon: Icons.video_camera_front_outlined,
                        title: 'Creator',
                        body:
                            'Publish football content, grow communities, and monetize fans.',
                        accent: const Color(0xFFFFB85C),
                        onTap: () => context.go('/auth/signup/creator'),
                      ),
                      _AccountTypeCard(
                        icon: Icons.candlestick_chart_outlined,
                        title: 'Coin Trader',
                        body:
                            'Trade GTEX Coin and Fan Coins with dedicated security.',
                        accent: const Color(0xFF76A7FF),
                        onTap: () => context.go('/auth/signup/trader'),
                      ),
                    ];
                    return Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        Text(
                          'Choose your GTEX lane',
                          style: Theme.of(context).textTheme.displaySmall
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 18),
                        narrow
                            ? Column(
                              children:
                                  cards
                                      .map(
                                        (Widget child) => Padding(
                                          padding: const EdgeInsets.only(
                                            bottom: 14,
                                          ),
                                          child: child,
                                        ),
                                      )
                                      .toList(),
                            )
                            : Row(
                              children:
                                  cards
                                      .map(
                                        (Widget child) => Expanded(
                                          child: Padding(
                                            padding: const EdgeInsets.only(
                                              right: 14,
                                            ),
                                            child: child,
                                          ),
                                        ),
                                      )
                                      .toList(),
                            ),
                        if (onOpenCreatorAccessRequest != null) ...<Widget>[
                          const SizedBox(height: 18),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: OutlinedButton.icon(
                              onPressed: onOpenCreatorAccessRequest,
                              icon: const Icon(Icons.how_to_reg_outlined),
                              label: const Text('Apply for creator access'),
                            ),
                          ),
                        ],
                      ],
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

class GtexUserSignupScreen extends StatefulWidget {
  const GtexUserSignupScreen({
    super.key,
    required this.controller,
    required this.config,
  });

  final GteExchangeController controller;
  final GteAppConfig config;

  @override
  State<GtexUserSignupScreen> createState() => _GtexUserSignupScreenState();
}

class _GtexUserSignupScreenState extends State<GtexUserSignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _country = TextEditingController(text: 'NG');
  final _state = TextEditingController();
  final _city = TextEditingController();
  final _clubName = TextEditingController();
  final _clubTag = TextEditingController();
  final _clubState = TextEditingController();
  final _clubLocality = TextEditingController();
  final _position = TextEditingController(text: 'CM');
  final _dominantFoot = TextEditingController(text: 'Right');
  final _height = TextEditingController(text: '178');
  final _jersey = TextEditingController(text: '8');
  final _preferredRole = TextEditingController(text: 'Box-to-box midfielder');
  final _govId = TextEditingController();
  final _selfie = TextEditingController();
  String _clubType = 'academy';
  String _footballIdentity = 'club_owner';
  bool _submitting = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    return _SignupScaffold(
      title: 'Football User signup',
      icon: Icons.sports_soccer,
      error: _error,
      submitting: _submitting,
      formKey: _formKey,
      onSubmit: _submit,
      children: <Widget>[
        _sectionLabel(context, 'Step 1', 'Personal identity'),
        _field(_name, 'Full Name'),
        _field(_username, 'Username'),
        _field(_email, 'Email'),
        _field(_password, 'Password', obscure: true),
        _field(_country, 'Country'),
        _field(_state, 'State'),
        _field(_city, 'City'),
        _sectionLabel(context, 'Step 2', 'Club creation'),
        _field(_clubName, 'Club Name'),
        _field(_clubTag, 'Club Short Tag'),
        _field(_clubState, 'Club State'),
        _field(_clubLocality, 'Club Locality'),
        _dropdown('Club Type', _clubType, const <String>[
          'academy',
          'professional',
          'community',
          'street_team',
        ], (value) => setState(() => _clubType = value)),
        _sectionLabel(context, 'Step 3', 'Football identity'),
        _dropdown(
          'Football Identity',
          _footballIdentity,
          const <String>['club_owner', 'player', 'both'],
          (value) => setState(() => _footballIdentity = value),
        ),
        if (_footballIdentity == 'player' ||
            _footballIdentity == 'both') ...<Widget>[
          _field(_position, 'Position'),
          _field(_dominantFoot, 'Dominant Foot'),
          _field(_height, 'Height'),
          _field(_jersey, 'Jersey Number'),
          _field(_preferredRole, 'Preferred Role'),
        ],
        _sectionLabel(context, 'Step 4', 'Compliance'),
        _field(_govId, 'Government ID Attachment ID'),
        _field(_selfie, 'Selfie Verification Attachment ID'),
      ],
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
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
          fullName: _name.text,
          username: _username.text,
          email: _email.text,
          password: _password.text,
          country: _country.text,
          state: _state.text,
          city: _city.text,
          clubName: _clubName.text,
          clubShortTag: _clubTag.text,
          clubCountry: _country.text,
          clubState: _clubState.text,
          clubLocality: _clubLocality.text,
          clubType: _clubType,
          footballIdentity: _footballIdentity,
          position:
              _footballIdentity == 'player' || _footballIdentity == 'both'
                  ? _position.text
                  : null,
          dominantFoot:
              _footballIdentity == 'player' || _footballIdentity == 'both'
                  ? _dominantFoot.text
                  : null,
          heightCm:
              _footballIdentity == 'player' || _footballIdentity == 'both'
                  ? int.tryParse(_height.text)
                  : null,
          jerseyNumber:
              _footballIdentity == 'player' || _footballIdentity == 'both'
                  ? int.tryParse(_jersey.text)
                  : null,
          preferredRole:
              _footballIdentity == 'player' || _footballIdentity == 'both'
                  ? _preferredRole.text
                  : null,
          compliance: GteComplianceSignupPayload(
            governmentIdAttachmentId: _govId.text,
            selfieAttachmentId: _selfie.text,
            countryConfirmation: _country.text,
          ),
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
  String _category = 'Football News';
  bool _submitting = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    return _SignupScaffold(
      title: 'Creator signup',
      icon: Icons.video_camera_front_outlined,
      error: _error,
      submitting: _submitting,
      formKey: _formKey,
      onSubmit: _submit,
      children: <Widget>[
        _sectionLabel(context, 'Creator profile', 'Public creator identity'),
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
        _sectionLabel(
          context,
          'Monetization',
          'Donations, Fan Coin Revenue, Paid Streams, Sponsorships',
        ),
      ],
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
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
          monetization: const <String>[
            'donations',
            'fan_coin_revenue',
            'paid_streams',
            'sponsorships',
          ],
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
  final _govId = TextEditingController();
  final _selfie = TextEditingController();
  final _address = TextEditingController();
  String _experience = 'beginner';
  bool _submitting = false;
  String? _error;
  static const String _setupSecret = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP';

  @override
  Widget build(BuildContext context) {
    return _SignupScaffold(
      title: 'Coin Trader signup',
      icon: Icons.candlestick_chart_outlined,
      error: _error,
      submitting: _submitting,
      formKey: _formKey,
      onSubmit: _submit,
      children: <Widget>[
        _sectionLabel(context, 'Step 1', 'Account'),
        _field(_name, 'Full Name'),
        _field(_alias, 'Trading Alias'),
        _field(_email, 'Email'),
        _field(_password, 'Password', obscure: true),
        _field(_phone, 'Phone Number'),
        _field(_country, 'Country'),
        _sectionLabel(context, 'Step 2', 'Trading profile'),
        _field(_currency, 'Preferred Currency'),
        _dropdown(
          'Trading Experience',
          _experience,
          const <String>['beginner', 'intermediate', 'professional'],
          (value) => setState(() => _experience = value),
        ),
        _sectionLabel(context, 'Step 3', 'Wallet security'),
        SelectableText('Authenticator setup secret: $_setupSecret'),
        _field(_totpCode, '2FA Authenticator Code'),
        _sectionLabel(context, 'Step 4', 'KYC'),
        _field(_govId, 'Government ID Attachment ID'),
        _field(_selfie, 'Selfie Attachment ID'),
        _field(_address, 'Proof of Address Attachment ID'),
      ],
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
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
          compliance: GteComplianceSignupPayload(
            governmentIdAttachmentId: _govId.text,
            selfieAttachmentId: _selfie.text,
            proofOfAddressAttachmentId: _address.text,
            countryConfirmation: _country.text,
          ),
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
    required this.icon,
    required this.error,
    required this.submitting,
    required this.formKey,
    required this.onSubmit,
    required this.children,
  });

  final String title;
  final IconData icon;
  final String? error;
  final bool submitting;
  final GlobalKey<FormState> formKey;
  final VoidCallback onSubmit;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: gteBackdropDecoration(),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Form(
                key: formKey,
                child: ListView(
                  padding: const EdgeInsets.all(24),
                  children: <Widget>[
                    Icon(icon, size: 48),
                    const SizedBox(height: 12),
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineMedium
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    if (error != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 12),
                        child: Text(
                          error!,
                          style: const TextStyle(color: Colors.redAccent),
                        ),
                      ),
                    const SizedBox(height: 18),
                    ...children.map(
                      (Widget child) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: child,
                      ),
                    ),
                    FilledButton.icon(
                      onPressed: submitting ? null : onSubmit,
                      icon:
                          submitting
                              ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                              : const Icon(Icons.arrow_forward),
                      label: Text(
                        submitting ? 'Creating account' : 'Create account',
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

class _AccountTypeCard extends StatelessWidget {
  const _AccountTypeCard({
    required this.icon,
    required this.title,
    required this.body,
    required this.accent,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String body;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        constraints: const BoxConstraints(minHeight: 220),
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: accent.withValues(alpha: 0.45)),
          boxShadow: <BoxShadow>[
            BoxShadow(color: accent.withValues(alpha: 0.18), blurRadius: 28),
          ],
          color: const Color(0xFF101820).withValues(alpha: 0.78),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, color: accent, size: 36),
            const SizedBox(height: 34),
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            Text(body),
            const SizedBox(height: 16),
            FilledButton(onPressed: onTap, child: const Text('Continue')),
          ],
        ),
      ),
    );
  }
}

Widget _field(
  TextEditingController controller,
  String label, {
  bool obscure = false,
}) {
  return TextFormField(
    controller: controller,
    obscureText: obscure,
    decoration: InputDecoration(
      labelText: label,
      border: const OutlineInputBorder(),
    ),
    validator:
        (String? value) =>
            (value == null || value.trim().isEmpty)
                ? '$label is required'
                : null,
  );
}

Widget _sectionLabel(BuildContext context, String label, String title) {
  return Padding(
    padding: const EdgeInsets.only(top: 10, bottom: 2),
    child: Row(
      children: <Widget>[
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: GteShellTheme.accent,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
        ),
      ],
    ),
  );
}

Widget _dropdown(
  String label,
  String value,
  List<String> options,
  ValueChanged<String> onChanged,
) {
  return DropdownButtonFormField<String>(
    value: value,
    decoration: InputDecoration(
      labelText: label,
      border: const OutlineInputBorder(),
    ),
    items:
        options
            .map(
              (String item) =>
                  DropdownMenuItem<String>(value: item, child: Text(item)),
            )
            .toList(),
    onChanged: (String? next) {
      if (next != null) onChanged(next);
    },
  );
}

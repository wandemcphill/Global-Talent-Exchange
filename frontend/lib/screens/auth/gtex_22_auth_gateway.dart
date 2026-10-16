import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';

class Gtex22AuthGateway extends StatelessWidget {
  const Gtex22AuthGateway({super.key, this.onLogin});
  final VoidCallback? onLogin;

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 820;
    final roles = <_Role>[
      const _Role(
        'PLAYER / CLUB',
        'Build your football identity, discover talent, manage squads and compete.',
        Icons.sports_soccer_rounded,
        GtexFloodlit.pitch,
        '/auth/signup/user',
      ),
      const _Role(
        'CREATOR',
        'Publish football stories, grow a following and build your community.',
        Icons.campaign_rounded,
        GtexFloodlit.scoreboard,
        '/auth/signup/creator',
      ),
      const _Role(
        'TRADER',
        'Access the GTEX economy with dedicated trading and wallet security.',
        Icons.candlestick_chart_rounded,
        GtexFloodlit.gold,
        '/auth/signup/trader',
      ),
    ];
    return Scaffold(
      backgroundColor: GtexFloodlit.night,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(narrow ? 20 : 42),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1160),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      SvgPicture.asset(
                        'assets/branding/gtex_wordmark_22.svg',
                        width: 170,
                        height: 40,
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: onLogin,
                        icon: const Icon(Icons.login_rounded, size: 17),
                        label: const Text('Already have an account? Sign in'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 55),
                  const Text(
                    'ENTER THE\nFOOTBALL WORLD.',
                    style: TextStyle(
                      fontFamily: 'BarlowCondensed',
                      color: GtexFloodlit.chalk,
                      fontSize: 68,
                      height: .84,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -1.5,
                    ),
                  ),
                  const SizedBox(height: 16),
                  const SizedBox(
                    width: 660,
                    child: Text(
                      'One account opens a living football ecosystem of talent, clubs, markets, matches and community. Pick the way you want to play.',
                      style: TextStyle(
                        color: GtexFloodlit.chalkMuted,
                        fontSize: 16,
                        height: 1.55,
                      ),
                    ),
                  ),
                  const SizedBox(height: 34),
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
                          childAspectRatio: columns == 1 ? 2.5 : 1.2,
                        ),
                        itemBuilder: (_, i) => _RoleCard(role: roles[i]),
                      );
                    },
                  ),
                  const SizedBox(height: 30),
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: GtexFloodlit.card,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: GtexFloodlit.line),
                    ),
                    child: const Row(
                      children: <Widget>[
                        Icon(
                          Icons.verified_user_rounded,
                          color: GtexFloodlit.pitch,
                          size: 20,
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Secure identity, protected account sessions and role-aware onboarding. KYC is requested where the platform actually needs it.',
                            style: TextStyle(
                              color: GtexFloodlit.chalkMuted,
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

class _Role {
  const _Role(this.title, this.body, this.icon, this.accent, this.route);
  final String title, body, route;
  final IconData icon;
  final Color accent;
}

class _RoleCard extends StatelessWidget {
  const _RoleCard({required this.role});
  final _Role role;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: () => context.go(role.route),
    borderRadius: BorderRadius.circular(20),
    child: Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: GtexFloodlit.card,
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
              color: GtexFloodlit.chalk,
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
                  color: GtexFloodlit.chalkMuted,
                  fontFamily: 'DMMono',
                  fontSize: 9,
                  letterSpacing: 1,
                ),
              ),
              Spacer(),
              Icon(
                Icons.arrow_forward_rounded,
                color: GtexFloodlit.chalkMuted,
                size: 17,
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class Gtex22LoginScreen extends StatefulWidget {
  const Gtex22LoginScreen({super.key, required this.controller, this.onSignup});
  final GteExchangeController controller;
  final VoidCallback? onSignup;
  @override
  State<Gtex22LoginScreen> createState() => _Gtex22LoginScreenState();
}

class _Gtex22LoginScreenState extends State<Gtex22LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  bool _busy = false;
  String? _error;
  bool _obscure = true;
  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.controller.signIn(
        email: _email.text.trim(),
        password: _password.text,
      );
      if (mounted && widget.controller.isAuthenticated) context.go('/app/home');
    } catch (e) {
      if (mounted) {
        final bool invalidCredentials =
            e is GteApiException &&
            (e.type == GteApiErrorType.unauthorized || e.statusCode == 401);
        setState(
          () => _error = invalidCredentials
              ? 'Email or password is incorrect.'
              : AppFeedback.messageFor(e),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: GtexFloodlit.night,
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1040),
            child: LayoutBuilder(
              builder: (_, c) {
                final narrow = c.maxWidth < 780;
                final form = _form(context);
                final story = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: const <Widget>[
                    _Eyebrow(text: 'WELCOME BACK TO GTEX'),
                    SizedBox(height: 18),
                    Text(
                      'THE WORLD\nIS STILL MOVING.',
                      style: TextStyle(
                        fontFamily: 'BarlowCondensed',
                        color: GtexFloodlit.chalk,
                        fontSize: 62,
                        height: .84,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    SizedBox(height: 16),
                    Text(
                      'Pick up where you left off. Your club, talent watchlist, market activity, matches and community are waiting.',
                      style: TextStyle(
                        color: GtexFloodlit.chalkMuted,
                        fontSize: 15,
                        height: 1.5,
                      ),
                    ),
                    SizedBox(height: 28),
                    _TinyStat('LIVE WORLD', 'MATCHES • MARKET • NEWS'),
                    _TinyStat(
                      'YOUR IDENTITY',
                      'CLUB • PLAYER • CREATOR • TRADER',
                    ),
                  ],
                );
                return narrow
                    ? Column(
                      children: <Widget>[
                        story,
                        const SizedBox(height: 34),
                        form,
                      ],
                    )
                    : Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: <Widget>[
                        Expanded(child: story),
                        const SizedBox(width: 70),
                        SizedBox(width: 390, child: form),
                      ],
                    );
              },
            ),
          ),
        ),
      ),
    ),
  );
  Widget _form(BuildContext context) => Container(
    padding: const EdgeInsets.all(26),
    decoration: BoxDecoration(
      color: GtexFloodlit.card,
      borderRadius: BorderRadius.circular(22),
      border: Border.all(color: GtexFloodlit.line),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        SvgPicture.asset(
          'assets/branding/gtex_mark_22.svg',
          width: 48,
          height: 48,
          alignment: Alignment.centerLeft,
        ),
        const SizedBox(height: 20),
        const Text(
          'Sign in',
          style: TextStyle(
            fontFamily: 'BarlowCondensed',
            color: GtexFloodlit.chalk,
            fontSize: 34,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 5),
        const Text(
          'Continue your football world.',
          style: TextStyle(color: GtexFloodlit.chalkMuted, fontSize: 12),
        ),
        const SizedBox(height: 22),
        Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _field(_email, 'Email', Icons.mail_outline_rounded),
              const SizedBox(height: 11),
              _passwordField(),
            ],
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(
              _error!,
              style: const TextStyle(
                color: GtexFloodlit.scoreboard,
                fontSize: 11,
              ),
            ),
          ),
        const SizedBox(height: 18),
        FilledButton(
          onPressed: _busy ? null : _submit,
          style: FilledButton.styleFrom(
            backgroundColor: GtexFloodlit.pitch,
            foregroundColor: GtexFloodlit.night,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
          ),
          child:
              _busy
                  ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                  : const Text(
                    'ENTER GTEX',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 12,
                      letterSpacing: .8,
                    ),
                  ),
        ),
        const SizedBox(height: 16),
        Row(
          children: const <Widget>[
            Expanded(child: Divider(color: GtexFloodlit.line)),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 10),
              child: Text(
                'OR',
                style: TextStyle(
                  color: GtexFloodlit.chalkMuted,
                  fontFamily: 'DMMono',
                  fontSize: 9,
                ),
              ),
            ),
            Expanded(child: Divider(color: GtexFloodlit.line)),
          ],
        ),
        const SizedBox(height: 14),
        OutlinedButton(
          onPressed: widget.onSignup ?? () => context.go('/auth'),
          style: OutlinedButton.styleFrom(
            foregroundColor: GtexFloodlit.chalk,
            side: const BorderSide(color: GtexFloodlit.line),
            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
          child: const Text(
            'CREATE A GTEX ID',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11),
          ),
        ),
      ],
    ),
  );
  Widget _field(TextEditingController c, String label, IconData icon) =>
      TextFormField(
        controller: c,
        keyboardType: TextInputType.emailAddress,
        style: const TextStyle(color: GtexFloodlit.chalk, fontSize: 13),
        decoration: _decoration(label, icon),
        validator: (String? value) {
          final String email = value?.trim() ?? '';
          if (email.isEmpty) {
            return 'Enter your email address.';
          }
          if (!email.contains('@')) {
            return 'Enter a valid email address.';
          }
          return null;
        },
      );
  Widget _passwordField() => TextFormField(
    controller: _password,
    obscureText: _obscure,
    style: const TextStyle(color: GtexFloodlit.chalk, fontSize: 13),
    decoration: _decoration('Password', Icons.lock_outline_rounded).copyWith(
      suffixIcon: IconButton(
        onPressed: () => setState(() => _obscure = !_obscure),
        icon: Icon(
          _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
          color: GtexFloodlit.chalkMuted,
          size: 18,
        ),
      ),
    ),
    validator: (String? value) {
      final String password = value ?? '';
      if (password.isEmpty) {
        return 'Enter your password.';
      }
      if (password.length < 8) {
        return 'Password must be at least 8 characters.';
      }
      return null;
    },
  );
  InputDecoration _decoration(String label, IconData icon) => InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(color: GtexFloodlit.chalkMuted, fontSize: 12),
    prefixIcon: Icon(icon, color: GtexFloodlit.chalkMuted, size: 18),
    filled: true,
    fillColor: GtexFloodlit.night,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: GtexFloodlit.line),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: GtexFloodlit.line),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: GtexFloodlit.pitch),
    ),
  );
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      Container(
        width: 6,
        height: 6,
        decoration: const BoxDecoration(
          color: GtexFloodlit.pitch,
          shape: BoxShape.circle,
        ),
      ),
      const SizedBox(width: 8),
      Text(
        text,
        style: const TextStyle(
          fontFamily: 'DMMono',
          color: GtexFloodlit.pitch,
          fontSize: 10,
          letterSpacing: 1.6,
        ),
      ),
    ],
  );
}

class _TinyStat extends StatelessWidget {
  const _TinyStat(this.a, this.b);
  final String a, b;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Row(
      children: <Widget>[
        Text(
          a,
          style: const TextStyle(
            fontFamily: 'DMMono',
            color: GtexFloodlit.chalk,
            fontSize: 9,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(width: 10),
        Text(
          b,
          style: const TextStyle(color: GtexFloodlit.chalkMuted, fontSize: 11),
        ),
      ],
    ),
  );
}

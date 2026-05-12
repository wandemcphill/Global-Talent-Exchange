import 'package:flutter/material.dart';

import '../../ui_gtex/components/gtex_button.dart';
import '../../ui_gtex/components/gtex_card.dart';
import '../../ui_gtex/theme/gtex_colors.dart';

enum GtexAuthMode { login, userSignup, creatorSignup }

class GtexAuthShellV2 extends StatefulWidget {
  const GtexAuthShellV2({
    super.key,
    required this.mode,
    this.onSubmit,
    this.onSwitchToLogin,
    this.onSwitchToSignup,
    this.onCreatorSignup,
  });

  final GtexAuthMode mode;
  final Future<void> Function(Map<String, String> values)? onSubmit;
  final VoidCallback? onSwitchToLogin;
  final VoidCallback? onSwitchToSignup;
  final VoidCallback? onCreatorSignup;

  @override
  State<GtexAuthShellV2> createState() => _GtexAuthShellV2State();
}

class _GtexAuthShellV2State extends State<GtexAuthShellV2> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _clubOrBrand = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    _clubOrBrand.dispose();
    super.dispose();
  }

  bool get _isLogin => widget.mode == GtexAuthMode.login;
  bool get _isCreator => widget.mode == GtexAuthMode.creatorSignup;

  @override
  Widget build(BuildContext context) {
    final title = switch (widget.mode) {
      GtexAuthMode.login => 'Welcome back to GTEX',
      GtexAuthMode.userSignup => 'Create your GTEX account',
      GtexAuthMode.creatorSignup => 'Apply as a GTEX creator',
    };
    final subtitle = switch (widget.mode) {
      GtexAuthMode.login => 'Return to your club, market, wallet and football universe.',
      GtexAuthMode.userSignup => 'Start with a club path, player shortlist, and region setup.',
      GtexAuthMode.creatorSignup => 'Host competitions, grow your audience and monetize football activity.',
    };

    return Scaffold(
      backgroundColor: GtexColors.black,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1080),
              child: LayoutBuilder(builder: (context, constraints) {
                final form = _AuthForm(
                  formKey: _formKey,
                  title: title,
                  subtitle: subtitle,
                  isLogin: _isLogin,
                  isCreator: _isCreator,
                  name: _name,
                  email: _email,
                  password: _password,
                  clubOrBrand: _clubOrBrand,
                  submitting: _submitting,
                  onSubmit: _handleSubmit,
                  onSwitchToLogin: widget.onSwitchToLogin,
                  onSwitchToSignup: widget.onSwitchToSignup,
                  onCreatorSignup: widget.onCreatorSignup,
                );
                if (constraints.maxWidth < 850) return form;
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const Expanded(child: _AuthStoryPanel()),
                    const SizedBox(width: 24),
                    Expanded(child: form),
                  ],
                );
              }),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    try {
      await widget.onSubmit?.call({
        'name': _name.text.trim(),
        'email': _email.text.trim(),
        'password': _password.text,
        'clubOrBrand': _clubOrBrand.text.trim(),
        'mode': widget.mode.name,
      });
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class _AuthForm extends StatelessWidget {
  const _AuthForm({
    required this.formKey,
    required this.title,
    required this.subtitle,
    required this.isLogin,
    required this.isCreator,
    required this.name,
    required this.email,
    required this.password,
    required this.clubOrBrand,
    required this.submitting,
    required this.onSubmit,
    this.onSwitchToLogin,
    this.onSwitchToSignup,
    this.onCreatorSignup,
  });

  final GlobalKey<FormState> formKey;
  final String title;
  final String subtitle;
  final bool isLogin;
  final bool isCreator;
  final TextEditingController name;
  final TextEditingController email;
  final TextEditingController password;
  final TextEditingController clubOrBrand;
  final bool submitting;
  final VoidCallback onSubmit;
  final VoidCallback? onSwitchToLogin;
  final VoidCallback? onSwitchToSignup;
  final VoidCallback? onCreatorSignup;

  @override
  Widget build(BuildContext context) {
    return GtexCard(
      padding: const EdgeInsets.all(24),
      child: Form(
        key: formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900)),
            const SizedBox(height: 10),
            Text(subtitle, style: const TextStyle(color: GtexColors.textSecondary, height: 1.4)),
            const SizedBox(height: 24),
            if (!isLogin) ...[
              _Field(label: 'Full name', controller: name, icon: Icons.person_outline),
              const SizedBox(height: 14),
              _Field(label: isCreator ? 'Creator brand / channel name' : 'Proposed club name', controller: clubOrBrand, icon: Icons.shield_outlined),
              const SizedBox(height: 14),
            ],
            _Field(label: 'Email address', controller: email, icon: Icons.email_outlined, keyboardType: TextInputType.emailAddress),
            const SizedBox(height: 14),
            _Field(label: 'Password', controller: password, icon: Icons.lock_outline, obscure: true),
            const SizedBox(height: 22),
            SizedBox(
              width: double.infinity,
              child: GtexButton(
                label: submitting ? 'Please wait...' : (isLogin ? 'Login' : isCreator ? 'Submit creator application' : 'Create account'),
                onPressed: submitting ? null : onSubmit,
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(isLogin ? 'New to GTEX?' : 'Already have an account?', style: const TextStyle(color: GtexColors.textMuted)),
                TextButton(onPressed: isLogin ? onSwitchToSignup : onSwitchToLogin, child: Text(isLogin ? 'Create account' : 'Login')),
                if (!isCreator && !isLogin) TextButton(onPressed: onCreatorSignup, child: const Text('Creator signup')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.controller, required this.icon, this.obscure = false, this.keyboardType});

  final String label;
  final TextEditingController controller;
  final IconData icon;
  final bool obscure;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboardType,
      style: const TextStyle(color: Colors.white),
      validator: (value) {
        if (value == null || value.trim().isEmpty) return '$label is required';
        if (keyboardType == TextInputType.emailAddress && !value.contains('@')) return 'Enter a valid email';
        if (obscure && value.length < 6) return 'Use at least 6 characters';
        return null;
      },
      decoration: InputDecoration(
        prefixIcon: Icon(icon, color: GtexColors.green),
        labelText: label,
        labelStyle: const TextStyle(color: GtexColors.textMuted),
        filled: true,
        fillColor: Colors.white.withOpacity(.045),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: Colors.white.withOpacity(.1))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: Colors.white.withOpacity(.1))),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: GtexColors.green)),
      ),
    );
  }
}

class _AuthStoryPanel extends StatelessWidget {
  const _AuthStoryPanel();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Build a football institution, not just an account.', style: TextStyle(color: Colors.white, fontSize: 36, height: 1.08, fontWeight: FontWeight.w900)),
        const SizedBox(height: 18),
        const Text('Your first GTEX session should guide you from signup to club creation, region selection, player shortlist, KYC and first competition.', style: TextStyle(color: GtexColors.textSecondary, height: 1.45, fontSize: 16)),
        const SizedBox(height: 22),
        ...['Create or join a club', 'Browse players by real football hierarchy', 'Shortlist players with visible total cost', 'Enter tournaments and follow the AI news cycle'].map((text) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(children: [
                const Icon(Icons.check_circle, color: GtexColors.green, size: 20),
                const SizedBox(width: 10),
                Expanded(child: Text(text, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700))),
              ]),
            )),
      ],
    );
  }
}

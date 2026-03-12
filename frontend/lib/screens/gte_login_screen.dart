import 'package:flutter/material.dart';

import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';

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
        appBar: AppBar(
          title: const Text('Sign in'),
        ),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: AnimatedBuilder(
                animation: widget.controller,
                builder: (BuildContext context, Widget? child) {
                  if (widget.controller.isAuthenticated) {
                    return GteStatePanel(
                      title: 'Signed in',
                      message:
                          'Active session for ${widget.controller.session!.user.username}. You can close this screen and continue trading.',
                      actionLabel: 'Back to trading',
                      onAction: () {
                        Navigator.of(context).pop(true);
                      },
                      icon: Icons.verified_user_outlined,
                    );
                  }

                  return GteSurfacePanel(
                    emphasized: true,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Demo login',
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        Text(
                          'Uses `POST /auth/login` and keeps the bearer token in the reusable client layer.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Demo credentials are prefilled so QA can move directly into the market flow.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 20),
                        TextField(
                          controller: _emailController,
                          enabled: !widget.controller.isSigningIn,
                          keyboardType: TextInputType.emailAddress,
                          textInputAction: TextInputAction.next,
                          decoration: const InputDecoration(labelText: 'Email'),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _passwordController,
                          enabled: !widget.controller.isSigningIn,
                          obscureText: true,
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _submit(),
                          decoration:
                              const InputDecoration(labelText: 'Password'),
                        ),
                        if (widget.controller.isSigningIn) ...<Widget>[
                          const SizedBox(height: 16),
                          const LinearProgressIndicator(),
                        ],
                        if (widget.controller.authError != null) ...<Widget>[
                          const SizedBox(height: 12),
                          Text(
                            widget.controller.authError!,
                            style: TextStyle(
                                color: Theme.of(context).colorScheme.error),
                          ),
                        ],
                        const SizedBox(height: 20),
                        Row(
                          children: <Widget>[
                            Expanded(
                              child: OutlinedButton(
                                onPressed: widget.controller.isSigningIn
                                    ? null
                                    : () {
                                        _emailController.text =
                                            'fan@demo.gte.local';
                                        _passwordController.text =
                                            'DemoPass123';
                                      },
                                child: const Text('Use demo creds'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: FilledButton(
                                onPressed: widget.controller.isSigningIn
                                    ? null
                                    : () {
                                        _submit();
                                      },
                                child: Text(
                                  widget.controller.isSigningIn
                                      ? 'Signing in...'
                                      : 'Sign in',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  );
                },
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

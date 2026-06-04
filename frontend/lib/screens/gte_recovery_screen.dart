import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';

class GteRecoveryScreen extends StatefulWidget {
  const GteRecoveryScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteRecoveryScreen> createState() => _GteRecoveryScreenState();
}

class _GteRecoveryScreenState extends State<GteRecoveryScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _answerOneController = TextEditingController();
  final TextEditingController _answerTwoController = TextEditingController();
  final TextEditingController _pinController = TextEditingController();
  final TextEditingController _newPasswordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  GteRecoveryChallenge? _challenge;
  bool _isLoading = false;
  bool _completed = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _answerOneController.dispose();
    _answerTwoController.dispose();
    _pinController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          title: const Text('Account recovery'),
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: GteSurfacePanel(
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      Text(
                        _completed ? 'Password reset' : 'Recover your account',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 16),
                      if (_completed)
                        FilledButton.icon(
                          onPressed: () => Navigator.of(context).pop(),
                          icon: const Icon(Icons.login),
                          label: const Text('Return to sign in'),
                        )
                      else ...<Widget>[
                        TextField(
                          controller: _emailController,
                          enabled: !_isLoading && _challenge == null,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            labelText: 'Email',
                            prefixIcon: Icon(Icons.alternate_email),
                          ),
                        ),
                        if (_challenge == null) ...<Widget>[
                          const SizedBox(height: 18),
                          FilledButton.icon(
                            onPressed: _isLoading ? null : _requestChallenge,
                            icon: const Icon(Icons.security),
                            label: Text(
                              _isLoading
                                  ? 'Checking account...'
                                  : 'Continue recovery',
                            ),
                          ),
                        ] else ...<Widget>[
                          const SizedBox(height: 18),
                          _RecoveryAnswerField(
                            controller: _answerOneController,
                            question: _challenge!.questions[0].question,
                          ),
                          const SizedBox(height: 14),
                          _RecoveryAnswerField(
                            controller: _answerTwoController,
                            question: _challenge!.questions[1].question,
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _pinController,
                            enabled: !_isLoading,
                            keyboardType: TextInputType.number,
                            obscureText: true,
                            maxLength: 4,
                            inputFormatters: <TextInputFormatter>[
                              FilteringTextInputFormatter.digitsOnly,
                            ],
                            decoration: const InputDecoration(
                              counterText: '',
                              labelText: 'Security PIN',
                              prefixIcon: Icon(Icons.pin_outlined),
                            ),
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _newPasswordController,
                            enabled: !_isLoading,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'New password',
                              prefixIcon: Icon(Icons.lock_reset),
                            ),
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _confirmPasswordController,
                            enabled: !_isLoading,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'Confirm new password',
                              prefixIcon: Icon(Icons.lock_outline),
                            ),
                          ),
                          const SizedBox(height: 18),
                          FilledButton.icon(
                            onPressed: _isLoading ? null : _resetPassword,
                            icon: const Icon(Icons.verified_user_outlined),
                            label: Text(
                              _isLoading ? 'Resetting...' : 'Reset password',
                            ),
                          ),
                        ],
                        if (_error != null) ...<Widget>[
                          const SizedBox(height: 14),
                          Text(
                            _error!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                            ),
                          ),
                        ],
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _requestChallenge() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final GteRecoveryChallenge challenge = await widget.controller.api
          .requestRecoveryChallenge(_emailController.text.trim());
      if (!mounted) {
        return;
      }
      if (challenge.questions.length != 2) {
        setState(() {
          _error = 'Account recovery could not be started.';
        });
        return;
      }
      setState(() {
        _challenge = challenge;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = 'Account recovery could not be started.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _resetPassword() async {
    final GteRecoveryChallenge? challenge = _challenge;
    if (challenge == null || challenge.questions.length != 2) {
      return;
    }
    final String pin = _pinController.text.trim();
    final String newPassword = _newPasswordController.text;
    final String confirmPassword = _confirmPasswordController.text;
    if (!RegExp(r'^\d{4}$').hasMatch(pin)) {
      setState(() {
        _error = 'Enter your 4-digit security PIN.';
      });
      return;
    }
    if (newPassword.length < 8) {
      setState(() {
        _error = 'Use at least 8 characters for the new password.';
      });
      return;
    }
    if (newPassword != confirmPassword) {
      setState(() {
        _error = 'New password confirmation does not match.';
      });
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await widget.controller.api.resetPasswordWithRecoveryQuestions(
        GteRecoveryQuestionResetRequest(
          email: challenge.email,
          answers: <GteRecoveryAnswerInput>[
            GteRecoveryAnswerInput(
              questionId: challenge.questions[0].id,
              answer: _answerOneController.text,
            ),
            GteRecoveryAnswerInput(
              questionId: challenge.questions[1].id,
              answer: _answerTwoController.text,
            ),
          ],
          pin: pin,
          newPassword: newPassword,
          confirmNewPassword: confirmPassword,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _completed = true;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = 'Account recovery could not be completed.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}

class _RecoveryAnswerField extends StatelessWidget {
  const _RecoveryAnswerField({
    required this.controller,
    required this.question,
  });

  final TextEditingController controller;
  final String question;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Icon(Icons.help_outline, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                question,
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Recovery answer',
            prefixIcon: Icon(Icons.key_outlined),
          ),
        ),
      ],
    );
  }
}

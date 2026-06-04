import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';
import 'creators/creator_access_request_screen.dart';

enum _SignupMode { player, organization }

class GteSignupScreen extends StatefulWidget {
  const GteSignupScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteSignupScreen> createState() => _GteSignupScreenState();
}

class _GteSignupScreenState extends State<GteSignupScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _fullNameController = TextEditingController();
  final TextEditingController _organizationNameController =
      TextEditingController();
  final TextEditingController _contactNameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _dateOfBirthController = TextEditingController();
  final TextEditingController _pinController = TextEditingController();
  final TextEditingController _questionOneController = TextEditingController();
  final TextEditingController _answerOneController = TextEditingController();
  final TextEditingController _questionTwoController = TextEditingController();
  final TextEditingController _answerTwoController = TextEditingController();

  _SignupMode _mode = _SignupMode.player;
  String _preferredPosition = 'Forward';
  String _organizationType = 'club';
  bool _isSubmitting = false;
  String? _error;

  @override
  void dispose() {
    _fullNameController.dispose();
    _organizationNameController.dispose();
    _contactNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _phoneController.dispose();
    _countryController.dispose();
    _dateOfBirthController.dispose();
    _pinController.dispose();
    _questionOneController.dispose();
    _answerOneController.dispose();
    _questionTwoController.dispose();
    _answerTwoController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      body: Container(
        decoration: gteBackdropDecoration(),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 920),
                child: GteSurfacePanel(
                  emphasized: true,
                  padding: const EdgeInsets.all(24),
                  accentColor:
                      _mode == _SignupMode.player
                          ? GteShellTheme.accentCommunity
                          : GteShellTheme.accentClub,
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            IconButton(
                              tooltip: 'Back',
                              onPressed:
                                  _isSubmitting
                                      ? null
                                      : () => Navigator.of(context).maybePop(),
                              icon: const Icon(Icons.arrow_back),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Create GTEX account',
                                style: theme.textTheme.headlineSmall?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: SegmentedButton<_SignupMode>(
                            segments: const <ButtonSegment<_SignupMode>>[
                              ButtonSegment<_SignupMode>(
                                value: _SignupMode.player,
                                icon: Icon(Icons.sports_soccer),
                                label: Text('Player'),
                              ),
                              ButtonSegment<_SignupMode>(
                                value: _SignupMode.organization,
                                icon: Icon(Icons.groups_2_outlined),
                                label: Text('Organization'),
                              ),
                            ],
                            selected: <_SignupMode>{_mode},
                            onSelectionChanged:
                                _isSubmitting
                                    ? null
                                    : (Set<_SignupMode> selected) {
                                      setState(() {
                                        _mode = selected.single;
                                        _error = null;
                                      });
                                    },
                          ),
                        ),
                        const SizedBox(height: 20),
                        _mode == _SignupMode.player
                            ? _buildPlayerFields()
                            : _buildOrganizationFields(),
                        const SizedBox(height: 14),
                        _buildAccountFields(),
                        const SizedBox(height: 14),
                        _buildTrustFields(),
                        if (_error != null) ...<Widget>[
                          const SizedBox(height: 14),
                          Text(
                            _error!,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.error,
                            ),
                          ),
                        ],
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: _isSubmitting ? null : _submit,
                          icon: const Icon(Icons.how_to_reg_outlined),
                          label: Text(
                            _isSubmitting
                                ? 'Creating account...'
                                : 'Create account',
                          ),
                        ),
                        const SizedBox(height: 12),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton.icon(
                            onPressed:
                                _isSubmitting
                                    ? null
                                    : _openCreatorAccessRequest,
                            icon: const Icon(Icons.video_camera_front_outlined),
                            label: const Text('Apply for creator access'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPlayerFields() {
    return _fieldGroup(
      children: <Widget>[
        _textField(
          controller: _fullNameController,
          label: 'Full name',
          icon: Icons.badge_outlined,
          textInputAction: TextInputAction.next,
        ),
        _twoColumn(
          left: DropdownButtonFormField<String>(
            initialValue: _preferredPosition,
            decoration: const InputDecoration(
              labelText: 'Preferred position',
              prefixIcon: Icon(Icons.sports_soccer),
            ),
            items: const <String>[
                  'Goalkeeper',
                  'Defender',
                  'Midfielder',
                  'Forward',
                  'Winger',
                  'Striker',
                ]
                .map((String value) {
                  return DropdownMenuItem<String>(
                    value: value,
                    child: Text(value),
                  );
                })
                .toList(growable: false),
            onChanged:
                _isSubmitting
                    ? null
                    : (String? value) {
                      if (value != null) {
                        setState(() => _preferredPosition = value);
                      }
                    },
          ),
          right: _textField(
            controller: _dateOfBirthController,
            label: 'Date of birth',
            icon: Icons.event_outlined,
            hint: 'YYYY-MM-DD',
            keyboardType: TextInputType.datetime,
            validator: _dateValidator,
            textInputAction: TextInputAction.next,
          ),
        ),
      ],
    );
  }

  Widget _buildOrganizationFields() {
    return _fieldGroup(
      children: <Widget>[
        _textField(
          controller: _organizationNameController,
          label: 'Organization name',
          icon: Icons.apartment_outlined,
          textInputAction: TextInputAction.next,
        ),
        _textField(
          controller: _contactNameController,
          label: 'Contact name',
          icon: Icons.badge_outlined,
          textInputAction: TextInputAction.next,
        ),
        DropdownButtonFormField<String>(
          initialValue: _organizationType,
          decoration: const InputDecoration(
            labelText: 'Organization type',
            prefixIcon: Icon(Icons.groups_2_outlined),
          ),
          items: const <String>[
                'club',
                'scout',
                'agent',
                'academy',
                'coach',
                'analyst',
                'recruiter',
              ]
              .map((String value) {
                return DropdownMenuItem<String>(
                  value: value,
                  child: Text(value),
                );
              })
              .toList(growable: false),
          onChanged:
              _isSubmitting
                  ? null
                  : (String? value) {
                    if (value != null) {
                      setState(() => _organizationType = value);
                    }
                  },
        ),
      ],
    );
  }

  Widget _buildAccountFields() {
    return _fieldGroup(
      children: <Widget>[
        _textField(
          controller: _emailController,
          label: 'Email',
          icon: Icons.mail_outline,
          keyboardType: TextInputType.emailAddress,
          validator: _emailValidator,
          textInputAction: TextInputAction.next,
        ),
        _textField(
          controller: _passwordController,
          label: 'Password',
          icon: Icons.lock_outline,
          obscureText: true,
          validator: _passwordValidator,
          textInputAction: TextInputAction.next,
        ),
        _twoColumn(
          left: _textField(
            controller: _phoneController,
            label: 'Phone number',
            icon: Icons.phone_outlined,
            required: false,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.next,
          ),
          right: _textField(
            controller: _countryController,
            label: 'Country',
            icon: Icons.public_outlined,
            textInputAction: TextInputAction.next,
          ),
        ),
      ],
    );
  }

  Widget _buildTrustFields() {
    return _fieldGroup(
      children: <Widget>[
        _textField(
          controller: _pinController,
          label: 'Security PIN',
          icon: Icons.pin_outlined,
          obscureText: true,
          maxLength: 4,
          keyboardType: TextInputType.number,
          inputFormatters: <TextInputFormatter>[
            FilteringTextInputFormatter.digitsOnly,
          ],
          validator: _pinValidator,
          textInputAction: TextInputAction.next,
        ),
        _textField(
          controller: _questionOneController,
          label: 'Recovery question 1',
          icon: Icons.help_outline,
          textInputAction: TextInputAction.next,
        ),
        _textField(
          controller: _answerOneController,
          label: 'Recovery answer 1',
          icon: Icons.key_outlined,
          obscureText: true,
          textInputAction: TextInputAction.next,
        ),
        _textField(
          controller: _questionTwoController,
          label: 'Recovery question 2',
          icon: Icons.help_outline,
          textInputAction: TextInputAction.next,
        ),
        _textField(
          controller: _answerTwoController,
          label: 'Recovery answer 2',
          icon: Icons.key_outlined,
          obscureText: true,
          textInputAction: TextInputAction.done,
          onFieldSubmitted: (_) => _submit(),
        ),
      ],
    );
  }

  Widget _fieldGroup({required List<Widget> children}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children
          .map(
            (Widget child) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: child,
            ),
          )
          .toList(growable: false),
    );
  }

  Widget _twoColumn({required Widget left, required Widget right}) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        if (constraints.maxWidth < 640) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[left, const SizedBox(height: 12), right],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(child: left),
            const SizedBox(width: 12),
            Expanded(child: right),
          ],
        );
      },
    );
  }

  Widget _textField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    String? hint,
    bool required = true,
    bool obscureText = false,
    int? maxLength,
    TextInputType? keyboardType,
    TextInputAction? textInputAction,
    List<TextInputFormatter>? inputFormatters,
    String? Function(String?)? validator,
    ValueChanged<String>? onFieldSubmitted,
  }) {
    return TextFormField(
      controller: controller,
      enabled: !_isSubmitting,
      obscureText: obscureText,
      maxLength: maxLength,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      inputFormatters: inputFormatters,
      validator:
          validator ??
          (String? value) {
            if (!required) {
              return null;
            }
            return _requiredValidator(label, value);
          },
      onFieldSubmitted: onFieldSubmitted,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(icon),
        counterText: '',
      ),
    );
  }

  String? _requiredValidator(String label, String? value) {
    if (value == null || value.trim().isEmpty) {
      return '$label is required';
    }
    return null;
  }

  String? _emailValidator(String? value) {
    final String email = value?.trim() ?? '';
    if (email.isEmpty) {
      return 'Email is required';
    }
    if (!email.contains('@') || !email.contains('.')) {
      return 'Enter a valid email';
    }
    return null;
  }

  String? _passwordValidator(String? value) {
    if ((value ?? '').length < 8) {
      return 'Use at least 8 characters';
    }
    return null;
  }

  String? _pinValidator(String? value) {
    final String pin = value?.trim() ?? '';
    if (!RegExp(r'^\d{4}$').hasMatch(pin)) {
      return 'Enter a 4-digit PIN';
    }
    return null;
  }

  String? _dateValidator(String? value) {
    final String date = value?.trim() ?? '';
    if (date.isEmpty) {
      return 'Date of birth is required';
    }
    final DateTime? parsed = DateTime.tryParse(date);
    if (parsed == null || !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(date)) {
      return 'Use YYYY-MM-DD';
    }
    return null;
  }

  List<GteRecoveryQuestionInput> _recoveryQuestions() {
    return <GteRecoveryQuestionInput>[
      GteRecoveryQuestionInput(
        question: _questionOneController.text.trim(),
        answer: _answerOneController.text.trim(),
      ),
      GteRecoveryQuestionInput(
        question: _questionTwoController.text.trim(),
        answer: _answerTwoController.text.trim(),
      ),
    ];
  }

  Future<void> _submit() async {
    if (_isSubmitting) {
      return;
    }
    final FormState? form = _formKey.currentState;
    if (form == null || !form.validate()) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final GteAuthSession session =
          _mode == _SignupMode.player
              ? await widget.controller.api.signupPlayer(
                GtePlayerFrictionlessSignupRequest(
                  fullName: _fullNameController.text.trim(),
                  email: _emailController.text.trim(),
                  password: _passwordController.text,
                  phoneNumber: _optional(_phoneController),
                  country: _countryController.text.trim(),
                  preferredPosition: _preferredPosition,
                  dateOfBirth: DateTime.parse(
                    _dateOfBirthController.text.trim(),
                  ),
                  pin: _pinController.text.trim(),
                  recoveryQuestions: _recoveryQuestions(),
                ),
              )
              : await widget.controller.api.signupOrganization(
                GteOrganizationFrictionlessSignupRequest(
                  organizationName: _organizationNameController.text.trim(),
                  contactName: _contactNameController.text.trim(),
                  email: _emailController.text.trim(),
                  password: _passwordController.text,
                  phoneNumber: _optional(_phoneController),
                  organizationType: _organizationType,
                  country: _countryController.text.trim(),
                  pin: _pinController.text.trim(),
                  recoveryQuestions: _recoveryQuestions(),
                ),
              );
      widget.controller.syncSession(session);
      await widget.controller.refreshAccount();
      if (!mounted) {
        return;
      }
      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  String? _optional(TextEditingController controller) {
    final String value = controller.text.trim();
    return value.isEmpty ? null : value;
  }

  void _openCreatorAccessRequest() {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => CreatorAccessRequestScreen(
              exchangeController: widget.controller,
            ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../controllers/creator_application_controller.dart';
import '../../data/creator_application_api.dart';
import '../../data/gte_api_repository.dart';
import '../../models/creator_application_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/gtex_branding.dart';
import '../gte_signup_screen.dart';

class CreatorAccessRequestScreen extends StatefulWidget {
  const CreatorAccessRequestScreen({
    super.key,
    required this.exchangeController,
  });

  final GteExchangeController exchangeController;

  @override
  State<CreatorAccessRequestScreen> createState() =>
      _CreatorAccessRequestScreenState();
}

class _CreatorAccessRequestScreenState
    extends State<CreatorAccessRequestScreen> {
  late final TextEditingController _handleController;
  late final TextEditingController _displayNameController;
  late final TextEditingController _followerCountController;
  late final TextEditingController _socialLinksController;

  CreatorApplicationController? _applicationController;
  String? _boundAccessToken;
  String? _boundBaseUrl;
  GteBackendMode? _boundMode;
  String? _seededApplicationSignature;
  String _selectedPlatform = 'youtube';
  String? _localError;

  @override
  void initState() {
    super.initState();
    _handleController = TextEditingController();
    _displayNameController = TextEditingController();
    _followerCountController = TextEditingController();
    _socialLinksController = TextEditingController();
    widget.exchangeController.addListener(_handleExchangeControllerChanged);
    _syncApplicationController(force: true);
  }

  @override
  void didUpdateWidget(covariant CreatorAccessRequestScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.exchangeController != widget.exchangeController) {
      oldWidget.exchangeController
          .removeListener(_handleExchangeControllerChanged);
      widget.exchangeController.addListener(_handleExchangeControllerChanged);
      _syncApplicationController(force: true);
    }
  }

  @override
  void dispose() {
    widget.exchangeController.removeListener(_handleExchangeControllerChanged);
    _disposeApplicationController();
    _handleController.dispose();
    _displayNameController.dispose();
    _followerCountController.dispose();
    _socialLinksController.dispose();
    super.dispose();
  }

  void _handleExchangeControllerChanged() {
    _syncApplicationController();
    if (mounted) {
      setState(() {});
    }
  }

  void _handleApplicationControllerChanged() {
    final CreatorApplicationView? application =
        _applicationController?.application;
    if (application != null) {
      final String signature =
          '${application.applicationId}:${application.updatedAt.toIso8601String()}';
      if (signature != _seededApplicationSignature) {
        _seededApplicationSignature = signature;
        _seedFormFromApplication(application);
      }
    }
    if (mounted) {
      setState(() {});
    }
  }

  void _syncApplicationController({bool force = false}) {
    final String? nextAccessToken = widget.exchangeController.accessToken;
    final String nextBaseUrl = widget.exchangeController.api.config.baseUrl;
    final GteBackendMode nextMode = widget.exchangeController.api.config.mode;
    final bool sameBinding = !force &&
        nextAccessToken == _boundAccessToken &&
        nextBaseUrl == _boundBaseUrl &&
        nextMode == _boundMode;
    if (sameBinding) {
      return;
    }

    _boundAccessToken = nextAccessToken;
    _boundBaseUrl = nextBaseUrl;
    _boundMode = nextMode;
    _seededApplicationSignature = null;
    _disposeApplicationController();

    if (nextAccessToken == null || nextAccessToken.isEmpty) {
      return;
    }

    final CreatorApplicationController controller =
        CreatorApplicationController(
      api: CreatorApplicationApi.standard(
        baseUrl: nextBaseUrl,
        accessToken: nextAccessToken,
        mode: nextMode,
      ),
    );
    controller.addListener(_handleApplicationControllerChanged);
    _applicationController = controller;
    controller.load();
  }

  void _disposeApplicationController() {
    _applicationController?.removeListener(_handleApplicationControllerChanged);
    _applicationController?.dispose();
    _applicationController = null;
  }

  void _seedFormFromApplication(CreatorApplicationView application) {
    _handleController.text = application.requestedHandle;
    _displayNameController.text = application.displayName;
    _followerCountController.text = application.followerCount.toString();
    _socialLinksController.text = application.socialLinks.join('\n');
    _selectedPlatform =
        <String>{'youtube', 'twitch', 'tiktok'}.contains(application.platform)
            ? application.platform
            : 'youtube';
  }

  @override
  Widget build(BuildContext context) {
    final CreatorApplicationController? applicationController =
        _applicationController;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Creator access request'),
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 980),
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: <Widget>[
                  const GteStatePanel(
                    eyebrow: 'CREATOR ACCESS',
                    title: 'Request creator access from inside GTEX.',
                    message:
                        'Creator applications are reviewed before creator tools are provisioned. Confirm the account contacts GTEX should use, then submit your creator details from this screen.',
                    icon: Icons.how_to_reg_outlined,
                    accentColor: GteShellTheme.accentCommunity,
                  ),
                  const SizedBox(height: 16),
                  if (!widget.exchangeController.isAuthenticated)
                    _UnauthenticatedCreatorAccessCard(
                      onCreateAccount: _openSignup,
                      onReturnToAuth: () {
                        Navigator.of(context).pop();
                      },
                    )
                  else if (applicationController == null ||
                      (applicationController.isLoading &&
                          !applicationController.hasLoadedOnce &&
                          applicationController.application == null))
                    const GteStatePanel(
                      eyebrow: 'CREATOR ACCESS',
                      title: 'Loading creator access status',
                      message:
                          'Checking your creator application status and contact readiness.',
                      icon: Icons.auto_awesome_motion_outlined,
                      isLoading: true,
                      accentColor: GteShellTheme.accentCommunity,
                    )
                  else
                    _buildAuthenticatedContent(context, applicationController),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAuthenticatedContent(
    BuildContext context,
    CreatorApplicationController controller,
  ) {
    final CreatorApplicationView? application = controller.application;
    final bool showForm = application == null || application.canResubmit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (controller.errorMessage != null &&
            application == null &&
            !controller.isLoading)
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: GteStatePanel(
              title: 'Creator access status unavailable',
              message: controller.errorMessage!,
              icon: Icons.error_outline,
              actionLabel: 'Retry',
              onAction: () {
                controller.load();
              },
              accentColor: GteShellTheme.accentWarm,
            ),
          ),
        _ContactReadinessCard(
          email:
              widget.exchangeController.session?.user.email ?? 'Unknown email',
          phoneNumber: widget.exchangeController.session?.user.phoneNumber ??
              'No phone number on account',
          verificationStatus: controller.verificationStatus,
          canVerifyPhone:
              (widget.exchangeController.session?.user.phoneNumber ?? '')
                  .trim()
                  .isNotEmpty,
          isVerifyingEmail: controller.isVerifyingEmail,
          isVerifyingPhone: controller.isVerifyingPhone,
          verificationError: controller.verificationError,
          onVerifyEmail: controller.verificationStatus.isEmailVerified
              ? null
              : controller.verifyEmail,
          onVerifyPhone: controller.verificationStatus.isPhoneVerified ||
                  (widget.exchangeController.session?.user.phoneNumber ?? '')
                      .trim()
                      .isEmpty
              ? null
              : controller.verifyPhone,
        ),
        if (application != null) ...<Widget>[
          const SizedBox(height: 16),
          _ApplicationStatusCard(
            application: application,
            onRefresh: controller.isLoading
                ? null
                : () {
                    controller.load();
                  },
          ),
        ],
        if (showForm) ...<Widget>[
          const SizedBox(height: 16),
          _buildApplicationForm(context, controller, application),
        ],
      ],
    );
  }

  Widget _buildApplicationForm(
    BuildContext context,
    CreatorApplicationController controller,
    CreatorApplicationView? application,
  ) {
    final bool contactsReady = controller.verificationStatus.isEmailVerified &&
        controller.verificationStatus.isPhoneVerified;
    final String submitLabel = application == null
        ? 'Submit creator application'
        : 'Resubmit creator application';
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentCommunity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const GtexLogoMark(size: 42, compact: true),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      application == null
                          ? 'Creator application'
                          : 'Update creator application',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Submit the public creator identity GTEX should review. This uses the real application backend.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _handleController,
            decoration: const InputDecoration(
              labelText: 'Requested handle',
              hintText: 'creator.name',
              prefixIcon: Icon(Icons.alternate_email_outlined),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _displayNameController,
            decoration: const InputDecoration(
              labelText: 'Display name',
              hintText: 'Creator Name',
              prefixIcon: Icon(Icons.badge_outlined),
            ),
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            value: _selectedPlatform,
            decoration: const InputDecoration(
              labelText: 'Primary platform',
              prefixIcon: Icon(Icons.video_library_outlined),
            ),
            items: const <DropdownMenuItem<String>>[
              DropdownMenuItem<String>(
                value: 'youtube',
                child: Text('YouTube'),
              ),
              DropdownMenuItem<String>(
                value: 'twitch',
                child: Text('Twitch'),
              ),
              DropdownMenuItem<String>(
                value: 'tiktok',
                child: Text('TikTok'),
              ),
            ],
            onChanged: (String? value) {
              if (value == null) {
                return;
              }
              setState(() {
                _selectedPlatform = value;
              });
            },
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _followerCountController,
            keyboardType: TextInputType.number,
            inputFormatters: <TextInputFormatter>[
              FilteringTextInputFormatter.digitsOnly,
            ],
            decoration: const InputDecoration(
              labelText: 'Follower count',
              hintText: '250000',
              prefixIcon: Icon(Icons.groups_2_outlined),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _socialLinksController,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Social links',
              hintText:
                  'https://youtube.com/@creatorname\nhttps://tiktok.com/@creatorname',
              prefixIcon: Icon(Icons.link_outlined),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Use one public http or https link per line.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (_localError != null) ...<Widget>[
            const SizedBox(height: 16),
            GteStatePanel(
              title: 'Creator application blocked',
              message: _localError!,
              icon: Icons.warning_amber_rounded,
              accentColor: GteShellTheme.accentWarm,
            ),
          ],
          if (controller.submitError != null) ...<Widget>[
            const SizedBox(height: 16),
            GteStatePanel(
              title: 'Creator application failed',
              message: controller.submitError!,
              icon: Icons.warning_amber_rounded,
              accentColor: GteShellTheme.accentWarm,
            ),
          ],
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: !contactsReady || controller.isSubmitting
                    ? null
                    : _submitApplication,
                icon: const Icon(Icons.send_outlined),
                label: Text(
                  controller.isSubmitting ? 'Submitting...' : submitLabel,
                ),
              ),
              OutlinedButton.icon(
                onPressed: controller.isLoading
                    ? null
                    : () {
                        controller.load();
                      },
                icon: const Icon(Icons.refresh_outlined),
                label: const Text('Refresh status'),
              ),
            ],
          ),
          if (!contactsReady) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'Confirm both the account email and phone above before you submit.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _openSignup() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteSignupScreen(
          controller: widget.exchangeController,
        ),
      ),
    );
    if (!mounted) {
      return;
    }
    if (widget.exchangeController.isAuthenticated) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Account ready. Complete the creator request below.'),
        ),
      );
    }
  }

  Future<void> _submitApplication() async {
    final CreatorApplicationController? controller = _applicationController;
    if (controller == null) {
      return;
    }
    final String requestedHandle = _handleController.text.trim();
    final String displayName = _displayNameController.text.trim();
    final int? followerCount =
        int.tryParse(_followerCountController.text.trim());
    final List<String> socialLinks = _socialLinksController.text
        .split(RegExp(r'\r?\n'))
        .map((String item) => item.trim())
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);

    setState(() {
      _localError = null;
    });

    if (requestedHandle.length < 3) {
      setState(() {
        _localError = 'Enter a creator handle with at least 3 characters.';
      });
      return;
    }
    if (displayName.length < 2) {
      setState(() {
        _localError = 'Enter the creator display name GTEX should review.';
      });
      return;
    }
    if (followerCount == null) {
      setState(() {
        _localError =
            'Enter the current follower count for the selected platform.';
      });
      return;
    }
    if (socialLinks.isEmpty) {
      setState(() {
        _localError = 'Add at least one public social link for review.';
      });
      return;
    }

    await controller.submitApplication(
      CreatorApplicationSubmitRequest(
        requestedHandle: requestedHandle,
        displayName: displayName,
        platform: _selectedPlatform,
        followerCount: followerCount,
        socialLinks: socialLinks,
      ),
    );
    if (!mounted || controller.submitError != null) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Creator application submitted for review.'),
      ),
    );
  }
}

class _UnauthenticatedCreatorAccessCard extends StatelessWidget {
  const _UnauthenticatedCreatorAccessCard({
    required this.onCreateAccount,
    required this.onReturnToAuth,
  });

  final VoidCallback onCreateAccount;
  final VoidCallback onReturnToAuth;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentCommunity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Sign in or create an account first',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Creator requests are tied to a GTEX account. Once you are signed in, this same screen will let you confirm the account contacts on file and submit the creator application.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onCreateAccount,
                icon: const Icon(Icons.person_add_alt_1_outlined),
                label: const Text('Create account to continue'),
              ),
              OutlinedButton.icon(
                onPressed: onReturnToAuth,
                icon: const Icon(Icons.login_outlined),
                label: const Text('Back to sign in'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ContactReadinessCard extends StatelessWidget {
  const _ContactReadinessCard({
    required this.email,
    required this.phoneNumber,
    required this.verificationStatus,
    required this.canVerifyPhone,
    required this.isVerifyingEmail,
    required this.isVerifyingPhone,
    required this.verificationError,
    required this.onVerifyEmail,
    required this.onVerifyPhone,
  });

  final String email;
  final String phoneNumber;
  final CreatorContactVerificationStatus verificationStatus;
  final bool canVerifyPhone;
  final bool isVerifyingEmail;
  final bool isVerifyingPhone;
  final String? verificationError;
  final VoidCallback? onVerifyEmail;
  final VoidCallback? onVerifyPhone;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCommunity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Contact readiness',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Creator review uses the GTEX account email and phone on file. Confirm both contacts before you submit.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          _ContactStatusRow(
            label: 'Account email',
            value: email,
            isReady: verificationStatus.isEmailVerified,
          ),
          const SizedBox(height: 12),
          _ContactStatusRow(
            label: 'Account phone',
            value: phoneNumber,
            isReady: verificationStatus.isPhoneVerified,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onVerifyEmail,
                icon: Icon(
                  isVerifyingEmail ? Icons.autorenew : Icons.mail_outline,
                ),
                label: Text(
                  verificationStatus.isEmailVerified
                      ? 'Email ready'
                      : isVerifyingEmail
                          ? 'Confirming email...'
                          : 'Use account email',
                ),
              ),
              FilledButton.tonalIcon(
                onPressed: onVerifyPhone,
                icon: Icon(
                  isVerifyingPhone ? Icons.autorenew : Icons.phone_outlined,
                ),
                label: Text(
                  verificationStatus.isPhoneVerified
                      ? 'Phone ready'
                      : isVerifyingPhone
                          ? 'Confirming phone...'
                          : 'Use account phone',
                ),
              ),
            ],
          ),
          if (!canVerifyPhone) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'Add a phone number to this account before you request creator access.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          if (verificationError != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              verificationError!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.error,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ApplicationStatusCard extends StatelessWidget {
  const _ApplicationStatusCard({
    required this.application,
    required this.onRefresh,
  });

  final CreatorApplicationView application;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final String title;
    final String message;
    final Color accentColor;
    if (application.isApproved) {
      title = 'Creator access approved';
      message = application.provisioning == null
          ? 'Your creator application is approved. Provisioning is being finalized for this account.'
          : 'Your creator application is approved and provisioning is attached to this account.';
      accentColor = GteShellTheme.accentCommunity;
    } else if (application.needsVerificationUpdate) {
      title = 'More verification is required';
      message = application.decisionReason ??
          application.reviewNotes ??
          'GTEX requested more verification before the creator application can proceed.';
      accentColor = GteShellTheme.accentWarm;
    } else if (application.isRejected) {
      title = 'Creator application was not approved';
      message = application.decisionReason ??
          application.reviewNotes ??
          'This creator application was rejected. Update the details below if you need to resubmit.';
      accentColor = GteShellTheme.accentWarm;
    } else {
      title = 'Creator application pending review';
      message =
          'Your creator request is in the GTEX review queue. Refresh this screen for status changes.';
      accentColor = GteShellTheme.accentCommunity;
    }

    return GteStatePanel(
      eyebrow: 'APPLICATION STATUS',
      title: title,
      message: message,
      icon: application.isApproved
          ? Icons.verified_outlined
          : application.isRejected
              ? Icons.cancel_outlined
              : application.needsVerificationUpdate
                  ? Icons.fact_check_outlined
                  : Icons.hourglass_top_outlined,
      accentColor: accentColor,
      actionLabel: 'Refresh status',
      onAction: onRefresh,
    );
  }
}

class _ContactStatusRow extends StatelessWidget {
  const _ContactStatusRow({
    required this.label,
    required this.value,
    required this.isReady,
  });

  final String label;
  final String value;
  final bool isReady;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            isReady ? Icons.check_circle_outline : Icons.radio_button_unchecked,
            color: isReady ? GteShellTheme.positive : GteShellTheme.textMuted,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(label, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(value, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
          Text(
            isReady ? 'Ready' : 'Pending',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: isReady
                      ? GteShellTheme.positive
                      : GteShellTheme.textMuted,
                ),
          ),
        ],
      ),
    );
  }
}

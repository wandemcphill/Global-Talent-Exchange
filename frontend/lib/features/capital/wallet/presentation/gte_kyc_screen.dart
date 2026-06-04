import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class GteKycScreen extends StatefulWidget {
  const GteKycScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteKycScreen> createState() => _GteKycScreenState();
}

class _GteKycScreenState extends State<GteKycScreen> {
  CapitalWalletApi get _walletApi => widget.controller.walletApi;
  late Future<GteKycProfile> _profileFuture;
  final TextEditingController _ninController = TextEditingController();
  final TextEditingController _bvnController = TextEditingController();
  final TextEditingController _addressLine1Controller = TextEditingController();
  final TextEditingController _addressLine2Controller = TextEditingController();
  final TextEditingController _cityController = TextEditingController();
  final TextEditingController _stateController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();

  bool _hasHydrated = false;
  bool _isSubmitting = false;
  bool _isUploading = false;
  String? _error;
  GteAttachment? _attachment;

  @override
  void initState() {
    super.initState();
    _profileFuture = _loadProfile();
  }

  @override
  void dispose() {
    _ninController.dispose();
    _bvnController.dispose();
    _addressLine1Controller.dispose();
    _addressLine2Controller.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _countryController.dispose();
    super.dispose();
  }

  Future<GteKycProfile> _loadProfile() async {
    final GteKycProfile profile = await _walletApi.fetchKycProfile();
    if (!mounted) {
      return profile;
    }
    _hydrateProfile(profile);
    return profile;
  }

  void _hydrateProfile(GteKycProfile profile) {
    if (_hasHydrated) {
      return;
    }
    _hasHydrated = true;
    _ninController.text = profile.nin ?? '';
    _bvnController.text = profile.bvn ?? '';
    _addressLine1Controller.text = profile.addressLine1 ?? '';
    _addressLine2Controller.text = profile.addressLine2 ?? '';
    _cityController.text = profile.city ?? '';
    _stateController.text = profile.state ?? '';
    _countryController.text = profile.country ?? '';
  }

  Future<void> _refresh() async {
    setState(() {
      _hasHydrated = false;
      _profileFuture = _loadProfile();
    });
  }

  Future<void> _pickAttachment() async {
    if (_isUploading) {
      return;
    }
    setState(() {
      _isUploading = true;
      _error = null;
    });
    try {
      final FilePickerResult? result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: const <String>['png', 'jpg', 'jpeg', 'pdf'],
      );
      if (result == null || result.files.isEmpty) {
        return;
      }
      final PlatformFile file = result.files.first;
      final List<int> bytes = file.bytes ?? const <int>[];
      if (bytes.isEmpty) {
        throw Exception('Unable to read the selected file.');
      }
      final GteAttachment attachment = await _walletApi.uploadAttachment(
        file.name,
        bytes,
        contentType: _contentTypeForAttachment(file),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _attachment = attachment;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  Future<void> _submit(GteKycProfile profile) async {
    if (_isSubmitting) {
      return;
    }
    final String nin = _ninController.text.trim();
    final String bvn = _bvnController.text.trim();
    final String addressLine1 = _addressLine1Controller.text.trim();
    final String addressLine2 = _addressLine2Controller.text.trim();
    final String city = _cityController.text.trim();
    final String state = _stateController.text.trim();
    final String country = _countryController.text.trim();
    final String? identityAttachmentId =
        _attachment?.id ?? profile.idDocumentAttachmentId;

    if (nin.isEmpty && bvn.isEmpty && identityAttachmentId == null) {
      setState(() {
        _error =
            'Provide an identity number or upload an ID document to continue.';
      });
      return;
    }
    if (addressLine1.isEmpty) {
      setState(() {
        _error = 'Address line 1 is required.';
      });
      return;
    }
    if (country.isEmpty) {
      setState(() {
        _error = 'Country is required.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await _walletApi.submitKycProfile(
        GteKycSubmitRequest(
          nin: nin.isEmpty ? null : nin,
          bvn: bvn.isEmpty ? null : bvn,
          addressLine1: addressLine1,
          addressLine2: addressLine2.isEmpty ? null : addressLine2,
          city: city.isEmpty ? null : city,
          state: state.isEmpty ? null : state,
          country: country,
          idDocumentAttachmentId: identityAttachmentId,
        ),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('KYC submission received.')));
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('KYC verification'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<GteKycProfile>(
        future: _profileFuture,
        builder: (BuildContext context, AsyncSnapshot<GteKycProfile> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError && !snapshot.hasData) {
            return Center(
              child: GteStatePanel(
                title: 'KYC unavailable',
                message: 'We could not sync your KYC profile from the backend.',
                icon: Icons.sync_problem_outlined,
                actionLabel: 'Retry',
                onAction: _refresh,
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(
              child: GteStatePanel(
                title: 'KYC unavailable',
                message: 'We could not load your KYC profile right now.',
                icon: Icons.verified_user_outlined,
              ),
            );
          }
          final GteKycProfile profile = snapshot.data!;
          final bool isLocked =
              profile.status == GteKycStatus.pending ||
              profile.status == GteKycStatus.fullyVerified;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  accentColor: _kycStatusColor(profile.status),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'KYC status',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _kycStatusLabel(profile.status),
                        style: Theme.of(
                          context,
                        ).textTheme.displaySmall?.copyWith(fontSize: 28),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        profile.rejectionReason == null
                            ? profile.submittedAt == null
                                ? 'No submission timestamp published by backend.'
                                : 'Submitted ${gteFormatDateTime(profile.submittedAt)}'
                            : 'Rejected: ${profile.rejectionReason}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      _KycAuditRow(label: 'Audit reference', value: profile.id),
                      if (profile.idDocumentAttachmentId != null)
                        _KycAuditRow(
                          label: 'ID attachment',
                          value: profile.idDocumentAttachmentId!,
                        ),
                      if (profile.reviewedAt != null)
                        _KycAuditRow(
                          label: 'Reviewed',
                          value: gteFormatDateTime(profile.reviewedAt),
                        ),
                      if (isLocked) ...<Widget>[
                        const SizedBox(height: 12),
                        Text(
                          profile.status == GteKycStatus.fullyVerified
                              ? 'Your KYC is confirmed. Updates are locked unless support reopens the profile.'
                              : 'Your submission is pending review. Updates are locked until the status changes.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Identity details',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _ninController,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'National ID number (if required)',
                          prefixIcon: Icon(Icons.badge_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _bvnController,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'Bank verification number (if required)',
                          prefixIcon: Icon(Icons.credit_card_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _addressLine1Controller,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'Address line 1',
                          prefixIcon: Icon(Icons.home_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _addressLine2Controller,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'Address line 2 (optional)',
                          prefixIcon: Icon(Icons.apartment_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _cityController,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'City (optional)',
                          prefixIcon: Icon(Icons.location_city_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _stateController,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'State (optional)',
                          prefixIcon: Icon(Icons.map_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _countryController,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'Country',
                          prefixIcon: Icon(Icons.public_outlined),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'ID document (if required by your country)',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          OutlinedButton.icon(
                            onPressed:
                                isLocked || _isUploading
                                    ? null
                                    : _pickAttachment,
                            icon: const Icon(Icons.upload_file_outlined),
                            label: Text(
                              _isUploading ? 'Uploading...' : 'Upload ID',
                            ),
                          ),
                          if (_attachment != null ||
                              profile.idDocumentAttachmentId != null)
                            Chip(
                              label: Text(
                                _attachment?.filename ?? 'Attachment on file',
                              ),
                            ),
                        ],
                      ),
                      if (_error != null) ...<Widget>[
                        const SizedBox(height: 16),
                        GteStatePanel(
                          title: 'KYC submission error',
                          message: _error!,
                          icon: Icons.warning_amber_rounded,
                        ),
                      ],
                      const SizedBox(height: 18),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed:
                              isLocked || _isSubmitting
                                  ? null
                                  : () => _submit(profile),
                          child: Text(
                            _isSubmitting ? 'Submitting...' : 'Submit KYC',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

String _contentTypeForAttachment(PlatformFile file) {
  final String extension = (file.extension ?? '').trim().toLowerCase();
  switch (extension) {
    case 'png':
      return 'image/png';
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg';
    case 'pdf':
      return 'application/pdf';
    default:
      return 'application/octet-stream';
  }
}

String _kycStatusLabel(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return 'Unverified';
    case GteKycStatus.pending:
      return 'Pending review';
    case GteKycStatus.partialVerifiedNoId:
      return 'Partial verification';
    case GteKycStatus.fullyVerified:
      return 'Fully verified';
    case GteKycStatus.rejected:
      return 'Rejected';
  }
}

class _KycAuditRow extends StatelessWidget {
  const _KycAuditRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 124,
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: GteShellTheme.textMuted),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

Color _kycStatusColor(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return GteShellTheme.warning;
    case GteKycStatus.pending:
      return GteShellTheme.accentWarm;
    case GteKycStatus.partialVerifiedNoId:
      return GteShellTheme.accent;
    case GteKycStatus.fullyVerified:
      return GteShellTheme.positive;
    case GteKycStatus.rejected:
      return GteShellTheme.negative;
  }
}

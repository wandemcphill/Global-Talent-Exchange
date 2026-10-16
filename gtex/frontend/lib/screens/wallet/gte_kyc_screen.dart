import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_wallet_flow_scaffold.dart';

class GteKycScreen extends StatefulWidget {
  const GteKycScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteKycScreen> createState() => _GteKycScreenState();
}

class _GteKycScreenState extends State<GteKycScreen> {
  late Future<GteKycProfile> _profileFuture;
  final TextEditingController _ninController = TextEditingController();
  final TextEditingController _bvnController = TextEditingController();
  final TextEditingController _addressLine1Controller = TextEditingController();
  final TextEditingController _addressLine2Controller = TextEditingController();
  final TextEditingController _cityController = TextEditingController();
  final TextEditingController _stateController = TextEditingController();
  final TextEditingController _countryController = TextEditingController(
    text: 'Nigeria',
  );

  bool _hasHydrated = false;
  bool _isSubmitting = false;
  String? _error;
  GteKycDocumentFile? _governmentIdFile;
  GteKycDocumentFile? _selfieFile;
  GteKycDocumentFile? _proofOfAddressFile;

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
    final GteKycProfile profile = await widget.controller.api.fetchKycProfile();
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
    _countryController.text = profile.country ?? 'Nigeria';
  }

  Future<void> _refresh() async {
    setState(() {
      _hasHydrated = false;
      _profileFuture = _loadProfile();
    });
  }

  Future<void> _pickDocument(ValueChanged<GteKycDocumentFile> onPicked) async {
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
      if (!mounted) {
        return;
      }
      setState(() {
        _error = null;
        onPicked(
          GteKycDocumentFile(
            filename: file.name,
            bytes: bytes,
            contentType:
                file.extension == null ? null : 'application/${file.extension}',
          ),
        );
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
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

    if (nin.isEmpty && bvn.isEmpty) {
      setState(() {
        _error = 'Provide either a NIN or BVN to continue.';
      });
      return;
    }
    if (addressLine1.isEmpty) {
      setState(() {
        _error = 'Address line 1 is required.';
      });
      return;
    }
    if (_governmentIdFile == null || _selfieFile == null) {
      setState(() {
        _error =
            'Upload both a government ID and a selfie to submit KYC. These are required before withdrawals.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await widget.controller.api.submitKycDocuments(
        GteKycDocumentSubmission(
          governmentId: _governmentIdFile!,
          selfie: _selfieFile!,
          proofOfAddress: _proofOfAddressFile,
          nin: nin.isEmpty ? null : nin,
          bvn: bvn.isEmpty ? null : bvn,
          addressLine1: addressLine1,
          addressLine2: addressLine2.isEmpty ? null : addressLine2,
          city: city.isEmpty ? null : city,
          state: state.isEmpty ? null : state,
          country: country.isEmpty ? 'Nigeria' : country,
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
    return GteWalletFlowScaffold(
      title: 'KYC verification',
      subtitle:
          'Submit identity and address details used by wallet, withdrawals, orders, and compliance controls.',
      icon: Icons.verified_user_outlined,
      statusLabel: 'TRUST OPS',
      actions: <Widget>[
        IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
      ],
      child: FutureBuilder<GteKycProfile>(
        future: _profileFuture,
        builder: (BuildContext context, AsyncSnapshot<GteKycProfile> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
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
                            ? 'Submitted ${gteFormatDateTime(profile.submittedAt)}'
                            : 'Rejected: ${profile.rejectionReason}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      if (isLocked) ...<Widget>[
                        const SizedBox(height: 12),
                        Text(
                          'Your submission is under review. Updates are locked until the status changes.',
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
                          labelText: 'NIN (optional)',
                          prefixIcon: Icon(Icons.badge_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _bvnController,
                        enabled: !isLocked,
                        decoration: const InputDecoration(
                          labelText: 'BVN (optional)',
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
                        'Verification documents',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Required before withdrawals. Accepted: PNG, JPG, or PDF.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      _documentPickerRow(
                        label: 'Government ID',
                        file: _governmentIdFile,
                        isLocked: isLocked,
                        onPick:
                            () => _pickDocument(
                              (f) => _governmentIdFile = f,
                            ),
                      ),
                      const SizedBox(height: 12),
                      _documentPickerRow(
                        label: 'Selfie verification',
                        file: _selfieFile,
                        isLocked: isLocked,
                        onPick:
                            () => _pickDocument((f) => _selfieFile = f),
                      ),
                      const SizedBox(height: 12),
                      _documentPickerRow(
                        label: 'Proof of address (optional)',
                        file: _proofOfAddressFile,
                        isLocked: isLocked,
                        onPick:
                            () => _pickDocument(
                              (f) => _proofOfAddressFile = f,
                            ),
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

  Widget _documentPickerRow({
    required String label,
    required GteKycDocumentFile? file,
    required bool isLocked,
    required VoidCallback onPick,
  }) {
    return Row(
      children: <Widget>[
        OutlinedButton.icon(
          onPressed: isLocked ? null : onPick,
          icon: const Icon(Icons.upload_file_outlined),
          label: Text(file == null ? 'Upload $label' : 'Replace $label'),
        ),
        const SizedBox(width: 12),
        if (file != null)
          Expanded(
            child: Chip(
              avatar: const Icon(Icons.check_circle_outline, size: 18),
              label: Text(
                file.filename,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
      ],
    );
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

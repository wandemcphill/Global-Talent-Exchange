import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class GteKycScreen extends StatefulWidget {
  const GteKycScreen({
    super.key,
    required this.controller,
  });

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
  final TextEditingController _countryController =
      TextEditingController(text: 'Nigeria');

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
    final GteKycProfile profile =
        await widget.controller.api.fetchKycProfile();
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
      final List<int> bytes = file.bytes ??
          (file.path == null ? <int>[] : File(file.path!).readAsBytesSync());
      if (bytes.isEmpty) {
        throw Exception('Unable to read the selected file.');
      }
      final GteAttachment attachment =
          await widget.controller.api.uploadAttachment(
        file.name,
        bytes,
        contentType: file.extension == null
            ? null
            : 'application/${file.extension}',
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

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await widget.controller.api.submitKycProfile(
        GteKycSubmitRequest(
          nin: nin.isEmpty ? null : nin,
          bvn: bvn.isEmpty ? null : bvn,
          addressLine1: addressLine1,
          addressLine2: addressLine2.isEmpty ? null : addressLine2,
          city: city.isEmpty ? null : city,
          state: state.isEmpty ? null : state,
          country: country.isEmpty ? 'Nigeria' : country,
          idDocumentAttachmentId:
              _attachment?.id ?? profile.idDocumentAttachmentId,
        ),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('KYC submission received.')),
      );
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
        builder:
            (BuildContext context, AsyncSnapshot<GteKycProfile> snapshot) {
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
          final bool isLocked = profile.status == GteKycStatus.pending ||
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
                      Text('KYC status',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text(
                        _kycStatusLabel(profile.status),
                        style: Theme.of(context)
                            .textTheme
                            .displaySmall
                            ?.copyWith(fontSize: 28),
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
                      Text('Identity details',
                          style: Theme.of(context).textTheme.titleMedium),
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
                        'ID document (optional for partial verification)',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          OutlinedButton.icon(
                            onPressed: isLocked || _isUploading
                                ? null
                                : _pickAttachment,
                            icon: const Icon(Icons.upload_file_outlined),
                            label: Text(_isUploading
                                ? 'Uploading...'
                                : 'Upload ID'),
                          ),
                          if (_attachment != null ||
                              profile.idDocumentAttachmentId != null)
                            Chip(
                              label: Text(_attachment?.filename ??
                                  'Attachment on file'),
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
                          onPressed: isLocked || _isSubmitting
                              ? null
                              : () => _submit(profile),
                          child: Text(_isSubmitting
                              ? 'Submitting...'
                              : 'Submit KYC'),
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

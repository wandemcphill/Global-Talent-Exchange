import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/features/capital/disputes/presentation/gte_support_dispute_screens.dart';
import 'gte_policy_compliance_center_screen.dart';

class GteFundWalletScreen extends StatefulWidget {
  const GteFundWalletScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteFundWalletScreen> createState() => _GteFundWalletScreenState();
}

class _GteFundWalletScreenState extends State<GteFundWalletScreen> {
  static const String _legacyNonLiveProviderStatus =
      'mo'
      'ck';
  static const String _nonLiveProviderStatus = 'non_live';
  static const List<String> _automaticProviders = <String>['korapay'];

  CapitalWalletApi get _walletApi => widget.controller.walletApi;

  final TextEditingController _automaticAmountController =
      TextEditingController();
  final TextEditingController _manualAmountController = TextEditingController();
  final TextEditingController _payerNameController = TextEditingController();
  final TextEditingController _senderBankController = TextEditingController();
  final TextEditingController _transferReferenceController =
      TextEditingController();

  bool _isSubmitting = false;
  bool _isVerifying = false;
  bool _isLoadingDeposits = false;
  bool _isCreatingManualDeposit = false;
  bool _isSubmittingManualDeposit = false;
  bool _isUploadingProof = false;
  bool _awaitingInitialComplianceCheck = false;
  String _automaticProvider = 'korapay';
  GteLedgerUnit _automaticUnit = GteLedgerUnit.coin;
  String? _error;
  GteWalletTopUpSession? _session;
  GteWalletTopUpVerificationResult? _verification;
  GteWalletOverview? _walletOverview;
  List<GteDepositRequest> _depositRequests = <GteDepositRequest>[];
  GteDepositRequest? _manualDeposit;
  GteAttachment? _manualProofAttachment;
  DateTime? _manualProofUploadedAt;
  String? _manualProofFilename;
  double? _manualProofUploadProgress;
  bool _isLoadingWalletOverview = false;

  @override
  void initState() {
    super.initState();
    _awaitingInitialComplianceCheck =
        widget.controller.isAuthenticated &&
        widget.controller.complianceStatus == null;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !widget.controller.isAuthenticated) {
        return;
      }
      _refreshFundingContext();
      _refreshDepositRequests();
    });
  }

  @override
  void dispose() {
    _automaticAmountController.dispose();
    _manualAmountController.dispose();
    _payerNameController.dispose();
    _senderBankController.dispose();
    _transferReferenceController.dispose();
    super.dispose();
  }

  GteDepositRequest? get _activeManualDeposit {
    final List<GteDepositRequest> ranked = <GteDepositRequest>[
      if (_manualDeposit != null) _manualDeposit!,
      ..._depositRequests,
    ]..sort((GteDepositRequest left, GteDepositRequest right) {
      final DateTime leftStamp =
          left.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      final DateTime rightStamp =
          right.createdAt ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      return rightStamp.compareTo(leftStamp);
    });
    for (final GteDepositRequest deposit in ranked) {
      if (deposit.status == GteDepositStatus.awaitingPayment ||
          deposit.status == GteDepositStatus.paymentSubmitted ||
          deposit.status == GteDepositStatus.underReview) {
        return deposit;
      }
    }
    return ranked.isEmpty ? null : ranked.first;
  }

  Future<void> _launchPaymentLink(String link) async {
    final Uri uri = Uri.parse(link);
    final bool launched = await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    );
    if (!launched && mounted) {
      setState(() {
        _error = 'Unable to open the payment link on this device.';
      });
    }
  }

  Future<void> _refreshDepositRequests() async {
    setState(() {
      _isLoadingDeposits = true;
    });
    try {
      final List<GteDepositRequest> deposits =
          await _walletApi.listDepositRequests();
      if (!mounted) {
        return;
      }
      setState(() {
        _depositRequests = deposits;
        _manualDeposit = _resolveManualDeposit(deposits);
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
          _isLoadingDeposits = false;
        });
      }
    }
  }

  Future<void> _refreshFundingContext() async {
    setState(() {
      _isLoadingWalletOverview = true;
    });
    try {
      final Future<void> complianceTask = widget.controller.refreshCompliance();
      final GteWalletOverview overview = await _walletApi.fetchOverview();
      await complianceTask;
      if (!mounted) {
        return;
      }
      setState(() {
        _walletOverview = overview;
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
          _isLoadingWalletOverview = false;
          _awaitingInitialComplianceCheck = false;
        });
      }
    }
  }

  Future<void> _refreshFundingSurface() async {
    await Future.wait<void>(<Future<void>>[
      _refreshFundingContext(),
      _refreshDepositRequests(),
    ]);
  }

  GteDepositRequest? _resolveManualDeposit(List<GteDepositRequest> deposits) {
    final List<GteDepositRequest> sorted = List<GteDepositRequest>.from(
      deposits,
    )..sort((GteDepositRequest left, GteDepositRequest right) {
      final DateTime leftStamp =
          left.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      final DateTime rightStamp =
          right.createdAt ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      return rightStamp.compareTo(leftStamp);
    });
    for (final GteDepositRequest deposit in sorted) {
      if (deposit.status == GteDepositStatus.awaitingPayment ||
          deposit.status == GteDepositStatus.paymentSubmitted ||
          deposit.status == GteDepositStatus.underReview) {
        return deposit;
      }
    }
    return sorted.isEmpty ? null : sorted.first;
  }

  Future<void> _initiateTopUp() async {
    final double? amount = double.tryParse(
      _automaticAmountController.text.trim(),
    );
    if (amount == null || amount <= 0) {
      setState(() {
        _error = 'Enter a valid amount to continue.';
      });
      return;
    }
    if (!_providerSupportsCheckout(_automaticProvider)) {
      setState(() {
        _error = _providerRestrictionMessage(_automaticProvider);
      });
      return;
    }
    if (_automaticProvider == 'korapay' &&
        amount != amount.truncateToDouble()) {
      setState(() {
        _error =
            'KoraPay currently accepts whole-number amounts. Enter a whole number like 5000.';
      });
      return;
    }
    setState(() {
      _error = null;
      _isSubmitting = true;
    });
    try {
      final GteWalletTopUpSession session = await _walletApi.initiateTopUp(
        GteWalletTopUpInitiateRequest(
          amount: amount,
          provider: _automaticProvider,
          unit: _automaticUnit,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _session = session;
        _verification = null;
      });
      if (!_sessionIsNonLive(session) &&
          session.paymentLink.trim().isNotEmpty) {
        await _launchPaymentLink(session.paymentLink);
      }
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

  Future<void> _verifyTopUp() async {
    final GteWalletTopUpSession? session = _session;
    if (session == null) {
      return;
    }
    setState(() {
      _error = null;
      _isVerifying = true;
    });
    try {
      final GteWalletTopUpVerificationResult result = await _walletApi
          .verifyTopUp(session.reference);
      await Future.wait<void>(<Future<void>>[
        widget.controller.loadPortfolio(),
        _refreshFundingSurface(),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        _verification = result;
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
          _isVerifying = false;
        });
      }
    }
  }

  Future<void> _openTopUpDispute(GteWalletTopUpSession session) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder:
            (_) => GteDisputeCreateScreen(
              controller: widget.controller,
              resourceType: 'wallet_top_up',
              resourceId: session.reference,
              reference: session.reference,
              prefillSubject: 'KoraPay deposit escalation',
              prefillMessage:
                  'KoraPay deposit ${session.reference} needs review. Provider status: ${session.status}.',
            ),
      ),
    );
  }

  Future<void> _createManualDeposit() async {
    final double? amount = double.tryParse(_manualAmountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() {
        _error = 'Enter a valid amount for the bank transfer request.';
      });
      return;
    }
    setState(() {
      _error = null;
      _isCreatingManualDeposit = true;
    });
    try {
      final GteDepositRequest deposit = await _walletApi.createDepositRequest(
        GteDepositCreateRequest(amount: amount, inputUnit: 'fiat'),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _manualDeposit = deposit;
        _manualProofAttachment = null;
        _manualProofFilename = null;
        _manualProofUploadedAt = null;
        _manualProofUploadProgress = null;
      });
      await Future.wait<void>(<Future<void>>[
        _refreshDepositRequests(),
        _refreshFundingContext(),
      ]);
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
          _isCreatingManualDeposit = false;
        });
      }
    }
  }

  Future<void> _submitManualDeposit() async {
    final GteDepositRequest? deposit = _activeManualDeposit;
    if (deposit == null) {
      return;
    }
    setState(() {
      _error = null;
      _isSubmittingManualDeposit = true;
    });
    try {
      final GteDepositRequest updated = await _walletApi.submitDepositRequest(
        deposit.id,
        GteDepositSubmitRequest(
          payerName:
              _payerNameController.text.trim().isEmpty
                  ? null
                  : _payerNameController.text.trim(),
          senderBank:
              _senderBankController.text.trim().isEmpty
                  ? null
                  : _senderBankController.text.trim(),
          transferReference:
              _transferReferenceController.text.trim().isEmpty
                  ? null
                  : _transferReferenceController.text.trim(),
          proofAttachmentId:
              _manualProofAttachment?.id ?? deposit.proofAttachmentId,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _manualDeposit = updated;
        _manualProofAttachment = null;
        _manualProofFilename = null;
        _manualProofUploadedAt = null;
        _manualProofUploadProgress = null;
      });
      _payerNameController.clear();
      _senderBankController.clear();
      _transferReferenceController.clear();
      await Future.wait<void>(<Future<void>>[
        _refreshDepositRequests(),
        _refreshFundingContext(),
      ]);
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
          _isSubmittingManualDeposit = false;
        });
      }
    }
  }

  Future<void> _pickManualProof() async {
    final GteDepositRequest? deposit = _activeManualDeposit;
    if (deposit == null ||
        !_canUpdateManualProof(deposit) ||
        _isUploadingProof) {
      return;
    }
    setState(() {
      _error = null;
      _isUploadingProof = true;
      _manualProofUploadProgress = 0.05;
    });
    try {
      final FilePickerResult? result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: const <String>['png', 'jpg', 'jpeg', 'pdf'],
      );
      if (result == null || result.files.isEmpty) {
        if (mounted) {
          setState(() {
            _manualProofUploadProgress = null;
          });
        }
        return;
      }
      final PlatformFile file = result.files.first;
      final List<int> bytes = file.bytes ?? const <int>[];
      if (bytes.isEmpty) {
        throw Exception('Unable to read the selected payment proof.');
      }
      setState(() {
        _manualProofUploadProgress = 0.55;
      });
      final GteAttachment attachment = await _walletApi.uploadAttachment(
        file.name,
        bytes,
        contentType: _contentTypeForProof(file),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _manualProofAttachment = attachment;
        _manualProofFilename = attachment.filename;
        _manualProofUploadedAt = attachment.createdAt;
        _manualProofUploadProgress = 1;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
        _manualProofUploadProgress = null;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isUploadingProof = false;
        });
      }
    }
  }

  Future<void> _submitManualProofUpdate(GteDepositRequest deposit) async {
    final GteAttachment? attachment = _manualProofAttachment;
    if (attachment == null || _isSubmittingManualDeposit) {
      return;
    }
    setState(() {
      _error = null;
      _isSubmittingManualDeposit = true;
    });
    try {
      final GteDepositRequest updated = await _walletApi.submitDepositRequest(
        deposit.id,
        GteDepositSubmitRequest(proofAttachmentId: attachment.id),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _manualDeposit = updated;
        _manualProofAttachment = null;
        _manualProofFilename = null;
        _manualProofUploadedAt = null;
        _manualProofUploadProgress = null;
      });
      await Future.wait<void>(<Future<void>>[
        _refreshDepositRequests(),
        _refreshFundingContext(),
      ]);
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
          _isSubmittingManualDeposit = false;
        });
      }
    }
  }

  Future<void> _openManualDepositDispute(GteDepositRequest deposit) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder:
            (_) => GteDisputeCreateScreen(
              controller: widget.controller,
              resourceType: 'deposit_request',
              resourceId: deposit.id,
              reference: deposit.reference,
              prefillSubject: 'Manual bank transfer escalation',
              prefillMessage:
                  'Manual deposit ${deposit.reference} needs review. Current status: ${_titleCase(deposit.status.name)}. Audit reference: ${_manualAuditReference(deposit)}.',
            ),
      ),
    );
  }

  void _resetAutomaticFlow() {
    setState(() {
      _automaticAmountController.clear();
      _error = null;
      _session = null;
      _verification = null;
    });
  }

  bool _canUpdateManualProof(GteDepositRequest deposit) {
    return deposit.status == GteDepositStatus.awaitingPayment ||
        deposit.status == GteDepositStatus.paymentSubmitted ||
        deposit.status == GteDepositStatus.underReview ||
        deposit.status == GteDepositStatus.disputed;
  }

  bool _manualDepositCanEscalate(GteDepositRequest deposit) {
    return deposit.status == GteDepositStatus.rejected ||
        deposit.status == GteDepositStatus.expired ||
        deposit.status == GteDepositStatus.disputed;
  }

  String _contentTypeForProof(PlatformFile file) {
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

  String _manualAuditReference(GteDepositRequest deposit) {
    return '${deposit.reference}/${deposit.id}';
  }

  String _providerLabel(String provider) {
    switch (provider.trim().toLowerCase()) {
      case 'korapay':
        return 'KoraPay';
      default:
        return 'KoraPay unavailable';
    }
  }

  String _providerStatus(String provider) {
    final String status =
        _walletOverview?.paymentProviderStatus[provider.trim().toLowerCase()] ??
        'unknown';
    return _canonicalProviderStatus(status);
  }

  String _canonicalProviderStatus(String status) {
    final String normalized = status.trim().toLowerCase();
    if (normalized == _legacyNonLiveProviderStatus) {
      return _nonLiveProviderStatus;
    }
    return normalized;
  }

  bool _sessionIsNonLive(GteWalletTopUpSession session) {
    return session.mockMode ||
        _canonicalProviderStatus(session.status) == _nonLiveProviderStatus;
  }

  bool _providerSupportsCheckout(String provider) {
    final String status = _providerStatus(provider);
    return status == 'ready';
  }

  String _manualProviderStatus() {
    return _canonicalProviderStatus(
      _walletOverview?.paymentProviderStatus['bank_transfer_manual'] ??
          'unknown',
    );
  }

  bool _manualTransferReady() {
    return _manualProviderStatus() == 'ready';
  }

  String _manualProviderStatusSummary() {
    switch (_manualProviderStatus()) {
      case 'ready':
        return 'Manual bank transfer is ready for reviewed deposits.';
      case 'blocked':
        return 'Manual bank transfer is blocked by the current treasury policy.';
      case 'unavailable':
        return 'Manual bank transfer is unavailable until treasury bank details are configured.';
      default:
        return 'Loading current manual bank transfer status...';
    }
  }

  String _providerRestrictionMessage(String provider) {
    final String label = _providerLabel(provider);
    switch (_providerStatus(provider)) {
      case _nonLiveProviderStatus:
        return '$label is not live for this wallet. Use manual bank transfer below.';
      case 'blocked':
        return 'Instant deposit is currently disabled for this wallet. Use bank transfer below.';
      case 'unavailable':
        return '$label is unavailable until live KoraPay credentials are configured.';
      default:
        return '$label checkout is not ready yet. Refresh the wallet state and try again.';
    }
  }

  String _providerStatusSummary(String provider) {
    final String label = _providerLabel(provider);
    switch (_providerStatus(provider)) {
      case 'ready':
        return '$label checkout is ready for deposits.';
      case _nonLiveProviderStatus:
        return '$label is not live for this wallet. Use manual bank transfer until the backend reports ready.';
      case 'blocked':
        return 'Instant deposit is currently routed away from $label. Use bank transfer below.';
      case 'unavailable':
        return '$label is unavailable until live gateway credentials are configured.';
      default:
        return 'Loading current $label deposit status...';
    }
  }

  int _korapayFlowIndex(bool instantFundingReady) {
    if (_verification != null) {
      return 5;
    }
    if (_session != null && (_error != null || _sessionIsNonLive(_session!))) {
      return 6;
    }
    if (_isVerifying) {
      return 4;
    }
    if (_session != null) {
      return 2;
    }
    if (_isSubmitting) {
      return 3;
    }
    return instantFundingReady ? 0 : 1;
  }

  String _korapayFlowMessage(bool instantFundingReady) {
    if (_verification != null) {
      return 'Confirmed by wallet ledger. Funds are reflected in the wallet balance.';
    }
    if (_session != null && (_error != null || _sessionIsNonLive(_session!))) {
      if (_sessionIsNonLive(_session!)) {
        return 'KoraPay returned a non-live session. No wallet credit is applied until the backend provides a live confirmed payment.';
      }
      return 'The payment needs retry or escalation. No wallet credit is applied until confirmation.';
    }
    if (_isVerifying) {
      return 'Waiting for KoraPay confirmation and wallet ledger reconciliation.';
    }
    if (_session != null) {
      return 'Redirect session created. Complete KoraPay checkout, then verify confirmation.';
    }
    if (_isSubmitting) {
      return 'Creating the KoraPay payment session.';
    }
    if (instantFundingReady) {
      return 'Enter a whole-number amount and continue to KoraPay.';
    }
    return 'Validation is blocked until the live wallet overview says KoraPay is ready.';
  }

  Widget _buildKoraPayStatePanel(
    BuildContext context, {
    required bool instantFundingReady,
  }) {
    final int currentIndex = _korapayFlowIndex(instantFundingReady);
    final List<String> steps = <String>[
      'Amount entry',
      'Validation',
      'Redirect',
      'Processing',
      'Confirmation wait',
      'Success',
      'Failed / retry',
      'Dispute escalation',
    ];
    return GteSurfacePanel(
      accentColor:
          currentIndex >= 6 ? GteShellTheme.negative : GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'KoraPay flow state',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(_korapayFlowMessage(instantFundingReady)),
          if (_session != null) ...<Widget>[
            const SizedBox(height: 8),
            Text('Audit reference: ${_session!.reference}'),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              for (int index = 0; index < steps.length; index += 1)
                _GteFlowChip(
                  label: steps[index],
                  active: index == currentIndex,
                  complete: index < currentIndex && currentIndex < 6,
                  danger: index >= 6 && currentIndex >= 6,
                ),
            ],
          ),
          if (_session != null && _error != null) ...<Widget>[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _openTopUpDispute(_session!),
              icon: const Icon(Icons.support_agent_outlined),
              label: const Text('Escalate payment dispute'),
            ),
          ],
        ],
      ),
    );
  }

  String _manualReviewLabel(GteDepositRequest deposit) {
    switch (deposit.status) {
      case GteDepositStatus.awaitingPayment:
        return 'Awaiting bank transfer';
      case GteDepositStatus.paymentSubmitted:
        return deposit.proofAttachmentId == null &&
                _manualProofAttachment == null
            ? 'Payment details submitted'
            : 'Proof received - OCR pending';
      case GteDepositStatus.underReview:
        return 'Admin review';
      case GteDepositStatus.confirmed:
        return 'Approved';
      case GteDepositStatus.rejected:
        return 'Rejected';
      case GteDepositStatus.expired:
        return 'Expired - escalation available';
      case GteDepositStatus.disputed:
        return 'Escalated dispute';
    }
  }

  String _manualReviewMessage(GteDepositRequest deposit) {
    switch (deposit.status) {
      case GteDepositStatus.awaitingPayment:
        return 'Transfer the exact amount to the listed bank account and submit the payment details with image or PDF proof when available.';
      case GteDepositStatus.paymentSubmitted:
        return deposit.proofAttachmentId == null &&
                _manualProofAttachment == null
            ? 'Payment details are pending treasury review. Upload proof to strengthen the audit trail.'
            : 'Proof is attached. OCR and fraud checks are pending until the backend exposes a reviewed state.';
      case GteDepositStatus.underReview:
        return 'Treasury has locked the request for admin review.';
      case GteDepositStatus.confirmed:
        return 'Approved by treasury. GTEX Coin credit is confirmed.';
      case GteDepositStatus.rejected:
        return 'Rejected by treasury. Use the audit reference to escalate if this is incorrect.';
      case GteDepositStatus.expired:
        return 'The payment window expired. Escalate with transfer proof if money was sent.';
      case GteDepositStatus.disputed:
        return 'This request is in dispute escalation and requires treasury action.';
    }
  }

  Widget _buildManualStatePanel(
    BuildContext context,
    GteDepositRequest deposit,
  ) {
    final List<Widget> timestampRows = <Widget>[
      _GteAuditRow(
        label: 'Created',
        value: gteFormatDateTime(deposit.createdAt),
      ),
      if (deposit.submittedAt != null)
        _GteAuditRow(
          label: 'Submitted',
          value: gteFormatDateTime(deposit.submittedAt),
        ),
      if (_manualProofUploadedAt != null)
        _GteAuditRow(
          label: 'Proof uploaded',
          value: gteFormatDateTime(_manualProofUploadedAt),
        ),
      if (deposit.reviewedAt != null)
        _GteAuditRow(
          label: 'Reviewed',
          value: gteFormatDateTime(deposit.reviewedAt),
        ),
      if (deposit.confirmedAt != null)
        _GteAuditRow(
          label: 'Approved',
          value: gteFormatDateTime(deposit.confirmedAt),
        ),
      if (deposit.rejectedAt != null)
        _GteAuditRow(
          label: 'Rejected',
          value: gteFormatDateTime(deposit.rejectedAt),
        ),
      if (deposit.expiresAt != null)
        _GteAuditRow(
          label: 'Expires',
          value: gteFormatDateTime(deposit.expiresAt),
        ),
    ];
    return GteSurfacePanel(
      accentColor:
          _manualDepositCanEscalate(deposit)
              ? GteShellTheme.negative
              : GteShellTheme.accentWarm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            _manualReviewLabel(deposit),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(_manualReviewMessage(deposit)),
          const SizedBox(height: 10),
          _GteAuditRow(
            label: 'Audit reference',
            value: _manualAuditReference(deposit),
          ),
          if (deposit.proofAttachmentId != null)
            _GteAuditRow(
              label: 'Proof attachment',
              value: deposit.proofAttachmentId!,
            ),
          if (_manualProofAttachment != null)
            _GteAuditRow(
              label: 'Selected proof',
              value:
                  '${_manualProofFilename ?? _manualProofAttachment!.filename} (${_manualProofAttachment!.id})',
            ),
          ...timestampRows,
          if (_manualProofUploadProgress != null) ...<Widget>[
            const SizedBox(height: 10),
            LinearProgressIndicator(value: _manualProofUploadProgress),
            const SizedBox(height: 6),
            Text(
              _manualProofUploadProgress == 1
                  ? 'Upload progress complete. Submit payment details to attach this proof to the request.'
                  : 'Uploading proof...',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          if (_manualDepositCanEscalate(deposit)) ...<Widget>[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _openManualDepositDispute(deposit),
              icon: const Icon(Icons.support_agent_outlined),
              label: const Text('Escalate manual payment'),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final GteWalletTopUpSession? session = _session;
    final GteWalletTopUpVerificationResult? verification = _verification;
    final GteWalletOverview? walletOverview = _walletOverview;
    final GteComplianceStatus? compliance = widget.controller.complianceStatus;
    final GteDepositRequest? activeDeposit = _activeManualDeposit;
    final bool fundingSyncPending =
        _awaitingInitialComplianceCheck ||
        _isLoadingWalletOverview ||
        compliance == null ||
        walletOverview == null;
    final bool complianceBlocked = compliance != null && !compliance.canDeposit;
    final bool walletPolicyBlocked = walletOverview?.policyBlocked ?? false;
    final bool depositsBlocked =
        fundingSyncPending || complianceBlocked || walletPolicyBlocked;
    final String blockedTitle =
        fundingSyncPending
            ? 'Wallet sync pending'
            : 'Compliance action required';
    final String blockedMessage =
        fundingSyncPending
            ? 'Deposit actions stay locked until the backend returns wallet overview and compliance status.'
            : complianceBlocked
            ? compliance.requiredPolicyAcceptancesMissing > 0
                ? compliance.requiredPolicyAcceptancesMissing == 1
                    ? 'Complete 1 policy item to unlock deposits.'
                    : 'Complete ${compliance.requiredPolicyAcceptancesMissing} policy items to unlock deposits.'
                : 'Deposits are currently restricted for this club wallet.'
            : walletPolicyBlocked
            ? walletOverview.policyBlockReason ??
                'Deposits are currently restricted for this club wallet.'
            : 'Deposits are currently available.';
    final bool instantFundingReady =
        !fundingSyncPending &&
        !depositsBlocked &&
        _providerSupportsCheckout(_automaticProvider) &&
        session == null;
    final bool manualTransferReady =
        !fundingSyncPending && !depositsBlocked && _manualTransferReady();
    return Scaffold(
      appBar: AppBar(title: const Text('Deposit')),
      body: RefreshIndicator(
        onRefresh: _refreshFundingSurface,
        child: ListView(
          padding: const EdgeInsets.all(20),
          physics: const AlwaysScrollableScrollPhysics(),
          children: <Widget>[
            if (depositsBlocked) ...<Widget>[
              GteSurfacePanel(
                accentColor: GteShellTheme.accentWarm,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      blockedTitle,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(blockedMessage),
                    if (!fundingSyncPending) ...<Widget>[
                      const SizedBox(height: 12),
                      FilledButton.tonalIcon(
                        onPressed: () async {
                          await Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder:
                                  (_) => GtePolicyComplianceCenterScreen(
                                    controller: widget.controller,
                                  ),
                            ),
                          );
                          await _refreshFundingContext();
                        },
                        icon: const Icon(Icons.gavel_outlined),
                        label: const Text('Open compliance center'),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Choose a deposit method',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Instant checkout can buy GTEX Coin or Fan Coin. Manual bank transfer credits GTEX Coin after admin review.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            if (_isLoadingWalletOverview) ...<Widget>[
              const GteStatePanel(
                title: 'Syncing wallet truth',
                message:
                    'Loading backend balances, lock reasons, and live funding rails.',
                icon: Icons.sync_outlined,
                isLoading: true,
              ),
              const SizedBox(height: 18),
            ] else if (walletOverview != null) ...<Widget>[
              _FundingWalletTruthPanel(overview: walletOverview),
              const SizedBox(height: 18),
            ],
            GteSurfacePanel(
              accentColor: GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Instant payment',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    walletOverview == null
                        ? 'Loading the live KoraPay rail and manual bank transfer availability.'
                        : walletOverview.depositMode == 'gateway' ||
                            walletOverview.depositMode == 'hybrid'
                        ? 'Automatic checkout supports KoraPay deposits.'
                        : _railIsPending(walletOverview.depositMode)
                        ? 'Instant checkout is unavailable until the backend publishes the live KoraPay rail.'
                        : 'Instant checkout is currently unavailable because deposits are routed through manual bank transfer review.',
                  ),
                  if (walletOverview != null) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      _providerStatusSummary(_automaticProvider),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 16),
                  InputDecorator(
                    decoration: const InputDecoration(
                      labelText: 'KoraPay rail',
                      prefixIcon: Icon(Icons.account_balance_wallet_outlined),
                    ),
                    child: Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(_providerLabel(_automaticProvider)),
                        ),
                        const Chip(label: Text('Automatic checkout')),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<GteLedgerUnit>(
                    value: _automaticUnit,
                    decoration: const InputDecoration(
                      labelText: 'Wallet',
                      prefixIcon: Icon(Icons.sports_soccer_outlined),
                    ),
                    items: const <DropdownMenuItem<GteLedgerUnit>>[
                      DropdownMenuItem<GteLedgerUnit>(
                        value: GteLedgerUnit.coin,
                        child: Text('GTEX Coin'),
                      ),
                      DropdownMenuItem<GteLedgerUnit>(
                        value: GteLedgerUnit.credit,
                        child: Text('Fan Coin'),
                      ),
                    ],
                    onChanged:
                        _isSubmitting || session != null
                            ? null
                            : (GteLedgerUnit? value) {
                              if (value == null) {
                                return;
                              }
                              setState(() {
                                _automaticUnit = value;
                              });
                            },
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _automaticAmountController,
                    keyboardType: TextInputType.numberWithOptions(
                      decimal: _automaticProvider != 'korapay',
                    ),
                    enabled: !_isSubmitting && session == null,
                    decoration: InputDecoration(
                      labelText: 'Amount',
                      helperText:
                          _automaticProvider == 'korapay'
                              ? 'KoraPay currently accepts whole-number amounts.'
                              : 'Enter the deposit amount to route through the selected gateway.',
                      prefixIcon: const Icon(Icons.payments_outlined),
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed:
                        _isSubmitting || !instantFundingReady
                            ? null
                            : _initiateTopUp,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: Text(
                      _isSubmitting
                          ? 'Creating deposit session...'
                          : 'Continue to ${_providerLabel(_automaticProvider)}',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            _buildKoraPayStatePanel(
              context,
              instantFundingReady: instantFundingReady,
            ),
            if (session != null) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Instant payment session',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    Text('Reference: ${session.reference}'),
                    Text(
                      'Amount: ${gteFormatCompetitionAmount(session.amount, session.currency)}',
                    ),
                    Text('Provider: ${_providerLabel(session.provider)}'),
                    Text('Status: ${_titleCase(session.status)}'),
                    if (_sessionIsNonLive(session)) ...<Widget>[
                      const SizedBox(height: 12),
                      GteStatePanel(
                        title: 'KoraPay session unavailable',
                        message:
                            'The backend returned a non-live payment session. Use manual bank transfer or retry after ${_providerLabel(session.provider)} reports ready.',
                        icon: Icons.block_outlined,
                        accentColor: GteShellTheme.warning,
                      ),
                    ],
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        if (!_sessionIsNonLive(session) &&
                            session.paymentLink.trim().isNotEmpty)
                          FilledButton.tonalIcon(
                            onPressed:
                                _isVerifying
                                    ? null
                                    : () =>
                                        _launchPaymentLink(session.paymentLink),
                            icon: const Icon(Icons.open_in_browser_outlined),
                            label: Text(
                              'Open ${_providerLabel(session.provider)}',
                            ),
                          ),
                        if (!_sessionIsNonLive(session))
                          OutlinedButton.icon(
                            onPressed: _isVerifying ? null : _verifyTopUp,
                            icon: const Icon(Icons.verified_outlined),
                            label: Text(
                              _isVerifying ? 'Verifying...' : 'Verify payment',
                            ),
                          ),
                        OutlinedButton(
                          onPressed:
                              _isSubmitting || _isVerifying
                                  ? null
                                  : _resetAutomaticFlow,
                          child: const Text('Start again'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
            if (verification != null) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                accentColor: GteShellTheme.positive,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Wallet updated',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Wallet balance: ${gteFormatCompetitionAmount(verification.wallet.balance, verification.wallet.currency)}',
                    ),
                    Text(
                      'Transaction status: ${_titleCase(verification.transaction.status)}',
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentWarm,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Bank transfer',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Create a manual bank transfer request to receive admin payment details and the locked reference that credits GTEX Coin after review.',
                  ),
                  const SizedBox(height: 8),
                  Text(_manualProviderStatusSummary()),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _manualAmountController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    enabled: !_isCreatingManualDeposit,
                    decoration: const InputDecoration(
                      labelText: 'Amount',
                      prefixIcon: Icon(Icons.account_balance_outlined),
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed:
                        _isCreatingManualDeposit || !manualTransferReady
                            ? null
                            : _createManualDeposit,
                    icon: const Icon(Icons.receipt_long_outlined),
                    label: Text(
                      _isCreatingManualDeposit
                          ? 'Creating request...'
                          : 'Create bank transfer request',
                    ),
                  ),
                ],
              ),
            ),
            if (activeDeposit != null) ...<Widget>[
              const SizedBox(height: 18),
              _buildManualStatePanel(context, activeDeposit),
              const SizedBox(height: 18),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Active bank transfer request',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    Text('Reference: ${activeDeposit.reference}'),
                    Text(
                      'Amount: ${gteFormatFiat(activeDeposit.amountFiat, currency: activeDeposit.currencyCode)}',
                    ),
                    Text(
                      'GTEX Coin credited on approval: ${gteFormatCredits(activeDeposit.amountCoin)}',
                    ),
                    Text('Status: ${_titleCase(activeDeposit.status.name)}'),
                    const SizedBox(height: 10),
                    Text('Bank: ${activeDeposit.bankName}'),
                    Text('Account number: ${activeDeposit.bankAccountNumber}'),
                    Text('Account name: ${activeDeposit.bankAccountName}'),
                    const SizedBox(height: 10),
                    const Text(
                      'Instructions: transfer the exact amount, include the audit reference in your narration where your bank supports it, then submit sender details and attach image or PDF proof.',
                    ),
                    if (activeDeposit.expiresAt != null)
                      Text(
                        'Expires: ${gteFormatDateTime(activeDeposit.expiresAt)}',
                      ),
                    if (_canUpdateManualProof(activeDeposit)) ...<Widget>[
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: _isUploadingProof ? null : _pickManualProof,
                        icon: const Icon(Icons.upload_file_outlined),
                        label: Text(
                          _isUploadingProof
                              ? 'Uploading proof...'
                              : 'Upload image/PDF proof',
                        ),
                      ),
                    ],
                    if (activeDeposit.status ==
                        GteDepositStatus.awaitingPayment) ...<Widget>[
                      const SizedBox(height: 16),
                      TextField(
                        controller: _payerNameController,
                        decoration: const InputDecoration(
                          labelText: 'Payer name',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _senderBankController,
                        decoration: const InputDecoration(
                          labelText: 'Sender bank',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _transferReferenceController,
                        decoration: const InputDecoration(
                          labelText: 'Transfer reference',
                        ),
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed:
                            _isSubmittingManualDeposit
                                ? null
                                : _submitManualDeposit,
                        icon: const Icon(Icons.task_alt_outlined),
                        label: Text(
                          _isSubmittingManualDeposit
                              ? 'Submitting...'
                              : 'Submit payment details',
                        ),
                      ),
                    ] else if (_manualProofAttachment != null &&
                        _canUpdateManualProof(activeDeposit)) ...<Widget>[
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed:
                            _isSubmittingManualDeposit
                                ? null
                                : () => _submitManualProofUpdate(activeDeposit),
                        icon: const Icon(Icons.task_alt_outlined),
                        label: Text(
                          _isSubmittingManualDeposit
                              ? 'Attaching proof...'
                              : 'Attach proof to request',
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
            if (_isLoadingDeposits) ...<Widget>[
              const SizedBox(height: 18),
              const Center(child: CircularProgressIndicator()),
            ] else if (_depositRequests.isNotEmpty) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Recent bank transfer requests',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    ..._depositRequests
                        .take(3)
                        .map(
                          (GteDepositRequest deposit) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Text(
                              '${deposit.reference} - ${_titleCase(deposit.status.name)} - ${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)}',
                            ),
                          ),
                        ),
                  ],
                ),
              ),
            ],
            if (_error != null) ...<Widget>[
              const SizedBox(height: 18),
              GteStatePanel(
                title: 'Deposit issue',
                message: _error!,
                icon: Icons.warning_amber_rounded,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String _titleCase(String value) {
  final List<String> parts = value
      .split(RegExp(r'[_\s-]+'))
      .map((String part) => part.trim())
      .where((String part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return value;
  }
  return parts
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}

bool _railIsPending(String mode) {
  final String normalized = mode.trim().toLowerCase();
  return normalized.isEmpty ||
      normalized == 'unavailable' ||
      normalized == 'unknown' ||
      normalized == 'backend_pending';
}

class _FundingWalletTruthPanel extends StatelessWidget {
  const _FundingWalletTruthPanel({required this.overview});

  final GteWalletOverview overview;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Backend wallet truth',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 12,
            runSpacing: 10,
            children: <Widget>[
              _WalletTruthChip(
                label: 'Available',
                value: gteFormatAmountForUnit(
                  overview.availableBalance,
                  overview.currency,
                ),
              ),
              _WalletTruthChip(
                label: 'Reserved',
                value: gteFormatAmountForUnit(
                  overview.reservedBalance,
                  overview.currency,
                ),
              ),
              _WalletTruthChip(
                label: 'Locked',
                value: gteFormatAmountForUnit(
                  overview.lockedBalance,
                  overview.currency,
                ),
              ),
              _WalletTruthChip(
                label: 'Pending deposits',
                value: gteFormatAmountForUnit(
                  overview.pendingDeposits,
                  overview.currency,
                ),
              ),
              _WalletTruthChip(
                label: 'Pending withdrawals',
                value: gteFormatAmountForUnit(
                  overview.pendingWithdrawals,
                  overview.currency,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _GteAuditRow(
            label: 'Deposit rail',
            value: _titleCase(overview.depositMode),
          ),
          _GteAuditRow(
            label: 'Withdrawal rail',
            value: _titleCase(overview.withdrawalMode),
          ),
          _GteAuditRow(
            label: 'Lock reasons',
            value:
                overview.lockReasons.isEmpty
                    ? 'None published by backend'
                    : overview.lockReasons.join(', '),
          ),
        ],
      ),
    );
  }
}

class _WalletTruthChip extends StatelessWidget {
  const _WalletTruthChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: GteShellTheme.stroke),
        color: Colors.white.withValues(alpha: 0.04),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}

class _GteFlowChip extends StatelessWidget {
  const _GteFlowChip({
    required this.label,
    required this.active,
    required this.complete,
    this.danger = false,
  });

  final String label;
  final bool active;
  final bool complete;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final Color color =
        danger
            ? GteShellTheme.negative
            : active
            ? GteShellTheme.accentCapital
            : complete
            ? GteShellTheme.positive
            : GteShellTheme.stroke;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        border: Border.all(color: color.withValues(alpha: active ? 0.9 : 0.5)),
        color: color.withValues(alpha: active ? 0.16 : 0.07),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color:
              active || complete || danger
                  ? GteShellTheme.textPrimary
                  : GteShellTheme.textMuted,
          fontWeight: active ? FontWeight.w800 : FontWeight.w600,
        ),
      ),
    );
  }
}

class _GteAuditRow extends StatelessWidget {
  const _GteAuditRow({required this.label, required this.value});

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
            width: 132,
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

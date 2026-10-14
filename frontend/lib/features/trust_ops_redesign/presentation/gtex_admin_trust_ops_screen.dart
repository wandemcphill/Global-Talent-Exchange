import 'package:flutter/material.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../data/gtex_trust_ops_api_repository.dart';
import '../data/gtex_trust_ops_demo_repository.dart';
import '../models/gtex_trust_ops_models.dart';
import '../widgets/gtex_kyc_dispute_widgets.dart';
import '../widgets/gtex_trust_context_panel.dart';
import '../widgets/gtex_wallet_order_widgets.dart';

class GtexAdminTrustOpsScreen extends StatefulWidget {
  const GtexAdminTrustOpsScreen({
    super.key,
    this.repository,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final GtexTrustOpsRepository? repository;
  final String baseUrl;
  final String? accessToken;
  final GteBackendMode backendMode;

  @override
  State<GtexAdminTrustOpsScreen> createState() =>
      _GtexAdminTrustOpsScreenState();
}

class _GtexAdminTrustOpsScreenState extends State<GtexAdminTrustOpsScreen> {
  late Future<GtexTrustOpsState> _future;
  late GtexTrustOpsRepository _repository;
  GtexTrustModule _selectedModule = GtexTrustModule.kyc;
  String? _selectedKycCaseId;
  String? _selectedDisputeId;
  String? _selectedOrderId;
  bool _kycReviewBusy = false;
  bool _disputeReplyBusy = false;
  bool _orderReviewBusy = false;

  @override
  void initState() {
    super.initState();
    _repository =
        widget.repository ??
        (widget.backendMode == GteBackendMode.fixture
            ? const GtexTrustOpsDemoRepository()
            : GtexTrustOpsApiRepository.standard(
              baseUrl: widget.baseUrl,
              accessToken: widget.accessToken,
              mode: widget.backendMode,
            ));
    _future = _repository.load();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GtexTrustOpsState>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<GtexTrustOpsState> snapshot,
      ) {
        if (snapshot.hasError) {
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: GtexPanel(
                title: 'Live trust ops unavailable',
                subtitle:
                    'Admin Trust Ops requires the live operations-readiness authority. Demo queues are available only in explicit fixture tests.',
                accent: GtexColors.red,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      snapshot.error.toString(),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: GtexColors.textMuted,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.md),
                    GtexActionButton(
                      label: 'Retry live queues',
                      icon: Icons.refresh,
                      onPressed:
                          () => setState(() => _future = _repository.load()),
                    ),
                  ],
                ),
              ),
            ),
          );
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final GtexTrustOpsState state = snapshot.data!;
        final GtexKycCaseRecord? selectedKyc = _selectedKycCase(state);
        final GtexDisputeRecord? selectedDispute = _selectedDispute(state);
        final GtexOrderRecord? selectedOrder = _selectedOrder(state);

        return GtexMasterDetailScaffold(
          title: 'Admin Trust Operations',
          subtitle:
              'KYC, disputes, orders, withdrawals and wallet risk review for GTEX operators.',
          mobileLeftTitle: 'Admin queues',
          leftPanelWidth: 320,
          rightPanelWidth: 370,
          accent: GtexColors.gold,
          actions: <Widget>[
            IconButton.filledTonal(
              tooltip: 'Refresh queues',
              onPressed: () => setState(() => _future = _repository.load()),
              icon: const Icon(Icons.sync),
            ),
          ],
          leftPanel: GtexTrustContextPanel(
            selectedModule: _selectedModule,
            onModuleSelected:
                (GtexTrustModule value) =>
                    setState(() => _selectedModule = value),
            state: state,
            adminMode: true,
          ),
          detail: _buildQueue(state),
          rightPanel: GtexTrustRightSummaryPanel(
            state: state,
            selectedOrder: selectedOrder,
            selectedDispute: selectedDispute,
            selectedKycCase: selectedKyc,
            adminMode: true,
            kycReviewBusy: _kycReviewBusy,
            disputeReplyBusy: _disputeReplyBusy,
            orderReviewBusy: _orderReviewBusy,
            onApproveKyc:
                selectedKyc == null
                    ? null
                    : () => _reviewSelectedKyc(approve: true),
            onRejectKyc:
                selectedKyc == null
                    ? null
                    : () => _reviewSelectedKyc(approve: false),
            onReplyDispute:
                selectedDispute == null ? null : _promptDisputeReply,
            onApproveOrder:
                selectedOrder == null
                    ? null
                    : () => _reviewSelectedOrder(approve: true),
            onRejectOrder:
                selectedOrder == null
                    ? null
                    : () => _reviewSelectedOrder(approve: false),
            onTopUp: _showAdminActionUnavailable,
            onWithdraw: _showAdminActionUnavailable,
          ),
        );
      },
    );
  }

  Widget _buildQueue(GtexTrustOpsState state) {
    switch (_selectedModule) {
      case GtexTrustModule.kyc:
        return GtexKycPanel(
          kycCases: state.kycCases,
          selectedCaseId: _selectedKycCaseId,
          onSelectCase: (String id) => setState(() => _selectedKycCaseId = id),
          adminMode: true,
        );
      case GtexTrustModule.disputes:
        return GtexDisputesPanel(
          disputes: state.disputes,
          selectedDisputeId: _selectedDisputeId,
          onSelectDispute:
              (String id) => setState(() => _selectedDisputeId = id),
          onCreateDispute: _showAdminActionUnavailable,
        );
      case GtexTrustModule.orders:
        return GtexOrdersPanel(
          orders: state.orders,
          selectedOrderId: _selectedOrderId,
          onSelectOrder: (String id) => setState(() => _selectedOrderId = id),
        );
      case GtexTrustModule.wallet:
        return GtexWalletOverviewPanel(
          state: state,
          onTopUp: _showAdminActionUnavailable,
          onWithdraw: _showAdminActionUnavailable,
        );
    }
  }

  void _showAdminActionUnavailable() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Admin trust actions require a mounted audited endpoint.',
        ),
      ),
    );
  }

  Future<void> _reviewSelectedKyc({required bool approve}) async {
    final GtexTrustOpsState state = await _future;
    if (!mounted) {
      return;
    }
    final GtexKycCaseRecord? selected = _selectedKycCase(state);
    if (selected == null) {
      return;
    }
    setState(() => _kycReviewBusy = true);
    try {
      await _repository.reviewKyc(
        selected.id,
        approve: approve,
        rejectionReason: approve ? null : 'Rejected by trust ops',
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            approve
                ? 'KYC ${selected.id} verified.'
                : 'KYC ${selected.id} rejected.',
          ),
        ),
      );
      setState(() {
        _kycReviewBusy = false;
        _future = _repository.load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _kycReviewBusy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('KYC review failed: $error')),
      );
    }
  }

  Future<void> _promptDisputeReply() async {
    final GtexTrustOpsState state = await _future;
    if (!mounted) {
      return;
    }
    final GtexDisputeRecord? selected = _selectedDispute(state);
    if (selected == null) {
      return;
    }
    final TextEditingController controller = TextEditingController(
      text:
          'We reviewed dispute ${selected.id}. Please reply with any additional details.',
    );
    final String? message = await showDialog<String>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Reply to dispute'),
          content: TextField(
            controller: controller,
            maxLines: 5,
            decoration: const InputDecoration(
              labelText: 'Admin message',
              border: OutlineInputBorder(),
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(controller.text),
              child: const Text('Send reply'),
            ),
          ],
        );
      },
    );
    controller.dispose();
    if (message == null || !mounted) {
      return;
    }
    final String trimmed = message.trim();
    if (trimmed.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Dispute reply message is required.')),
      );
      return;
    }
    setState(() => _disputeReplyBusy = true);
    try {
      await _repository.replyToDispute(selected.id, message: trimmed);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Reply sent on dispute ${selected.id}.')),
      );
      setState(() {
        _disputeReplyBusy = false;
        _future = _repository.load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _disputeReplyBusy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Dispute reply failed: $error')),
      );
    }
  }

  Future<void> _reviewSelectedOrder({required bool approve}) async {
    final GtexTrustOpsState state = await _future;
    if (!mounted) {
      return;
    }
    final GtexOrderRecord? selected = _selectedOrder(state);
    if (selected == null || !selected.isReviewable) {
      return;
    }
    setState(() => _orderReviewBusy = true);
    try {
      await _repository.reviewOrder(
        selected.id,
        approve: approve,
        kind: selected.kind,
        notes: approve ? null : 'Rejected by trust ops',
      );
      if (!mounted) {
        return;
      }
      final String kindLabel =
          selected.kind == GtexOrderKind.withdrawal
              ? 'Withdrawal'
              : 'Purchase order';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            approve
                ? '$kindLabel ${selected.id} approved.'
                : '$kindLabel ${selected.id} rejected.',
          ),
        ),
      );
      setState(() {
        _orderReviewBusy = false;
        _future = _repository.load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _orderReviewBusy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Order review failed: $error')),
      );
    }
  }

  GtexKycCaseRecord? _selectedKycCase(GtexTrustOpsState state) {
    if (_selectedKycCaseId == null) {
      return _selectedModule == GtexTrustModule.kyc && state.kycCases.isNotEmpty
          ? state.kycCases.first
          : null;
    }
    return state.kycCases
        .where((GtexKycCaseRecord item) => item.id == _selectedKycCaseId)
        .firstOrNull;
  }

  GtexDisputeRecord? _selectedDispute(GtexTrustOpsState state) {
    if (_selectedDisputeId == null) {
      return _selectedModule == GtexTrustModule.disputes &&
              state.disputes.isNotEmpty
          ? state.disputes.first
          : null;
    }
    return state.disputes
        .where((GtexDisputeRecord item) => item.id == _selectedDisputeId)
        .firstOrNull;
  }

  GtexOrderRecord? _selectedOrder(GtexTrustOpsState state) {
    if (_selectedOrderId == null) {
      return _selectedModule == GtexTrustModule.orders &&
              state.orders.isNotEmpty
          ? state.orders.first
          : null;
    }
    return state.orders
        .where((GtexOrderRecord item) => item.id == _selectedOrderId)
        .firstOrNull;
  }
}

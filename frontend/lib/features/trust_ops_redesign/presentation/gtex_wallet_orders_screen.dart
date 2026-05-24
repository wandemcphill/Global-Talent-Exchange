import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../data/gtex_trust_ops_demo_repository.dart';
import '../models/gtex_trust_ops_models.dart';
import '../widgets/gtex_kyc_dispute_widgets.dart';
import '../widgets/gtex_trust_context_panel.dart';
import '../widgets/gtex_wallet_order_widgets.dart';

class GtexWalletOrdersScreen extends StatefulWidget {
  const GtexWalletOrdersScreen({
    super.key,
    this.repository,
    this.initialModule = GtexTrustModule.wallet,
    this.onTopUp,
    this.onWithdraw,
    this.onCreateDispute,
  });

  final GtexTrustOpsRepository? repository;
  final GtexTrustModule initialModule;
  final VoidCallback? onTopUp;
  final VoidCallback? onWithdraw;
  final VoidCallback? onCreateDispute;

  @override
  State<GtexWalletOrdersScreen> createState() => _GtexWalletOrdersScreenState();
}

class _GtexWalletOrdersScreenState extends State<GtexWalletOrdersScreen> {
  late Future<GtexTrustOpsState> _future;
  late GtexTrustModule _selectedModule;
  String? _selectedOrderId;
  String? _selectedDisputeId;
  String? _selectedKycCaseId;

  @override
  void initState() {
    super.initState();
    _selectedModule = widget.initialModule;
    _future =
        widget.repository?.load() ??
        Future<GtexTrustOpsState>.error(
          StateError('Trust operations repository is not configured.'),
        );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.repository == null) {
      return const GtexEmptyState(
        title: 'Trust data unavailable',
        message:
            'This wallet trust workspace needs a live trust-ops repository. Demo data is available only in explicit fixture mode.',
        icon: Icons.lock_outline,
      );
    }
    return FutureBuilder<GtexTrustOpsState>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<GtexTrustOpsState> snapshot,
      ) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final GtexTrustOpsState state = snapshot.data!;
        final GtexOrderRecord? selectedOrder = _selectedOrder(state);
        final GtexDisputeRecord? selectedDispute = _selectedDispute(state);
        final GtexKycCaseRecord? selectedKyc = _selectedKycCase(state);

        return GtexMasterDetailScaffold(
          title: 'Wallet, Orders & Trust Center',
          subtitle:
              'Top up, withdraw, track orders, verify identity and resolve disputes without leaving the GTEX shell.',
          mobileLeftTitle: 'Wallet menu',
          leftPanelWidth: 310,
          rightPanelWidth: 350,
          actions: <Widget>[
            IconButton.filledTonal(
              tooltip: 'Refresh wallet',
              onPressed:
                  () => setState(() => _future = widget.repository!.load()),
              icon: const Icon(Icons.sync),
            ),
          ],
          leftPanel: GtexTrustContextPanel(
            selectedModule: _selectedModule,
            onModuleSelected:
                (GtexTrustModule value) =>
                    setState(() => _selectedModule = value),
            state: state,
          ),
          detail: _buildDetail(state),
          rightPanel: GtexTrustRightSummaryPanel(
            state: state,
            selectedOrder: selectedOrder,
            selectedDispute: selectedDispute,
            selectedKycCase: selectedKyc,
            onTopUp: widget.onTopUp ?? _showTopUpComingSoon,
            onWithdraw: widget.onWithdraw ?? _showWithdrawComingSoon,
          ),
        );
      },
    );
  }

  Widget _buildDetail(GtexTrustOpsState state) {
    switch (_selectedModule) {
      case GtexTrustModule.wallet:
        return GtexWalletOverviewPanel(
          state: state,
          onTopUp: widget.onTopUp ?? _showTopUpComingSoon,
          onWithdraw: widget.onWithdraw ?? _showWithdrawComingSoon,
        );
      case GtexTrustModule.orders:
        return GtexOrdersPanel(
          orders: state.orders,
          selectedOrderId: _selectedOrderId,
          onSelectOrder: (String id) => setState(() => _selectedOrderId = id),
        );
      case GtexTrustModule.kyc:
        return GtexKycPanel(
          kycCases: state.kycCases.take(1).toList(growable: false),
          selectedCaseId: _selectedKycCaseId,
          onSelectCase: (String id) => setState(() => _selectedKycCaseId = id),
        );
      case GtexTrustModule.disputes:
        return GtexDisputesPanel(
          disputes: state.disputes,
          selectedDisputeId: _selectedDisputeId,
          onSelectDispute:
              (String id) => setState(() => _selectedDisputeId = id),
          onCreateDispute:
              widget.onCreateDispute ?? _showCreateDisputeComingSoon,
        );
    }
  }

  GtexOrderRecord? _selectedOrder(GtexTrustOpsState state) {
    if (_selectedOrderId == null) {
      return state.orders.isEmpty ? null : state.orders.first;
    }
    return state.orders
        .where((GtexOrderRecord item) => item.id == _selectedOrderId)
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

  void _showTopUpComingSoon() =>
      _snack('Wire this to the existing top-up flow.');
  void _showWithdrawComingSoon() =>
      _snack('Wire this to the existing withdrawal flow.');
  void _showCreateDisputeComingSoon() =>
      _snack('Wire this to the existing create-dispute flow.');

  void _snack(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}

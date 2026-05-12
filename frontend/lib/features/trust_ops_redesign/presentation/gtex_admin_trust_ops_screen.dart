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

  @override
  void initState() {
    super.initState();
    _repository =
        widget.repository ??
        GtexTrustOpsApiRepository.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
        );
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
            onTopUp: () {},
            onWithdraw: () {},
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
          onCreateDispute: () {},
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
          onTopUp: () {},
          onWithdraw: () {},
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

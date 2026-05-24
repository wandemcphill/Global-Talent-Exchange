import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../data/gtex_trust_ops_demo_repository.dart';
import '../models/gtex_trust_ops_models.dart';
import '../widgets/gtex_kyc_dispute_widgets.dart';
import '../widgets/gtex_trust_context_panel.dart';
import '../widgets/gtex_wallet_order_widgets.dart';

class GtexKycDisputesScreen extends StatefulWidget {
  const GtexKycDisputesScreen({
    super.key,
    this.repository,
    this.initialModule = GtexTrustModule.kyc,
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
  State<GtexKycDisputesScreen> createState() => _GtexKycDisputesScreenState();
}

class _GtexKycDisputesScreenState extends State<GtexKycDisputesScreen> {
  late Future<GtexTrustOpsState> _future;
  late GtexTrustModule _selectedModule;
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
            'KYC and dispute screens need a live trust-ops repository. Demo data is available only in explicit fixture mode.',
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
        return GtexMasterDetailScaffold(
          title: 'KYC & Dispute Center',
          subtitle:
              'Identity verification and case resolution in one GTEX trust workspace.',
          mobileLeftTitle: 'Trust menu',
          leftPanel: GtexTrustContextPanel(
            selectedModule: _selectedModule,
            onModuleSelected:
                (GtexTrustModule value) =>
                    setState(() => _selectedModule = value),
            state: state,
          ),
          detail:
              _selectedModule == GtexTrustModule.disputes
                  ? GtexDisputesPanel(
                    disputes: state.disputes,
                    selectedDisputeId: _selectedDisputeId,
                    onSelectDispute:
                        (String id) => setState(() => _selectedDisputeId = id),
                    onCreateDispute:
                        widget.onCreateDispute ?? _showCreateDisputeUnavailable,
                  )
                  : GtexKycPanel(
                    kycCases: state.kycCases.take(1).toList(growable: false),
                    selectedCaseId: _selectedKycCaseId,
                    onSelectCase:
                        (String id) => setState(() => _selectedKycCaseId = id),
                  ),
          rightPanel: GtexTrustRightSummaryPanel(
            state: state,
            selectedDispute:
                state.disputes
                    .where(
                      (GtexDisputeRecord item) => item.id == _selectedDisputeId,
                    )
                    .firstOrNull,
            selectedKycCase:
                state.kycCases
                    .where(
                      (GtexKycCaseRecord item) => item.id == _selectedKycCaseId,
                    )
                    .firstOrNull,
            onTopUp: widget.onTopUp ?? _showTopUpUnavailable,
            onWithdraw: widget.onWithdraw ?? _showWithdrawUnavailable,
          ),
        );
      },
    );
  }

  void _showTopUpUnavailable() =>
      _snack('Open the wallet route to use the live top-up flow.');

  void _showWithdrawUnavailable() =>
      _snack('Open the wallet route to use the live withdrawal flow.');

  void _showCreateDisputeUnavailable() =>
      _snack('Create-dispute routing is not mounted for this entry point yet.');

  void _snack(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}

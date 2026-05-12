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
    this.repository = const GtexTrustOpsDemoRepository(),
    this.initialModule = GtexTrustModule.kyc,
    this.onCreateDispute,
  });

  final GtexTrustOpsRepository repository;
  final GtexTrustModule initialModule;
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
    _future = widget.repository.load();
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
                    onCreateDispute: widget.onCreateDispute ?? () {},
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
            onTopUp: () {},
            onWithdraw: () {},
          ),
        );
      },
    );
  }
}

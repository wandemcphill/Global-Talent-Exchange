import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_trust_ops_models.dart';

class GtexKycPanel extends StatelessWidget {
  const GtexKycPanel({
    super.key,
    required this.kycCases,
    required this.selectedCaseId,
    required this.onSelectCase,
    this.adminMode = false,
  });

  final List<GtexKycCaseRecord> kycCases;
  final String? selectedCaseId;
  final ValueChanged<String> onSelectCase;
  final bool adminMode;

  @override
  Widget build(BuildContext context) {
    if (kycCases.isEmpty) {
      return const GtexEmptyState(
        title: 'No KYC records',
        message: 'KYC submissions and verification status will appear here.',
        icon: Icons.verified_user_outlined,
      );
    }
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        if (!adminMode)
          GtexPanel(
            title: 'Your KYC status',
            subtitle:
                'Verification unlocks wallet withdrawals, higher limits, tournaments and marketplace payments.',
            accent: GtexColors.pitch,
            child: const _KycChecklist(),
          ),
        if (!adminMode) const SizedBox(height: GtexSpacing.md),
        for (final GtexKycCaseRecord item in kycCases) ...<Widget>[
          GtexPanel(
            isSelected: selectedCaseId == item.id,
            onTap: () => onSelectCase(item.id),
            accent: GtexTrustFormatters.statusColor(item.status),
            title: item.userName,
            subtitle: item.notes,
            trailing: GtexStatusChip(
              label: GtexTrustFormatters.statusLabel(item.status),
              color: GtexTrustFormatters.statusColor(item.status),
              compact: true,
            ),
            child: Wrap(
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.xs,
              children: <Widget>[
                GtexStatusChip(
                  label: item.country,
                  color: GtexColors.cyan,
                  compact: true,
                ),
                GtexStatusChip(
                  label: item.level,
                  color: GtexColors.gold,
                  compact: true,
                ),
                GtexStatusChip(
                  label: item.riskLabel,
                  color: GtexColors.orange,
                  compact: true,
                ),
              ],
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
        ],
      ],
    );
  }
}

class GtexDisputesPanel extends StatelessWidget {
  const GtexDisputesPanel({
    super.key,
    required this.disputes,
    required this.selectedDisputeId,
    required this.onSelectDispute,
    required this.onCreateDispute,
  });

  final List<GtexDisputeRecord> disputes;
  final String? selectedDisputeId;
  final ValueChanged<String> onSelectDispute;
  final VoidCallback onCreateDispute;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                'Disputes',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            GtexActionButton(
              label: 'New dispute',
              icon: Icons.add,
              compact: true,
              onPressed: onCreateDispute,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        if (disputes.isEmpty)
          const GtexEmptyState(
            title: 'No disputes',
            message:
                'Escrow, order, player rental and wallet disputes will appear here.',
            icon: Icons.support_agent_outlined,
          )
        else
          for (final GtexDisputeRecord dispute in disputes) ...<Widget>[
            GtexPanel(
              isSelected: selectedDisputeId == dispute.id,
              onTap: () => onSelectDispute(dispute.id),
              accent: GtexTrustFormatters.statusColor(dispute.status),
              title: dispute.title,
              subtitle: dispute.summary,
              trailing: Text(
                dispute.amountLabel,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: GtexColors.gold,
                  fontWeight: FontWeight.w900,
                ),
              ),
              child: Wrap(
                spacing: GtexSpacing.sm,
                children: <Widget>[
                  GtexStatusChip(
                    label: GtexTrustFormatters.statusLabel(dispute.status),
                    color: GtexTrustFormatters.statusColor(dispute.status),
                    compact: true,
                  ),
                  GtexStatusChip(
                    label: dispute.counterparty,
                    color: GtexColors.cyan,
                    compact: true,
                  ),
                  GtexStatusChip(
                    label: dispute.openedLabel,
                    color: GtexColors.gold,
                    compact: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: GtexSpacing.sm),
          ],
      ],
    );
  }
}

class _KycChecklist extends StatelessWidget {
  const _KycChecklist();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: const <Widget>[
        _ChecklistRow(label: 'Identity document uploaded', done: true),
        _ChecklistRow(label: 'Selfie / liveness check', done: true),
        _ChecklistRow(label: 'Address or bank verification', done: true),
        _ChecklistRow(label: 'Admin review complete', done: true),
      ],
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({required this.label, required this.done});
  final String label;
  final bool done;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: <Widget>[
          Icon(
            done ? Icons.check_circle : Icons.radio_button_unchecked,
            color: done ? GtexColors.pitch : GtexColors.textMuted,
            size: 18,
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GtexColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}

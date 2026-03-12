import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/screens/competitions/competition_share_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_financial_breakdown_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_payout_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_status_badge.dart';
import 'package:gte_frontend/widgets/competitions/competition_visibility_chip.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionPublishPreviewScreen extends StatefulWidget {
  const CompetitionPublishPreviewScreen({
    super.key,
    required this.controller,
  });

  final CompetitionController controller;

  @override
  State<CompetitionPublishPreviewScreen> createState() =>
      _CompetitionPublishPreviewScreenState();
}

class _CompetitionPublishPreviewScreenState
    extends State<CompetitionPublishPreviewScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Publish preview'),
      ),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, Widget? child) {
          final preview = widget.controller.previewSummary;
          final financials = widget.controller.previewFinancials;
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                preview.name,
                                style: Theme.of(context).textTheme.headlineSmall,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                '${preview.safeFormatLabel} • Creator competition by ${preview.creatorLabel}',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                        CompetitionStatusBadge(status: preview.status),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        CompetitionVisibilityChip(visibility: preview.visibility),
                        Material(
                          color: Colors.transparent,
                          child: Chip(
                            label: Text('Contest status: ${preview.status.name}'),
                          ),
                        ),
                        if (preview.beginnerFriendly == true)
                          const Material(
                            color: Colors.transparent,
                            child: Chip(label: Text('Beginner friendly')),
                          ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      preview.rulesSummary,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              CompetitionFinancialBreakdownCard(
                title: 'Projected financials',
                entryFee: financials.entryFee,
                participantCount: financials.participantCount,
                platformFeePct: preview.platformFeePct,
                platformFeeAmount: financials.platformFeeAmount,
                hostFeePct: preview.hostFeePct,
                hostFeeAmount: financials.hostFeeAmount,
                prizePool: financials.prizePool,
                currency: financials.currency,
                projected: true,
                lockNotice:
                    'After the first paid entry clears, fee settings and transparent payout lock for participant safety.',
              ),
              const SizedBox(height: 16),
              CompetitionPayoutCard(
                title: 'Projected payout',
                currency: preview.currency,
                payouts: financials.payoutStructure,
              ),
              if (widget.controller.actionError != null) ...<Widget>[
                const SizedBox(height: 16),
                GteStatePanel(
                  title: 'Publish blocked',
                  message: widget.controller.actionError!,
                  icon: Icons.info_outline,
                ),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: widget.controller.isPublishing ? null : _publish,
                child: Text(
                  widget.controller.isPublishing
                      ? 'Publishing...'
                      : 'Publish competition',
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _publish() async {
    final result = await widget.controller.publishDraft();
    if (!mounted || result == null) {
      return;
    }
    await Navigator.of(context).pushReplacement<void, void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionShareScreen(
          controller: widget.controller,
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/competition_join_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_share_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_financial_breakdown_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_payout_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_status_badge.dart';
import 'package:gte_frontend/widgets/competitions/competition_visibility_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionDetailScreen extends StatefulWidget {
  const CompetitionDetailScreen({
    super.key,
    required this.controller,
    required this.competitionId,
  });

  final CompetitionController controller;
  final String competitionId;

  @override
  State<CompetitionDetailScreen> createState() => _CompetitionDetailScreenState();
}

class _CompetitionDetailScreenState extends State<CompetitionDetailScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.openCompetition(widget.competitionId);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Competition detail'),
        ),
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            final CompetitionSummary? competition =
                widget.controller.selectedCompetition;
            final CompetitionFinancialSummary? financials =
                widget.controller.selectedFinancials;
            if (widget.controller.isLoadingDetail && competition == null) {
              return const Center(child: CircularProgressIndicator());
            }
            if (widget.controller.detailError != null && competition == null) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Competition detail unavailable',
                  message: widget.controller.detailError!,
                  actionLabel: 'Retry',
                  onAction: () {
                    widget.controller.openCompetition(widget.competitionId);
                  },
                  icon: Icons.groups_outlined,
                ),
              );
            }
            if (competition == null || financials == null) {
              return const SizedBox.shrink();
            }

            final String lockNotice = competition.isLockedForPaidEntryEdits
                ? 'Paid entries have begun. Entry fee, platform service fee, host fee, and payout settings are now locked for participant safety.'
                : competition.isFreeToJoin
                    ? 'This community competition is free to join, so no fee lock is required.'
                    : 'Once the first paid entry clears, fee settings lock to protect participants.';

            return RefreshIndicator(
              onRefresh: () => widget.controller.openCompetition(widget.competitionId),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
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
                                    competition.name,
                                    style:
                                        Theme.of(context).textTheme.headlineSmall,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    '${competition.safeFormatLabel} • Creator competition by ${competition.creatorLabel}',
                                    style: Theme.of(context).textTheme.bodyMedium,
                                  ),
                                ],
                              ),
                            ),
                            CompetitionStatusBadge(status: competition.status),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            CompetitionVisibilityChip(
                              visibility: competition.visibility,
                            ),
                            Material(
                              color: Colors.transparent,
                              child: Chip(
                                label: Text(
                                  'Contest status: ${competition.status.name}',
                                ),
                              ),
                            ),
                            Material(
                              color: Colors.transparent,
                              child: Chip(
                                label: Text(
                                  'Players ${competition.participantCount}/${competition.capacity}',
                                ),
                              ),
                            ),
                            if (competition.beginnerFriendly == true)
                              const Material(
                                color: Colors.transparent,
                                child: Chip(label: Text('Beginner friendly')),
                              ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          competition.rulesSummary,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 18),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.icon(
                              onPressed: competition.joinEligibility.eligible
                                  ? _openJoin
                                  : null,
                              icon: const Icon(Icons.group_add_outlined),
                              label: const Text('Join competition'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: _openShare,
                              icon: const Icon(Icons.share_outlined),
                              label: const Text('Share'),
                            ),
                          ],
                        ),
                        if (!competition.joinEligibility.eligible) ...<Widget>[
                          const SizedBox(height: 12),
                          Text(
                            widget.controller.formatJoinReason(
                              competition.joinEligibility.reason,
                            ),
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  CompetitionFinancialBreakdownCard(
                    title: 'Transparent financials',
                    entryFee: financials.entryFee,
                    participantCount: financials.participantCount,
                    platformFeePct: competition.platformFeePct,
                    platformFeeAmount: financials.platformFeeAmount,
                    hostFeePct: competition.hostFeePct,
                    hostFeeAmount: financials.hostFeeAmount,
                    prizePool: financials.prizePool,
                    currency: financials.currency,
                    lockNotice: lockNotice,
                  ),
                  const SizedBox(height: 16),
                  CompetitionPayoutCard(
                    title: 'Transparent payout',
                    currency: competition.currency,
                    payouts: financials.payoutStructure,
                  ),
                  const SizedBox(height: 16),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Rules summary',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          competition.rulesSummary,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 16),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            const Icon(
                              Icons.policy_outlined,
                              color: GteShellTheme.accent,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'This community competition settles only through published rules and verified player performance. No house-banked outcomes or sports-style pricing appears in this flow.',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Future<void> _openJoin() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionJoinScreen(
          controller: widget.controller,
        ),
      ),
    );
  }

  Future<void> _openShare() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionShareScreen(
          controller: widget.controller,
        ),
      ),
    );
  }
}

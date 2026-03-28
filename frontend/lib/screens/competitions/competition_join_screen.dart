import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/competitions/competition_financial_breakdown_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_payout_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionJoinScreen extends StatefulWidget {
  const CompetitionJoinScreen({super.key, required this.controller});

  final CompetitionController controller;

  @override
  State<CompetitionJoinScreen> createState() => _CompetitionJoinScreenState();
}

class _CompetitionJoinScreenState extends State<CompetitionJoinScreen> {
  bool _agreed = false;
  final TextEditingController _inviteCodeController = TextEditingController();

  @override
  void dispose() {
    _inviteCodeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Join competition')),
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            final CompetitionSummary? competition =
                widget.controller.selectedCompetition;
            final CompetitionFinancialSummary? financials =
                widget.controller.selectedFinancials;
            if (competition == null || financials == null) {
              return const SizedBox.shrink();
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Join ${competition.name}',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        competition.isGtexHosted
                            ? 'GTEX is funding this competition, so entry is free. Review the rules before you lock your place.'
                            : competition.isFastMatch
                            ? 'Fast Match is a paid lane. Review the wallet charge and rules before you lock your slot.'
                            : 'Review entry fee, rules, and contest status before you confirm your place in this hosted competition.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (competition
                          .joinEligibility
                          .requiresInvite) ...<Widget>[
                        const SizedBox(height: 16),
                        TextField(
                          controller: _inviteCodeController,
                          decoration: const InputDecoration(
                            labelText: 'Invite code',
                            hintText: 'Enter creator invite code',
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  accentColor:
                      competition.isGtexHosted
                          ? Colors.green
                          : competition.isFastMatch
                          ? GteShellTheme.accentWarm
                          : GteShellTheme.accentCapital,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Icon(
                        competition.isGtexHosted
                            ? Icons.celebration_outlined
                            : Icons.account_balance_wallet_outlined,
                        color:
                            competition.isGtexHosted
                                ? Colors.green
                                : competition.isFastMatch
                                ? GteShellTheme.accentWarm
                                : GteShellTheme.accentCapital,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          competition.economyNotice,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                CompetitionFinancialBreakdownCard(
                  title: 'Entry summary',
                  entryFee: financials.entryFee,
                  participantCount: financials.participantCount,
                  platformFeePct: competition.platformFeePct,
                  platformFeeAmount: financials.platformFeeAmount,
                  hostFeePct: competition.hostFeePct,
                  hostFeeAmount: financials.hostFeeAmount,
                  prizePool: financials.prizePool,
                  currency: financials.currency,
                  matchType: competition.matchType,
                  lockNotice:
                      competition.isLockedForPaidEntryEdits
                          ? 'Paid entries have begun, so these settings are locked.'
                          : 'If this is a paid competition, settings lock once the first paid entry clears.',
                ),
                const SizedBox(height: 16),
                CompetitionPayoutCard(
                  title: 'Published payout',
                  currency: competition.currency,
                  payouts: financials.payoutStructure,
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentWarm,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Icon(
                        Icons.verified_outlined,
                        color: GteShellTheme.accentWarm,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'GTEX promotional pools fund platform-run competitions. Outcomes follow published rules and verified performance, not betting odds.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: CheckboxListTile(
                    value: _agreed,
                    contentPadding: EdgeInsets.zero,
                    onChanged: (bool? value) {
                      setState(() {
                        _agreed = value ?? false;
                      });
                    },
                    title: const Text('I understand the published rules'),
                    subtitle: Text(
                      competition.isGtexHosted
                          ? 'I understand this GTEX-hosted competition is free to join and the payout follows the published rules and verified results.'
                          : competition.isFastMatch
                          ? 'I understand this fast-match entry is paid from my wallet and the payout follows the published rules and verified results.'
                          : 'I understand that entry fees are held in secure escrow and the transparent payout follows the published rules and verified results.',
                    ),
                  ),
                ),
                if (widget.controller.actionError != null) ...<Widget>[
                  const SizedBox(height: 16),
                  GteStatePanel(
                    title: 'Unable to join yet',
                    message: widget.controller.actionError!,
                    icon: Icons.info_outline,
                  ),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed:
                      !_agreed || widget.controller.isJoining
                          ? null
                          : _joinCompetition,
                  child: Text(
                    widget.controller.isJoining
                        ? 'Joining...'
                        : competition.entryButtonLabel,
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _joinCompetition() async {
    final CompetitionSummary? joined = await widget.controller
        .joinSelectedCompetition(
          inviteCode:
              _inviteCodeController.text.trim().isEmpty
                  ? null
                  : _inviteCodeController.text.trim(),
        );
    if (!mounted || joined == null) {
      return;
    }
    Navigator.of(context).pop();
  }
}

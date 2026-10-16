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
  final TextEditingController _passcodeController = TextEditingController();

  @override
  void dispose() {
    _inviteCodeController.dispose();
    _passcodeController.dispose();
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
                        _introCopy(competition),
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
                      if (competition.requiresPasscode ||
                          competition
                              .joinEligibility
                              .requiresPasscode) ...<Widget>[
                        const SizedBox(height: 16),
                        TextField(
                          controller: _passcodeController,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Competition passcode',
                            hintText: 'Enter passcode to join',
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
                if (competition.fastMatchEntitlement != null) ...<Widget>[
                  _FastMatchEntitlementPanel(
                    entitlement: competition.fastMatchEntitlement!,
                  ),
                  const SizedBox(height: 16),
                ],
                if (competition.fastCupRegistration != null) ...<Widget>[
                  _FastCupEscrowPanel(
                    registration: competition.fastCupRegistration!,
                  ),
                  const SizedBox(height: 16),
                ],
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
                  grossPot: competition.grossPot,
                  netPayoutPot: financials.prizePool,
                  prizeMode: financials.prizeMode,
                  isRanked: financials.isRanked,
                  remainingSlots: financials.remainingSlots,
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
                    subtitle: Text(_acknowledgementCopy(competition)),
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
          passcode:
              _passcodeController.text.trim().isEmpty
                  ? null
                  : _passcodeController.text.trim(),
        );
    if (!mounted || joined == null) {
      return;
    }
    Navigator.of(context).pop();
  }
}

class _FastMatchEntitlementPanel extends StatelessWidget {
  const _FastMatchEntitlementPanel({required this.entitlement});

  final FastMatchEntitlementView entitlement;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor:
          entitlement.chargeRequiredNow
              ? GteShellTheme.accentCapital
              : GteShellTheme.accentWarm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Fast Match entitlement',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            entitlement.serverRuleLabel,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              Chip(
                label: Text(
                  '${entitlement.freeMatchesRemaining} free remaining',
                ),
              ),
              Chip(label: Text('${entitlement.freeMatchesUsed} used')),
              Chip(label: Text(entitlement.entryCurrencyLabel)),
              if (entitlement.chargeRequiredNow)
                Chip(label: Text('Fee ${entitlement.entryFeeLabel}')),
              Chip(label: Text(_humanizeStatus(entitlement.entitlementStatus))),
            ],
          ),
        ],
      ),
    );
  }
}

class _FastCupEscrowPanel extends StatelessWidget {
  const _FastCupEscrowPanel({required this.registration});

  final FastCupRegistrationView registration;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor:
          registration.isEscrowBacked
              ? GteShellTheme.accent
              : GteShellTheme.accentWarm,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(
            registration.isEscrowBacked
                ? Icons.lock_outline
                : Icons.pending_actions_outlined,
            color:
                registration.isEscrowBacked
                    ? GteShellTheme.accent
                    : GteShellTheme.accentWarm,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Fast Cup escrow',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Entry fee ${registration.entryFeeLabel}; escrow status ${registration.escrowStatusLabel.toLowerCase()}.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                if (registration.walletLedgerId?.trim().isNotEmpty ==
                    true) ...<Widget>[
                  const SizedBox(height: 8),
                  Text(
                    'Ledger ${registration.walletLedgerId}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String _introCopy(CompetitionSummary competition) {
  if (competition.isGtexHosted) {
    return 'GTEX is funding this competition, so entry is free. Review the rules before you lock your place.';
  }
  if (competition.isNationalCompetition) {
    return 'Club ranking is not required for national competitions. Entry depends on national team rental/build affordability and roster validity.';
  }
  if (competition.isFastMatch) {
    final FastMatchEntitlementView? entitlement =
        competition.fastMatchEntitlement;
    if (entitlement == null) {
      return 'Quick Match checks your server entitlement before kickoff and uses Fan Coin when a paid entry is required.';
    }
    return entitlement.chargeRequiredNow
        ? 'Your free Fast Match run is exhausted, so ${entitlement.entryFeeLabel} is required before kickoff.'
        : 'Your server entitlement has ${entitlement.freeMatchesRemaining} free Fast Match run(s) remaining before Fan Coin is required.';
  }
  return 'Review Fan Coin entry fee, escrow state, rules, and start time before you confirm your place.';
}

String _acknowledgementCopy(CompetitionSummary competition) {
  if (competition.isGtexHosted) {
    return 'I understand this GTEX-hosted competition is free to join and the payout follows the published rules and verified results.';
  }
  if (competition.isNationalCompetition) {
    return 'I understand national entry is checked against rental/build affordability and roster rules, not club ranking.';
  }
  if (competition.isFastMatch) {
    final FastMatchEntitlementView? entitlement =
        competition.fastMatchEntitlement;
    if (entitlement == null) {
      return 'I understand Quick Match eligibility and Fan Coin charges are verified by the server before kickoff.';
    }
    return entitlement.chargeRequiredNow
        ? 'I understand this Fast Match requires ${entitlement.entryFeeLabel} before kickoff.'
        : 'I understand this Fast Match uses my persisted server free-run entitlement; draws count and the first loss ends the free run.';
  }
  final FastCupRegistrationView? registration = competition.fastCupRegistration;
  if (registration != null) {
    return 'I understand ${registration.entryFeeLabel} is held in secure escrow and payout follows the verified bracket.';
  }
  return 'I understand Fan Coin entry fees are held in secure escrow and the transparent payout follows the published rules and verified results.';
}

String _humanizeStatus(String value) {
  final String normalized = value.replaceAll('_', ' ').trim();
  if (normalized.isEmpty) {
    return value;
  }
  return normalized[0].toUpperCase() + normalized.substring(1);
}

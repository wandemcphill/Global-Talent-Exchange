import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/competitions/competition_share_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class CompetitionShareScreen extends StatefulWidget {
  const CompetitionShareScreen({
    super.key,
    required this.controller,
  });

  final CompetitionController controller;

  @override
  State<CompetitionShareScreen> createState() => _CompetitionShareScreenState();
}

class _CompetitionShareScreenState extends State<CompetitionShareScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.ensureInviteForSelectedCompetition();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Share competition'),
        ),
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            final CompetitionSummary? competition =
                widget.controller.selectedCompetition;
            final CompetitionInviteView? invite = widget.controller.latestInvite;
            if (competition == null) {
              return const SizedBox.shrink();
            }
            if (widget.controller.isCreatingInvite && invite == null) {
              return const Center(child: CircularProgressIndicator());
            }
            if (invite == null) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Invite unavailable',
                  message: widget.controller.actionError ??
                      'A shareable invite could not be generated yet.',
                  actionLabel: 'Generate invite',
                  onAction: () {
                    widget.controller.createInviteForCompetition(
                      competition.id,
                      note: '${competition.safeFormatLabel} invite',
                    );
                  },
                  icon: Icons.share_outlined,
                ),
              );
            }
            final String message = _buildShareMessage(competition, invite);
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                CompetitionShareCard(
                  competition: competition,
                  invite: invite,
                  message: message,
                  onCopyCode: () => _copy(invite.inviteCode, 'Invite code copied'),
                  onCopyMessage: () => _copy(message, 'Share message copied'),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _copy(String value, String notice) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(notice)),
    );
  }

  String _buildShareMessage(
    CompetitionSummary competition,
    CompetitionInviteView invite,
  ) {
    return 'Join my ${competition.safeFormatLabel.toLowerCase()} "${competition.name}". '
        'Entry fee: ${_formatAmount(competition.entryFee, competition.currency)}. '
        'Prize pool: ${_formatAmount(competition.prizePool, competition.currency)}. '
        'Invite code: ${invite.inviteCode}. '
        'Rules and transparent payout are published before join.';
  }
}

String _formatAmount(double value, String currency) {
  final bool whole = value == value.roundToDouble();
  final String number = value.toStringAsFixed(whole ? 0 : 2);
  if (currency.toLowerCase() == 'credit') {
    return '$number cr';
  }
  return '$number ${currency.toUpperCase()}';
}

import 'package:flutter/material.dart';

import '../../controllers/referral_controller.dart';
import '../../models/referral_models.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class ReferralInvitesScreen extends StatefulWidget {
  const ReferralInvitesScreen({
    super.key,
    required this.controller,
  });

  final ReferralController controller;

  @override
  State<ReferralInvitesScreen> createState() => _ReferralInvitesScreenState();
}

class _ReferralInvitesScreenState extends State<ReferralInvitesScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Referral invites')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, _) {
          if (widget.controller.isLoading && !widget.controller.hasData) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading invite attribution',
                message:
                    'Reviewing invites sent, qualified joins, and contest participation.',
                icon: Icons.mark_email_read_outlined,
              ),
            );
          }
          if (widget.controller.errorMessage != null && !widget.controller.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Referral invites unavailable',
                message: widget.controller.errorMessage!,
                icon: Icons.error_outline,
              ),
            );
          }

          final List<ReferralInviteEntry> invites = widget.controller.hub!.invites;
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            itemBuilder: (BuildContext context, int index) {
              final ReferralInviteEntry invite = invites[index];
              return GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            invite.inviteeLabel,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                        Chip(
                          label: Text(invite.isQualified ? 'Qualified' : 'Pending'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      invite.competitionLabel,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Channel: ${invite.channel.label}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      invite.statusLabel,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      invite.inviteAttributionLabel,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatDate(invite.sentAt),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              );
            },
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemCount: invites.length,
          );
        },
      ),
    );
  }
}

String _formatDate(DateTime date) {
  const List<String> months = <String>[
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  final String minute = date.minute.toString().padLeft(2, '0');
  return '${months[date.month - 1]} ${date.day}, ${date.year} - ${date.hour}:$minute UTC';
}

import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionShareCard extends StatelessWidget {
  const CompetitionShareCard({
    super.key,
    required this.competition,
    required this.invite,
    required this.message,
    this.onCopyCode,
    this.onCopyMessage,
  });

  final CompetitionSummary competition;
  final CompetitionInviteView invite;
  final String message;
  final VoidCallback? onCopyCode;
  final VoidCallback? onCopyMessage;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.share_outlined, color: GteShellTheme.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Share invite',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Invite players into this ${competition.safeFormatLabel.toLowerCase()} with a clear fee summary and published rules.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: GteShellTheme.stroke),
              color: GteShellTheme.panelStrong.withValues(alpha: 0.44),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Invite code', style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 4),
                SelectableText(
                  invite.inviteCode,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  invite.note ?? 'Creator competition invite',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Text('Share message', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SelectableText(
            message,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onCopyCode,
                icon: const Icon(Icons.copy_outlined),
                label: const Text('Copy code'),
              ),
              FilledButton(
                onPressed: onCopyMessage,
                child: const Text('Copy message'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class ClubLegacyPreseasonData {
  const ClubLegacyPreseasonData({
    required this.windowName,
    required this.invites,
    required this.history,
    required this.offers,
    required this.platformShare,
    required this.hostShare,
    required this.participantShare,
    required this.reputation,
    required this.audience,
    required this.money,
    required this.gmPolicy,
    required this.tournament,
  });

  final String windowName;
  final List<Map<String, dynamic>> invites;
  final List<Map<String, dynamic>> history;
  final List<Map<String, dynamic>> offers;
  final String platformShare;
  final String hostShare;
  final String participantShare;
  final int reputation;
  final int audience;
  final String money;
  final String gmPolicy;
  final String tournament;
}

class ClubLegacyPreseasonPanel extends StatelessWidget {
  const ClubLegacyPreseasonPanel({super.key, required this.data, required this.onAction});

  final ClubLegacyPreseasonData data;
  final void Function(String action) onAction;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('club-legacy-preseason-panel'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Window',
          subtitle: data.windowName,
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              for (final Map<String, dynamic> row in data.invites)
                Text('${row['match_on']} · ${row['status']} · ${row['appearance_fee']}', key: Key('club-preseason-invite-${row['id']}')),
              const SizedBox(height: GtexSpacing.sm),
              Text('GM policy ${data.gmPolicy}', key: const Key('club-preseason-gm')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Offers',
          subtitle: 'A counter keeps the previous offer',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              for (final Map<String, dynamic> row in data.offers)
                Text('${row['status']} · ${row['appearance_fee']} · ${row['match_on']}', key: Key('club-preseason-offer-${row['sequence']}')),
              for (final Map<String, dynamic> row in data.history)
                Text('${row['sequence']} · ${row['status']}', key: Key('club-preseason-history-${row['sequence']}')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Settlement',
          subtitle: 'Shares sum to 100 percent',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Platform ${data.platformShare}', key: const Key('club-preseason-platform')),
              Text('Host ${data.hostShare}', key: const Key('club-preseason-host')),
              Text('Participants ${data.participantShare}', key: const Key('club-preseason-participants')),
              Text('Reputation ${data.reputation}', key: const Key('club-preseason-reputation')),
              Text('Audience ${data.audience}', key: const Key('club-preseason-audience')),
              Text('Money ${data.money}', key: const Key('club-preseason-money')),
              Text(data.tournament, key: const Key('club-preseason-tournament')),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.xs,
          children: <Widget>[
            GtexActionButton(key: const Key('club-preseason-counter'), label: 'Counter', icon: Icons.reply, compact: true, onPressed: () => onAction('counter')),
            GtexActionButton(key: const Key('club-preseason-accept'), label: 'Accept', icon: Icons.check, compact: true, onPressed: () => onAction('accept')),
            GtexActionButton(key: const Key('club-preseason-reject'), label: 'Reject', icon: Icons.close, compact: true, secondary: true, onPressed: () => onAction('reject')),
            GtexActionButton(key: const Key('club-preseason-settle'), label: 'Settle', icon: Icons.payments_outlined, compact: true, secondary: true, onPressed: () => onAction('settle')),
          ],
        ),
      ],
    );
  }
}

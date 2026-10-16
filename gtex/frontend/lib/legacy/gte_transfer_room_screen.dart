import 'package:flutter/material.dart';

import '../data/gte_models.dart';
import 'gte_app_controller.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';

class GteTransferRoomScreen extends StatelessWidget {
  const GteTransferRoomScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
  });

  final GteAppController controller;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    final MarketPulse? pulse = controller.marketPulse;
    final List<TransferRoomEntry> entries =
        pulse?.transferRoom ?? const <TransferRoomEntry>[];

    return Theme(
      data: GteShellTheme.build(),
      child: Container(
        decoration: gteBackdropDecoration(),
        child: DefaultTabController(
          length: 3,
          child: Scaffold(
            appBar: AppBar(
              title: const Text('Transfer room'),
              bottom: const TabBar(
                tabs: <Widget>[
                  Tab(text: 'Platform Deals'),
                  Tab(text: 'User Market Deals'),
                  Tab(text: 'Announcements'),
                ],
              ),
            ),
            body: Column(
              children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                  child: GteSurfacePanel(
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Live acquisition signal',
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        Text(
                          'Platform deals, user market fills, and public announcements stay separated so deal context stays clean.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: TabBarView(
                    children: <Widget>[
                      _RoomLane(
                        entries: _entriesForLane(entries, 'Platform Deals'),
                        players: controller.transferRoomPlayers,
                        onOpenPlayer: onOpenPlayer,
                      ),
                      _RoomLane(
                        entries: _entriesForLane(entries, 'User Market Deals'),
                        players: controller.shortlistPlayers,
                        onOpenPlayer: onOpenPlayer,
                      ),
                      _RoomLane(
                        entries: _entriesForLane(entries, 'Announcements'),
                        players: controller.featuredPlayers
                            .take(3)
                            .toList(growable: false),
                        onOpenPlayer: onOpenPlayer,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RoomLane extends StatelessWidget {
  const _RoomLane({
    required this.entries,
    required this.players,
    required this.onOpenPlayer,
  });

  final List<TransferRoomEntry> entries;
  final List<PlayerSnapshot> players;
  final ValueChanged<String> onOpenPlayer;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      children: <Widget>[
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Feed', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 14),
              if (entries.isEmpty)
                Text('No entries in this lane yet.',
                    style: Theme.of(context).textTheme.bodyMedium)
              else
                ...entries.map(
                  (TransferRoomEntry entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(entry.headline,
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 4),
                        Text(entry.activity,
                            style: Theme.of(context).textTheme.bodyMedium),
                        const SizedBox(height: 4),
                        Text('${entry.marketCredits} cr',
                            style: Theme.of(context).textTheme.bodyLarge),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Suggested player routes',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 14),
              if (players.isEmpty)
                Text('No player routes available.',
                    style: Theme.of(context).textTheme.bodyMedium)
              else
                ...players.map(
                  (PlayerSnapshot player) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(player.name),
                    subtitle:
                        Text('${player.club} - ${player.marketCredits} cr'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => onOpenPlayer(player.id),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

List<TransferRoomEntry> _entriesForLane(
    List<TransferRoomEntry> entries, String lane) {
  return entries
      .where((TransferRoomEntry entry) => entry.lane == lane)
      .toList(growable: false);
}

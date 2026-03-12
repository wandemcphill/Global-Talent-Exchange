import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

import '../data/reputation_models.dart';
import 'reputation_event_tile.dart';

class ReputationTimelineList extends StatelessWidget {
  const ReputationTimelineList({
    super.key,
    required this.events,
    required this.emptyTitle,
    required this.emptyMessage,
  });

  final List<ReputationEventDto> events;
  final String emptyTitle;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return GteStatePanel(
        title: emptyTitle,
        message: emptyMessage,
        icon: Icons.auto_graph,
      );
    }
    return Column(
      children: events
          .map(
            (ReputationEventDto event) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: ReputationEventTile(event: event),
            ),
          )
          .toList(growable: false),
    );
  }
}

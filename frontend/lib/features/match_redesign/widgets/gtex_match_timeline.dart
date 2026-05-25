import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexMatchTimeline extends StatelessWidget {
  const GtexMatchTimeline({super.key, required this.events});

  final List<GtexMatchTimelineEvent> events;

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return const GtexMatchEmptyFeed(
        icon: Icons.timeline_rounded,
        title: 'Timeline unavailable',
        message:
            'The match authority has not returned timeline events for this fixture.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: events.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final event = events[index];
        final Color accent = _eventAccent(event.type);
        return Container(
          padding: const EdgeInsets.all(12),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: _eventBackground(event.type),
            borderColor: accent.withOpacity(.34),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 58,
                child: Column(
                  children: [
                    Icon(_eventIcon(event.type), color: accent, size: 20),
                    const SizedBox(height: 4),
                    Text(
                      '${event.minute}\'',
                      style: TextStyle(
                        color: accent,
                        fontFamily: 'JetBrains Mono',
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      event.playerName ?? event.title,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontWeight: FontWeight.w900,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      event.playerName == null
                          ? event.description
                          : event.title,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textSecondary,
                        height: 1.25,
                      ),
                    ),
                    if (event.playerName != null &&
                        event.description.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        event.description,
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.textSecondary,
                          fontSize: 12,
                          height: 1.25,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  IconData _eventIcon(GtexPitchEventType type) {
    switch (type) {
      case GtexPitchEventType.goal:
        return Icons.sports_soccer;
      case GtexPitchEventType.yellowCard:
        return Icons.crop_square;
      case GtexPitchEventType.redCard:
        return Icons.stop;
      case GtexPitchEventType.substitution:
        return Icons.swap_horiz;
      case GtexPitchEventType.save:
        return Icons.back_hand_outlined;
      case GtexPitchEventType.tacticalChange:
        return Icons.tune;
      case GtexPitchEventType.shot:
        return Icons.my_location;
      case GtexPitchEventType.foul:
        return Icons.report_outlined;
      case GtexPitchEventType.kickoff:
        return Icons.play_arrow;
      case GtexPitchEventType.pass:
      case GtexPitchEventType.tackle:
        return Icons.circle;
    }
  }

  Color _eventAccent(GtexPitchEventType type) {
    switch (type) {
      case GtexPitchEventType.goal:
        return const Color(0xFF00E87A);
      case GtexPitchEventType.yellowCard:
        return const Color(0xFFFFB800);
      case GtexPitchEventType.redCard:
      case GtexPitchEventType.foul:
        return const Color(0xFFFF3D3D);
      case GtexPitchEventType.substitution:
      case GtexPitchEventType.tacticalChange:
        return const Color(0xFF52A8FF);
      case GtexPitchEventType.kickoff:
      case GtexPitchEventType.shot:
      case GtexPitchEventType.pass:
      case GtexPitchEventType.tackle:
      case GtexPitchEventType.save:
        return GtexMatchVisualTokens.textSecondary;
    }
  }

  Color _eventBackground(GtexPitchEventType type) {
    switch (type) {
      case GtexPitchEventType.goal:
        return const Color(0xFF00E87A).withOpacity(.09);
      case GtexPitchEventType.yellowCard:
        return const Color(0xFFFFB800).withOpacity(.09);
      case GtexPitchEventType.redCard:
      case GtexPitchEventType.foul:
        return const Color(0xFFFF3D3D).withOpacity(.08);
      case GtexPitchEventType.substitution:
      case GtexPitchEventType.tacticalChange:
        return const Color(0xFF52A8FF).withOpacity(.08);
      case GtexPitchEventType.kickoff:
      case GtexPitchEventType.shot:
      case GtexPitchEventType.pass:
      case GtexPitchEventType.tackle:
      case GtexPitchEventType.save:
        return GtexMatchVisualTokens.surfaceOverlay;
    }
  }
}

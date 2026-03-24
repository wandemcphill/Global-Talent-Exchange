import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_event.dart';

class GtexEventOverlay extends StatelessWidget {
  const GtexEventOverlay({
    super.key,
    required this.event,
  });

  final GtexBroadcastEvent? event;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: const Alignment(0, -0.34),
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 220),
        switchInCurve: Curves.easeOutCubic,
        switchOutCurve: Curves.easeInCubic,
        child: event == null
            ? const SizedBox.shrink()
            : Container(
                key: ValueKey<String>(event!.id),
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                constraints: const BoxConstraints(maxWidth: 420),
                decoration: BoxDecoration(
                  color: const Color(0xE8101D2A),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: _accentForType(event!.type).withValues(alpha: 0.55),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Icon(
                      _iconForType(event!.type),
                      color: _accentForType(event!.type),
                    ),
                    const SizedBox(width: 10),
                    Flexible(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(
                            event!.title,
                            style:
                                Theme.of(context).textTheme.titleMedium?.copyWith(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w800,
                                    ),
                          ),
                          if (event!.subtitle?.trim().isNotEmpty == true)
                            Text(
                              event!.subtitle!,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: Colors.white70),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}

IconData _iconForType(GtexBroadcastEventType type) {
  switch (type) {
    case GtexBroadcastEventType.goal:
      return Icons.sports_soccer_rounded;
    case GtexBroadcastEventType.redCard:
      return Icons.crop_portrait_rounded;
    case GtexBroadcastEventType.yellowCard:
      return Icons.rectangle_rounded;
    case GtexBroadcastEventType.offside:
      return Icons.flag_rounded;
    case GtexBroadcastEventType.fullTime:
      return Icons.stop_circle_outlined;
    case GtexBroadcastEventType.missedChance:
    case GtexBroadcastEventType.commentaryBeat:
      return Icons.bolt_rounded;
    case GtexBroadcastEventType.varChecking:
    case GtexBroadcastEventType.varConfirmed:
    case GtexBroadcastEventType.varDisallowed:
    case GtexBroadcastEventType.intro:
      return Icons.live_tv_rounded;
  }
}

Color _accentForType(GtexBroadcastEventType type) {
  switch (type) {
    case GtexBroadcastEventType.goal:
    case GtexBroadcastEventType.varConfirmed:
      return const Color(0xFF17B26A);
    case GtexBroadcastEventType.redCard:
    case GtexBroadcastEventType.varDisallowed:
      return const Color(0xFFF04438);
    case GtexBroadcastEventType.yellowCard:
      return const Color(0xFFFDB022);
    case GtexBroadcastEventType.offside:
      return const Color(0xFFF79009);
    case GtexBroadcastEventType.varChecking:
      return const Color(0xFF53B1FD);
    case GtexBroadcastEventType.missedChance:
    case GtexBroadcastEventType.commentaryBeat:
    case GtexBroadcastEventType.fullTime:
    case GtexBroadcastEventType.intro:
      return const Color(0xFFD0D5DD);
  }
}

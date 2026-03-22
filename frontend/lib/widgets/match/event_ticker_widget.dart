import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match_event.dart';

class EventTickerWidget extends StatelessWidget {
  const EventTickerWidget({
    super.key,
    required this.event,
  });

  final MatchEvent? event;

  @override
  Widget build(BuildContext context) {
    final MatchEvent? activeEvent = event;
    if (activeEvent == null) {
      return const SizedBox.shrink();
    }
    final Color accent = _tickerColor(activeEvent.type);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xD90A1827),
        border: Border.all(color: accent.withValues(alpha: 0.55)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(activeEvent.icon, color: accent, size: 18),
          const SizedBox(width: 10),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  activeEvent.bannerText,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                if (activeEvent.isDataUnavailable) ...<Widget>[
                  const SizedBox(height: 4),
                  Text(
                    'Viewer placeholder',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.white70,
                          letterSpacing: 0.3,
                        ),
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

Color _tickerColor(MatchViewerEventType type) {
  switch (type) {
    case MatchViewerEventType.goal:
      return const Color(0xFF17B26A);
    case MatchViewerEventType.save:
      return const Color(0xFF53B1FD);
    case MatchViewerEventType.miss:
      return const Color(0xFFF79009);
    case MatchViewerEventType.offside:
      return const Color(0xFFF97066);
    case MatchViewerEventType.redCard:
      return const Color(0xFFF04438);
    default:
      return const Color(0xFFD0D5DD);
  }
}

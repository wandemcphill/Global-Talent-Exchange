import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexMatchTimeline extends StatelessWidget {
  const GtexMatchTimeline({super.key, required this.events});

  final List<GtexMatchTimelineEvent> events;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: events.length,
      separatorBuilder: (_, __) => Divider(color: Colors.white.withOpacity(.08)),
      itemBuilder: (context, index) {
        final event = events[index];
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 48,
              padding: const EdgeInsets.symmetric(vertical: 6),
              decoration: BoxDecoration(color: const Color(0xFF18FF88).withOpacity(.12), borderRadius: BorderRadius.circular(12)),
              alignment: Alignment.center,
              child: Text('${event.minute}\'', style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w900)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(event.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text(event.description, style: TextStyle(color: Colors.white.withOpacity(.62), height: 1.25)),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexHighlightsPanel extends StatelessWidget {
  const GtexHighlightsPanel({super.key, required this.highlights});

  final List<GtexMatchHighlight> highlights;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: highlights.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final item = highlights[index];
        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: Colors.white.withOpacity(.045), borderRadius: BorderRadius.circular(18), border: Border.all(color: Colors.white.withOpacity(.08))),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(shape: BoxShape.circle, color: const Color(0xFFFFD166).withOpacity(.16)),
                child: Center(child: Text('${item.minute}\'', style: const TextStyle(color: Color(0xFFFFD166), fontWeight: FontWeight.w900))),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(item.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text(item.summary, style: TextStyle(color: Colors.white.withOpacity(.62), height: 1.25)),
                ]),
              ),
            ],
          ),
        );
      },
    );
  }
}

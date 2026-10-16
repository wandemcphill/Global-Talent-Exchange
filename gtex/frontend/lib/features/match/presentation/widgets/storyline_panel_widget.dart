import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class StorylinePanelWidget extends StatelessWidget {
  const StorylinePanelWidget({super.key, required this.panel});

  final BroadcastStorylinePanelData panel;

  @override
  Widget build(BuildContext context) {
    if (!panel.hasContent) {
      return const SizedBox.shrink();
    }
    final List<BroadcastStorylineBucketData> buckets = panel.visibleBuckets;
    return DecoratedBox(
      key: const Key('storyline-panel'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF13161E), Color(0xFF090E14)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Storyline Panel',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Verified pre-match and live sidebars only.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
            ),
            const SizedBox(height: 16),
            for (int index = 0; index < buckets.length; index += 1) ...<Widget>[
              _StorylineBucket(bucket: buckets[index]),
              if (index < buckets.length - 1) const SizedBox(height: 12),
            ],
          ],
        ),
      ),
    );
  }
}

class _StorylineBucket extends StatelessWidget {
  const _StorylineBucket({required this.bucket});

  final BroadcastStorylineBucketData bucket;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              bucket.title.toUpperCase(),
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: const Color(0xFFFDA29B),
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 10),
            for (final String item in bucket.items.take(4))
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Container(
                      width: 6,
                      height: 6,
                      margin: const EdgeInsets.only(top: 6),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Color(0xFFF97316),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        item,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.white70,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

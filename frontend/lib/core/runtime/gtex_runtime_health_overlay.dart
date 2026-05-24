import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'gtex_runtime_graph.dart';
import 'gtex_runtime_models.dart';

class GtexRuntimeHealthOverlay extends ConsumerWidget {
  const GtexRuntimeHealthOverlay({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final GtexRuntime runtime = ref.watch(gtexRuntimeProvider);
    if (!runtime.observability.healthOverlayEnabled) {
      return child;
    }
    final String readiness = runtime.readiness.ready ? 'LIVE' : 'BLOCKED';
    final Color accent =
        runtime.readiness.ready ? const Color(0xFF35D07F) : Colors.amber;
    return Stack(
      children: <Widget>[
        child,
        Positioned(
          right: 12,
          bottom: 12,
          child: IgnorePointer(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: const Color(0xE6081110),
                border: Border.all(color: accent.withValues(alpha: 0.64)),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                child: DefaultTextStyle(
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text('STRICT LIVE $readiness'),
                      Text(
                        runtime.observability.sourceOfTruthTag,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.72),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (!runtime.readiness.ready)
                        Text(runtime.readiness.blockedReasons.join(', ')),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

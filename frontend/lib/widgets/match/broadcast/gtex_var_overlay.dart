import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_event.dart';

class GtexVarOverlay extends StatelessWidget {
  const GtexVarOverlay({
    super.key,
    required this.event,
  });

  final GtexBroadcastEvent? event;

  @override
  Widget build(BuildContext context) {
    if (event == null) {
      return const SizedBox.shrink();
    }
    final bool warning = event!.type == GtexBroadcastEventType.varDisallowed;
    return Align(
      alignment: const Alignment(0, -0.02),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 360),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          color: const Color(0xEC07131F),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: (warning ? const Color(0xFFF04438) : const Color(0xFF53B1FD))
                .withValues(alpha: 0.65),
          ),
        ),
        child: Row(
          children: <Widget>[
            Icon(
              warning ? Icons.gpp_bad_outlined : Icons.manage_search_rounded,
              color:
                  warning ? const Color(0xFFF04438) : const Color(0xFF53B1FD),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    event!.title.toUpperCase(),
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1,
                        ),
                  ),
                  if (event!.subtitle?.trim().isNotEmpty == true)
                    Text(
                      event!.subtitle!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.white70,
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

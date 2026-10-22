import 'package:flutter/material.dart';

/// A restrained, explicitly reserved advertising surface for GTEX matchday
/// pages. Live inventory is still supplied by the canonical ad/monetization
/// pipeline; this is the fallback placement label when no campaign is filled.
class GtexMatchdayAdSlot extends StatelessWidget {
  const GtexMatchdayAdSlot({
    super.key,
    required this.placement,
    this.compact = false,
  });

  final String placement;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool narrow = constraints.maxWidth < 520;
        return Container(
          key: Key('gtex-matchday-ad-slot-${placement.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-')}'),
          padding: EdgeInsets.all(compact ? 10 : 14),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF111D2A), Color(0xFF0B121D)],
            ),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF415166).withValues(alpha: 0.8)),
          ),
          child: Row(
            children: <Widget>[
              Container(
                width: compact ? 34 : 42,
                height: compact ? 34 : 42,
                decoration: BoxDecoration(
                  color: const Color(0xFFF0C66B).withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFF0C66B).withValues(alpha: 0.34)),
                ),
                child: const Icon(
                  Icons.campaign_outlined,
                  color: Color(0xFFF0C66B),
                  size: 21,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      'ADVERTISE HERE',
                      style: TextStyle(
                        color: const Color(0xFFF0C66B),
                        fontSize: compact ? 10 : 11,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.05,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      placement,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: compact ? 11 : 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    if (!compact) ...<Widget>[
                      const SizedBox(height: 2),
                      const Text(
                        'GTEX official matchday partner placement',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: Color(0xFF91A0B3), fontSize: 10),
                      ),
                    ],
                  ],
                ),
              ),
              if (!narrow && !compact) ...<Widget>[
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(5),
                    color: Colors.white.withValues(alpha: 0.04),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
                  ),
                  child: const Text(
                    'SPONSOR SPACE',
                    style: TextStyle(
                      color: Color(0xFFB8C4D1),
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.6,
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

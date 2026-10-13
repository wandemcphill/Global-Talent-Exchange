import 'package:flutter/material.dart';

/// Compact badge for an active GTEX regen endorsement deal.
class RegenEndorsementBadge extends StatelessWidget {
  const RegenEndorsementBadge({
    super.key,
    required this.label,
    this.sponsorName,
  });

  final String label;
  final String? sponsorName;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFFFD166).withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFFFD166).withValues(alpha: 0.45)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          const Icon(Icons.verified_rounded, size: 14, color: Color(0xFFFFD166)),
          const SizedBox(width: 6),
          Text(
            sponsorName == null || sponsorName!.isEmpty
                ? label
                : '$label · $sponsorName',
            style: const TextStyle(
              color: Color(0xFFFFD166),
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

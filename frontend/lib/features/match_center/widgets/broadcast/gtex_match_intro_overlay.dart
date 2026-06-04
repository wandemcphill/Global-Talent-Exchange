import 'package:flutter/material.dart';

class GtexMatchIntroOverlay extends StatelessWidget {
  const GtexMatchIntroOverlay({
    super.key,
    required this.visible,
    required this.competitionLabel,
    required this.matchTitle,
  });

  final bool visible;
  final String competitionLabel;
  final String matchTitle;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      ignoring: !visible,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 220),
        opacity: visible ? 1 : 0,
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 420),
            padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 20),
            decoration: BoxDecoration(
              color: const Color(0xE6101E2F),
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  competitionLabel,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Colors.white70,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  matchTitle,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Match starting',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: const Color(0xFF98A2B3),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';

class TurnstileChallenge extends StatelessWidget {
  const TurnstileChallenge({
    super.key,
    required this.siteKey,
    required this.onTokenChanged,
  });

  final String siteKey;
  final ValueChanged<String?> onTokenChanged;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Text(
      siteKey.trim().isEmpty
          ? 'Turnstile is not configured for this build.'
          : 'Complete signup in the GTEX web app to verify this security challenge.',
      style: const TextStyle(color: Color(0xFF93A0AA), fontSize: 12),
    ),
  );
}

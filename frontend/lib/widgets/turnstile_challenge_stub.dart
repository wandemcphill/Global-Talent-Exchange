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
  Widget build(BuildContext context) => siteKey.trim().isEmpty
      ? const SizedBox.shrink()
      : const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Text(
            'Complete signup in the GTEX web app to verify this security challenge.',
            style: TextStyle(color: Color(0xFF93A0AA), fontSize: 12),
          ),
        );
}

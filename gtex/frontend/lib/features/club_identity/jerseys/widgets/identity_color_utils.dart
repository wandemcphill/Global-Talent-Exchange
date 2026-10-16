import 'package:flutter/material.dart';

Color identityColorFromHex(String hex) {
  final String normalized =
      hex.replaceAll('#', '').padLeft(6, '0').substring(0, 6);
  return Color(int.parse('FF$normalized', radix: 16));
}

Color identityReadableOn(Color background) {
  return background.computeLuminance() > 0.5 ? Colors.black : Colors.white;
}

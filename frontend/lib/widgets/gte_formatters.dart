String gteFormatCredits(double value) {
  final bool wholeNumber = value == value.roundToDouble();
  return '${value.toStringAsFixed(wholeNumber ? 0 : 2)} cr';
}

String gteFormatNullableCredits(double? value) {
  if (value == null) {
    return '--';
  }
  return gteFormatCredits(value);
}

String gteFormatMovement(double fraction) {
  final double pct = fraction * 100;
  final String sign = pct > 0 ? '+' : '';
  return '$sign${pct.toStringAsFixed(1)}%';
}

String gteFormatDateTime(DateTime? value) {
  if (value == null) {
    return 'n/a';
  }
  final DateTime utc = value.toUtc();
  final String month = utc.month.toString().padLeft(2, '0');
  final String day = utc.day.toString().padLeft(2, '0');
  final String hour = utc.hour.toString().padLeft(2, '0');
  final String minute = utc.minute.toString().padLeft(2, '0');
  return '${utc.year}-$month-$day $hour:$minute UTC';
}

String gteFormatOrderStatus(String rawStatus) {
  final String spaced =
      rawStatus.replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (Match match) {
    return '${match.group(1)} ${match.group(2)}';
  }).replaceAll('_', ' ');
  return spaced.toUpperCase();
}

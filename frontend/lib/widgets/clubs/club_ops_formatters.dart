String clubOpsFormatCurrency(double value) {
  final double absoluteValue = value.abs();
  final String prefix = value < 0 ? '-\$' : '\$';
  if (absoluteValue >= 1000000) {
    return '$prefix${(absoluteValue / 1000000).toStringAsFixed(1)}M';
  }
  if (absoluteValue >= 1000) {
    return '$prefix${(absoluteValue / 1000).toStringAsFixed(0)}K';
  }
  return '$prefix${absoluteValue.toStringAsFixed(0)}';
}

String clubOpsFormatSignedCurrency(double value) {
  final String sign = value > 0 ? '+' : '';
  return '$sign${clubOpsFormatCurrency(value)}';
}

String clubOpsFormatPercent(double value) {
  final String sign = value > 0 ? '+' : '';
  return '$sign${value.toStringAsFixed(1)}%';
}

String clubOpsFormatCompactNumber(num value) {
  final num absoluteValue = value.abs();
  if (absoluteValue >= 1000000) {
    return '${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (absoluteValue >= 1000) {
    return '${(value / 1000).toStringAsFixed(1)}K';
  }
  return value.toStringAsFixed(value % 1 == 0 ? 0 : 1);
}

String clubOpsFormatDate(DateTime value) {
  const List<String> months = <String>[
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  final DateTime local = value.toLocal();
  return '${months[local.month - 1]} ${local.day}, ${local.year}';
}

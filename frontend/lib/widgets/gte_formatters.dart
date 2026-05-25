import '../data/gte_models.dart';

String _gteFormatUnitAmount(double value, String unitLabel) {
  final bool wholeNumber = value == value.roundToDouble();
  return '${value.toStringAsFixed(wholeNumber ? 0 : 2)} $unitLabel';
}

String gteFormatCredits(double value) {
  return _gteFormatUnitAmount(value, 'GTEX Coin');
}

String gteFormatAmountForUnit(double value, GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.coin:
      return gteFormatCredits(value);
    case GteLedgerUnit.credit:
      return gteFormatFanCoins(value);
    case GteLedgerUnit.unknown:
      return _gteFormatUnitAmount(value, 'Unit');
  }
}

String gteFormatCompetitionAmount(double value, [String currency = 'credit']) {
  final String normalized = currency.trim().toLowerCase();
  if (normalized.isEmpty ||
      normalized == 'coin' ||
      normalized == 'coins' ||
      normalized == 'gtex' ||
      normalized == 'gtex coin') {
    return gteFormatCredits(value);
  }
  if (normalized == 'credit' ||
      normalized == 'credits' ||
      normalized == 'fan coin' ||
      normalized == 'fan coins' ||
      normalized == 'fancoin' ||
      normalized == 'fan_coin') {
    return gteFormatFanCoins(value);
  }
  return _gteFormatUnitAmount(value, currency.trim().toUpperCase());
}

String gteFormatFanCoins(double value) {
  return _gteFormatUnitAmount(value, 'Fan Coin');
}

String gteFormatGtc(double value) {
  return _gteFormatUnitAmount(value, 'GTC');
}

String gteFormatFnc(double value) {
  return _gteFormatUnitAmount(value, 'FNC');
}

String gteFormatShortAmountForUnit(double value, GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.coin:
      return gteFormatGtc(value);
    case GteLedgerUnit.credit:
      return gteFormatFnc(value);
    case GteLedgerUnit.unknown:
      return _gteFormatUnitAmount(value, 'Unit');
  }
}

String gteFormatFanCoin(double value) {
  return gteFormatFanCoins(value);
}

String gteLedgerUnitCode(GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.credit:
      return 'FNC';
    case GteLedgerUnit.coin:
      return 'GTC';
    case GteLedgerUnit.unknown:
      return 'UNIT';
  }
}

String gteFormatLedgerUnitName(GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.credit:
      return 'Fan Coin';
    case GteLedgerUnit.coin:
      return 'GTEX Coin';
    case GteLedgerUnit.unknown:
      return 'Unit';
  }
}

String gteFormatFiat(double value, {String currency = 'NGN'}) {
  final bool wholeNumber = value == value.roundToDouble();
  return '${value.toStringAsFixed(wholeNumber ? 0 : 2)} $currency';
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

String gteFormatDate(DateTime? value) {
  return gteFormatDateTime(value);
}

String gteFormatOrderStatus(String rawStatus) {
  final String spaced = rawStatus
      .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (Match match) {
        return '${match.group(1)} ${match.group(2)}';
      })
      .replaceAll('_', ' ');
  return spaced.toUpperCase();
}

String gteFormatRelativeTime(DateTime? value, {DateTime? now}) {
  if (value == null) {
    return 'waiting for first sync';
  }
  final DateTime reference = (now ?? DateTime.now()).toUtc();
  final Duration delta = reference.difference(value.toUtc());
  if (delta.inSeconds.abs() < 5) {
    return 'just now';
  }
  if (delta.inMinutes.abs() < 1) {
    return '${delta.inSeconds.abs()}s ago';
  }
  if (delta.inHours.abs() < 1) {
    return '${delta.inMinutes.abs()}m ago';
  }
  if (delta.inDays.abs() < 1) {
    return '${delta.inHours.abs()}h ago';
  }
  if (delta.inDays.abs() < 7) {
    return '${delta.inDays.abs()}d ago';
  }
  return gteFormatDateTime(value);
}

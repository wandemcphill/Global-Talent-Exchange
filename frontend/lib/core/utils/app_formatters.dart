class AppFormatters {
  const AppFormatters._();

  static String money(double amountInMillions) {
    final String fixed = amountInMillions.toStringAsFixed(
      amountInMillions.truncateToDouble() == amountInMillions ? 0 : 1,
    );
    return '\$${fixed}M';
  }

  static String naira(num amount) {
    final int value = amount.round();
    return '₦${_grouped(value)}';
  }

  static String gtex(num amount) {
    return '${_trimmed(amount)} GTex';
  }

  static String fanCoin(num amount) {
    return '${_trimmed(amount)} GTEX Coin';
  }

  static String signedGtex(num amount) {
    final String prefix = amount > 0 ? '+' : '';
    return '$prefix${_trimmed(amount)} GTex';
  }

  static String percent(num amount) {
    final String prefix = amount > 0 ? '+' : '';
    return '$prefix${amount.toStringAsFixed(1)}%';
  }

  static String compact(int value) {
    if (value >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (value >= 1000) {
      return '${(value / 1000).toStringAsFixed(1)}K';
    }
    return '$value';
  }

  static String _trimmed(num value) {
    final double normalized = value.toDouble();
    if (normalized == normalized.truncateToDouble()) {
      return normalized.toStringAsFixed(0);
    }
    return normalized.toStringAsFixed(1);
  }

  static String _grouped(int value) {
    final String raw = value.abs().toString();
    final StringBuffer buffer = StringBuffer();

    for (int index = 0; index < raw.length; index++) {
      if (index > 0 && (raw.length - index) % 3 == 0) {
        buffer.write(',');
      }
      buffer.write(raw[index]);
    }

    return value < 0 ? '-${buffer.toString()}' : buffer.toString();
  }
}

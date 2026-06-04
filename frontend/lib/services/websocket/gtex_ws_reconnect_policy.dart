class GtexWsReconnectPolicy {
  const GtexWsReconnectPolicy({
    this.initialDelay = const Duration(seconds: 1),
    this.maxDelay = const Duration(seconds: 30),
    this.multiplier = 2,
  }) : assert(multiplier >= 1);

  final Duration initialDelay;
  final Duration maxDelay;
  final int multiplier;

  Duration delayForAttempt(int attempt) {
    if (attempt <= 0) {
      return Duration.zero;
    }
    int factor = 1;
    for (int index = 1; index < attempt; index += 1) {
      factor *= multiplier;
    }
    final Duration delay = initialDelay * factor;
    return delay > maxDelay ? maxDelay : delay;
  }
}

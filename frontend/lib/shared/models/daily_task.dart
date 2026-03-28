class DailyTask {
  const DailyTask({
    required this.id,
    required this.title,
    required this.reward,
    required this.current,
    required this.target,
  });

  final String id;
  final String title;
  final String reward;
  final int current;
  final int target;

  bool get isComplete => current >= target;
  double get progress => target == 0 ? 0 : current / target;
}

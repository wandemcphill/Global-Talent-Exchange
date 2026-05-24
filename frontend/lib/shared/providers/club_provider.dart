import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/club.dart';
import '../models/daily_task.dart';
import 'tasks_provider.dart';

final Provider<Club?> clubProvider = Provider<Club?>((Ref ref) => null);

final Provider<List<DailyTask>> dailyTasksProvider = Provider<List<DailyTask>>(
  (Ref ref) =>
      ref.watch(tasksProvider.select((TasksState state) => state.dailyTasks)),
);

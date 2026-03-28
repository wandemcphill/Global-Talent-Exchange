import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/club.dart';
import '../models/daily_task.dart';
import 'tasks_provider.dart';

final Provider<Club> clubProvider = Provider<Club>(
  (Ref ref) => const Club(
    id: 'lagos-atlas',
    name: 'Lagos Atlas FC',
    country: 'Nigeria',
    league: 'Elite Talent League',
    stadium: 'Atlas Dome',
    budgetInMillions: 186,
    startingXiRating: 84,
    academyLevel: 5,
    formLabel: 'WWDWW',
    fans: 3240000,
    badgeAsset: 'assets/branding/gtex_logo.png',
  ),
);

final Provider<List<DailyTask>> dailyTasksProvider = Provider<List<DailyTask>>(
  (Ref ref) =>
      ref.watch(tasksProvider.select((TasksState state) => state.dailyTasks)),
);

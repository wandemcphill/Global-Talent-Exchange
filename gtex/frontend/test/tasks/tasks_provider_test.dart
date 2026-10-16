import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/shared/providers/tasks_provider.dart';

void main() {
  test('season pass exposes a claimable reward and marks it claimed', () {
    final ProviderContainer container = ProviderContainer();
    addTearDown(container.dispose);

    final TasksState initialState = container.read(tasksProvider);
    expect(initialState.seasonPass.currentLevel, 12);
    expect(initialState.seasonPass.claimableRewardCount, 1);

    final claim = container
        .read(tasksProvider.notifier)
        .claimSeasonReward('season-reward-10');

    expect(claim, isNotNull);
    expect(claim?.level, 10);
    expect(claim?.rewardLabel, 'Player Pack');

    final TasksState updatedState = container.read(tasksProvider);
    expect(updatedState.seasonPass.claimableRewardCount, 0);
    expect(
      updatedState.seasonPass.rewards
          .firstWhere((reward) => reward.id == 'season-reward-10')
          .claimed,
      isTrue,
    );
  });
}

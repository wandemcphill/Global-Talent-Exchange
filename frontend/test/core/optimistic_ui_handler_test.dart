import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/optimistic_ui_handler.dart';

void main() {
  test('applies optimistic state on success', () async {
    Set<String> currentState = <String>{};
    final OptimisticUiHandler<String, Set<String>> handler =
        OptimisticUiHandler<String, Set<String>>();

    await handler.run(
      key: 'like:clip-1',
      currentState: currentState,
      optimisticState:
          (Set<String> existing) => <String>{...existing, 'clip-1'},
      apply: (Set<String> nextState) {
        currentState = nextState;
      },
      commit: () async {},
    );

    expect(currentState, <String>{'clip-1'});
    expect(handler.isPending('like:clip-1'), isFalse);
  });

  test('rolls back optimistic state when commit fails', () async {
    Set<String> currentState = <String>{};
    final OptimisticUiHandler<String, Set<String>> handler =
        OptimisticUiHandler<String, Set<String>>();

    await expectLater(
      () => handler.run(
        key: 'share:clip-2',
        currentState: currentState,
        optimisticState:
            (Set<String> existing) => <String>{...existing, 'clip-2'},
        apply: (Set<String> nextState) {
          currentState = nextState;
        },
        commit: () async {
          throw StateError('request failed');
        },
      ),
      throwsStateError,
    );

    expect(currentState, isEmpty);
    expect(handler.isPending('share:clip-2'), isFalse);
  });
}

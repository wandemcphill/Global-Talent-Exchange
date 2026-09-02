import 'dart:async';

/// Keep the shared test executable hook completely passive.
///
/// Do not initialize a widget binding or mount a widget tree here. The
/// `flutter_test` runner initializes the appropriate binding when a
/// `testWidgets` case starts. Initializing it from this global hook can make
/// plain `test` cases participate in widget-test lifecycle management and can
/// race flutter_tools' test stream during teardown.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  await testMain();
}

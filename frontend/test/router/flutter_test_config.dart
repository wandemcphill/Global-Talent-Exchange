import 'dart:async';

/// Route coverage tests must not mutate the Flutter test binding from the
/// test executable hook. `testExecutable` runs outside an individual test,
/// so calling `runApp()` here violates `AutomatedTestWidgetsFlutterBinding`
///'s `inTest` assertion and can also race the stream-channel shutdown.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  await testMain();
}

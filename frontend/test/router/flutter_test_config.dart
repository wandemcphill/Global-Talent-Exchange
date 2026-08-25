import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

/// Keep the shared test executable hook limited to test-runner setup.
///
/// Widget trees must be mounted from individual `testWidgets` bodies. Calling
/// `runApp()` here executes outside an active Flutter test and can trigger
/// AutomatedTestWidgetsFlutterBinding's `inTest` assertion and race the
/// stream-channel shutdown with flutter_tools.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  TestWidgetsFlutterBinding.ensureInitialized();
  await testMain();
}

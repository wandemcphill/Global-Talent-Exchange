import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

/// Route coverage mounts a large number of stateful production surfaces. Some
/// of those surfaces can finish asynchronous work after the assertion phase of
/// a test. Unmount the test tree during tearDown so widget-owned controllers,
/// timers, and listeners are disposed before Flutter's test channel closes.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  tearDown(() async {
    final TestWidgetsFlutterBinding binding =
        TestWidgetsFlutterBinding.ensureInitialized();
    runApp(const SizedBox.shrink());
    await binding.pump();
  });

  await testMain();
}

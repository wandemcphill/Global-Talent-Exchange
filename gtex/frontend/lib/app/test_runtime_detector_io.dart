import 'dart:io';

bool get isFlutterTestRuntime => Platform.environment['FLUTTER_TEST'] == 'true';

void assertFixtureFactoryAllowed(String factoryName) {
  if (!isFlutterTestRuntime) {
    throw StateError('$factoryName is available only in Flutter test runtime.');
  }
}

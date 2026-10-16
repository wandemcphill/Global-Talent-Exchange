bool get isFlutterTestRuntime => false;

void assertFixtureFactoryAllowed(String factoryName) {
  throw StateError('$factoryName is available only in Flutter test runtime.');
}

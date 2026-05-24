import '../data/gte_api_repository.dart';
import 'test_runtime_detector.dart';

const String gteFixtureApiBaseUrl = 'https://fixture.invalid';
const String gteFlutterTestApiBaseUrl = 'https://runtime-config.invalid';

class GteAppConfig {
  const GteAppConfig({
    required this.apiBaseUrl,
    required this.backendMode,
    this.rawBackendMode = 'strict_live',
  });

  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final String rawBackendMode;

  GteBackendMode get activeShellBackendMode =>
      backendMode == GteBackendMode.fixture
          ? GteBackendMode.fixture
          : GteBackendMode.live;

  static GteAppConfig fromEnvironment() {
    const String rawBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
    const String rawMode = String.fromEnvironment(
      'GTE_BACKEND_MODE',
      defaultValue: 'strict_live',
    );
    final GteBackendMode backendMode = _parseBackendMode(
      rawMode,
      allowFixtureMode: isFlutterTestRuntime,
    );
    return GteAppConfig(
      apiBaseUrl: resolveGteApiBaseUrl(
        rawBaseUrl: rawBaseUrl,
        backendMode: backendMode,
      ),
      backendMode: backendMode,
      rawBackendMode: rawMode,
    );
  }

  static GteAppConfig fromRuntimeEnvironment() {
    const String rawBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
    const String rawMode = String.fromEnvironment(
      'GTE_BACKEND_MODE',
      defaultValue: 'strict_live',
    );
    final GteBackendMode backendMode = _parseBackendMode(
      rawMode,
      allowFixtureMode: isFlutterTestRuntime,
    );
    return GteAppConfig(
      apiBaseUrl: resolveGteApiBaseUrlForRuntimeEnvironment(
        rawBaseUrl: rawBaseUrl,
        rawMode: rawMode,
      ),
      backendMode: backendMode,
      rawBackendMode: rawMode,
    );
  }
}

String resolveGteApiBaseUrl({
  required String rawBaseUrl,
  required GteBackendMode backendMode,
}) {
  final String baseUrl = rawBaseUrl.trim();
  if (baseUrl.isNotEmpty) {
    return baseUrl;
  }
  if (backendMode == GteBackendMode.fixture) {
    return gteFixtureApiBaseUrl;
  }
  throw StateError(
    'GTE_API_BASE_URL must be set when GTE_BACKEND_MODE is strict_live.',
  );
}

String resolveGteApiBaseUrlFromEnvironment({
  String rawBaseUrl = const String.fromEnvironment('GTE_API_BASE_URL'),
  String rawMode = const String.fromEnvironment(
    'GTE_BACKEND_MODE',
    defaultValue: 'strict_live',
  ),
}) {
  return resolveGteApiBaseUrl(
    rawBaseUrl: rawBaseUrl,
    backendMode: _parseBackendMode(
      rawMode,
      allowFixtureMode: isFlutterTestRuntime,
    ),
  );
}

String resolveGteApiBaseUrlForRuntimeEnvironment({
  String rawBaseUrl = const String.fromEnvironment('GTE_API_BASE_URL'),
  String rawMode = const String.fromEnvironment(
    'GTE_BACKEND_MODE',
    defaultValue: 'strict_live',
  ),
}) {
  final String baseUrl = rawBaseUrl.trim();
  if (baseUrl.isNotEmpty) {
    return baseUrl;
  }
  final GteBackendMode backendMode = _parseBackendMode(
    rawMode,
    allowFixtureMode: isFlutterTestRuntime,
  );
  if (backendMode == GteBackendMode.fixture) {
    return gteFixtureApiBaseUrl;
  }
  if (isFlutterTestRuntime) {
    // Widget and unit tests often build feature surfaces directly, outside the
    // bootstrapped app entrypoint that normally injects the live API base URL.
    return gteFlutterTestApiBaseUrl;
  }
  return resolveGteApiBaseUrl(rawBaseUrl: rawBaseUrl, backendMode: backendMode);
}

GteBackendMode _parseBackendMode(
  String rawMode, {
  bool allowFixtureMode = false,
}) {
  switch (rawMode.trim().toLowerCase()) {
    case 'fixture':
      if (allowFixtureMode) {
        return GteBackendMode.fixture;
      }
      throw StateError(
        'GTE_BACKEND_MODE=fixture is not allowed outside Flutter test runtime.',
      );
    case 'strict_live':
    case 'strictlive':
    case 'production':
    case 'live':
      return GteBackendMode.live;
    case 'livethenfixture':
      throw StateError(
        'GTE_BACKEND_MODE=liveThenFixture is forbidden. Use strict_live.',
      );
    default:
      return GteBackendMode.live;
  }
}

import '../data/gte_api_repository.dart';
import 'test_runtime_detector.dart';

const String gteFixtureApiBaseUrl = 'https://fixture.invalid';
const String gteFlutterTestApiBaseUrl = 'https://runtime-config.invalid';

class GteAppConfig {
  const GteAppConfig({required this.apiBaseUrl, required this.backendMode});

  final String apiBaseUrl;
  final GteBackendMode backendMode;

  GteBackendMode get activeShellBackendMode =>
      backendMode == GteBackendMode.fixture
          ? GteBackendMode.fixture
          : GteBackendMode.live;

  static GteAppConfig fromEnvironment() {
    const String rawBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
    const String rawMode = String.fromEnvironment(
      'GTE_BACKEND_MODE',
      // Default to live so imported players, regens, and admin changes are
      // visible without requiring a local launch flag override.
      defaultValue: 'live',
    );
    final GteBackendMode backendMode = _parseBackendMode(rawMode);
    return GteAppConfig(
      apiBaseUrl: resolveGteApiBaseUrl(
        rawBaseUrl: rawBaseUrl,
        backendMode: backendMode,
      ),
      backendMode: backendMode,
    );
  }

  static GteAppConfig fromRuntimeEnvironment() {
    const String rawBaseUrl = String.fromEnvironment('GTE_API_BASE_URL');
    const String rawMode = String.fromEnvironment(
      'GTE_BACKEND_MODE',
      defaultValue: 'live',
    );
    final GteBackendMode backendMode = _parseBackendMode(rawMode);
    return GteAppConfig(
      apiBaseUrl: resolveGteApiBaseUrlForRuntimeEnvironment(
        rawBaseUrl: rawBaseUrl,
        rawMode: rawMode,
      ),
      backendMode: backendMode,
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
    'GTE_API_BASE_URL must be set when GTE_BACKEND_MODE is live or '
    'liveThenFixture.',
  );
}

String resolveGteApiBaseUrlFromEnvironment({
  String rawBaseUrl = const String.fromEnvironment('GTE_API_BASE_URL'),
  String rawMode = const String.fromEnvironment(
    'GTE_BACKEND_MODE',
    defaultValue: 'live',
  ),
}) {
  return resolveGteApiBaseUrl(
    rawBaseUrl: rawBaseUrl,
    backendMode: _parseBackendMode(rawMode),
  );
}

String resolveGteApiBaseUrlForRuntimeEnvironment({
  String rawBaseUrl = const String.fromEnvironment('GTE_API_BASE_URL'),
  String rawMode = const String.fromEnvironment(
    'GTE_BACKEND_MODE',
    defaultValue: 'live',
  ),
}) {
  final String baseUrl = rawBaseUrl.trim();
  if (baseUrl.isNotEmpty) {
    return baseUrl;
  }
  final GteBackendMode backendMode = _parseBackendMode(rawMode);
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

GteBackendMode _parseBackendMode(String rawMode) {
  switch (rawMode.trim().toLowerCase()) {
    case 'fixture':
      return GteBackendMode.fixture;
    case 'live':
      return GteBackendMode.live;
    case 'livethenfixture':
    default:
      // Preserved for legacy/dev/test wiring. Shipped active-shell providers
      // clamp this back to live before building critical clients.
      return GteBackendMode.liveThenFixture;
  }
}

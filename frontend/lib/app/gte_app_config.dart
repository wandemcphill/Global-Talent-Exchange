import '../data/gte_api_repository.dart';

class GteAppConfig {
  const GteAppConfig({required this.apiBaseUrl, required this.backendMode});

  final String apiBaseUrl;
  final GteBackendMode backendMode;

  GteBackendMode get activeShellBackendMode =>
      backendMode == GteBackendMode.fixture
          ? GteBackendMode.fixture
          : GteBackendMode.live;

  static GteAppConfig fromEnvironment() {
    const String rawBaseUrl = String.fromEnvironment(
      'GTE_API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000',
    );
    const String rawMode = String.fromEnvironment(
      'GTE_BACKEND_MODE',
      // Default to live so imported players, regens, and admin changes are
      // visible without requiring a local launch flag override.
      defaultValue: 'live',
    );
    return GteAppConfig(
      apiBaseUrl: rawBaseUrl,
      backendMode: _parseBackendMode(rawMode),
    );
  }
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

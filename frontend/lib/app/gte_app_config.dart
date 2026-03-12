import '../data/gte_api_repository.dart';

class GteAppConfig {
  const GteAppConfig({
    required this.apiBaseUrl,
    required this.backendMode,
  });

  final String apiBaseUrl;
  final GteBackendMode backendMode;

  static GteAppConfig fromEnvironment() {
    const String rawBaseUrl = String.fromEnvironment(
      'GTE_API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000',
    );
    const String rawMode = String.fromEnvironment(
      'GTE_BACKEND_MODE',
      defaultValue: 'liveThenFixture',
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
      return GteBackendMode.liveThenFixture;
  }
}

import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  test('resolveGteApiBaseUrl returns trimmed explicit base URL', () {
    expect(
      resolveGteApiBaseUrl(
        rawBaseUrl: ' https://example.test/api ',
        backendMode: GteBackendMode.live,
      ),
      'https://example.test/api',
    );
  });

  test(
    'resolveGteApiBaseUrlFromEnvironment fails fast for missing live URL',
    () {
      expect(
        () => resolveGteApiBaseUrlFromEnvironment(
          rawBaseUrl: '',
          rawMode: 'live',
        ),
        throwsA(
          isA<StateError>().having(
            (StateError error) => error.message,
            'message',
            contains('GTE_API_BASE_URL must be set'),
          ),
        ),
      );
    },
  );

  test(
    'resolveGteApiBaseUrlFromEnvironment treats liveThenFixture as live-capable',
    () {
      expect(
        () => resolveGteApiBaseUrlFromEnvironment(
          rawBaseUrl: '',
          rawMode: 'liveThenFixture',
        ),
        throwsA(isA<StateError>()),
      );
    },
  );

  test(
    'resolveGteApiBaseUrlFromEnvironment keeps fixture mode off localhost when unset',
    () {
      expect(
        resolveGteApiBaseUrlFromEnvironment(rawBaseUrl: '', rawMode: 'fixture'),
        gteFixtureApiBaseUrl,
      );
    },
  );
}

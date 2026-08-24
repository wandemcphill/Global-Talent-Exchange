import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match/live_match_session_service.dart';

void main() {
  LiveMatchSessionService serviceFor(String baseUrl) {
    return LiveMatchSessionService(
      config: GteAppConfig(
        apiBaseUrl: baseUrl,
        backendMode: GteBackendMode.live,
      ),
    );
  }

  group('LiveMatchSessionService websocket URL resolution', () {
    test('upgrades relative HTTPS paths to WSS and preserves query', () {
      final Uri? uri = serviceFor('https://gtex-api-opea.onrender.com')
          .resolveWebSocketUri('/api/matches/fixture-123/ws?token=abc');

      expect(
        uri,
        Uri.parse(
          'wss://gtex-api-opea.onrender.com/api/matches/fixture-123/ws?token=abc',
        ),
      );
    });

    test('upgrades relative HTTP paths to WS', () {
      final Uri? uri = serviceFor('http://localhost:8000/api')
          .resolveWebSocketUri('matches/fixture-123/ws');

      expect(uri, Uri.parse('ws://localhost:8000/matches/fixture-123/ws'));
    });

    test('accepts explicit WSS endpoints and removes fragments', () {
      final Uri? uri = serviceFor('https://gtex-api-opea.onrender.com')
          .resolveWebSocketUri('wss://stream.example.com/matches/123#viewer');

      expect(uri, Uri.parse('wss://stream.example.com/matches/123'));
    });

    test('rejects malformed websocket values without throwing', () {
      final LiveMatchSessionService service =
          serviceFor('https://gtex-api-opea.onrender.com');

      expect(service.resolveWebSocketUri('%%%not-a-uri%%%'), isNull);
      expect(service.resolveWebSocketUri('ftp://stream.example.com/match'), isNull);
      expect(service.resolveWebSocketUri('ws:///missing-host'), isNull);
      expect(service.resolveWebSocketUri('   '), isNull);
      expect(service.resolveWebSocketUri(null), isNull);
    });
  });
}

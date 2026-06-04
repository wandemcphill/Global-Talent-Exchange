import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/match_center/live_match_session.dart';
import 'package:gte_frontend/features/match_center/live_match_session_service.dart';

void main() {
  test('spectate session parses canonical 2D websocket paths', () {
    final LiveMatchSpectateSession session = LiveMatchSpectateSession.fromJson(
      <String, Object?>{
        'id': 'session-1',
        'match_id': 'match-1',
        'user_id': 'viewer-1',
        'joined_at': '2026-06-01T00:00:00Z',
        'channel': 'match:match-1:events',
        'websocket_path': '/api/matches/match-1/stream?session_id=session-1',
        'commentary_websocket_path':
            '/api/matches/match-1/commentary/stream?session_id=session-1',
        'audio_stem_websocket_path':
            '/api/matches/match-1/audio/stems/stream?session_id=session-1',
        'presence_websocket_path': '/ws/spectate/match-1',
        'tts_websocket_path': '/tts/live?voice=default',
        'replay_route': '/api/matches/match-1/replay',
        'speed_modes': <Object?>[
          <String, Object?>{
            'key': 'normal',
            'label': 'Normal',
            'target_duration_seconds': 90,
          },
        ],
      },
    );

    expect(session.id, 'session-1');
    expect(session.matchId, 'match-1');
    expect(session.websocketPath, contains('/api/matches/match-1/stream'));
    expect(session.websocketPath, contains('session_id=session-1'));
    expect(session.commentaryWebsocketPath, contains('/commentary/stream'));
    expect(session.audioStemWebsocketPath, contains('/audio/stems/stream'));
    expect(session.presenceWebsocketPath, '/ws/spectate/match-1');
    expect(session.ttsWebsocketPath, '/tts/live?voice=default');
    expect(session.replayRoute, '/api/matches/match-1/replay');
    expect(session.speedModes.single.key, 'normal');
    expect(session.websocketPath.toLowerCase(), isNot(contains('legacy')));
    expect(session.websocketPath.toLowerCase(), isNot(contains('/realtime/')));
    expect(session.websocketPath.toLowerCase(), isNot(contains('unity')));
    expect(session.websocketPath.toLowerCase(), isNot(contains('3d')));
  });

  test('websocket resolver converts canonical API paths to ws transports', () {
    final LiveMatchSessionService secureService = LiveMatchSessionService(
      config: const GteAppConfig(
        apiBaseUrl: 'https://api.gtex.test/base',
        backendMode: GteBackendMode.live,
      ),
    );
    final LiveMatchSessionService localService = LiveMatchSessionService(
      config: const GteAppConfig(
        apiBaseUrl: 'http://localhost:8080',
        backendMode: GteBackendMode.live,
      ),
    );

    expect(
      secureService
          .resolveWebSocketUri(
            '/api/matches/match-1/stream?session_id=session-1',
          )
          .toString(),
      'wss://api.gtex.test/api/matches/match-1/stream?session_id=session-1',
    );
    expect(
      localService
          .resolveWebSocketUri(
            '/api/matches/match-1/commentary/stream?session_id=session-1',
          )
          .toString(),
      'ws://localhost:8080/api/matches/match-1/commentary/stream?session_id=session-1',
    );
    expect(
      secureService
          .resolveWebSocketUri(
            'wss://stream.gtex.test/api/matches/match-1/stream?session_id=session-1',
          )
          .toString(),
      'wss://stream.gtex.test/api/matches/match-1/stream?session_id=session-1',
    );
  });

  test('websocket resolver rejects retired realtime match transports', () {
    final LiveMatchSessionService service = LiveMatchSessionService(
      config: const GteAppConfig(
        apiBaseUrl: 'https://api.gtex.test',
        backendMode: GteBackendMode.live,
      ),
    );

    expect(
      service.resolveWebSocketUri('/realtime/matches/match-1/stream'),
      isNull,
    );
    expect(
      service.resolveWebSocketUri(
        'wss://api.gtex.test/realtime/matches/match-1/stream',
      ),
      isNull,
    );
    expect(
      service.resolveWebSocketUri(
        'wss://api.gtex.test/api/v2/realtime/matches/match-1/stream',
      ),
      isNull,
    );
    expect(service.resolveWebSocketUri('/api/matches/match-1/replay'), isNull);
    expect(
      service.resolveWebSocketUri('/api/matches/match-1/gateway/stream'),
      isNull,
    );
    expect(
      service.resolveWebSocketUri('/api/matches/match-1/unity/stream'),
      isNull,
    );
    expect(
      service.resolveWebSocketUri(
        'https://api.gtex.test/api/matches/match-1/stream',
      ),
      isNull,
    );
    expect(
      service
          .resolveWebSocketUri(
            '/api/v2/matches/match-1/stream?session_id=session-1',
          )
          .toString(),
      'wss://api.gtex.test/api/v2/matches/match-1/stream?session_id=session-1',
    );
    expect(
      service
          .resolveWebSocketUri(
            '/api/v2/matches/match-1/audio/stems/stream?session_id=session-1',
          )
          .toString(),
      'wss://api.gtex.test/api/v2/matches/match-1/audio/stems/stream?session_id=session-1',
    );
  });
}

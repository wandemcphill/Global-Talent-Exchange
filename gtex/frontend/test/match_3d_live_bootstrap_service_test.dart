import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/models/match_3d_native_session.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test(
    'Android live bootstrap service issues unity access and stages bootstrap payload',
    () async {
      final _BootstrapCaptureBackend backend = _BootstrapCaptureBackend();
      final Match3dAndroidLiveBootstrapService service =
          Match3dAndroidLiveBootstrapService(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(baseUrl: 'https://api.gtex.dev'),
              transport: _StaticTransport(
                responseBody: <String, Object?>{
                  'success': true,
                  'data': <String, Object?>{
                    'match_id': 'match-123',
                    'spectator_session_id': 'spectator-123',
                    'access_token': 'unity-access-token',
                    'refresh_token': 'unity-refresh-token',
                    'token_type': 'bearer',
                    'expires_in': 1800,
                    'refresh_expires_in': 43200,
                    'live_path': '/match/match-123/live',
                    'websocket_path': '/api/v2/ws/match/match-123?format=unity',
                    'refresh_path': '/match/match-123/unity-access/refresh',
                  },
                },
              ),
              authSession: const AuthSession(
                userId: 'user-1',
                accessToken: 'app-access-token',
                refreshToken: 'app-refresh-token',
                sessionId: 'session-1',
              ),
            ),
            bridge: Match3DBridge(backend: backend),
            now: () => DateTime.utc(2026, 4, 16, 15, 30),
          );

      final Match3dAndroidLiveBootstrapResult result = await service.provision(
        matchId: 'match-123',
      );

      expect(result.staged, isTrue);
      expect(result.bootstrapPath, '/android/files/tmp/gtex-live-bootstrap.json');
      expect(backend.lastBootstrapRequest, isNotNull);
      expect(backend.lastBootstrapRequest!['matchId'], 'match-123');
      expect(backend.lastBootstrapRequest!['baseUrl'], 'https://api.gtex.dev');
      expect(
        backend.lastBootstrapRequest!['liveAccessToken'],
        'unity-access-token',
      );
      expect(
        backend.lastBootstrapRequest!['liveRefreshToken'],
        'unity-refresh-token',
      );
      expect(backend.lastBootstrapRequest!['runtimeMode'], 'live');
      expect(backend.lastBootstrapRequest!['environment'], 'custom');
    },
  );
}

class _StaticTransport implements GteTransport {
  const _StaticTransport({required this.responseBody});

  final Object? responseBody;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return GteTransportResponse(statusCode: 200, body: responseBody);
  }
}

class _BootstrapCaptureBackend
    implements Match3dBridgeBackend, Match3dBridgeSessionBackend {
  Map<String, Object?>? lastBootstrapRequest;

  @override
  Stream<dynamic> get events => const Stream<dynamic>.empty();

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<void> handleEvent(Map<String, dynamic> event) async {}

  @override
  Future<Map<String, dynamic>> getRuntimeInfo() async {
    return const <String, dynamic>{'available': true};
  }

  @override
  Future<Map<String, dynamic>> stageLiveBootstrap(
    Map<String, Object?> request,
  ) async {
    lastBootstrapRequest = Map<String, Object?>.from(request);
    return <String, dynamic>{
      'staged': true,
      'bootstrapPath': '/android/files/tmp/gtex-live-bootstrap.json',
      'matchId': request['matchId'] as String? ?? '',
    };
  }

  @override
  Future<Map<String, dynamic>> openSession(Map<String, Object?> request) async {
    return const <String, dynamic>{};
  }

  @override
  Future<Map<String, dynamic>> closeSession({String? sessionId}) async {
    return const <String, dynamic>{};
  }

  @override
  Future<Map<String, dynamic>> getSessionState() async {
    return const <String, dynamic>{};
  }
}

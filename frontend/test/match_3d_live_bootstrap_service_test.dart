import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/3d/models/match_3d_native_session.dart';
import 'package:gte_frontend/features/3d/services/match_3d_bridge.dart';
import 'package:gte_frontend/features/3d/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/shared/models/auth_session.dart';

void main() {
  test(
    'Android live bootstrap service stays unstaged while legacy runtime is quarantined',
    () async {
      final _BootstrapCaptureBackend backend = _BootstrapCaptureBackend();
      final _StaticTransport transport = _StaticTransport(
        responseBody: <String, Object?>{
          'success': true,
          'data': <String, Object?>{
            'match_id': 'match-123',
            'access_token': 'legacy-access-token',
            'refresh_token': 'legacy-refresh-token',
          },
        },
      );
      final Match3dAndroidLiveBootstrapService service =
          Match3dAndroidLiveBootstrapService(
            api: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'https://api.gtex.dev',
              ),
              transport: transport,
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

      expect(result.staged, isFalse);
      expect(result.bootstrapPath, isEmpty);
      expect(result.message, contains('canonical 2D broadcast match center'));
      expect(backend.lastBootstrapRequest, isNull);
      expect(transport.sendCount, 0);
    },
  );
}

class _StaticTransport implements GteTransport {
  _StaticTransport({required this.responseBody});

  final Object? responseBody;
  int sendCount = 0;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    sendCount += 1;
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

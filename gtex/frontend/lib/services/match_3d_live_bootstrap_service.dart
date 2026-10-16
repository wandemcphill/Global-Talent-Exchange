import '../data/gte_api_repository.dart';
import '../data/gte_authed_api.dart';
import '../models/match_3d_native_session.dart';
import 'match_3d_bridge.dart';

abstract interface class Match3dAndroidLiveBootstrapProvisioner {
  Future<Match3dAndroidLiveBootstrapResult> provision({
    required String matchId,
  });
}

class Match3dAndroidLiveBootstrapService
    implements Match3dAndroidLiveBootstrapProvisioner {
  Match3dAndroidLiveBootstrapService({
    required this.api,
    required this.bridge,
    DateTime Function()? now,
  }) : _now = now ?? DateTime.now;

  final GteAuthedApi api;
  final Match3DBridge bridge;
  final DateTime Function() _now;

  @override
  Future<Match3dAndroidLiveBootstrapResult> provision({
    required String matchId,
  }) async {
    final String resolvedMatchId = matchId.trim();
    if (resolvedMatchId.isEmpty) {
      return const Match3dAndroidLiveBootstrapResult.unstaged(
        message:
            'Unity live bootstrap is unavailable because the routed match id was missing.',
      );
    }

    try {
      final Object? rawGrant = await api.post(
        '/api/matches/$resolvedMatchId/unity-access',
        query: const <String, Object?>{'pay_to_view': false},
      );
      final Map<String, dynamic> grant = _requireMap(rawGrant);
      final String grantMatchId = _requireString(
        grant,
        'match_id',
        fallback: resolvedMatchId,
      );
      final String accessToken = _requireString(grant, 'access_token');
      final String refreshToken = _requireString(grant, 'refresh_token');
      final Match3dAndroidLiveBootstrapResult result =
          await bridge.stageLiveBootstrap(<String, Object?>{
            'profile': _profileForBaseUrl(api.config.baseUrl),
            'runtimeMode': 'live',
            'environment': 'custom',
            'matchId': grantMatchId,
            'baseUrl': _normalizedBaseUrl(api.config.baseUrl),
            'liveAccessToken': accessToken,
            'liveRefreshToken': refreshToken,
            'issuedAtUtc': _now().toUtc().toIso8601String(),
            'bootstrapTtlSeconds': 900,
            'consumeOnLoad': false,
          });
      return result.staged
          ? result
          : Match3dAndroidLiveBootstrapResult.unstaged(
            matchId: grantMatchId,
            message:
                result.message ??
                'Unity live bootstrap could not be staged on Android; Flutter 3D fallback active.',
          );
    } on GteApiException catch (error) {
      return Match3dAndroidLiveBootstrapResult.unstaged(
        matchId: resolvedMatchId,
        message:
            'Unity live bootstrap could not be issued from the live route: ${error.message}',
      );
    } on StateError catch (error) {
      return Match3dAndroidLiveBootstrapResult.unstaged(
        matchId: resolvedMatchId,
        message:
            'Unity live bootstrap payload was incomplete: ${error.message}',
      );
    } catch (error) {
      return Match3dAndroidLiveBootstrapResult.unstaged(
        matchId: resolvedMatchId,
        message:
            'Unity live bootstrap failed on Android; Flutter 3D fallback active. ${error.toString()}',
      );
    }
  }
}

Map<String, dynamic> _requireMap(Object? value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map<Object?, Object?>) {
    return value.map(
      (Object? key, Object? nestedValue) =>
          MapEntry(key.toString(), nestedValue),
    );
  }
  throw const GteApiException(
    type: GteApiErrorType.parsing,
    message: 'Unity live access did not return a valid JSON object.',
  );
}

String _requireString(
  Map<String, dynamic> payload,
  String key, {
  String fallback = '',
}) {
  final String resolved = (payload[key] ?? fallback).toString().trim();
  if (resolved.isEmpty) {
    throw StateError('Missing "$key".');
  }
  return resolved;
}

String _normalizedBaseUrl(String baseUrl) {
  return baseUrl.trim().replaceFirst(RegExp(r'/+$'), '');
}

String _profileForBaseUrl(String baseUrl) {
  final Uri uri = Uri.parse(baseUrl.trim());
  final String host = uri.host.trim().toLowerCase();
  if (host == '127.0.0.1' || host == 'localhost' || host == '10.0.2.2') {
    return 'local';
  }
  return 'custom';
}

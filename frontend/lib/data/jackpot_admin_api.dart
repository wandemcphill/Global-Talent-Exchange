import '../models/jackpot_admin_models.dart';
import 'gte_authed_api.dart';

class JackpotAdminApi {
  JackpotAdminApi({required this.client});

  final GteAuthedApi client;

  Future<JackpotAdminRuntime> fetchRuntime() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/jackpot/runtime',
    );
    return JackpotAdminRuntime.fromJson(payload);
  }

  Future<List<JackpotHistoryItem>> fetchHistory({int limit = 12}) async {
    final List<dynamic> payload = await client.getList(
      '/api/jackpot/history',
      query: <String, Object?>{'limit': limit},
      auth: false,
    );
    return payload.map(JackpotHistoryItem.fromJson).toList(growable: false);
  }

  Future<JackpotAdminRuntime> updateRuntime(Map<String, Object?> body) async {
    final Object? payload = await client.request(
      'POST',
      '/api/admin/jackpot/runtime',
      body: body,
    );
    return JackpotAdminRuntime.fromJson(payload);
  }

  Future<JackpotAdminRuntime> updateBalance({
    required String balance,
    String? reason,
  }) async {
    final Object? payload = await client.request(
      'PATCH',
      '/api/admin/jackpot/balance',
      body: <String, Object?>{
        'balance': balance,
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      },
    );
    return JackpotAdminRuntime.fromJson(payload);
  }

  Future<String> triggerRound() async {
    final Object? payload = await client.request(
      'POST',
      '/api/admin/jackpot/trigger',
      body: const <String, Object?>{},
    );
    if (payload is Map) {
      final Object? detail = payload['detail'];
      if (detail != null) {
        return detail.toString();
      }
    }
    return 'Jackpot round triggered.';
  }
}

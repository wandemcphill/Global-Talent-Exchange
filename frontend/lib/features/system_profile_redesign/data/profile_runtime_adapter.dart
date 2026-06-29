import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_models.dart';
import '../../../providers/gte_exchange_controller.dart';

class GtexProfileRuntimeSnapshot {
  const GtexProfileRuntimeSnapshot({
    required this.bootstrap,
    required this.user,
    required this.security,
    required this.sessions,
    required this.wallet,
    required this.club,
    required this.syncedAt,
  });

  final Map<String, Object?> bootstrap;
  final GteCurrentUser user;
  final Map<String, Object?> security;
  final List<Map<String, Object?>> sessions;
  final GteWalletSummary wallet;
  final Map<String, Object?>? club;
  final DateTime syncedAt;

  String? get clubName {
    final Map<String, Object?>? clubPayload = club;
    if (clubPayload == null) {
      return null;
    }
    return _firstString(clubPayload, const <String>[
      'name',
      'club_name',
      'clubName',
      'display_name',
      'displayName',
    ]);
  }

  int get activeSessionCount {
    final Object? explicit =
        security['active_session_count'] ?? security['activeSessionCount'];
    if (explicit is int) {
      return explicit;
    }
    if (explicit is num) {
      return explicit.toInt();
    }
    final int parsed = int.tryParse(explicit?.toString() ?? '') ?? 0;
    if (parsed > 0) {
      return parsed;
    }
    return sessions.length;
  }

  bool get mfaEnabled {
    final Object? value =
        security['mfa_enabled'] ??
        security['mfaEnabled'] ??
        security['totp_enabled'] ??
        security['totpEnabled'];
    if (value is bool) {
      return value;
    }
    final String normalized = value?.toString().trim().toLowerCase() ?? '';
    return normalized == 'true' || normalized == '1' || normalized == 'yes';
  }

  List<String> get roles => _stringList(bootstrap['roles']);

  List<String> get permissions => _stringList(bootstrap['permissions']);

  bool get strictLive {
    final Map<String, Object?> runtime =
        _mapValue(bootstrap['runtime']) ?? const <String, Object?>{};
    return _boolValue(runtime['strictLive'] ?? runtime['strict_live']);
  }

  bool get korapayEnabled {
    final Map<String, Object?> runtime =
        _mapValue(bootstrap['runtime']) ?? const <String, Object?>{};
    final Map<String, Object?> payments =
        _mapValue(runtime['payments']) ?? const <String, Object?>{};
    return _boolValue(
      payments['korapayEnabled'] ?? payments['korapay_enabled'],
    );
  }

  bool get paystackEnabled {
    final Map<String, Object?> runtime =
        _mapValue(bootstrap['runtime']) ?? const <String, Object?>{};
    final Map<String, Object?> payments =
        _mapValue(runtime['payments']) ?? const <String, Object?>{};
    return _boolValue(
      payments['paystackEnabled'] ?? payments['paystack_enabled'],
    );
  }

  String get sessionSource => 'profile_runtime_adapter';
}

class BootstrapSessionRepository {
  const BootstrapSessionRepository({required GteAuthedApi client})
    : _client = client;

  final GteAuthedApi _client;

  Future<Map<String, Object?>> load() async {
    return Map<String, Object?>.from(
      await _client.getMap('/api/session/bootstrap'),
    );
  }
}

class ProfileRuntimeAdapter {
  ProfileRuntimeAdapter({
    required GteAuthedApi client,
    BootstrapSessionRepository? bootstrapRepository,
  }) : _client = client,
       _bootstrapRepository =
           bootstrapRepository ?? BootstrapSessionRepository(client: client);

  factory ProfileRuntimeAdapter.fromController(
    GteExchangeController controller,
  ) {
    final String? token = controller.accessToken;
    if (token == null || token.trim().isEmpty) {
      throw const GteApiException(
        type: GteApiErrorType.unauthorized,
        message: 'A live GTEX access token is required for Profile V2.',
      );
    }
    return ProfileRuntimeAdapter(
      client: GteAuthedApi(
        config: controller.api.config,
        transport: controller.api.transport,
        accessToken: token,
      ),
    );
  }

  final GteAuthedApi _client;
  final BootstrapSessionRepository _bootstrapRepository;

  Future<GtexProfileRuntimeSnapshot> load() async {
    final List<dynamic> payload = await Future.wait<dynamic>(<Future<dynamic>>[
      _bootstrapRepository.load(),
      _client.getMap('/api/profile'),
      _client.getMap('/api/profile/security'),
      _client.getList('/api/profile/sessions'),
      _client.getMap('/api/wallet/summary'),
      _optionalClub(),
    ]);

    return GtexProfileRuntimeSnapshot(
      bootstrap: Map<String, Object?>.from(payload[0] as Map),
      user: GteCurrentUser.fromJson(payload[1]),
      security: Map<String, Object?>.from(payload[2] as Map),
      sessions: (payload[3] as List<dynamic>)
          .whereType<Map>()
          .map((Map value) => Map<String, Object?>.from(value))
          .toList(growable: false),
      wallet: GteWalletSummary.fromJson(payload[4]),
      club:
          payload[5] == null
              ? null
              : Map<String, Object?>.from(payload[5] as Map),
      syncedAt: DateTime.now().toUtc(),
    );
  }

  Future<Map<String, dynamic>?> _optionalClub() async {
    try {
      return await _client.getMap('/api/club/current');
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.notFound || error.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }
}

String? _firstString(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is String && value.trim().isNotEmpty) {
      return value.trim();
    }
  }
  return null;
}

Map<String, Object?>? _mapValue(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return Map<String, Object?>.from(value);
  }
  return null;
}

List<String> _stringList(Object? value) {
  if (value is Iterable) {
    return value
        .map((Object? item) => item?.toString().trim() ?? '')
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);
  }
  return const <String>[];
}

bool _boolValue(Object? value) {
  if (value is bool) {
    return value;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  return normalized == 'true' || normalized == '1' || normalized == 'yes';
}

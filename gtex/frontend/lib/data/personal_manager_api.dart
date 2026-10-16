import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';

class PersonalManagerProfile {
  const PersonalManagerProfile({
    required this.id,
    required this.userId,
    required this.displayName,
    required this.qualityBand,
    required this.gsiMin,
    required this.gsiMax,
    required this.gsiRating,
    required this.fanCoinPrice,
    required this.permanent,
    required this.transferable,
    required this.salaryBearing,
    this.tacticalIdentity = const <String, Object?>{},
  });

  final String id;
  final String userId;
  final String displayName;
  final String qualityBand;
  final int gsiMin;
  final int gsiMax;
  final int gsiRating;
  final int fanCoinPrice;
  final bool permanent;
  final bool transferable;
  final bool salaryBearing;
  final Map<String, Object?> tacticalIdentity;

  factory PersonalManagerProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'personal manager',
    );
    return PersonalManagerProfile(
      id: GteJson.string(json, <String>['id']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      displayName: GteJson.string(json, <String>['display_name', 'displayName']),
      qualityBand:
          GteJson.stringOrNull(json, <String>['quality_band', 'qualityBand']) ??
          '${GteJson.integer(json, <String>['quality_band', 'qualityBand'], fallback: 1)}',
      gsiMin: GteJson.integer(json, <String>['gsi_min', 'gsiMin']),
      gsiMax: GteJson.integer(json, <String>['gsi_max', 'gsiMax']),
      gsiRating: GteJson.integer(json, <String>['gsi_rating', 'gsiRating']),
      fanCoinPrice: GteJson.integer(json, <String>[
        'fan_coin_price',
        'fanCoinPrice',
      ]),
      permanent: GteJson.boolean(json, <String>['permanent'], fallback: true),
      transferable: GteJson.boolean(
        json,
        <String>['transferable'],
        fallback: false,
      ),
      salaryBearing: GteJson.boolean(
        json,
        <String>['salary_bearing', 'salaryBearing'],
        fallback: false,
      ),
      tacticalIdentity: Map<String, Object?>.from(
        GteJson.map(
          json,
          keys: <String>['tactical_identity', 'tacticalIdentity'],
          fallback: const <String, Object?>{},
        ),
      ),
    );
  }
}

class PersonalManagerApi {
  PersonalManagerApi({required this.client});

  final GteAuthedApi client;

  factory PersonalManagerApi.standard({
    required String baseUrl,
    required String accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return PersonalManagerApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
    );
  }

  Future<PersonalManagerProfile?> fetchMe() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/clubs/personal-manager/me',
        auth: true,
      );
      return PersonalManagerProfile.fromJson(payload);
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.notFound) {
        return null;
      }
      rethrow;
    }
  }

  Future<PersonalManagerProfile> create({
    required String displayName,
    required int qualityBand,
    required int fanCoinPrice,
    Map<String, Object?> tacticalIdentity = const <String, Object?>{},
  }) async {
    final Object? payload = await client.post(
      '/api/clubs/personal-manager',
      body: <String, Object?>{
        'display_name': displayName,
        'quality_band': qualityBand,
        'fan_coin_price': fanCoinPrice,
        'tactical_identity': tacticalIdentity,
      },
      auth: true,
    );
    return PersonalManagerProfile.fromJson(payload);
  }

  Future<Map<String, Object?>> appointToClub(String clubId) async {
    final Object? payload = await client.post(
      '/api/clubs/$clubId/growth/personal-manager/appoint',
      body: const <String, Object?>{},
      auth: true,
    );
    return Map<String, Object?>.from(
      GteJson.map(payload, label: 'personal manager appointment'),
    );
  }
}

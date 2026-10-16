import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';

class GteCreateClubRequest {
  const GteCreateClubRequest({
    required this.clubName,
    required this.shortName,
    required this.slug,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
    required this.homeVenueName,
    required this.countryCode,
    required this.regionName,
    required this.cityName,
    required this.description,
    required this.visibility,
  });

  final String clubName;
  final String? shortName;
  final String slug;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;
  final String? homeVenueName;
  final String? countryCode;
  final String? regionName;
  final String? cityName;
  final String? description;
  final String visibility;

  Map<String, Object?> toJson() => <String, Object?>{
    'club_name': clubName,
    if (shortName != null && shortName!.trim().isNotEmpty)
      'short_name': shortName!.trim(),
    'slug': slug,
    'primary_color': primaryColor,
    'secondary_color': secondaryColor,
    'accent_color': accentColor,
    if (homeVenueName != null && homeVenueName!.trim().isNotEmpty)
      'home_venue_name': homeVenueName!.trim(),
    if (countryCode != null && countryCode!.trim().isNotEmpty)
      'country_code': countryCode!.trim().toUpperCase(),
    if (regionName != null && regionName!.trim().isNotEmpty)
      'region_name': regionName!.trim(),
    if (cityName != null && cityName!.trim().isNotEmpty)
      'city_name': cityName!.trim(),
    if (description != null && description!.trim().isNotEmpty)
      'description': description!.trim(),
    'visibility': visibility,
  };
}

class GteCreatedClubProfile {
  const GteCreatedClubProfile({
    required this.id,
    required this.clubName,
    required this.slug,
    this.shortName,
    this.countryCode,
    this.regionName,
    this.cityName,
    this.homeVenueName,
  });

  final String id;
  final String clubName;
  final String slug;
  final String? shortName;
  final String? countryCode;
  final String? regionName;
  final String? cityName;
  final String? homeVenueName;

  factory GteCreatedClubProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club creation response',
    );
    final Map<String, Object?> profile = GteJson.map(
      GteJson.value(json, const <String>['profile']) ?? json,
      label: 'club profile',
    );
    return GteCreatedClubProfile(
      id: GteJson.string(profile, const <String>['id']),
      clubName: GteJson.string(profile, const <String>[
        'club_name',
        'clubName',
      ]),
      slug: GteJson.string(profile, const <String>['slug']),
      shortName: GteJson.stringOrNull(profile, const <String>[
        'short_name',
        'shortName',
      ]),
      countryCode: GteJson.stringOrNull(profile, const <String>[
        'country_code',
        'countryCode',
      ]),
      regionName: GteJson.stringOrNull(profile, const <String>[
        'region_name',
        'regionName',
      ]),
      cityName: GteJson.stringOrNull(profile, const <String>[
        'city_name',
        'cityName',
      ]),
      homeVenueName: GteJson.stringOrNull(profile, const <String>[
        'home_venue_name',
        'homeVenueName',
      ]),
    );
  }
}

class ClubCreationApi {
  ClubCreationApi({required this.client});

  factory ClubCreationApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    return ClubCreationApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
    );
  }

  final GteAuthedApi client;

  Future<GteCreatedClubProfile> createClub(GteCreateClubRequest request) async {
    final Object? response = await client.post(
      '/api/clubs',
      body: request.toJson(),
    );
    return GteCreatedClubProfile.fromJson(response);
  }
}

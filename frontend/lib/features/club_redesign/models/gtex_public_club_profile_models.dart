import 'package:flutter/foundation.dart';

typedef GtexPublicJson = Map<String, Object?>;

String? _publicString(Object? value) {
  if (value == null) return null;
  final String text = value.toString().trim();
  return text.isEmpty ? null : text;
}

int? _publicInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.round();
  return int.tryParse(value?.toString() ?? '');
}

double? _publicDouble(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '');
}

GtexPublicJson _publicMap(Object? value) =>
    value is Map ? Map<String, Object?>.from(value) : <String, Object?>{};

List<GtexPublicJson> _publicRows(Object? value) =>
    value is List
        ? value.whereType<Map>().map((Map row) => Map<String, Object?>.from(row)).toList(growable: false)
        : const <GtexPublicJson>[];


@immutable
class GtexPublicClubAsset {
  const GtexPublicClubAsset({
    required this.name,
    required this.category,
    this.value,
    this.editionNumber,
    this.previewFile,
    this.fallbackLabel,
    this.supplyCap,
  });

  final String name;
  final String category;
  final String? value;
  final int? editionNumber;
  final String? previewFile;
  final String? fallbackLabel;
  final int? supplyCap;

  factory GtexPublicClubAsset.fromJson(GtexPublicJson json) => GtexPublicClubAsset(
    name: _publicString(json['name']) ?? 'Club asset',
    category: _publicString(json['category']) ?? 'asset',
    value: _publicString(json['value']),
    editionNumber: _publicInt(json['edition_number']),
    previewFile: _publicString(json['preview_file']),
    fallbackLabel: _publicString(json['fallback_label']),
    supplyCap: _publicInt(json['supply_cap']),
  );
}

@immutable
class GtexPublicClubPerson {
  const GtexPublicClubPerson({
    required this.role,
    required this.title,
    this.name,
    this.rating,
    this.appointed = false,
  });

  final String role;
  final String title;
  final String? name;
  final int? rating;
  final bool appointed;

  factory GtexPublicClubPerson.fromJson(GtexPublicJson json) => GtexPublicClubPerson(
    role: _publicString(json['role']) ?? 'staff',
    title: _publicString(json['title']) ?? 'Club staff',
    name: _publicString(json['name']),
    rating: _publicInt(json['rating']),
    appointed: json['appointed'] == true,
  );
}

@immutable
class GtexPublicClubPlayer {
  const GtexPublicClubPlayer({
    required this.id,
    required this.name,
    this.position,
    this.age,
    this.rating,
    this.potential,
    this.isRegen = false,
    this.portraitUrl,
  });

  final String id;
  final String name;
  final String? position;
  final int? age;
  final int? rating;
  final int? potential;
  final bool isRegen;
  final String? portraitUrl;

  factory GtexPublicClubPlayer.fromJson(GtexPublicJson json) => GtexPublicClubPlayer(
    id: _publicString(json['id']) ?? '',
    name: _publicString(json['name']) ?? 'Player',
    position: _publicString(json['position']),
    age: _publicInt(json['age']),
    rating: _publicInt(json['rating']),
    potential: _publicInt(json['potential']),
    isRegen: json['is_regen'] == true,
    portraitUrl: _publicString(json['portrait_url']),
  );
}

@immutable
class GtexPublicClubTrophy {
  const GtexPublicClubTrophy({required this.name, this.competition, this.season});

  final String name;
  final String? competition;
  final String? season;

  factory GtexPublicClubTrophy.fromJson(GtexPublicJson json) => GtexPublicClubTrophy(
    name: _publicString(json['name']) ?? 'Honour',
    competition: _publicString(json['competition']),
    season: _publicString(json['season']),
  );
}

@immutable
class GtexPublicClubSummary {
  const GtexPublicClubSummary({
    required this.id,
    required this.name,
    required this.slug,
    this.shortName,
    this.city,
    this.countryCode,
    this.crestUrl,
    this.primaryColor,
    this.secondaryColor,
  });

  final String id;
  final String name;
  final String slug;
  final String? shortName;
  final String? city;
  final String? countryCode;
  final String? crestUrl;
  final String? primaryColor;
  final String? secondaryColor;

  factory GtexPublicClubSummary.fromJson(GtexPublicJson json) => GtexPublicClubSummary(
    id: _publicString(json['id']) ?? '',
    name: _publicString(json['name']) ?? 'GTEX Club',
    slug: _publicString(json['slug']) ?? '',
    shortName: _publicString(json['short_name']),
    city: _publicString(json['city']),
    countryCode: _publicString(json['country_code']),
    crestUrl: _publicString(json['crest_url']),
    primaryColor: _publicString(json['primary_color']),
    secondaryColor: _publicString(json['secondary_color']),
  );
}

@immutable
class GtexPublicOwnerSummary {
  const GtexPublicOwnerSummary({
    required this.id,
    required this.displayName,
    required this.clubCount,
    required this.luxuryAssetCount,
    this.netWorth,
    this.netWorthCurrency = 'GTX',
    this.profilePath,
    this.publicClubs = const <GtexPublicClubSummary>[],
  });

  final String id;
  final String displayName;
  final int clubCount;
  final int luxuryAssetCount;
  final String? netWorth;
  final String netWorthCurrency;
  final String? profilePath;
  final List<GtexPublicClubSummary> publicClubs;

  factory GtexPublicOwnerSummary.fromJson(GtexPublicJson json) => GtexPublicOwnerSummary(
    id: _publicString(json['id']) ?? '',
    displayName: _publicString(json['display_name']) ?? 'Club Owner',
    clubCount: _publicInt(json['club_count']) ?? 0,
    luxuryAssetCount: _publicInt(json['luxury_asset_count']) ?? 0,
    netWorth: _publicString(json['net_worth']),
    netWorthCurrency: _publicString(json['net_worth_currency']) ?? 'GTX',
    profilePath: _publicString(json['profile_path']),
    publicClubs: _publicRows(json['public_clubs'])
        .map(GtexPublicClubSummary.fromJson)
        .toList(growable: false),
  );
}

@immutable
class GtexPublicClubProfileData {
  const GtexPublicClubProfileData({
    required this.clubId,
    required this.name,
    required this.slug,
    required this.owner,
    required this.stadium,
    required this.facilities,
    required this.academy,
    required this.squadPlayerCount,
    this.squadPlayers = const <GtexPublicClubPlayer>[],
    required this.staff,
    required this.coachBuses,
    required this.trophies,
    this.shortName,
    this.description,
    this.crestUrl,
    this.primaryColor = '#101B32',
    this.secondaryColor = '#D5B46A',
    this.accentColor = '#24D18F',
    this.countryCode,
    this.regionName,
    this.cityName,
    this.foundedYear,
    this.homeVenueName,
    this.bestPlayer,
    this.mostPromisingPlayer,
  });

  final String clubId;
  final String name;
  final String slug;
  final String? shortName;
  final String? description;
  final String? crestUrl;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;
  final String? countryCode;
  final String? regionName;
  final String? cityName;
  final int? foundedYear;
  final String? homeVenueName;
  final GtexPublicOwnerSummary owner;
  final GtexPublicJson stadium;
  final GtexPublicJson facilities;
  final GtexPublicJson academy;
  final int squadPlayerCount;
  final List<GtexPublicClubPlayer> squadPlayers;
  final GtexPublicClubPlayer? bestPlayer;
  final GtexPublicClubPlayer? mostPromisingPlayer;
  final List<GtexPublicClubPerson> staff;
  final List<GtexPublicClubAsset> coachBuses;
  final List<GtexPublicClubTrophy> trophies;

  factory GtexPublicClubProfileData.fromJson(GtexPublicJson json) {
    final GtexPublicJson club = _publicMap(json['club']);
    final GtexPublicJson squad = _publicMap(json['squad']);
    final Object? best = squad['best_player'];
    final Object? promising = squad['most_promising_player'];
    return GtexPublicClubProfileData(
      clubId: _publicString(club['id']) ?? _publicString(json['club_id']) ?? '',
      name: _publicString(club['name']) ?? 'GTEX Club',
      slug: _publicString(club['slug']) ?? '',
      shortName: _publicString(club['short_name']),
      description: _publicString(club['description']),
      crestUrl: _publicString(club['crest_url']),
      primaryColor: _publicString(club['primary_color']) ?? '#101B32',
      secondaryColor: _publicString(club['secondary_color']) ?? '#D5B46A',
      accentColor: _publicString(club['accent_color']) ?? '#24D18F',
      countryCode: _publicString(club['country_code']),
      regionName: _publicString(club['region_name']),
      cityName: _publicString(club['city_name']),
      foundedYear: _publicInt(club['founded_year']),
      homeVenueName: _publicString(club['home_venue_name']),
      owner: GtexPublicOwnerSummary.fromJson(_publicMap(json['owner'])),
      stadium: _publicMap(json['stadium']),
      facilities: _publicMap(json['facilities']),
      academy: _publicMap(json['academy']),
      squadPlayerCount: _publicInt(squad['player_count']) ?? 0,
      squadPlayers: _publicRows(squad['players'])
          .map(GtexPublicClubPlayer.fromJson)
          .toList(growable: false),
      bestPlayer: best is Map ? GtexPublicClubPlayer.fromJson(Map<String, Object?>.from(best)) : null,
      mostPromisingPlayer: promising is Map
          ? GtexPublicClubPlayer.fromJson(Map<String, Object?>.from(promising))
          : null,
      staff: _publicRows(json['staff']).map(GtexPublicClubPerson.fromJson).toList(growable: false),
      coachBuses: _publicRows(json['coach_buses']).map(GtexPublicClubAsset.fromJson).toList(growable: false),
      trophies: _publicRows(json['trophies']).map(GtexPublicClubTrophy.fromJson).toList(growable: false),
    );
  }
}

@immutable
class GtexPublicOwnerProfileData {
  const GtexPublicOwnerProfileData({
    required this.id,
    required this.displayName,
    required this.clubCount,
    required this.luxuryAssetCount,
    required this.assets,
    required this.publicClubs,
    this.netWorth,
    this.netWorthCurrency = 'GTX',
    this.profilePath,
  });

  final String id;
  final String displayName;
  final int clubCount;
  final int luxuryAssetCount;
  final String? netWorth;
  final String netWorthCurrency;
  final String? profilePath;
  final List<GtexPublicClubAsset> assets;
  final List<GtexPublicClubSummary> publicClubs;

  factory GtexPublicOwnerProfileData.fromJson(GtexPublicJson json) => GtexPublicOwnerProfileData(
    id: _publicString(json['id']) ?? '',
    displayName: _publicString(json['display_name']) ?? 'Club Owner',
    clubCount: _publicInt(json['club_count']) ?? 0,
    luxuryAssetCount: _publicInt(json['luxury_asset_count']) ?? _publicRows(json['assets']).length,
    netWorth: _publicString(json['net_worth']),
    netWorthCurrency: _publicString(json['net_worth_currency']) ?? 'GTX',
    profilePath: _publicString(json['profile_path']),
    assets: _publicRows(json['assets']).map(GtexPublicClubAsset.fromJson).toList(growable: false),
    publicClubs: _publicRows(json['public_clubs']).map(GtexPublicClubSummary.fromJson).toList(growable: false),
  );
}

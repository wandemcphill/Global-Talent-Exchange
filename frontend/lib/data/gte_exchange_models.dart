import 'gte_models.dart';
import '../models/player_avatar.dart';

const Object _playerFilterUnset = Object();

class PlayerFilter {
  const PlayerFilter({
    this.search,
    this.position,
    this.country,
    this.nationalTeam,
    this.club,
    this.league,
    this.division,
    this.minAge,
    this.maxAge,
    this.minValue,
    this.maxValue,
    this.availability,
  });

  final String? search;
  final String? position;
  final String? country;
  final String? nationalTeam;
  final String? club;
  final String? league;
  final String? division;
  final int? minAge;
  final int? maxAge;
  final double? minValue;
  final double? maxValue;
  final String? availability;

  PlayerFilter copyWith({
    Object? search = _playerFilterUnset,
    Object? position = _playerFilterUnset,
    Object? country = _playerFilterUnset,
    Object? nationalTeam = _playerFilterUnset,
    Object? club = _playerFilterUnset,
    Object? league = _playerFilterUnset,
    Object? division = _playerFilterUnset,
    Object? minAge = _playerFilterUnset,
    Object? maxAge = _playerFilterUnset,
    Object? minValue = _playerFilterUnset,
    Object? maxValue = _playerFilterUnset,
    Object? availability = _playerFilterUnset,
  }) {
    return PlayerFilter(
      search: search == _playerFilterUnset ? this.search : search as String?,
      position:
          position == _playerFilterUnset ? this.position : position as String?,
      country:
          country == _playerFilterUnset ? this.country : country as String?,
      nationalTeam:
          nationalTeam == _playerFilterUnset
              ? this.nationalTeam
              : nationalTeam as String?,
      club: club == _playerFilterUnset ? this.club : club as String?,
      league: league == _playerFilterUnset ? this.league : league as String?,
      division:
          division == _playerFilterUnset ? this.division : division as String?,
      minAge: minAge == _playerFilterUnset ? this.minAge : minAge as int?,
      maxAge: maxAge == _playerFilterUnset ? this.maxAge : maxAge as int?,
      minValue:
          minValue == _playerFilterUnset ? this.minValue : minValue as double?,
      maxValue:
          maxValue == _playerFilterUnset ? this.maxValue : maxValue as double?,
      availability:
          availability == _playerFilterUnset
              ? this.availability
              : availability as String?,
    );
  }

  PlayerFilter reset() => const PlayerFilter();

  PlayerFilter normalized() {
    return PlayerFilter(
      search: _trimOrNull(search),
      position: _trimOrNull(position),
      country: _trimOrNull(country),
      nationalTeam: _trimOrNull(nationalTeam),
      club: _trimOrNull(club),
      league: _trimOrNull(league),
      division: _trimOrNull(division),
      minAge: minAge,
      maxAge: maxAge,
      minValue: minValue,
      maxValue: maxValue,
      availability: _trimOrNull(availability),
    );
  }

  bool get hasActiveFilters {
    final PlayerFilter value = normalized();
    return value.search != null ||
        value.position != null ||
        value.country != null ||
        value.nationalTeam != null ||
        value.club != null ||
        value.league != null ||
        value.division != null ||
        value.minAge != null ||
        value.maxAge != null ||
        value.minValue != null ||
        value.maxValue != null ||
        value.availability != null;
  }

  @override
  bool operator ==(Object other) {
    return other is PlayerFilter &&
        other.search == search &&
        other.position == position &&
        other.country == country &&
        other.nationalTeam == nationalTeam &&
        other.club == club &&
        other.league == league &&
        other.division == division &&
        other.minAge == minAge &&
        other.maxAge == maxAge &&
        other.minValue == minValue &&
        other.maxValue == maxValue &&
        other.availability == availability;
  }

  @override
  int get hashCode => Object.hash(
    search,
    position,
    country,
    nationalTeam,
    club,
    league,
    division,
    minAge,
    maxAge,
    minValue,
    maxValue,
    availability,
  );
}

class GteMarketPlayersQuery {
  const GteMarketPlayersQuery({
    this.limit = 20,
    this.cursor,
    this.offset = 0,
    this.search,
    this.position,
    this.country,
    this.nationalTeam,
    this.club,
    this.league,
    this.division,
    this.minAge,
    this.maxAge,
    this.minValue,
    this.maxValue,
    this.availability,
  });

  final int limit;
  final String? cursor;
  final int offset;
  final String? search;
  final String? position;
  final String? country;
  final String? nationalTeam;
  final String? club;
  final String? league;
  final String? division;
  final int? minAge;
  final int? maxAge;
  final double? minValue;
  final double? maxValue;
  final String? availability;

  Map<String, Object?> toQueryParameters() {
    final String? trimmedSearch = search?.trim();
    final String? trimmedCursor = cursor?.trim();
    final String? trimmedPosition = _trimOrNull(position);
    final String? trimmedCountry = _trimOrNull(country);
    final String? trimmedNationalTeam = _trimOrNull(nationalTeam);
    final String? trimmedClub = _trimOrNull(club);
    final String? trimmedLeague = _trimOrNull(league);
    final String? trimmedDivision = _trimOrNull(division);
    final String? trimmedAvailability = _trimOrNull(availability);
    return <String, Object?>{
      'limit': limit,
      if (trimmedCursor != null && trimmedCursor.isNotEmpty)
        'cursor': trimmedCursor
      else
        'offset': offset,
      if (trimmedSearch != null && trimmedSearch.isNotEmpty)
        'search': trimmedSearch,
      if (trimmedPosition != null) 'position': trimmedPosition,
      if (trimmedCountry != null) 'country': trimmedCountry,
      if (trimmedNationalTeam != null) 'national_team': trimmedNationalTeam,
      if (trimmedClub != null) 'club': trimmedClub,
      if (trimmedLeague != null) 'league': trimmedLeague,
      if (trimmedDivision != null) 'division': trimmedDivision,
      if (minAge != null) 'min_age': minAge,
      if (maxAge != null) 'max_age': maxAge,
      if (minValue != null) 'min_value': minValue,
      if (maxValue != null) 'max_value': maxValue,
      if (trimmedAvailability != null) 'availability': trimmedAvailability,
    };
  }
}

class GteMarketPlayerListItem {
  const GteMarketPlayerListItem({
    required this.playerId,
    required this.playerName,
    required this.position,
    required this.nationality,
    this.nationalityCode,
    this.currentClubId,
    required this.currentClubName,
    this.currentCompetitionId,
    this.currentCompetitionName,
    this.currentCompetitionCountryName,
    this.currentDivisionId,
    this.currentDivisionName,
    this.age,
    this.marketValueEur,
    required this.currentValueCredits,
    required this.movementPct,
    required this.trendScore,
    required this.marketInterestScore,
    required this.averageRating,
    this.globalScoutingIndex,
    this.previousGlobalScoutingIndex,
    this.globalScoutingIndexMovementPct,
    this.transferListingId,
    this.transferListingStatus,
    this.sellingClubId,
    this.isAvailable = true,
    this.availabilityLabel = 'Available now',
    this.askingType = 'transfer',
    this.agentUserId = '',
    this.agentName = 'Listed agent',
    this.marketplaceNote,
    this.isTradable = true,
    this.salaryAmount,
    this.contractYearsRemaining,
    this.buyClauseAmount,
    this.loanTerms = const <String, Object?>{},
    this.swapTerms = const <String, Object?>{},
    this.availabilityTerms = const <String, Object?>{},
    this.imageUrl,
    this.avatar,
  });

  final String playerId;
  final String playerName;
  final String? position;
  final String? nationality;
  final String? nationalityCode;
  final String? currentClubId;
  final String? currentClubName;
  final String? currentCompetitionId;
  final String? currentCompetitionName;
  final String? currentCompetitionCountryName;
  final String? currentDivisionId;
  final String? currentDivisionName;
  final int? age;
  final double? marketValueEur;
  final double? currentValueCredits;
  final double? movementPct;
  final double? trendScore;
  final int? marketInterestScore;
  final double? averageRating;
  final double? globalScoutingIndex;
  final double? previousGlobalScoutingIndex;
  final double? globalScoutingIndexMovementPct;
  final String? transferListingId;
  final String? transferListingStatus;
  final String? sellingClubId;
  final bool isAvailable;
  final String availabilityLabel;
  final String askingType;
  final String agentUserId;
  final String agentName;
  final String? marketplaceNote;
  final bool isTradable;
  final double? salaryAmount;
  final double? contractYearsRemaining;
  final double? buyClauseAmount;
  final Map<String, Object?> loanTerms;
  final Map<String, Object?> swapTerms;
  final Map<String, Object?> availabilityTerms;
  final String? imageUrl;
  final PlayerAvatar? avatar;

  bool get isRising => (movementPct ?? 0) > 0;

  int get displayRating {
    final double? dynamicGsi = globalScoutingIndex;
    if (dynamicGsi != null) {
      return dynamicGsi.round().clamp(0, 100).toInt();
    }
    final double? rating = averageRating;
    if (rating != null) {
      return (rating * 10).round().clamp(0, 100).toInt();
    }
    final double? trend = trendScore;
    if (trend != null) {
      return trend.round().clamp(0, 100).toInt();
    }
    return (marketInterestScore ?? 0).clamp(0, 100).toInt();
  }

  String get gsiBand {
    final int score = displayRating;
    if (score >= 90) return 'World Class';
    if (score >= 84) return 'Elite';
    if (score >= 75) return 'Professional';
    if (score >= 65) return 'Average';
    if (score >= 50) return 'Developing';
    return 'Youth';
  }

  factory GteMarketPlayerListItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market player list item',
    );
    return GteMarketPlayerListItem(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      position: GteJson.stringOrNull(json, <String>['position']),
      nationality: GteJson.stringOrNull(json, <String>['nationality']),
      nationalityCode: GteJson.stringOrNull(json, <String>[
        'nationality_code',
        'nationalityCode',
      ]),
      currentClubId: GteJson.stringOrNull(json, <String>[
        'current_club_id',
        'currentClubId',
      ]),
      currentClubName: GteJson.stringOrNull(json, <String>[
        'current_club_name',
        'currentClubName',
      ]),
      currentCompetitionId: GteJson.stringOrNull(json, <String>[
        'current_competition_id',
        'currentCompetitionId',
      ]),
      currentCompetitionName: GteJson.stringOrNull(json, <String>[
        'current_competition_name',
        'currentCompetitionName',
      ]),
      currentCompetitionCountryName: GteJson.stringOrNull(json, <String>[
        'current_competition_country_name',
        'currentCompetitionCountryName',
      ]),
      currentDivisionId: GteJson.stringOrNull(json, <String>[
        'current_division_id',
        'currentDivisionId',
      ]),
      currentDivisionName: GteJson.stringOrNull(json, <String>[
        'current_division_name',
        'currentDivisionName',
      ]),
      age: _nullableInteger(json, <String>['age']),
      marketValueEur: _nullableNumber(json, <String>[
        'market_value_eur',
        'marketValueEur',
      ]),
      currentValueCredits: _nullableNumber(json, <String>[
        'current_value_credits',
        'currentValueCredits',
      ]),
      movementPct: _nullableNumber(json, <String>[
        'movement_pct',
        'movementPct',
      ]),
      trendScore: _nullableNumber(json, <String>['trend_score', 'trendScore']),
      marketInterestScore: _nullableInteger(json, <String>[
        'market_interest_score',
        'marketInterestScore',
      ]),
      averageRating: _nullableNumber(json, <String>[
        'average_rating',
        'averageRating',
      ]),
      globalScoutingIndex: _nullableNumber(json, <String>[
        'global_scouting_index',
        'globalScoutingIndex',
        'gsi',
      ]),
      previousGlobalScoutingIndex: _nullableNumber(json, <String>[
        'previous_global_scouting_index',
        'previousGlobalScoutingIndex',
      ]),
      globalScoutingIndexMovementPct: _nullableNumber(json, <String>[
        'global_scouting_index_movement_pct',
        'globalScoutingIndexMovementPct',
      ]),
      transferListingId: GteJson.stringOrNull(json, <String>[
        'transfer_listing_id',
        'transferListingId',
      ]),
      transferListingStatus: GteJson.stringOrNull(json, <String>[
        'transfer_listing_status',
        'transferListingStatus',
      ]),
      sellingClubId: GteJson.stringOrNull(json, <String>[
        'selling_club_id',
        'sellingClubId',
      ]),
      isAvailable: GteJson.boolean(json, <String>[
        'is_available',
        'isAvailable',
      ], fallback: true),
      availabilityLabel: GteJson.string(json, <String>[
        'availability_label',
        'availabilityLabel',
      ], fallback: 'Available now'),
      askingType: GteJson.string(json, <String>[
        'asking_type',
        'askingType',
      ], fallback: 'transfer'),
      agentUserId: GteJson.string(json, <String>[
        'agent_user_id',
        'agentUserId',
      ], fallback: ''),
      agentName: GteJson.string(json, <String>[
        'agent_name',
        'agentName',
      ], fallback: 'Listed agent'),
      marketplaceNote: GteJson.stringOrNull(json, <String>[
        'marketplace_note',
        'marketplaceNote',
      ]),
      isTradable: GteJson.boolean(json, <String>[
        'is_tradable',
        'isTradable',
      ], fallback: true),
      salaryAmount: _nullableNumber(json, <String>[
        'salary_amount',
        'salaryAmount',
      ]),
      contractYearsRemaining: _nullableNumber(json, <String>[
        'contract_years_remaining',
        'contractYearsRemaining',
      ]),
      buyClauseAmount: _nullableNumber(json, <String>[
        'buy_clause_amount',
        'buyClauseAmount',
      ]),
      loanTerms: GteJson.map(
        json,
        keys: const <String>['loan_terms', 'loanTerms'],
      ),
      swapTerms: GteJson.map(
        json,
        keys: const <String>['swap_terms', 'swapTerms'],
      ),
      availabilityTerms: GteJson.map(
        json,
        keys: const <String>['availability', 'availabilityTerms'],
      ),
      imageUrl: GteJson.stringOrNull(json, <String>['image_url', 'imageUrl']),
      avatar: PlayerAvatar.fromJsonOrNull(
        GteJson.value(json, <String>['avatar']),
      ),
    );
  }
}

class GteMarketPlayerListView {
  const GteMarketPlayerListView({
    required this.items,
    required this.limit,
    required this.hasMore,
    this.nextCursor,
    required this.offset,
    required this.total,
  });

  final List<GteMarketPlayerListItem> items;
  final int limit;
  final bool hasMore;
  final String? nextCursor;
  final int offset;
  final int total;

  factory GteMarketPlayerListView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market players',
    );
    final List<GteMarketPlayerListItem> items = GteJson.typedList(
      json,
      <String>['players', 'items'],
      GteMarketPlayerListItem.fromJson,
    );
    final int offset = GteJson.integer(json, <String>['offset'], fallback: 0);
    final int total = GteJson.integer(json, <String>[
      'total',
    ], fallback: offset + items.length);
    return GteMarketPlayerListView(
      items: items,
      limit: GteJson.integer(json, <String>[
        'limit',
      ], fallback: items.isEmpty ? 20 : items.length),
      hasMore: GteJson.boolean(json, <String>[
        'has_more',
        'hasMore',
      ], fallback: offset + items.length < total),
      nextCursor: GteJson.stringOrNull(json, <String>[
        'next_cursor',
        'nextCursor',
      ]),
      offset: offset,
      total: total,
    );
  }
}

class GteMarketLeagueBrowseItem {
  const GteMarketLeagueBrowseItem({
    required this.leagueId,
    required this.slug,
    required this.displayName,
    required this.playerCount,
    required this.clubCount,
    this.country,
    this.countryCode,
    this.crestUrl,
  });

  final String leagueId;
  final String slug;
  final String displayName;
  final int playerCount;
  final int clubCount;
  final String? country;
  final String? countryCode;
  final String? crestUrl;

  factory GteMarketLeagueBrowseItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market league browse item',
    );
    return GteMarketLeagueBrowseItem(
      leagueId: GteJson.string(json, <String>['league_id', 'leagueId']),
      slug: GteJson.string(json, <String>['slug'], fallback: 'league'),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      playerCount: GteJson.integer(json, <String>[
        'player_count',
        'playerCount',
      ]),
      clubCount: GteJson.integer(json, <String>['club_count', 'clubCount']),
      country: GteJson.stringOrNull(json, <String>['country']),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      crestUrl: GteJson.stringOrNull(json, <String>['crest_url', 'crestUrl']),
    );
  }
}

class GteMarketClubBrowseItem {
  const GteMarketClubBrowseItem({
    required this.clubId,
    required this.slug,
    required this.displayName,
    required this.playerCount,
    this.shortName,
    this.country,
    this.countryCode,
    this.crestUrl,
  });

  final String clubId;
  final String slug;
  final String displayName;
  final int playerCount;
  final String? shortName;
  final String? country;
  final String? countryCode;
  final String? crestUrl;

  factory GteMarketClubBrowseItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market club browse item',
    );
    return GteMarketClubBrowseItem(
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      slug: GteJson.string(json, <String>['slug'], fallback: 'club'),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      playerCount: GteJson.integer(json, <String>[
        'player_count',
        'playerCount',
      ]),
      shortName: GteJson.stringOrNull(json, <String>[
        'short_name',
        'shortName',
      ]),
      country: GteJson.stringOrNull(json, <String>['country']),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      crestUrl: GteJson.stringOrNull(json, <String>['crest_url', 'crestUrl']),
    );
  }
}

class GteMarketNationalityBrowseItem {
  const GteMarketNationalityBrowseItem({
    required this.countryCode,
    required this.slug,
    required this.displayName,
    required this.eligiblePlayerCount,
    this.flagUrl,
  });

  final String countryCode;
  final String slug;
  final String displayName;
  final int eligiblePlayerCount;
  final String? flagUrl;

  factory GteMarketNationalityBrowseItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market nationality browse item',
    );
    return GteMarketNationalityBrowseItem(
      countryCode: GteJson.string(json, <String>[
        'country_code',
        'countryCode',
        'team_id',
        'teamId',
      ]),
      slug: GteJson.string(json, <String>['slug'], fallback: 'nationality'),
      displayName: GteJson.string(json, <String>[
        'display_name',
        'displayName',
      ]),
      eligiblePlayerCount: GteJson.integer(json, <String>[
        'eligible_player_count',
        'eligiblePlayerCount',
      ]),
      flagUrl: GteJson.stringOrNull(json, <String>['flag_url', 'flagUrl']),
    );
  }
}

class GteMarketBrowseOption {
  const GteMarketBrowseOption({
    required this.id,
    required this.label,
    required this.count,
    this.subtitle,
    this.parentId,
    this.countryId,
    this.leagueId,
    this.divisionId,
  });

  final String id;
  final String label;
  final int count;
  final String? subtitle;
  final String? parentId;
  final String? countryId;
  final String? leagueId;
  final String? divisionId;

  factory GteMarketBrowseOption.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market browse option',
    );
    return GteMarketBrowseOption(
      id: GteJson.string(json, <String>['id']),
      label: GteJson.string(json, <String>['label']),
      count: GteJson.integer(json, <String>['count'], fallback: 0),
      subtitle: GteJson.stringOrNull(json, <String>['subtitle']),
      parentId: GteJson.stringOrNull(json, <String>['parent_id', 'parentId']),
      countryId: GteJson.stringOrNull(json, <String>[
        'country_id',
        'countryId',
      ]),
      leagueId: GteJson.stringOrNull(json, <String>['league_id', 'leagueId']),
      divisionId: GteJson.stringOrNull(json, <String>[
        'division_id',
        'divisionId',
      ]),
    );
  }
}

class GteMarketBrowseCatalog {
  const GteMarketBrowseCatalog({
    required this.total,
    required this.countries,
    required this.leagues,
    required this.divisions,
    required this.clubs,
  });

  final int total;
  final List<GteMarketBrowseOption> countries;
  final List<GteMarketBrowseOption> leagues;
  final List<GteMarketBrowseOption> divisions;
  final List<GteMarketBrowseOption> clubs;

  factory GteMarketBrowseCatalog.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market browse catalog',
    );
    return GteMarketBrowseCatalog(
      total: GteJson.integer(json, <String>['total'], fallback: 0),
      countries: GteJson.typedList(json, <String>[
        'countries',
      ], GteMarketBrowseOption.fromJson),
      leagues: GteJson.typedList(json, <String>[
        'leagues',
      ], GteMarketBrowseOption.fromJson),
      divisions: GteJson.typedList(json, <String>[
        'divisions',
      ], GteMarketBrowseOption.fromJson),
      clubs: GteJson.typedList(json, <String>[
        'clubs',
      ], GteMarketBrowseOption.fromJson),
    );
  }
}

class GteMarketPlayerIdentity {
  const GteMarketPlayerIdentity({
    required this.playerName,
    required this.firstName,
    required this.lastName,
    required this.shortName,
    required this.position,
    required this.normalizedPosition,
    required this.nationality,
    required this.nationalityCode,
    required this.age,
    required this.dateOfBirth,
    required this.preferredFoot,
    required this.shirtNumber,
    required this.heightCm,
    required this.weightKg,
    required this.currentClubId,
    required this.currentClubName,
    required this.currentCompetitionId,
    required this.currentCompetitionName,
    required this.imageUrl,
    this.avatar,
  });

  final String playerName;
  final String? firstName;
  final String? lastName;
  final String? shortName;
  final String? position;
  final String? normalizedPosition;
  final String? nationality;
  final String? nationalityCode;
  final int age;
  final String? dateOfBirth;
  final String? preferredFoot;
  final int? shirtNumber;
  final int? heightCm;
  final int? weightKg;
  final String? currentClubId;
  final String? currentClubName;
  final String? currentCompetitionId;
  final String? currentCompetitionName;
  final String? imageUrl;
  final PlayerAvatar? avatar;

  factory GteMarketPlayerIdentity.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market player identity',
    );
    return GteMarketPlayerIdentity(
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      firstName: GteJson.stringOrNull(json, <String>[
        'first_name',
        'firstName',
      ]),
      lastName: GteJson.stringOrNull(json, <String>['last_name', 'lastName']),
      shortName: GteJson.stringOrNull(json, <String>[
        'short_name',
        'shortName',
      ]),
      position: GteJson.stringOrNull(json, <String>['position']),
      normalizedPosition: GteJson.stringOrNull(json, <String>[
        'normalized_position',
        'normalizedPosition',
      ]),
      nationality: GteJson.stringOrNull(json, <String>['nationality']),
      nationalityCode: GteJson.stringOrNull(json, <String>[
        'nationality_code',
        'nationalityCode',
      ]),
      age: GteJson.integer(json, <String>['age']),
      dateOfBirth: GteJson.stringOrNull(json, <String>[
        'date_of_birth',
        'dateOfBirth',
      ]),
      preferredFoot: GteJson.stringOrNull(json, <String>[
        'preferred_foot',
        'preferredFoot',
      ]),
      shirtNumber: _nullableInteger(json, <String>[
        'shirt_number',
        'shirtNumber',
      ]),
      heightCm: _nullableInteger(json, <String>['height_cm', 'heightCm']),
      weightKg: _nullableInteger(json, <String>['weight_kg', 'weightKg']),
      currentClubId: GteJson.stringOrNull(json, <String>[
        'current_club_id',
        'currentClubId',
      ]),
      currentClubName: GteJson.stringOrNull(json, <String>[
        'current_club_name',
        'currentClubName',
      ]),
      currentCompetitionId: GteJson.stringOrNull(json, <String>[
        'current_competition_id',
        'currentCompetitionId',
      ]),
      currentCompetitionName: GteJson.stringOrNull(json, <String>[
        'current_competition_name',
        'currentCompetitionName',
      ]),
      imageUrl: GteJson.stringOrNull(json, <String>['image_url', 'imageUrl']),
      avatar: PlayerAvatar.fromJsonOrNull(
        GteJson.value(json, <String>['avatar']),
      ),
    );
  }
}

class GteMarketPlayerMarketProfile {
  const GteMarketPlayerMarketProfile({
    required this.isTradable,
    required this.marketValueEur,
    required this.supplyTier,
    required this.liquidityBand,
    required this.holderCount,
    required this.topHolderSharePct,
    required this.top3HolderSharePct,
    required this.snapshotMarketPriceCredits,
    required this.quotedMarketPriceCredits,
    required this.trustedTradePriceCredits,
    required this.tradeTrustScore,
  });

  final bool isTradable;
  final double? marketValueEur;
  final String? supplyTier;
  final String? liquidityBand;
  final int? holderCount;
  final double? topHolderSharePct;
  final double? top3HolderSharePct;
  final double? snapshotMarketPriceCredits;
  final double? quotedMarketPriceCredits;
  final double? trustedTradePriceCredits;
  final double? tradeTrustScore;

  factory GteMarketPlayerMarketProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market profile',
    );
    return GteMarketPlayerMarketProfile(
      isTradable: GteJson.boolean(json, <String>['is_tradable', 'isTradable']),
      marketValueEur: _nullableNumber(json, <String>[
        'market_value_eur',
        'marketValueEur',
      ]),
      supplyTier: GteJson.stringOrNull(json, <String>[
        'supply_tier',
        'supplyTier',
      ]),
      liquidityBand: GteJson.stringOrNull(json, <String>[
        'liquidity_band',
        'liquidityBand',
      ]),
      holderCount: _nullableInteger(json, <String>[
        'holder_count',
        'holderCount',
      ]),
      topHolderSharePct: _nullableNumber(json, <String>[
        'top_holder_share_pct',
        'topHolderSharePct',
      ]),
      top3HolderSharePct: _nullableNumber(json, <String>[
        'top_3_holder_share_pct',
        'top3HolderSharePct',
      ]),
      snapshotMarketPriceCredits: _nullableNumber(json, <String>[
        'snapshot_market_price_credits',
        'snapshotMarketPriceCredits',
      ]),
      quotedMarketPriceCredits: _nullableNumber(json, <String>[
        'quoted_market_price_credits',
        'quotedMarketPriceCredits',
      ]),
      trustedTradePriceCredits: _nullableNumber(json, <String>[
        'trusted_trade_price_credits',
        'trustedTradePriceCredits',
      ]),
      tradeTrustScore: _nullableNumber(json, <String>[
        'trade_trust_score',
        'tradeTrustScore',
      ]),
    );
  }
}

class GteMarketPlayerValue {
  const GteMarketPlayerValue({
    required this.lastSnapshotId,
    required this.lastSnapshotAt,
    required this.currentValueCredits,
    required this.previousValueCredits,
    required this.movementPct,
    required this.footballTruthValueCredits,
    required this.marketSignalValueCredits,
    required this.publishedCardValueCredits,
    required this.scoutingSignalValueCredits,
    required this.egameSignalValueCredits,
    required this.confidenceScore,
    required this.confidenceTier,
    required this.trend7dPct,
    required this.trend30dPct,
    required this.trendDirection,
    required this.trendConfidence,
    required this.movementTags,
  });

  final String? lastSnapshotId;
  final DateTime? lastSnapshotAt;
  final double currentValueCredits;
  final double? previousValueCredits;
  final double movementPct;
  final double? footballTruthValueCredits;
  final double? marketSignalValueCredits;
  final double? publishedCardValueCredits;
  final double? scoutingSignalValueCredits;
  final double? egameSignalValueCredits;
  final double? confidenceScore;
  final String? confidenceTier;
  final double? trend7dPct;
  final double? trend30dPct;
  final String? trendDirection;
  final double? trendConfidence;
  final List<String> movementTags;

  factory GteMarketPlayerValue.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market player value',
    );
    return GteMarketPlayerValue(
      lastSnapshotId: GteJson.stringOrNull(json, <String>[
        'last_snapshot_id',
        'lastSnapshotId',
      ]),
      lastSnapshotAt: GteJson.dateTimeOrNull(json, <String>[
        'last_snapshot_at',
        'lastSnapshotAt',
      ]),
      currentValueCredits: GteJson.number(json, <String>[
        'current_value_credits',
        'currentValueCredits',
      ]),
      previousValueCredits: _nullableNumber(json, <String>[
        'previous_value_credits',
        'previousValueCredits',
      ]),
      movementPct: GteJson.number(json, <String>[
        'movement_pct',
        'movementPct',
      ]),
      footballTruthValueCredits: _nullableNumber(json, <String>[
        'football_truth_value_credits',
        'footballTruthValueCredits',
      ]),
      marketSignalValueCredits: _nullableNumber(json, <String>[
        'market_signal_value_credits',
        'marketSignalValueCredits',
      ]),
      publishedCardValueCredits: _nullableNumber(json, <String>[
        'published_card_value_credits',
        'publishedCardValueCredits',
      ]),
      scoutingSignalValueCredits: _nullableNumber(json, <String>[
        'scouting_signal_value_credits',
        'scoutingSignalValueCredits',
      ]),
      egameSignalValueCredits: _nullableNumber(json, <String>[
        'egame_signal_value_credits',
        'egameSignalValueCredits',
      ]),
      confidenceScore: _nullableNumber(json, <String>[
        'confidence_score',
        'confidenceScore',
      ]),
      confidenceTier: GteJson.stringOrNull(json, <String>[
        'confidence_tier',
        'confidenceTier',
      ]),
      trend7dPct: _nullableNumber(json, <String>['trend_7d_pct', 'trend7dPct']),
      trend30dPct: _nullableNumber(json, <String>[
        'trend_30d_pct',
        'trend30dPct',
      ]),
      trendDirection: GteJson.stringOrNull(json, <String>[
        'trend_direction',
        'trendDirection',
      ]),
      trendConfidence: _nullableNumber(json, <String>[
        'trend_confidence',
        'trendConfidence',
      ]),
      movementTags: GteJson.typedList(
        json,
        <String>['movement_tags', 'movementTags'],
        (Object? entry) => entry?.toString() ?? '',
      ).where((String entry) => entry.isNotEmpty).toList(growable: false),
    );
  }
}

class GteMarketPlayerTrend {
  const GteMarketPlayerTrend({
    required this.trendScore,
    required this.marketInterestScore,
    required this.averageRating,
    required this.globalScoutingIndex,
    required this.previousGlobalScoutingIndex,
    required this.globalScoutingIndexMovementPct,
    required this.drivers,
    required this.trend7dPct,
    required this.trend30dPct,
    required this.trendDirection,
    required this.trendConfidence,
    required this.confidenceTier,
    required this.movementTags,
  });

  final double trendScore;
  final int marketInterestScore;
  final double? averageRating;
  final double globalScoutingIndex;
  final double? previousGlobalScoutingIndex;
  final double? globalScoutingIndexMovementPct;
  final List<String> drivers;
  final double? trend7dPct;
  final double? trend30dPct;
  final String? trendDirection;
  final double? trendConfidence;
  final String? confidenceTier;
  final List<String> movementTags;

  factory GteMarketPlayerTrend.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market player trend',
    );
    return GteMarketPlayerTrend(
      trendScore: GteJson.number(json, <String>['trend_score', 'trendScore']),
      marketInterestScore: GteJson.integer(json, <String>[
        'market_interest_score',
        'marketInterestScore',
      ]),
      averageRating: _nullableNumber(json, <String>[
        'average_rating',
        'averageRating',
      ]),
      globalScoutingIndex: GteJson.number(json, <String>[
        'global_scouting_index',
        'globalScoutingIndex',
      ]),
      previousGlobalScoutingIndex: _nullableNumber(json, <String>[
        'previous_global_scouting_index',
        'previousGlobalScoutingIndex',
      ]),
      globalScoutingIndexMovementPct: _nullableNumber(json, <String>[
        'global_scouting_index_movement_pct',
        'globalScoutingIndexMovementPct',
      ]),
      drivers: GteJson.typedList(
        json,
        <String>['drivers'],
        (Object? entry) => entry?.toString() ?? '',
      ).where((String entry) => entry.isNotEmpty).toList(growable: false),
      trend7dPct: _nullableNumber(json, <String>['trend_7d_pct', 'trend7dPct']),
      trend30dPct: _nullableNumber(json, <String>[
        'trend_30d_pct',
        'trend30dPct',
      ]),
      trendDirection: GteJson.stringOrNull(json, <String>[
        'trend_direction',
        'trendDirection',
      ]),
      trendConfidence: _nullableNumber(json, <String>[
        'trend_confidence',
        'trendConfidence',
      ]),
      confidenceTier: GteJson.stringOrNull(json, <String>[
        'confidence_tier',
        'confidenceTier',
      ]),
      movementTags: GteJson.typedList(
        json,
        <String>['movement_tags', 'movementTags'],
        (Object? entry) => entry?.toString() ?? '',
      ).where((String entry) => entry.isNotEmpty).toList(growable: false),
    );
  }
}

class GteMarketPlayerDetailView {
  const GteMarketPlayerDetailView({
    required this.playerId,
    required this.identity,
    required this.marketProfile,
    required this.value,
    required this.trend,
  });

  final String playerId;
  final GteMarketPlayerIdentity identity;
  final GteMarketPlayerMarketProfile marketProfile;
  final GteMarketPlayerValue value;
  final GteMarketPlayerTrend trend;

  factory GteMarketPlayerDetailView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market player detail',
    );
    return GteMarketPlayerDetailView(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      identity: GteMarketPlayerIdentity.fromJson(
        GteJson.value(json, <String>['identity']) ?? const <String, Object?>{},
      ),
      marketProfile: GteMarketPlayerMarketProfile.fromJson(
        GteJson.value(json, <String>['market_profile', 'marketProfile']) ??
            const <String, Object?>{},
      ),
      value: GteMarketPlayerValue.fromJson(
        GteJson.value(json, <String>['value']) ?? const <String, Object?>{},
      ),
      trend: GteMarketPlayerTrend.fromJson(
        GteJson.value(json, <String>['trend']) ?? const <String, Object?>{},
      ),
    );
  }
}

class GteLifecycleBadgeView {
  const GteLifecycleBadgeView({
    required this.status,
    required this.label,
    required this.available,
    this.reason,
    this.until,
  });

  final String status;
  final String label;
  final bool available;
  final String? reason;
  final DateTime? until;

  factory GteLifecycleBadgeView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'lifecycle badge',
    );
    return GteLifecycleBadgeView(
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      label: GteJson.string(json, <String>['label'], fallback: 'Unknown'),
      available: GteJson.boolean(json, <String>['available'], fallback: false),
      reason: GteJson.stringOrNull(json, <String>['reason']),
      until: GteJson.dateTimeOrNull(json, <String>['until']),
    );
  }
}

class GteContractBadgeView {
  const GteContractBadgeView({
    required this.status,
    required this.label,
    this.clubName,
    this.endsOn,
  });

  final String status;
  final String label;
  final String? clubName;
  final DateTime? endsOn;

  factory GteContractBadgeView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'contract badge',
    );
    return GteContractBadgeView(
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      label: GteJson.string(json, <String>['label'], fallback: 'Unknown'),
      clubName: GteJson.stringOrNull(json, <String>['club_name', 'clubName']),
      endsOn: GteJson.dateTimeOrNull(json, <String>['ends_on', 'endsOn']),
    );
  }
}

class GteTransferStatusView {
  const GteTransferStatusView({
    required this.windowOpen,
    required this.eligible,
    this.reason,
    this.windowLabel,
    this.lastBidStatus,
  });

  final bool windowOpen;
  final bool eligible;
  final String? reason;
  final String? windowLabel;
  final String? lastBidStatus;

  factory GteTransferStatusView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'transfer status',
    );
    return GteTransferStatusView(
      windowOpen: GteJson.boolean(json, <String>['window_open', 'windowOpen']),
      eligible: GteJson.boolean(json, <String>['eligible']),
      reason: GteJson.stringOrNull(json, <String>['reason']),
      windowLabel: GteJson.stringOrNull(json, <String>[
        'window_label',
        'windowLabel',
      ]),
      lastBidStatus: GteJson.stringOrNull(json, <String>[
        'last_bid_status',
        'lastBidStatus',
      ]),
    );
  }
}

class GtePlayerAgencyPressureView {
  const GtePlayerAgencyPressureView({
    required this.currentState,
    required this.transferDesire,
    required this.activeTransferRequest,
    required this.refusesNewContract,
    required this.endOfContractPressure,
  });

  final String currentState;
  final double transferDesire;
  final bool activeTransferRequest;
  final bool refusesNewContract;
  final bool endOfContractPressure;

  factory GtePlayerAgencyPressureView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'agency pressure state',
    );
    return GtePlayerAgencyPressureView(
      currentState: GteJson.string(json, <String>[
        'current_state',
        'currentState',
      ]),
      transferDesire: GteJson.number(json, <String>[
        'transfer_desire',
        'transferDesire',
      ], fallback: 0),
      activeTransferRequest: GteJson.boolean(json, <String>[
        'active_transfer_request',
        'activeTransferRequest',
      ], fallback: false),
      refusesNewContract: GteJson.boolean(json, <String>[
        'refuses_new_contract',
        'refusesNewContract',
      ], fallback: false),
      endOfContractPressure: GteJson.boolean(json, <String>[
        'end_of_contract_pressure',
        'endOfContractPressure',
      ], fallback: false),
    );
  }
}

class GtePlayerAgencyTeamDynamicsView {
  const GtePlayerAgencyTeamDynamicsView({
    required this.active,
    required this.moralePenalty,
    required this.chemistryPenalty,
  });

  final bool active;
  final double moralePenalty;
  final double chemistryPenalty;

  factory GtePlayerAgencyTeamDynamicsView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'team dynamics',
    );
    return GtePlayerAgencyTeamDynamicsView(
      active: GteJson.boolean(json, <String>['active'], fallback: false),
      moralePenalty: GteJson.number(json, <String>[
        'morale_penalty',
        'moralePenalty',
      ], fallback: 0),
      chemistryPenalty: GteJson.number(json, <String>[
        'chemistry_penalty',
        'chemistryPenalty',
      ], fallback: 0),
    );
  }
}

class GtePlayerAgencySummary {
  const GtePlayerAgencySummary({
    required this.status,
    required this.lifecyclePhase,
    required this.transferListed,
    required this.freeAgent,
    required this.retirementPressure,
    this.agencyMessage,
    this.pressureState,
    this.teamDynamics,
  });

  final String status;
  final String lifecyclePhase;
  final bool transferListed;
  final bool freeAgent;
  final bool retirementPressure;
  final String? agencyMessage;
  final GtePlayerAgencyPressureView? pressureState;
  final GtePlayerAgencyTeamDynamicsView? teamDynamics;

  factory GtePlayerAgencySummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'player agency summary',
    );
    return GtePlayerAgencySummary(
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      lifecyclePhase: GteJson.string(json, <String>[
        'lifecycle_phase',
        'lifecyclePhase',
      ], fallback: 'unknown'),
      transferListed: GteJson.boolean(json, <String>[
        'transfer_listed',
        'transferListed',
      ], fallback: false),
      freeAgent: GteJson.boolean(json, <String>[
        'free_agent',
        'freeAgent',
      ], fallback: false),
      retirementPressure: GteJson.boolean(json, <String>[
        'retirement_pressure',
        'retirementPressure',
      ], fallback: false),
      agencyMessage: GteJson.stringOrNull(json, <String>[
        'agency_message',
        'agencyMessage',
      ]),
      pressureState:
          GteJson.value(json, <String>['pressure_state', 'pressureState']) ==
                  null
              ? null
              : GtePlayerAgencyPressureView.fromJson(
                GteJson.value(json, <String>[
                  'pressure_state',
                  'pressureState',
                ]),
              ),
      teamDynamics:
          GteJson.value(json, <String>['team_dynamics', 'teamDynamics']) == null
              ? null
              : GtePlayerAgencyTeamDynamicsView.fromJson(
                GteJson.value(json, <String>['team_dynamics', 'teamDynamics']),
              ),
    );
  }

  String get transferStanceLabel {
    if (freeAgent) {
      return 'Free agent';
    }
    if (pressureState?.activeTransferRequest == true || transferListed) {
      return 'Wants move';
    }
    if ((pressureState?.transferDesire ?? 0) >= 0.65) {
      return 'Open to move';
    }
    return 'Stable';
  }

  String get contractStanceLabel {
    if (freeAgent) {
      return 'Unsigned';
    }
    if (pressureState?.refusesNewContract == true) {
      return 'Holding out';
    }
    if (pressureState?.endOfContractPressure == true) {
      return 'Expiry pressure';
    }
    return 'Open to renew';
  }

  String? get moraleLabel {
    final GtePlayerAgencyTeamDynamicsView? dynamics = teamDynamics;
    if (dynamics == null) {
      return null;
    }
    if (!dynamics.active) {
      return 'Stable';
    }
    if (dynamics.moralePenalty >= 0.5 || dynamics.chemistryPenalty >= 0.5) {
      return 'Under strain';
    }
    return 'Monitor';
  }

  String? get reasonSnippet {
    final String? trimmed = agencyMessage?.trim();
    if (trimmed == null || trimmed.isEmpty) {
      return null;
    }
    return trimmed;
  }
}

class GteLifecycleEventItem {
  const GteLifecycleEventItem({
    required this.eventType,
    required this.summary,
    this.occurredOn,
  });

  final String eventType;
  final String summary;
  final DateTime? occurredOn;

  factory GteLifecycleEventItem.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'lifecycle event',
    );
    return GteLifecycleEventItem(
      eventType: GteJson.string(json, <String>['event_type', 'eventType']),
      summary: GteJson.string(json, <String>[
        'summary',
      ], fallback: 'Lifecycle event'),
      occurredOn: GteJson.dateTimeOrNull(json, <String>[
        'occurred_on',
        'occurredOn',
      ]),
    );
  }
}

class GtePlayerLifecycleSnapshot {
  const GtePlayerLifecycleSnapshot({
    required this.playerId,
    required this.playerName,
    required this.availabilityBadge,
    required this.transferStatus,
    required this.recentEvents,
    this.contractBadge,
    this.agencySummary,
  });

  final String playerId;
  final String playerName;
  final GteLifecycleBadgeView availabilityBadge;
  final GteTransferStatusView transferStatus;
  final List<GteLifecycleEventItem> recentEvents;
  final GteContractBadgeView? contractBadge;
  final GtePlayerAgencySummary? agencySummary;

  factory GtePlayerLifecycleSnapshot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'player lifecycle snapshot',
    );
    return GtePlayerLifecycleSnapshot(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      availabilityBadge: GteLifecycleBadgeView.fromJson(
        GteJson.value(json, <String>[
              'availability_badge',
              'availabilityBadge',
            ]) ??
            const <String, Object?>{},
      ),
      transferStatus: GteTransferStatusView.fromJson(
        GteJson.value(json, <String>['transfer_status', 'transferStatus']) ??
            const <String, Object?>{},
      ),
      contractBadge:
          GteJson.value(json, <String>['contract_badge', 'contractBadge']) ==
                  null
              ? null
              : GteContractBadgeView.fromJson(
                GteJson.value(json, <String>[
                  'contract_badge',
                  'contractBadge',
                ]),
              ),
      agencySummary: _agencySummaryFromJson(json),
      recentEvents: GteJson.typedList(json, <String>[
        'recent_events',
        'recentEvents',
      ], GteLifecycleEventItem.fromJson),
    );
  }

  factory GtePlayerLifecycleSnapshot.fromOverview(GtePlayerOverview overview) {
    return GtePlayerLifecycleSnapshot(
      playerId: overview.playerId,
      playerName: overview.playerName,
      availabilityBadge: overview.availabilityBadge,
      transferStatus: overview.transferStatus,
      recentEvents: overview.recentEvents,
      contractBadge: overview.contractBadge,
      agencySummary: overview.agencySummary,
    );
  }
}

class GteCareerTotals {
  const GteCareerTotals({
    required this.appearances,
    required this.starts,
    required this.goals,
    required this.assists,
    required this.cleanSheets,
    required this.saves,
    required this.minutes,
  });

  final int appearances;
  final int starts;
  final int goals;
  final int assists;
  final int cleanSheets;
  final int saves;
  final int minutes;

  factory GteCareerTotals.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'career totals',
    );
    return GteCareerTotals(
      appearances: GteJson.integer(json, <String>['appearances']),
      starts: GteJson.integer(json, <String>['starts'], fallback: 0),
      goals: GteJson.integer(json, <String>['goals']),
      assists: GteJson.integer(json, <String>['assists']),
      cleanSheets: GteJson.integer(json, <String>[
        'clean_sheets',
        'cleanSheets',
      ], fallback: 0),
      saves: GteJson.integer(json, <String>['saves'], fallback: 0),
      minutes: GteJson.integer(json, <String>['minutes']),
    );
  }
}

class GteSeasonProgression {
  const GteSeasonProgression({
    required this.seasonLabel,
    required this.competitionId,
    required this.competitionName,
    required this.clubId,
    required this.clubName,
    required this.appearances,
    required this.starts,
    required this.goals,
    required this.assists,
    required this.cleanSheets,
    required this.saves,
    required this.minutes,
    required this.averageRating,
  });

  final String seasonLabel;
  final String? competitionId;
  final String? competitionName;
  final String? clubId;
  final String? clubName;
  final int appearances;
  final int starts;
  final int goals;
  final int assists;
  final int cleanSheets;
  final int saves;
  final int minutes;
  final double? averageRating;

  factory GteSeasonProgression.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'season progression',
    );
    return GteSeasonProgression(
      seasonLabel: GteJson.string(json, <String>[
        'season_label',
        'seasonLabel',
      ]),
      competitionId: GteJson.stringOrNull(json, <String>[
        'competition_id',
        'competitionId',
      ]),
      competitionName: GteJson.stringOrNull(json, <String>[
        'competition_name',
        'competitionName',
      ]),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      clubName: GteJson.stringOrNull(json, <String>['club_name', 'clubName']),
      appearances: GteJson.integer(json, <String>['appearances']),
      starts: GteJson.integer(json, <String>['starts'], fallback: 0),
      goals: GteJson.integer(json, <String>['goals']),
      assists: GteJson.integer(json, <String>['assists']),
      cleanSheets: GteJson.integer(json, <String>[
        'clean_sheets',
        'cleanSheets',
      ], fallback: 0),
      saves: GteJson.integer(json, <String>['saves'], fallback: 0),
      minutes: GteJson.integer(json, <String>['minutes']),
      averageRating: _nullableNumber(json, <String>[
        'average_rating',
        'averageRating',
      ]),
    );
  }
}

class GtePlayerCareerSummary {
  const GtePlayerCareerSummary({
    required this.playerId,
    required this.playerName,
    required this.currentClubId,
    required this.currentClubName,
    required this.currentCompetitionId,
    required this.currentCompetitionName,
    required this.totals,
    required this.seasonalProgression,
  });

  final String playerId;
  final String playerName;
  final String? currentClubId;
  final String? currentClubName;
  final String? currentCompetitionId;
  final String? currentCompetitionName;
  final GteCareerTotals totals;
  final List<GteSeasonProgression> seasonalProgression;

  factory GtePlayerCareerSummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'player career summary',
    );
    return GtePlayerCareerSummary(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      currentClubId: GteJson.stringOrNull(json, <String>[
        'current_club_id',
        'currentClubId',
      ]),
      currentClubName: GteJson.stringOrNull(json, <String>[
        'current_club_name',
        'currentClubName',
      ]),
      currentCompetitionId: GteJson.stringOrNull(json, <String>[
        'current_competition_id',
        'currentCompetitionId',
      ]),
      currentCompetitionName: GteJson.stringOrNull(json, <String>[
        'current_competition_name',
        'currentCompetitionName',
      ]),
      totals: GteCareerTotals.fromJson(
        GteJson.value(json, <String>['totals']) ?? const <String, Object?>{},
      ),
      seasonalProgression: GteJson.typedList(json, <String>[
        'seasonal_progression',
        'seasonalProgression',
      ], GteSeasonProgression.fromJson),
    );
  }
}

class GteCareerEntry {
  const GteCareerEntry({
    required this.id,
    required this.playerId,
    required this.clubId,
    required this.clubName,
    required this.seasonLabel,
    required this.squadRole,
    required this.appearances,
    required this.goals,
    required this.assists,
    required this.averageRating,
    required this.notes,
    required this.startOn,
    required this.endOn,
    required this.updatedAt,
  });

  final String id;
  final String playerId;
  final String? clubId;
  final String clubName;
  final String seasonLabel;
  final String? squadRole;
  final int appearances;
  final int goals;
  final int assists;
  final int? averageRating;
  final String? notes;
  final DateTime? startOn;
  final DateTime? endOn;
  final DateTime updatedAt;

  DateTime get timelineAnchor => endOn ?? startOn ?? updatedAt;

  factory GteCareerEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'career entry');
    return GteCareerEntry(
      id: GteJson.string(json, <String>['id']),
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      clubName: GteJson.string(json, <String>['club_name', 'clubName']),
      seasonLabel: GteJson.string(json, <String>[
        'season_label',
        'seasonLabel',
      ]),
      squadRole: GteJson.stringOrNull(json, <String>[
        'squad_role',
        'squadRole',
      ]),
      appearances: GteJson.integer(json, <String>['appearances']),
      goals: GteJson.integer(json, <String>['goals']),
      assists: GteJson.integer(json, <String>['assists']),
      averageRating: _nullableInteger(json, <String>[
        'average_rating',
        'averageRating',
      ]),
      notes: GteJson.stringOrNull(json, <String>['notes']),
      startOn: GteJson.dateTimeOrNull(json, <String>['start_on', 'startOn']),
      endOn: GteJson.dateTimeOrNull(json, <String>['end_on', 'endOn']),
      updatedAt:
          GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    );
  }
}

class GtePlayerOverview {
  const GtePlayerOverview({
    required this.playerId,
    required this.playerName,
    required this.position,
    required this.marketValueEur,
    required this.overviewGeneratedOn,
    required this.careerSummary,
    required this.availabilityBadge,
    required this.contractBadge,
    required this.transferStatus,
    required this.agencySummary,
    required this.recentEvents,
  });

  final String playerId;
  final String playerName;
  final String? position;
  final double? marketValueEur;
  final DateTime overviewGeneratedOn;
  final GtePlayerCareerSummary careerSummary;
  final GteLifecycleBadgeView availabilityBadge;
  final GteContractBadgeView? contractBadge;
  final GteTransferStatusView transferStatus;
  final GtePlayerAgencySummary? agencySummary;
  final List<GteLifecycleEventItem> recentEvents;

  factory GtePlayerOverview.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'player overview',
    );
    return GtePlayerOverview(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      position: GteJson.stringOrNull(json, <String>['position']),
      marketValueEur: _nullableNumber(json, <String>[
        'market_value_eur',
        'marketValueEur',
      ]),
      overviewGeneratedOn:
          GteJson.dateTimeOrNull(json, <String>[
            'overview_generated_on',
            'overviewGeneratedOn',
          ]) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      careerSummary: GtePlayerCareerSummary.fromJson(
        GteJson.value(json, <String>['career_summary', 'careerSummary']) ??
            const <String, Object?>{},
      ),
      availabilityBadge: GteLifecycleBadgeView.fromJson(
        GteJson.value(json, <String>[
              'availability_badge',
              'availabilityBadge',
            ]) ??
            const <String, Object?>{},
      ),
      contractBadge:
          GteJson.value(json, <String>['contract_badge', 'contractBadge']) ==
                  null
              ? null
              : GteContractBadgeView.fromJson(
                GteJson.value(json, <String>[
                  'contract_badge',
                  'contractBadge',
                ]),
              ),
      transferStatus: GteTransferStatusView.fromJson(
        GteJson.value(json, <String>['transfer_status', 'transferStatus']) ??
            const <String, Object?>{},
      ),
      agencySummary: _agencySummaryFromJson(json),
      recentEvents: GteJson.typedList(json, <String>[
        'recent_events',
        'recentEvents',
      ], GteLifecycleEventItem.fromJson),
    );
  }
}

class GtePlayerMarketSnapshot {
  const GtePlayerMarketSnapshot({
    required this.detail,
    required this.ticker,
    required this.candles,
    required this.orderBook,
    required this.careerEntries,
    this.overview,
    this.lifecycle,
  });

  final GteMarketPlayerDetailView detail;
  final GteMarketTicker ticker;
  final GteMarketCandles candles;
  final GteOrderBook orderBook;
  final GtePlayerOverview? overview;
  final List<GteCareerEntry> careerEntries;
  final GtePlayerLifecycleSnapshot? lifecycle;

  GtePlayerMarketSnapshot copyWith({
    GteMarketPlayerDetailView? detail,
    GteMarketTicker? ticker,
    GteMarketCandles? candles,
    GteOrderBook? orderBook,
    GtePlayerOverview? overview,
    List<GteCareerEntry>? careerEntries,
    GtePlayerLifecycleSnapshot? lifecycle,
  }) {
    return GtePlayerMarketSnapshot(
      detail: detail ?? this.detail,
      ticker: ticker ?? this.ticker,
      candles: candles ?? this.candles,
      orderBook: orderBook ?? this.orderBook,
      overview: overview ?? this.overview,
      careerEntries: careerEntries ?? this.careerEntries,
      lifecycle: lifecycle ?? this.lifecycle,
    );
  }
}

double? _nullableNumber(Map<String, Object?> json, List<String> keys) {
  if (GteJson.value(json, keys) == null) {
    return null;
  }
  return GteJson.number(json, keys);
}

int? _nullableInteger(Map<String, Object?> json, List<String> keys) {
  if (GteJson.value(json, keys) == null) {
    return null;
  }
  return GteJson.integer(json, keys);
}

GtePlayerAgencySummary? _agencySummaryFromJson(Map<String, Object?> json) {
  final Object? rawValue = GteJson.value(json, <String>[
    'agency_summary',
    'agencySummary',
    'regen_summary',
    'regenSummary',
  ]);
  if (rawValue == null) {
    return null;
  }
  return GtePlayerAgencySummary.fromJson(rawValue);
}

String? _trimOrNull(String? value) {
  if (value == null) {
    return null;
  }
  final String trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

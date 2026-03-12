enum DynastyStatus {
  none,
  active,
  fallen,
}

DynastyStatus dynastyStatusFromRaw(Object? rawValue) {
  switch (_normalize(rawValue)) {
    case 'active':
      return DynastyStatus.active;
    case 'fallen':
      return DynastyStatus.fallen;
    case 'none':
    default:
      return DynastyStatus.none;
  }
}

extension DynastyStatusX on DynastyStatus {
  String get label {
    switch (this) {
      case DynastyStatus.active:
        return 'Active Dynasty';
      case DynastyStatus.fallen:
        return 'Historic Giant';
      case DynastyStatus.none:
        return 'No Dynasty';
    }
  }
}

enum DynastyEraType {
  none,
  emergingPower,
  dominantEra,
  continentalDynasty,
  globalDynasty,
  fallenGiant,
}

DynastyEraType dynastyEraTypeFromRaw(Object? rawValue) {
  switch (_normalize(rawValue)) {
    case 'emergingpower':
      return DynastyEraType.emergingPower;
    case 'dominantera':
      return DynastyEraType.dominantEra;
    case 'continentaldynasty':
      return DynastyEraType.continentalDynasty;
    case 'globaldynasty':
      return DynastyEraType.globalDynasty;
    case 'fallengiant':
      return DynastyEraType.fallenGiant;
    case 'noactivedynasty':
    case 'none':
    default:
      return DynastyEraType.none;
  }
}

extension DynastyEraTypeX on DynastyEraType {
  String get label {
    switch (this) {
      case DynastyEraType.emergingPower:
        return 'Emerging Power';
      case DynastyEraType.dominantEra:
        return 'Dominant Era';
      case DynastyEraType.continentalDynasty:
        return 'Continental Dynasty';
      case DynastyEraType.globalDynasty:
        return 'Global Dynasty';
      case DynastyEraType.fallenGiant:
        return 'Fallen Giant';
      case DynastyEraType.none:
        return 'No Active Dynasty';
    }
  }

  String get strapline {
    switch (this) {
      case DynastyEraType.emergingPower:
        return 'The badge is rising and the league is starting to notice.';
      case DynastyEraType.dominantEra:
        return 'Domestic control has turned from a good spell into a standard.';
      case DynastyEraType.continentalDynasty:
        return 'The club owns big European nights and backs it up every spring.';
      case DynastyEraType.globalDynasty:
        return 'This is football royalty. The world stage expects them to arrive.';
      case DynastyEraType.fallenGiant:
        return 'The history still carries weight, even if the present has cooled.';
      case DynastyEraType.none:
        return 'The club is still writing the chapter that could become an era.';
    }
  }

  bool get isDynasty =>
      this == DynastyEraType.dominantEra ||
      this == DynastyEraType.continentalDynasty ||
      this == DynastyEraType.globalDynasty;

  bool get isRising => this == DynastyEraType.emergingPower;
}

enum DynastyLeaderboardFilter {
  activeDynasties,
  allTimeDynasties,
  risingPowers,
}

extension DynastyLeaderboardFilterX on DynastyLeaderboardFilter {
  String get label {
    switch (this) {
      case DynastyLeaderboardFilter.activeDynasties:
        return 'Active dynasties';
      case DynastyLeaderboardFilter.allTimeDynasties:
        return 'All-time dynasties';
      case DynastyLeaderboardFilter.risingPowers:
        return 'Rising powers';
    }
  }

  String get emptyTitle {
    switch (this) {
      case DynastyLeaderboardFilter.activeDynasties:
        return 'No active dynasties';
      case DynastyLeaderboardFilter.allTimeDynasties:
        return 'No dynasty records';
      case DynastyLeaderboardFilter.risingPowers:
        return 'No rising powers yet';
    }
  }

  String get emptyMessage {
    switch (this) {
      case DynastyLeaderboardFilter.activeDynasties:
        return 'No club currently meets the active dynasty bar in this feed.';
      case DynastyLeaderboardFilter.allTimeDynasties:
        return 'Dynasty history has not been published for this competition view.';
      case DynastyLeaderboardFilter.risingPowers:
        return 'No clubs are close enough to a breakthrough to feature here yet.';
    }
  }
}

String _normalize(Object? rawValue) {
  return rawValue
      .toString()
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '');
}

enum GtexAudioContext {
  home,
  club,
  market,
  competition,
  matchday,
  world,
  celebration;

  String get label {
    switch (this) {
      case GtexAudioContext.home:
        return 'Home';
      case GtexAudioContext.club:
        return 'Club';
      case GtexAudioContext.market:
        return 'Market';
      case GtexAudioContext.competition:
        return 'Competition';
      case GtexAudioContext.matchday:
        return 'Matchday';
      case GtexAudioContext.world:
        return 'World';
      case GtexAudioContext.celebration:
        return 'Celebration';
    }
  }

  String get description {
    switch (this) {
      case GtexAudioContext.home:
        return 'Atmospheric GTEX OS theme';
      case GtexAudioContext.club:
        return 'Tactical HQ ambient synth';
      case GtexAudioContext.market:
        return 'Trading floor rhythm & dynamics';
      case GtexAudioContext.competition:
        return 'Arena hype & championship pulse';
      case GtexAudioContext.matchday:
        return 'Stadium crowd & match broadcast stems';
      case GtexAudioContext.world:
        return 'Global scouting pulse & regens';
      case GtexAudioContext.celebration:
        return 'Triumphant celebration fanfare';
    }
  }
}

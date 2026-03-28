import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/live_match.dart';

final Provider<List<LiveMatch>> matchProvider = Provider<List<LiveMatch>>(
  (Ref ref) => const <LiveMatch>[
    LiveMatch(
      id: 'atlas-v-phoenix',
      homeClub: 'Lagos Atlas',
      awayClub: 'Nairobi Phoenix',
      homeStarPlayer: 'Tunde Bamidele',
      awayStarPlayer: 'Amani Odede',
      homeScore: 2,
      awayScore: 1,
      minute: 67,
      headline: 'Atlas pin Phoenix deep after a rapid touchline switch.',
      venue: 'Atlas Dome',
      crowd: 58420,
      momentum: 0.72,
    ),
    LiveMatch(
      id: 'cairo-v-kigali',
      homeClub: 'Cairo Kings',
      awayClub: 'Kigali Wave',
      homeStarPlayer: 'Youssef Nabil',
      awayStarPlayer: 'Prince Tuyisenge',
      homeScore: 0,
      awayScore: 0,
      minute: 41,
      headline: 'Kigali keep the line compact and deny the half-spaces.',
      venue: 'Nile Arena',
      crowd: 47210,
      momentum: 0.47,
    ),
    LiveMatch(
      id: 'accra-v-casablanca',
      homeClub: 'Accra Republic',
      awayClub: 'Casablanca Stars',
      homeStarPlayer: 'Kojo Mensah',
      awayStarPlayer: 'Ilyas Ziani',
      homeScore: 3,
      awayScore: 2,
      minute: 83,
      headline: 'The tempo spikes again as Casablanca chase a late equalizer.',
      venue: 'Republic Grounds',
      crowd: 61230,
      momentum: 0.55,
    ),
  ],
);

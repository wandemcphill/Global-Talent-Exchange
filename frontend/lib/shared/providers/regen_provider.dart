import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/competition.dart';
import '../models/federation.dart';
import '../models/player.dart';

final Provider<List<Player>> regenProvider = Provider<List<Player>>(
  (Ref ref) => const <Player>[
    Player(
      id: 'regen-kamara',
      name: 'Ibrahim Kamara',
      position: 'RW',
      country: 'Sierra Leone',
      age: 17,
      rating: 76,
      potential: 92,
      valueInMillions: 9.8,
      pace: 0.91,
      technique: 0.84,
      mentality: 0.73,
      image: 'assets/branding/gtex_icon.png',
      isHot: true,
    ),
    Player(
      id: 'regen-adebayo',
      name: 'Tomi Adebayo',
      position: 'CM',
      country: 'Nigeria',
      age: 18,
      rating: 79,
      potential: 90,
      valueInMillions: 12.6,
      pace: 0.74,
      technique: 0.88,
      mentality: 0.81,
      image: 'assets/branding/gtex_icon.png',
    ),
    Player(
      id: 'regen-mensah',
      name: 'Kojo Mensah',
      position: 'CB',
      country: 'Ghana',
      age: 18,
      rating: 78,
      potential: 89,
      valueInMillions: 11.1,
      pace: 0.68,
      technique: 0.71,
      mentality: 0.87,
      image: 'assets/branding/gtex_icon.png',
      isHot: true,
    ),
    Player(
      id: 'regen-toure',
      name: 'Yaya Toure Jr',
      position: 'ST',
      country: 'Ivory Coast',
      age: 17,
      rating: 75,
      potential: 91,
      valueInMillions: 10.4,
      pace: 0.83,
      technique: 0.79,
      mentality: 0.78,
      image: 'assets/branding/gtex_icon.png',
    ),
  ],
);

final Provider<List<Competition>> competitionsProvider =
    Provider<List<Competition>>(
  (Ref ref) => const <Competition>[
    Competition(
      name: 'GTEX World Cup',
      region: 'Global',
      stage: 'Quarter Finals',
      nextFixture: 'Lagos Atlas vs Rio Norte',
      spotlight: 'Cinematic broadcast package unlocked',
    ),
    Competition(
      name: 'Continental Challenger',
      region: 'Africa',
      stage: 'Group Stage',
      nextFixture: 'Nairobi Phoenix vs Dakar Port',
      spotlight: 'Top 8 regens are being tracked live',
    ),
    Competition(
      name: 'U-19 Future Stars',
      region: 'Global',
      stage: 'Semi Finals',
      nextFixture: 'Abuja Pulse vs Tokyo Sora',
      spotlight: 'Scouts predict a record transfer window',
    ),
  ],
);

final Provider<List<String>> historyProvider = Provider<List<String>>(
  (Ref ref) => const <String>[
    '2025: Lagos Atlas completed the first academy-led treble.',
    '2024: The federation expanded cross-continent loan windows.',
    '2023: GTEX launched live regen forecasting and dynamic scouting scores.',
  ],
);

final Provider<List<Federation>> federationsProvider =
    Provider<List<Federation>>(
  (Ref ref) => const <Federation>[
    Federation(
      name: 'West Africa Football Board',
      region: 'West Africa',
      ranking: 1,
      focus: 'Youth pathways and transfer transparency',
      memberClubs: 18,
    ),
    Federation(
      name: 'East Africa Pro Council',
      region: 'East Africa',
      ranking: 2,
      focus: 'Broadcast quality and matchday analytics',
      memberClubs: 14,
    ),
    Federation(
      name: 'Mediterranean Elite Union',
      region: 'North Africa',
      ranking: 3,
      focus: 'Elite competition depth and academy exports',
      memberClubs: 16,
    ),
  ],
);

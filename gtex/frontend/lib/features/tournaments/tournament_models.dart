import '../../shared/models/competition.dart';
import '../../shared/models/player.dart';

enum TournamentFixtureStatus { scheduled, live, complete }

class TournamentFixture {
  const TournamentFixture({
    required this.roundLabel,
    required this.homeClub,
    required this.awayClub,
    required this.kickoffLabel,
    required this.venue,
    required this.status,
    this.homeScore,
    this.awayScore,
  });

  final String roundLabel;
  final String homeClub;
  final String awayClub;
  final String kickoffLabel;
  final String venue;
  final TournamentFixtureStatus status;
  final int? homeScore;
  final int? awayScore;
}

class TournamentStanding {
  const TournamentStanding({
    required this.club,
    required this.played,
    required this.won,
    required this.drawn,
    required this.lost,
    required this.goalDifference,
    required this.points,
  });

  final String club;
  final int played;
  final int won;
  final int drawn;
  final int lost;
  final int goalDifference;
  final int points;
}

List<TournamentFixture> buildTournamentFixtures(Competition competition) {
  return <TournamentFixture>[
    TournamentFixture(
      roundLabel: 'Opening Night',
      homeClub: 'Lagos Atlas FC',
      awayClub: 'Rio Norte',
      kickoffLabel: '19:30 WAT',
      venue: 'Atlas Dome',
      status: TournamentFixtureStatus.live,
      homeScore: 2,
      awayScore: 1,
    ),
    TournamentFixture(
      roundLabel: 'Feature Clash',
      homeClub: 'Abuja Pulse',
      awayClub: 'Tokyo Sora',
      kickoffLabel: '21:00 WAT',
      venue: 'Neo Arena',
      status: TournamentFixtureStatus.scheduled,
    ),
    TournamentFixture(
      roundLabel: 'Group B',
      homeClub: 'Nairobi Phoenix',
      awayClub: 'Dakar Port',
      kickoffLabel: 'Tomorrow • 18:00',
      venue: 'Harbor Lights Stadium',
      status: TournamentFixtureStatus.scheduled,
    ),
    TournamentFixture(
      roundLabel: competition.stage,
      homeClub: 'Coastal Union',
      awayClub: 'Metro Sporting',
      kickoffLabel: 'Completed',
      venue: 'Union Ground',
      status: TournamentFixtureStatus.complete,
      homeScore: 0,
      awayScore: 0,
    ),
  ];
}

List<TournamentStanding> buildTournamentStandings(Competition competition) {
  return const <TournamentStanding>[
    TournamentStanding(
      club: 'Lagos Atlas FC',
      played: 3,
      won: 2,
      drawn: 1,
      lost: 0,
      goalDifference: 4,
      points: 7,
    ),
    TournamentStanding(
      club: 'Tokyo Sora',
      played: 3,
      won: 2,
      drawn: 0,
      lost: 1,
      goalDifference: 3,
      points: 6,
    ),
    TournamentStanding(
      club: 'Abuja Pulse',
      played: 3,
      won: 1,
      drawn: 2,
      lost: 0,
      goalDifference: 2,
      points: 5,
    ),
    TournamentStanding(
      club: 'Rio Norte',
      played: 3,
      won: 1,
      drawn: 1,
      lost: 1,
      goalDifference: 0,
      points: 4,
    ),
    TournamentStanding(
      club: 'Dakar Port',
      played: 3,
      won: 1,
      drawn: 0,
      lost: 2,
      goalDifference: -2,
      points: 3,
    ),
    TournamentStanding(
      club: 'Nairobi Phoenix',
      played: 3,
      won: 0,
      drawn: 0,
      lost: 3,
      goalDifference: -7,
      points: 0,
    ),
  ];
}

List<Player> buildTournamentSquad(List<Player> prospects) {
  const String asset = 'assets/branding/gtex_icon.png';
  final List<Player> generated = <Player>[
    const Player(
      id: 'tournament-gk',
      name: 'Ifeanyi Bassey',
      position: 'GK',
      country: 'Nigeria',
      age: 27,
      rating: 84,
      potential: 86,
      valueInMillions: 26,
      pace: 0.58,
      technique: 0.68,
      mentality: 0.9,
      image: asset,
    ),
    const Player(
      id: 'tournament-cb1',
      name: 'Moussa Diallo',
      position: 'CB',
      country: 'Senegal',
      age: 25,
      rating: 84,
      potential: 87,
      valueInMillions: 28,
      pace: 0.75,
      technique: 0.73,
      mentality: 0.87,
      image: asset,
    ),
    const Player(
      id: 'tournament-cm1',
      name: 'Samuel Onana',
      position: 'CAM',
      country: 'Cameroon',
      age: 23,
      rating: 85,
      potential: 88,
      valueInMillions: 34,
      pace: 0.81,
      technique: 0.89,
      mentality: 0.78,
      image: asset,
      isHot: true,
    ),
    const Player(
      id: 'tournament-st1',
      name: 'Daniel Okoro',
      position: 'ST',
      country: 'Nigeria',
      age: 20,
      rating: 86,
      potential: 91,
      valueInMillions: 39,
      pace: 0.89,
      technique: 0.84,
      mentality: 0.8,
      image: asset,
      isHot: true,
    ),
  ];

  return <Player>[...generated, ...prospects.take(5)];
}

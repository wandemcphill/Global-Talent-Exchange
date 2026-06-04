import 'dart:math';

import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';

export 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';

class LiveMatchTestFixtures {
  const LiveMatchTestFixtures._();

  static LiveMatchSnapshot buildSnapshot(CompetitionSummary competition) {
    final int seed = competition.id.hashCode.abs();
    final Random rng = Random(seed);
    final List<String> teams = List<String>.from(_teamNames, growable: false);
    teams.shuffle(rng);
    final String homeTeam = teams.first;
    final String awayTeam = teams.length > 1 ? teams[1] : 'GTEX Select';

    final LiveMatchPhase phase = _phaseForCompetition(competition);
    final int minute = _minuteForPhase(rng, phase);
    final int homeScore = _scoreForSide(rng, phase, isHome: true);
    final int awayScore = _scoreForSide(rng, phase, isHome: false);

    final List<LiveMatchEvent> commentary = _buildCommentary(
      homeTeam: homeTeam,
      awayTeam: awayTeam,
      minute: minute,
    );
    final List<LiveMatchEvent> substitutions = commentary
        .where(
          (LiveMatchEvent event) =>
              event.type == LiveMatchEventType.substitution,
        )
        .toList(growable: false);
    final List<LiveMatchEvent> cards = commentary
        .where((LiveMatchEvent event) => event.type == LiveMatchEventType.card)
        .toList(growable: false);
    final List<LiveMatchHighlightClip> keyMoments = _buildKeyMoments(
      competition,
      commentary
          .where((LiveMatchEvent event) => event.isKeyMoment)
          .toList(growable: false),
    );

    final DateTime now = DateTime.now().toUtc();
    final DateTime standardExpiry = now.add(const Duration(minutes: 10));
    final DateTime premiumExpiry = now.add(const Duration(hours: 3));
    final List<LiveMatchHighlightClip> highlights = _buildHighlights(
      competition,
      commentary,
      standardExpiry,
      premiumExpiry,
    );

    return LiveMatchSnapshot(
      matchId: competition.id,
      halftimeAnalyticsAvailable: false,
      highlightsAvailable: highlights.isNotEmpty,
      keyMomentsAvailable: keyMoments.isNotEmpty,
      homeTeam: homeTeam,
      awayTeam: awayTeam,
      homeScore: homeScore,
      awayScore: awayScore,
      minute: minute,
      phase: phase,
      momentum: List<int>.generate(12, (int index) => rng.nextInt(7) - 3),
      commentary: commentary,
      homeLineup: _buildLineup(rng, homeTeam, captainSeed: seed),
      awayLineup: _buildLineup(rng, awayTeam, captainSeed: seed + 8),
      substitutions: substitutions,
      cards: cards,
      tacticalSuggestions: _buildSuggestions(rng),
      keyMoments: keyMoments,
      highlights: highlights,
      standardHighlightExpiresAt: standardExpiry,
      premiumHighlightExpiresAt: premiumExpiry,
    );
  }

  static LiveMatchPhase _phaseForCompetition(CompetitionSummary competition) {
    switch (competition.status) {
      case CompetitionStatus.inProgress:
        return LiveMatchPhase.firstHalf;
      case CompetitionStatus.completed:
        return LiveMatchPhase.fullTime;
      case CompetitionStatus.locked:
      case CompetitionStatus.filled:
      case CompetitionStatus.published:
      case CompetitionStatus.openForJoin:
        return LiveMatchPhase.preMatch;
      default:
        return LiveMatchPhase.preMatch;
    }
  }

  static int _minuteForPhase(Random rng, LiveMatchPhase phase) {
    switch (phase) {
      case LiveMatchPhase.firstHalf:
        return 18 + rng.nextInt(27);
      case LiveMatchPhase.halftime:
        return 45;
      case LiveMatchPhase.secondHalf:
        return 52 + rng.nextInt(35);
      case LiveMatchPhase.fullTime:
        return 90;
      case LiveMatchPhase.preMatch:
        return 0;
    }
  }

  static int _scoreForSide(
    Random rng,
    LiveMatchPhase phase, {
    required bool isHome,
  }) {
    if (phase == LiveMatchPhase.preMatch) {
      return 0;
    }
    final int base = rng.nextInt(3);
    if (isHome && phase == LiveMatchPhase.firstHalf) {
      return base;
    }
    if (!isHome && phase == LiveMatchPhase.firstHalf) {
      return max(0, base - 1);
    }
    if (phase == LiveMatchPhase.fullTime) {
      return base + rng.nextInt(2);
    }
    return base;
  }

  static List<LiveMatchLineupPlayer> _buildLineup(
    Random rng,
    String team, {
    required int captainSeed,
  }) {
    final List<String> names = List<String>.from(_playerNames, growable: false);
    names.shuffle(rng);
    final int captainIndex = captainSeed % 11;
    return List<LiveMatchLineupPlayer>.generate(11, (int index) {
      final String player = names[index];
      return LiveMatchLineupPlayer(
        name: player,
        position: _positions[index % _positions.length],
        rating: 6.2 + rng.nextDouble() * 2.2,
        captain: index == captainIndex,
      );
    });
  }

  static List<LiveMatchEvent> _buildCommentary({
    required String homeTeam,
    required String awayTeam,
    required int minute,
  }) {
    final List<LiveMatchEvent> events = <LiveMatchEvent>[
      LiveMatchEvent(
        minute: 2,
        title: 'Opening tempo',
        detail: '$homeTeam press immediately and win the first second-ball.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 9,
        title: 'Early warning',
        detail: '$awayTeam switch the flank to stretch the back line.',
        team: awayTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 18,
        title: 'First shot on target',
        detail: '$homeTeam force a low save after a diagonal cutback.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 24,
        title: 'Yellow card',
        detail: 'Late pressure foul as $awayTeam breaks the press.',
        team: awayTeam,
        type: LiveMatchEventType.card,
      ),
      LiveMatchEvent(
        minute: 33,
        title: 'Key moment',
        detail: '$homeTeam finish a three-pass transition for the opener.',
        team: homeTeam,
        type: LiveMatchEventType.goal,
        isKeyMoment: true,
      ),
      LiveMatchEvent(
        minute: 41,
        title: 'Momentum swing',
        detail: '$awayTeam answer with an aggressive corner routine.',
        team: awayTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 56,
        title: 'Substitution',
        detail: '$awayTeam bring on a fresh winger to isolate the fullback.',
        team: awayTeam,
        type: LiveMatchEventType.substitution,
      ),
      LiveMatchEvent(
        minute: 64,
        title: 'Key moment',
        detail: '$awayTeam pull level after a rebound falls in the box.',
        team: awayTeam,
        type: LiveMatchEventType.goal,
        isKeyMoment: true,
      ),
      LiveMatchEvent(
        minute: 71,
        title: 'Tactical reset',
        detail: '$homeTeam shift into a 4-2-3-1 to regain midfield control.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
      ),
      LiveMatchEvent(
        minute: 78,
        title: 'Substitution',
        detail: '$homeTeam add a second striker and stretch the line.',
        team: homeTeam,
        type: LiveMatchEventType.substitution,
      ),
      LiveMatchEvent(
        minute: max(82, minute),
        title: 'Key moment',
        detail: '$homeTeam fire wide after a late cut-in.',
        team: homeTeam,
        type: LiveMatchEventType.incident,
        isKeyMoment: true,
      ),
    ];
    return events
        .where((LiveMatchEvent event) => event.minute <= max(90, minute))
        .toList(growable: false);
  }

  static List<LiveMatchTacticalSuggestion> _buildSuggestions(Random rng) {
    final List<LiveMatchTacticalSuggestion>
    suggestions = <LiveMatchTacticalSuggestion>[
      const LiveMatchTacticalSuggestion(
        title: 'Shift press to the right channel',
        detail:
            'Their build-up overloads the left side. Force turnovers toward the touchline to compress space.',
        impactLabel: 'High press +8',
      ),
      const LiveMatchTacticalSuggestion(
        title: 'Trigger early fullback overlap',
        detail:
            'Opposition winger is staying high. Overlap quickly to create 2v1s on the outside.',
        impactLabel: 'Width +12',
      ),
      const LiveMatchTacticalSuggestion(
        title: 'Rotate the striker',
        detail: 'Stagger the forward line to pull a center-back out of shape.',
        impactLabel: 'Shot quality +6',
      ),
    ];
    suggestions.shuffle(rng);
    return suggestions.take(2).toList(growable: false);
  }

  static List<LiveMatchHighlightClip> _buildKeyMoments(
    CompetitionSummary competition,
    List<LiveMatchEvent> keyMoments,
  ) {
    final DateTime now = DateTime.now().toUtc();
    return keyMoments
        .asMap()
        .entries
        .map((MapEntry<int, LiveMatchEvent> entry) {
          final LiveMatchEvent event = entry.value;
          return LiveMatchHighlightClip(
            id: '${competition.id}-key-${entry.key}',
            title: event.title,
            minute: event.minute,
            durationLabel: '${18 + entry.key * 3} sec',
            isPremium: true,
            isArchived: false,
            expiresAt: now.add(const Duration(hours: 3)),
            downloadEligible: true,
          );
        })
        .toList(growable: false);
  }

  static List<LiveMatchHighlightClip> _buildHighlights(
    CompetitionSummary competition,
    List<LiveMatchEvent> commentary,
    DateTime standardExpiry,
    DateTime premiumExpiry,
  ) {
    final List<LiveMatchEvent> shortlist = commentary
        .where(
          (LiveMatchEvent event) =>
              event.type == LiveMatchEventType.goal || event.isKeyMoment,
        )
        .take(4)
        .toList(growable: false);
    if (shortlist.isEmpty) {
      shortlist.addAll(commentary.take(3));
    }
    return shortlist
        .asMap()
        .entries
        .map((MapEntry<int, LiveMatchEvent> entry) {
          final LiveMatchEvent event = entry.value;
          final bool premium = entry.key.isEven;
          return LiveMatchHighlightClip(
            id: '${competition.id}-clip-${entry.key}',
            title: event.detail,
            minute: event.minute,
            durationLabel: '${22 + entry.key * 4} sec',
            isPremium: premium,
            isArchived: false,
            expiresAt: premium ? premiumExpiry : standardExpiry,
            downloadEligible: premium,
          );
        })
        .toList(growable: false);
  }
}

const List<String> _teamNames = <String>[
  'GTEX United',
  'Atlas City',
  'Solar FC',
  'Northbridge',
  'Lumen SC',
  'Tidehold',
  'Copperlane',
  'Aster Athletic',
];

const List<String> _playerNames = <String>[
  'Adebayo Musa',
  'Kofi Mensah',
  'Jasper Hale',
  'Ibrahim Diallo',
  'Luca Moretti',
  'Noah Rivers',
  'Theo Martins',
  'Samir Keita',
  'Emeka Odion',
  'Bastien Clarke',
  'Rene Savic',
  'Marcos Silva',
  'Jude Akin',
  'Elias Hart',
  'Dario Lopez',
  'Victor Nwosu',
  'Hugo Lane',
  'Felix Morel',
  'Amir Kone',
  'Liam Okoro',
  'Omar Suazo',
  'Nico Patel',
  'Sergio Quinn',
  'Jonah Brandt',
];

const List<String> _positions = <String>[
  'GK',
  'RB',
  'CB',
  'CB',
  'LB',
  'DM',
  'CM',
  'CM',
  'RW',
  'ST',
  'LW',
];

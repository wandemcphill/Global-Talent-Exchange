import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/match/match_simulation_engine.dart';
import 'package:gte_frontend/features/match_center/data/match/match_simulation_models.dart';
import 'package:gte_frontend/features/match_center/data/match/match_value_engine.dart';

void main() {
  test(
    'local match event generation is disabled for the canonical match center',
    () {
      final MatchSimulationRequest request = MatchSimulationRequest(
        matchId: 'deterministic-sim',
        seed: 19,
        importance: MatchSimulationImportance.quickMatch,
        homeTeam: MatchSimulationTeam(
          id: 'home',
          name: 'Atlas City',
          shortName: 'ATL',
          formation: '4-3-3',
          primaryColorHex: '#173F7A',
          secondaryColorHex: '#F4F7FB',
          accentColorHex: '#F59E0B',
          goalkeeperColorHex: '#0F172A',
          attack: 82,
          midfield: 78,
          defense: 75,
          goalkeeper: 79,
          tactics: MatchSimulationTactics(
            style: MatchSimulationStyle.possession,
            pressing: MatchSimulationPressing.high,
            tempo: MatchSimulationTempo.fast,
          ),
          players: <MatchSimulationPlayer>[
            _player('home-gk', 'A. Keeper', 'GK', 74),
            _player('home-rb', 'B. Back', 'RB', 73),
            _player('home-cb1', 'C. Centre', 'CB', 75),
            _player('home-cb2', 'D. Marker', 'CB', 74),
            _player('home-lb', 'E. Fullback', 'LB', 73),
            _player('home-dm', 'F. Shield', 'DM', 77),
            _player('home-cm1', 'G. Progressor', 'CM', 79),
            _player('home-cm2', 'H. Creator', 'CM', 78),
            _player('home-rw', 'I. Winger', 'RW', 81),
            _player('home-st', 'J. Finisher', 'ST', 84),
            _player('home-lw', 'K. Inside', 'LW', 80),
          ],
        ),
        awayTeam: MatchSimulationTeam(
          id: 'away',
          name: 'Northbridge',
          shortName: 'NOR',
          formation: '4-3-3',
          primaryColorHex: '#B42318',
          secondaryColorHex: '#FFF3F2',
          accentColorHex: '#FDB022',
          goalkeeperColorHex: '#111827',
          attack: 76,
          midfield: 74,
          defense: 80,
          goalkeeper: 82,
          tactics: MatchSimulationTactics(
            style: MatchSimulationStyle.counter,
            pressing: MatchSimulationPressing.low,
            tempo: MatchSimulationTempo.medium,
          ),
          players: <MatchSimulationPlayer>[
            _player('away-gk', 'L. Stopper', 'GK', 78),
            _player('away-rb', 'M. Back', 'RB', 77),
            _player('away-cb1', 'N. Centre', 'CB', 79),
            _player('away-cb2', 'O. Marker', 'CB', 78),
            _player('away-lb', 'P. Fullback', 'LB', 76),
            _player('away-dm', 'Q. Anchor', 'DM', 75),
            _player('away-cm1', 'R. Carrier', 'CM', 74),
            _player('away-cm2', 'S. Runner', 'CM', 74),
            _player('away-rw', 'T. Outlet', 'RW', 76),
            _player('away-st', 'U. Breaker', 'ST', 79),
            _player('away-lw', 'V. Sprint', 'LW', 76),
          ],
        ),
      );

      expect(
        () => const MatchSimulationEngine().simulate(request),
        throwsA(
          isA<UnsupportedError>().having(
            (UnsupportedError error) => error.message,
            'message',
            contains(
              'Local match event generation is disabled for the canonical match center',
            ),
          ),
        ),
      );
    },
  );

  test('value engine applies match-performance multipliers and decay', () {
    final MatchSimulationPlayer attacker = _player(
      'attacker',
      'Hat Trick',
      'ST',
      84,
      age: 20,
    );
    final MatchSimulationPlayer defender = _player(
      'defender',
      'Clean Sheet',
      'CB',
      79,
      age: 24,
    );

    final List<MatchSimulationPlayerPerformance> updated =
        const MatchValueEngine().apply(
          performances: <MatchSimulationPlayerPerformance>[
            MatchSimulationPlayerPerformance(
              player: attacker,
              teamId: 'home',
              teamName: 'Atlas City',
              rating: 8.8,
              goals: 3,
              assists: 1,
              keyPasses: 2,
              shots: 5,
              shotsOnTarget: 4,
              saves: 0,
              turnoversWon: 1,
              mistakes: 0,
              cleanSheet: false,
              isMvp: false,
              formTag: MatchFormTag.steady,
              previousValueCredits: attacker.baseValueCredits,
              nextValueCredits: attacker.baseValueCredits,
              valueDeltaPct: 0,
            ),
            MatchSimulationPlayerPerformance(
              player: defender,
              teamId: 'away',
              teamName: 'Northbridge',
              rating: 7.4,
              goals: 0,
              assists: 0,
              keyPasses: 0,
              shots: 0,
              shotsOnTarget: 0,
              saves: 0,
              turnoversWon: 4,
              mistakes: 0,
              cleanSheet: true,
              isMvp: false,
              formTag: MatchFormTag.steady,
              previousValueCredits: defender.baseValueCredits,
              nextValueCredits: defender.baseValueCredits,
              valueDeltaPct: 0,
            ),
          ],
          importance: MatchSimulationImportance.finalMatch,
        );

    final MatchSimulationPlayerPerformance boostedAttacker = updated.firstWhere(
      (MatchSimulationPlayerPerformance item) => item.player.id == attacker.id,
    );
    final MatchSimulationPlayerPerformance boostedDefender = updated.firstWhere(
      (MatchSimulationPlayerPerformance item) => item.player.id == defender.id,
    );

    expect(boostedAttacker.isMvp, isTrue);
    expect(boostedAttacker.valueDeltaPct, greaterThan(0.20));
    expect(boostedAttacker.formTag, MatchFormTag.risingTalent);
    expect(boostedDefender.valueDeltaPct, greaterThan(0.05));
    expect(
      const MatchValueEngine().applyDailyDecay(1000, days: 2),
      closeTo(990.025, 0.001),
    );
  });

  test('local simulation preview generation is quarantined', () {
    final MatchSimulationRequest request = MatchSimulationRequest(
      matchId: 'preview-fairness',
      seed: 33,
      homeTeam: MatchSimulationTeam(
        id: 'home',
        name: 'Atlas City',
        shortName: 'ATL',
        formation: '4-3-3',
        primaryColorHex: '#173F7A',
        secondaryColorHex: '#F4F7FB',
        accentColorHex: '#F59E0B',
        goalkeeperColorHex: '#0F172A',
        attack: 80,
        midfield: 78,
        defense: 76,
        goalkeeper: 79,
        tactics: MatchSimulationTactics(
          style: MatchSimulationStyle.direct,
          pressing: MatchSimulationPressing.medium,
          tempo: MatchSimulationTempo.fast,
        ),
        players: <MatchSimulationPlayer>[
          _player('home-gk', 'A. Keeper', 'GK', 74),
          _player('home-rb', 'B. Back', 'RB', 73),
          _player('home-cb1', 'C. Centre', 'CB', 75),
          _player('home-cb2', 'D. Marker', 'CB', 74),
          _player('home-lb', 'E. Fullback', 'LB', 73),
          _player('home-dm', 'F. Shield', 'DM', 77),
          _player('home-cm1', 'G. Progressor', 'CM', 79),
          _player('home-cm2', 'H. Creator', 'CM', 78),
          _player('home-rw', 'I. Winger', 'RW', 81),
          _player('home-st', 'J. Finisher', 'ST', 84),
          _player('home-lw', 'K. Inside', 'LW', 80),
        ],
      ),
      awayTeam: MatchSimulationTeam(
        id: 'away',
        name: 'Northbridge',
        shortName: 'NOR',
        formation: '4-3-3',
        primaryColorHex: '#B42318',
        secondaryColorHex: '#FFF3F2',
        accentColorHex: '#FDB022',
        goalkeeperColorHex: '#111827',
        attack: 76,
        midfield: 74,
        defense: 80,
        goalkeeper: 82,
        tactics: MatchSimulationTactics(
          style: MatchSimulationStyle.counter,
          pressing: MatchSimulationPressing.low,
          tempo: MatchSimulationTempo.medium,
        ),
        players: <MatchSimulationPlayer>[
          _player('away-gk', 'L. Stopper', 'GK', 78),
          _player('away-rb', 'M. Back', 'RB', 77),
          _player('away-cb1', 'N. Centre', 'CB', 79),
          _player('away-cb2', 'O. Marker', 'CB', 78),
          _player('away-lb', 'P. Fullback', 'LB', 76),
          _player('away-dm', 'Q. Anchor', 'DM', 75),
          _player('away-cm1', 'R. Carrier', 'CM', 74),
          _player('away-cm2', 'S. Runner', 'CM', 74),
          _player('away-rw', 'T. Outlet', 'RW', 76),
          _player('away-st', 'U. Breaker', 'ST', 79),
          _player('away-lw', 'V. Sprint', 'LW', 76),
        ],
      ),
    );

    expect(
      () => const MatchSimulationEngine().simulate(request),
      throwsA(
        isA<UnsupportedError>().having(
          (UnsupportedError error) => error.message,
          'message',
          contains(
            'Local match event generation is disabled for the canonical match center',
          ),
        ),
      ),
    );
  });
}

MatchSimulationPlayer _player(
  String id,
  String name,
  String position,
  int overall, {
  int age = 23,
}) {
  final String normalized = position.trim().toUpperCase();
  return MatchSimulationPlayer(
    id: id,
    name: name,
    position: normalized,
    overall: overall,
    age: age,
    baseValueCredits: (overall * 18).toDouble(),
    finishing:
        normalized == 'ST' || normalized == 'RW' || normalized == 'LW'
            ? overall + 6
            : normalized == 'GK'
            ? 35
            : overall - 4,
    creativity:
        normalized == 'CM' || normalized == 'DM' ? overall + 5 : overall,
    defending:
        normalized == 'CB' || normalized == 'RB' || normalized == 'LB'
            ? overall + 6
            : overall - 6,
    goalkeeping: normalized == 'GK' ? overall + 8 : 35,
    pace: normalized == 'RW' || normalized == 'LW' ? overall + 7 : overall,
    workRate:
        normalized == 'DM' || normalized == 'CM' || normalized == 'CB'
            ? overall + 5
            : overall,
  );
}

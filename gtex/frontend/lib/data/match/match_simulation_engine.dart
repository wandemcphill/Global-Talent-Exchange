import 'dart:math';

import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/data/match/match_simulation_models.dart';
import 'package:gte_frontend/data/match/match_value_engine.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/fairness_indicator_service.dart';

class MatchSimulationRequestFactory {
  const MatchSimulationRequestFactory._();

  static MatchSimulationRequest fromLiveSnapshot(
    LiveMatchSnapshot snapshot, {
    String? matchId,
    MatchSimulationImportance importance = MatchSimulationImportance.quickMatch,
    int? seed,
  }) {
    final String resolvedMatchId = _resolveMatchId(snapshot, matchId: matchId);
    final int resolvedSeed = seed ??
        (resolvedMatchId.hashCode ^
                snapshot.homeTeam.hashCode ^
                snapshot.awayTeam.hashCode)
            .abs();

    final List<MatchSimulationPlayer> homePlayers = _mapPlayers(
      snapshot.homeLineup,
      teamName: snapshot.homeTeam,
      matchId: resolvedMatchId,
    );
    final List<MatchSimulationPlayer> awayPlayers = _mapPlayers(
      snapshot.awayLineup,
      teamName: snapshot.awayTeam,
      matchId: resolvedMatchId,
    );

    return MatchSimulationRequest(
      matchId: resolvedMatchId,
      seed: resolvedSeed,
      importance: importance,
      homeTeam: _buildTeam(
        id: 'home',
        name: snapshot.homeTeam,
        players: homePlayers,
        tactics: _deriveTactics(
          homePlayers,
          isHome: true,
          opponentSeed: snapshot.awayTeam.hashCode.abs(),
        ),
        colors: _paletteForTeam(snapshot.homeTeam, home: true),
      ),
      awayTeam: _buildTeam(
        id: 'away',
        name: snapshot.awayTeam,
        players: awayPlayers,
        tactics: _deriveTactics(
          awayPlayers,
          isHome: false,
          opponentSeed: snapshot.homeTeam.hashCode.abs(),
        ),
        colors: _paletteForTeam(snapshot.awayTeam, home: false),
      ),
    );
  }

  static String _resolveMatchId(
    LiveMatchSnapshot snapshot, {
    String? matchId,
  }) {
    final String? explicitMatchId = matchId?.trim();
    if (explicitMatchId != null && explicitMatchId.isNotEmpty) {
      return explicitMatchId;
    }
    final String? snapshotMatchId = snapshot.matchId?.trim();
    if (snapshotMatchId != null && snapshotMatchId.isNotEmpty) {
      return snapshotMatchId;
    }
    return '${snapshot.homeTeam}-${snapshot.awayTeam}'
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-');
  }

  static MatchSimulationTeam _buildTeam({
    required String id,
    required String name,
    required List<MatchSimulationPlayer> players,
    required MatchSimulationTactics tactics,
    required _TeamPalette colors,
  }) {
    final MatchSimulationPlayer goalkeeper = players.firstWhere(
      (MatchSimulationPlayer player) => player.isGoalkeeper,
      orElse: () => players.first,
    );
    final List<MatchSimulationPlayer> attackers = players
        .where((MatchSimulationPlayer player) => player.isForward)
        .toList(growable: false);
    final List<MatchSimulationPlayer> midfielders = players
        .where((MatchSimulationPlayer player) => player.isMidfielder)
        .toList(growable: false);
    final List<MatchSimulationPlayer> defenders = players
        .where((MatchSimulationPlayer player) => player.isDefender)
        .toList(growable: false);

    final int attack = _roundedAverage(
      attackers.isEmpty ? players : attackers,
      (MatchSimulationPlayer player) => ((player.finishing * 0.55) +
              (player.pace * 0.20) +
              (player.overall * 0.25))
          .round(),
    );
    final int midfield = _roundedAverage(
      midfielders.isEmpty ? players : midfielders,
      (MatchSimulationPlayer player) => ((player.creativity * 0.50) +
              (player.workRate * 0.20) +
              (player.overall * 0.30))
          .round(),
    );
    final int defense = _roundedAverage(
      defenders.isEmpty ? players : defenders,
      (MatchSimulationPlayer player) => ((player.defending * 0.65) +
              (player.workRate * 0.15) +
              (player.overall * 0.20))
          .round(),
    );

    return MatchSimulationTeam(
      id: id,
      name: name,
      shortName: _shortName(name),
      formation: '4-3-3',
      primaryColorHex: colors.primaryColorHex,
      secondaryColorHex: colors.secondaryColorHex,
      accentColorHex: colors.accentColorHex,
      goalkeeperColorHex: colors.goalkeeperColorHex,
      attack: attack.clamp(60, 92),
      midfield: midfield.clamp(60, 92),
      defense: (((defense * 0.82) + (goalkeeper.goalkeeping * 0.18)).round())
          .clamp(60, 92),
      goalkeeper: goalkeeper.goalkeeping.clamp(60, 95),
      tactics: tactics,
      players: List<MatchSimulationPlayer>.unmodifiable(players),
    );
  }

  static List<MatchSimulationPlayer> _mapPlayers(
    List<LiveMatchLineupPlayer> lineup, {
    required String teamName,
    required String matchId,
  }) {
    final List<LiveMatchLineupPlayer> source =
        lineup.isEmpty ? _fallbackLineup(teamName) : lineup;
    return List<MatchSimulationPlayer>.generate(
      min(11, source.length),
      (int index) {
        final LiveMatchLineupPlayer item = source[index];
        final String stableId = item.stablePlayerReference(
          teamName: teamName,
          matchId: matchId,
        );
        final int overall = ((item.rating * 10).round()).clamp(58, 88);
        final int age = 18 + (stableId.hashCode.abs() % 14);
        final double baseValueCredits =
            max(240, ((overall - 44) * (overall - 38)).toDouble());
        final String normalizedPosition = _normalizedPosition(item.position);
        return MatchSimulationPlayer(
          id: stableId,
          name: item.name,
          position: normalizedPosition,
          overall: overall,
          age: age,
          baseValueCredits: baseValueCredits,
          finishing: _attribute(
            overall,
            bonus: switch (normalizedPosition) {
              'ST' || 'CF' => 10,
              'RW' || 'LW' => 6,
              'AM' => 4,
              'CM' || 'RM' || 'LM' => 1,
              'GK' => -24,
              _ => -8,
            },
          ),
          creativity: _attribute(
            overall,
            bonus: switch (normalizedPosition) {
              'AM' || 'CM' => 9,
              'RW' || 'LW' || 'RM' || 'LM' => 7,
              'DM' => 5,
              'ST' || 'CF' => 2,
              'GK' => -18,
              _ => -3,
            },
          ),
          defending: _attribute(
            overall,
            bonus: switch (normalizedPosition) {
              'CB' || 'RB' || 'LB' || 'RWB' || 'LWB' => 10,
              'DM' => 8,
              'GK' => -16,
              _ => -7,
            },
          ),
          goalkeeping: _attribute(
            overall,
            bonus: normalizedPosition == 'GK' ? 12 : -28,
          ),
          pace: _attribute(
            overall,
            bonus: switch (normalizedPosition) {
              'RW' || 'LW' || 'RB' || 'LB' || 'RWB' || 'LWB' => 8,
              'ST' || 'CF' => 4,
              'GK' => -20,
              _ => 0,
            },
          ),
          workRate: _attribute(
            overall,
            bonus: switch (normalizedPosition) {
              'DM' || 'CM' || 'RB' || 'LB' || 'CB' => 6,
              'GK' => -12,
              _ => 2,
            },
          ),
          role: _roleForPosition(
            normalizedPosition,
            stableId: stableId,
          ),
        );
      },
      growable: false,
    );
  }

  static MatchSimulationTactics _deriveTactics(
    List<MatchSimulationPlayer> players, {
    required bool isHome,
    required int opponentSeed,
  }) {
    final int attackBias = players
        .where((MatchSimulationPlayer player) => player.isForward)
        .fold<int>(
          0,
          (int sum, MatchSimulationPlayer player) => sum + player.overall,
        );
    final int controlBias = players
        .where((MatchSimulationPlayer player) =>
            player.isMidfielder || player.isDefender)
        .fold<int>(
          0,
          (int sum, MatchSimulationPlayer player) => sum + player.workRate,
        );
    final int wideBias = players
        .where((MatchSimulationPlayer player) => player.isWidePlayer)
        .fold<int>(
          0,
          (int sum, MatchSimulationPlayer player) =>
              sum + player.pace + player.creativity,
        );
    final bool possessionLean = controlBias >= attackBias || isHome;
    final bool directLean = attackBias > (controlBias + 20);
    final bool wingLean = wideBias >= ((attackBias + controlBias) ~/ 2);
    final MatchSimulationStyle style = wingLean
        ? MatchSimulationStyle.wingPlay
        : possessionLean
            ? MatchSimulationStyle.possession
            : directLean
                ? MatchSimulationStyle.direct
                : MatchSimulationStyle.counter;
    return MatchSimulationTactics(
      style: style,
      pressing: possessionLean || (opponentSeed % 3 == 0)
          ? MatchSimulationPressing.high
          : directLean
              ? MatchSimulationPressing.medium
              : MatchSimulationPressing.low,
      tempo: attackBias >= controlBias
          ? MatchSimulationTempo.fast
          : wingLean
              ? MatchSimulationTempo.fast
              : MatchSimulationTempo.medium,
      lineHeight: possessionLean
          ? MatchSimulationLineHeight.high
          : directLean
              ? MatchSimulationLineHeight.medium
              : MatchSimulationLineHeight.low,
      width: wingLean
          ? MatchSimulationWidth.wide
          : controlBias > attackBias
              ? MatchSimulationWidth.balanced
              : MatchSimulationWidth.narrow,
    );
  }

  static _TeamPalette _paletteForTeam(String teamName, {required bool home}) {
    final List<_TeamPalette> palettes = home
        ? const <_TeamPalette>[
            _TeamPalette('#173F7A', '#F4F7FB', '#F59E0B', '#0F172A'),
            _TeamPalette('#0F4C5C', '#E0FBFC', '#EE6C4D', '#17313A'),
            _TeamPalette('#245953', '#E6FFFB', '#FFD166', '#112D2A'),
          ]
        : const <_TeamPalette>[
            _TeamPalette('#B42318', '#FFF3F2', '#FDB022', '#111827'),
            _TeamPalette('#6D1F5F', '#FFF0FB', '#F79009', '#261225'),
            _TeamPalette('#7A2E0B', '#FFF5EB', '#53B1FD', '#24170D'),
          ];
    return palettes[teamName.hashCode.abs() % palettes.length];
  }

  static String _shortName(String teamName) {
    final List<String> parts = teamName
        .split(RegExp(r'\s+'))
        .where((String part) => part.trim().isNotEmpty)
        .toList(growable: false);
    if (parts.length >= 2) {
      final String third = parts.length > 2 ? parts[2][0] : '';
      return '${parts[0][0]}${parts[1][0]}$third'.toUpperCase();
    }
    final String trimmed = teamName.trim().toUpperCase();
    return trimmed.length <= 3 ? trimmed : trimmed.substring(0, 3);
  }

  static List<LiveMatchLineupPlayer> _fallbackLineup(String teamName) {
    return List<LiveMatchLineupPlayer>.generate(
      11,
      (int index) => LiveMatchLineupPlayer(
        name: '$teamName Player ${index + 1}',
        position: const <String>[
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
        ][index],
        rating: 6.4 + ((index % 4) * 0.3),
      ),
      growable: false,
    );
  }

  static int _attribute(int overall, {required int bonus}) {
    return (overall + bonus).clamp(35, 95);
  }

  static int _roundedAverage<T>(
    List<T> source,
    int Function(T item) selector,
  ) {
    if (source.isEmpty) {
      return 70;
    }
    final int sum = source.fold<int>(
      0,
      (int value, T item) => value + selector(item),
    );
    return (sum / source.length).round();
  }

  static MatchSimulationRole _roleForPosition(
    String normalizedPosition, {
    required String stableId,
  }) {
    return switch (normalizedPosition) {
      'GK' => MatchSimulationRole.sweeperKeeper,
      'CB' => MatchSimulationRole.stopper,
      'RB' || 'LB' || 'RWB' || 'LWB' => MatchSimulationRole.fullback,
      'DM' => MatchSimulationRole.anchor,
      'AM' => MatchSimulationRole.playmaker,
      'CM' => stableId.hashCode.isEven
          ? MatchSimulationRole.playmaker
          : MatchSimulationRole.boxToBox,
      'RM' || 'LM' || 'RW' || 'LW' => MatchSimulationRole.winger,
      'CF' => MatchSimulationRole.finisher,
      'ST' => stableId.hashCode.isEven
          ? MatchSimulationRole.poacher
          : MatchSimulationRole.finisher,
      _ => MatchSimulationRole.generic,
    };
  }
}

class MatchSimulationEngine {
  const MatchSimulationEngine({
    MatchValueEngine? valueEngine,
  }) : _valueEngine = valueEngine ?? const MatchValueEngine();

  final MatchValueEngine _valueEngine;

  MatchSimulationResult simulate(MatchSimulationRequest request) {
    final Random rng = Random(request.seed);
    final _MutableTeamState homeState = _MutableTeamState(request.homeTeam);
    final _MutableTeamState awayState = _MutableTeamState(request.awayTeam);
    final int halftimeMinute = (request.durationMinutes / 2).round();
    final double inPlayScale =
        request.playbackDurationSeconds / (request.durationMinutes + 1);
    Set<String> recoveringPlayerIds = <String>{};

    int sequence = 0;
    final MatchEvent kickoff = _buildEvent(
      id: '${request.matchId}-kickoff',
      sequence: sequence++,
      type: MatchViewerEventType.kickoff,
      minute: 0,
      timeSeconds: 0,
      homeScore: 0,
      awayScore: 0,
      bannerText: 'Kickoff',
      commentary:
          '${request.homeTeam.name} and ${request.awayTeam.name} get the tactical simulation underway.',
    );

    final List<MatchEvent> events = <MatchEvent>[kickoff];
    final List<_MinuteSnapshot> minutes = <_MinuteSnapshot>[
      _MinuteSnapshot(
        minute: 0,
        homeScore: 0,
        awayScore: 0,
        homePossessionShare: 50,
        possessionSide: MatchViewerSide.home,
        context: _MinuteContext.control,
        event: kickoff,
        ballLane: 50,
        recoveringPlayerIds: const <String>{},
      ),
    ];

    for (int minute = 1; minute <= request.durationMinutes; minute += 1) {
      final double homePossessionShare = _resolvePossessionShare(
        homeState: homeState,
        awayState: awayState,
        minute: minute,
        rng: rng,
      );
      homeState.possessionAccumulator += homePossessionShare;
      awayState.possessionAccumulator += 1 - homePossessionShare;

      final bool homePossession = rng.nextDouble() < homePossessionShare;
      final _MutableTeamState attacking =
          homePossession ? homeState : awayState;
      final _MutableTeamState defending =
          homePossession ? awayState : homeState;
      final MatchViewerSide possessionSide =
          homePossession ? MatchViewerSide.home : MatchViewerSide.away;
      final _MinuteContext context = _resolveContext(
        attacking: attacking,
        defending: defending,
        rng: rng,
      );

      MatchEvent? event;
      String? shooterId;
      String? creatorId;
      String? winnerId;
      double ballLane = 30 + (rng.nextDouble() * 40);
      final Set<String> nextRecoveryIds = <String>{};

      final double chanceProbability = _resolveChanceProbability(
        attacking: attacking,
        defending: defending,
        context: context,
        minute: minute,
        rng: rng,
      );

      if (rng.nextDouble() < chanceProbability) {
        final _MutablePlayerState shooter = _selectShooter(
          attacking,
          context: context,
          minute: minute,
          rng: rng,
        );
        final _MutablePlayerState? creator = _selectCreator(
          attacking,
          shooter: shooter,
          minute: minute,
          rng: rng,
        );
        shooter.shots += 1;
        shooter.recoveries += 1;
        nextRecoveryIds.add(shooter.player.id);
        if (creator != null) {
          creator.keyPasses += 1;
          creator.passesCompleted += 1;
          if (context != _MinuteContext.control) {
            creator.recoveries += 1;
            nextRecoveryIds.add(creator.player.id);
          }
        }
        shooterId = shooter.player.id;
        creatorId = creator?.player.id;
        ballLane = _laneForPlayer(shooter.player, fallback: ballLane);

        if (context == _MinuteContext.counter &&
            defending.team.tactics.style == MatchSimulationStyle.possession &&
            rng.nextDouble() < 0.11) {
          event = _buildEvent(
            id: '${request.matchId}-offside-$minute',
            sequence: sequence++,
            type: MatchViewerEventType.offside,
            minute: minute,
            timeSeconds: minute * inPlayScale,
            teamId: attacking.team.id,
            teamName: attacking.team.name,
            primaryPlayerId: shooter.player.id,
            primaryPlayerName: shooter.player.name,
            homeScore: homeState.score,
            awayScore: awayState.score,
            bannerText: 'Offside',
            commentary:
                '${attacking.team.name} spring the counter, but ${shooter.player.name} is caught offside.',
            emphasisLevel: 2,
            highlightedPlayerIds: <String>[
              shooter.player.id,
              if (creator != null) creator.player.id,
            ],
            flags: _flagsForContext(context),
            playbackProfile: 'offside',
          );
        } else {
          attacking.shots += 1;
          shooter.shots += 1;
          final double xg = _resolveXg(
            attacking: attacking,
            defending: defending,
            shooter: shooter.player,
            context: context,
            rng: rng,
          );
          attacking.expectedGoals += xg;
          if (xg >= 0.25) {
            attacking.bigChances += 1;
          }
          final _ShotOutcome outcome = _resolveShotOutcome(
            xg: xg,
            shooter: shooter.player,
            goalkeeperRating: defending.team.goalkeeper,
            rng: rng,
          );

          switch (outcome) {
            case _ShotOutcome.goal:
              shooter.shotsOnTarget += 1;
              attacking.shotsOnTarget += 1;
              attacking.score += 1;
              shooter.goals += 1;
              if (creator != null && creator.player.id != shooter.player.id) {
                creator.assists += 1;
              }
              defending.concededAtMinute = minute;
              attacking.momentumUntilMinute = minute + 5;
              event = _buildGoalEvent(
                request: request,
                sequence: sequence++,
                minute: minute,
                timeSeconds: minute * inPlayScale,
                attacking: attacking,
                shooter: shooter.player,
                creator: creator?.player,
                homeScore: homeState.score,
                awayScore: awayState.score,
                context: context,
              );
              break;
            case _ShotOutcome.save:
              shooter.shotsOnTarget += 1;
              attacking.shotsOnTarget += 1;
              defending.goalkeeperState.saves += 1;
              event = _buildEvent(
                id: '${request.matchId}-save-$minute',
                sequence: sequence++,
                type: MatchViewerEventType.save,
                minute: minute,
                timeSeconds: minute * inPlayScale,
                teamId: defending.team.id,
                teamName: defending.team.name,
                primaryPlayerId: shooter.player.id,
                primaryPlayerName: shooter.player.name,
                secondaryPlayerId: defending.goalkeeperState.player.id,
                secondaryPlayerName: defending.goalkeeperState.player.name,
                homeScore: homeState.score,
                awayScore: awayState.score,
                bannerText: 'Saved chance',
                commentary:
                    '${defending.goalkeeperState.player.name} keeps out ${shooter.player.name} after a ${_contextLabel(context)} move.',
                emphasisLevel: 2,
                highlightedPlayerIds: <String>[
                  shooter.player.id,
                  defending.goalkeeperState.player.id,
                ],
                flags: _flagsForContext(context),
                playbackProfile: 'attack',
              );
              break;
            case _ShotOutcome.miss:
              event = _buildEvent(
                id: '${request.matchId}-miss-$minute',
                sequence: sequence++,
                type: MatchViewerEventType.miss,
                minute: minute,
                timeSeconds: minute * inPlayScale,
                teamId: attacking.team.id,
                teamName: attacking.team.name,
                primaryPlayerId: shooter.player.id,
                primaryPlayerName: shooter.player.name,
                homeScore: homeState.score,
                awayScore: awayState.score,
                bannerText: 'Big chance missed',
                commentary:
                    '${shooter.player.name} gets on the end of the ${_contextLabel(context)} attack but misses the target.',
                emphasisLevel: 2,
                highlightedPlayerIds: <String>[
                  shooter.player.id,
                  if (creator != null) creator.player.id,
                ],
                flags: _flagsForContext(context),
                playbackProfile: 'attack',
                missVariant: rng.nextBool() ? 'wide' : 'post',
              );
              break;
          }
        }
      } else if ((minute % 9 == 0) || rng.nextDouble() < 0.05) {
        final _MutablePlayerState progressor = _selectProgressor(
          attacking,
          minute: minute,
          rng: rng,
        );
        shooterId = progressor.player.id;
        ballLane = _laneForPlayer(progressor.player, fallback: ballLane);
        if (_snapshotIntensity(context) >= 0.72) {
          progressor.recoveries += 1;
          nextRecoveryIds.add(progressor.player.id);
        }
        event = _buildEvent(
          id: '${request.matchId}-attack-$minute',
          sequence: sequence++,
          type: MatchViewerEventType.attack,
          minute: minute,
          timeSeconds: minute * inPlayScale,
          teamId: attacking.team.id,
          teamName: attacking.team.name,
          primaryPlayerId: progressor.player.id,
          primaryPlayerName: progressor.player.name,
          homeScore: homeState.score,
          awayScore: awayState.score,
          bannerText: 'Building pressure',
          commentary:
              '${attacking.team.name} circulate the ball with intent and probe for a lane through midfield.',
          emphasisLevel: 1,
          highlightedPlayerIds: <String>[progressor.player.id],
          flags: _flagsForContext(context),
          playbackProfile: 'neutral',
        );
      }

      if (context == _MinuteContext.turnover) {
        attacking.turnoversForced += 1;
        final _MutablePlayerState winner =
            _selectBallWinner(attacking, minute: minute, rng: rng);
        winner.turnoversWon += 1;
        winner.pressuresWon += 1;
        winner.recoveries += 1;
        winnerId = winner.player.id;
        nextRecoveryIds.add(winner.player.id);
        if (rng.nextDouble() < 0.35) {
          final _MutablePlayerState mistake =
              _selectMistakePlayer(defending, rng: rng);
          mistake.mistakes += 1;
        }
      }

      minutes.add(
        _MinuteSnapshot(
          minute: minute,
          homeScore: homeState.score,
          awayScore: awayState.score,
          homePossessionShare: (homePossessionShare * 100).round(),
          possessionSide: possessionSide,
          context: context,
          event: event,
          ballLane: ballLane,
          shooterId: shooterId,
          creatorId: creatorId,
          winnerId: winnerId,
          recoveringPlayerIds: Set<String>.unmodifiable(recoveringPlayerIds),
        ),
      );
      recoveringPlayerIds = nextRecoveryIds;
      if (event != null) {
        events.add(event);
      }

      if (minute == halftimeMinute) {
        events.add(
          _buildEvent(
            id: '${request.matchId}-halftime',
            sequence: sequence++,
            type: MatchViewerEventType.halftime,
            minute: halftimeMinute,
            timeSeconds: (halftimeMinute + 0.45) * inPlayScale,
            homeScore: homeState.score,
            awayScore: awayState.score,
            bannerText: 'Halftime',
            commentary:
                'Halftime arrives with ${request.homeTeam.name} ${homeState.score}-${awayState.score} ${request.awayTeam.name}.',
            emphasisLevel: 1,
          ),
        );
      }
    }

    events.add(
      _buildEvent(
        id: '${request.matchId}-fulltime',
        sequence: sequence++,
        type: MatchViewerEventType.fulltime,
        minute: request.durationMinutes,
        timeSeconds: request.playbackDurationSeconds.toDouble(),
        homeScore: homeState.score,
        awayScore: awayState.score,
        bannerText: 'Full time',
        commentary:
            'Full time. ${request.homeTeam.name} ${homeState.score}-${awayState.score} ${request.awayTeam.name}.',
      ),
    );

    final List<MatchSimulationPlayerPerformance> basePerformances =
        <MatchSimulationPlayerPerformance>[
      ...homeState.finalizePerformances(concededGoals: awayState.score),
      ...awayState.finalizePerformances(concededGoals: homeState.score),
    ];

    return MatchSimulationResult(
      request: request,
      viewState: _buildViewState(
        request: request,
        minutes: minutes,
        events: events,
      ),
      homeStats: MatchSimulationTeamStats(
        teamId: request.homeTeam.id,
        teamName: request.homeTeam.name,
        possessionPct:
            (homeState.possessionAccumulator / request.durationMinutes * 100)
                .round(),
        shots: homeState.shots,
        shotsOnTarget: homeState.shotsOnTarget,
        expectedGoals: _roundDouble(homeState.expectedGoals),
        bigChances: homeState.bigChances,
        turnoversForced: homeState.turnoversForced,
        averageStaminaPct: _teamAverageStamina(
          request.homeTeam,
          minute: request.durationMinutes,
        ),
        recoveries: homeState.totalRecoveries,
        successfulPresses: homeState.totalPressuresWon,
      ),
      awayStats: MatchSimulationTeamStats(
        teamId: request.awayTeam.id,
        teamName: request.awayTeam.name,
        possessionPct: 100 -
            (homeState.possessionAccumulator / request.durationMinutes * 100)
                .round(),
        shots: awayState.shots,
        shotsOnTarget: awayState.shotsOnTarget,
        expectedGoals: _roundDouble(awayState.expectedGoals),
        bigChances: awayState.bigChances,
        turnoversForced: awayState.turnoversForced,
        averageStaminaPct: _teamAverageStamina(
          request.awayTeam,
          minute: request.durationMinutes,
        ),
        recoveries: awayState.totalRecoveries,
        successfulPresses: awayState.totalPressuresWon,
      ),
      playerPerformances: _valueEngine.apply(
        performances: basePerformances,
        importance: request.importance,
      ),
    );
  }

  double _resolvePossessionShare({
    required _MutableTeamState homeState,
    required _MutableTeamState awayState,
    required int minute,
    required Random rng,
  }) {
    final double homeModifier = _possessionModifier(homeState, minute: minute);
    final double awayModifier = _possessionModifier(awayState, minute: minute);
    final double homeWeighted = homeState.team.midfield * homeModifier;
    final double awayWeighted = awayState.team.midfield * awayModifier;
    final double share = homeWeighted / (homeWeighted + awayWeighted);
    final double drift = (rng.nextDouble() * 0.06) - 0.03;
    return (share + drift).clamp(0.34, 0.66).toDouble();
  }

  double _possessionModifier(
    _MutableTeamState teamState, {
    required int minute,
  }) {
    double modifier = 1;
    if (teamState.team.tactics.style == MatchSimulationStyle.possession) {
      modifier += 0.10;
    }
    if (teamState.team.tactics.style == MatchSimulationStyle.wingPlay) {
      modifier += 0.04;
    }
    if (teamState.team.tactics.pressing == MatchSimulationPressing.high) {
      modifier += 0.05;
    }
    if (teamState.team.tactics.style == MatchSimulationStyle.counter) {
      modifier -= 0.10;
    }
    if (teamState.team.tactics.style == MatchSimulationStyle.direct) {
      modifier -= 0.04;
    }
    if (minute <= teamState.momentumUntilMinute) {
      modifier += 0.05;
    }
    if (teamState.concededAtMinute != null &&
        (minute - teamState.concededAtMinute!) <= 4) {
      modifier -= 0.03;
    }
    modifier *= _teamStaminaModifier(
      teamState.team,
      minute: minute,
      lowerBound: 0.90,
      upperBound: 1.05,
    );
    return modifier.clamp(0.82, 1.22).toDouble();
  }

  _MinuteContext _resolveContext({
    required _MutableTeamState attacking,
    required _MutableTeamState defending,
    required Random rng,
  }) {
    if (attacking.team.tactics.style == MatchSimulationStyle.counter &&
        defending.team.tactics.style == MatchSimulationStyle.possession) {
      return _MinuteContext.counter;
    }
    if (attacking.team.tactics.pressing == MatchSimulationPressing.high &&
        defending.team.tactics.pressing == MatchSimulationPressing.low &&
        rng.nextDouble() < 0.32) {
      return _MinuteContext.turnover;
    }
    return _MinuteContext.control;
  }

  double _resolveChanceProbability({
    required _MutableTeamState attacking,
    required _MutableTeamState defending,
    required _MinuteContext context,
    required int minute,
    required Random rng,
  }) {
    final double tempoFactor = switch (attacking.team.tactics.tempo) {
      MatchSimulationTempo.slow => 0.90,
      MatchSimulationTempo.medium => 1.00,
      MatchSimulationTempo.fast => 1.14,
    };
    final double contextFactor = switch (context) {
      _MinuteContext.control => 1.00,
      _MinuteContext.counter => 1.10,
      _MinuteContext.turnover => 1.18,
    };
    final double styleFactor = switch (attacking.team.tactics.style) {
      MatchSimulationStyle.possession => 1.02,
      MatchSimulationStyle.counter => 1.06,
      MatchSimulationStyle.balanced => 1.00,
      MatchSimulationStyle.direct => 1.08,
      MatchSimulationStyle.wingPlay => 1.05,
    };
    final double momentumFactor =
        minute <= attacking.momentumUntilMinute ? 1.05 : 1.0;
    final double staminaFactor = _teamStaminaModifier(
      attacking.team,
      minute: minute,
      lowerBound: 0.86,
      upperBound: 1.02,
    );
    final double randomFactor = 0.82 + (rng.nextDouble() * 0.36);
    final double ratingFactor =
        attacking.team.attack / max(1, defending.team.defense);
    final double value = 0.11 *
        ratingFactor *
        tempoFactor *
        contextFactor *
        styleFactor *
        momentumFactor *
        staminaFactor *
        randomFactor;
    return value.clamp(0.05, 0.24).toDouble();
  }

  double _resolveXg({
    required _MutableTeamState attacking,
    required _MutableTeamState defending,
    required MatchSimulationPlayer shooter,
    required _MinuteContext context,
    required Random rng,
  }) {
    final double edge =
        ((attacking.team.attack / max(1, defending.team.defense)) - 0.85)
            .clamp(0.04, 0.42)
            .toDouble();
    final double tacticalBonus = switch (context) {
      _MinuteContext.control =>
        attacking.team.tactics.style == MatchSimulationStyle.possession
            ? 1.06
            : 1.0,
      _MinuteContext.counter => 1.18,
      _MinuteContext.turnover => 1.12,
    };
    final double styleBonus = switch (attacking.team.tactics.style) {
      MatchSimulationStyle.possession => 1.02,
      MatchSimulationStyle.counter => 1.04,
      MatchSimulationStyle.balanced => 1.0,
      MatchSimulationStyle.direct => 1.06,
      MatchSimulationStyle.wingPlay => shooter.isWidePlayer ? 1.08 : 1.01,
    };
    final double tempoAccuracy = switch (attacking.team.tactics.tempo) {
      MatchSimulationTempo.slow => 1.04,
      MatchSimulationTempo.medium => 1.0,
      MatchSimulationTempo.fast => 0.94,
    };
    final double finishingFactor = 0.86 + (shooter.finishing / 100 * 0.24);
    final double randomFactor = 0.82 + (rng.nextDouble() * 0.36);
    final double xg = (0.08 + (edge * 0.24)) *
        tacticalBonus *
        styleBonus *
        tempoAccuracy *
        finishingFactor *
        randomFactor;
    return xg.clamp(0.05, 0.42).toDouble();
  }

  _ShotOutcome _resolveShotOutcome({
    required double xg,
    required MatchSimulationPlayer shooter,
    required int goalkeeperRating,
    required Random rng,
  }) {
    final double goalChance = (xg *
            (0.90 + (shooter.finishing / 100 * 0.18)) *
            (0.74 + ((100 - goalkeeperRating) / 100 * 0.22)))
        .clamp(0.03, 0.58)
        .toDouble();
    final double saveChance =
        (0.12 + xg + (shooter.finishing / 500)).clamp(0.12, 0.46).toDouble();
    final double roll = rng.nextDouble();
    if (roll < goalChance) {
      return _ShotOutcome.goal;
    }
    if (roll < goalChance + saveChance) {
      return _ShotOutcome.save;
    }
    return _ShotOutcome.miss;
  }

  _MutablePlayerState _selectShooter(
    _MutableTeamState teamState, {
    required _MinuteContext context,
    required int minute,
    required Random rng,
  }) {
    final List<_WeightedPlayer> weights = teamState.playerStates
        .map(
          (_MutablePlayerState player) => _WeightedPlayer(
            player: player,
            weight: () {
              double weight = 0.2 +
                  (player.player.finishing / 120) +
                  _roleShotWeight(player.player.role);
              if (player.player.isForward) {
                weight += 1.0;
              } else if (player.player.isMidfielder) {
                weight += 0.45;
              } else if (player.player.isDefender) {
                weight += 0.18;
              }
              if (context == _MinuteContext.counter) {
                weight += player.player.pace / 220;
              }
              weight *= _staminaModifierForPlayer(
                player.player,
                teamState.team,
                minute: minute,
                intense: true,
              );
              return weight;
            }(),
          ),
        )
        .toList(growable: false);
    return _pickWeighted(weights, rng).player;
  }

  _MutablePlayerState? _selectCreator(
    _MutableTeamState teamState, {
    required _MutablePlayerState shooter,
    required int minute,
    required Random rng,
  }) {
    final List<_WeightedPlayer> weights = teamState.playerStates
        .where(
          (_MutablePlayerState player) => player.player.id != shooter.player.id,
        )
        .map(
          (_MutablePlayerState player) => _WeightedPlayer(
            player: player,
            weight: (0.18 +
                    (player.player.creativity / 130) +
                    _roleCreatorWeight(player.player.role) +
                    (player.player.isMidfielder ? 0.5 : 0) +
                    (player.player.isForward ? 0.25 : 0)) *
                _staminaModifierForPlayer(
                  player.player,
                  teamState.team,
                  minute: minute,
                  intense: false,
                ),
          ),
        )
        .toList(growable: false);
    if (weights.isEmpty || rng.nextDouble() < 0.18) {
      return null;
    }
    return _pickWeighted(weights, rng).player;
  }

  _MutablePlayerState _selectProgressor(
    _MutableTeamState teamState, {
    required int minute,
    required Random rng,
  }) {
    final List<_WeightedPlayer> weights = teamState.playerStates
        .map(
          (_MutablePlayerState player) => _WeightedPlayer(
            player: player,
            weight: (0.18 +
                    (player.player.creativity / 150) +
                    (player.player.workRate / 200) +
                    _roleProgressionWeight(player.player.role)) *
                _staminaModifierForPlayer(
                  player.player,
                  teamState.team,
                  minute: minute,
                  intense: false,
                ),
          ),
        )
        .toList(growable: false);
    return _pickWeighted(weights, rng).player;
  }

  _MutablePlayerState _selectBallWinner(
    _MutableTeamState teamState, {
    required int minute,
    required Random rng,
  }) {
    final List<_WeightedPlayer> weights = teamState.playerStates
        .map(
          (_MutablePlayerState player) => _WeightedPlayer(
            player: player,
            weight: (0.2 +
                    (player.player.workRate / 160) +
                    (player.player.defending / 180) +
                    _roleDefensiveWeight(player.player.role)) *
                _staminaModifierForPlayer(
                  player.player,
                  teamState.team,
                  minute: minute,
                  intense: true,
                ),
          ),
        )
        .toList(growable: false);
    return _pickWeighted(weights, rng).player;
  }

  _MutablePlayerState _selectMistakePlayer(
    _MutableTeamState teamState, {
    required Random rng,
  }) {
    final List<_WeightedPlayer> weights = teamState.playerStates
        .map(
          (_MutablePlayerState player) => _WeightedPlayer(
            player: player,
            weight: player.player.isGoalkeeper
                ? 0.18
                : player.player.isDefender
                    ? 0.55
                    : 0.24,
          ),
        )
        .toList(growable: false);
    return _pickWeighted(weights, rng).player;
  }

  MatchEvent _buildGoalEvent({
    required MatchSimulationRequest request,
    required int sequence,
    required int minute,
    required double timeSeconds,
    required _MutableTeamState attacking,
    required MatchSimulationPlayer shooter,
    required MatchSimulationPlayer? creator,
    required int homeScore,
    required int awayScore,
    required _MinuteContext context,
  }) {
    final String commentary = switch (context) {
      _MinuteContext.control =>
        '${attacking.team.name} pull the shape apart and ${shooter.name} finishes the move.',
      _MinuteContext.counter =>
        'Counter attack from ${attacking.team.name}, and ${shooter.name} converts at pace.',
      _MinuteContext.turnover =>
        '${attacking.team.name} win it high, and ${shooter.name} punishes the turnover.',
    };
    return _buildEvent(
      id: '${request.matchId}-goal-$minute-$sequence',
      sequence: sequence,
      type: MatchViewerEventType.goal,
      minute: minute,
      timeSeconds: timeSeconds,
      teamId: attacking.team.id,
      teamName: attacking.team.name,
      primaryPlayerId: shooter.id,
      primaryPlayerName: shooter.name,
      secondaryPlayerId: creator?.id,
      secondaryPlayerName: creator?.name,
      homeScore: homeScore,
      awayScore: awayScore,
      bannerText: 'Goal',
      commentary: commentary,
      emphasisLevel: 3,
      highlightedPlayerIds: <String>[
        shooter.id,
        if (creator != null) creator.id,
      ],
      flags: _flagsForContext(context),
      playbackProfile: 'goal',
    );
  }

  MatchEvent _buildEvent({
    required String id,
    required int sequence,
    required MatchViewerEventType type,
    required int minute,
    required double timeSeconds,
    required int homeScore,
    required int awayScore,
    required String bannerText,
    required String commentary,
    String? teamId,
    String? teamName,
    String? primaryPlayerId,
    String? primaryPlayerName,
    String? secondaryPlayerId,
    String? secondaryPlayerName,
    int emphasisLevel = 1,
    List<String> highlightedPlayerIds = const <String>[],
    List<String> flags = const <String>[],
    String playbackProfile = 'neutral',
    String? missVariant,
  }) {
    return MatchEvent(
      id: id,
      sequence: sequence,
      type: type,
      minute: minute,
      addedTime: 0,
      clockLabel: '$minute\'',
      timeSeconds: _roundDouble(timeSeconds),
      teamId: teamId,
      teamName: teamName,
      primaryPlayerId: primaryPlayerId,
      primaryPlayerName: primaryPlayerName,
      secondaryPlayerId: secondaryPlayerId,
      secondaryPlayerName: secondaryPlayerName,
      homeScore: homeScore,
      awayScore: awayScore,
      bannerText: bannerText,
      commentary: commentary,
      emphasisLevel: emphasisLevel,
      highlightedPlayerIds: highlightedPlayerIds,
      flags: flags,
      playbackProfile: playbackProfile,
      missVariant: missVariant,
    );
  }

  MatchViewState _buildViewState({
    required MatchSimulationRequest request,
    required List<_MinuteSnapshot> minutes,
    required List<MatchEvent> events,
  }) {
    final List<MatchTimelineFrame> frames = <MatchTimelineFrame>[];
    final double inPlayScale =
        request.playbackDurationSeconds / (request.durationMinutes + 1);
    final int halftimeMinute = (request.durationMinutes / 2).round();

    for (final _MinuteSnapshot snapshot in minutes) {
      if (snapshot.minute == 0) {
        frames.add(
          _buildFrame(
            request: request,
            snapshot: snapshot,
            phase: MatchViewerPhase.kickoff,
            stage: MatchPlaybackStage.reset,
            timeSeconds: 0,
            clockMinute: 0,
          ),
        );
        continue;
      }

      frames.add(
        _buildFrame(
          request: request,
          snapshot: snapshot,
          phase: MatchViewerPhase.openPlay,
          stage: snapshot.event == null
              ? MatchPlaybackStage.pre
              : MatchPlaybackStage.event,
          timeSeconds: snapshot.minute * inPlayScale,
          clockMinute: snapshot.minute.toDouble(),
        ),
      );

      if (snapshot.minute == halftimeMinute) {
        frames.add(
          _buildFrame(
            request: request,
            snapshot: snapshot,
            phase: MatchViewerPhase.halftime,
            stage: MatchPlaybackStage.hold,
            timeSeconds: (snapshot.minute + 0.45) * inPlayScale,
            clockMinute: snapshot.minute.toDouble(),
            activeEventId: '${request.matchId}-halftime',
            eventBanner: 'Halftime',
            overlayText: 'Halftime',
          ),
        );
      }
    }

    final _MinuteSnapshot finalSnapshot = minutes.last;
    frames.add(
      _buildFrame(
        request: request,
        snapshot: finalSnapshot,
        phase: MatchViewerPhase.fulltime,
        stage: MatchPlaybackStage.post,
        timeSeconds: request.playbackDurationSeconds.toDouble(),
        clockMinute: request.durationMinutes.toDouble(),
        activeEventId: '${request.matchId}-fulltime',
        eventBanner: 'Full time',
        overlayText: 'Full time',
      ),
    );

    final MatchViewState previewViewState = MatchViewState(
      matchId: request.matchId,
      source: 'local_simulation',
      supportsOffside: true,
      deterministicSeed: request.seed,
      matchMode: MatchMode.standard,
      durationSeconds: request.playbackDurationSeconds,
      homeTeam: MatchViewerTeam(
        teamId: request.homeTeam.id,
        teamName: request.homeTeam.name,
        shortName: request.homeTeam.shortName,
        side: MatchViewerSide.home,
        formation: request.homeTeam.formation,
        primaryColorHex: request.homeTeam.primaryColorHex,
        secondaryColorHex: request.homeTeam.secondaryColorHex,
        accentColorHex: request.homeTeam.accentColorHex,
        goalkeeperColorHex: request.homeTeam.goalkeeperColorHex,
      ),
      awayTeam: MatchViewerTeam(
        teamId: request.awayTeam.id,
        teamName: request.awayTeam.name,
        shortName: request.awayTeam.shortName,
        side: MatchViewerSide.away,
        formation: request.awayTeam.formation,
        primaryColorHex: request.awayTeam.primaryColorHex,
        secondaryColorHex: request.awayTeam.secondaryColorHex,
        accentColorHex: request.awayTeam.accentColorHex,
        goalkeeperColorHex: request.awayTeam.goalkeeperColorHex,
      ),
      events: List<MatchEvent>.unmodifiable(events),
      frames: List<MatchTimelineFrame>.unmodifiable(frames),
      fairnessIndicator: const MatchFairnessIndicator(
        status: MatchVerificationStatus.unverified,
        label: 'Preview Mode',
        message:
            'Deterministic preview with tactical roles, stamina, and recovery. Competitive anti-cheat and replay validation belong to the authoritative server path.',
        serverAuthoritative: false,
      ),
      timelineProof: MatchTimelineProof(
        status: MatchVerificationStatus.unverified,
        matchHash: 'seed:${request.seed}',
        timelineHash: 'timeline:${request.matchId}:${request.seed}',
        signed: false,
        revealedThroughSeconds: request.playbackDurationSeconds,
      ),
    );
    return previewViewState.copyWith(
      timelineProof: MatchTimelineProof(
        status: MatchVerificationStatus.unverified,
        matchHash: 'seed:${request.seed}',
        timelineHash: 'timeline:${request.matchId}:${request.seed}',
        visibleTimelineHash:
            FairnessIndicatorService.computeVisibleTimelineHash(
                previewViewState),
        signed: false,
        revealedThroughSeconds: request.playbackDurationSeconds,
      ),
    );
  }

  MatchTimelineFrame _buildFrame({
    required MatchSimulationRequest request,
    required _MinuteSnapshot snapshot,
    required MatchViewerPhase phase,
    required MatchPlaybackStage stage,
    required double timeSeconds,
    required double clockMinute,
    String? activeEventId,
    String? eventBanner,
    String? overlayText,
  }) {
    final bool homeAttacksRight =
        snapshot.minute <= (request.durationMinutes / 2).round();
    final MatchViewerPoint homeTarget = _targetPoint(
      side: MatchViewerSide.home,
      homeAttacksRight: homeAttacksRight,
      context: snapshot.context,
      ballLane: snapshot.ballLane,
      event: snapshot.event,
    );
    final MatchViewerPoint awayTarget = _targetPoint(
      side: MatchViewerSide.away,
      homeAttacksRight: homeAttacksRight,
      context: snapshot.context,
      ballLane: snapshot.ballLane,
      event: snapshot.event,
    );

    return MatchTimelineFrame(
      id: '${request.matchId}:${(timeSeconds * 100).round()}:${stage.name}',
      timeSeconds: _roundDouble(timeSeconds),
      clockMinute: _roundDouble(clockMinute),
      phase: phase,
      homeScore: snapshot.homeScore,
      awayScore: snapshot.awayScore,
      homeAttacksRight: homeAttacksRight,
      possessionSide: snapshot.possessionSide,
      activeEventId: activeEventId ?? snapshot.event?.id,
      eventBanner: eventBanner ?? snapshot.event?.bannerText,
      stage: stage,
      cameraPreset: _cameraForSnapshot(snapshot),
      overlayText: overlayText,
      playbackRate:
          snapshot.event?.type == MatchViewerEventType.goal ? 0.95 : 1.0,
      players: <MatchViewerPlayerFrame>[
        ..._playerFramesForTeam(
          team: request.homeTeam,
          side: MatchViewerSide.home,
          homeAttacksRight: homeAttacksRight,
          snapshot: snapshot,
          target: homeTarget,
        ),
        ..._playerFramesForTeam(
          team: request.awayTeam,
          side: MatchViewerSide.away,
          homeAttacksRight: homeAttacksRight,
          snapshot: snapshot,
          target: awayTarget,
        ),
      ],
      ball: _ballForFrame(
        snapshot: snapshot,
        homeAttacksRight: homeAttacksRight,
        homeTarget: homeTarget,
        awayTarget: awayTarget,
      ),
    );
  }

  List<MatchViewerPlayerFrame> _playerFramesForTeam({
    required MatchSimulationTeam team,
    required MatchViewerSide side,
    required bool homeAttacksRight,
    required _MinuteSnapshot snapshot,
    required MatchViewerPoint target,
  }) {
    final bool sideAttacksRight =
        side == MatchViewerSide.home ? homeAttacksRight : !homeAttacksRight;
    final List<MatchViewerPoint> anchors = _formationAnchors(
      formation: team.formation,
      attacksRight: sideAttacksRight,
    );
    return List<MatchViewerPlayerFrame>.generate(
      min(team.players.length, anchors.length),
      (int index) {
        final MatchSimulationPlayer player = team.players[index];
        final MatchViewerPoint anchor = anchors[index];
        final bool ownsPossession = snapshot.possessionSide == side;
        final bool highlighted = snapshot.shooterId == player.id ||
            snapshot.creatorId == player.id ||
            snapshot.winnerId == player.id;
        final double direction = sideAttacksRight ? 1 : -1;
        final int staminaPct = _staminaPctForPlayer(
          player,
          team,
          minute: snapshot.minute,
          highlighted: highlighted,
          context: snapshot.context,
        );
        final bool recovering =
            snapshot.recoveringPlayerIds.contains(player.id) ||
                (staminaPct < 42 && !highlighted);
        final MatchPlayerAnimationState animationState =
            _animationStateForPlayer(
          player: player,
          team: team,
          snapshot: snapshot,
          ownsPossession: ownsPossession,
          highlighted: highlighted,
          recovering: recovering,
        );
        final double speedRatio = _speedRatioForAnimation(
          animationState,
          staminaPct: staminaPct,
          player: player,
        );
        final double blendFactor = _blendFactorForAnimation(
          animationState,
          highlighted: highlighted,
          recovering: recovering,
        );
        final double lineShift = _lineShiftForPlayer(
          player: player,
          tactics: team.tactics,
          ownsPossession: ownsPossession,
          context: snapshot.context,
        );
        final double ballShiftX = _ballShiftForPossession(
          ballLane: snapshot.ballLane,
          tactics: team.tactics,
          ownsPossession: ownsPossession,
          direction: direction,
        );
        final double roleShiftX = _roleOffsetX(
          player: player,
          context: snapshot.context,
          ownsPossession: ownsPossession,
          direction: direction,
        );
        final double laneShift = _laneShiftForBall(
          player: player,
          tactics: team.tactics,
          ballLane: snapshot.ballLane,
          ownsPossession: ownsPossession,
        );
        final double roleShiftY = _roleOffsetY(
          player: player,
          context: snapshot.context,
          ballLane: snapshot.ballLane,
        );

        MatchViewerPoint position = MatchViewerPoint(
          x: (anchor.x + (lineShift * direction) + ballShiftX + roleShiftX)
              .clamp(4, 96)
              .toDouble(),
          y: (anchor.y +
                  laneShift +
                  roleShiftY +
                  _laneJitter(player.id, snapshot.minute))
              .clamp(10, 90)
              .toDouble(),
        );

        if (highlighted && !recovering) {
          position = MatchViewerPoint.lerp(
            position,
            target,
            animationState == MatchPlayerAnimationState.shoot ? 0.82 : 0.72,
          );
        } else if (ownsPossession && !player.isGoalkeeper) {
          position = MatchViewerPoint.lerp(
            position,
            target,
            animationState == MatchPlayerAnimationState.control ? 0.26 : 0.18,
          );
        } else if (!ownsPossession && !player.isGoalkeeper) {
          position = MatchViewerPoint.lerp(
            position,
            target,
            animationState == MatchPlayerAnimationState.intercept ? 0.14 : 0.08,
          );
        }

        if (recovering && !player.isGoalkeeper) {
          position = MatchViewerPoint.lerp(position, anchor, 0.24);
        }

        if (player.isGoalkeeper) {
          position = MatchViewerPoint(
            x: sideAttacksRight ? 8 : 92,
            y: 50 + (_laneJitter(player.id, snapshot.minute) * 0.4),
          );
        }

        return MatchViewerPlayerFrame(
          playerId: player.id,
          teamId: team.id,
          side: side,
          shirtNumber: index + 1,
          label: (index + 1).toString(),
          role: _roleForPlayer(player),
          line: _lineForPlayer(player),
          state: _viewerStateForAnimation(
            animationState,
            ownsPossession: ownsPossession,
          ),
          active: true,
          highlighted: highlighted,
          position: position,
          anchorPosition: anchor,
          animationState: animationState,
          speedRatio: speedRatio,
          blendFactor: blendFactor,
          staminaPct: staminaPct,
        );
      },
      growable: false,
    );
  }

  MatchViewerBallFrame _ballForFrame({
    required _MinuteSnapshot snapshot,
    required bool homeAttacksRight,
    required MatchViewerPoint homeTarget,
    required MatchViewerPoint awayTarget,
  }) {
    MatchViewerPoint position = snapshot.possessionSide == MatchViewerSide.home
        ? homeTarget
        : awayTarget;
    String state = 'rolling';
    double elevation = 0;

    switch (snapshot.event?.type) {
      case MatchViewerEventType.goal:
        position = _goalPoint(
          side: snapshot.possessionSide,
          homeAttacksRight: homeAttacksRight,
          lane: snapshot.ballLane,
        );
        state = 'net';
        elevation = 0.2;
        break;
      case MatchViewerEventType.save:
        position = _goalPoint(
          side: snapshot.possessionSide,
          homeAttacksRight: homeAttacksRight,
          lane: snapshot.ballLane,
        );
        state = 'save';
        elevation = 0.15;
        break;
      case MatchViewerEventType.miss:
        position = _goalPoint(
          side: snapshot.possessionSide,
          homeAttacksRight: homeAttacksRight,
          lane: snapshot.ballLane,
        ).copyWith(
          y: (snapshot.ballLane + 8).clamp(16, 84).toDouble(),
        );
        state = 'wide';
        elevation = 0.22;
        break;
      case MatchViewerEventType.offside:
        position = MatchViewerPoint.lerp(position, _centerPoint(), 0.18);
        state = 'stopped';
        break;
      case MatchViewerEventType.halftime:
      case MatchViewerEventType.fulltime:
        position = _centerPoint();
        state = 'stopped';
        break;
      default:
        break;
    }

    return MatchViewerBallFrame(
      position: position,
      ownerPlayerId: snapshot.shooterId ?? snapshot.winnerId,
      state: state,
      elevation: elevation,
    );
  }

  MatchCameraPreset _cameraForSnapshot(_MinuteSnapshot snapshot) {
    return switch (snapshot.event?.type) {
      MatchViewerEventType.goal => MatchCameraPreset.goalCelebration,
      MatchViewerEventType.offside => MatchCameraPreset.assistantFlag,
      MatchViewerEventType.save ||
      MatchViewerEventType.miss ||
      MatchViewerEventType.attack =>
        MatchCameraPreset.attackPush,
      _ => MatchCameraPreset.broadcast,
    };
  }

  MatchViewerPoint _targetPoint({
    required MatchViewerSide side,
    required bool homeAttacksRight,
    required _MinuteContext context,
    required double ballLane,
    required MatchEvent? event,
  }) {
    final bool attacksRight =
        side == MatchViewerSide.home ? homeAttacksRight : !homeAttacksRight;
    final double direction = attacksRight ? 1 : -1;
    final double baseX = switch (context) {
      _MinuteContext.control => attacksRight ? 62 : 38,
      _MinuteContext.counter => attacksRight ? 74 : 26,
      _MinuteContext.turnover => attacksRight ? 79 : 21,
    };
    if (event?.type == MatchViewerEventType.goal ||
        event?.type == MatchViewerEventType.save ||
        event?.type == MatchViewerEventType.miss) {
      return MatchViewerPoint(
        x: (baseX + (6 * direction)).clamp(8, 92).toDouble(),
        y: ballLane.clamp(18, 82).toDouble(),
      );
    }
    return MatchViewerPoint(
      x: baseX,
      y: ballLane.clamp(18, 82).toDouble(),
    );
  }

  MatchViewerPoint _goalPoint({
    required MatchViewerSide side,
    required bool homeAttacksRight,
    required double lane,
  }) {
    final bool attacksRight =
        side == MatchViewerSide.home ? homeAttacksRight : !homeAttacksRight;
    return MatchViewerPoint(
      x: attacksRight ? 92 : 8,
      y: lane.clamp(24, 76).toDouble(),
    );
  }

  MatchViewerPoint _centerPoint() => const MatchViewerPoint(x: 50, y: 50);
}

double _snapshotIntensity(_MinuteContext context) {
  return switch (context) {
    _MinuteContext.control => 0.54,
    _MinuteContext.counter => 0.82,
    _MinuteContext.turnover => 0.9,
  };
}

double _roleShotWeight(MatchSimulationRole role) {
  return switch (role) {
    MatchSimulationRole.poacher => 0.82,
    MatchSimulationRole.finisher => 0.74,
    MatchSimulationRole.winger => 0.34,
    MatchSimulationRole.playmaker => 0.12,
    MatchSimulationRole.boxToBox => 0.22,
    _ => 0,
  };
}

double _roleCreatorWeight(MatchSimulationRole role) {
  return switch (role) {
    MatchSimulationRole.playmaker => 0.82,
    MatchSimulationRole.winger => 0.48,
    MatchSimulationRole.boxToBox => 0.34,
    MatchSimulationRole.anchor => 0.22,
    _ => 0,
  };
}

double _roleProgressionWeight(MatchSimulationRole role) {
  return switch (role) {
    MatchSimulationRole.playmaker => 0.58,
    MatchSimulationRole.boxToBox => 0.44,
    MatchSimulationRole.fullback => 0.24,
    MatchSimulationRole.winger => 0.28,
    MatchSimulationRole.anchor => 0.18,
    _ => 0,
  };
}

double _roleDefensiveWeight(MatchSimulationRole role) {
  return switch (role) {
    MatchSimulationRole.stopper => 0.62,
    MatchSimulationRole.anchor => 0.48,
    MatchSimulationRole.boxToBox => 0.32,
    MatchSimulationRole.fullback => 0.28,
    _ => 0,
  };
}

int _teamAverageStamina(
  MatchSimulationTeam team, {
  required int minute,
}) {
  if (team.players.isEmpty) {
    return 100;
  }
  final int total = team.players.fold<int>(
    0,
    (int sum, MatchSimulationPlayer player) =>
        sum +
        _staminaPctForPlayer(
          player,
          team,
          minute: minute,
          highlighted: false,
          context: _MinuteContext.control,
        ),
  );
  return (total / team.players.length).round();
}

double _teamStaminaModifier(
  MatchSimulationTeam team, {
  required int minute,
  required double lowerBound,
  required double upperBound,
}) {
  final double modifier =
      0.78 + (_teamAverageStamina(team, minute: minute) / 100 * 0.28);
  return modifier.clamp(lowerBound, upperBound).toDouble();
}

double _staminaModifierForPlayer(
  MatchSimulationPlayer player,
  MatchSimulationTeam team, {
  required int minute,
  required bool intense,
}) {
  final int staminaPct = _staminaPctForPlayer(
    player,
    team,
    minute: minute,
    highlighted: intense,
    context: intense ? _MinuteContext.turnover : _MinuteContext.control,
  );
  return (0.74 + (staminaPct / 100 * 0.32)).clamp(0.74, 1.06).toDouble();
}

int _staminaPctForPlayer(
  MatchSimulationPlayer player,
  MatchSimulationTeam team, {
  required int minute,
  required bool highlighted,
  required _MinuteContext context,
}) {
  final double tempoDrain = switch (team.tactics.tempo) {
    MatchSimulationTempo.slow => 0.18,
    MatchSimulationTempo.medium => 0.26,
    MatchSimulationTempo.fast => 0.34,
  };
  final double pressDrain = switch (team.tactics.pressing) {
    MatchSimulationPressing.low => 0.08,
    MatchSimulationPressing.medium => 0.14,
    MatchSimulationPressing.high => 0.21,
  };
  final double lineDrain = switch (team.tactics.lineHeight) {
    MatchSimulationLineHeight.low => 0.03,
    MatchSimulationLineHeight.medium => 0.06,
    MatchSimulationLineHeight.high => 0.10,
  };
  final double roleDrain = switch (player.role) {
    MatchSimulationRole.boxToBox => 0.16,
    MatchSimulationRole.fullback => 0.12,
    MatchSimulationRole.winger => 0.11,
    MatchSimulationRole.poacher || MatchSimulationRole.finisher => 0.13,
    MatchSimulationRole.stopper || MatchSimulationRole.anchor => 0.09,
    MatchSimulationRole.sweeperKeeper => 0.04,
    _ => 0.08,
  };
  final double workload = minute *
      (tempoDrain +
          pressDrain +
          lineDrain +
          roleDrain +
          (_snapshotIntensity(context) * 0.08));
  final double workRateRelief = player.workRate * 0.10;
  final double paceTax = max(0, player.pace - 72) * 0.08;
  final double ageTax = max(0, player.age - 29) * 0.5;
  final double spotlightTax = highlighted ? 3.2 : 0;
  final double stamina =
      98 - workload - paceTax - ageTax - spotlightTax + workRateRelief;
  return stamina.round().clamp(34, 99);
}

MatchPlayerAnimationState _animationStateForPlayer({
  required MatchSimulationPlayer player,
  required MatchSimulationTeam team,
  required _MinuteSnapshot snapshot,
  required bool ownsPossession,
  required bool highlighted,
  required bool recovering,
}) {
  if (recovering) {
    return MatchPlayerAnimationState.recover;
  }
  if (player.isGoalkeeper) {
    if (snapshot.event?.type == MatchViewerEventType.save && highlighted) {
      return MatchPlayerAnimationState.control;
    }
    return MatchPlayerAnimationState.idle;
  }
  if (snapshot.winnerId == player.id) {
    final double urgency = _snapshotIntensity(snapshot.context) +
        (team.tactics.pressing == MatchSimulationPressing.high ? 0.08 : 0);
    return urgency > 0.86
        ? MatchPlayerAnimationState.tackle
        : MatchPlayerAnimationState.intercept;
  }
  if (snapshot.creatorId == player.id) {
    return MatchPlayerAnimationState.pass;
  }
  if (snapshot.shooterId == player.id) {
    return switch (snapshot.event?.type) {
      MatchViewerEventType.goal ||
      MatchViewerEventType.save ||
      MatchViewerEventType.miss =>
        MatchPlayerAnimationState.shoot,
      MatchViewerEventType.offside => MatchPlayerAnimationState.sprint,
      _ => MatchPlayerAnimationState.control,
    };
  }
  if (ownsPossession) {
    if (snapshot.context == _MinuteContext.counter) {
      return player.isForward || player.role == MatchSimulationRole.winger
          ? MatchPlayerAnimationState.sprint
          : MatchPlayerAnimationState.run;
    }
    if (player.role == MatchSimulationRole.playmaker ||
        player.role == MatchSimulationRole.anchor) {
      return MatchPlayerAnimationState.control;
    }
    return switch (_lineForPlayer(player)) {
      MatchPlayerLine.attack => MatchPlayerAnimationState.run,
      MatchPlayerLine.midfield => MatchPlayerAnimationState.run,
      MatchPlayerLine.defense => MatchPlayerAnimationState.jog,
      MatchPlayerLine.goalkeeper => MatchPlayerAnimationState.idle,
    };
  }
  if (team.tactics.pressing == MatchSimulationPressing.high &&
      (player.isDefender || player.isMidfielder)) {
    return MatchPlayerAnimationState.press;
  }
  return player.isForward
      ? MatchPlayerAnimationState.jog
      : MatchPlayerAnimationState.run;
}

double _speedRatioForAnimation(
  MatchPlayerAnimationState animationState, {
  required int staminaPct,
  required MatchSimulationPlayer player,
}) {
  final double base = switch (animationState) {
    MatchPlayerAnimationState.idle => 0.05,
    MatchPlayerAnimationState.jog => 0.34,
    MatchPlayerAnimationState.run => 0.58,
    MatchPlayerAnimationState.sprint => 0.92,
    MatchPlayerAnimationState.control => 0.24,
    MatchPlayerAnimationState.pass => 0.46,
    MatchPlayerAnimationState.shoot => 0.68,
    MatchPlayerAnimationState.press => 0.62,
    MatchPlayerAnimationState.save => 0.64,
    MatchPlayerAnimationState.celebrate => 0.42,
    MatchPlayerAnimationState.setPiece => 0.28,
    MatchPlayerAnimationState.sentOff => 0.03,
    MatchPlayerAnimationState.tackle => 0.74,
    MatchPlayerAnimationState.intercept => 0.66,
    MatchPlayerAnimationState.recover => 0.18,
  };
  final double paceLift = max(0, player.pace - 70) / 220;
  final double fatigueDrag = (staminaPct / 100).clamp(0.52, 1.0);
  return (base + paceLift) * fatigueDrag;
}

double _blendFactorForAnimation(
  MatchPlayerAnimationState animationState, {
  required bool highlighted,
  required bool recovering,
}) {
  if (recovering) {
    return 0.24;
  }
  final double base = switch (animationState) {
    MatchPlayerAnimationState.idle => 0.10,
    MatchPlayerAnimationState.jog => 0.24,
    MatchPlayerAnimationState.run => 0.42,
    MatchPlayerAnimationState.sprint => 0.70,
    MatchPlayerAnimationState.control => 0.56,
    MatchPlayerAnimationState.pass => 0.78,
    MatchPlayerAnimationState.shoot => 0.92,
    MatchPlayerAnimationState.press => 0.72,
    MatchPlayerAnimationState.save => 0.88,
    MatchPlayerAnimationState.celebrate => 0.82,
    MatchPlayerAnimationState.setPiece => 0.70,
    MatchPlayerAnimationState.sentOff => 0.14,
    MatchPlayerAnimationState.tackle => 0.88,
    MatchPlayerAnimationState.intercept => 0.80,
    MatchPlayerAnimationState.recover => 0.24,
  };
  return highlighted ? min(1, base + 0.06).toDouble() : base;
}

double _lineShiftForPlayer({
  required MatchSimulationPlayer player,
  required MatchSimulationTactics tactics,
  required bool ownsPossession,
  required _MinuteContext context,
}) {
  double base = ownsPossession
      ? switch (_lineForPlayer(player)) {
          MatchPlayerLine.goalkeeper => 0,
          MatchPlayerLine.defense => 2.5,
          MatchPlayerLine.midfield => 6,
          MatchPlayerLine.attack => 10,
        }
      : switch (_lineForPlayer(player)) {
          MatchPlayerLine.goalkeeper => 0,
          MatchPlayerLine.defense => -1.5,
          MatchPlayerLine.midfield => -3,
          MatchPlayerLine.attack => -5,
        };
  base += switch (tactics.lineHeight) {
    MatchSimulationLineHeight.low => -2.4,
    MatchSimulationLineHeight.medium => 0,
    MatchSimulationLineHeight.high => 2.6,
  };
  if (context == _MinuteContext.counter) {
    base += ownsPossession ? 2.2 : -1.0;
  }
  if (context == _MinuteContext.turnover) {
    base += ownsPossession ? 2.8 : -1.4;
  }
  if (tactics.style == MatchSimulationStyle.direct && ownsPossession) {
    base += 1.0;
  }
  return base;
}

double _ballShiftForPossession({
  required double ballLane,
  required MatchSimulationTactics tactics,
  required bool ownsPossession,
  required double direction,
}) {
  if (!ownsPossession) {
    return 0;
  }
  final double widthBias = switch (tactics.width) {
    MatchSimulationWidth.narrow => 0.55,
    MatchSimulationWidth.balanced => 0.72,
    MatchSimulationWidth.wide => 0.92,
  };
  final double centrality = 1 - ((ballLane - 50).abs() / 50);
  return direction * widthBias * centrality;
}

double _laneShiftForBall({
  required MatchSimulationPlayer player,
  required MatchSimulationTactics tactics,
  required double ballLane,
  required bool ownsPossession,
}) {
  final double towardBall = (ballLane - 50) * (ownsPossession ? 0.16 : 0.08);
  final double widthSpread = switch (tactics.width) {
    MatchSimulationWidth.narrow => player.isWidePlayer ? 3.4 : -1.2,
    MatchSimulationWidth.balanced => player.isWidePlayer ? 1.8 : 0,
    MatchSimulationWidth.wide => player.isWidePlayer ? -2.8 : 1.0,
  };
  return towardBall + widthSpread;
}

double _roleOffsetX({
  required MatchSimulationPlayer player,
  required _MinuteContext context,
  required bool ownsPossession,
  required double direction,
}) {
  final double base = switch (player.role) {
    MatchSimulationRole.poacher ||
    MatchSimulationRole.finisher =>
      ownsPossession ? 1.8 : -0.6,
    MatchSimulationRole.playmaker => ownsPossession ? -0.8 : 0.4,
    MatchSimulationRole.boxToBox => ownsPossession ? 0.7 : -0.2,
    MatchSimulationRole.anchor => ownsPossession ? -1.4 : -0.4,
    MatchSimulationRole.fullback => ownsPossession ? 0.4 : -0.6,
    MatchSimulationRole.stopper => ownsPossession ? -0.5 : 0.7,
    MatchSimulationRole.sweeperKeeper => -0.4,
    _ => 0,
  };
  final double contextBonus = switch (context) {
    _MinuteContext.control => 0,
    _MinuteContext.counter => ownsPossession ? 1.0 : -0.4,
    _MinuteContext.turnover => ownsPossession ? 0.8 : -0.6,
  };
  return (base + contextBonus) * direction;
}

double _roleOffsetY({
  required MatchSimulationPlayer player,
  required _MinuteContext context,
  required double ballLane,
}) {
  final double laneDelta = ballLane - 50;
  final double roleBias = switch (player.role) {
    MatchSimulationRole.winger ||
    MatchSimulationRole.fullback =>
      player.position.startsWith('R') ? -4.2 : 4.2,
    MatchSimulationRole.poacher ||
    MatchSimulationRole.finisher =>
      laneDelta * 0.04,
    MatchSimulationRole.playmaker => laneDelta * 0.07,
    MatchSimulationRole.anchor ||
    MatchSimulationRole.stopper =>
      laneDelta * 0.03,
    _ => 0,
  };
  final double contextBias = switch (context) {
    _MinuteContext.control => laneDelta * 0.05,
    _MinuteContext.counter => laneDelta * 0.10,
    _MinuteContext.turnover => laneDelta * 0.08,
  };
  return roleBias + contextBias;
}

MatchViewerPlayerState _viewerStateForAnimation(
  MatchPlayerAnimationState animationState, {
  required bool ownsPossession,
}) {
  return switch (animationState) {
    MatchPlayerAnimationState.idle => MatchViewerPlayerState.idle,
    MatchPlayerAnimationState.control ||
    MatchPlayerAnimationState.pass ||
    MatchPlayerAnimationState.shoot ||
    MatchPlayerAnimationState.celebrate ||
    MatchPlayerAnimationState.setPiece =>
      MatchViewerPlayerState.attacking,
    MatchPlayerAnimationState.press ||
    MatchPlayerAnimationState.tackle ||
    MatchPlayerAnimationState.intercept =>
      MatchViewerPlayerState.pressing,
    MatchPlayerAnimationState.save => MatchViewerPlayerState.defending,
    MatchPlayerAnimationState.sentOff => MatchViewerPlayerState.sentOff,
    MatchPlayerAnimationState.recover => ownsPossession
        ? MatchViewerPlayerState.moving
        : MatchViewerPlayerState.defending,
    MatchPlayerAnimationState.jog ||
    MatchPlayerAnimationState.run ||
    MatchPlayerAnimationState.sprint =>
      ownsPossession
          ? MatchViewerPlayerState.moving
          : MatchViewerPlayerState.defending,
  };
}

class _MutableTeamState {
  _MutableTeamState(this.team)
      : playersById = <String, _MutablePlayerState>{
          for (final MatchSimulationPlayer player in team.players)
            player.id: _MutablePlayerState(
              player: player,
              teamId: team.id,
              teamName: team.name,
            ),
        };

  final MatchSimulationTeam team;
  final Map<String, _MutablePlayerState> playersById;

  double possessionAccumulator = 0;
  double expectedGoals = 0;
  int score = 0;
  int shots = 0;
  int shotsOnTarget = 0;
  int bigChances = 0;
  int turnoversForced = 0;
  int momentumUntilMinute = 0;
  int? concededAtMinute;

  List<_MutablePlayerState> get playerStates =>
      playersById.values.toList(growable: false);

  int get totalRecoveries => playerStates.fold<int>(
        0,
        (int total, _MutablePlayerState player) => total + player.recoveries,
      );

  int get totalPressuresWon => playerStates.fold<int>(
        0,
        (int total, _MutablePlayerState player) => total + player.pressuresWon,
      );

  _MutablePlayerState get goalkeeperState {
    return playerStates.firstWhere(
      (_MutablePlayerState player) => player.player.isGoalkeeper,
      orElse: () => playerStates.first,
    );
  }

  List<MatchSimulationPlayerPerformance> finalizePerformances({
    required int concededGoals,
  }) {
    return playerStates
        .map(
          (_MutablePlayerState player) => player.toPerformance(
            cleanSheet: concededGoals == 0,
          ),
        )
        .toList(growable: false);
  }
}

class _MutablePlayerState {
  _MutablePlayerState({
    required this.player,
    required this.teamId,
    required this.teamName,
  });

  final MatchSimulationPlayer player;
  final String teamId;
  final String teamName;

  int goals = 0;
  int assists = 0;
  int keyPasses = 0;
  int shots = 0;
  int shotsOnTarget = 0;
  int saves = 0;
  int turnoversWon = 0;
  int mistakes = 0;
  int passesCompleted = 0;
  int pressuresWon = 0;
  int recoveries = 0;

  MatchSimulationPlayerPerformance toPerformance({
    required bool cleanSheet,
  }) {
    double rating = 6.0;
    rating += goals * 0.5;
    rating += assists * 0.3;
    rating += keyPasses * 0.1;
    rating += saves * 0.08;
    rating += turnoversWon * 0.04;
    rating -= mistakes * 0.25;
    if (cleanSheet && (player.isGoalkeeper || player.isDefender)) {
      rating += 0.4;
    }
    if (shots > 0 && goals == 0) {
      rating -= min(0.18, shots * 0.03);
    }
    rating = rating.clamp(4.4, 9.7).toDouble();
    return MatchSimulationPlayerPerformance(
      player: player,
      teamId: teamId,
      teamName: teamName,
      rating: _roundDouble(rating),
      goals: goals,
      assists: assists,
      keyPasses: keyPasses,
      shots: shots,
      shotsOnTarget: shotsOnTarget,
      saves: saves,
      turnoversWon: turnoversWon,
      mistakes: mistakes,
      cleanSheet: cleanSheet,
      isMvp: false,
      formTag: MatchFormTag.steady,
      previousValueCredits: player.baseValueCredits,
      nextValueCredits: player.baseValueCredits,
      valueDeltaPct: 0,
    );
  }
}

class _TeamPalette {
  const _TeamPalette(
    this.primaryColorHex,
    this.secondaryColorHex,
    this.accentColorHex,
    this.goalkeeperColorHex,
  );

  final String primaryColorHex;
  final String secondaryColorHex;
  final String accentColorHex;
  final String goalkeeperColorHex;
}

class _MinuteSnapshot {
  const _MinuteSnapshot({
    required this.minute,
    required this.homeScore,
    required this.awayScore,
    required this.homePossessionShare,
    required this.possessionSide,
    required this.context,
    required this.ballLane,
    this.event,
    this.shooterId,
    this.creatorId,
    this.winnerId,
    this.recoveringPlayerIds = const <String>{},
  });

  final int minute;
  final int homeScore;
  final int awayScore;
  final int homePossessionShare;
  final MatchViewerSide possessionSide;
  final _MinuteContext context;
  final MatchEvent? event;
  final double ballLane;
  final String? shooterId;
  final String? creatorId;
  final String? winnerId;
  final Set<String> recoveringPlayerIds;
}

enum _MinuteContext {
  control,
  counter,
  turnover,
}

enum _ShotOutcome {
  goal,
  save,
  miss,
}

class _WeightedPlayer {
  const _WeightedPlayer({
    required this.player,
    required this.weight,
  });

  final _MutablePlayerState player;
  final double weight;
}

_WeightedPlayer _pickWeighted(List<_WeightedPlayer> values, Random rng) {
  if (values.isEmpty) {
    throw StateError('Cannot select from an empty weighted player list.');
  }
  final double total = values.fold<double>(
    0,
    (double sum, _WeightedPlayer item) => sum + item.weight,
  );
  double roll = rng.nextDouble() * total;
  for (final _WeightedPlayer item in values) {
    roll -= item.weight;
    if (roll <= 0) {
      return item;
    }
  }
  return values.last;
}

List<String> _flagsForContext(_MinuteContext context) {
  return switch (context) {
    _MinuteContext.control => const <String>['structured_attack'],
    _MinuteContext.counter => const <String>['counter_attack'],
    _MinuteContext.turnover => const <String>['high_press_turnover'],
  };
}

String _contextLabel(_MinuteContext context) {
  return switch (context) {
    _MinuteContext.control => 'controlled',
    _MinuteContext.counter => 'counter',
    _MinuteContext.turnover => 'turnover-led',
  };
}

MatchViewerRole _roleForPlayer(MatchSimulationPlayer player) {
  if (player.isGoalkeeper) {
    return MatchViewerRole.goalkeeper;
  }
  if (player.isDefender) {
    return MatchViewerRole.defender;
  }
  if (player.isForward) {
    return MatchViewerRole.forward;
  }
  return MatchViewerRole.midfielder;
}

MatchPlayerLine _lineForPlayer(MatchSimulationPlayer player) {
  if (player.isGoalkeeper) {
    return MatchPlayerLine.goalkeeper;
  }
  if (player.isDefender) {
    return MatchPlayerLine.defense;
  }
  if (player.isForward) {
    return MatchPlayerLine.attack;
  }
  return MatchPlayerLine.midfield;
}

double _laneForPlayer(MatchSimulationPlayer player,
    {required double fallback}) {
  final String normalized = _normalizedPosition(player.position);
  return switch (normalized) {
    'RW' || 'RB' || 'RWB' => 26,
    'LW' || 'LB' || 'LWB' => 74,
    'ST' || 'CF' || 'AM' || 'CM' || 'DM' => 50,
    _ => fallback,
  };
}

double _laneJitter(String playerId, int minute) {
  final double phase =
      ((playerId.hashCode.abs() % 100) / 100) + (minute * 0.14);
  return sin(phase) * 2.8;
}

List<MatchViewerPoint> _formationAnchors({
  required String formation,
  required bool attacksRight,
}) {
  final List<int> lines = switch (formation.trim()) {
    '4-2-3-1' => const <int>[4, 2, 3, 1],
    '4-4-2' => const <int>[4, 4, 2],
    '4-3-3' => const <int>[4, 3, 3],
    _ => const <int>[4, 3, 3],
  };
  final List<MatchViewerPoint> anchors = <MatchViewerPoint>[
    MatchViewerPoint(x: attacksRight ? 8 : 92, y: 50),
  ];
  final double denominator = max(1, lines.length - 1).toDouble();
  for (int lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    final double rawX = 22 + ((60 / denominator) * lineIndex);
    final double x = attacksRight ? rawX : 100 - rawX;
    for (final double y in _lanePositions(lines[lineIndex])) {
      anchors.add(MatchViewerPoint(x: x, y: y));
    }
  }
  return anchors;
}

List<double> _lanePositions(int count) {
  if (count <= 1) {
    return const <double>[50];
  }
  return List<double>.generate(
    count,
    (int index) => 18 + ((64 / (count - 1)) * index),
    growable: false,
  );
}

double _roundDouble(double value) {
  return double.parse(value.toStringAsFixed(2));
}

String _normalizedPosition(String value) {
  final String upper = value.trim().toUpperCase();
  if (upper.contains('GK')) {
    return 'GK';
  }
  if (upper.contains('RWB')) {
    return 'RWB';
  }
  if (upper.contains('LWB')) {
    return 'LWB';
  }
  if (upper.contains('RB')) {
    return 'RB';
  }
  if (upper.contains('LB')) {
    return 'LB';
  }
  if (upper.contains('CB')) {
    return 'CB';
  }
  if (upper.contains('DM')) {
    return 'DM';
  }
  if (upper.contains('AM')) {
    return 'AM';
  }
  if (upper.contains('CM')) {
    return 'CM';
  }
  if (upper.contains('RM')) {
    return 'RM';
  }
  if (upper.contains('LM')) {
    return 'LM';
  }
  if (upper.contains('RW')) {
    return 'RW';
  }
  if (upper.contains('LW')) {
    return 'LW';
  }
  if (upper.contains('CF')) {
    return 'CF';
  }
  if (upper.contains('ST')) {
    return 'ST';
  }
  return upper;
}

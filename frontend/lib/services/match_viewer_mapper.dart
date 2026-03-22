import 'dart:math';

import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class MatchViewerMapper {
  MatchViewerMapper._();

  static final GteAppConfig _config = GteAppConfig.fromEnvironment();
  static final GteExchangeApiClient _api = GteExchangeApiClient.standard(
    baseUrl: _config.apiBaseUrl,
    mode: _config.backendMode,
  );

  static Future<MatchViewState> load({
    required CompetitionSummary competition,
    required String matchKey,
    LiveMatchSnapshot? fallbackSnapshot,
    bool preferFallback = false,
  }) async {
    final LiveMatchSnapshot snapshot =
        fallbackSnapshot ?? LiveMatchFixtures.buildSnapshot(competition);
    if (preferFallback || _config.backendMode == GteBackendMode.fixture) {
      return _buildFallbackState(
        competition: competition,
        matchKey: matchKey,
        snapshot: snapshot,
      );
    }

    try {
      final Map<String, Object?> payload =
          await _api.fetchMatchViewer(matchKey);
      return MatchViewState.fromJson(payload);
    } catch (_) {
      return _buildFallbackState(
        competition: competition,
        matchKey: matchKey,
        snapshot: snapshot,
      );
    }
  }

  static MatchViewState _buildFallbackState({
    required CompetitionSummary competition,
    required String matchKey,
    required LiveMatchSnapshot snapshot,
  }) {
    final List<_FallbackPlayer> homePlayers = _buildPlayers(snapshot.homeLineup,
        teamId: 'home',
        teamName: snapshot.homeTeam,
        matchId: matchKey,
        side: MatchViewerSide.home);
    final List<_FallbackPlayer> awayPlayers = _buildPlayers(snapshot.awayLineup,
        teamId: 'away',
        teamName: snapshot.awayTeam,
        matchId: matchKey,
        side: MatchViewerSide.away);
    final int durationSeconds = max(180, (snapshot.minute * 4) + 45);
    final List<MatchEvent> events = _buildFallbackEvents(
      snapshot: snapshot,
      durationSeconds: durationSeconds,
    );
    final List<MatchTimelineFrame> frames = _buildFallbackFrames(
      matchId: matchKey,
      snapshot: snapshot,
      events: events,
      homePlayers: homePlayers,
      awayPlayers: awayPlayers,
      durationSeconds: durationSeconds,
    );

    return MatchViewState(
      matchId: matchKey,
      source: 'fixture_fallback',
      supportsOffside: true,
      deterministicSeed: null,
      durationSeconds: durationSeconds,
      homeTeam: const MatchViewerTeam(
        teamId: 'home',
        teamName: 'Home',
        shortName: 'HOM',
        side: MatchViewerSide.home,
        formation: '4-3-3',
        primaryColorHex: '#173F7A',
        secondaryColorHex: '#F4F7FB',
        accentColorHex: '#F59E0B',
        goalkeeperColorHex: '#0F172A',
      ),
      awayTeam: const MatchViewerTeam(
        teamId: 'away',
        teamName: 'Away',
        shortName: 'AWY',
        side: MatchViewerSide.away,
        formation: '4-3-3',
        primaryColorHex: '#B42318',
        secondaryColorHex: '#FFF3F2',
        accentColorHex: '#FDB022',
        goalkeeperColorHex: '#111827',
      ),
      events: events,
      frames: frames,
    ).copyWithTeamNames(
      homeTeamName: snapshot.homeTeam,
      awayTeamName: snapshot.awayTeam,
    );
  }

  static List<_FallbackPlayer> _buildPlayers(
    List<LiveMatchLineupPlayer> lineup, {
    required String teamId,
    required String teamName,
    required String matchId,
    required MatchViewerSide side,
  }) {
    final List<_FallbackPlayer> players = <_FallbackPlayer>[];
    for (int index = 0; index < min(11, lineup.length); index += 1) {
      final LiveMatchLineupPlayer player = lineup[index];
      players.add(
        _FallbackPlayer(
          id: player.stablePlayerReference(
            teamName: teamName,
            matchId: matchId,
          ),
          teamId: teamId,
          side: side,
          label: '${index + 1}',
          role: _roleFromPosition(player.position, index: index),
        ),
      );
    }
    while (players.length < 11) {
      players.add(
        _FallbackPlayer(
          id: '$teamId-${players.length}',
          teamId: teamId,
          side: side,
          label: '${players.length + 1}',
          role: players.isEmpty
              ? MatchViewerRole.goalkeeper
              : MatchViewerRole.midfielder,
        ),
      );
    }
    return players;
  }

  static MatchViewerRole _roleFromPosition(String position,
      {required int index}) {
    final String normalized = position.trim().toUpperCase();
    if (normalized.contains('GK') || index == 0) {
      return MatchViewerRole.goalkeeper;
    }
    if (normalized.startsWith('D') ||
        normalized.contains('CB') ||
        normalized.contains('FB')) {
      return MatchViewerRole.defender;
    }
    if (normalized.startsWith('F') ||
        normalized.contains('ST') ||
        normalized.contains('W')) {
      return MatchViewerRole.forward;
    }
    return MatchViewerRole.midfielder;
  }

  static List<MatchEvent> _buildFallbackEvents({
    required LiveMatchSnapshot snapshot,
    required int durationSeconds,
  }) {
    final List<LiveMatchEvent> commentary =
        List<LiveMatchEvent>.from(snapshot.commentary)
          ..sort((LiveMatchEvent left, LiveMatchEvent right) =>
              left.minute.compareTo(right.minute));
    final List<MatchEvent> events = <MatchEvent>[
      const MatchEvent(
        id: 'kickoff',
        sequence: 0,
        type: MatchViewerEventType.kickoff,
        minute: 0,
        addedTime: 0,
        clockLabel: '0\'',
        timeSeconds: 0,
        teamId: null,
        teamName: null,
        primaryPlayerId: null,
        primaryPlayerName: null,
        secondaryPlayerId: null,
        secondaryPlayerName: null,
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Kickoff',
        commentary: 'Kickoff',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
    ];

    int homeScore = 0;
    int awayScore = 0;
    final double scale = max(1, snapshot.minute).toDouble();
    for (int index = 0; index < commentary.length; index += 1) {
      final LiveMatchEvent item = commentary[index];
      final MatchViewerEventType type = _viewerTypeFromLiveEvent(item);
      if (type == MatchViewerEventType.goal) {
        if (item.team == snapshot.homeTeam) {
          homeScore += 1;
        } else {
          awayScore += 1;
        }
      }
      events.add(
        MatchEvent(
          id: 'event-$index',
          sequence: index + 1,
          type: type,
          minute: item.minute,
          addedTime: 0,
          clockLabel: '${item.minute}\'',
          timeSeconds: ((item.minute / scale) * (durationSeconds - 20))
              .clamp(8, durationSeconds - 8)
              .toDouble(),
          teamId: item.team == snapshot.homeTeam ? 'home' : 'away',
          teamName: item.team,
          primaryPlayerId: null,
          primaryPlayerName: item.title,
          secondaryPlayerId: null,
          secondaryPlayerName: null,
          homeScore: homeScore,
          awayScore: awayScore,
          bannerText: item.title,
          commentary: item.detail,
          emphasisLevel: _emphasisForType(type),
          highlightedPlayerIds: const <String>[],
          flags: const <String>[],
        ),
      );
    }

    if (snapshot.isHalftime) {
      events.add(
        MatchEvent(
          id: 'halftime',
          sequence: events.length,
          type: MatchViewerEventType.halftime,
          minute: 45,
          addedTime: 0,
          clockLabel: '45\'',
          timeSeconds: (durationSeconds / 2).toDouble(),
          teamId: null,
          teamName: null,
          primaryPlayerId: null,
          primaryPlayerName: null,
          secondaryPlayerId: null,
          secondaryPlayerName: null,
          homeScore: homeScore,
          awayScore: awayScore,
          bannerText: 'Halftime',
          commentary: 'Halftime',
          emphasisLevel: 1,
          highlightedPlayerIds: const <String>[],
          flags: const <String>[],
        ),
      );
    }

    events.add(
      MatchEvent(
        id: 'fulltime',
        sequence: events.length,
        type: MatchViewerEventType.fulltime,
        minute: snapshot.isFinal ? 90 : snapshot.minute,
        addedTime: 0,
        clockLabel: snapshot.isFinal ? '90\'' : '${snapshot.minute}\'',
        timeSeconds: durationSeconds.toDouble(),
        teamId: null,
        teamName: null,
        primaryPlayerId: null,
        primaryPlayerName: null,
        secondaryPlayerId: null,
        secondaryPlayerName: null,
        homeScore: snapshot.homeScore,
        awayScore: snapshot.awayScore,
        bannerText: snapshot.isFinal ? 'Fulltime' : 'Live',
        commentary: snapshot.isFinal ? 'Fulltime' : 'Live match',
        emphasisLevel: 1,
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
    );
    return _normalizeFallbackEvents(
      _ensureFallbackOffsidePlaceholder(
        events: events,
        snapshot: snapshot,
        durationSeconds: durationSeconds,
      ),
    );
  }

  static List<MatchEvent> _ensureFallbackOffsidePlaceholder({
    required List<MatchEvent> events,
    required LiveMatchSnapshot snapshot,
    required int durationSeconds,
  }) {
    if (events.any(
        (MatchEvent event) => event.type == MatchViewerEventType.offside)) {
      return events;
    }

    final int placeholderMinute =
        snapshot.minute <= 6 ? max(1, snapshot.minute) : 6;
    final String teamId =
        snapshot.homeScore > snapshot.awayScore ? 'away' : 'home';
    final String teamName =
        teamId == 'home' ? snapshot.homeTeam : snapshot.awayTeam;
    int homeScore = 0;
    int awayScore = 0;
    for (final MatchEvent event in events) {
      if (event.minute > placeholderMinute) {
        break;
      }
      homeScore = event.homeScore;
      awayScore = event.awayScore;
    }

    return <MatchEvent>[
      ...events,
      MatchEvent(
        id: 'offside-placeholder',
        sequence: events.length,
        type: MatchViewerEventType.offside,
        minute: placeholderMinute,
        addedTime: 0,
        clockLabel: '$placeholderMinute\'',
        timeSeconds: ((placeholderMinute / max(1, snapshot.minute)) *
                (durationSeconds - 20))
            .clamp(8, durationSeconds - 24)
            .toDouble(),
        teamId: teamId,
        teamName: teamName,
        primaryPlayerId: null,
        primaryPlayerName: null,
        secondaryPlayerId: null,
        secondaryPlayerName: null,
        homeScore: homeScore,
        awayScore: awayScore,
        bannerText: 'Offside (data unavailable)',
        commentary:
            'Simulation replay does not yet emit offside events. Viewer placeholder inserted to validate the offside path.',
        emphasisLevel: 2,
        highlightedPlayerIds: const <String>[],
        flags: const <String>['data_unavailable'],
      ),
    ];
  }

  static List<MatchEvent> _normalizeFallbackEvents(List<MatchEvent> events) {
    final List<MatchEvent> ordered = List<MatchEvent>.from(events)
      ..sort((MatchEvent left, MatchEvent right) {
        final int timeCompare = left.timeSeconds.compareTo(right.timeSeconds);
        if (timeCompare != 0) {
          return timeCompare;
        }
        final int minuteCompare = left.minute.compareTo(right.minute);
        if (minuteCompare != 0) {
          return minuteCompare;
        }
        return left.sequence.compareTo(right.sequence);
      });
    return List<MatchEvent>.generate(ordered.length, (int index) {
      final MatchEvent event = ordered[index];
      return MatchEvent(
        id: event.id,
        sequence: index,
        type: event.type,
        minute: event.minute,
        addedTime: event.addedTime,
        clockLabel: event.clockLabel,
        timeSeconds: event.timeSeconds,
        teamId: event.teamId,
        teamName: event.teamName,
        primaryPlayerId: event.primaryPlayerId,
        primaryPlayerName: event.primaryPlayerName,
        secondaryPlayerId: event.secondaryPlayerId,
        secondaryPlayerName: event.secondaryPlayerName,
        homeScore: event.homeScore,
        awayScore: event.awayScore,
        bannerText: event.bannerText,
        commentary: event.commentary,
        emphasisLevel: event.emphasisLevel,
        highlightedPlayerIds: event.highlightedPlayerIds,
        flags: event.flags,
      );
    }, growable: false);
  }

  static MatchViewerEventType _viewerTypeFromLiveEvent(LiveMatchEvent item) {
    if (item.type == LiveMatchEventType.goal) {
      return MatchViewerEventType.goal;
    }
    if (item.type == LiveMatchEventType.substitution) {
      return MatchViewerEventType.substitution;
    }
    if (item.type == LiveMatchEventType.card) {
      return item.detail.toLowerCase().contains('red')
          ? MatchViewerEventType.redCard
          : MatchViewerEventType.yellowCard;
    }
    final String text = '${item.title} ${item.detail}'.toLowerCase();
    if (text.contains('save')) {
      return MatchViewerEventType.save;
    }
    if (text.contains('offside')) {
      return MatchViewerEventType.offside;
    }
    if (text.contains('miss')) {
      return MatchViewerEventType.miss;
    }
    return MatchViewerEventType.attack;
  }

  static int _emphasisForType(MatchViewerEventType type) {
    switch (type) {
      case MatchViewerEventType.goal:
      case MatchViewerEventType.redCard:
        return 3;
      case MatchViewerEventType.save:
      case MatchViewerEventType.miss:
      case MatchViewerEventType.offside:
        return 2;
      default:
        return 1;
    }
  }

  static List<MatchTimelineFrame> _buildFallbackFrames({
    required String matchId,
    required LiveMatchSnapshot snapshot,
    required List<MatchEvent> events,
    required List<_FallbackPlayer> homePlayers,
    required List<_FallbackPlayer> awayPlayers,
    required int durationSeconds,
  }) {
    final List<MatchTimelineFrame> frames = <MatchTimelineFrame>[];
    for (int index = 0; index < events.length; index += 1) {
      final MatchEvent event = events[index];
      final MatchEvent? previousEvent = index == 0 ? null : events[index - 1];
      final double preTime = max(0, event.timeSeconds - 1.4);
      if (index == 0) {
        frames.add(
          _buildFallbackFrame(
            matchId: matchId,
            timeSeconds: 0,
            clockMinute: 0,
            homeScore: 0,
            awayScore: 0,
            phase: MatchViewerPhase.kickoff,
            event: event,
            homePlayers: homePlayers,
            awayPlayers: awayPlayers,
            stage: 'reset',
          ),
        );
      } else if (preTime > frames.last.timeSeconds + 0.1) {
        frames.add(
          _buildFallbackFrame(
            matchId: matchId,
            timeSeconds: preTime,
            clockMinute:
                max(previousEvent?.minute.toDouble() ?? 0, event.minute - 0.25),
            homeScore: previousEvent?.homeScore ?? 0,
            awayScore: previousEvent?.awayScore ?? 0,
            phase: _phaseForEvent(event.type),
            event: event,
            homePlayers: homePlayers,
            awayPlayers: awayPlayers,
            stage: 'pre',
          ),
        );
      }

      frames.add(
        _buildFallbackFrame(
          matchId: matchId,
          timeSeconds: event.timeSeconds,
          clockMinute: event.minute.toDouble(),
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: _phaseForEvent(event.type),
          event: event,
          homePlayers: homePlayers,
          awayPlayers: awayPlayers,
          stage: event.type == MatchViewerEventType.goal
              ? 'event'
              : event.type == MatchViewerEventType.fulltime
                  ? 'post'
                  : 'event',
        ),
      );

      if (event.type == MatchViewerEventType.goal) {
        frames.add(
          _buildFallbackFrame(
            matchId: matchId,
            timeSeconds:
                min(durationSeconds.toDouble(), event.timeSeconds + 1.6),
            clockMinute: event.minute + 0.3,
            homeScore: event.homeScore,
            awayScore: event.awayScore,
            phase: MatchViewerPhase.kickoff,
            event: event,
            homePlayers: homePlayers,
            awayPlayers: awayPlayers,
            stage: 'reset',
          ),
        );
      } else if (event.type != MatchViewerEventType.fulltime) {
        frames.add(
          _buildFallbackFrame(
            matchId: matchId,
            timeSeconds:
                min(durationSeconds.toDouble(), event.timeSeconds + 1.1),
            clockMinute: event.minute + 0.15,
            homeScore: event.homeScore,
            awayScore: event.awayScore,
            phase: _phaseForEvent(event.type),
            event: event,
            homePlayers: homePlayers,
            awayPlayers: awayPlayers,
            stage: 'post',
          ),
        );
      }
    }

    if (frames.isEmpty || frames.last.timeSeconds < durationSeconds) {
      frames.add(
        _buildFallbackFrame(
          matchId: matchId,
          timeSeconds: durationSeconds.toDouble(),
          clockMinute: snapshot.minute.toDouble(),
          homeScore: snapshot.homeScore,
          awayScore: snapshot.awayScore,
          phase: snapshot.isFinal
              ? MatchViewerPhase.fulltime
              : MatchViewerPhase.openPlay,
          event: events.isEmpty ? null : events.last,
          homePlayers: homePlayers,
          awayPlayers: awayPlayers,
          stage: snapshot.isFinal ? 'post' : 'pre',
        ),
      );
    }

    return frames;
  }

  static MatchTimelineFrame _buildFallbackFrame({
    required String matchId,
    required double timeSeconds,
    required double clockMinute,
    required int homeScore,
    required int awayScore,
    required MatchViewerPhase phase,
    required List<_FallbackPlayer> homePlayers,
    required List<_FallbackPlayer> awayPlayers,
    required String stage,
    MatchEvent? event,
  }) {
    final bool homeAttacksRight = clockMinute < 45;
    final MatchViewerSide possessionSide = _possessionSideForFrame(
      event: event,
      stage: stage,
      clockMinute: clockMinute,
    );
    final MatchViewerPoint homeTarget = _eventTarget(
      side: MatchViewerSide.home,
      homeAttacksRight: homeAttacksRight,
      event: event,
    );
    final MatchViewerPoint awayTarget = _eventTarget(
      side: MatchViewerSide.away,
      homeAttacksRight: homeAttacksRight,
      event: event,
    );
    final List<MatchViewerPlayerFrame> players = <MatchViewerPlayerFrame>[
      ..._playerFramesForSide(
        teamId: 'home',
        players: homePlayers,
        homeAttacksRight: homeAttacksRight,
        event: event,
        possessionSide: possessionSide,
        target: homeTarget,
        stage: stage,
      ),
      ..._playerFramesForSide(
        teamId: 'away',
        players: awayPlayers,
        homeAttacksRight: !homeAttacksRight,
        event: event,
        possessionSide: possessionSide,
        target: awayTarget,
        stage: stage,
      ),
    ];
    final List<MatchViewerPlayerFrame> resolvedPlayers =
        _resolveFallbackCollisions(players);
    final MatchViewerBallFrame ball = _ballForFrame(
      event: event,
      players: resolvedPlayers,
      phase: phase,
      homeAttacksRight: homeAttacksRight,
      stage: stage,
    );
    return MatchTimelineFrame(
      id: '$matchId:${(timeSeconds * 100).round()}:$stage',
      timeSeconds: timeSeconds,
      clockMinute: clockMinute,
      phase: phase,
      homeScore: homeScore,
      awayScore: awayScore,
      homeAttacksRight: homeAttacksRight,
      possessionSide: possessionSide,
      activeEventId: stage == 'pre' ? null : event?.id,
      eventBanner: stage == 'pre' ? null : event?.bannerText,
      players: resolvedPlayers,
      ball: ball,
    );
  }

  static MatchViewerSide _possessionSideForFrame({
    required MatchEvent? event,
    required String stage,
    required double clockMinute,
  }) {
    if (stage == 'reset') {
      return clockMinute >= 45 ? MatchViewerSide.away : MatchViewerSide.home;
    }
    return event?.teamId == 'away'
        ? MatchViewerSide.away
        : MatchViewerSide.home;
  }

  static MatchViewerPhase _phaseForEvent(MatchViewerEventType type) {
    switch (type) {
      case MatchViewerEventType.kickoff:
        return MatchViewerPhase.kickoff;
      case MatchViewerEventType.penalty:
      case MatchViewerEventType.setPiece:
        return MatchViewerPhase.setPiece;
      case MatchViewerEventType.halftime:
        return MatchViewerPhase.halftime;
      case MatchViewerEventType.fulltime:
        return MatchViewerPhase.fulltime;
      default:
        return MatchViewerPhase.openPlay;
    }
  }

  static List<MatchViewerPlayerFrame> _playerFramesForSide({
    required String teamId,
    required List<_FallbackPlayer> players,
    required bool homeAttacksRight,
    required MatchViewerSide possessionSide,
    required MatchViewerPoint target,
    required String stage,
    MatchEvent? event,
  }) {
    final List<MatchViewerPoint> anchors =
        _anchors(homeAttacksRight: homeAttacksRight);
    return List<MatchViewerPlayerFrame>.generate(players.length, (int index) {
      final _FallbackPlayer player = players[index];
      final MatchViewerPoint anchor = anchors[index];
      MatchViewerPoint position = anchor;
      MatchViewerPlayerState state = MatchViewerPlayerState.idle;
      final bool ownsPossession = player.side == possessionSide;
      final double direction = homeAttacksRight ? 1 : -1;
      if (stage == 'reset' && index > 0) {
        position = MatchViewerPoint.lerp(
          anchor,
          MatchViewerPoint(
            x: 50 + (homeAttacksRight ? 4 : -4),
            y: 50,
          ),
          player.role == MatchViewerRole.forward ? 0.45 : 0.18,
        );
        state = MatchViewerPlayerState.moving;
      } else {
        final double shapeShift = player.role == MatchViewerRole.goalkeeper
            ? 0
            : ownsPossession
                ? 2.6
                : -1.8;
        position = MatchViewerPoint(
          x: (anchor.x + (shapeShift * direction)).clamp(0, 100).toDouble(),
          y: anchor.y,
        );
        state = ownsPossession
            ? MatchViewerPlayerState.moving
            : MatchViewerPlayerState.defending;
      }
      if (event != null && event.teamId == teamId) {
        final double intensity = stage == 'pre'
            ? 0.22
            : stage == 'event'
                ? 0.52
                : 0.34;
        if (player.role != MatchViewerRole.goalkeeper) {
          position = MatchViewerPoint.lerp(anchor, target, intensity);
          state = player.role == MatchViewerRole.forward
              ? MatchViewerPlayerState.attacking
              : MatchViewerPlayerState.moving;
        }
      } else if (event != null && event.teamId != null) {
        final MatchViewerPoint defendingTarget = MatchViewerPoint(
          x: homeAttacksRight ? anchor.x - 4 : anchor.x + 4,
          y: anchor.y,
        );
        position = MatchViewerPoint.lerp(anchor, defendingTarget, 0.18);
        state = MatchViewerPlayerState.defending;
      }

      return MatchViewerPlayerFrame(
        playerId: player.id,
        teamId: player.teamId,
        side: player.side,
        shirtNumber: index + 1,
        label: player.label,
        role: player.role,
        line: _lineForIndex(index),
        state: event?.type == MatchViewerEventType.redCard &&
                event?.teamId == teamId &&
                index == 6
            ? MatchViewerPlayerState.sentOff
            : state,
        active: !(event?.type == MatchViewerEventType.redCard &&
            stage == 'post' &&
            event?.teamId == teamId &&
            index == 6),
        highlighted: event != null &&
            stage != 'pre' &&
            ((teamId == event.teamId && index == 8) ||
                (event.type == MatchViewerEventType.redCard &&
                    teamId == event.teamId &&
                    index == 6)),
        position: position,
        anchorPosition: anchor,
      );
    });
  }

  static List<MatchViewerPlayerFrame> _resolveFallbackCollisions(
    List<MatchViewerPlayerFrame> players,
  ) {
    final List<MatchViewerPoint> positions = players
        .map((MatchViewerPlayerFrame player) => player.position)
        .toList();
    for (int index = 0; index < players.length; index += 1) {
      for (int otherIndex = index + 1;
          otherIndex < players.length;
          otherIndex += 1) {
        if (players[index].teamId != players[otherIndex].teamId) {
          continue;
        }
        final double deltaX = positions[otherIndex].x - positions[index].x;
        final double deltaY = positions[otherIndex].y - positions[index].y;
        final double distanceSquared = (deltaX * deltaX) + (deltaY * deltaY);
        if (distanceSquared >= 14) {
          continue;
        }
        final double fraction = _stableFraction(
          '${players[index].playerId}:${players[otherIndex].playerId}',
        );
        final double offsetX = (2.4 * fraction) - 1.2;
        final double offsetY = (2.4 * (1 - fraction)) - 1.2;
        positions[index] = MatchViewerPoint(
          x: (positions[index].x - offsetX).clamp(0, 100).toDouble(),
          y: (positions[index].y - offsetY).clamp(0, 100).toDouble(),
        );
        positions[otherIndex] = MatchViewerPoint(
          x: (positions[otherIndex].x + offsetX).clamp(0, 100).toDouble(),
          y: (positions[otherIndex].y + offsetY).clamp(0, 100).toDouble(),
        );
      }
    }
    return List<MatchViewerPlayerFrame>.generate(players.length, (int index) {
      return players[index].copyWith(position: positions[index]);
    }, growable: false);
  }

  static MatchViewerBallFrame _ballForFrame({
    required List<MatchViewerPlayerFrame> players,
    required MatchViewerPhase phase,
    required bool homeAttacksRight,
    required String stage,
    MatchEvent? event,
  }) {
    if (stage == 'reset' || phase == MatchViewerPhase.kickoff) {
      return const MatchViewerBallFrame(
        position: MatchViewerPoint(x: 50, y: 50),
        ownerPlayerId: null,
        state: 'placed',
      );
    }
    final MatchViewerPlayerFrame attacker = players.firstWhere(
      (MatchViewerPlayerFrame player) =>
          player.side ==
              (event?.teamId == 'away'
                  ? MatchViewerSide.away
                  : MatchViewerSide.home) &&
          player.role == MatchViewerRole.forward,
      orElse: () => players.first,
    );
    final MatchViewerPoint attackTarget = MatchViewerPoint(
      x: homeAttacksRight ? 90 : 10,
      y: 50,
    );
    if (event?.type == MatchViewerEventType.goal) {
      return MatchViewerBallFrame(
        position: stage == 'event'
            ? MatchViewerPoint(x: homeAttacksRight ? 96 : 4, y: 50)
            : MatchViewerPoint(x: homeAttacksRight ? 94 : 6, y: 50),
        ownerPlayerId: null,
        state: 'shot',
      );
    }
    if (event?.type == MatchViewerEventType.save) {
      return MatchViewerBallFrame(
        position: stage == 'event'
            ? MatchViewerPoint(x: homeAttacksRight ? 92 : 8, y: 48)
            : MatchViewerPoint(x: homeAttacksRight ? 88 : 12, y: 48),
        ownerPlayerId: null,
        state: 'saved',
      );
    }
    if (event?.type == MatchViewerEventType.miss) {
      return MatchViewerBallFrame(
        position: stage == 'event'
            ? MatchViewerPoint(x: homeAttacksRight ? 97 : 3, y: 10)
            : MatchViewerPoint(x: homeAttacksRight ? 95 : 5, y: 12),
        ownerPlayerId: null,
        state: 'missed',
      );
    }
    if (event?.type == MatchViewerEventType.offside) {
      return MatchViewerBallFrame(
        position: MatchViewerPoint(x: attackTarget.x, y: 40),
        ownerPlayerId: attacker.playerId,
        state: 'stopped',
      );
    }
    return MatchViewerBallFrame(
      position: MatchViewerPoint(
        x: attacker.position.x + 1,
        y: attacker.position.y + 1,
      ),
      ownerPlayerId: attacker.playerId,
      state: 'rolling',
    );
  }

  static MatchViewerPoint _eventTarget({
    required MatchViewerSide side,
    required bool homeAttacksRight,
    MatchEvent? event,
  }) {
    final bool attacksRight =
        side == MatchViewerSide.home ? homeAttacksRight : !homeAttacksRight;
    final double y =
        event == null ? 50 : 26 + ((event.sequence % 5) * 12).toDouble();
    return MatchViewerPoint(
      x: attacksRight ? 86 : 14,
      y: y.clamp(18, 82).toDouble(),
    );
  }

  static List<MatchViewerPoint> _anchors({required bool homeAttacksRight}) {
    final List<double> baseX = homeAttacksRight
        ? <double>[8, 22, 22, 22, 22, 48, 48, 48, 76, 76, 76]
        : <double>[92, 78, 78, 78, 78, 52, 52, 52, 24, 24, 24];
    final List<double> baseY = <double>[
      50,
      18,
      39,
      61,
      82,
      26,
      50,
      74,
      20,
      50,
      80
    ];
    return List<MatchViewerPoint>.generate(
      11,
      (int index) => MatchViewerPoint(x: baseX[index], y: baseY[index]),
      growable: false,
    );
  }

  static MatchPlayerLine _lineForIndex(int index) {
    if (index == 0) {
      return MatchPlayerLine.goalkeeper;
    }
    if (index <= 4) {
      return MatchPlayerLine.defense;
    }
    if (index <= 7) {
      return MatchPlayerLine.midfield;
    }
    return MatchPlayerLine.attack;
  }

  static double _stableFraction(String seed) {
    int hash = 2166136261;
    for (final int codeUnit in seed.codeUnits) {
      hash ^= codeUnit;
      hash = (hash * 16777619) & 0x7fffffff;
    }
    return hash / 0x7fffffff;
  }
}

class _FallbackPlayer {
  const _FallbackPlayer({
    required this.id,
    required this.teamId,
    required this.side,
    required this.label,
    required this.role,
  });

  final String id;
  final String teamId;
  final MatchViewerSide side;
  final String label;
  final MatchViewerRole role;
}

extension on MatchViewState {
  MatchViewState copyWithTeamNames({
    required String homeTeamName,
    required String awayTeamName,
  }) {
    return MatchViewState(
      matchId: matchId,
      source: source,
      supportsOffside: supportsOffside,
      deterministicSeed: deterministicSeed,
      durationSeconds: durationSeconds,
      homeTeam: MatchViewerTeam(
        teamId: homeTeam.teamId,
        teamName: homeTeamName,
        shortName: homeTeamName.length >= 3
            ? homeTeamName.substring(0, 3).toUpperCase()
            : homeTeamName.toUpperCase(),
        side: homeTeam.side,
        formation: homeTeam.formation,
        primaryColorHex: homeTeam.primaryColorHex,
        secondaryColorHex: homeTeam.secondaryColorHex,
        accentColorHex: homeTeam.accentColorHex,
        goalkeeperColorHex: homeTeam.goalkeeperColorHex,
      ),
      awayTeam: MatchViewerTeam(
        teamId: awayTeam.teamId,
        teamName: awayTeamName,
        shortName: awayTeamName.length >= 3
            ? awayTeamName.substring(0, 3).toUpperCase()
            : awayTeamName.toUpperCase(),
        side: awayTeam.side,
        formation: awayTeam.formation,
        primaryColorHex: awayTeam.primaryColorHex,
        secondaryColorHex: awayTeam.secondaryColorHex,
        accentColorHex: awayTeam.accentColorHex,
        goalkeeperColorHex: awayTeam.goalkeeperColorHex,
      ),
      events: events,
      frames: frames,
    );
  }
}

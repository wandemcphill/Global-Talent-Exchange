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
    MatchMode mode = MatchMode.standard,
    LiveMatchSnapshot? fallbackSnapshot,
    bool preferFallback = false,
  }) async {
    final LiveMatchSnapshot snapshot =
        fallbackSnapshot ?? LiveMatchFixtures.buildSnapshot(competition);
    if (preferFallback || _config.backendMode == GteBackendMode.fixture) {
      return _applyLocalModeScaling(
        _buildFallbackState(
          matchKey: matchKey,
          snapshot: snapshot,
        ),
        mode: mode,
      );
    }

    final Map<String, Object?> payload = await _api.fetchMatchViewerSession(
      matchKey,
      mode: mode,
    );
    return MatchViewState.fromJson(payload);
  }

  static Future<MatchViewState> loadContinuation({
    required String matchKey,
    required String continuationToken,
    MatchMode mode = MatchMode.standard,
  }) async {
    final Map<String, Object?> payload = await _api.fetchMatchViewerSession(
      matchKey,
      mode: mode,
      continuationToken: continuationToken,
    );
    return MatchViewState.fromJson(payload);
  }

  static MatchViewState _buildFallbackState({
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
      matchMode: MatchMode.standard,
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

  static MatchViewState _applyLocalModeScaling(
    MatchViewState viewState, {
    required MatchMode mode,
  }) {
    final double baseDuration = max(
      1,
      max(
        viewState.durationSeconds.toDouble(),
        max(
          viewState.events.isEmpty ? 0 : viewState.events.last.timeSeconds,
          viewState.frames.isEmpty ? 0 : viewState.frames.last.timeSeconds,
        ),
      ),
    ).toDouble();
    final int targetDuration = _targetDurationForMode(viewState, mode: mode);
    final List<MatchEvent> events = _scaleEvents(
      viewState.events,
      baseDuration: baseDuration,
      targetDuration: targetDuration,
      mode: mode,
    );
    final Map<String, MatchEvent> eventLookup = <String, MatchEvent>{
      for (final MatchEvent event in events) event.id: event,
    };
    final List<MatchTimelineFrame> frames = _normalizeFrames(
      _scaleFrames(
        viewState.frames,
        baseDuration: baseDuration,
        targetDuration: targetDuration,
        matchId: viewState.matchId,
        eventLookup: eventLookup,
        mode: mode,
      ),
      matchId: viewState.matchId,
      targetDuration: targetDuration,
    );
    return viewState.copyWith(
      matchMode: mode,
      durationSeconds: targetDuration,
      events: events,
      frames: frames,
    );
  }

  static int _targetDurationForMode(
    MatchViewState viewState, {
    required MatchMode mode,
  }) {
    final (int minimum, int maximum) = switch (mode) {
      MatchMode.quick => (180, 300),
      MatchMode.standard => (420, 600),
      MatchMode.cinematic => (600, 900),
    };
    double richness = min(viewState.frames.length / 80, 1.0);
    for (final MatchEvent event in viewState.events) {
      richness += 0.2;
      richness += switch (event.type) {
        MatchViewerEventType.goal => 1.4,
        MatchViewerEventType.save => 1.1,
        MatchViewerEventType.miss => 1.1,
        MatchViewerEventType.offside => 0.8,
        MatchViewerEventType.redCard => 1.2,
        MatchViewerEventType.yellowCard => 0.6,
        MatchViewerEventType.substitution => 0.55,
        MatchViewerEventType.injury => 0.75,
        MatchViewerEventType.attack => 0.85,
        MatchViewerEventType.setPiece => 0.95,
        MatchViewerEventType.penalty => 1.15,
        MatchViewerEventType.kickoff ||
        MatchViewerEventType.halftime ||
        MatchViewerEventType.fulltime =>
          0.15,
        MatchViewerEventType.foul => 0.7,
        MatchViewerEventType.neutral => 0.45,
      };
      richness += max(0, event.emphasisLevel - 1) * 0.15;
    }
    final double normalized = ((richness - 6.0) / 10.0).clamp(0.0, 1.0);
    return (minimum + ((maximum - minimum) * normalized)).round();
  }

  static List<MatchEvent> _scaleEvents(
    List<MatchEvent> events, {
    required double baseDuration,
    required int targetDuration,
    required MatchMode mode,
  }) {
    final double minimumGap = switch (mode) {
      MatchMode.quick => 0.35,
      MatchMode.standard => 0.45,
      MatchMode.cinematic => 0.55,
    };
    final List<MatchEvent> scaled = <MatchEvent>[];
    double previousTime = -minimumGap;
    for (int index = 0; index < events.length; index += 1) {
      final MatchEvent event = events[index];
      double timeSeconds = event.type == MatchViewerEventType.kickoff
          ? 0
          : event.type == MatchViewerEventType.fulltime
              ? targetDuration.toDouble()
              : ((event.timeSeconds / baseDuration) * targetDuration)
                  .clamp(0, targetDuration)
                  .toDouble();
      if (timeSeconds <= previousTime) {
        timeSeconds = previousTime + minimumGap;
      }
      scaled.add(event.copyWith(
          timeSeconds: double.parse(timeSeconds.toStringAsFixed(2))));
      previousTime = scaled.last.timeSeconds;
    }
    return scaled;
  }

  static List<MatchTimelineFrame> _scaleFrames(
    List<MatchTimelineFrame> frames, {
    required double baseDuration,
    required int targetDuration,
    required String matchId,
    required Map<String, MatchEvent> eventLookup,
    required MatchMode mode,
  }) {
    final List<MatchTimelineFrame> scaled = <MatchTimelineFrame>[];
    for (final MatchTimelineFrame frame in frames) {
      if (mode == MatchMode.quick && !_keepQuickFrame(frame, eventLookup)) {
        continue;
      }
      final double timeSeconds =
          ((frame.timeSeconds / baseDuration) * targetDuration)
              .clamp(0, targetDuration)
              .toDouble();
      final String? activeEventId = eventLookup.containsKey(frame.activeEventId)
          ? frame.activeEventId
          : null;
      final String stage = _frameStage(frame.id);
      scaled.add(
        frame.copyWith(
          id: '$matchId:${(timeSeconds * 100).round()}:$stage',
          timeSeconds: double.parse(timeSeconds.toStringAsFixed(2)),
          activeEventId: activeEventId,
          eventBanner: activeEventId == null
              ? null
              : eventLookup[activeEventId]?.bannerText,
        ),
      );
    }
    return scaled;
  }

  static bool _keepQuickFrame(
    MatchTimelineFrame frame,
    Map<String, MatchEvent> eventLookup,
  ) {
    final String stage = _frameStage(frame.id);
    if (stage == 'event' || stage == 'reset') {
      return true;
    }
    final MatchEvent? event = eventLookup[frame.activeEventId];
    if (stage == 'post') {
      return event != null &&
          <MatchViewerEventType>{
            MatchViewerEventType.fulltime,
            MatchViewerEventType.goal,
            MatchViewerEventType.halftime,
            MatchViewerEventType.redCard,
          }.contains(event.type);
    }
    if (stage == 'pre') {
      return event != null &&
          <MatchViewerEventType>{
            MatchViewerEventType.fulltime,
            MatchViewerEventType.goal,
            MatchViewerEventType.halftime,
            MatchViewerEventType.kickoff,
          }.contains(event.type);
    }
    return false;
  }

  static List<MatchTimelineFrame> _normalizeFrames(
    List<MatchTimelineFrame> frames, {
    required String matchId,
    required int targetDuration,
  }) {
    if (frames.isEmpty) {
      return frames;
    }
    final List<MatchTimelineFrame> ordered =
        List<MatchTimelineFrame>.from(frames)
          ..sort((MatchTimelineFrame left, MatchTimelineFrame right) =>
              left.timeSeconds.compareTo(right.timeSeconds));
    final List<MatchTimelineFrame> normalized = <MatchTimelineFrame>[];
    for (final MatchTimelineFrame frame in ordered) {
      double timeSeconds =
          frame.timeSeconds.clamp(0, targetDuration).toDouble();
      if (normalized.isNotEmpty && timeSeconds <= normalized.last.timeSeconds) {
        timeSeconds = (normalized.last.timeSeconds + 0.05)
            .clamp(0, targetDuration)
            .toDouble();
      }
      final String stage = _frameStage(frame.id);
      normalized.add(
        frame.copyWith(
          id: '$matchId:${(timeSeconds * 100).round()}:$stage',
          timeSeconds: double.parse(timeSeconds.toStringAsFixed(2)),
        ),
      );
    }
    if (normalized.first.timeSeconds > 0) {
      normalized.insert(
        0,
        normalized.first.copyWith(
          id: '$matchId:0:reset',
          timeSeconds: 0,
        ),
      );
    }
    if (normalized.last.timeSeconds < targetDuration) {
      normalized.add(
        normalized.last.copyWith(
          id: '$matchId:${targetDuration * 100}:post',
          timeSeconds: targetDuration.toDouble(),
        ),
      );
    }
    return normalized;
  }

  static String _frameStage(String frameId) {
    final int separator = frameId.lastIndexOf(':');
    if (separator < 0 || separator == frameId.length - 1) {
      return 'event';
    }
    return frameId.substring(separator + 1).trim().toLowerCase();
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
    double secondForMinute(int minute) {
      return ((minute / 90) * (durationSeconds - 18))
          .clamp(0, durationSeconds)
          .toDouble();
    }

    final List<MatchEvent> events = <MatchEvent>[
      const MatchEvent(
        id: 'kickoff',
        sequence: 0,
        type: MatchViewerEventType.kickoff,
        minute: 0,
        addedTime: 0,
        clockLabel: '0\'',
        timeSeconds: 0,
        homeScore: 0,
        awayScore: 0,
        bannerText: 'Kickoff',
        commentary: 'Kickoff',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
      MatchEvent(
        id: 'goal-var-confirmed',
        sequence: 1,
        type: MatchViewerEventType.goal,
        minute: 18,
        addedTime: 0,
        clockLabel: '18\'',
        timeSeconds: secondForMinute(18),
        teamId: 'home',
        teamName: snapshot.homeTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Goal review',
        commentary: 'The finish is checked and confirmed by VAR.',
        emphasisLevel: 3,
        playbackProfile: 'goal',
        reviewable: true,
        reviewReason: 'possible offside in the build-up',
        reviewDecision: 'confirmed',
        scoreCommit: 'after_review',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'foul-var-disallowed',
        sequence: 2,
        type: MatchViewerEventType.foul,
        minute: 34,
        addedTime: 0,
        clockLabel: '34\'',
        timeSeconds: secondForMinute(34),
        teamId: 'away',
        teamName: snapshot.awayTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Foul review',
        commentary: 'VAR overturns the foul call and play resumes.',
        emphasisLevel: 2,
        playbackProfile: 'foul',
        reviewable: true,
        reviewReason: 'possible foul in the challenge',
        reviewDecision: 'disallowed',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'yellow-card',
        sequence: 3,
        type: MatchViewerEventType.yellowCard,
        minute: 41,
        addedTime: 0,
        clockLabel: '41\'',
        timeSeconds: secondForMinute(41),
        teamId: 'away',
        teamName: snapshot.awayTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Yellow card',
        commentary: 'The challenge earns a booking.',
        emphasisLevel: 2,
        playbackProfile: 'foul',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'halftime',
        sequence: 4,
        type: MatchViewerEventType.halftime,
        minute: 45,
        addedTime: 0,
        clockLabel: '45\'',
        timeSeconds: secondForMinute(45),
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Halftime',
        commentary: 'Halftime',
        emphasisLevel: 1,
        highlightedPlayerIds: <String>[],
        flags: <String>[],
      ),
      MatchEvent(
        id: 'offside',
        sequence: 5,
        type: MatchViewerEventType.offside,
        minute: 58,
        addedTime: 0,
        clockLabel: '58\'',
        timeSeconds: secondForMinute(58),
        teamId: 'away',
        teamName: snapshot.awayTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Offside',
        commentary: 'The move is flagged offside after the shot attempt.',
        emphasisLevel: 2,
        playbackProfile: 'offside',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'save-miss',
        sequence: 6,
        type: MatchViewerEventType.save,
        minute: 67,
        addedTime: 0,
        clockLabel: '67\'',
        timeSeconds: secondForMinute(67),
        teamId: 'home',
        teamName: snapshot.homeTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Saved chance',
        commentary: 'The goalkeeper pushes the effort away.',
        emphasisLevel: 2,
        playbackProfile: 'attack',
        missVariant: 'save',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'post-miss',
        sequence: 7,
        type: MatchViewerEventType.miss,
        minute: 74,
        addedTime: 0,
        clockLabel: '74\'',
        timeSeconds: secondForMinute(74),
        teamId: 'away',
        teamName: snapshot.awayTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Hits the post',
        commentary: 'The effort crashes back off the upright.',
        emphasisLevel: 2,
        playbackProfile: 'attack',
        missVariant: 'post',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'wide-miss',
        sequence: 8,
        type: MatchViewerEventType.miss,
        minute: 79,
        addedTime: 0,
        clockLabel: '79\'',
        timeSeconds: secondForMinute(79),
        teamId: 'home',
        teamName: snapshot.homeTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Wide chance',
        commentary: 'The chance drifts wide of the target.',
        emphasisLevel: 2,
        playbackProfile: 'attack',
        missVariant: 'wide',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'red-card',
        sequence: 9,
        type: MatchViewerEventType.redCard,
        minute: 83,
        addedTime: 0,
        clockLabel: '83\'',
        timeSeconds: secondForMinute(83),
        teamId: 'home',
        teamName: snapshot.homeTeam,
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Red card',
        commentary: 'The challenge leaves the referee with no choice.',
        emphasisLevel: 3,
        playbackProfile: 'foul',
        scoreCommit: 'never',
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
      MatchEvent(
        id: 'fulltime',
        sequence: 10,
        type: MatchViewerEventType.fulltime,
        minute: 90,
        addedTime: 0,
        clockLabel: '90\'',
        timeSeconds: durationSeconds.toDouble(),
        homeScore: 1,
        awayScore: 0,
        bannerText: 'Fulltime',
        commentary: 'Fulltime',
        emphasisLevel: 1,
        highlightedPlayerIds: const <String>[],
        flags: const <String>[],
      ),
    ];
    return _normalizeFallbackEvents(events);
  }

  // ignore: unused_element
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
        playbackProfile: event.playbackProfile,
        missVariant: event.missVariant,
        reviewable: event.reviewable,
        reviewReason: event.reviewReason,
        reviewDecision: event.reviewDecision,
        scoreCommit: event.scoreCommit,
        highlightedPlayerIds: event.highlightedPlayerIds,
        flags: event.flags,
      );
    }, growable: false);
  }

  // ignore: unused_element
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
    if (text.contains('foul')) {
      return MatchViewerEventType.foul;
    }
    if (text.contains('miss')) {
      return MatchViewerEventType.miss;
    }
    return MatchViewerEventType.attack;
  }

  // ignore: unused_element
  static int _emphasisForType(MatchViewerEventType type) {
    switch (type) {
      case MatchViewerEventType.goal:
      case MatchViewerEventType.redCard:
        return 3;
      case MatchViewerEventType.save:
      case MatchViewerEventType.miss:
      case MatchViewerEventType.offside:
      case MatchViewerEventType.foul:
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
    double lastTime = 0;

    void appendFrame({
      required double timeSeconds,
      required double clockMinute,
      required int homeScore,
      required int awayScore,
      required MatchViewerPhase phase,
      required String stage,
      required MatchCameraPreset cameraPreset,
      String? overlayText,
      bool pausePlayback = false,
      double playbackRate = 1,
      bool flagAnimation = false,
      String? celebrationTeamId,
      MatchEvent? event,
    }) {
      final double resolvedTime = frames.isEmpty
          ? timeSeconds
          : max(timeSeconds, lastTime + 0.05).toDouble();
      frames.add(
        _buildFallbackFrame(
          matchId: matchId,
          timeSeconds: resolvedTime,
          clockMinute: clockMinute,
          homeScore: homeScore,
          awayScore: awayScore,
          phase: phase,
          event: event,
          homePlayers: homePlayers,
          awayPlayers: awayPlayers,
          stage: stage,
          cameraPreset: cameraPreset,
          overlayText: overlayText,
          pausePlayback: pausePlayback,
          playbackRate: playbackRate,
          flagAnimation: flagAnimation,
          celebrationTeamId: celebrationTeamId,
        ),
      );
      lastTime = frames.last.timeSeconds;
    }

    for (final MatchEvent event in events) {
      final int priorHomeScore = frames.isEmpty ? 0 : frames.last.homeScore;
      final int priorAwayScore = frames.isEmpty ? 0 : frames.last.awayScore;
      final MatchViewerPhase phase = _phaseForEvent(event.type);
      final double buildUp = event.playbackProfile == 'foul' ||
              event.type == MatchViewerEventType.foul ||
              event.type == MatchViewerEventType.yellowCard ||
              event.type == MatchViewerEventType.redCard
          ? 1.6
          : event.type == MatchViewerEventType.goal ||
                  event.type == MatchViewerEventType.save ||
                  event.type == MatchViewerEventType.miss ||
                  event.type == MatchViewerEventType.offside
              ? 2.2
              : 1.1;

      if (frames.isEmpty) {
        appendFrame(
          timeSeconds: 0,
          clockMinute: 0,
          homeScore: 0,
          awayScore: 0,
          phase: MatchViewerPhase.kickoff,
          stage: 'reset',
          cameraPreset: MatchCameraPreset.broadcast,
          event: event,
        );
      }

      if (event.type == MatchViewerEventType.kickoff) {
        continue;
      }

      final double preTime = max(lastTime + 0.4, event.timeSeconds - buildUp);
      if (preTime > lastTime + 0.1) {
        appendFrame(
          timeSeconds: preTime,
          clockMinute: max(0, event.minute - 0.25).toDouble(),
          homeScore: priorHomeScore,
          awayScore: priorAwayScore,
          phase: phase,
          stage: 'pre',
          cameraPreset: event.type == MatchViewerEventType.foul ||
                  event.type == MatchViewerEventType.yellowCard ||
                  event.type == MatchViewerEventType.redCard
              ? MatchCameraPreset.broadcast
              : MatchCameraPreset.attackPush,
          event: event,
        );
      }

      appendFrame(
        timeSeconds: max(event.timeSeconds, lastTime + 0.1),
        clockMinute: event.minute.toDouble(),
        homeScore: event.type == MatchViewerEventType.goal
            ? priorHomeScore
            : event.homeScore,
        awayScore: event.type == MatchViewerEventType.goal
            ? priorAwayScore
            : event.awayScore,
        phase: phase,
        stage: 'event',
        cameraPreset: event.type == MatchViewerEventType.goal ||
                event.type == MatchViewerEventType.save ||
                event.type == MatchViewerEventType.miss ||
                event.type == MatchViewerEventType.offside ||
                event.type == MatchViewerEventType.foul ||
                event.type == MatchViewerEventType.yellowCard ||
                event.type == MatchViewerEventType.redCard
            ? MatchCameraPreset.boxZoom
            : MatchCameraPreset.broadcast,
        event: event,
      );

      if (event.type == MatchViewerEventType.goal) {
        appendFrame(
          timeSeconds: lastTime + 0.6,
          clockMinute: event.minute.toDouble(),
          homeScore: priorHomeScore,
          awayScore: priorAwayScore,
          phase: phase,
          stage: 'hold',
          cameraPreset: MatchCameraPreset.boxZoom,
          overlayText: event.reviewable ? 'Checking...' : null,
          pausePlayback: event.reviewable,
          event: event,
        );
        if (event.reviewable) {
          appendFrame(
            timeSeconds: lastTime + 2.4,
            clockMinute: event.minute.toDouble(),
            homeScore: priorHomeScore,
            awayScore: priorAwayScore,
            phase: phase,
            stage: 'review',
            cameraPreset: MatchCameraPreset.varReplay,
            overlayText: 'Checking...',
            playbackRate: 0.35,
            event: event,
          );
        }
        appendFrame(
          timeSeconds: lastTime + 1.0,
          clockMinute: event.minute + 0.05,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: phase,
          stage: 'decision',
          cameraPreset: MatchCameraPreset.goalCelebration,
          overlayText: event.reviewable ? 'Confirmed' : 'GOAL',
          celebrationTeamId: event.teamId,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 1.8,
          clockMinute: event.minute + 0.12,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: phase,
          stage: 'post',
          cameraPreset: MatchCameraPreset.goalCelebration,
          celebrationTeamId: event.teamId,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 0.8,
          clockMinute: event.minute + 0.2,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.kickoff,
          stage: 'reset',
          cameraPreset: MatchCameraPreset.broadcast,
          event: event,
        );
      } else if (event.type == MatchViewerEventType.foul) {
        appendFrame(
          timeSeconds: lastTime + 1.2,
          clockMinute: event.minute.toDouble(),
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.setPiece,
          stage: 'hold',
          cameraPreset: MatchCameraPreset.boxZoom,
          overlayText: 'Checking...',
          pausePlayback: true,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 2.4,
          clockMinute: event.minute.toDouble(),
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.setPiece,
          stage: 'review',
          cameraPreset: MatchCameraPreset.varReplay,
          overlayText: 'Checking...',
          playbackRate: 0.35,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 1.0,
          clockMinute: event.minute + 0.04,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.setPiece,
          stage: 'decision',
          cameraPreset: MatchCameraPreset.broadcast,
          overlayText:
              event.reviewDecision == 'confirmed' ? 'Confirmed' : 'Disallowed',
          pausePlayback: true,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 0.8,
          clockMinute: event.minute + 0.1,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.openPlay,
          stage: 'reset',
          cameraPreset: MatchCameraPreset.broadcast,
          event: event,
        );
      } else if (event.type == MatchViewerEventType.offside) {
        appendFrame(
          timeSeconds: lastTime + 0.6,
          clockMinute: event.minute.toDouble(),
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: phase,
          stage: 'hold',
          cameraPreset: MatchCameraPreset.assistantFlag,
          pausePlayback: true,
          flagAnimation: true,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 1.4,
          clockMinute: event.minute + 0.05,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: phase,
          stage: 'decision',
          cameraPreset: MatchCameraPreset.assistantFlag,
          overlayText: 'OFFSIDE',
          pausePlayback: true,
          flagAnimation: true,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 0.8,
          clockMinute: event.minute + 0.12,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.openPlay,
          stage: 'reset',
          cameraPreset: MatchCameraPreset.broadcast,
          event: event,
        );
      } else if (event.type == MatchViewerEventType.yellowCard ||
          event.type == MatchViewerEventType.redCard) {
        appendFrame(
          timeSeconds: lastTime + 0.9,
          clockMinute: event.minute + 0.05,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: phase,
          stage: 'post',
          cameraPreset: MatchCameraPreset.boxZoom,
          overlayText: event.type == MatchViewerEventType.redCard
              ? 'RED CARD'
              : 'YELLOW CARD',
          pausePlayback: true,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 0.8,
          clockMinute: event.minute + 0.1,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.openPlay,
          stage: 'reset',
          cameraPreset: MatchCameraPreset.broadcast,
          event: event,
        );
      } else if (event.type == MatchViewerEventType.halftime) {
        appendFrame(
          timeSeconds: lastTime + 1.0,
          clockMinute: 45,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.halftime,
          stage: 'post',
          cameraPreset: MatchCameraPreset.broadcast,
          overlayText: 'HALFTIME',
          pausePlayback: true,
          event: event,
        );
        appendFrame(
          timeSeconds: lastTime + 1.4,
          clockMinute: 45.1,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: MatchViewerPhase.kickoff,
          stage: 'reset',
          cameraPreset: MatchCameraPreset.broadcast,
          event: event,
        );
      } else if (event.type != MatchViewerEventType.fulltime) {
        appendFrame(
          timeSeconds: lastTime + 1.1,
          clockMinute: event.minute + 0.12,
          homeScore: event.homeScore,
          awayScore: event.awayScore,
          phase: phase,
          stage: 'post',
          cameraPreset: event.type == MatchViewerEventType.save ||
                  event.type == MatchViewerEventType.miss
              ? MatchCameraPreset.boxZoom
              : MatchCameraPreset.broadcast,
          event: event,
        );
      }
    }

    if (frames.isEmpty || frames.last.timeSeconds < durationSeconds) {
      appendFrame(
        timeSeconds: durationSeconds.toDouble(),
        clockMinute: 90,
        homeScore: events.last.homeScore,
        awayScore: events.last.awayScore,
        phase: MatchViewerPhase.fulltime,
        stage: 'post',
        cameraPreset: MatchCameraPreset.broadcast,
        event: events.last,
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
    required MatchCameraPreset cameraPreset,
    String? overlayText,
    bool pausePlayback = false,
    double playbackRate = 1,
    bool flagAnimation = false,
    String? celebrationTeamId,
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
      stage: matchPlaybackStageFromString(stage),
      cameraPreset: cameraPreset,
      overlayText: overlayText,
      pausePlayback: pausePlayback,
      playbackRate: playbackRate,
      flagAnimation: flagAnimation,
      celebrationTeamId: celebrationTeamId,
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
    return copyWith(
      homeTeam: homeTeam.copyWith(
        teamName: homeTeamName,
        shortName: homeTeamName.length >= 3
            ? homeTeamName.substring(0, 3).toUpperCase()
            : homeTeamName.toUpperCase(),
      ),
      awayTeam: awayTeam.copyWith(
        teamName: awayTeamName,
        shortName: awayTeamName.length >= 3
            ? awayTeamName.substring(0, 3).toUpperCase()
            : awayTeamName.toUpperCase(),
      ),
    );
  }
}

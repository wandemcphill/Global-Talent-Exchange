import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';

void main() {
  test('player frame parser preserves enriched backend animation states', () {
    expect(
      MatchViewerPlayerFrame.fromJson(
        _playerFrameJson('celebrate'),
      ).animationState,
      MatchPlayerAnimationState.celebrate,
    );
    expect(
      MatchViewerPlayerFrame.fromJson(
        _playerFrameJson('set_piece'),
      ).animationState,
      MatchPlayerAnimationState.setPiece,
    );
    expect(
      MatchViewerPlayerFrame.fromJson(_playerFrameJson('press')).animationState,
      MatchPlayerAnimationState.press,
    );
    expect(
      MatchViewerPlayerFrame.fromJson(_playerFrameJson('save')).animationState,
      MatchPlayerAnimationState.save,
    );
    expect(
      MatchViewerPlayerFrame.fromJson(
        _playerFrameJson('sent_off'),
      ).animationState,
      MatchPlayerAnimationState.sentOff,
    );
  });

  test(
    'timeline frame parser preserves enriched backend possession phases',
    () {
      expect(
        matchPossessionPhaseFromString('transition'),
        MatchPossessionPhase.transition,
      );
      expect(
        matchPossessionPhaseFromString('final_third'),
        MatchPossessionPhase.finalThird,
      );
      expect(
        matchPossessionPhaseFromString('box_attack'),
        MatchPossessionPhase.boxAttack,
      );
      expect(
        matchPossessionPhaseFromString('set_piece'),
        MatchPossessionPhase.setPiece,
      );
      expect(
        matchPossessionPhaseFromString('dead_ball'),
        MatchPossessionPhase.deadBall,
      );
    },
  );

  test('timeline frame parser preserves backend frame telemetry', () {
    final MatchTimelineFrame frame = MatchTimelineFrame.fromJson(
      <String, Object?>{
        'frame_id': 'frame-1',
        'time_seconds': 12.5,
        'clock_minute': 19.2,
        'phase': 'open_play',
        'home_score': 1,
        'away_score': 0,
        'home_attacks_right': true,
        'possession_side': 'home',
        'possession_phase': 'box_attack',
        'transition_state': 'home_break',
        'danger_zone': 'box',
        'pressure_index': 0.84,
        'compactness_home': 0.63,
        'compactness_away': 0.41,
        'frame_tags': <String>['counter', 'box_entry'],
        'players': <Map<String, Object?>>[_playerFrameJson('sprint')],
        'ball': <String, Object?>{
          'position': <String, Object?>{'x': 82.0, 'y': 43.0},
          'owner_player_id': 'p-1',
          'state': 'rolling',
        },
      },
    );

    expect(frame.possessionPhase, MatchPossessionPhase.boxAttack);
    expect(frame.transitionState, MatchTransitionState.homeBreak);
    expect(frame.dangerZone, 'box');
    expect(frame.pressureIndex, closeTo(0.84, 0.0001));
    expect(frame.compactnessHome, closeTo(0.63, 0.0001));
    expect(frame.compactnessAway, closeTo(0.41, 0.0001));
    expect(frame.frameTags, containsAll(<String>['counter', 'box_entry']));
  });

  test('timeline frame interpolation preserves backend telemetry cues', () {
    final MatchViewerPlayerFrame player = MatchViewerPlayerFrame.fromJson(
      _playerFrameJson('run'),
    );
    final MatchTimelineFrame left = MatchTimelineFrame(
      id: 'left',
      timeSeconds: 10,
      clockMinute: 14,
      phase: MatchViewerPhase.openPlay,
      homeScore: 0,
      awayScore: 0,
      homeAttacksRight: true,
      possessionSide: MatchViewerSide.home,
      possessionPhase: MatchPossessionPhase.transition,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'final_third',
      pressureIndex: 0.58,
      compactnessHome: 0.61,
      compactnessAway: 0.47,
      frameTags: const <String>['counter'],
      players: <MatchViewerPlayerFrame>[player],
      ball: const MatchViewerBallFrame(
        position: MatchViewerPoint(x: 64, y: 44),
        ownerPlayerId: 'p-1',
        state: 'rolling',
      ),
    );
    final MatchTimelineFrame right = MatchTimelineFrame(
      id: 'right',
      timeSeconds: 11,
      clockMinute: 15,
      phase: MatchViewerPhase.openPlay,
      homeScore: 0,
      awayScore: 0,
      homeAttacksRight: true,
      possessionSide: MatchViewerSide.home,
      possessionPhase: MatchPossessionPhase.boxAttack,
      transitionState: MatchTransitionState.homeBreak,
      dangerZone: 'box',
      pressureIndex: 0.92,
      compactnessHome: 0.68,
      compactnessAway: 0.38,
      frameTags: const <String>['box_entry'],
      players: <MatchViewerPlayerFrame>[
        player.copyWith(position: const MatchViewerPoint(x: 72, y: 42)),
      ],
      ball: const MatchViewerBallFrame(
        position: MatchViewerPoint(x: 76, y: 41),
        ownerPlayerId: 'p-1',
        state: 'rolling',
      ),
    );

    final MatchTimelineFrame interpolated = left.interpolate(right, 0.5);

    expect(interpolated.transitionState, MatchTransitionState.homeBreak);
    expect(interpolated.dangerZone, 'box');
    expect(interpolated.pressureIndex, closeTo(0.75, 0.0001));
    expect(interpolated.compactnessHome, closeTo(0.645, 0.0001));
    expect(interpolated.compactnessAway, closeTo(0.425, 0.0001));
    expect(
      interpolated.frameTags,
      containsAll(<String>['counter', 'box_entry']),
    );
  });
}

Map<String, Object?> _playerFrameJson(String animationState) {
  return <String, Object?>{
    'player_id': 'p-1',
    'team_id': 'team-1',
    'side': 'home',
    'label': '9',
    'role': 'forward',
    'line': 'attack',
    'state': 'attacking',
    'active': true,
    'highlighted': true,
    'position': <String, Object?>{'x': 55.0, 'y': 42.0},
    'anchor_position': <String, Object?>{'x': 52.0, 'y': 40.0},
    'animation_state': animationState,
    'speed_ratio': 0.82,
    'blend_factor': 0.61,
    'stamina_pct': 74,
  };
}

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/compete/compete.dart';

void main() {
  group('CompetitionBracketPayload', () {
    test('parses nested backend bracket payload without reordering nodes', () {
      final CompetitionBracketPayload
      payload = CompetitionBracketPayload.fromJson(<String, Object?>{
        'competition_id': 'comp-42',
        'title': 'GTEX Sunday Cup',
        'lifecycle': <String, Object?>{
          'stage': 'in_progress',
          'bracket_published': true,
          'updated_at': '2026-05-28T20:00:00Z',
        },
        'bracket': <String, Object?>{
          'id': 'bracket-42',
          'revision': 'rev-7',
          'rounds': <Object?>[
            <String, Object?>{
              'id': 'round-final',
              'name': 'Final',
              'order': 2,
              'status': 'scheduled',
              'matches': <Object?>[
                <String, Object?>{
                  'id': 'match-final',
                  'order': 2,
                  'status': 'scheduled',
                  'participants': <Object?>[
                    <String, Object?>{'placeholder_label': 'Winner of Semi 1'},
                    <String, Object?>{'placeholder_label': 'Winner of Semi 2'},
                  ],
                },
              ],
            },
            <String, Object?>{
              'id': 'round-semi',
              'name': 'Semi Final',
              'order': 1,
              'status': 'live',
              'matches': <Object?>[
                <String, Object?>{
                  'id': 'match-semi-1',
                  'order': 1,
                  'status': 'live',
                  'home': <String, Object?>{
                    'participant_id': 'alpha',
                    'name': 'Alpha FC',
                    'seed': 1,
                  },
                  'away': <String, Object?>{
                    'participant_id': 'beta',
                    'name': 'Beta FC',
                    'seed': 4,
                  },
                  'score': <String, Object?>{'home': 3, 'away': 1},
                  'winner_participant_id': 'alpha',
                  'live_match_id': 'live-semi-1',
                },
              ],
            },
          ],
        },
      });

      expect(payload.competitionId, 'comp-42');
      expect(payload.bracketId, 'bracket-42');
      expect(payload.revision, 'rev-7');
      expect(payload.lifecycle.stage, CompetitionLifecycleStage.inProgress);
      expect(payload.lifecycle.bracketPublished, isTrue);
      expect(
        payload.rounds.map((CompetitionBracketRound round) => round.id),
        <String>['round-final', 'round-semi'],
      );

      final CompetitionBracketMatch liveMatch =
          payload.rounds[1].matches.single;
      expect(liveMatch.home.displayName, 'Alpha FC');
      expect(liveMatch.away.displayName, 'Beta FC');
      expect(liveMatch.homeScore, 3);
      expect(liveMatch.awayScore, 1);
      expect(liveMatch.winnerParticipantId, 'alpha');
    });

    test('does not synthesize rounds from capacity or participants', () {
      final CompetitionBracketPayload payload =
          CompetitionBracketPayload.fromJson(<String, Object?>{
            'competition_id': 'comp-empty',
            'title': 'Locked Cup',
            'status': 'locked',
            'participant_count': 16,
            'capacity': 16,
          });

      expect(payload.lifecycle.stage, CompetitionLifecycleStage.locked);
      expect(payload.rounds, isEmpty);
      expect(payload.hasMatches, isFalse);
      expect(payload.isDegraded, isTrue);
    });

    test('captures lifecycle degraded and blocked backend state', () {
      final CompetitionLifecycleState state =
          CompetitionLifecycleState.fromJson(<String, Object?>{
            'status': 'seeding',
            'blocked_reason': 'awaiting_backend_seed_commit',
            'degraded_reasons': <String>[
              'missing_rounds',
              'waiting_for_worker',
            ],
          });

      expect(state.stage, CompetitionLifecycleStage.seeding);
      expect(state.isBlocked, isTrue);
      expect(state.degraded, isTrue);
      expect(state.degradedReasons, contains('missing_rounds'));
    });

    test('maps settlement-ready lifecycle aliases to completed', () {
      final CompetitionLifecycleState readyState =
          CompetitionLifecycleState.fromJson(<String, Object?>{
            'status': 'settlement_ready',
            'blocked_reason': null,
          });
      final CompetitionLifecycleState awaitingState =
          CompetitionLifecycleState.fromJson(<String, Object?>{
            'status': 'awaiting_settlement',
          });

      expect(readyState.stage, CompetitionLifecycleStage.completed);
      expect(readyState.isTerminal, isTrue);
      expect(awaitingState.stage, CompetitionLifecycleStage.completed);
      expect(awaitingState.isTerminal, isTrue);
    });
  });
}

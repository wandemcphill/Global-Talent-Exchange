import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_lifecycle_redesign/club_lifecycle_redesign.dart';

void main() {
  test('club lifecycle model parses Batch 24 operating dashboard', () {
    final GtexClubOperatingDashboard dashboard =
        GtexClubOperatingDashboard.fromJson(<String, Object?>{
          'club_id': 'club-1',
          'lifecycle': <String, Object?>{
            'club_id': 'club-1',
            'state': 'squad_ready',
            'previous_state': 'squad_building',
            'readiness_score': 88,
            'blocked_reason': 'squad_registered',
            'metadata': <String, Object?>{},
            'updated_at': '2026-05-11T10:30:00Z',
            'readiness': <String, Object?>{
              'club_id': 'club-1',
              'readiness_score': 88,
              'recommended_state': 'squad_ready',
              'competition_eligible': false,
              'checklist': <Object?>[
                <String, Object?>{
                  'key': 'profile_complete',
                  'label': 'Club profile complete',
                  'complete': true,
                  'detail': 'Profile is ready.',
                },
                <String, Object?>{
                  'key': 'squad_registered',
                  'label': 'Squad registration submitted',
                  'complete': false,
                  'detail': 'Submit the launch squad.',
                },
              ],
              'blockers': <String>['squad_registered'],
              'updated_at': '2026-05-11T10:30:00Z',
            },
          },
          'squad_registration': <String, Object?>{
            'id': 'registration-1',
            'club_id': 'club-1',
            'season_label': 'launch',
            'status': 'draft',
            'players': <Object?>[
              <String, Object?>{
                'player_id': 'player-1',
                'name': 'Launch Keeper',
                'position': 'GK',
                'position_group': 'goalkeeper',
              },
            ],
            'position_summary': <String, Object?>{'goalkeeper': 1},
            'submitted_at': null,
            'locked_at': null,
            'updated_at': '2026-05-11T10:30:00Z',
          },
          'module_links': <Object?>[],
          'counts': <String, Object?>{'players': 11, 'registered': 1},
          'alerts': <String>['squad_registered'],
          'updated_at': '2026-05-11T10:30:00Z',
        });

    expect(dashboard.lifecycle.state, GtexClubLifecycleState.squadReady);
    expect(dashboard.readiness.completedCount, 1);
    expect(
      dashboard.squadRegistration?.players.single.positionGroup,
      'goalkeeper',
    );
    expect(dashboard.counts['players'], 11);
  });

  test(
    'controller uses fixture fallback and mutates registration state',
    () async {
      final GtexClubLifecycleController controller =
          GtexClubLifecycleController(
            api: GtexClubLifecycleApi.fixture(),
            clubId: 'fixture-club',
          );

      await controller.load();

      expect(controller.dashboard, isNotNull);
      expect(controller.dashboard!.readiness.readinessScore, 88);
      expect(
        controller.dashboard!.squadRegistration?.status,
        GtexSquadRegistrationStatus.draft,
      );

      await controller.submitSquadRegistration();

      expect(
        controller.dashboard!.squadRegistration?.status,
        GtexSquadRegistrationStatus.submitted,
      );
    },
  );
}

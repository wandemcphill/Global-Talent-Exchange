import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_living_star.dart';

void main() {
  test('parses living-star payload with voice, mood and exit ladder', () {
    final GtexRegenLivingStar star = GtexRegenLivingStar.fromJson(
      <String, Object?>{
        'player_id': 'p-1',
        'regen_id': 'r-1',
        'is_unique_collectible': true,
        'archetype': <String, Object?>{
          'code': 'mercenary',
          'label': 'The Mercenary',
          'summary': 'Chases wage spikes.',
          'dominant_traits': <String>['greed', 'ambition'],
        },
        'mood': <String, Object?>{
          'code': 'restless',
          'label': 'Restless',
          'severity': 2,
          'drivers': <String>['wage dissatisfaction'],
        },
        'monologue': <String, Object?>{
          'voice_line': 'I am producing. The wage does not match the output.',
          'tone': 'tense',
          'generated_at': '2026-10-12T20:00:00Z',
          'seed': 'abc',
        },
        'exit_ladder': <String, Object?>{
          'stage': 'formal_request',
          'label': 'Formal transfer request',
          'severity': 2,
          'next_stage': 'training_exile',
          'can_petition_termination': true,
          'owner_actions': <String>['negotiate stay', 'list at ask'],
        },
        'personality': <String, Object?>{
          'ambition': 80,
          'loyalty': 20,
          'professionalism': 50,
          'greed': 90,
          'temperament': 60,
          'patience': 40,
          'adaptability': 50,
          'competitiveness': 70,
          'ego': 75,
          'development_focus': 40,
          'hometown_affinity': 20,
          'trophy_hunger': 70,
          'media_appetite': 55,
          'default_career_target_band': 'trophy-first',
        },
        'agency': <String, Object?>{
          'morale': 40,
          'happiness': 35,
          'transfer_appetite': 70,
          'contract_stance': 'hardball',
          'wage_satisfaction': 30,
          'playing_time_satisfaction': 40,
          'development_satisfaction': 45,
          'club_project_belief': 35,
          'grievance_count': 1,
          'transfer_request_status': 'transfer_request',
          'preferred_role_band': 'starter',
          'career_stage': 'peak',
          'career_target_band': 'trophy-first',
          'salary_expectation_amount': '1000',
        },
        'promises': <Map<String, Object?>>[
          <String, Object?>{
            'key': 'cl',
            'statement': 'Champions League by 2028',
            'status': 'broken',
            'broken': true,
          },
        ],
        'grievances': <String>['Wage respect is below their threshold'],
        'behavior_brief': <String, Object?>{
          'player_id': 'p-1',
          'risk_appetite': 0.7,
          'pressing_intensity': 0.6,
          'big_game_nerves': 0.2,
          'celebration_hunger': 0.5,
          'captaincy_willingness': 0.3,
          'shot_greed': 0.8,
          'discipline_risk': 0.4,
          'notes': <String>['May refuse armband'],
        },
        'inbox_notes': <String>['Mood: Restless'],
      },
    );

    expect(star.archetypeCode, 'mercenary');
    expect(star.moodLabel, 'Restless');
    expect(star.voiceLine, contains('wage'));
    expect(star.exitStage, 'formal_request');
    expect(star.canPetitionTermination, isTrue);
    expect(star.promises.single.broken, isTrue);
    expect(star.behaviorBrief.shotGreed, 0.8);
    expect(star.isUniqueCollectible, isTrue);
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/match/match_dto.dart';
import 'package:gte_frontend/features/match_center/data/match/match_mapper.dart';

void main() {
  test('mapper converts v2 match dto into a stable domain result', () {
    final MatchResponseDto response = MatchResponseDto.fromJson(
      <String, dynamic>{
        'matches': <Map<String, dynamic>>[
          <String, dynamic>{
            'player_id': 'player-osimhen',
            'score': 0.87,
            'score_breakdown': <String, dynamic>{
              'age': 0.18,
              'position': 0.4,
              'country': 0.1,
            },
            'reasons': <Map<String, dynamic>>[
              <String, dynamic>{
                'type': 'position',
                'label': 'Age profile fits the brief',
                'impact': 'positive',
              },
              <String, dynamic>{
                'type': 'country',
                'label': 'Same country',
                'impact': 'positive',
              },
            ],
            'flags': <String, dynamic>{
              'is_free_agent': true,
              'is_exact_position': true,
              'is_high_potential': true,
            },
            'player': <String, dynamic>{
              'player_id': 'player-osimhen',
              'player_name': 'Victor Demo',
              'position': 'ST',
              'age': 24,
              'nationality': 'Nigeria',
              'current_club_name': 'Free Agent',
              'dominant_foot': 'Right',
              'height_cm': 186,
            },
          },
        ],
        'meta': <String, dynamic>{'total': 1},
        'summary': <String, dynamic>{'returned': 1},
      },
    );

    final result = MatchMapper.toDomain(response.matches.single);

    expect(result.player.id, 'player-osimhen');
    expect(result.player.name, 'Victor Demo');
    expect(result.score, 0.87);
    expect(result.reasons.first, contains('Age'));
    expect(result.breakdown['position'], 0.4);
    expect(result.flags.isFreeAgent, isTrue);
    expect(result.flags.isExactPosition, isTrue);
    expect(result.flags.isHighPotential, isTrue);
    expect(result.preferredFoot, 'Right');
    expect(result.heightMeters, 1.86);
  });

  test('mapper tolerates the current slim backend match payload', () {
    final MatchResponseDto response = MatchResponseDto.fromJson(
      <String, dynamic>{
        'matches': <Map<String, dynamic>>[
          <String, dynamic>{
            'player': <String, dynamic>{
              'player_id': 'player-history-winger',
              'player_name': 'History Winger',
              'position': 'Winger',
              'age': 22,
              'nationality': 'England',
              'current_club_name': 'Free Agent',
              'dominant_foot': 'Left',
              'height_cm': 175,
              'is_free_agent': true,
            },
            'score': 0.9,
            'reasons': <String>[
              'Perfect position match',
              'Preferred scouting region',
            ],
          },
        ],
      },
    );

    final result = MatchMapper.toDomain(response.matches.single);

    expect(result.player.id, 'player-history-winger');
    expect(result.score, 0.9);
    expect(result.reasons, contains('Preferred scouting region'));
    expect(result.flags.isFreeAgent, isTrue);
    expect(result.flags.isExactPosition, isTrue);
    expect(result.preferredFoot, 'Left');
    expect(result.heightMeters, 1.75);
  });
}

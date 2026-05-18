import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/models/national_team_models.dart';

void main() {
  test('rental collection parses portraits and diagnostics', () {
    final NationalTeamRentalPlayerCollection collection =
        NationalTeamRentalPlayerCollection.fromJson(<String, Object?>{
          'total': 1,
          'partial': true,
          'failed_count': 1,
          'warnings': <String>['preseeded:bad skipped'],
          'source_counts': <String, Object?>{'preseeded': 1},
          'items': <Object?>[
            <String, Object?>{
              'player_id': 'seed_1',
              'player_name': 'Ayo Okafor',
              'image_url': 'https://media.test/regen.png',
              'portrait_url': 'https://media.test/regen.png',
              'portrait_status': 'approved',
              'portrait_source': 'approved_newgen_bank',
              'overall_rating': 82,
              'primary_position': 'ST',
              'nationality': 'Nigeria',
              'country_code': 'NG',
              'age': 18,
              'gsi': 84,
              'base_value_coin': '84.0000',
              'loan_price_coin': '50.4000',
              'tier_label': 'high',
              'source_bucket': 'preseeded',
              'is_regen': true,
              'is_preseeded_national_regen': true,
              'market_eligible': false,
            },
          ],
        });

    expect(collection.partial, isTrue);
    expect(collection.failedCount, 1);
    expect(collection.warnings, contains('preseeded:bad skipped'));
    expect(collection.sourceCounts['preseeded'], 1);
    expect(collection.items, hasLength(1));
    expect(collection.items.single.imageUrl, 'https://media.test/regen.png');
    expect(collection.items.single.portraitStatus, 'approved');
    expect(collection.items.single.isPreseededNationalRegen, isTrue);
  });

  test(
    'rental collection skips malformed players and preserves valid rows',
    () {
      final NationalTeamRentalPlayerCollection collection =
          NationalTeamRentalPlayerCollection.fromJson(<String, Object?>{
            'items': <Object?>[
              <String, Object?>{'player_id': 'missing-name'},
              <String, Object?>{
                'player_id': 'real_1',
                'player_name': 'Live Player',
                'overall_rating': 74,
                'gsi': 74,
                'base_value_coin': '74.0000',
                'loan_price_coin': '74.0000',
                'tier_label': 'mid',
                'source_bucket': 'real',
              },
            ],
          });

      expect(collection.partial, isTrue);
      expect(collection.failedCount, 1);
      expect(collection.items, hasLength(1));
      expect(collection.items.single.playerName, 'Live Player');
    },
  );
}

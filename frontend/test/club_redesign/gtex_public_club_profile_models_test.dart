import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_contract.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_public_club_profile_models.dart';

void main() {
  test('public club profile parses the complete football and owner dossier', () {
    final GtexPublicClubProfileData profile = GtexPublicClubProfileData.fromJson(
      <String, Object?>{
        'club': <String, Object?>{
          'id': 'club-eclipse',
          'name': 'Lagos Eclipse FC',
          'slug': 'lagos-eclipse',
          'short_name': 'LEFC',
          'country_code': 'NG',
          'city_name': 'Lagos',
          'primary_color': '#101B32',
          'secondary_color': '#D5B46A',
        },
        'owner': <String, Object?>{
          'id': 'owner-123',
          'display_name': 'Amara Okafor',
          'club_count': 2,
          'luxury_asset_count': 3,
          'net_worth': '720000.00',
          'net_worth_currency': 'GTX',
          'profile_path': '/owner/public/profile/owner-123',
          'public_clubs': <Object?>[
            <String, Object?>{
              'id': 'club-eclipse',
              'name': 'Lagos Eclipse FC',
              'slug': 'lagos-eclipse',
              'short_name': 'LEFC',
              'city': 'Lagos',
              'country_code': 'NG',
            },
          ],
        },
        'stadium': <String, Object?>{
          'name': 'Eclipse Arena',
          'level': 4,
          'capacity': 42000,
          'image_asset': 'assets/showroom/arena_imperiale_stadium.webp',
        },
        'facilities': <String, Object?>{
          'training_level': 4,
          'academy_level': 5,
          'medical_level': 3,
          'youth_recruitment_level': 5,
        },
        'academy': <String, Object?>{
          'level': 5,
          'capacity': 24,
          'prospect_count': 1,
          'prospects': <Object?>[
            <String, Object?>{
              'id': 'prospect-1',
              'name': 'Tunde Bello',
              'position': 'CM',
              'age': 16,
              'potential': 91,
            },
          ],
        },
        'squad': <String, Object?>{
          'player_count': 22,
          'players': <Object?>[
            <String, Object?>{
              'id': 'player-1',
              'name': 'Samuel Okoro',
              'position': 'ST',
              'age': 24,
              'rating': 91,
              'potential': 93,
            },
            <String, Object?>{
              'id': 'regen-1',
              'name': 'Kaito Mensah',
              'position': 'RW',
              'age': 17,
              'rating': 78,
              'potential': 97,
              'is_regen': true,
            },
          ],
          'best_player': <String, Object?>{
            'id': 'player-1',
            'name': 'Samuel Okoro',
            'position': 'ST',
            'age': 24,
            'rating': 91,
            'potential': 93,
          },
          'most_promising_player': <String, Object?>{
            'id': 'regen-1',
            'name': 'Kaito Mensah',
            'position': 'RW',
            'age': 17,
            'rating': 78,
            'potential': 97,
            'is_regen': true,
          },
        },
        'staff': <Object?>[
          <String, Object?>{
            'role': 'general_manager',
            'title': 'General Manager',
            'name': 'Nneka Manager',
            'appointed': true,
          },
          <String, Object?>{
            'role': 'head_of_youth_development',
            'title': 'Head of Youth Development',
            'name': 'Chidi Youth Director',
            'appointed': true,
          },
        ],
        'coach_buses': <Object?>[
          <String, Object?>{
            'name': 'Vanguard First-Team Coach',
            'category': 'coach',
            'edition_number': 1,
            'preview_file': 'assets/showroom/vanguard_xii_coach.webp',
          },
        ],
        'trophies': <Object?>[
          <String, Object?>{
            'id': 'trophy-1',
            'name': 'GTEX Champions Cup',
            'competition': 'GTEX Champions Cup',
            'season': '2026',
          },
        ],
      },
    );

    expect(profile.clubId, 'club-eclipse');
    expect(profile.name, 'Lagos Eclipse FC');
    expect(profile.stadium['capacity'], 42000);
    expect(profile.facilities['training_level'], 4);
    expect(profile.academy['prospect_count'], 1);
    expect(profile.squadPlayerCount, 22);
    expect(profile.squadPlayers.map((player) => player.name), <String>[
      'Samuel Okoro',
      'Kaito Mensah',
    ]);
    expect(profile.bestPlayer?.name, 'Samuel Okoro');
    expect(profile.mostPromisingPlayer?.name, 'Kaito Mensah');
    expect(profile.mostPromisingPlayer?.isRegen, isTrue);
    expect(profile.staff.first.name, 'Nneka Manager');
    expect(profile.coachBuses.single.name, 'Vanguard First-Team Coach');
    expect(profile.owner.displayName, 'Amara Okafor');
    expect(profile.owner.clubCount, 2);
    expect(profile.owner.netWorth, '720000.00');
  });

  test('public owner profile parses personal luxury collection and clubs', () {
    final GtexPublicOwnerProfileData owner = GtexPublicOwnerProfileData.fromJson(
      <String, Object?>{
        'id': 'owner-123',
        'display_name': 'Amara Okafor',
        'club_count': 2,
        'luxury_asset_count': 3,
        'net_worth': '720000.00',
        'net_worth_currency': 'GTX',
        'assets': <Object?>[
          <String, Object?>{
            'name': 'Sovereign 900X Jet',
            'category': 'jet',
            'catalog_price': '50000.00',
          },
          <String, Object?>{'name': 'Veloce GT9', 'category': 'car'},
          <String, Object?>{'name': 'Chronos Tourbillon', 'category': 'watch'},
        ],
        'public_clubs': <Object?>[
          <String, Object?>{'id': 'club-1', 'name': 'Lagos Eclipse FC', 'slug': 'lagos-eclipse'},
          <String, Object?>{'id': 'club-2', 'name': 'Coastal Lions', 'slug': 'coastal-lions'},
        ],
      },
    );

    expect(owner.clubCount, 2);
    expect(owner.luxuryAssetCount, 3);
    expect(owner.assets.map((asset) => asset.category), <String>['jet', 'car', 'watch']);
    expect(owner.assets.first.catalogPrice, '50000.00');
    expect(owner.publicClubs, hasLength(2));
  });

  test('new public profile URLs are registered in the canonical API contract', () {
    expect(
      gteCanonicalApiPath('/api/clubs/club-eclipse/public-profile'),
      '/api/v2/clubs/club-eclipse/public-profile',
    );
    expect(
      gteCanonicalApiPath('/owner/public/profile/owner-123'),
      '/api/v2/owner/public/profile/owner-123',
    );
  });
  test('world clock path resolves through the generated API contract', () {
    expect(
      gteCanonicalApiPath('/api/world/clock'),
      '/api/v2/world/clock',
    );
  });

}

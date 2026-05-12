import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';

void main() {
  test('club growth model parses Batch 25-27 dashboard JSON', () {
    final GtexClubGrowthDashboard dashboard = GtexClubGrowthDashboard.fromJson(
      <String, Object?>{
        'club_id': 'club-1',
        'staff_market': <Object?>[
          <String, Object?>{
            'id': 'staff-1',
            'display_name': 'Regional Scout',
            'staff_type': 'scout',
            'rarity': 'standard',
            'skills': <String>['scouting', 'academy_growth'],
            'salary_minor': 18000,
            'commission_bps': 100,
            'rating': 58,
            'active': true,
            'metadata': <String, Object?>{},
          },
        ],
        'staff_contracts': <Object?>[],
        'staff_effects': <String, Object?>{'scout_quality': 58},
        'academy_profile': <String, Object?>{
          'id': 'academy-1',
          'club_id': 'club-1',
          'level': 2,
          'investment_minor': 100000,
          'generation_cooldown_until': null,
          'metadata': <String, Object?>{},
          'updated_at': '2026-05-11T12:00:00Z',
        },
        'academy_prospects': <Object?>[
          <String, Object?>{
            'id': 'prospect-1',
            'club_id': 'club-1',
            'display_name': 'Academy Regen 001',
            'nationality': 'NG',
            'position': 'CM',
            'age': 16,
            'personality': <String, Object?>{'temperament': 'focused'},
            'current_ability': 42,
            'potential': 78,
            'portrait_asset_ref': null,
            'status': 'discovered',
            'metadata': <String, Object?>{
              'portrait_policy': 'newgen_bank_only',
            },
            'updated_at': '2026-05-11T12:00:00Z',
          },
        ],
        'sponsorship': <String, Object?>{
          'active_contracts': 1,
          'pending_contracts': 0,
          'settled_payout_minor': 25000,
          'outstanding_payout_minor': 75000,
          'open_leads': 1,
        },
        'updated_at': '2026-05-11T12:00:00Z',
      },
    );

    expect(dashboard.clubId, 'club-1');
    expect(dashboard.staffMarket.single.staffType, 'scout');
    expect(dashboard.academyProfile.level, 2);
    expect(dashboard.academyProspects.single.contractEligible, isTrue);
    expect(dashboard.sponsorship.outstandingPayoutMinor, 75000);
  });

  test(
    'controller uses fixture fallback for staff and academy mutations',
    () async {
      final GtexClubGrowthController controller = GtexClubGrowthController(
        api: GtexClubGrowthApi.fixture(),
        clubId: 'fixture-club',
      );

      await controller.load();

      expect(controller.dashboard, isNotNull);
      expect(controller.dashboard!.staffMarket, isNotEmpty);
      expect(controller.dashboard!.academyProspects, isEmpty);

      await controller.hireStaff(controller.dashboard!.staffMarket.first.id);

      expect(controller.dashboard!.activeStaffCount, 1);

      await controller.generateProspects();

      final GtexAcademyProspect prospect =
          controller.dashboard!.academyProspects.first;
      expect(prospect.metadata['portrait_policy'], 'newgen_bank_only');

      await controller.offerAndAcceptProspectContract(prospect.id);

      expect(
        controller.dashboard!.academyProspects.first.status,
        'youth_signed',
      );

      await controller.promoteProspect(prospect.id);

      expect(
        controller.dashboard!.academyProspects.first.status,
        'promoted_to_senior',
      );
    },
  );
}

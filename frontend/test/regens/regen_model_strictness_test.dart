import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';

void main() {
  test('regen DNA parser rejects partial backend stat payloads', () {
    expect(
      () => RegenDnaProfile.fromJson(<String, Object?>{'PAC': 88, 'SHO': 82}),
      throwsA(isA<GteParsingException>()),
    );
  });

  test('request-son preview requires backend trait echo', () {
    final Map<String, Object?> payload =
        _requestSonPreviewPayload()..remove('selected_traits');

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(isA<GteParsingException>()),
    );
  });

  test('regen market access defaults missing live permissions to blocked', () {
    final RegenUniversePlayer player =
        RegenUniversePlayer.fromJson(<String, Object?>{
          'id': 'regen-1',
          'name': 'Ayo Future',
          'age': 16,
          'nationality': 'Nigeria',
          'position': 'ST',
          'current_rating': 71,
          'potential': 90,
          'growth_curve': 0.82,
          'source_type': 'generated',
        });

    expect(player.marketAccess.marketEligible, isFalse);
    expect(player.marketAccess.shareMarketEligible, isFalse);
    expect(player.marketAccess.tradable, isFalse);
    expect(player.marketAccess.buyable, isFalse);
    expect(player.marketAccess.transferable, isFalse);
    expect(player.marketAccess.cardMintEligible, isFalse);
    expect(player.marketAccess.buyCtaAllowed, isFalse);
  });

  test('national regen seeds require backend generation and rarity', () {
    expect(
      () => NationalRegenSeed.fromJson(
        _nationalSeedPayload()..remove('generation_index'),
      ),
      throwsA(isA<GteParsingException>()),
    );
    expect(
      () => NationalRegenSeed.fromJson(
        _nationalSeedPayload()..remove('rarity_tier'),
      ),
      throwsA(isA<GteParsingException>()),
    );
  });
}

Map<String, Object?> _requestSonPreviewPayload() {
  return <String, Object?>{
    'parent': <String, Object?>{
      'player_id': 'parent-1',
      'full_name': 'Victor Adebayo',
    },
    'selected_traits': <String>['Leader', 'Two-Footed', 'Clutch Finisher'],
    'projected_dna': <String, Object?>{
      'PAC': 78,
      'SHO': 74,
      'PAS': 69,
      'DRI': 76,
      'DEF': 44,
      'PHY': 73,
    },
    'projected_ovr': 67,
    'projected_pot': 91,
    'parent_generation': 1,
    'projected_generation': 2,
    'generation_label': 'GEN-2',
    'total_cost_coin': 200,
    'wallet': <String, Object?>{
      'can_pay_with_wallet': true,
      'available_balance': 500,
      'reserved_balance': 0,
      'locked_balance': 0,
      'pending_withdrawal_balance': 0,
      'total_balance': 500,
      'currency': 'GTC',
    },
  };
}

Map<String, Object?> _nationalSeedPayload() {
  return <String, Object?>{
    'id': 'national-seed-ng-1',
    'seed_key': 'seed:ng:1',
    'display_name': 'Azeez Salisu',
    'age': 16,
    'age_band': 'u17',
    'country_code': 'NG',
    'country_name': 'Nigeria',
    'seed_type': 'national_seed',
    'generation_index': 1,
    'primary_position': 'RW',
    'current_rating': 71,
    'potential_rating': 90,
    'growth_curve': 0.82,
    'rarity_tier': 'elite',
    'status': 'active',
    'metadata': <String, Object?>{},
  };
}

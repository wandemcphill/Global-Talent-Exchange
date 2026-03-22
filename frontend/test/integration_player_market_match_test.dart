import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_models.dart';

void main() {
  test(
      'player-card listings expose authoritative GTEX value when backend provides it',
      () {
    final PlayerCardMarketplaceListing listing =
        PlayerCardMarketplaceListing.fromJson(<String, Object?>{
      'listing_id': 'listing-1',
      'listing_type': 'sale',
      'player_card_id': 'card-1',
      'player_id': 'player-1',
      'player_name': 'Ayo Signal',
      'club_name': 'Lagos City',
      'position': 'CM',
      'tier_code': 'elite',
      'tier_name': 'Elite',
      'rarity_rank': 1,
      'edition_code': '2026',
      'listing_owner_user_id': 'seller-1',
      'status': 'open',
      'availability': 'available',
      'is_negotiable': false,
      'asset_origin': 'standard',
      'is_regen_newgen': false,
      'is_creator_linked': false,
      'quantity': 1,
      'available_quantity': 1,
      'sale_price_credits': 1800,
      'latest_value_credits': 2200,
      'requested_filters_json': <String, Object?>{},
      'created_at': '2026-03-21T10:00:00Z',
      'avatar': <String, Object?>{
        'avatar_version': 1,
        'version': 'fm_v1',
        'seed_token': 'seed-1',
        'dna_seed': 100,
        'skin_tone': 2,
        'hair_style': 3,
        'hair_color': 1,
        'face_shape': 2,
        'eyebrow_style': 2,
        'eye_type': 1,
        'nose_type': 2,
        'mouth_type': 2,
        'beard_style': 0,
        'has_accessory': false,
        'accessory_type': 0,
        'jersey_style': 2,
        'accent_tone': 1,
      },
    });

    expect(listing.latestValueCredits, 2200);
  });

  test('lifecycle snapshot parses additive agency summary safely', () {
    final GtePlayerLifecycleSnapshot snapshot =
        GtePlayerLifecycleSnapshot.fromJson(<String, Object?>{
      'player_id': 'player-9',
      'player_name': 'Canonical Prospect',
      'availability_badge': <String, Object?>{
        'status': 'available',
        'label': 'Available',
        'available': true,
      },
      'transfer_status': <String, Object?>{
        'window_open': true,
        'eligible': true,
        'reason': 'Agency remains open to the right project.',
      },
      'regen_summary': <String, Object?>{
        'status': 'active',
        'lifecycle_phase': 'senior',
        'transfer_listed': true,
        'free_agent': false,
        'retirement_pressure': false,
        'agency_message': 'Wants a bigger role before committing long term.',
        'pressure_state': <String, Object?>{
          'current_state': 'monitoring',
          'transfer_desire': 0.8,
          'active_transfer_request': true,
          'refuses_new_contract': true,
          'end_of_contract_pressure': false,
        },
        'team_dynamics': <String, Object?>{
          'active': true,
          'morale_penalty': 0.7,
          'chemistry_penalty': 0.3,
        },
      },
      'recent_events': const <Object?>[],
    });

    expect(snapshot.agencySummary, isNotNull);
    expect(snapshot.agencySummary!.transferStanceLabel, 'Wants move');
    expect(snapshot.agencySummary!.contractStanceLabel, 'Holding out');
    expect(snapshot.agencySummary!.moraleLabel, 'Under strain');
  });
}

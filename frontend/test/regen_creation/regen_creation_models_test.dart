import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

void main() {
  test('request-son models parse canonical parent and preview truth', () {
    final RegenCreationParentPlayer parent = RegenCreationParentPlayer.fromJson(
      <String, Object?>{
        'player_id': 'parent-1',
        'full_name': 'Victor Adebayo',
        'position': 'ST',
        'country_code': 'NGA',
        'ovr': 84,
        'gen': 'GEN-1',
        'traits': <String>['Leader', 'Two-Footed'],
        'lineage': <String>['Adebayo Line'],
        'dna': <String, Object?>{
          'PAC': 88,
          'SHO': 82,
          'PAS': 71,
          'DRI': 84,
          'DEF': 42,
          'PHY': 78,
        },
      },
    );

    expect(parent.overallRating, 84);
    expect(parent.generationNumber, 1);
    expect(parent.traits, contains('Leader'));
    expect(parent.lineage, contains('Adebayo Line'));
    expect(parent.dnaProfile!.valueFor('PAC'), 88);

    final RequestSonPreview preview = RequestSonPreview.fromJson(
      <String, Object?>{
        'parent': <String, Object?>{
          'player_id': 'parent-1',
          'full_name': 'Victor Adebayo',
          'position': 'ST',
          'country_code': 'NGA',
          'current_rating': 84,
          'generation': 1,
          'traits': <String>['Leader', 'Two-Footed', 'Clutch Finisher'],
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
          'reserved_balance': 40,
          'locked_balance': 10,
          'pending_withdrawal_balance': 0,
          'total_balance': 550,
          'currency': 'GTC',
          'lock_reasons': <String>['Transfer bid reservation'],
        },
      },
    );

    expect(preview.canConfirm, isTrue);
    expect(preview.parentPlayerId, 'parent-1');
    expect(preview.parentGeneration, 1);
    expect(preview.generationNumber, 2);
    expect(preview.generationLabel, 'GEN-2');
    expect(preview.projectedOverall, 67);
    expect(preview.projectedPotential, 91);
    expect(preview.walletAvailability.availableBalanceCoin, 500);
    expect(
      preview.walletAvailability.lockReasons,
      contains('Transfer bid reservation'),
    );
  });

  test('request-son preview and order drafts serialize inherited traits', () {
    const RequestSonPreviewDraft previewDraft = RequestSonPreviewDraft(
      parentPlayerId: 'parent-1',
      selectedTraits: <String>['Leader', 'Leader', 'Two-Footed', ' Finisher '],
      requestedName: 'Ayo Adebayo',
      requestedCountryCode: 'nga',
      requestedPosition: 'cam',
    );

    expect(previewDraft.hasExactlyThreeTraits, isTrue);
    expect(
      previewDraft.toJson(),
      containsPair('selected_traits', <String>[
        'Leader',
        'Two-Footed',
        'Finisher',
      ]),
    );
    expect(
      previewDraft.toJson(),
      containsPair('requested_country_code', 'NGA'),
    );
    expect(previewDraft.toJson(), containsPair('requested_position', 'AM'));

    const RequestSonOrderDraft orderDraft = RequestSonOrderDraft(
      parentPlayerId: 'parent-1',
      paymentMethod: 'wallet',
      selectedTraits: <String>['Leader', 'Two-Footed', 'Finisher'],
      requestedPosition: 'CF',
    );

    expect(
      orderDraft.toJson(),
      containsPair('selected_traits', <String>[
        'Leader',
        'Two-Footed',
        'Finisher',
      ]),
    );
    expect(orderDraft.toJson(), containsPair('requested_position', 'ST'));
  });

  test('request-son drafts reject external payment methods', () {
    const RequestSonPreviewDraft previewDraft = RequestSonPreviewDraft(
      parentPlayerId: 'parent-1',
      selectedTraits: <String>['Leader', 'Two-Footed', 'Finisher'],
      paymentMethod: 'korapay',
    );
    const RequestSonOrderDraft orderDraft = RequestSonOrderDraft(
      parentPlayerId: 'parent-1',
      paymentMethod: 'bank_transfer_manual',
      selectedTraits: <String>['Leader', 'Two-Footed', 'Finisher'],
    );

    final Matcher walletOnlyError = throwsA(
      isA<GteParsingException>().having(
        (GteParsingException error) => error.message,
        'message',
        contains('wallet payment'),
      ),
    );

    expect(() => previewDraft.toJson(), walletOnlyError);
    expect(() => orderDraft.toJson(), walletOnlyError);
  });

  test('creation order status helpers keep generated truth strict', () {
    final RegenCreationOrder paid = _creationOrder(status: 'paid');
    final RegenCreationOrder generating = _creationOrder(status: 'generating');
    final RegenCreationOrder generatedWithoutPlayer = _creationOrder(
      status: 'generated',
    );
    final RegenCreationOrder generatedWithPlayer = _creationOrder(
      status: 'generated',
      generatedPlayer: const RegenCreationGeneratedPlayer(
        playerId: 'regen-1',
        regenProfileId: 'profile-1',
        fullName: 'Ayo Adebayo',
        age: 15,
        position: 'ST',
        currentRating: 55,
        potentialRating: 91,
      ),
    );

    expect(paid.isPaid, isTrue);
    expect(paid.isGenerating, isFalse);
    expect(paid.isGenerated, isFalse);
    expect(generating.isGenerating, isTrue);
    expect(generating.isGenerated, isFalse);
    expect(generatedWithoutPlayer.isGenerated, isFalse);
    expect(generatedWithPlayer.isGenerated, isTrue);
  });

  test('request-son options require backend-owned identity selectors', () {
    final Map<String, Object?> payload = <String, Object?>{
      'club_id': 'club-1',
      'club_name': 'Lagos Royals',
      'currency': 'GTC',
      'pricing': <String, Object?>{
        'base_cost_coin': 200,
        'name_cost_coin': 0,
        'customization_cost_coin': 0,
      },
      'nationality_options': <Object?>[
        <String, Object?>{
          'code': 'NG',
          'name': 'Nigeria',
          'alpha2_code': 'NG',
          'market_region': 'west-africa',
          'is_default': true,
        },
      ],
      'position_options': <Object?>[
        <String, Object?>{
          'code': 'AM',
          'label': 'Attacking Midfielder',
          'aliases': <String>['CAM'],
          'group': 'midfielder',
          'is_default': true,
        },
        <String, Object?>{
          'code': 'ST',
          'label': 'Striker',
          'aliases': <String>['CF'],
          'group': 'forward',
        },
      ],
      'default_country_code': 'NG',
      'default_position': 'AM',
      'eligible_parents': <Object?>[],
    };

    final RequestSonOptions options = RequestSonOptions.fromJson(payload);

    expect(options.defaultCountryCode, 'NG');
    expect(options.defaultPosition, 'AM');
    expect(options.nationalityOptions.single.displayLabel, 'NG - Nigeria');
    expect(options.nationalityOptions.single.marketRegion, 'west-africa');
    expect(options.positionOptions.first.aliases, <String>['CAM']);
    expect(options.positionOptions.last.displayLabel, 'ST - Striker');

    final Map<String, Object?> missingSelectors =
        Map<String, Object?>.from(payload)
          ..remove('nationality_options')
          ..remove('position_options');
    expect(
      () => RequestSonOptions.fromJson(missingSelectors),
      throwsA(
        isA<GteParsingException>().having(
          (GteParsingException error) => error.message,
          'message',
          contains('selector fields'),
        ),
      ),
    );
  });

  test(
    'request-son preview rejects generic DNA aliases as projection truth',
    () {
      final Map<String, Object?> payload = <String, Object?>{
        'parent': <String, Object?>{'player_id': 'parent-1'},
        'selected_traits': <String>['Leader', 'Two-Footed', 'Clutch Finisher'],
        'dna_profile': <String, Object?>{
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
          'reserved_balance': 40,
          'locked_balance': 10,
          'pending_withdrawal_balance': 0,
          'total_balance': 550,
          'currency': 'GTC',
        },
      };

      expect(
        () => RequestSonPreview.fromJson(payload),
        throwsA(
          isA<FormatException>().having(
            (FormatException error) => error.message,
            'message',
            contains('projected_dna'),
          ),
        ),
      );
    },
  );

  test('request-son preview rejects legacy preview aliases', () {
    final Map<String, Object?> payload = <String, Object?>{
      'parent': <String, Object?>{'player_id': 'parent-1'},
      'selectedTraits': <String>['Leader', 'Two-Footed', 'Clutch Finisher'],
      'projectedDna': <String, Object?>{
        'PAC': 78,
        'SHO': 74,
        'PAS': 69,
        'DRI': 76,
        'DEF': 44,
        'PHY': 73,
      },
      'projectedOverall': 67,
      'projectedPotential': 91,
      'projectedGeneration': 2,
      'generationLabel': 'GEN-2',
      'totalCostCoin': 200,
      'walletAvailability': <String, Object?>{
        'canPayWithWallet': true,
        'availableBalance': 500,
        'reservedBalance': 40,
        'lockedBalance': 10,
        'pendingWithdrawalBalance': 0,
        'totalBalance': 550,
        'currency': 'GTC',
      },
    };

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(
        isA<FormatException>().having(
          (FormatException error) => error.message,
          'message',
          allOf(
            contains('selected_traits'),
            contains('projected_dna'),
            contains('wallet'),
          ),
        ),
      ),
    );
  });

  test('request-son preview requires exactly 3 echoed traits', () {
    final Map<String, Object?> payload = <String, Object?>{
      'parent': <String, Object?>{'player_id': 'parent-1'},
      'selected_traits': <String>['Leader', 'Two-Footed'],
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
        'reserved_balance': 40,
        'locked_balance': 10,
        'pending_withdrawal_balance': 0,
        'total_balance': 550,
        'currency': 'GTC',
      },
    };

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(
        isA<FormatException>().having(
          (FormatException error) => error.message,
          'message',
          contains('exactly 3 backend traits'),
        ),
      ),
    );
  });

  test('request-son preview enforces backend GEN-N+1 lineage', () {
    final Map<String, Object?> payload = <String, Object?>{
      'parent': <String, Object?>{'player_id': 'parent-1'},
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
      'parent_generation': 3,
      'projected_generation': 3,
      'generation_label': 'GEN-3',
      'total_cost_coin': 200,
      'wallet': <String, Object?>{
        'can_pay_with_wallet': true,
        'available_balance': 500,
        'reserved_balance': 40,
        'locked_balance': 10,
        'pending_withdrawal_balance': 0,
        'total_balance': 550,
        'currency': 'GTC',
      },
    };

    expect(
      () => RequestSonPreview.fromJson(payload),
      throwsA(
        isA<FormatException>().having(
          (FormatException error) => error.message,
          'message',
          contains('parent_generation + 1'),
        ),
      ),
    );
  });
}

RegenCreationOrder _creationOrder({
  required String status,
  RegenCreationGeneratedPlayer? generatedPlayer,
}) {
  final DateTime now = DateTime.utc(2026, 6, 3, 3);
  return RegenCreationOrder(
    id: 'order-1',
    userId: 'user-1',
    requestType: 'son',
    amountCoin: 200,
    currency: 'GTC',
    paymentMethod: 'wallet',
    status: status,
    createdAt: now,
    updatedAt: now,
    generatedPlayer: generatedPlayer,
  );
}

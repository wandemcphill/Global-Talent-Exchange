import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';

void main() {
  test('wallet overview rejects missing backend balance facts', () {
    final Map<String, Object?> payload =
        _walletOverviewPayload()..remove('reserved_balance');

    expect(
      () => GteWalletOverview.fromJson(payload),
      throwsA(isA<GteParsingException>()),
    );
  });

  test('wallet overview requires canonical pending withdrawal balance', () {
    final Map<String, Object?> payload =
        _walletOverviewPayload()
          ..remove('pending_withdrawal_balance')
          ..['pending_withdrawals'] = 75;

    expect(
      () => GteWalletOverview.fromJson(payload),
      throwsA(
        isA<GteParsingException>().having(
          (GteParsingException error) => error.message,
          'message',
          contains('pending_withdrawal_balance'),
        ),
      ),
    );
  });

  test('wallet lock reasons preserve backend message and audit reference', () {
    final Map<String, Object?> payload = _walletOverviewPayload();
    payload['lock_reasons'] = <Object?>[
      <String, Object?>{
        'code': 'transfer_bid_reservation',
        'label': 'Transfer bid reservations',
        'amount': '200.0000',
        'currency': 'coin',
        'source': 'transfer_bid',
        'reference': 'transfer_bid:bid-123',
        'message': 'Transfer bid reservations: 200.0000 coin',
      },
    ];

    final GteWalletOverview overview = GteWalletOverview.fromJson(payload);
    final GteWalletSummary summary =
        GteWalletSummary.fromJson(<String, Object?>{
          'available_balance': 1000,
          'reserved_balance': 200,
          'locked_balance': 200,
          'total_balance': 1200,
          'currency': 'coin',
          'lock_reasons': payload['lock_reasons'],
        });

    expect(
      overview.lockReasons,
      contains(
        'Transfer bid reservations: 200.0000 coin | Ref transfer_bid:bid-123',
      ),
    );
    expect(summary.lockReasons, overview.lockReasons);
    expect(overview.lockReasons.single, isNot(contains('{')));
  });

  test('wallet overview preserves canonical payment rail status map', () {
    final GteWalletOverview overview = GteWalletOverview.fromJson(
      _walletOverviewPayload(),
    );

    expect(overview.paymentProviderStatus, <String, String>{
      'bank_transfer_manual': 'ready',
      'korapay': 'ready',
    });
  });

  test('wallet overview rejects non-canonical payment rail status keys', () {
    final Map<String, Object?> payload = _walletOverviewPayload();
    payload['payment_provider_status'] = <String, Object?>{
      'bank_transfer_manual': 'ready',
      'korapay': 'ready',
      'cards': 'ready',
    };

    expect(
      () => GteWalletOverview.fromJson(payload),
      throwsA(
        isA<GteParsingException>().having(
          (GteParsingException error) => error.message,
          'message',
          contains('non-canonical payment provider "cards"'),
        ),
      ),
    );
  });

  test('withdrawal eligibility requires backend rail and balance facts', () {
    final Map<String, Object?> payload =
        _withdrawalEligibilityPayload()..remove('country_withdrawals_enabled');

    expect(
      () => GteWithdrawalEligibility.fromJson(payload),
      throwsA(isA<GteParsingException>()),
    );
  });

  test('KYC profile does not invent geography or timestamps', () {
    final GteKycProfile profile = GteKycProfile.fromJson(<String, Object?>{
      'id': 'kyc-1',
      'status': 'unverified',
    });

    expect(profile.country, isNull);
    expect(profile.city, isNull);
    expect(profile.state, isNull);
    expect(profile.submittedAt, isNull);
    expect(profile.reviewedAt, isNull);
  });
}

Map<String, Object?> _walletOverviewPayload() {
  return <String, Object?>{
    'available_balance': 1200,
    'reserved_balance': 200,
    'locked_balance': 50,
    'pending_deposits': 25,
    'pending_withdrawal_balance': 75,
    'total_inflow': 2000,
    'total_outflow': 800,
    'withdrawable_now': 925,
    'currency': 'coin',
    'country_code': 'NG',
    'required_policy_acceptances_missing': 0,
    'policy_blocked': false,
    'deposit_mode': 'bank_transfer',
    'withdrawal_mode': 'bank_transfer',
    'payment_provider_status': <String, Object?>{
      'bank_transfer_manual': 'ready',
      'korapay': 'ready',
    },
  };
}

Map<String, Object?> _withdrawalEligibilityPayload() {
  return <String, Object?>{
    'available_balance': 1200,
    'withdrawable_now': 1000,
    'remaining_allowance': 1000,
    'next_eligible_at': null,
    'kyc_status': 'fully_verified',
    'requires_kyc': false,
    'requires_bank_account': false,
    'pending_withdrawals': 0,
    'country_code': 'NG',
    'country_withdrawals_enabled': true,
    'missing_required_policies': <Object?>[],
    'policy_blocked': false,
  };
}

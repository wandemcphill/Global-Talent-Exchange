import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';
import 'package:gte_frontend/data/gte_models.dart';

void main() {
  test('wallet repository uses canonical plural wallet routes', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'id': 'wallet-1',
            'user_id': 'user-1',
            'balance': 1250,
            'currency': 'coin',
            'compliance_status': 'verified',
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'id': 'txn-1',
              'user_id': 'user-1',
              'type': 'top_up',
              'amount': 250,
              'status': 'confirmed',
              'reference': 'topup-1',
            },
          ],
        ),
        const GteTransportResponse(
          statusCode: 201,
          body: <String, Object?>{
            'reference': 'topup-2',
            'payment_link': 'https://example.test/pay/topup-2',
            'amount': 500,
            'currency': 'NGN',
            'provider': 'korapay',
            'status': 'pending',
            'mock_mode': false,
          },
        ),
        const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{
            'wallet': <String, Object?>{
              'id': 'wallet-1',
              'user_id': 'user-1',
              'balance': 1750,
              'currency': 'coin',
              'compliance_status': 'verified',
            },
            'transaction': <String, Object?>{
              'id': 'txn-2',
              'user_id': 'user-1',
              'type': 'top_up',
              'amount': 500,
              'status': 'confirmed',
              'reference': 'topup-2',
            },
          },
        ),
      ],
    );
    final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
    await tokenStore.writeToken('token-1');
    final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      fixtures: GteMockApi(),
      tokenStore: tokenStore,
    );

    await repository.fetchWallet();
    await repository.listWalletTransactions(limit: 25);
    await repository.initiateWalletTopUp(
      const GteWalletTopUpInitiateRequest(amount: 500),
    );
    await repository.verifyWalletTopUp('topup-2');

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v2/wallets',
        '/api/v2/wallets/transactions',
        '/api/v2/wallets/top-up/initiate',
        '/api/v2/wallets/top-up/verify',
      ],
    );
    expect(transport.requests[1].uri.queryParameters['limit'], '25');
    expect(transport.requests[3].body, <String, Object?>{
      'reference': 'topup-2',
    });
    expect(
      transport.requests.map(
        (GteTransportRequest request) => request.headers['Authorization'],
      ),
      everyElement('Bearer token-1'),
    );
  });

  test(
    'wallet repository falls back to ledger history when transactions are empty',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(statusCode: 200, body: <Object?>[]),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'page': 1,
              'page_size': 8,
              'total': 2,
              'items': <Object?>[
                <String, Object?>{
                  'id': 'entry-1',
                  'transaction_id': 'txn-1',
                  'amount': '250.0000',
                  'reference': 'wallet-topup-1',
                  'created_at': '2026-05-06T12:00:00Z',
                },
                <String, Object?>{
                  'id': 'entry-2',
                  'transaction_id': 'txn-2',
                  'amount': '-50.0000',
                  'reference': 'gift-1',
                  'created_at': '2026-05-06T12:05:00Z',
                },
              ],
            },
          ),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('token-2');
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(),
        tokenStore: tokenStore,
      );

      final List<GteWalletTransactionRecord> transactions = await repository
          .listWalletTransactions(limit: 8);

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>['/api/v2/wallets/transactions', '/api/v2/wallets/ledger'],
      );
      expect(transport.requests[1].uri.queryParameters, <String, String>{
        'page': '1',
        'page_size': '8',
      });
      expect(transactions, hasLength(2));
      expect(transactions.first.type, 'credit');
      expect(transactions.first.amount, 250);
      expect(transactions.last.type, 'debit');
      expect(transactions.last.amount, 50);
    },
  );

  test(
    'wallet capital flows use canonical backend routes and audit bodies',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(statusCode: 201, body: _depositBody()),
          GteTransportResponse(
            statusCode: 200,
            body: _depositBody(
              status: 'payment_submitted',
              proofAttachmentId: 'proof-1',
            ),
          ),
          GteTransportResponse(statusCode: 200, body: _eligibilityBody()),
          GteTransportResponse(statusCode: 200, body: _withdrawalQuoteBody()),
          GteTransportResponse(statusCode: 201, body: _withdrawalBody()),
          GteTransportResponse(
            statusCode: 200,
            body: <Object?>[_withdrawalBody(status: 'processing')],
          ),
          GteTransportResponse(statusCode: 200, body: _kycBody()),
          GteTransportResponse(
            statusCode: 200,
            body: _kycBody(idDocumentAttachmentId: 'kyc-proof-1'),
          ),
          GteTransportResponse(statusCode: 201, body: _disputeBody()),
          GteTransportResponse(statusCode: 201, body: _disputeMessageBody()),
        ],
      );
      final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
      await tokenStore.writeToken('token-capital');
      final GteModeAwareApiRepository repository = GteModeAwareApiRepository(
        config: const GteRepositoryConfig(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        fixtures: GteMockApi(),
        tokenStore: tokenStore,
      );

      await repository.createDepositRequest(
        const GteDepositCreateRequest(amount: 5000, inputUnit: 'fiat'),
      );
      await repository.submitDepositRequest(
        'dep-1',
        const GteDepositSubmitRequest(
          payerName: 'Ayo Martins',
          senderBank: 'GTEX Treasury Bank',
          transferReference: 'bank-ref-1',
          proofAttachmentId: 'proof-1',
        ),
      );
      await repository.fetchWithdrawalEligibility();
      await repository.fetchWithdrawalQuote(
        const GteWithdrawalQuoteRequest(amountCoin: 10),
      );
      await repository.createWithdrawalRequest(
        const GteWithdrawalCreateRequest(
          amountCoin: 10,
          bankAccountId: 'bank-1',
          sourceScope: 'trade',
        ),
      );
      await repository.listWithdrawalRequests();
      await repository.fetchKycProfile();
      await repository.submitKycProfile(
        const GteKycSubmitRequest(
          nin: '12345678901',
          addressLine1: '1 Stadium Road',
          country: 'Nigeria',
          idDocumentAttachmentId: 'kyc-proof-1',
        ),
      );
      await repository.openDispute(
        const GteDisputeCreateRequest(
          resourceType: 'deposit_request',
          resourceId: 'dep-1',
          reference: 'DEP-1',
          subject: 'Manual transfer review',
          message: 'Please review proof proof-1.',
          attachmentId: 'proof-1',
        ),
      );
      await repository.sendDisputeMessage(
        'dispute-1',
        const GteDisputeMessageRequest(
          message: 'Adding another audit note.',
          attachmentId: 'proof-1',
        ),
      );

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/wallets/deposits',
          '/api/v2/wallets/deposits/dep-1/submit',
          '/api/v2/wallets/withdrawals/eligibility',
          '/api/v2/wallets/withdrawals/quote',
          '/api/v2/wallets/withdrawals',
          '/api/v2/wallets/withdrawals',
          '/api/v2/kyc',
          '/api/v2/kyc',
          '/api/v2/disputes',
          '/api/v2/disputes/dispute-1/messages',
        ],
      );
      expect(transport.requests[0].body, <String, Object?>{
        'amount': 5000,
        'input_unit': 'fiat',
      });
      expect(
        transport.requests[1].body,
        containsPair('proof_attachment_id', 'proof-1'),
      );
      expect(
        transport.requests[4].body,
        containsPair('bank_account_id', 'bank-1'),
      );
      expect(transport.requests[8].body, containsPair('reference', 'DEP-1'));
      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.headers['Authorization'],
        ),
        everyElement('Bearer token-capital'),
      );
    },
  );
}

Map<String, Object?> _depositBody({
  String status = 'awaiting_payment',
  String? proofAttachmentId,
}) {
  return <String, Object?>{
    'id': 'dep-1',
    'reference': 'DEP-1',
    'status': status,
    'amount_fiat': 5000,
    'amount_coin': 5.5,
    'currency_code': 'NGN',
    'rate_value': 900,
    'rate_direction': 'fiat_per_coin',
    'bank_name': 'GTEX Treasury Bank',
    'bank_account_number': '0123456789',
    'bank_account_name': 'Global Talent Exchange',
    'bank_code': '999',
    'payer_name': 'Ayo Martins',
    'sender_bank': 'GTEX Treasury Bank',
    'transfer_reference': 'bank-ref-1',
    'proof_attachment_id': proofAttachmentId,
    'admin_notes': null,
    'created_at': '2026-05-27T10:00:00Z',
    'submitted_at':
        status == 'payment_submitted' ? '2026-05-27T10:10:00Z' : null,
    'reviewed_at': null,
    'confirmed_at': null,
    'rejected_at': null,
    'expires_at': '2026-05-28T10:00:00Z',
  };
}

Map<String, Object?> _eligibilityBody() {
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

Map<String, Object?> _withdrawalQuoteBody() {
  return <String, Object?>{
    'gross_amount': 10,
    'fee_amount': 1,
    'net_amount': 9,
    'total_debit': 11,
    'source_scope': 'trade',
    'currency_code': 'NGN',
    'rate_value': 900,
    'rate_direction': 'fiat_per_coin',
    'estimated_fiat_payout': 8100,
    'processor_mode': 'manual_bank_transfer',
    'payout_channel': 'bank_transfer',
    'fee_bps': 1000,
    'minimum_fee': 1,
    'eligibility': _eligibilityBody(),
    'blocked_reason': null,
  };
}

Map<String, Object?> _withdrawalBody({String status = 'pending_review'}) {
  return <String, Object?>{
    'id': 'wd-1',
    'payout_request_id': 'payout-1',
    'reference': 'WD-1',
    'status': status,
    'unit': 'coin',
    'amount_coin': 10,
    'amount_fiat': 9000,
    'currency_code': 'NGN',
    'rate_value': 900,
    'rate_direction': 'fiat_per_coin',
    'bank_name': 'GTEX Treasury Bank',
    'bank_account_number': '0123456789',
    'bank_account_name': 'Ayo Martins',
    'bank_code': '999',
    'kyc_status_snapshot': 'fully_verified',
    'kyc_tier_snapshot': 'fully_verified',
    'fee_amount': 1,
    'total_debit': 11,
    'notes': null,
    'created_at': '2026-05-27T10:00:00Z',
    'reviewed_at': null,
    'approved_at': null,
    'processed_at': null,
    'paid_at': null,
    'rejected_at': null,
    'cancelled_at': null,
  };
}

Map<String, Object?> _kycBody({String? idDocumentAttachmentId}) {
  return <String, Object?>{
    'id': 'kyc-1',
    'status': 'pending',
    'nin': '12345678901',
    'bvn': null,
    'address_line1': '1 Stadium Road',
    'address_line2': null,
    'city': 'Lagos',
    'state': 'Lagos',
    'country': 'Nigeria',
    'id_document_attachment_id': idDocumentAttachmentId,
    'submitted_at': '2026-05-27T10:00:00Z',
    'reviewed_at': null,
    'rejection_reason': null,
    'created_at': '2026-05-27T09:00:00Z',
    'updated_at': '2026-05-27T10:00:00Z',
  };
}

Map<String, Object?> _disputeBody() {
  return <String, Object?>{
    'id': 'dispute-1',
    'status': 'open',
    'reference': 'DEP-1',
    'resource_type': 'deposit_request',
    'resource_id': 'dep-1',
    'subject': 'Manual transfer review',
    'created_at': '2026-05-27T10:20:00Z',
    'updated_at': '2026-05-27T10:20:00Z',
    'last_message_at': '2026-05-27T10:20:00Z',
    'user_id': 'user-1',
    'user_email': 'user-1@gtex.test',
    'user_full_name': 'Ayo Martins',
    'user_phone_number': null,
    'messages': <Object?>[_disputeMessageBody()],
  };
}

Map<String, Object?> _disputeMessageBody() {
  return <String, Object?>{
    'id': 'message-1',
    'sender_user_id': 'user-1',
    'sender_role': 'user',
    'message': 'Please review proof proof-1.',
    'attachment_id': 'proof-1',
    'created_at': '2026-05-27T10:20:00Z',
  };
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}

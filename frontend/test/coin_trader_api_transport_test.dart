import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/coin_trader_redesign/coin_trader_redesign.dart';

void main() {
  test(
    'coin trader marketplace uses public lowercase ledger-unit query',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          GteTransportResponse(
            statusCode: 200,
            body: <Object?>[_profileBody()],
          ),
        ],
      );
      final GtexCoinTraderApi api = _api(transport);

      final List<GtexCoinTraderProfile> traders = await api.listTraders(
        coinUnit: 'CREDIT',
      );

      expect(traders, hasLength(1));
      expect(transport.requests.single.method, 'GET');
      expect(transport.requests.single.uri.path, '/api/coin-traders');
      expect(
        transport.requests.single.uri.queryParameters['coin_unit'],
        'credit',
      );
      expect(transport.requests.single.headers['Authorization'], isNull);
    },
  );

  test('coin trader order actions target live escrow endpoints', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_orderBody(status: 'created')],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_orderBody(status: 'payment_pending')],
        ),
        GteTransportResponse(statusCode: 201, body: _orderBody()),
        GteTransportResponse(
          statusCode: 200,
          body: _orderBody(status: 'payment_pending'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _orderBody(status: 'proof_submitted'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _orderBody(status: 'released'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _orderBody(status: 'refunded'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _orderBody(status: 'disputed'),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: _orderBody(status: 'admin_released'),
        ),
      ],
    );
    final GtexCoinTraderApi api = _api(transport);

    await api.listMyOrders();
    await api.listMyOrders(asTrader: true);
    await api.createOrder(
      traderProfileId: 'trader-profile-1',
      direction: 'user_buys',
      coinUnit: 'COIN',
      coinAmount: 500,
      fiatCurrency: 'NGN',
      paymentMethod: 'bank_transfer',
    );
    await api.acceptOrder('order-1');
    await api.submitProof(
      orderId: 'order-1',
      proofReference: 'receipt-9',
      proofUrl: 'https://proof.test/receipt-9',
      note: 'paid',
    );
    await api.confirmOrder('order-1');
    await api.cancelOrder('order-1');
    await api.disputeOrder(orderId: 'order-1', reason: 'Payment mismatch');
    await api.adminResolveOrder(
      'order-1',
      resolution: 'release',
      note: 'Admin reviewed receipt.',
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.method),
      <String>[
        'GET',
        'GET',
        'POST',
        'POST',
        'POST',
        'POST',
        'POST',
        'POST',
        'POST',
      ],
    );
    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/coin-traders/orders',
        '/api/coin-traders/orders',
        '/api/coin-traders/orders',
        '/api/coin-traders/orders/order-1/accept',
        '/api/coin-traders/orders/order-1/proof',
        '/api/coin-traders/orders/order-1/confirm',
        '/api/coin-traders/orders/order-1/cancel',
        '/api/coin-traders/orders/order-1/dispute',
        '/api/admin/coin-traders/orders/order-1/resolve',
      ],
    );
    expect(transport.requests.first.uri.queryParameters['as_trader'], 'false');
    expect(transport.requests[1].uri.queryParameters['as_trader'], 'true');
    expect(transport.requests[2].body, containsPair('coin_unit', 'coin'));
    expect(
      transport.requests[2].body,
      containsPair('payment_method', 'bank_transfer'),
    );
    expect(
      transport.requests[4].body,
      containsPair('proof_reference', 'receipt-9'),
    );
    expect(
      transport.requests[7].body,
      containsPair('reason', 'Payment mismatch'),
    );
    expect(transport.requests.last.body, <String, Object?>{
      'resolution': 'release',
      'note': 'Admin reviewed receipt.',
    });
    expect(
      transport.requests.map(
        (GteTransportRequest request) => request.headers['Authorization'],
      ),
      everyElement('Bearer token-1'),
    );
  });

  test(
    'coin trader profile, rate, and admin decisions send full payloads',
    () async {
      final _RecordingTransport transport =
          _RecordingTransport(<GteTransportResponse>[
            GteTransportResponse(statusCode: 201, body: _profileBody()),
            GteTransportResponse(statusCode: 200, body: _rateBody()),
            GteTransportResponse(statusCode: 200, body: _profileBody()),
            GteTransportResponse(statusCode: 200, body: _profileBody()),
            GteTransportResponse(statusCode: 200, body: _profileBody()),
          ]);
      final GtexCoinTraderApi api = _api(transport);

      await api.applyTraderProfile(
        displayName: 'Lagos OTC Desk',
        countryCode: 'ng',
        terms: const <String, Object?>{
          'same_name_account_only': true,
          'working_hours': '09:00-18:00',
        },
        paymentMethods: const <Map<String, Object?>>[
          <String, Object?>{'label': 'Bank transfer', 'type': 'bank_transfer'},
        ],
        bankAccounts: const <Map<String, Object?>>[
          <String, Object?>{'bank': 'GTBank'},
        ],
        metadata: const <String, Object?>{'operator': 'ops'},
      );
      await api.upsertRate(
        coinUnit: 'CREDIT',
        fiatCurrency: 'USD',
        buyRateFiat: 0.9,
        sellRateFiat: 1.1,
        minCoinAmount: 25,
        maxCoinAmount: 10000,
        availableLiquidity: 50000,
        isActive: false,
      );
      await api.adminApproveTrader(
        'trader-profile-1',
        tier: 'gold',
        note: 'Verified treasury funding.',
      );
      await api.adminRejectTrader('trader-profile-1', note: 'KYC failed.');
      await api.adminFreezeTrader('trader-profile-1', note: 'Risk hold.');

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/coin-traders/apply',
          '/api/coin-traders/me/rates',
          '/api/admin/coin-traders/trader-profile-1/approve',
          '/api/admin/coin-traders/trader-profile-1/reject',
          '/api/admin/coin-traders/trader-profile-1/freeze',
        ],
      );
      expect(transport.requests[0].body, containsPair('country_code', 'ng'));
      expect(
        (transport.requests[0].body as Map<String, Object?>)['terms'],
        containsPair('working_hours', '09:00-18:00'),
      );
      expect(
        (transport.requests[0].body as Map<String, Object?>)['bank_accounts'],
        <Map<String, Object?>>[
          <String, Object?>{'bank': 'GTBank'},
        ],
      );
      expect(transport.requests[1].method, 'PUT');
      expect(transport.requests[1].body, containsPair('coin_unit', 'credit'));
      expect(transport.requests[1].body, containsPair('fiat_currency', 'USD'));
      expect(transport.requests[1].body, containsPair('min_coin_amount', 25));
      expect(
        transport.requests[1].body,
        containsPair('max_coin_amount', 10000),
      );
      expect(transport.requests[1].body, containsPair('is_active', false));
      expect(transport.requests[2].body, <String, Object?>{
        'tier': 'gold',
        'note': 'Verified treasury funding.',
      });
      expect(transport.requests[3].body, <String, Object?>{
        'note': 'KYC failed.',
      });
      expect(transport.requests[4].body, <String, Object?>{
        'note': 'Risk hold.',
      });
    },
  );

  test('coin trader order model exposes lifecycle action flags', () {
    final GtexCoinTradeOrder created = GtexCoinTradeOrder.fromJson(
      _orderBody(status: 'created'),
    );
    final GtexCoinTradeOrder pending = GtexCoinTradeOrder.fromJson(
      _orderBody(status: 'payment_pending'),
    );
    final GtexCoinTradeOrder proofSubmitted = GtexCoinTradeOrder.fromJson(
      _orderBody(status: 'proof_submitted'),
    );
    final GtexCoinTradeOrder disputed = GtexCoinTradeOrder.fromJson(
      _orderBody(status: 'disputed'),
    );
    final GtexCoinTradeOrder released = GtexCoinTradeOrder.fromJson(
      _orderBody(status: 'released'),
    );

    expect(created.canAccept, isTrue);
    expect(created.canSubmitProof, isFalse);
    expect(pending.statusLabel, 'Payment Pending');
    expect(pending.canSubmitProof, isTrue);
    expect(pending.canSubmitProofFor(isTrader: false), isTrue);
    expect(pending.canSubmitProofFor(isTrader: true), isFalse);
    expect(pending.canAccept, isFalse);
    expect(pending.canConfirmRelease, isFalse);
    expect(pending.canConfirmReleaseFor(isTrader: false), isFalse);
    expect(pending.canCancel, isTrue);
    expect(pending.canDispute, isTrue);
    expect(pending.canAdminResolve, isTrue);
    expect(pending.paymentWindowExpiresAt, isNotNull);
    expect(pending.acceptedAt, isNotNull);
    expect(pending.termsSnapshotLabels, contains('Same Name Account Only'));
    expect(pending.proofLabels, contains('Proof Reference: receipt-9'));
    expect(pending.ledgerLabels, contains('Escrow Lock Entry Ids: 2'));
    expect(proofSubmitted.canConfirmRelease, isTrue);
    expect(proofSubmitted.canCancel, isFalse);
    expect(proofSubmitted.canConfirmReleaseFor(isTrader: true), isTrue);
    expect(proofSubmitted.canConfirmReleaseFor(isTrader: false), isFalse);
    expect(disputed.canAdminResolve, isTrue);
    expect(disputed.canCancel, isFalse);
    expect(released.canAdminResolve, isFalse);
    expect(released.canSubmitProof, isFalse);

    final GtexCoinTradeOrder sellPending = GtexCoinTradeOrder.fromJson(
      _orderBody(status: 'proof_submitted', direction: 'user_sells'),
    );
    expect(sellPending.canSubmitProofFor(isTrader: true), isTrue);
    expect(sellPending.canConfirmReleaseFor(isTrader: false), isTrue);
  });

  test('coin trader profile model exposes bank and term labels', () {
    final GtexCoinTraderProfile profile = GtexCoinTraderProfile.fromJson(
      _profileBody(),
    );

    expect(profile.paymentMethodLabels, contains('Bank transfer'));
    expect(profile.bankAccountLabels, contains('GTBank'));
    expect(profile.termLabels, contains('Same Name Account Only'));
    expect(profile.verificationLevel, 'standard');
    expect(profile.completedVolumeFiat, 12400000);
    expect(profile.disputeScore, 0.2);
    expect(profile.rates.single.spreadFiat, 30);
    expect(profile.rates.single.treasuryDepositRateFiat, 900);
    expect(profile.rates.single.treasuryWithdrawalRateFiat, 880);
    expect(profile.rates.single.minTraderBuyRateFiat, 820);
    expect(profile.rates.single.maxTraderSellRateFiat, 980);
    expect(profile.rates.single.maxTraderSpreadFiat, 120);
    expect(profile.rates.single.governanceStatus, 'compliant');
    expect(profile.rates.single.isRestricted, isFalse);
  });

  test('coin trader order chat and admin expiration transport endpoints', () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(
          statusCode: 201,
          body: <String, Object?>{
            'id': 'msg-1',
            'order_id': 'order-1',
            'sender_user_id': 'user-1',
            'sender_name': 'Buyer User',
            'message': 'Paid via bank transfer',
            'created_at': '2026-05-11T16:02:00Z',
          },
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[
            <String, Object?>{
              'id': 'msg-1',
              'order_id': 'order-1',
              'sender_user_id': 'user-1',
              'sender_name': 'Buyer User',
              'message': 'Paid via bank transfer',
              'created_at': '2026-05-11T16:02:00Z',
            },
          ],
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_orderBody(status: 'cancelled')],
        ),
      ],
    );
    final GtexCoinTraderApi api = _api(transport);

    final GtexCoinTradeMessage sentMsg = await api.sendOrderMessage(
      'order-1',
      'Paid via bank transfer',
    );
    expect(sentMsg.id, 'msg-1');
    expect(sentMsg.message, 'Paid via bank transfer');
    expect(transport.requests[0].method, 'POST');
    expect(transport.requests[0].uri.path, '/api/coin-traders/orders/order-1/messages');

    final List<GtexCoinTradeMessage> messages = await api.fetchOrderMessages('order-1');
    expect(messages, hasLength(1));
    expect(messages.first.senderName, 'Buyer User');
    expect(transport.requests[1].method, 'GET');
    expect(transport.requests[1].uri.path, '/api/coin-traders/orders/order-1/messages');

    final List<GtexCoinTradeOrder> expiredOrders = await api.adminExpireStaleOrders();
    expect(expiredOrders, hasLength(1));
    expect(expiredOrders.first.status, 'cancelled');
    expect(transport.requests[2].method, 'POST');
    expect(transport.requests[2].uri.path, '/api/admin/coin-traders/orders/expire-stale');
  });

  test(
    'didit trader kyc initiation, status retrieval, trusted handoff validation, exact rate lookup, and admin dual-unit liquidity',
    () async {
      final _RecordingTransport transport = _RecordingTransport(
        <GteTransportResponse>[
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'session_id': 'didit-sess-1',
              'provider': 'didit',
              'reference': 'gtex-ref-1',
              'verification_type': 'bvn_nin',
              'status': 'pending',
              'handoff_url': 'https://verify.didit.me/session/didit-sess-1',
            },
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'id': 'kyc-rec-1',
              'user_id': 'trader-user-1',
              'trader_profile_id': 'trader-profile-1',
              'provider': 'didit',
              'provider_reference': 'gtex-ref-1',
              'verification_type': 'bvn_nin',
              'status': 'pending',
              'decision': 'In Review',
              'checks_summary': <String, Object?>{
                'id_verification': 'Approved',
                'liveness': 'Approved',
              },
              'initiated_at': '2026-11-16T00:00:00Z',
            },
          ),
          const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found'},
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'flow': 'issue',
              'coin_unit': 'credit',
              'amount': 500,
              'available_balance': 1500,
            },
          ),
          const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'flow': 'redeem',
              'coin_unit': 'coin',
              'amount': 200,
              'available_balance': 800,
            },
          ),
        ],
      );
      final GtexCoinTraderApi api = _api(transport);

      final GtexTraderVerificationSession session = await api
          .initiateTraderVerification(
            verificationType: 'bvn_nin',
            callbackUrl: 'https://app.gtex.local/trader',
          );
      expect(session.provider, 'didit');
      expect(session.verificationType, 'bvn_nin');
      expect(session.hasTrustedDiditHandoffUrl, isTrue);
      expect(
        transport.requests[0].uri.path,
        '/api/coin-traders/verification/initiate',
      );
      expect(
        (transport.requests[0].body as Map<String, Object?>)['verification_type'],
        'bvn_nin',
      );

      const GtexTraderVerificationSession untrustedSession =
          GtexTraderVerificationSession(
            sessionId: 'bad-sess',
            provider: 'didit',
            reference: 'ref-bad',
            verificationType: 'full_kyc',
            status: 'pending',
            handoffUrl: 'https://evil.example/phish',
          );
      expect(untrustedSession.hasTrustedDiditHandoffUrl, isFalse);

      final GtexTraderVerificationStatus? status = await api
          .fetchTraderVerificationStatus();
      expect(status, isNotNull);
      expect(status!.decision, 'In Review');
      expect(status.isVerified, isFalse);
      expect(status.isRejected, isFalse);

      final GtexTraderVerificationStatus? missingStatus = await api
          .fetchTraderVerificationStatus();
      expect(missingStatus, isNull);

      final GtexCoinTraderProfile profileWithOnlyCredit =
          GtexCoinTraderProfile.fromJson(_profileBody());
      expect(profileWithOnlyCredit.exactRateFor('CREDIT'), isNotNull);
      expect(profileWithOnlyCredit.exactRateFor('COIN'), isNull);

      final Map<String, dynamic> issued = await api.adminIssueLiquidity(
        profileId: 'trader-profile-1',
        coinUnit: 'CREDIT',
        amount: 500,
        reference: 'admin-fnc-001',
        note: 'FNC restock',
      );
      expect(issued['coin_unit'], 'credit');
      expect(
        transport.requests[3].uri.path,
        '/api/admin/coin-traders/trader-profile-1/liquidity/issue',
      );
      expect(
        (transport.requests[3].body as Map<String, Object?>)['coin_unit'],
        'credit',
      );

      final Map<String, dynamic> redeemed = await api.adminRedeemLiquidity(
        profileId: 'trader-profile-1',
        coinUnit: 'COIN',
        amount: 200,
        reference: 'admin-gtc-001',
      );
      expect(redeemed['coin_unit'], 'coin');
      expect(
        transport.requests[4].uri.path,
        '/api/admin/coin-traders/trader-profile-1/liquidity/redeem',
      );
      expect(
        (transport.requests[4].body as Map<String, Object?>)['coin_unit'],
        'coin',
      );
    },
  );
}

GtexCoinTraderApi _api(_RecordingTransport transport) {
  return GtexCoinTraderApi(
    client: GteAuthedApi(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      accessToken: 'token-1',
      mode: GteBackendMode.live,
    ),
  );
}



Map<String, Object?> _profileBody() {
  return <String, Object?>{
    'id': 'trader-profile-1',
    'user_id': 'trader-user-1',
    'display_name': 'Lagos OTC Desk',
    'country_code': 'NG',
    'status': 'approved',
    'tier': 'gold',
    'verification_level': 'standard',
    'completion_rate': 98,
    'average_release_minutes': 7,
    'rating': 4.8,
    'completed_volume_fiat': 12400000,
    'dispute_score': 0.2,
    'terms': <String, Object?>{'same_name_account_only': true},
    'payment_methods': <Object?>[
      <String, Object?>{'label': 'Bank transfer', 'type': 'bank_transfer'},
    ],
    'bank_accounts': <Object?>[
      <String, Object?>{'bank': 'GTBank'},
    ],
    'liquidity_snapshot': <String, Object?>{},
    'rates': <Object?>[
      <String, Object?>{
        'id': 'rate-1',
        'trader_profile_id': 'trader-profile-1',
        'coin_unit': 'CREDIT',
        'fiat_currency': 'NGN',
        'buy_rate_fiat': 960,
        'sell_rate_fiat': 990,
        'min_coin_amount': 100,
        'max_coin_amount': 100000,
        'available_liquidity': 50000,
        'is_active': true,
        'spread_fiat': 30,
        'treasury_deposit_rate_fiat': 900,
        'treasury_withdrawal_rate_fiat': 880,
        'min_trader_buy_rate_fiat': 820,
        'max_trader_buy_rate_fiat': 890,
        'min_trader_sell_rate_fiat': 900,
        'max_trader_sell_rate_fiat': 980,
        'max_trader_spread_fiat': 120,
        'governance_status': 'compliant',
        'governance_reasons': <Object?>[],
      },
    ],
    'metadata_json': <String, Object?>{},
  };
}

Map<String, Object?> _rateBody() {
  return <String, Object?>{
    'id': 'rate-1',
    'trader_profile_id': 'trader-profile-1',
    'coin_unit': 'CREDIT',
    'fiat_currency': 'USD',
    'buy_rate_fiat': 0.9,
    'sell_rate_fiat': 1.1,
    'min_coin_amount': 25,
    'max_coin_amount': 10000,
    'available_liquidity': 50000,
    'is_active': false,
    'spread_fiat': 0.2,
    'governance_status': 'compliant',
    'governance_reasons': <Object?>[],
    'metadata_json': <String, Object?>{},
  };
}

Map<String, Object?> _orderBody({
  String status = 'payment_pending',
  String direction = 'user_buys',
}) {
  return <String, Object?>{
    'id': 'order-1',
    'trader_profile_id': 'trader-profile-1',
    'user_id': 'user-1',
    'direction': direction,
    'coin_unit': 'COIN',
    'coin_amount': 500,
    'quoted_rate_fiat': 990,
    'fiat_total': 495000,
    'fiat_currency': 'NGN',
    'status': status,
    'escrow_owner_user_id': 'trader-user-1',
    'idempotency_key': 'web-test-1',
    'payment_method': 'bank_transfer',
    'payment_window_expires_at': '2026-05-11T16:45:00Z',
    'accepted_at': '2026-05-11T16:00:00Z',
    'proof_submitted_at': '2026-05-11T16:05:00Z',
    'released_at': status == 'released' ? '2026-05-11T16:10:00Z' : null,
    'cancelled_at': status == 'refunded' ? '2026-05-11T16:12:00Z' : null,
    'disputed_at': status == 'disputed' ? '2026-05-11T16:15:00Z' : null,
    'proof': <String, Object?>{
      'proof_reference': 'receipt-9',
      'submitted_by_user_id': 'user-1',
    },
    'terms_snapshot': <String, Object?>{'same_name_account_only': true},
    'ledger_refs': <String, Object?>{
      'escrow_lock_entry_ids': <String>['ledger-1', 'ledger-2'],
    },
    'metadata_json': <String, Object?>{
      if (status == 'disputed') 'dispute': <String, Object?>{'reason': 'hold'},
    },
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

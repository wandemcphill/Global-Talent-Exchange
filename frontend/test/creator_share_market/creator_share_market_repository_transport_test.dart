import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/creator_share_market/data/creator_share_market_models.dart';
import 'package:gte_frontend/features/creator_share_market/data/creator_share_market_repository.dart';

void main() {
  test('creator share market repository uses creator ops routes', () async {
    const Map<String, Object?> marketBody = <String, Object?>{
      'id': 'market-1',
      'club_id': 'club-1',
      'club_name': 'Creator FC',
      'creator_user_id': 'creator-1',
      'issued_by_user_id': 'creator-1',
      'status': 'active',
      'share_price_coin': 12.5,
      'max_shares_issued': 1000,
      'shares_sold': 250,
      'shares_remaining': 750,
      'max_shares_per_fan': 100,
      'creator_controlled_shares': 550,
      'creator_control_bps': 5500,
      'shareholder_revenue_share_bps': 1500,
      'shareholder_count': 23,
      'total_purchase_volume_coin': 3125,
      'total_revenue_distributed_coin': 420,
      'metadata_json': <String, Object?>{},
      'revenue_streams': <String, Object?>{
        'match_winnings_coin': 100,
        'fan_growth_bonus_coin': 50,
        'trading_fees_coin': 10,
        'sponsorship_pool_coin': 20,
        'broadcast_rights_coin': 30,
        'total_coin': 210,
        'metadata_json': <String, Object?>{},
      },
      'valuation_ticker': <String, Object?>{
        'total_valuation_coin': 25000,
        'treasury_balance_coin': 5000,
        'player_market_value_coin': 12000,
        'infrastructure_value_coin': 8000,
        'recent_performance_score': 0.8,
        'recent_performance_multiplier': 1.1,
        'recent_performance_bonus_coin': 250,
        'implied_share_price_coin': 12,
        'market_share_price_coin': 12.5,
        'market_price_delta_coin': 0.5,
        'market_price_delta_bps': 417,
        'price_to_value_ratio': 1.04,
        'fan_count': 5000,
        'wins_last_five': 3,
        'draws_last_five': 1,
        'losses_last_five': 1,
        'points_last_five': 10,
        'last_refreshed_at': '2026-04-18T12:00:00Z',
        'metadata_json': <String, Object?>{},
      },
      'governance_policy': <String, Object?>{
        'governance_mode': 'creator_controlled',
        'vote_weight_model': 'pro_rata',
        'anti_takeover_enabled': true,
        'max_holder_bps': 2000,
        'owner_approval_threshold_bps': 6000,
        'proposal_share_threshold': 25,
        'quorum_share_bps': 1000,
        'shareholder_rights_preserved_on_sale': true,
      },
      'ownership_ledger': <String, Object?>{
        'current_owner_user_id': 'creator-1',
        'total_governance_shares': 1000,
        'shareholder_count': 23,
        'circulating_share_count': 250,
        'last_transfer_id': 'transfer-1',
        'last_transfer_at': '2026-04-18T12:00:00Z',
        'recent_entries': <Object?>[],
      },
      'created_at': '2026-04-18T12:00:00Z',
      'updated_at': '2026-04-18T12:00:00Z',
      'viewer_holding': null,
      'viewer_benefits': <String, Object?>{
        'shareholder': false,
        'share_count': 0,
        'has_priority_chat_visibility': false,
        'has_early_ticket_access': false,
        'has_cosmetic_voting_rights': false,
        'tournament_qualification_method': null,
        'cosmetic_vote_power': 0,
      },
    };
    const Map<String, Object?> purchaseBody = <String, Object?>{
      'id': 'purchase-1',
      'market_id': 'market-1',
      'club_id': 'club-1',
      'creator_user_id': 'creator-1',
      'user_id': 'user-1',
      'share_count': 5,
      'share_price_coin': 12.5,
      'total_price_coin': 62.5,
      'ledger_transaction_id': 'ledger-1',
      'metadata_json': <String, Object?>{},
      'created_at': '2026-04-18T12:00:00Z',
      'updated_at': '2026-04-18T12:00:00Z',
    };
    const Map<String, Object?> controlBody = <String, Object?>{
      'id': 'control-1',
      'control_key': 'fan_share_market',
      'max_shares_per_club': 10000,
      'max_shares_per_fan': 100,
      'shareholder_revenue_share_bps': 1500,
      'issuance_enabled': true,
      'purchase_enabled': true,
      'max_primary_purchase_value_coin': 5000,
      'metadata_json': <String, Object?>{},
      'created_at': '2026-04-18T12:00:00Z',
      'updated_at': '2026-04-18T12:00:00Z',
    };

    final _RecordingTransport transport =
        _RecordingTransport(<GteTransportResponse>[
          const GteTransportResponse(statusCode: 200, body: marketBody),
          const GteTransportResponse(statusCode: 200, body: marketBody),
          const GteTransportResponse(statusCode: 200, body: purchaseBody),
          const GteTransportResponse(statusCode: 200, body: null),
          const GteTransportResponse(statusCode: 200, body: <Object?>[]),
          const GteTransportResponse(statusCode: 200, body: controlBody),
          const GteTransportResponse(statusCode: 200, body: controlBody),
        ]);
    final CreatorShareMarketApiRepository repository =
        CreatorShareMarketApiRepository(
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

    await repository.fetchMarket('club-1');
    await repository.issueMarket(
      'club-1',
      const CreatorClubShareMarketIssueRequest(
        sharePriceCoin: 12.5,
        maxSharesIssued: 1000,
        maxSharesPerFan: 100,
      ),
    );
    await repository.purchaseShares(
      'club-1',
      const CreatorClubSharePurchaseRequest(shareCount: 5),
    );
    await repository.fetchHolding('club-1');
    await repository.fetchDistributions('club-1');
    await repository.fetchControl();
    await repository.updateControl(
      const CreatorClubShareMarketControlUpdateRequest(
        maxSharesPerClub: 10000,
        maxSharesPerFan: 100,
        shareholderRevenueShareBps: 1500,
        issuanceEnabled: true,
        purchaseEnabled: true,
        maxPrimaryPurchaseValueCoin: 5000,
      ),
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/v1/creator/clubs/club-1/fan-share-market',
        '/api/v1/creator/clubs/club-1/fan-share-market',
        '/api/v1/creator/clubs/club-1/fan-share-market/purchase',
        '/api/v1/creator/clubs/club-1/fan-share-market/holding',
        '/api/v1/creator/clubs/club-1/fan-share-market/distributions',
        '/api/v1/admin/creator/fan-share-market/control',
        '/api/v1/admin/creator/fan-share-market/control',
      ],
    );
    expect(
      transport.requests.map((GteTransportRequest request) => request.method),
      <String>['GET', 'POST', 'POST', 'GET', 'GET', 'GET', 'PUT'],
    );
  });
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

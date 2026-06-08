import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/creator/creator.dart';
import 'package:gte_frontend/features/shell/domain/gtex_surface_state.dart';

void main() {
  test(
    'repository uses canonical creator contracts and preserves states',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          'GET /api/v2/creator/profile': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'state': 'confirmed',
              'profile': <String, Object?>{
                'creator_id': 'creator-1',
                'display_name': 'Creator One',
                'status': 'approved',
              },
            },
          ),
          'GET /api/v2/creator/campaigns': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{'state': 'empty', 'campaigns': <Object?>[]},
          ),
          'GET /api/v2/creator/wallet': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'state': 'confirmed',
              'balance': <String, Object?>{
                'currency': 'credits',
                'available': '125.50',
                'reserved': '5.00',
              },
              'pending_settlements': 1,
              'withdrawal_available': true,
            },
          ),
          'GET /api/v2/creator/clips': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{'state': 'empty', 'clips': <Object?>[]},
          ),
          'GET /api/v2/creator/settlements': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'state': 'degraded',
              'degraded_reason': 'settlement wallet transaction missing',
              'settlements': <Object?>[
                <String, Object?>{
                  'id': 'settlement-1',
                  'status': 'pending',
                  'currency': 'credits',
                  'amount': null,
                  'degraded_reason': 'wallet transaction missing',
                },
              ],
            },
          ),
          'GET /api/v2/creator/moderation': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{'state': 'empty', 'items': <Object?>[]},
          ),
        },
      );
      final CreatorApiRepository repository = _repository(transport);

      final CreatorSurfaceState<CreatorProfileDto> profile =
          await repository.getProfile();
      final CreatorSurfaceState<List<CampaignDto>> campaigns =
          await repository.getCampaigns();
      final CreatorSurfaceState<CreatorWalletDto> wallet =
          await repository.getWallet();
      final CreatorSurfaceState<List<SponsoredClipDto>> clips =
          await repository.getClips();
      final CreatorSurfaceState<List<SettlementDto>> settlements =
          await repository.getSettlements();
      final CreatorSurfaceState<List<ModerationInboxItemDto>> moderation =
          await repository.getModerationInbox();

      expect(profile.state, GtexSurfaceState.confirmed);
      expect(profile.data?.displayName, 'Creator One');
      expect(campaigns.state, GtexSurfaceState.empty);
      expect(wallet.state, GtexSurfaceState.confirmed);
      expect(wallet.data?.balance?.available, 125.5);
      expect(wallet.data?.withdrawalAvailable, isTrue);
      expect(clips.state, GtexSurfaceState.empty);
      expect(settlements.state, GtexSurfaceState.degraded);
      expect(settlements.data?.single.amount, isNull);
      expect(moderation.state, GtexSurfaceState.empty);
      expect(
        transport.requests,
        containsAll(<String>[
          'GET /api/v2/creator/profile',
          'GET /api/v2/creator/campaigns',
          'GET /api/v2/creator/wallet',
          'GET /api/v2/creator/clips',
          'GET /api/v2/creator/settlements',
          'GET /api/v2/creator/moderation',
        ]),
      );
    },
  );

  test(
    'repository blocks withdrawals above backend available balance',
    () async {
      final CreatorApiRepository repository = _repository(
        _PathTransport(<String, GteTransportResponse>{
          'GET /api/v2/creator/wallet': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'balance': <String, Object?>{
                'currency': 'credits',
                'available': 50,
              },
              'withdrawal_available': true,
            },
          ),
        }),
      );

      final CreatorSurfaceState<CreatorWithdrawalReceiptDto> result =
          await repository.requestWithdrawal(
            const CreatorWithdrawalRequest(
              amount: 75,
              currency: 'credits',
              method: 'bank_transfer',
              auditRef: 'audit-withdrawal-2',
            ),
          );

      expect(result.state, GtexSurfaceState.blocked);
      expect(
        result.blockedReason,
        'creator.withdrawal.exceeds_available_balance',
      );
      expect(result.auditRef, 'audit-withdrawal-2');
    },
  );

  test(
    'repository blocks withdrawal without payout destination before mutation',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          'GET /api/v2/creator/wallet': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'balance': <String, Object?>{
                'currency': 'credits',
                'available': 100,
              },
              'withdrawal_available': true,
            },
          ),
        },
      );
      final CreatorApiRepository repository = _repository(transport);

      final CreatorSurfaceState<CreatorWithdrawalReceiptDto> result =
          await repository.requestWithdrawal(
            const CreatorWithdrawalRequest(
              amount: 25,
              currency: 'credits',
              method: 'bank_transfer',
              auditRef: 'audit-withdrawal-3',
            ),
          );

      expect(result.state, GtexSurfaceState.blocked);
      expect(result.blockedReason, 'creator.withdrawal.destination_missing');
      expect(
        transport.requests,
        isNot(contains('POST /api/v2/creator/wallet/withdraw')),
      );
    },
  );

  test(
    'repository posts withdrawal only when backend can authorize it',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          'GET /api/v2/creator/wallet': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'balance': <String, Object?>{
                'currency': 'credits',
                'available': 100,
              },
              'withdrawal_available': true,
            },
          ),
          'POST /api/v2/creator/wallet/withdraw': const GteTransportResponse(
            statusCode: 201,
            body: <String, Object?>{
              'state': 'confirmed',
              'withdrawal_id': 'withdrawal-1',
              'action_state': 'completed',
              'audit_reference': 'audit-backend-1',
            },
          ),
        },
      );
      final CreatorApiRepository repository = _repository(transport);

      final CreatorSurfaceState<CreatorWithdrawalReceiptDto> result =
          await repository.requestWithdrawal(
            const CreatorWithdrawalRequest(
              amount: 25,
              currency: 'credits',
              method: 'bank_transfer',
              destinationReference: 'bank-destination-1',
              auditRef: 'audit-withdrawal-4',
            ),
          );

      expect(result.state, GtexSurfaceState.confirmed);
      expect(result.data?.id, 'withdrawal-1');
      expect(result.auditRef, 'audit-backend-1');
      expect(
        transport.requests,
        contains('POST /api/v2/creator/wallet/withdraw'),
      );
    },
  );

  test('repository blocks action mutations without audit refs', () async {
    final CreatorApiRepository repository = _repository(
      _PathTransport(const <String, GteTransportResponse>{}),
    );

    final CreatorSurfaceState<CampaignDto> campaign = await repository
        .createCampaign(
          const CreateCampaignRequest(
            title: 'No audit',
            brief: 'Missing audit ref',
            auditRef: '',
          ),
        );
    final CreatorSurfaceState<void> clip = await repository.submitClip(
      const SubmitClipRequest(
        campaignId: 'campaign-1',
        title: 'No audit',
        url: 'https://clips.test/no-audit.mp4',
        auditRef: '',
      ),
    );

    expect(campaign.state, GtexSurfaceState.blocked);
    expect(campaign.blockedReason, 'creator.audit_ref_missing');
    expect(clip.state, GtexSurfaceState.blocked);
    expect(clip.blockedReason, 'creator.audit_ref_missing');
  });
}

CreatorApiRepository _repository(_PathTransport transport) {
  return CreatorApiRepository(
    client: GteAuthedApi(
      config: const GteRepositoryConfig(
        baseUrl: 'https://api.gtex.test',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      accessToken: 'token',
    ),
  );
}

class _PathTransport implements GteTransport {
  _PathTransport(this.responses);

  final Map<String, GteTransportResponse> responses;
  final List<String> requests = <String>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    final String key = '${request.method} ${request.uri.path}';
    requests.add(key);
    return responses[key] ??
        const GteTransportResponse(
          statusCode: 404,
          body: <String, Object?>{'detail': 'not_found'},
        );
  }
}

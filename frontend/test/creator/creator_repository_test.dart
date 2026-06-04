import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/creator/creator.dart';
import 'package:gte_frontend/features/shell/domain/gtex_surface_state.dart';

void main() {
  test(
    'repository uses existing creator contracts and degrades campaign truth',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          'GET /api/v2/creators/me/summary': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'profile': <String, Object?>{
                'creator_id': 'creator-1',
                'display_name': 'Creator One',
                'status': 'approved',
              },
            },
          ),
          'GET /api/v2/creators/me/competitions': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'competition_id': 'competition-1',
                'title': 'Sunday Cup',
              },
            ],
          ),
          'GET /api/v2/creators/me/finance': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'currency': 'credits',
              'wallet_available_balance': '125.50',
              'pending_withdrawals': 1,
            },
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

      expect(profile.state, GtexSurfaceState.confirmed);
      expect(profile.data?.displayName, 'Creator One');
      expect(campaigns.state, GtexSurfaceState.degraded);
      expect(campaigns.data?.single.title, 'Sunday Cup');
      expect(campaigns.message, contains('Module 7 campaign contract'));
      expect(wallet.state, GtexSurfaceState.confirmed);
      expect(wallet.data?.balance?.available, 125.5);
      expect(
        transport.requests,
        containsAll(<String>[
          'GET /api/v2/creators/me/summary',
          'GET /api/v2/creators/me/competitions',
          'GET /api/v2/creators/me/finance',
        ]),
      );
    },
  );

  test(
    'repository blocks withdrawals above backend available balance',
    () async {
      final CreatorApiRepository repository = _repository(
        _PathTransport(<String, GteTransportResponse>{
          'GET /api/v2/creators/me/finance': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'currency': 'credits',
              'wallet_available_balance': 50,
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

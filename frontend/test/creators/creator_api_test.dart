import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';

void main() {
  test(
    'creator api prefers media clip earnings endpoint for clip finance fields',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v1/creators/me/finance': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'currency': 'credits',
              'total_gift_income': '8.0000',
              'total_reward_income': '14.0000',
              'total_clip_income': '11.0000',
              'total_clip_views': 12,
              'monetized_clips': 1,
              'viral_clip_count': 0,
              'total_viral_bonus': '0.0000',
              'total_referral_bonus': '0.0000',
              'total_weekly_top_creator_bonus': '0.0000',
              'total_withdrawn_gross': '20.0000',
              'total_withdrawal_fees': '5.0000',
              'total_withdrawn_net': '20.0000',
              'pending_withdrawals': '0.0000',
              'wallet_balance': '11.0000',
              'wallet_available_balance': '11.0000',
              'wallet_currency': 'credits',
              'active_competitions': 2,
              'attributed_signups': 9,
              'qualified_joins': 6,
              'insights': <Object?>['Coarse creator summary'],
            },
          ),
          '/api/v1/media/me/clip-earnings': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'generated_clip_count': 4,
              'monetized_clip_count': 3,
              'total_views': 150000,
              'total_gross_revenue_credit': '200.0000',
              'total_creator_payout_credit': '165.0000',
              'total_platform_share_credit': '20.0000',
              'total_growth_pool_retained_credit': '10.0000',
              'total_viral_bonus_credit': '15.0000',
              'total_referral_bonus_credit': '4.5000',
              'total_weekly_top_creator_bonus_credit': '6.7500',
              'viral_clip_count': 1,
              'wallet_user_id': 'creator-1',
              'wallet_balance_credit': '165.0000',
              'wallet_available_credit': '150.0000',
              'wallet_currency': 'credits',
              'incentives': <Object?>[
                'Viral bonuses unlocked: 15.0000 credits.',
              ],
            },
          ),
        },
      );
      final CreatorApi api = CreatorApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token-1',
        mode: GteBackendMode.live,
        transport: transport,
      );

      final summary = await api.fetchCreatorFinance();

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v1/creators/me/finance',
          '/api/v1/media/me/clip-earnings',
        ],
      );
      expect(summary.totalGiftIncome, 8);
      expect(summary.totalRewardIncome, 14);
      expect(summary.totalClipIncome, 165);
      expect(summary.totalClipViews, 150000);
      expect(summary.monetizedClips, 3);
      expect(summary.viralClipCount, 1);
      expect(summary.totalViralBonus, 15);
      expect(summary.totalReferralBonus, 4.5);
      expect(summary.totalWeeklyTopCreatorBonus, 6.75);
      expect(summary.walletBalance, 165);
      expect(summary.walletAvailableBalance, 150);
      expect(summary.activeCompetitions, 2);
      expect(summary.insights, contains('Coarse creator summary'));
      expect(
        summary.insights,
        contains('Viral bonuses unlocked: 15.0000 credits.'),
      );
    },
  );

  test(
    'creator api falls back to coarse finance summary when clip earnings endpoint is unavailable',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v1/creators/me/finance': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'currency': 'credits',
              'total_gift_income': '2.0000',
              'total_reward_income': '3.0000',
              'total_clip_income': '7.0000',
              'total_clip_views': 900,
              'monetized_clips': 2,
              'viral_clip_count': 0,
              'total_viral_bonus': '0.0000',
              'total_referral_bonus': '1.0000',
              'total_weekly_top_creator_bonus': '0.5000',
              'total_withdrawn_gross': '0.0000',
              'total_withdrawal_fees': '0.0000',
              'total_withdrawn_net': '0.0000',
              'pending_withdrawals': '0.0000',
              'wallet_balance': '7.0000',
              'wallet_available_balance': '6.5000',
              'wallet_currency': 'credits',
              'active_competitions': 1,
              'attributed_signups': 2,
              'qualified_joins': 1,
              'insights': <Object?>['Finance summary only'],
            },
          ),
          '/api/v1/media/me/clip-earnings': const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found.'},
          ),
          '/api/media/me/clip-earnings': const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found.'},
          ),
        },
      );
      final CreatorApi api = CreatorApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token-1',
        mode: GteBackendMode.live,
        transport: transport,
      );

      final summary = await api.fetchCreatorFinance();

      expect(summary.totalClipIncome, 7);
      expect(summary.totalClipViews, 900);
      expect(summary.walletAvailableBalance, 6.5);
      expect(summary.totalReferralBonus, 1);
      expect(summary.insights, <String>['Finance summary only']);
    },
  );
}

class _PathTransport implements GteTransport {
  _PathTransport(this.responses);

  final Map<String, GteTransportResponse> responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return responses[request.uri.path] ??
        const GteTransportResponse(
          statusCode: 404,
          body: <String, Object?>{'detail': 'Not found.'},
        );
  }
}

import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/creator_models.dart';

void main() {
  test(
    'creator api current profile flow uses creators api routes and public community links',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/creators/me/summary': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'profile': <String, Object?>{
                'creator_id': 'creator-1',
                'user_id': 'user-1',
                'display_name': 'Maya Scout',
                'handle': 'maya_scout',
                'default_share_code': 'MAYA',
                'tier': 'elite',
                'status': 'active',
                'revenue_share_percent': 55,
              },
              'total_signups': 10,
              'qualified_joins': 4,
              'active_participants': 11,
              'pending_rewards': 2,
              'approved_rewards': 6,
            },
          ),
          '/api/v2/creators/me/competitions': const GteTransportResponse(
            statusCode: 200,
            body: <Object?>[
              <String, Object?>{
                'competition_id': 'comp-1',
                'title': 'Creator Cup',
                'active_participants': 11,
                'attributed_signups': 10,
                'qualified_joins': 4,
                'linked_share_code': 'MAYA',
              },
            ],
          ),
          '/api/v2/creators/me/finance': const GteTransportResponse(
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
        },
      );
      final CreatorApi api = CreatorApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token-1',
        mode: GteBackendMode.live,
        transport: transport,
      );

      final profile = await api.fetchCreatorProfile();

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/creators/me/summary',
          '/api/v2/creators/me/competitions',
          '/api/v2/creators/me/finance',
        ],
      );
      expect(profile.handle, 'maya_scout');
      expect(
        profile.profileLink,
        'https://example.test/community/creator/maya_scout',
      );
      expect(profile.stats.communityInvites, 10);
      expect(profile.competitions.single.competitionId, 'comp-1');
    },
  );

  test(
    'creator api public profile flow uses creators api route and community link',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/creators/maya_scout': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{
              'creator_id': 'creator-1',
              'user_id': 'user-1',
              'display_name': 'Maya Scout',
              'handle': 'maya_scout',
              'default_share_code': 'MAYA',
              'tier': 'elite',
              'status': 'active',
              'revenue_share_percent': 55,
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

      final profile = await api.fetchCreatorProfile(creatorId: 'maya_scout');

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>['/api/v2/creators/maya_scout'],
      );
      expect(profile.handle, 'maya_scout');
      expect(profile.displayName, 'Maya Scout');
      expect(profile.tier, 'elite');
      expect(
        profile.profileLink,
        'https://example.test/community/creator/maya_scout',
      );
      expect(profile.competitions, isEmpty);
      expect(profile.stats.communityInvites, 0);
    },
  );

  test(
    'creator api public profile falls back within creators api family when missing',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/creators/maya_scout': const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found.'},
          ),
          '/api/creators/maya_scout': const GteTransportResponse(
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

      await expectLater(
        api.fetchCreatorProfile(creatorId: 'maya_scout'),
        throwsA(
          isA<GteApiException>().having(
            (GteApiException error) => error.type,
            'type',
            GteApiErrorType.notFound,
          ),
        ),
      );

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>['/api/v2/creators/maya_scout', '/api/creators/maya_scout'],
      );
    },
  );

  test('creator api copilot analysis uses creators route', () async {
    final _PathTransport transport = _PathTransport(
      <String, GteTransportResponse>{
        '/api/v2/creators/me/copilot/analyze': const GteTransportResponse(
          statusCode: 200,
          body: <String, Object?>{'creator_id': 'creator-1'},
        ),
      },
    );
    final CreatorApi api = CreatorApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token-1',
      mode: GteBackendMode.live,
      transport: transport,
    );

    final CreatorCopilotAnalysis analysis = await api.analyzeCopilotDraft(
      const CreatorCopilotDraft(
        title: 'Goal breakdown',
        durationSeconds: 18,
        eventType: 'goal',
        tags: <String>['goal', 'highlight'],
        preferredFormat: 'instant',
        introSeconds: 1.2,
        visualIntensity: 0.7,
        eventDensity: 0.8,
        audienceCluster: 'general',
        hasReactionOverlay: true,
      ),
    );

    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>['/api/v2/creators/me/copilot/analyze'],
    );
    expect(
      transport.requests.map((GteTransportRequest request) => request.method),
      <String>['POST'],
    );
    expect(analysis.creatorId, 'creator-1');
  });

  test(
    'creator api copilot analysis falls back to legacy creators route',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/creators/me/copilot/analyze': const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found.'},
          ),
          '/creators/me/copilot/analyze': const GteTransportResponse(
            statusCode: 200,
            body: <String, Object?>{'creator_id': 'creator-legacy'},
          ),
        },
      );
      final CreatorApi api = CreatorApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token-1',
        mode: GteBackendMode.live,
        transport: transport,
      );

      final CreatorCopilotAnalysis analysis = await api.analyzeCopilotDraft(
        const CreatorCopilotDraft(
          title: 'Debate cut',
          durationSeconds: 24,
          eventType: 'analysis',
          tags: <String>['debate'],
          preferredFormat: 'debate',
          introSeconds: 1.6,
          visualIntensity: 0.5,
          eventDensity: 0.6,
          audienceCluster: 'tactics',
          hasReactionOverlay: false,
        ),
      );

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/creators/me/copilot/analyze',
          '/creators/me/copilot/analyze',
        ],
      );
      expect(analysis.creatorId, 'creator-legacy');
    },
  );

  test(
    'creator api prefers media clip earnings endpoint for clip finance fields',
    () async {
      final _PathTransport transport = _PathTransport(
        <String, GteTransportResponse>{
          '/api/v2/creators/me/finance': const GteTransportResponse(
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
          '/api/v2/media-engine/me/clip-earnings': const GteTransportResponse(
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
          '/api/v2/creators/me/finance',
          '/api/v2/media-engine/me/clip-earnings',
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
          '/api/v2/creators/me/finance': const GteTransportResponse(
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
          '/api/v2/media-engine/me/clip-earnings': const GteTransportResponse(
            statusCode: 404,
            body: <String, Object?>{'detail': 'Not found.'},
          ),
          '/media-engine/me/clip-earnings': const GteTransportResponse(
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

      expect(
        transport.requests.map(
          (GteTransportRequest request) => request.uri.path,
        ),
        <String>[
          '/api/v2/creators/me/finance',
          '/api/v2/media-engine/me/clip-earnings',
          '/media-engine/me/clip-earnings',
        ],
      );
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

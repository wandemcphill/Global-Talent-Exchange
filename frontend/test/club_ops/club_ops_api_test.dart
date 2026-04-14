import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  late http.Client Function() previousClientFactory;

  setUp(() {
    previousClientFactory = GteHttpTransport.clientFactory;
  });

  tearDown(() {
    GteHttpTransport.clientFactory = previousClientFactory;
  });

  test('club ops api merges live sponsorship catalog and overview', () async {
    final List<Map<String, Object?>> postBodies = <Map<String, Object?>>[];
    final List<Map<String, Object?>> patchBodies = <Map<String, Object?>>[];
    GteHttpTransport.clientFactory =
        () => MockClient((http.Request request) async {
          if (request.method == 'GET' &&
              request.url.path == '/api/v1/clubs/club-live/sponsorships') {
            return http.Response(
              jsonEncode(<String, Object?>{
                'club_id': 'club-live',
                'contracts': <Object?>[
                  <String, Object?>{
                    'id': 'contract-1',
                    'package_code': 'community-jersey-front',
                    'asset_type': 'jersey_front',
                    'sponsor_name': 'Harbor Energy',
                    'status': 'active',
                    'contract_amount_minor': 420000,
                    'currency': 'USD',
                    'duration_months': 6,
                    'payout_schedule': 'monthly',
                    'start_at': '2026-04-01T00:00:00Z',
                    'end_at': '2026-10-01T00:00:00Z',
                    'moderation_status': 'approved',
                    'asset_slot_codes': <Object?>['front-slot'],
                  },
                ],
                'visible_assets': <Object?>[
                  <String, Object?>{
                    'id': 'asset-1',
                    'asset_type': 'jersey_front',
                    'slot_code': 'front-slot',
                    'is_visible': true,
                    'rendered_text': 'Harbor Energy',
                    'moderation_status': 'approved',
                  },
                ],
                'active_contract_count': 1,
                'total_settled_revenue_minor': 140000,
              }),
              200,
            );
          }
          if (request.method == 'GET' &&
              request.url.path ==
                  '/api/v1/clubs/club-live/sponsorships/catalog') {
            return http.Response(
              jsonEncode(<String, Object?>{
                'packages': <Object?>[
                  <String, Object?>{
                    'id': 'pkg-community-jersey-front',
                    'code': 'community-jersey-front',
                    'name': 'Community Jersey Front',
                    'asset_type': 'jersey_front',
                    'base_amount_minor': 420000,
                    'currency': 'USD',
                    'default_duration_months': 6,
                    'payout_schedule': 'monthly',
                    'description':
                        'Front-of-shirt placement for community clubs.',
                  },
                ],
              }),
              200,
            );
          }
          if (request.method == 'POST' &&
              request.url.path ==
                  '/api/v1/clubs/club-live/sponsorships/contracts') {
            postBodies.add(
              Map<String, Object?>.from(
                jsonDecode(request.body) as Map<String, dynamic>,
              ),
            );
            return http.Response(
              jsonEncode(<String, Object?>{
                'id': 'contract-created',
                'package_code': 'community-jersey-front',
                'asset_type': 'jersey_front',
                'sponsor_name': 'Dockland Power',
                'status': 'pending_approval',
                'contract_amount_minor': 420000,
                'currency': 'USD',
                'duration_months': 6,
                'payout_schedule': 'monthly',
                'start_at': '2026-04-13T00:00:00Z',
                'end_at': '2026-10-13T00:00:00Z',
                'moderation_status': 'pending',
                'asset_slot_codes': <Object?>['front-slot'],
              }),
              201,
            );
          }
          if (request.method == 'PATCH' &&
              request.url.path ==
                  '/api/v1/clubs/club-live/sponsorships/contracts/contract-created') {
            patchBodies.add(
              Map<String, Object?>.from(
                jsonDecode(request.body) as Map<String, dynamic>,
              ),
            );
            return http.Response(
              jsonEncode(<String, Object?>{
                'id': 'contract-created',
                'package_code': 'community-jersey-front',
                'asset_type': 'jersey_front',
                'sponsor_name': 'Dockland Power',
                'status': 'pending_approval',
                'contract_amount_minor': 420000,
                'currency': 'USD',
                'duration_months': 6,
                'payout_schedule': 'monthly',
                'start_at': '2026-04-13T00:00:00Z',
                'end_at': '2026-10-13T00:00:00Z',
                'moderation_required': true,
                'moderation_status': 'pending',
                'custom_copy': 'Dockland Power Academy',
                'custom_logo_url': 'https://cdn.example.com/dockland.png',
                'settled_amount_minor': 0,
                'outstanding_amount_minor': 420000,
                'asset_slot_codes': <Object?>['front-slot'],
              }),
              200,
            );
          }
          return http.Response('{}', 404);
        });

    final ClubOpsApi api = ClubOpsApi.standard(
      baseUrl: 'http://example.com',
      mode: GteBackendMode.live,
      accessToken: 'token',
    );

    final SponsorshipDashboard dashboard = await api.fetchSponsorships(
      clubId: 'club-live',
      clubName: 'Club Live',
    );

    expect(dashboard.packages.single.code, 'community-jersey-front');
    expect(dashboard.contracts.single.packageName, 'Community Jersey Front');
    expect(dashboard.activeContractCount, 1);
    expect(dashboard.activeContractValue, 4200);
    expect(dashboard.settledRevenue, 1400);
    expect(dashboard.assetSlots.single.slotCode, 'front-slot');

    final SponsorshipContract created = await api.createSponsorshipContract(
      clubId: 'club-live',
      draft: const SponsorshipApplicationDraft(
        packageCode: 'community-jersey-front',
        sponsorName: 'Dockland Power',
        durationMonths: 6,
      ),
      packageNamesByCode: const <String, String>{
        'community-jersey-front': 'Community Jersey Front',
      },
    );

    expect(postBodies.single['package_code'], 'community-jersey-front');
    expect(postBodies.single['sponsor_name'], 'Dockland Power');
    expect(created.packageName, 'Community Jersey Front');
    expect(created.status, SponsorshipContractStatus.pendingApproval);

    final SponsorshipContract updated = await api.updateSponsorshipContract(
      clubId: 'club-live',
      contractId: 'contract-created',
      draft: const SponsorshipContractUpdateDraft(
        customCopy: 'Dockland Power Academy',
        customLogoUrl: 'https://cdn.example.com/dockland.png',
        moderationStatus: 'pending',
      ),
      packageNamesByCode: const <String, String>{
        'community-jersey-front': 'Community Jersey Front',
      },
    );

    expect(patchBodies.single['custom_copy'], 'Dockland Power Academy');
    expect(
      patchBodies.single['custom_logo_url'],
      'https://cdn.example.com/dockland.png',
    );
    expect(patchBodies.single['moderation_status'], 'pending');
    expect(patchBodies.single['settle_due_payouts'], false);
    expect(updated.customCopy, 'Dockland Power Academy');
    expect(updated.customLogoUrl, 'https://cdn.example.com/dockland.png');
    expect(updated.outstandingValue, 4200);
  });
}

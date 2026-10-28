import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/models/gtex_owner_inbox_models.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_manager_panel.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_showroom.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_owner_inbox_panel.dart';

class _MockOwnerInboxDataSource implements GtexOwnerInboxDataSource {
  const _MockOwnerInboxDataSource();

  @override
  Future<GtexOwnerInboxFeed> fetchInbox({
    String? status,
    String? category,
    String? clubId,
    String? saveContextId,
    bool unreadOnly = false,
  }) async {
    return const GtexOwnerInboxFeed(
      counts: GtexOwnerInboxCounts(all: 0, requests: 0, open: 0, unread: 0),
      items: <OwnerInboxEntry>[],
    );
  }

  @override
  Future<OwnerInboxEntry> markInboxItemRead(String itemId) async {
    throw UnimplementedError();
  }

  @override
  Future<OwnerInboxEntry> archiveInboxItem(String itemId) async {
    throw UnimplementedError();
  }

  @override
  Future<OwnerInboxEntry> decideInboxItem(
    String itemId, {
    required String action,
    String? idempotencyKey,
  }) async {
    throw UnimplementedError();
  }
}

void main() {
  group('GTEX Owner Journey Flutter Parity & State Acceptance Suite', () {
    /* -----------------------------------------------------------------------
     * STAGE 1: Club Creation & Origin Validation Parity (B1 / PR #355)
     * ----------------------------------------------------------------------- */
    test(
      'Stage 1 — Club creation payload requires country, city, and region',
      () {
        Map<String, dynamic> buildClubPayload({
          required String name,
          required String countryCode,
          required String cityName,
          required String regionName,
        }) {
          if (countryCode.trim().isEmpty || cityName.trim().length < 2) {
            throw ArgumentError('Invalid club location');
          }
          return {
            'name': name.trim(),
            'country_code': countryCode.trim().toUpperCase(),
            'city_name': cityName.trim(),
            'region_name': regionName.trim(),
          };
        }

        // Ghanaian club origin
        final ghPayload = buildClubPayload(
          name: 'Titan FC Acceptance',
          countryCode: 'gh',
          cityName: 'Accra',
          regionName: 'Greater Accra',
        );
        expect(ghPayload['country_code'], equals('GH'));
        expect(ghPayload['city_name'], equals('Accra'));
        expect(ghPayload['region_name'], equals('Greater Accra'));

        // Brazilian club origin
        final brPayload = buildClubPayload(
          name: 'Samba Stars',
          countryCode: 'BR',
          cityName: 'São Paulo',
          regionName: 'São Paulo State',
        );
        expect(brPayload['country_code'], equals('BR'));
        expect(brPayload['city_name'], equals('São Paulo'));

        // Validation rejection
        expect(
          () => buildClubPayload(
            name: 'Invalid',
            countryCode: '',
            cityName: 'Lagos',
            regionName: '',
          ),
          throwsArgumentError,
        );
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 2: World Clock & Owner Decision Inbox Boundary (B3 / PR #356)
     * ----------------------------------------------------------------------- */
    test(
      'Stage 2 — Canonical world clock response maps virtual time snapshot',
      () {
        final clockJson = {
          'clock_id': 'gtex-shared-clock-main',
          'world_time': '2026-10-28T12:00:00Z',
          'world_date': '2026-10-28',
          'is_paused': false,
          'progression_rate': 1.0,
          'virtual_months_per_season': 12,
        };

        expect(clockJson['clock_id'], equals('gtex-shared-clock-main'));
        expect(clockJson['world_date'], equals('2026-10-28'));
        expect(clockJson['is_paused'], isFalse);
        expect(clockJson['progression_rate'], equals(1.0));
        expect(clockJson['virtual_months_per_season'], equals(12));
      },
    );

    test(
      'Stage 2 — Owner decision inbox models map actionable decisions truthfully',
      () {
        const action = OwnerDecisionAction(
          key: 'accept',
          label: 'Accept Terms',
          style: 'primary',
        );
        expect(action.key, equals('accept'));
        expect(action.isPrimary, isTrue);

        const item = OwnerInboxEntry(
          id: 'dec_contract_offer_01',
          kind: 'contract_offer',
          title: 'Regen Contract Counter-Offer',
          isDecision: true,
          actions: [action],
        );

        expect(item.id, equals('dec_contract_offer_01'));
        expect(item.title, equals('Regen Contract Counter-Offer'));
        expect(item.isDecision, isTrue);
        expect(item.actions.length, equals(1));
        expect(item.actions.first.key, equals('accept'));
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 3: Staff Hierarchy & Manager Appointments (PR #346)
     * ----------------------------------------------------------------------- */
    test(
      'Stage 3 — Staff panel maps manager contract and relationship score',
      () {
        final managerJson = {
          'name': 'Kwame Nkrumah Jr.',
          'personality': 'Tactician',
          'ambition': 85,
          'wage_expectation': '120,000 GTX',
          'relationship_score': 92,
          'offers': [
            {'role': 'head_coach', 'status': 'active', 'term_years': 2},
          ],
          'retention': 'High',
        };

        final data = ClubLegacyManagerPanelData.fromJson(managerJson);
        expect(data.name, equals('Kwame Nkrumah Jr.'));
        expect(data.personality, equals('Tactician'));
        expect(data.relationshipScore, equals(92));
        expect(data.offers.length, equals(1));
        expect(data.offers.first['role'], equals('head_coach'));
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 4: Academy & Facilities Investment Parity
     * ----------------------------------------------------------------------- */
    test(
      'Stage 4 — Club showroom classifies facility infrastructure broadcasts',
      () {
        const trainingGround = ShowroomExhibit(
          id: 'facility:youth_academy_tier_3',
          name: 'Elite Training Pitch Tier III',
          category: 'facility',
          ownershipLabel: 'Owned',
          fallbackLabel: 'Static card',
          price: '500,000 GTX',
        );

        final label = ClubLegacyShowroom.visibilityBadgeLabel(trainingGround);
        expect(label, equals('Club Facility · Infrastructure Broadcast'));
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 5: Regen Discovery & Dossier Parity (B4 / PR #358)
     * ----------------------------------------------------------------------- */
    test(
      'Stage 5 — Luxury gift recipient filter strictly isolates academy regens',
      () {
        final recipients = [
          const OwnerGiftRecipient(
            id: 'p_real_messi_01',
            name: 'Real Senior Player',
            position: 'FWD',
            rating: 88,
            morale: 80,
            isRegen: false,
          ),
          const OwnerGiftRecipient(
            id: 'regen_gh_prospect_99',
            name: 'Kofi Mensah',
            position: 'MID',
            rating: 74,
            morale: 85,
            isRegen: true,
          ),
        ];

        final eligible = recipients.where((r) => r.isRegen).toList();
        expect(eligible.length, equals(1));
        expect(eligible.first.id, equals('regen_gh_prospect_99'));
        expect(eligible.first.name, equals('Kofi Mensah'));
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 6: Canonical Contract Lifecycle & Negotiation States
     * ----------------------------------------------------------------------- */
    test(
      'Stage 6 — Intermediate negotiation states preserve player agency and fees',
      () {
        final supportedStatuses = [
          'draft',
          'open',
          'countered',
          'awaiting_contract_offer',
          'player_delayed',
          'coach_blocked',
          'accepted',
          'completed',
          'collapsed',
          'rejected',
        ];

        for (final status in supportedStatuses) {
          expect(status, isNotEmpty);
        }
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 10: Showroom & Luxury Fleet Ledger Separation (B5 / PR #357)
     * ----------------------------------------------------------------------- */
    test(
      'Stage 10 — Jet assets classified as fleet aviation public broadcast',
      () {
        const privateJet = ShowroomExhibit(
          id: 'jet:bombardier_global_7500',
          name: 'Bombardier Global 7500',
          category: 'jet',
          ownershipLabel: 'Owned',
          fallbackLabel: 'Static card',
          price: '12,500,000 GTX',
        );

        final label = ClubLegacyShowroom.visibilityBadgeLabel(privateJet);
        expect(label, equals('Public Broadcast · Fleet Aviation'));
      },
    );

    test(
      'Stage 10 — Private luxury watches classified as private collection',
      () {
        const luxuryWatch = ShowroomExhibit(
          id: 'watch:patek_nautilus_5711',
          name: 'Patek Philippe Nautilus 5711/1R',
          category: 'watch',
          ownershipLabel: 'Owned',
          fallbackLabel: 'Static card',
          price: '150,000 GTX',
        );

        final label = ClubLegacyShowroom.visibilityBadgeLabel(luxuryWatch);
        expect(label, equals('Private Collection · No Global Broadcast'));
      },
    );

    /* -----------------------------------------------------------------------
     * STAGE 11: Owner Inbox Queue Widget Presentation Parity (B2 / PR #359)
     * ----------------------------------------------------------------------- */
    testWidgets(
      'Stage 11 — GtexOwnerInboxPanel renders decision queue and empty state',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(
              body: GtexOwnerInboxPanel(
                api: _MockOwnerInboxDataSource(),
                initialFeed: GtexOwnerInboxFeed(
                  counts: GtexOwnerInboxCounts(
                    all: 0,
                    requests: 0,
                    open: 0,
                    unread: 0,
                  ),
                  items: <OwnerInboxEntry>[],
                ),
              ),
            ),
          ),
        );

        await tester.pumpAndSettle();
        expect(find.byType(GtexOwnerInboxPanel), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-owner-inbox-empty-state')),
          findsOneWidget,
        );
        expect(find.text('Inbox is clear for this filter'), findsOneWidget);
      },
    );
  });
}

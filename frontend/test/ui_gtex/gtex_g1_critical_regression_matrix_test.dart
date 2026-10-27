import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/navigation/model/gtex_deep_link_resolver.dart';
import 'package:gte_frontend/features/navigation/model/gtex_route_alias_table.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  group('Phase G1 — Decision O-05 Workspace Destination Matrix', () {
    const GtexShellCapabilities fullCapabilities = GtexShellCapabilities(
      isAuthenticated: true,
      ownedClubIds: <String>['club-lagos'],
      activeClubId: 'club-lagos',
      isOrgScoutOrAgent: true,
      isCoinTrader: true,
      isCreator: true,
      isAdmin: true,
      clubLegacyEnabled: true,
      unreadInboxCount: 4,
      unreadNotificationCount: 3,
    );

    test(
      'maps all workspaces (club, scouting, trader/trading, creator, explore, admin, fan) to deterministic 5-slot primary destinations',
      () {
        const ShellNavigationModel model = ShellNavigationModel(
          capabilities: fullCapabilities,
        );

        // User/club-owner accounts never acquire Creator or Trader
        // workspaces from stale additive capability flags.
        expect(
          model.availableWorkspaces,
          orderedEquals(<GtexWorkspaceKind>[
            GtexWorkspaceKind.club,
            GtexWorkspaceKind.fan,
            GtexWorkspaceKind.scouting,
            GtexWorkspaceKind.admin,
          ]),
        );
        expect(model.availableWorkspaces, isNot(contains(GtexWorkspaceKind.trader)));
        expect(model.availableWorkspaces, isNot(contains(GtexWorkspaceKind.creator)));
        expect(model.showWorkspaceSwitcher, isTrue);

        // 1. Club workspace
        final List<GtexShellSlotSpec> clubSlots = model.primarySlotsFor(
          GtexWorkspaceKind.club,
        );
        expect(clubSlots, hasLength(5));
        expect(
          clubSlots.map((GtexShellSlotSpec s) => s.id).toList(),
          equals(<GtexShellSlotId>[
            GtexShellSlotId.home,
            GtexShellSlotId.club,
            GtexShellSlotId.matchday,
            GtexShellSlotId.market,
            GtexShellSlotId.more,
          ]),
        );
        expect(clubSlots[1].canonicalRoute, equals('/app/club/club-lagos'));

        // 2. Scouting workspace
        final List<GtexShellSlotSpec> scoutingSlots = model.primarySlotsFor(
          GtexWorkspaceKind.scouting,
        );
        expect(scoutingSlots, hasLength(5));
        expect(
          scoutingSlots.map((GtexShellSlotSpec s) => s.id).toList(),
          equals(<GtexShellSlotId>[
            GtexShellSlotId.home,
            GtexShellSlotId.recruitment,
            GtexShellSlotId.matchday,
            GtexShellSlotId.market,
            GtexShellSlotId.more,
          ]),
        );
        expect(
          scoutingSlots[1].canonicalRoute,
          equals('/app/club/club-lagos/recruitment'),
        );

        // 3. Trading (trader) workspace
        final List<GtexShellSlotSpec> tradingSlots = model.primarySlotsFor(
          GtexWorkspaceKind.trader,
        );
        expect(tradingSlots, hasLength(5));
        expect(
          tradingSlots.map((GtexShellSlotSpec s) => s.id).toList(),
          equals(<GtexShellSlotId>[
            GtexShellSlotId.home,
            GtexShellSlotId.traderDesk,
            GtexShellSlotId.market,
            GtexShellSlotId.wallet,
            GtexShellSlotId.more,
          ]),
        );
        expect(
          tradingSlots[1].canonicalRoute,
          equals(GtexCanonicalRoutes.walletTraderDesk),
        );

        // 4. Creator workspace
        final List<GtexShellSlotSpec> creatorSlots = model.primarySlotsFor(
          GtexWorkspaceKind.creator,
        );
        expect(creatorSlots, hasLength(5));
        expect(
          creatorSlots.map((GtexShellSlotSpec s) => s.id).toList(),
          equals(<GtexShellSlotId>[
            GtexShellSlotId.home,
            GtexShellSlotId.studio,
            GtexShellSlotId.matchday,
            GtexShellSlotId.community,
            GtexShellSlotId.more,
          ]),
        );
        expect(
          creatorSlots[1].canonicalRoute,
          equals(GtexCanonicalRoutes.studio),
        );

        // 5. Explore (guest) workspace
        const ShellNavigationModel guestModel = ShellNavigationModel(
          capabilities: GtexShellCapabilities(isAuthenticated: false),
        );
        expect(
          guestModel.availableWorkspaces,
          equals(const <GtexWorkspaceKind>[GtexWorkspaceKind.explore]),
        );
        final List<GtexShellSlotSpec> exploreSlots = guestModel.primarySlotsFor(
          GtexWorkspaceKind.explore,
        );
        expect(exploreSlots, hasLength(5));
        expect(
          exploreSlots.map((GtexShellSlotSpec s) => s.id).toList(),
          equals(<GtexShellSlotId>[
            GtexShellSlotId.explore,
            GtexShellSlotId.matchday,
            GtexShellSlotId.market,
            GtexShellSlotId.world,
            GtexShellSlotId.signIn,
          ]),
        );
        expect(
          exploreSlots.last.canonicalRoute,
          equals(GtexCanonicalRoutes.signIn),
        );

        // 6. Admin workspace
        final List<GtexShellSlotSpec> adminSlots = model.primarySlotsFor(
          GtexWorkspaceKind.admin,
        );
        expect(adminSlots, hasLength(5));
        expect(
          adminSlots.map((GtexShellSlotSpec s) => s.id).toList(),
          equals(<GtexShellSlotId>[
            GtexShellSlotId.ops,
            GtexShellSlotId.queues,
            GtexShellSlotId.matchday,
            GtexShellSlotId.treasury,
            GtexShellSlotId.more,
          ]),
        );
        expect(adminSlots[0].canonicalRoute, equals(GtexCanonicalRoutes.admin));
        expect(
          adminSlots[1].canonicalRoute,
          equals(GtexCanonicalRoutes.adminQueues),
        );
      },
    );
  });

  group('Phase G1 — MR1 Legacy Alias Redirects & Deep-Link Resolution', () {
    test(
      'GtexRouteAliasTable resolves legacy aliases and preserves path/query parameters',
      () {
        const String clubId = 'club-lagos';

        expect(
          GtexRouteAliasTable.resolve(
            '/matches/viewer/match-901',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/matchday/match/match-901'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/matches/broadcast/match-902',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/matchday/match/match-902'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/matches/3d/match-903',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/matchday/match/match-903'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/competitions/league/comp-42',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/matchday/competitions/comp-42'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/world/federations/caf-west',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/world/federations/caf-west'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/market/transfers/offer-501',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/club/club-lagos/transfers/offers/offer-501'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/clubs/club-accra/identity',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/app/club/club-accra/identity'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/players/player-88/profile',
            activeClubId: clubId,
          ).canonicalPath,
          equals('/players/player-88'),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/app/market?mode=ownership',
            activeClubId: clubId,
          ).canonicalPath,
          equals(GtexCanonicalRoutes.walletHoldings),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/app/market?mode=cards',
            activeClubId: clubId,
          ).canonicalPath,
          equals(GtexCanonicalRoutes.marketCards),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/owner/newsroom',
            activeClubId: clubId,
          ).canonicalPath,
          equals(GtexCanonicalRoutes.newsroom),
        );
        expect(
          GtexRouteAliasTable.resolve(
            '/owner/inbox',
            activeClubId: clubId,
          ).canonicalPath,
          equals(GtexCanonicalRoutes.inbox),
        );
      },
    );

    test(
      'GtexDeepLinkResolver resolves inbox, notification, and ticker payloads without losing entity IDs',
      () {
        final GtexResolvedDeepLink transferOfferLink =
            GtexDeepLinkResolver.resolveInboxItem(<String, Object?>{
              'id': 'inb-101',
              'kind': 'transfer_offer',
              'club_id': 'club-lagos',
              'metadata_json': <String, Object?>{'offer_id': 'offer-777'},
            });
        expect(
          transferOfferLink.canonicalRoute,
          equals('/app/club/club-lagos/transfers/offers/offer-777'),
        );
        expect(transferOfferLink.usedFallback, isFalse);

        final GtexResolvedDeepLink approvalLink =
            GtexDeepLinkResolver.resolveInboxItem(<String, Object?>{
              'id': 'inb-202',
              'kind': 'approval_required',
              'respond_by': '2026-10-25T00:00:00Z',
            });
        expect(approvalLink.canonicalRoute, equals('/app/inbox/inb-202'));
        expect(approvalLink.usedFallback, isFalse);

        final GtexResolvedDeepLink matchNotifLink =
            GtexDeepLinkResolver.resolveNotification(<String, Object?>{
              'id': 'notif-1',
              'fixture_id': 'fix-303',
            });
        expect(
          matchNotifLink.canonicalRoute,
          equals('/app/matchday/match/fix-303'),
        );

        final GtexResolvedDeepLink tickerArticleLink =
            GtexDeepLinkResolver.resolveTickerEvent(<String, Object?>{
              'id': 'tick-1',
              'article_id': 'art-808',
            });
        expect(
          tickerArticleLink.canonicalRoute,
          equals('/app/newsroom/art-808'),
        );
      },
    );
  });

  group('Phase G1 — MR5 GtexStatusPresenter Complete Backend Enum Matrix', () {
    test(
      'maps all 16 canonical backend statuses to deterministic labels, icons, and tones',
      () {
        final Map<String, (GtexSemanticStatusKind, String, IconData, bool)>
        expectedMatrix =
            <String, (GtexSemanticStatusKind, String, IconData, bool)>{
              'pending': (
                GtexSemanticStatusKind.warning,
                'Pending',
                Icons.schedule_rounded,
                false,
              ),
              'awaiting_payment': (
                GtexSemanticStatusKind.warning,
                'Pending',
                Icons.schedule_rounded,
                false,
              ),
              'payment_submitted': (
                GtexSemanticStatusKind.warning,
                'In review',
                Icons.schedule_rounded,
                false,
              ),
              'under_review': (
                GtexSemanticStatusKind.warning,
                'In review',
                Icons.schedule_rounded,
                false,
              ),
              'processing': (
                GtexSemanticStatusKind.info,
                'Processing',
                Icons.sync_rounded,
                false,
              ),
              'held': (
                GtexSemanticStatusKind.info,
                'On hold',
                Icons.pause_circle_outline_rounded,
                false,
              ),
              'confirmed': (
                GtexSemanticStatusKind.success,
                'Confirmed',
                Icons.check_circle_outline_rounded,
                false,
              ),
              'completed': (
                GtexSemanticStatusKind.success,
                'Done',
                Icons.check_circle_outline_rounded,
                false,
              ),
              'verified': (
                GtexSemanticStatusKind.success,
                'Confirmed',
                Icons.check_circle_outline_rounded,
                false,
              ),
              'rejected': (
                GtexSemanticStatusKind.danger,
                'Rejected',
                Icons.cancel_outlined,
                false,
              ),
              'expired': (
                GtexSemanticStatusKind.danger,
                'Expired',
                Icons.cancel_outlined,
                false,
              ),
              'cancelled': (
                GtexSemanticStatusKind.danger,
                'Cancelled',
                Icons.cancel_outlined,
                false,
              ),
              'reversed': (
                GtexSemanticStatusKind.dangerOutline,
                'Reversed',
                Icons.undo_rounded,
                true,
              ),
              'retracted': (
                GtexSemanticStatusKind.dangerOutline,
                'Retracted',
                Icons.undo_rounded,
                true,
              ),
              'disputed': (
                GtexSemanticStatusKind.dangerOutline,
                'Disputed',
                Icons.flag_outlined,
                true,
              ),
              'live': (
                GtexSemanticStatusKind.live,
                'Live',
                Icons.sensors_rounded,
                false,
              ),
            };

        for (final MapEntry<
              String,
              (GtexSemanticStatusKind, String, IconData, bool)
            >
            entry
            in expectedMatrix.entries) {
          final GtexPresentedStatus presented = GtexStatusPresenter.present(
            entry.key,
          );
          final (
            GtexSemanticStatusKind expectedKind,
            String expectedLabel,
            IconData expectedIcon,
            bool expectedOutlined,
          ) = entry.value;

          expect(
            presented.kind,
            equals(expectedKind),
            reason: '${entry.key} kind mismatch',
          );
          expect(
            presented.label,
            equals(expectedLabel),
            reason: '${entry.key} label mismatch',
          );
          expect(
            presented.icon,
            equals(expectedIcon),
            reason: '${entry.key} icon mismatch',
          );
          expect(
            presented.outlined,
            equals(expectedOutlined),
            reason: '${entry.key} outlined mismatch',
          );
          expect(presented.isUnknown, isFalse);
        }
      },
    );
  });

  group('Phase G1 — MR25 CI Hex-Literal Gate', () {
    test(
      'canonical P9-SHELL component and layout files contain zero raw Color(0x...) literals outside gtex_colors.dart',
      () {
        const List<String> p9ShellFiles = <String>[
          'lib/ui_gtex/components/gtex_status_presenter.dart',
          'lib/ui_gtex/components/gtex_confirm_sheet.dart',
          'lib/ui_gtex/components/gtex_attention_card.dart',
          'lib/ui_gtex/components/gtex_money.dart',
          'lib/ui_gtex/components/gtex_policy_chip.dart',
          'lib/ui_gtex/layout/gtex_top_bar.dart',
          'lib/ui_gtex/layout/gtex_nav_bar.dart',
          'lib/ui_gtex/layout/gtex_more_sheet.dart',
          'lib/ui_gtex/layout/gtex_shell_scaffold.dart',
        ];

        final RegExp rawHexColorPattern = RegExp(r'Color\(\s*0x[0-9A-Fa-f]+\s*\)');

        for (final String relativePath in p9ShellFiles) {
          final File file = File(relativePath);
          expect(
            file.existsSync(),
            isTrue,
            reason: 'Expected canonical file $relativePath to exist',
          );
          final String content = file.readAsStringSync();
          final Iterable<RegExpMatch> matches = rawHexColorPattern.allMatches(
            content,
          );
          expect(
            matches,
            isEmpty,
            reason:
                '$relativePath must not contain raw Color(0x...) literals; use GtexColors.navy tokens instead.',
          );
        }
      },
    );
  });
}

import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/navigation/model/gtex_deep_link_resolver.dart';
import 'package:gte_frontend/features/navigation/model/gtex_route_alias_table.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';

void main() {
  group('Phase A3 — ShellNavigationModel workspace & slot matrix', () {
    test('produces exact 5-slot phone bottom bar per workspace (Document E1)', () {
      final Map<GtexWorkspaceKind, List<String>> expectedSlotLabels =
          <GtexWorkspaceKind, List<String>>{
            GtexWorkspaceKind.club: <String>[
              'Home',
              'Club',
              'Matchday',
              'Market',
              'More',
            ],
            GtexWorkspaceKind.fan: <String>[
              'Home',
              'Matchday',
              'Market',
              'World',
              'More',
            ],
            GtexWorkspaceKind.scouting: <String>[
              'Home',
              'Recruitment',
              'Matchday',
              'Market',
              'More',
            ],
            GtexWorkspaceKind.trader: <String>[
              'Home',
              'Trader Desk',
              'Market',
              'Wallet',
              'More',
            ],
            GtexWorkspaceKind.creator: <String>[
              'Home',
              'Studio',
              'Matchday',
              'Community',
              'More',
            ],
            GtexWorkspaceKind.admin: <String>[
              'Ops',
              'Queues',
              'Matchday',
              'Treasury',
              'More',
            ],
            GtexWorkspaceKind.explore: <String>[
              'Explore',
              'Matchday',
              'Market',
              'World',
              'Sign in',
            ],
          };

      const ShellNavigationModel model = ShellNavigationModel(
        capabilities: GtexShellCapabilities(
          isAuthenticated: true,
          ownedClubIds: <String>['royal-lagos-fc'],
          activeClubId: 'royal-lagos-fc',
          isOrgScoutOrAgent: true,
          isCoinTrader: true,
          isCreator: true,
          isAdmin: true,
          clubLegacyEnabled: true,
        ),
      );

      for (final MapEntry<GtexWorkspaceKind, List<String>> entry
          in expectedSlotLabels.entries) {
        final List<GtexShellSlotSpec> slots = model.primarySlotsFor(entry.key);
        expect(slots, hasLength(5), reason: '${entry.key} must have 5 slots');
        expect(
          slots.map((GtexShellSlotSpec s) => s.label).toList(),
          orderedEquals(entry.value),
          reason: '${entry.key} slot order',
        );
      }
    });

    test('multi-role user gets Workspace Switcher and honors lastUsedWorkspace / selectedWorkspace (O-05)', () {
      final GtexShellCapabilities capabilities =
          GtexShellCapabilities.fromSessionMap(
            sessionJson: <String, Object?>{
              'current_club_id': 'royal-lagos-fc',
              'user': <String, Object?>{
                'id': 'user-1',
                'role': 'coin_trader',
                'permissions': <String>['creator.studio', 'scouting.access'],
              },
            },
            ownedClubIds: const <String>['royal-lagos-fc'],
            unreadInboxCount: 4,
            unreadNotificationCount: 3,
          );

      final ShellNavigationModel defaultModel = ShellNavigationModel(
        capabilities: capabilities,
      );
      expect(defaultModel.showWorkspaceSwitcher, isTrue);
      expect(
        defaultModel.availableWorkspaces,
        orderedEquals(<GtexWorkspaceKind>[
          GtexWorkspaceKind.club,
          GtexWorkspaceKind.fan,
          GtexWorkspaceKind.scouting,
          GtexWorkspaceKind.trader,
          GtexWorkspaceKind.creator,
        ]),
      );
      // Default workspace prefers Club if owner when lastUsedWorkspace is null.
      expect(defaultModel.activeWorkspace, GtexWorkspaceKind.club);
      // Owner top-bar attention count combines unreadInboxCount + unreadNotificationCount.
      expect(defaultModel.topBarAttentionCount, 7);

      final ShellNavigationModel lastUsedTrader = ShellNavigationModel(
        capabilities: capabilities,
        lastUsedWorkspace: GtexWorkspaceKind.trader,
      );
      expect(lastUsedTrader.activeWorkspace, GtexWorkspaceKind.trader);

      final ShellNavigationModel switchedCreator = ShellNavigationModel(
        capabilities: capabilities,
        lastUsedWorkspace: GtexWorkspaceKind.trader,
        selectedWorkspace: GtexWorkspaceKind.creator,
      );
      expect(switchedCreator.activeWorkspace, GtexWorkspaceKind.creator);
    });

    test('clubLegacyEnabled flag gates Boardroom in More sheet without hiding sporting Club routes', () {
      const ShellNavigationModel flagOffModel = ShellNavigationModel(
        capabilities: GtexShellCapabilities(
          isAuthenticated: true,
          ownedClubIds: <String>['lagos-stars'],
          activeClubId: 'lagos-stars',
          clubLegacyEnabled: false,
        ),
      );
      expect(
        flagOffModel.moreDestinations.any(
          (GtexSecondaryDestinationSpec d) =>
              d.id == GtexSecondaryDestinationId.boardroom,
        ),
        isFalse,
      );
      expect(
        flagOffModel.primarySlots[1].canonicalRoute,
        '/app/club/lagos-stars',
      );

      const ShellNavigationModel flagOnModel = ShellNavigationModel(
        capabilities: GtexShellCapabilities(
          isAuthenticated: true,
          ownedClubIds: <String>['lagos-stars'],
          activeClubId: 'lagos-stars',
          clubLegacyEnabled: true,
        ),
      );
      expect(
        flagOnModel.moreDestinations.any(
          (GtexSecondaryDestinationSpec d) =>
              d.id == GtexSecondaryDestinationId.boardroom &&
              d.canonicalRoute == '/app/club/lagos-stars/boardroom',
        ),
        isTrue,
      );
    });
  });

  group('Phase A3 — GtexRouteAliasTable legacy compatibility', () {
    test('maps legacy routes to Document E3 canonical routes', () {
      expect(
        GtexRouteAliasTable.resolve('/app/play/overview').canonicalPath,
        '/app/matchday',
      );
      expect(
        GtexRouteAliasTable.resolve('/matches/viewer/match-99').canonicalPath,
        '/app/matchday/match/match-99',
      );
      expect(
        GtexRouteAliasTable.resolve('/matches/3d/match-99').canonicalPath,
        '/app/matchday/match/match-99',
      );
      expect(
        GtexRouteAliasTable.resolve(
          '/lineup',
          activeClubId: 'royal-lagos-fc',
        ).canonicalPath,
        '/app/club/royal-lagos-fc/squad/lineup',
      );
      expect(
        GtexRouteAliasTable.resolve(
          '/football/transfer-center',
          activeClubId: 'royal-lagos-fc',
        ).canonicalPath,
        '/app/club/royal-lagos-fc/transfers',
      );
      expect(
        GtexRouteAliasTable.resolve('/app/market?mode=ownership').canonicalPath,
        '/app/wallet/holdings',
      );
      expect(
        GtexRouteAliasTable.resolve('/app/regens').canonicalPath,
        '/app/world/regens',
      );
      expect(
        GtexRouteAliasTable.resolve('/news').canonicalPath,
        '/app/newsroom',
      );
      expect(
        GtexRouteAliasTable.resolve('/players/p-42/profile').canonicalPath,
        '/players/p-42',
      );
      expect(
        GtexRouteAliasTable.resolve('/gtex/jackpot').canonicalPath,
        '/app/wallet/jackpot',
      );
    });
  });

  group('Phase A3 — GtexDeepLinkResolver server payload resolution', () {
    test('resolves inbox payloads for approvals, scouting, transfers, boardroom, and unknown fallback', () {
      expect(
        GtexDeepLinkResolver.resolveInboxItem(<String, Object?>{
          'id': 'dec-101',
          'kind': 'legacy_approval',
        }, activeClubId: 'royal-lagos-fc').canonicalRoute,
        '/app/inbox/dec-101',
      );

      expect(
        GtexDeepLinkResolver.resolveInboxItem(<String, Object?>{
          'id': 'item-202',
          'category': 'scouting_report',
        }, activeClubId: 'royal-lagos-fc').canonicalRoute,
        '/app/club/royal-lagos-fc/recruitment',
      );

      expect(
        GtexDeepLinkResolver.resolveInboxItem(<String, Object?>{
          'id': 'item-303',
          'kind': 'transfer_offer',
          'metadata_json': <String, Object?>{'offer_id': 'off-77'},
        }, activeClubId: 'royal-lagos-fc').canonicalRoute,
        '/app/club/royal-lagos-fc/transfers/offers/off-77',
      );

      // Unknown target falls back safely to `/app/inbox/:itemId` (never error screen).
      final GtexResolvedDeepLink unknown = GtexDeepLinkResolver.resolveInboxItem(
        <String, Object?>{'id': 'mystery-99', 'kind': 'unrecognized_event'},
        activeClubId: 'royal-lagos-fc',
      );
      expect(unknown.canonicalRoute, '/app/inbox/mystery-99');
      expect(unknown.usedFallback, isTrue);
    });

    test('resolves notification records across metadata_json deep_link_route, fixture_id, competition_id, and fallback', () {
      expect(
        GtexDeepLinkResolver.resolveNotification(<String, Object?>{
          'id': 'notif-1',
          'metadata_json': <String, Object?>{
            'deep_link_route': '/matches/viewer/fix-500',
          },
        }).canonicalRoute,
        '/app/matchday/match/fix-500',
      );

      expect(
        GtexDeepLinkResolver.resolveNotification(<String, Object?>{
          'id': 'notif-2',
          'competition_id': 'comp-elite-1',
          'template_key': 'ROUND_STARTED',
        }).canonicalRoute,
        '/app/matchday/competitions/comp-elite-1',
      );

      final GtexResolvedDeepLink fallback =
          GtexDeepLinkResolver.resolveNotification(<String, Object?>{
            'id': 'notif-fallback',
            'template_key': 'GENERAL_NOTICE',
          });
      expect(fallback.canonicalRoute, '/app/inbox/notif-fallback');
      expect(fallback.usedFallback, isTrue);
    });

    test('resolves global broadcast ticker items to newsroom article, match, player, or club', () {
      expect(
        GtexDeepLinkResolver.resolveTickerEvent(<String, Object?>{
          'article_id': 'art-88',
          'headline': 'Royal Lagos FC acquire Gulfstream G700',
        }).canonicalRoute,
        '/app/newsroom/art-88',
      );

      expect(
        GtexDeepLinkResolver.resolveTickerEvent(<String, Object?>{
          'club_id': 'royal-lagos-fc',
          'event_type': 'private_jet_purchase',
        }).canonicalRoute,
        '/app/world/clubs/royal-lagos-fc',
      );
    });
  });
}

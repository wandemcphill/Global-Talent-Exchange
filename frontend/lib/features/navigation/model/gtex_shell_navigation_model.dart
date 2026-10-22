import 'package:flutter/material.dart';

import 'gtex_route_alias_table.dart';

/// Canonical workspace kinds derived strictly from server session and ownership
/// data (Master Plan Document D2 & E1, Decision O-05).
enum GtexWorkspaceKind {
  explore,
  fan,
  club,
  scouting,
  trader,
  creator,
  admin,
}

extension GtexWorkspaceKindX on GtexWorkspaceKind {
  String get label {
    return switch (this) {
      GtexWorkspaceKind.explore => 'Explore',
      GtexWorkspaceKind.fan => 'Fan',
      GtexWorkspaceKind.club => 'Club',
      GtexWorkspaceKind.scouting => 'Scouting',
      GtexWorkspaceKind.trader => 'Trader',
      GtexWorkspaceKind.creator => 'Creator',
      GtexWorkspaceKind.admin => 'Admin',
    };
  }

  String get switcherTitle {
    return switch (this) {
      GtexWorkspaceKind.explore => 'Spectator / Explore',
      GtexWorkspaceKind.fan => 'Fan Workspace',
      GtexWorkspaceKind.club => 'Club Owner / Manager',
      GtexWorkspaceKind.scouting => 'Talent Scout / Agent',
      GtexWorkspaceKind.trader => 'Investor / Trader',
      GtexWorkspaceKind.creator => 'Creator Studio',
      GtexWorkspaceKind.admin => 'Admin Operations',
    };
  }

  IconData get icon {
    return switch (this) {
      GtexWorkspaceKind.explore => Icons.explore_outlined,
      GtexWorkspaceKind.fan => Icons.sports_soccer_outlined,
      GtexWorkspaceKind.club => Icons.shield_outlined,
      GtexWorkspaceKind.scouting => Icons.radar_outlined,
      GtexWorkspaceKind.trader => Icons.candlestick_chart_outlined,
      GtexWorkspaceKind.creator => Icons.video_settings_outlined,
      GtexWorkspaceKind.admin => Icons.admin_panel_settings_outlined,
    };
  }
}

/// Primary bottom-bar / rail slot identifiers (Master Plan Document E1).
enum GtexShellSlotId {
  home,
  explore,
  club,
  recruitment,
  traderDesk,
  studio,
  ops,
  queues,
  matchday,
  market,
  world,
  community,
  wallet,
  treasury,
  more,
  signIn,
}

/// Secondary / overflow destinations reachable via the `More` sheet on compact
/// screens or the left rail on medium/expanded screens (Master Plan Document E1).
enum GtexSecondaryDestinationId {
  newsroom,
  world,
  community,
  wallet,
  rewards,
  you,
  boardroom,
  admin,
}

@immutable
class GtexShellCapabilities {
  const GtexShellCapabilities({
    this.isAuthenticated = false,
    this.accountType = 'user',
    this.ownedClubIds = const <String>[],
    this.activeClubId,
    this.isOrgScoutOrAgent = false,
    this.isCoinTrader = false,
    this.isCreator = false,
    this.isAdmin = false,
    this.clubLegacyEnabled = false,
    this.unreadInboxCount = 0,
    this.unreadNotificationCount = 0,
  });

  final bool isAuthenticated;
  /// Dedicated product lane: user, creator, or coin_trader.
  final String accountType;
  final List<String> ownedClubIds;
  final String? activeClubId;
  final bool isOrgScoutOrAgent;
  final bool isCoinTrader;
  final bool isCreator;
  final bool isAdmin;
  final bool clubLegacyEnabled;
  final int unreadInboxCount;
  final int unreadNotificationCount;

  bool get isDedicatedTraderAccount =>
      accountType.trim().toLowerCase() == 'coin_trader' || isCoinTrader;

  bool get isDedicatedCreatorAccount =>
      accountType.trim().toLowerCase() == 'creator' || isCreator;

  bool get isClubOwner =>
      isAuthenticated &&
      !isDedicatedTraderAccount &&
      !isDedicatedCreatorAccount &&
      (ownedClubIds.isNotEmpty ||
          (activeClubId != null && activeClubId!.trim().isNotEmpty));

  String get resolvedClubId {
    final String? active = activeClubId?.trim();
    if (active != null && active.isNotEmpty) {
      return active;
    }
    if (ownedClubIds.isNotEmpty && ownedClubIds.first.trim().isNotEmpty) {
      return ownedClubIds.first.trim();
    }
    return GtexRouteAliasTable.defaultClubPlaceholder;
  }

  /// Derives capabilities from a raw user/session map without inventing
  /// client-only roles.
  factory GtexShellCapabilities.fromSessionMap({
    Map<String, Object?>? sessionJson,
    List<String> ownedClubIds = const <String>[],
    bool clubLegacyEnabled = false,
    int unreadInboxCount = 0,
    int unreadNotificationCount = 0,
  }) {
    if (sessionJson == null) {
      return GtexShellCapabilities(
        isAuthenticated: false,
        clubLegacyEnabled: clubLegacyEnabled,
      );
    }

    final Map<String, Object?> userMap =
        sessionJson['user'] is Map<String, Object?>
            ? sessionJson['user']! as Map<String, Object?>
            : sessionJson;
    final String role =
        (userMap['role'] ?? sessionJson['role'] ?? '')
            .toString()
            .trim()
            .toLowerCase();
    final String accountType = (
      userMap['account_type'] ??
      userMap['accountType'] ??
      sessionJson['account_type'] ??
      sessionJson['accountType'] ??
      'user'
    ).toString().trim().toLowerCase();
    final List<String> permissions = <String>[
      if (userMap['permissions'] is Iterable)
        ...(userMap['permissions']! as Iterable).map(
          (Object? item) => item.toString().trim().toLowerCase(),
        ),
      if (sessionJson['permissions'] is Iterable)
        ...(sessionJson['permissions']! as Iterable).map(
          (Object? item) => item.toString().trim().toLowerCase(),
        ),
    ];
    final String? clubId =
        (sessionJson['current_club_id'] ??
                userMap['current_club_id'] ??
                sessionJson['club_id'])
            ?.toString()
            .trim();
    final List<String> mergedClubs = <String>[
      ...ownedClubIds.where((String id) => id.trim().isNotEmpty),
      if (clubId != null &&
          clubId.isNotEmpty &&
          !ownedClubIds.contains(clubId))
        clubId,
    ];

    final bool isAdmin =
        role == 'admin' ||
        role == 'super_admin' ||
        role.endsWith('_admin') ||
        permissions.any((String p) => p.startsWith('admin.'));
    // Account type is the source of truth. A permission/profile must not
    // expose another account lane through the workspace switcher.
    final bool isCoinTrader = accountType == 'coin_trader';
    final bool isCreator = accountType == 'creator';
    final bool isOrgScoutOrAgent =
        role == 'scout' ||
        role == 'agent' ||
        role == 'staff' ||
        role == 'club' ||
        permissions.contains('players.manage_own') ||
        permissions.contains('scouting.access');

    return GtexShellCapabilities(
      isAuthenticated: true,
      accountType: accountType,
      ownedClubIds: List<String>.unmodifiable(mergedClubs),
      activeClubId:
          clubId != null && clubId.isNotEmpty
              ? clubId
              : (mergedClubs.isNotEmpty ? mergedClubs.first : null),
      isOrgScoutOrAgent: isOrgScoutOrAgent,
      isCoinTrader: isCoinTrader,
      isCreator: isCreator,
      isAdmin: isAdmin,
      clubLegacyEnabled: clubLegacyEnabled,
      unreadInboxCount: unreadInboxCount < 0 ? 0 : unreadInboxCount,
      unreadNotificationCount:
          unreadNotificationCount < 0 ? 0 : unreadNotificationCount,
    );
  }
}

@immutable
class GtexShellSlotSpec {
  const GtexShellSlotSpec({
    required this.id,
    required this.label,
    required this.canonicalRoute,
    required this.icon,
    required this.selectedIcon,
    this.badgeCount = 0,
    this.opensMoreSheet = false,
  });

  final GtexShellSlotId id;
  final String label;
  final String canonicalRoute;
  final IconData icon;
  final IconData selectedIcon;

  /// Numeric count only (Master Plan E6 rule 3: no decorative text badges).
  final int badgeCount;
  final bool opensMoreSheet;

  bool get hasBadge => badgeCount > 0;
}

@immutable
class GtexSecondaryDestinationSpec {
  const GtexSecondaryDestinationSpec({
    required this.id,
    required this.label,
    required this.canonicalRoute,
    required this.icon,
    this.badgeCount = 0,
  });

  final GtexSecondaryDestinationId id;
  final String label;
  final String canonicalRoute;
  final IconData icon;
  final int badgeCount;
}

/// Deterministic navigation model for the GTEX Shell (Master Plan Document D2,
/// E1–E6, Decision O-05, Phase A3).
class ShellNavigationModel {
  const ShellNavigationModel({
    required this.capabilities,
    GtexWorkspaceKind? selectedWorkspace,
    this.lastUsedWorkspace,
  }) : _selectedWorkspace = selectedWorkspace;

  final GtexShellCapabilities capabilities;
  final GtexWorkspaceKind? _selectedWorkspace;
  final GtexWorkspaceKind? lastUsedWorkspace;

  /// All workspaces available to the current user for the top-bar Workspace
  /// Switcher (`Document D2`, `Decision O-05`).
  List<GtexWorkspaceKind> get availableWorkspaces {
    if (!capabilities.isAuthenticated) {
      return const <GtexWorkspaceKind>[GtexWorkspaceKind.explore];
    }

    // Creator and coin-trader accounts are dedicated lanes, not switchable
    // roles on a normal GTEX ID. Old club/profile/permission data must not
    // expand these accounts into a Club, Creator, or Trader workspace menu.
    if (capabilities.isDedicatedTraderAccount) {
      return const <GtexWorkspaceKind>[GtexWorkspaceKind.trader];
    }
    if (capabilities.isDedicatedCreatorAccount) {
      return const <GtexWorkspaceKind>[GtexWorkspaceKind.creator];
    }

    final List<GtexWorkspaceKind> workspaces = <GtexWorkspaceKind>[
      if (capabilities.isClubOwner) GtexWorkspaceKind.club,
      GtexWorkspaceKind.fan,
      if (capabilities.isOrgScoutOrAgent) GtexWorkspaceKind.scouting,
      if (capabilities.isAdmin) GtexWorkspaceKind.admin,
    ];
    return List<GtexWorkspaceKind>.unmodifiable(workspaces);
  }

  bool get showWorkspaceSwitcher => availableWorkspaces.length > 1;

  /// Resolves the active workspace using Document D2 rules:
  /// 1. Explicitly selected workspace (if permitted).
  /// 2. Last-used workspace (if permitted).
  /// 3. `Club` if owner, else role-specific workspace (`Admin` / `Trader` /
  ///    `Creator` / `Scouting`), else `Fan` (or `Explore` for guest).
  GtexWorkspaceKind get activeWorkspace {
    final List<GtexWorkspaceKind> allowed = availableWorkspaces;
    if (_selectedWorkspace != null && allowed.contains(_selectedWorkspace)) {
      return _selectedWorkspace;
    }
    if (lastUsedWorkspace != null && allowed.contains(lastUsedWorkspace)) {
      return lastUsedWorkspace!;
    }
    if (!capabilities.isAuthenticated) {
      return GtexWorkspaceKind.explore;
    }
    if (capabilities.isDedicatedTraderAccount) {
      return GtexWorkspaceKind.trader;
    }
    if (capabilities.isDedicatedCreatorAccount) {
      return GtexWorkspaceKind.creator;
    }
    if (capabilities.isClubOwner) {
      return GtexWorkspaceKind.club;
    }
    if (capabilities.isAdmin) {
      return GtexWorkspaceKind.admin;
    }
    if (capabilities.isOrgScoutOrAgent) {
      return GtexWorkspaceKind.scouting;
    }
    return GtexWorkspaceKind.fan;
  }

  /// Numeric attention count for the top-bar Inbox/Notification bell (`E1`, `E6`):
  /// - Owner (`Club` workspace or club owner): `unreadInboxCount + unreadNotificationCount`
  /// - Other authenticated workspaces: `unreadNotificationCount`
  /// - Guest (`Explore`): `0`
  int get topBarAttentionCount {
    if (!capabilities.isAuthenticated) {
      return 0;
    }
    if (activeWorkspace == GtexWorkspaceKind.club || capabilities.isClubOwner) {
      return capabilities.unreadInboxCount +
          capabilities.unreadNotificationCount;
    }
    return capabilities.unreadNotificationCount;
  }

  /// Phone (`<720 dp`) bottom-bar slots — always exactly 5 slots in a fixed,
  /// predictable order per workspace (Master Plan Document E1 & E6).
  List<GtexShellSlotSpec> get primarySlots => primarySlotsFor(activeWorkspace);

  List<GtexShellSlotSpec> primarySlotsFor(GtexWorkspaceKind workspace) {
    final String clubId = capabilities.resolvedClubId;
    return switch (workspace) {
      GtexWorkspaceKind.club => <GtexShellSlotSpec>[
        const GtexShellSlotSpec(
          id: GtexShellSlotId.home,
          label: 'Home',
          canonicalRoute: GtexCanonicalRoutes.home,
          icon: Icons.home_outlined,
          selectedIcon: Icons.home_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.club,
          label: 'Club',
          canonicalRoute: GtexCanonicalRoutes.clubRoot(clubId),
          icon: Icons.shield_outlined,
          selectedIcon: Icons.shield_rounded,
        ),
        const GtexShellSlotSpec(
          id: GtexShellSlotId.matchday,
          label: 'Matchday',
          canonicalRoute: GtexCanonicalRoutes.matchday,
          icon: Icons.sports_soccer_outlined,
          selectedIcon: Icons.sports_soccer_rounded,
        ),
        const GtexShellSlotSpec(
          id: GtexShellSlotId.market,
          label: 'Market',
          canonicalRoute: GtexCanonicalRoutes.market,
          icon: Icons.storefront_outlined,
          selectedIcon: Icons.storefront_rounded,
        ),
        const GtexShellSlotSpec(
          id: GtexShellSlotId.more,
          label: 'More',
          canonicalRoute: GtexCanonicalRoutes.you,
          icon: Icons.more_horiz_rounded,
          selectedIcon: Icons.more_rounded,
          opensMoreSheet: true,
        ),
      ],
      GtexWorkspaceKind.fan => const <GtexShellSlotSpec>[
        GtexShellSlotSpec(
          id: GtexShellSlotId.home,
          label: 'Home',
          canonicalRoute: GtexCanonicalRoutes.home,
          icon: Icons.home_outlined,
          selectedIcon: Icons.home_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.matchday,
          label: 'Matchday',
          canonicalRoute: GtexCanonicalRoutes.matchday,
          icon: Icons.sports_soccer_outlined,
          selectedIcon: Icons.sports_soccer_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.market,
          label: 'Market',
          canonicalRoute: GtexCanonicalRoutes.market,
          icon: Icons.storefront_outlined,
          selectedIcon: Icons.storefront_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.world,
          label: 'World',
          canonicalRoute: GtexCanonicalRoutes.world,
          icon: Icons.public_outlined,
          selectedIcon: Icons.public_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.more,
          label: 'More',
          canonicalRoute: GtexCanonicalRoutes.you,
          icon: Icons.more_horiz_rounded,
          selectedIcon: Icons.more_rounded,
          opensMoreSheet: true,
        ),
      ],
      GtexWorkspaceKind.scouting => <GtexShellSlotSpec>[
        const GtexShellSlotSpec(
          id: GtexShellSlotId.home,
          label: 'Home',
          canonicalRoute: GtexCanonicalRoutes.home,
          icon: Icons.home_outlined,
          selectedIcon: Icons.home_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.recruitment,
          label: 'Recruitment',
          canonicalRoute: GtexCanonicalRoutes.clubRecruitment(clubId),
          icon: Icons.radar_outlined,
          selectedIcon: Icons.radar_rounded,
        ),
        const GtexShellSlotSpec(
          id: GtexShellSlotId.matchday,
          label: 'Matchday',
          canonicalRoute: GtexCanonicalRoutes.matchday,
          icon: Icons.sports_soccer_outlined,
          selectedIcon: Icons.sports_soccer_rounded,
        ),
        const GtexShellSlotSpec(
          id: GtexShellSlotId.market,
          label: 'Market',
          canonicalRoute: GtexCanonicalRoutes.market,
          icon: Icons.storefront_outlined,
          selectedIcon: Icons.storefront_rounded,
        ),
        const GtexShellSlotSpec(
          id: GtexShellSlotId.more,
          label: 'More',
          canonicalRoute: GtexCanonicalRoutes.you,
          icon: Icons.more_horiz_rounded,
          selectedIcon: Icons.more_rounded,
          opensMoreSheet: true,
        ),
      ],
      GtexWorkspaceKind.trader => const <GtexShellSlotSpec>[
        GtexShellSlotSpec(
          id: GtexShellSlotId.home,
          label: 'Home',
          canonicalRoute: GtexCanonicalRoutes.home,
          icon: Icons.home_outlined,
          selectedIcon: Icons.home_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.traderDesk,
          label: 'Trader Desk',
          canonicalRoute: GtexCanonicalRoutes.walletTraderDesk,
          icon: Icons.candlestick_chart_outlined,
          selectedIcon: Icons.candlestick_chart_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.market,
          label: 'Market',
          canonicalRoute: GtexCanonicalRoutes.market,
          icon: Icons.storefront_outlined,
          selectedIcon: Icons.storefront_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.wallet,
          label: 'Wallet',
          canonicalRoute: GtexCanonicalRoutes.wallet,
          icon: Icons.account_balance_wallet_outlined,
          selectedIcon: Icons.account_balance_wallet_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.more,
          label: 'More',
          canonicalRoute: GtexCanonicalRoutes.you,
          icon: Icons.more_horiz_rounded,
          selectedIcon: Icons.more_rounded,
          opensMoreSheet: true,
        ),
      ],
      GtexWorkspaceKind.creator => const <GtexShellSlotSpec>[
        GtexShellSlotSpec(
          id: GtexShellSlotId.home,
          label: 'Home',
          canonicalRoute: GtexCanonicalRoutes.home,
          icon: Icons.home_outlined,
          selectedIcon: Icons.home_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.studio,
          label: 'Studio',
          canonicalRoute: GtexCanonicalRoutes.studio,
          icon: Icons.dashboard_customize_outlined,
          selectedIcon: Icons.dashboard_customize_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.matchday,
          label: 'Matchday',
          canonicalRoute: GtexCanonicalRoutes.matchday,
          icon: Icons.sports_soccer_outlined,
          selectedIcon: Icons.sports_soccer_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.community,
          label: 'Community',
          canonicalRoute: GtexCanonicalRoutes.community,
          icon: Icons.forum_outlined,
          selectedIcon: Icons.forum_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.more,
          label: 'More',
          canonicalRoute: GtexCanonicalRoutes.you,
          icon: Icons.more_horiz_rounded,
          selectedIcon: Icons.more_rounded,
          opensMoreSheet: true,
        ),
      ],
      GtexWorkspaceKind.admin => const <GtexShellSlotSpec>[
        GtexShellSlotSpec(
          id: GtexShellSlotId.ops,
          label: 'Ops',
          canonicalRoute: GtexCanonicalRoutes.admin,
          icon: Icons.admin_panel_settings_outlined,
          selectedIcon: Icons.admin_panel_settings_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.queues,
          label: 'Queues',
          canonicalRoute: GtexCanonicalRoutes.adminQueues,
          icon: Icons.fact_check_outlined,
          selectedIcon: Icons.fact_check_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.matchday,
          label: 'Matchday',
          canonicalRoute: GtexCanonicalRoutes.matchday,
          icon: Icons.sports_soccer_outlined,
          selectedIcon: Icons.sports_soccer_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.treasury,
          label: 'Treasury',
          canonicalRoute: GtexCanonicalRoutes.wallet,
          icon: Icons.account_balance_outlined,
          selectedIcon: Icons.account_balance_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.more,
          label: 'More',
          canonicalRoute: GtexCanonicalRoutes.you,
          icon: Icons.more_horiz_rounded,
          selectedIcon: Icons.more_rounded,
          opensMoreSheet: true,
        ),
      ],
      GtexWorkspaceKind.explore => const <GtexShellSlotSpec>[
        GtexShellSlotSpec(
          id: GtexShellSlotId.explore,
          label: 'Explore',
          canonicalRoute: GtexCanonicalRoutes.home,
          icon: Icons.explore_outlined,
          selectedIcon: Icons.explore_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.matchday,
          label: 'Matchday',
          canonicalRoute: GtexCanonicalRoutes.matchday,
          icon: Icons.sports_soccer_outlined,
          selectedIcon: Icons.sports_soccer_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.market,
          label: 'Market',
          canonicalRoute: GtexCanonicalRoutes.market,
          icon: Icons.storefront_outlined,
          selectedIcon: Icons.storefront_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.world,
          label: 'World',
          canonicalRoute: GtexCanonicalRoutes.world,
          icon: Icons.public_outlined,
          selectedIcon: Icons.public_rounded,
        ),
        GtexShellSlotSpec(
          id: GtexShellSlotId.signIn,
          label: 'Sign in',
          canonicalRoute: GtexCanonicalRoutes.signIn,
          icon: Icons.login_rounded,
          selectedIcon: Icons.login_rounded,
        ),
      ],
    };
  }

  /// Destinations displayed inside the `More` sheet (`Document E1` & `E6`).
  ///
  /// Feature flags (`clubLegacyEnabled`) gate only unlaunched subsystems
  /// (`Boardroom`), while `Admin` is shown only when `capabilities.isAdmin` is true.
  List<GtexSecondaryDestinationSpec> get moreDestinations =>
      moreDestinationsFor(activeWorkspace);

  List<GtexSecondaryDestinationSpec> moreDestinationsFor(
    GtexWorkspaceKind workspace,
  ) {
    final String clubId = capabilities.resolvedClubId;
    final List<GtexSecondaryDestinationSpec> items =
        <GtexSecondaryDestinationSpec>[
          const GtexSecondaryDestinationSpec(
            id: GtexSecondaryDestinationId.newsroom,
            label: 'Newsroom',
            canonicalRoute: GtexCanonicalRoutes.newsroom,
            icon: Icons.newspaper_outlined,
          ),
          if (workspace != GtexWorkspaceKind.fan &&
              workspace != GtexWorkspaceKind.explore)
            const GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.world,
              label: 'World',
              canonicalRoute: GtexCanonicalRoutes.world,
              icon: Icons.public_outlined,
            ),
          if (workspace != GtexWorkspaceKind.creator)
            const GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.community,
              label: 'Community',
              canonicalRoute: GtexCanonicalRoutes.community,
              icon: Icons.forum_outlined,
            ),
          if (capabilities.isClubOwner && capabilities.clubLegacyEnabled)
            GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.boardroom,
              label: 'Boardroom',
              canonicalRoute: GtexCanonicalRoutes.clubBoardroom(clubId),
              icon: Icons.apartment_outlined,
            ),
          if (capabilities.isAuthenticated &&
              workspace != GtexWorkspaceKind.trader &&
              workspace != GtexWorkspaceKind.admin)
            const GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.wallet,
              label: 'Wallet',
              canonicalRoute: GtexCanonicalRoutes.wallet,
              icon: Icons.account_balance_wallet_outlined,
            ),
          if (capabilities.isAuthenticated)
            const GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.rewards,
              label: 'Rewards',
              canonicalRoute: GtexCanonicalRoutes.youRewards,
              icon: Icons.emoji_events_outlined,
            ),
          if (capabilities.isAuthenticated)
            const GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.you,
              label: 'You',
              canonicalRoute: GtexCanonicalRoutes.you,
              icon: Icons.person_outline_rounded,
            ),
          if (capabilities.isAdmin && workspace != GtexWorkspaceKind.admin)
            const GtexSecondaryDestinationSpec(
              id: GtexSecondaryDestinationId.admin,
              label: 'Admin',
              canonicalRoute: GtexCanonicalRoutes.admin,
              icon: Icons.admin_panel_settings_outlined,
            ),
        ];
    return List<GtexSecondaryDestinationSpec>.unmodifiable(items);
  }
}

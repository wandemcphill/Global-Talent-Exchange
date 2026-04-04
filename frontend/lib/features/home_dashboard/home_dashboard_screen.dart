import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/controllers/regen_universe_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/club_creation_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/shared/presentation/gte_no_club_onboarding_view.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/clubs/club_profile_screen.dart';
import 'package:gte_frontend/screens/clubs/create_club_screen.dart';
import 'package:gte_frontend/screens/clubs/club_trophy_cabinet_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_discovery_screen.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

import 'widgets/home_featured_event_banner.dart';
import 'widgets/home_section_card.dart';

class HomeDashboardScreen extends StatefulWidget {
  const HomeDashboardScreen({
    super.key,
    required this.exchangeController,
    required this.apiBaseUrl,
    required this.backendMode,
    this.onOpenLogin,
    this.isCheckingCreatorAccess = false,
    this.canHostCompetitions = false,
    this.clubId,
    this.clubName,
    this.onOpenClubTab,
    this.onOpenCompetitionsTab,
    this.onOpenMarketTab,
    this.onOpenHubTab,
    this.onOpenWalletTab,
    this.onOpenClubSubtab,
    this.onOpenCreatorAccessRequest,
    this.navigationDependencies,
  });

  final GteExchangeController exchangeController;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final VoidCallback? onOpenLogin;
  final bool isCheckingCreatorAccess;
  final bool canHostCompetitions;
  final String? clubId;
  final String? clubName;
  final VoidCallback? onOpenClubTab;
  final VoidCallback? onOpenCompetitionsTab;
  final VoidCallback? onOpenMarketTab;
  final VoidCallback? onOpenHubTab;
  final VoidCallback? onOpenWalletTab;
  final ValueChanged<ClubNavigationTab>? onOpenClubSubtab;
  final Future<void> Function()? onOpenCreatorAccessRequest;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<HomeDashboardScreen> createState() => _HomeDashboardScreenState();
}

class _HomeDashboardScreenState extends State<HomeDashboardScreen> {
  ClubController? _clubController;
  late CompetitionController _competitionController;
  late RegenUniverseController _regenUniverseController;
  late String _userId;
  late String? _userName;
  String? _clubId;
  String? _clubName;
  bool _tradingSummaryPrimeQueued = false;

  @override
  void initState() {
    super.initState();
    widget.exchangeController.addListener(_handleExchangeChanged);
    _createControllers();
    _primeTradingSummary();
  }

  @override
  void didUpdateWidget(covariant HomeDashboardScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.exchangeController != widget.exchangeController) {
      oldWidget.exchangeController.removeListener(_handleExchangeChanged);
      widget.exchangeController.addListener(_handleExchangeChanged);
    }
    if (oldWidget.apiBaseUrl != widget.apiBaseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.clubId != widget.clubId ||
        oldWidget.clubName != widget.clubName ||
        oldWidget.exchangeController != widget.exchangeController) {
      _recreateControllers();
    } else {
      _handleExchangeChanged();
    }
  }

  @override
  void dispose() {
    widget.exchangeController.removeListener(_handleExchangeChanged);
    _clubController?.dispose();
    _competitionController.dispose();
    _regenUniverseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ClubController? clubController = _clubController;
    final String? clubId = _clubId;
    final String? clubName = _clubName;
    if (clubController == null ||
        clubId == null ||
        clubId.isEmpty ||
        clubName == null ||
        clubName.isEmpty) {
      return _buildNoClubState();
    }
    final CompetitionController competitionController = _competitionController;
    return AnimatedBuilder(
      animation: Listenable.merge(<Listenable>[
        widget.exchangeController,
        clubController,
        competitionController,
        _regenUniverseController,
      ]),
      builder: (BuildContext context, Widget? child) {
        final ClubDashboardData? clubData = clubController.data;
        final bool waitingForFirstFrame =
            clubData == null &&
            competitionController.competitions.isEmpty &&
            (clubController.isLoading ||
                competitionController.isLoadingDiscovery);
        if (waitingForFirstFrame) {
          return const _HomeLoadingView();
        }

        if (clubData == null &&
            competitionController.competitions.isEmpty &&
            clubController.errorMessage != null &&
            competitionController.discoveryError != null) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Home is unavailable',
              message:
                  '${clubController.errorMessage!} ${competitionController.discoveryError!}',
              actionLabel: 'Retry',
              onAction: _refresh,
              icon: Icons.home_outlined,
            ),
          );
        }

        final _HomeSnapshot snapshot = _HomeSnapshot.fromSources(
          clubName: clubName,
          isAuthenticated: widget.exchangeController.isAuthenticated,
          userLabel: _displayUserLabel(),
          clubData: clubData,
          competitions: competitionController.competitions,
        );

        return RefreshIndicator(
          onRefresh: _refresh,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _HomeHeroPanel(
                  clubName: clubName,
                  userLabel: _displayUserLabel(),
                  title: '$clubName matchday lobby',
                  subtitle:
                      widget.exchangeController.isAuthenticated
                          ? 'Your club, capital room, and next football story now live in one place.'
                          : 'Preview the football universe first, then sign in to trade, fund, and manage the badge.',
                  capitalLabel: _capitalMetricLabel(),
                  liveLabel: _livePulseLabel(snapshot),
                  isAuthenticated: widget.exchangeController.isAuthenticated,
                  onOpenClub: () => _openTarget(_HomeLinkTarget.club),
                  onOpenCompetitions:
                      () => _openTarget(_HomeLinkTarget.competitions),
                  onOpenWallet: widget.onOpenWalletTab,
                  onOpenLogin: widget.onOpenLogin,
                  chips: <Widget>[
                    GteMetricChip(
                      label: 'Prestige',
                      value: snapshot.prestigeLabel,
                    ),
                    GteMetricChip(
                      label: 'Honors',
                      value: snapshot.totalHonors.toString(),
                    ),
                    GteMetricChip(
                      label: 'Capital',
                      value: _capitalMetricLabel(),
                    ),
                    GteMetricChip(
                      label: 'Orders',
                      value:
                          widget.exchangeController.openOrders.length
                              .toString(),
                      positive: widget.exchangeController.openOrders.isNotEmpty,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _HomeRuntimeSignalPanel(
                  backendMode: widget.backendMode,
                  apiHostLabel: _apiHostLabel(),
                  narrative: _runtimeNarrative(hasClubScope: true),
                  isAuthenticated: widget.exchangeController.isAuthenticated,
                  hasClubScope: true,
                  capitalLabel: _capitalMetricLabel(),
                  isSyncing:
                      clubController.isLoading ||
                      competitionController.isLoadingDiscovery,
                ),
                const SizedBox(height: 16),
                GteSyncStatusCard(
                  title: 'App-wide premium sync',
                  status:
                      widget.exchangeController.isAuthenticated
                          ? 'Market, play, hub, club, and capital layers are stitched into one premium shell.'
                          : 'Guest access is live. Sign in to unlock trading, capital execution, and writable club actions.',
                  syncedAt: widget.exchangeController.marketSyncedAt,
                  accent: GteShellTheme.accent,
                  isRefreshing:
                      clubController.isLoading ||
                      competitionController.isLoadingDiscovery,
                  onRefresh: _refresh,
                ),
                if (clubController.errorMessage != null ||
                    competitionController.discoveryError != null) ...<Widget>[
                  const SizedBox(height: 18),
                  _InlineWarning(
                    message: <String>[
                      if (clubController.errorMessage != null)
                        clubController.errorMessage!,
                      if (competitionController.discoveryError != null)
                        competitionController.discoveryError!,
                    ].join(' '),
                  ),
                ],
                const SizedBox(height: 20),
                HomeFeaturedEventBanner(
                  label: snapshot.featuredBanner.label,
                  title: snapshot.featuredBanner.title,
                  summary: snapshot.featuredBanner.summary,
                  body: snapshot.featuredBanner.body,
                  icon: snapshot.featuredBanner.icon,
                  gradientColors: snapshot.featuredBanner.gradientColors,
                  stats: snapshot.featuredBanner.stats,
                  actionLabel: snapshot.featuredBanner.actionLabel,
                  onPressed: () => _openTarget(snapshot.featuredBanner.target),
                ),
                const SizedBox(height: 20),
                _HomeSectionHeading(
                  eyebrow: 'RIGHT NOW',
                  title:
                      'The control deck keeps the next best move in plain sight.',
                  detail:
                      'Top cards are reserved for the most actionable club and match context. The quieter signals live below so the home screen stays premium instead of crowded.',
                ),
                const SizedBox(height: 14),
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final int columnCount =
                        constraints.maxWidth >= 1220
                            ? 2
                            : constraints.maxWidth >= 760
                            ? 2
                            : 1;
                    final double spacing = 16;
                    final double cardWidth =
                        (constraints.maxWidth - (spacing * (columnCount - 1))) /
                        columnCount;
                    final List<_HomeCardData> primaryCards = <_HomeCardData>[
                      snapshot.nextMatch,
                      snapshot.leagueSnapshot,
                      snapshot.championsLeagueStatus,
                      snapshot.fastCupCountdown,
                    ];
                    return Wrap(
                      spacing: spacing,
                      runSpacing: spacing,
                      children: primaryCards
                          .map(
                            (_HomeCardData card) => SizedBox(
                              width: cardWidth,
                              child: HomeSectionCard(
                                eyebrow: card.eyebrow,
                                title: card.title,
                                summary: card.summary,
                                detail: card.detail,
                                icon: card.icon,
                                accent: card.accent,
                                stats: card.stats,
                                highlights: card.highlights,
                                actionLabel: card.actionLabel,
                                onTap: () => _openTarget(card.target),
                              ),
                            ),
                          )
                          .toList(growable: false),
                    );
                  },
                ),
                const SizedBox(height: 20),
                _HomeQuickActionsStrip(
                  isAuthenticated: widget.exchangeController.isAuthenticated,
                  onOpenMarket: widget.onOpenMarketTab,
                  onOpenCompetitions:
                      () => _openTarget(_HomeLinkTarget.competitions),
                  onOpenReplays: () => _openTarget(_HomeLinkTarget.replays),
                  onOpenLogin: widget.onOpenLogin,
                ),
                const SizedBox(height: 16),
                _HomeJourneyPanel(
                  isAuthenticated: widget.exchangeController.isAuthenticated,
                  clubName: clubName,
                  notificationCount: snapshot.notificationCount,
                  openCompetitionCount: snapshot.openCompetitionCount,
                  onOpenCompetitions:
                      () => _openTarget(_HomeLinkTarget.competitions),
                  onOpenClub: () => _openTarget(_HomeLinkTarget.club),
                  onOpenLogin: widget.onOpenLogin,
                ),
                const SizedBox(height: 20),
                _HomeRegenUniverseSection(
                  controller: _regenUniverseController,
                  onRetry: _refresh,
                  onOpenNationalTeams:
                      () => _openFeatureRoute(
                        const NationalTeamCompetitionsRouteData(),
                      ),
                  onOpenWorldRegens:
                      () => _openFeatureRoute(
                        WorldClubContextRouteData(
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                ),
                const SizedBox(height: 20),
                _HomeExpansionLanesPanel(
                  isAdmin:
                      (widget.navigationDependencies?.currentUserRole ??
                              widget.exchangeController.session?.user.role)
                          ?.trim() ==
                      'admin',
                  onOpenStreamerTournaments:
                      () => _openFeatureRoute(
                        const StreamerTournamentsListRouteData(),
                      ),
                  onOpenNationsCup:
                      () => _openFeatureRoute(
                        const NationalTeamCompetitionsRouteData(),
                      ),
                  onOpenWorld:
                      () => _openFeatureRoute(
                        WorldClubContextRouteData(
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                  onOpenTransferCenter:
                      () => _openFeatureRoute(
                        const FootballTransferCenterRouteData(),
                      ),
                  onOpenPlayerCards:
                      () =>
                          _openFeatureRoute(const PlayerCardsBrowseRouteData()),
                  onOpenCreatorShareMarket:
                      () => _openFeatureRoute(
                        CreatorShareMarketClubRouteData(
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                  onOpenClubSaleMarket:
                      () => _openFeatureRoute(
                        const ClubSaleMarketListingsRouteData(),
                      ),
                  onOpenCreatorStadium:
                      () => _openFeatureRoute(
                        CreatorStadiumClubRouteData(
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                  onOpenBroadcastDesk:
                      () => _openFeatureRoute(const BroadcastDeskRouteData()),
                  onOpenGtexJackpot:
                      () => _openFeatureRoute(const GtexJackpotRouteData()),
                  onOpenClubAiAssistant:
                      () => _openFeatureRoute(
                        ClubAiAssistantRouteData(
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                  onOpenFinanceAdmin:
                      () => _openFeatureRoute(
                        const CreatorLeagueFinancialReportRouteData(),
                      ),
                  onOpenGiftStabilizer:
                      () => _openFeatureRoute(const GiftStabilizerRouteData()),
                ),
                const SizedBox(height: 20),
                _HomeSectionHeading(
                  eyebrow: 'QUIETER SIGNALS',
                  title:
                      'Match stories and alerts stay visible without hijacking the dashboard.',
                  detail:
                      'These cards stay visible for storylines, reminders, and follow-up actions once the primary route is clear.',
                ),
                const SizedBox(height: 14),
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final int columnCount =
                        constraints.maxWidth >= 1100 ? 2 : 1;
                    final double spacing = 16;
                    final double cardWidth =
                        (constraints.maxWidth - (spacing * (columnCount - 1))) /
                        columnCount;
                    final List<_HomeCardData> signalCards = <_HomeCardData>[
                      snapshot.recentReplay,
                      snapshot.notificationsSummary,
                    ];
                    return Wrap(
                      spacing: spacing,
                      runSpacing: spacing,
                      children: signalCards
                          .map(
                            (_HomeCardData card) => SizedBox(
                              width: cardWidth,
                              child: HomeSectionCard(
                                eyebrow: card.eyebrow,
                                title: card.title,
                                summary: card.summary,
                                detail: card.detail,
                                icon: card.icon,
                                accent: card.accent,
                                stats: card.stats,
                                highlights: card.highlights,
                                actionLabel: card.actionLabel,
                                onTap: () => _openTarget(card.target),
                              ),
                            ),
                          )
                          .toList(growable: false),
                    );
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _refresh() async {
    final ClubController? clubController = _clubController;
    final bool hasClubScope = _hasClubScope(_clubId, _clubName);
    await Future.wait<void>(<Future<void>>[
      if (clubController != null) clubController.refresh(),
      if (hasClubScope) _competitionController.loadDiscovery(),
      if (hasClubScope) _regenUniverseController.refresh(),
    ]);
    _primeTradingSummary();
  }

  void _createControllers() {
    final _HomeIdentity identity = _deriveIdentity();
    _userId = identity.userId;
    _userName = identity.userName;
    _clubId = identity.clubId;
    _clubName = identity.clubName;
    _competitionController = _buildCompetitionController();
    _regenUniverseController = RegenUniverseController.standard(
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
    );
    final String? clubId = _clubId;
    final String? clubName = _clubName;
    if (_hasClubScope(clubId, clubName)) {
      _clubController = _buildClubController(
        clubId: clubId!,
        clubName: clubName!,
      );
      _clubController!.ensureLoaded();
      _competitionController.bootstrap();
      _regenUniverseController.ensureLoaded();
    } else {
      _clubController = null;
    }
  }

  void _recreateControllers() {
    final ClubController? previousClub = _clubController;
    final CompetitionController previousCompetition = _competitionController;
    final RegenUniverseController previousRegen = _regenUniverseController;
    _createControllers();
    previousClub?.dispose();
    previousCompetition.dispose();
    previousRegen.dispose();
    if (mounted) {
      setState(() {});
    }
    _primeTradingSummary();
  }

  void _handleExchangeChanged() {
    final _HomeIdentity next = _deriveIdentity();
    if (next.userId != _userId || next.userName != _userName) {
      _userId = next.userId;
      _userName = next.userName;
      final CompetitionController competitionController =
          _competitionController;
      competitionController.updateCurrentUser(
        userId: _userId,
        userName: _userName,
      );
      competitionController.loadDiscovery();
    }
    if (next.clubId != _clubId || next.clubName != _clubName) {
      final ClubController? previousClub = _clubController;
      _clubId = next.clubId;
      _clubName = next.clubName;
      final String? clubId = _clubId;
      final String? clubName = _clubName;
      if (_hasClubScope(clubId, clubName)) {
        _clubController = _buildClubController(
          clubId: clubId!,
          clubName: clubName!,
        );
        _clubController!.ensureLoaded();
        _competitionController.bootstrap();
        _regenUniverseController.ensureLoaded();
      } else {
        _clubController = null;
      }
      previousClub?.dispose();
      if (mounted) {
        setState(() {});
      }
    }
    _primeTradingSummary();
  }

  void _primeTradingSummary() {
    if (_tradingSummaryPrimeQueued ||
        !_hasClubScope(_clubId, _clubName) ||
        !widget.exchangeController.isAuthenticated ||
        widget.exchangeController.hasLoadedOrders ||
        widget.exchangeController.isLoadingOrders) {
      return;
    }
    _tradingSummaryPrimeQueued = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _tradingSummaryPrimeQueued = false;
      if (!mounted ||
          !_hasClubScope(_clubId, _clubName) ||
          !widget.exchangeController.isAuthenticated ||
          widget.exchangeController.hasLoadedOrders ||
          widget.exchangeController.isLoadingOrders) {
        return;
      }
      widget.exchangeController.loadOrders();
    });
  }

  Future<void> _openFeatureRoute(GteAppRouteData route) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies == null) {
      return Future<void>.value();
    }
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
  }

  Future<void> _openCurrentClubFeatureRoute(
    GteAppRouteData Function(String clubId, String? clubName) buildRoute, {
    required String title,
    required String message,
  }) async {
    final String? clubId = widget.navigationDependencies?.currentClubId?.trim();
    if (clubId == null || clubId.isEmpty) {
      await _showRouteRequirementDialog(title: title, message: message);
      return;
    }
    await _openFeatureRoute(
      buildRoute(clubId, widget.navigationDependencies?.currentClubName),
    );
  }

  Future<void> _showRouteRequirementDialog({
    required String title,
    required String message,
  }) {
    return showDialog<void>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  _HomeIdentity _deriveIdentity() {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    final dynamic session = widget.exchangeController.session;
    final String? displayName = session?.user.displayName?.trim();
    final String username = session?.user.username.trim() ?? '';
    final String sessionUserId = session?.user.id.trim() ?? '';
    final String dependencyUserId = dependencies?.currentUserId.trim() ?? '';
    final String? dependencyUserName = dependencies?.currentUserName?.trim();
    final String? dependencyClubId = dependencies?.currentClubId?.trim();
    final String? dependencyClubName = dependencies?.currentClubName?.trim();
    final String userId =
        sessionUserId.isNotEmpty
            ? sessionUserId
            : dependencyUserId.isNotEmpty
            ? dependencyUserId
            : 'guest-user';
    final String? userName =
        displayName?.isNotEmpty == true
            ? displayName
            : username.isNotEmpty
            ? username
            : dependencyUserName?.isNotEmpty == true
            ? dependencyUserName
            : null;
    final String? clubId =
        widget.clubId?.trim().isNotEmpty == true
            ? widget.clubId!.trim()
            : dependencyClubId?.isNotEmpty == true
            ? dependencyClubId!
            : null;
    final String? clubName =
        widget.clubName?.trim().isNotEmpty == true
            ? widget.clubName!.trim()
            : dependencyClubName?.isNotEmpty == true
            ? dependencyClubName!
            : clubId == null || clubId.isEmpty
            ? null
            : _formatClubName(clubId);
    return _HomeIdentity(
      userId: userId,
      userName: userName,
      clubId: clubId,
      clubName: clubName,
    );
  }

  String? _resolveClubId() {
    final String? directClubId = widget.clubId?.trim();
    if (directClubId != null && directClubId.isNotEmpty) {
      return directClubId;
    }
    final String? dependencyClubId =
        widget.navigationDependencies?.currentClubId?.trim();
    if (dependencyClubId != null && dependencyClubId.isNotEmpty) {
      return dependencyClubId;
    }
    return null;
  }

  String? _resolveClubName(String? clubId) {
    final String? directClubName = widget.clubName?.trim();
    if (directClubName != null && directClubName.isNotEmpty) {
      return directClubName;
    }
    final String? dependencyClubName =
        widget.navigationDependencies?.currentClubName?.trim();
    if (dependencyClubName != null && dependencyClubName.isNotEmpty) {
      return dependencyClubName;
    }
    if (clubId == null || clubId.isEmpty) {
      return null;
    }
    return _formatClubName(clubId);
  }

  String _capitalMetricLabel() {
    final wallet = widget.exchangeController.walletSummary;
    if (wallet != null) {
      return gteFormatAmountForUnit(wallet.availableBalance, wallet.currency);
    }
    final portfolioSummary = widget.exchangeController.portfolioSummary;
    if (portfolioSummary != null) {
      return gteFormatCredits(portfolioSummary.cashBalance);
    }
    if (!widget.exchangeController.isAuthenticated) {
      return 'Preview';
    }
    if (widget.exchangeController.isLoadingPortfolio) {
      return 'Syncing';
    }
    return 'Ready';
  }

  String _livePulseLabel(_HomeSnapshot snapshot) {
    if (snapshot.openCompetitionCount > 0) {
      return '${snapshot.openCompetitionCount} live competitions open';
    }
    if (snapshot.notificationCount > 0) {
      return '${snapshot.notificationCount} fresh club signals';
    }
    return 'Club board settled';
  }

  String _displayUserLabel() {
    final dynamic session = widget.exchangeController.session;
    final String? displayName = session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String username = session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return username;
    }
    return 'Guest user';
  }

  String _apiHostLabel() {
    final Uri? uri = Uri.tryParse(widget.apiBaseUrl.trim());
    final String? host = uri?.host.trim();
    if (host != null && host.isNotEmpty) {
      return host;
    }
    final String raw = widget.apiBaseUrl.trim();
    if (raw.isEmpty) {
      return 'not configured';
    }
    return raw.replaceFirst(RegExp(r'^https?://'), '');
  }

  String _backendModeLabel() {
    switch (widget.backendMode) {
      case GteBackendMode.live:
        return 'Live stack';
      case GteBackendMode.fixture:
        return 'Fixture preview';
      case GteBackendMode.liveThenFixture:
        return 'Hybrid fallback';
    }
  }

  String _runtimeNarrative({required bool hasClubScope}) {
    final String accessLabel =
        widget.exchangeController.isAuthenticated
            ? 'signed-in account'
            : 'guest access';
    final String clubLabel =
        hasClubScope ? 'club routes open' : 'club setup next';
    return '${_backendModeLabel()} is wired to ${_apiHostLabel()} for this session, with $accessLabel and $clubLabel.';
  }

  String _formatClubName(String clubId) {
    return clubId
        .split(RegExp(r'[-_]+'))
        .where((String token) => token.isNotEmpty)
        .map((String token) {
          if (token.length <= 3) {
            return token.toUpperCase();
          }
          return '${token[0].toUpperCase()}${token.substring(1)}';
        })
        .join(' ');
  }

  String _slugifyClub(String clubName) {
    return clubName
        .toLowerCase()
        .replaceAll(RegExp(r'[^\w\s-]'), '')
        .replaceAll(RegExp(r'\s+'), '-')
        .replaceAll(RegExp(r'-+'), '-');
  }

  bool _hasClubScope(String? clubId, String? clubName) {
    return clubId != null &&
        clubId.isNotEmpty &&
        clubName != null &&
        clubName.isNotEmpty;
  }

  ClubController _buildClubController({
    required String clubId,
    required String clubName,
  }) {
    return ClubController.standard(
      clubId: clubId,
      clubName: clubName,
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
    );
  }

  CompetitionController _buildCompetitionController() {
    return CompetitionController(
      api: CompetitionApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: widget.backendMode,
      ),
      currentUserId: _userId,
      currentUserName: _userName,
    );
  }

  VoidCallback? _createClubOnboardingAction() {
    if (!widget.exchangeController.isAuthenticated) {
      return widget.onOpenLogin;
    }
    return () {
      _openCreateClubFlow();
    };
  }

  VoidCallback? _arenaOnboardingAction() {
    return widget.onOpenCompetitionsTab ??
        (widget.exchangeController.isAuthenticated ? null : widget.onOpenLogin);
  }

  VoidCallback? _browseClubMarketOnboardingAction() {
    if (widget.navigationDependencies == null) {
      return null;
    }
    return () {
      _openFeatureRoute(const ClubSaleMarketListingsRouteData());
    };
  }

  Widget _buildNoClubState() {
    final bool isAuthenticated = widget.exchangeController.isAuthenticated;
    if (isAuthenticated) {
      return GteNoClubOnboardingView(
        onCreateClub: _createClubOnboardingAction(),
        onBrowseClubMarket: _browseClubMarketOnboardingAction(),
        onExploreArena: _arenaOnboardingAction(),
      );
    }
    final VoidCallback? createClubAction = _createClubOnboardingAction();
    final VoidCallback? browseClubAction = _browseClubMarketOnboardingAction();
    final VoidCallback? arenaAction = _arenaOnboardingAction();
    final List<Widget> cards = <Widget>[
      _HomeActionCard(
        eyebrow: 'STEP 1',
        title: 'Create Club',
        detail:
            isAuthenticated
                ? 'Create a club from Home to unlock identity, trophies, and live matchday operations.'
                : 'Sign in, then start your first club to unlock Home, trophies, and matchday stories.',
        icon: Icons.add_circle_outline,
        accent: GteShellTheme.accent,
        badge: 'Start',
        actionLabel: 'Create Club',
        onTap: createClubAction,
      ),
      _HomeActionCard(
        eyebrow: 'STEP 2',
        title: 'Own an Existing Club',
        detail:
            'Browse clubs already available for sale, compare their current position, and step straight into a live owner workspace.',
        icon: Icons.storefront_outlined,
        accent: GteShellTheme.accentWarm,
        badge: 'Own',
        actionLabel: 'Open Club Market',
        onTap: browseClubAction,
      ),
      if (arenaAction != null)
        _HomeActionCard(
          eyebrow: 'OPTIONAL',
          title: 'Explore Arena',
          detail:
              'Jump into cups and live match nights while you decide which club to back first.',
          icon: Icons.stadium_outlined,
          accent: GteShellTheme.accentArena,
          badge: 'Live',
          actionLabel: 'Explore Arena',
          onTap: arenaAction,
        ),
    ];
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.accent,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'HOME ONBOARDING',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: GteShellTheme.accent,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  isAuthenticated
                      ? 'Create or join a club to unlock Home'
                      : 'Sign in, then build or join a club',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  isAuthenticated
                      ? 'Create a club from scratch or step into one already listed on the market, then use Home as the command surface for your sporting and commercial journey.'
                      : 'Scout the lobby first, then sign in to create a club or buy one already on the market. That unlocks the full Home crowd.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    Chip(label: const Text('1. Create Club')),
                    Chip(label: const Text('2. Own an Existing Club')),
                    if (arenaAction != null)
                      const Chip(label: Text('3. Explore Arena')),
                  ],
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    FilledButton(
                      onPressed: createClubAction,
                      child: const Text('Create Club'),
                    ),
                    FilledButton.tonal(
                      onPressed: browseClubAction,
                      child: const Text('Open Club Market'),
                    ),
                    if (arenaAction != null)
                      OutlinedButton(
                        onPressed: arenaAction,
                        child: const Text('Explore Arena'),
                      ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _HomeRuntimeSignalPanel(
            backendMode: widget.backendMode,
            apiHostLabel: _apiHostLabel(),
            narrative: _runtimeNarrative(hasClubScope: false),
            isAuthenticated: widget.exchangeController.isAuthenticated,
            hasClubScope: false,
            capitalLabel: _capitalMetricLabel(),
            isSyncing: widget.exchangeController.isBootstrapping,
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              if (constraints.maxWidth < 820) {
                return Column(
                  children: cards
                      .map(
                        (Widget child) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: child,
                        ),
                      )
                      .toList(growable: false),
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: cards
                    .map(
                      (Widget child) => Expanded(
                        child: Padding(
                          padding: EdgeInsets.only(
                            right: child == cards.last ? 0 : 12,
                          ),
                          child: child,
                        ),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }

  Future<void> _openTarget(_HomeLinkTarget target) async {
    final ClubController? clubController = _clubController;
    final CompetitionController competitionController = _competitionController;
    final String? clubId = _clubId;
    final String? clubName = _clubName;
    if (clubController == null ||
        clubId == null ||
        clubId.isEmpty ||
        clubName == null ||
        clubName.isEmpty) {
      return;
    }
    if (target == _HomeLinkTarget.club) {
      if (widget.onOpenClubTab != null) {
        widget.onOpenClubTab!();
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) => ClubProfileScreen(
                clubId: clubId,
                clubName: clubName,
                controller: clubController,
                baseUrl: widget.apiBaseUrl,
                backendMode: widget.backendMode,
                isAuthenticated: widget.exchangeController.isAuthenticated,
                onOpenLogin: widget.onOpenLogin,
              ),
        ),
      );
      return;
    }
    if (target == _HomeLinkTarget.competitions) {
      if (widget.onOpenCompetitionsTab != null) {
        widget.onOpenCompetitionsTab!();
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) => CompetitionDiscoveryScreen(
                controller: competitionController,
                baseUrl: widget.apiBaseUrl,
                backendMode: widget.backendMode,
                currentUserId: _userId,
                currentUserName: _userName,
                isAuthenticated: widget.exchangeController.isAuthenticated,
                onOpenLogin: widget.onOpenLogin,
              ),
        ),
      );
      return;
    }
    if (target == _HomeLinkTarget.trophies && widget.onOpenClubSubtab != null) {
      widget.onOpenClubSubtab!(ClubNavigationTab.trophies);
      return;
    }
    if (target == _HomeLinkTarget.tactics && widget.onOpenClubSubtab != null) {
      widget.onOpenClubSubtab!(ClubNavigationTab.tactics);
      return;
    }
    await _ensureClubLoaded();
    if (!mounted) {
      return;
    }
    if (target == _HomeLinkTarget.trophies) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) =>
                  ClubTrophyCabinetScreen(controller: clubController),
        ),
      );
      return;
    }
    final _HomeSnapshot snapshot = _HomeSnapshot.fromSources(
      clubName: clubName,
      isAuthenticated: widget.exchangeController.isAuthenticated,
      userLabel: _displayUserLabel(),
      clubData: clubController.data,
      competitions: competitionController.competitions,
    );
    if (target == _HomeLinkTarget.replays) {
      final GteNavigationDependencies? dependencies =
          widget.navigationDependencies;
      final String? canonicalClubId = widget.clubId?.trim();
      if (dependencies != null &&
          canonicalClubId != null &&
          canonicalClubId.isNotEmpty) {
        await GteNavigationHelpers.pushRoute(
          context,
          route: ClubReplaysRouteData(
            clubId: canonicalClubId,
            clubName: clubName,
          ),
          dependencies: dependencies,
        );
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) => _HomeReplayHubScreen(
                clubName: clubName,
                replays: snapshot.replays,
              ),
        ),
      );
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => _HomeTacticsScreen(
              clubName: clubName,
              nextMatch: snapshot.nextMatch,
              tacticalNotes: snapshot.tacticalNotes,
            ),
      ),
    );
  }

  Future<void> _ensureClubLoaded() async {
    final ClubController? clubController = _clubController;
    if (clubController == null || clubController.hasData) {
      return;
    }
    if (!clubController.isLoading) {
      await clubController.load();
      return;
    }
    while (clubController.isLoading && mounted) {
      await Future<void>.delayed(const Duration(milliseconds: 60));
    }
  }

  Future<void> _openCreateClubFlow() async {
    final String? accessToken = widget.exchangeController.accessToken;
    if (accessToken == null || accessToken.trim().isEmpty) {
      widget.onOpenLogin?.call();
      return;
    }
    final GteCreatedClubProfile? created = await Navigator.of(
      context,
    ).push<GteCreatedClubProfile>(
      MaterialPageRoute<GteCreatedClubProfile>(
        builder:
            (BuildContext context) => CreateClubScreen(
              baseUrl: widget.apiBaseUrl,
              accessToken: accessToken,
              backendMode: widget.backendMode,
              onClubCreated: _adoptCreatedClub,
            ),
      ),
    );
    if (created != null) {
      _adoptCreatedClub(created);
    }
  }

  void _adoptCreatedClub(GteCreatedClubProfile club) {
    widget.exchangeController.bindCurrentClub(
      clubId: club.id,
      clubName: club.clubName,
      clubSlug: club.slug,
    );
    widget.onOpenClubTab?.call();
  }
}

class _HomeHeroPanel extends StatelessWidget {
  const _HomeHeroPanel({
    required this.clubName,
    required this.userLabel,
    required this.title,
    required this.subtitle,
    required this.capitalLabel,
    required this.liveLabel,
    required this.chips,
    required this.isAuthenticated,
    required this.onOpenClub,
    required this.onOpenCompetitions,
    this.onOpenWallet,
    this.onOpenLogin,
  });

  final String clubName;
  final String userLabel;
  final String title;
  final String subtitle;
  final String capitalLabel;
  final String liveLabel;
  final List<Widget> chips;
  final bool isAuthenticated;
  final VoidCallback onOpenClub;
  final VoidCallback onOpenCompetitions;
  final VoidCallback? onOpenWallet;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Home'.toUpperCase(),
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: GteShellTheme.accent,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '$clubName • $userLabel',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: GteShellTheme.textMuted),
          ),
          const SizedBox(height: 8),
          Text(title, style: Theme.of(context).textTheme.displaySmall),
          const SizedBox(height: 8),
          Text(subtitle, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 18),
          Wrap(spacing: 12, runSpacing: 12, children: chips),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed: onOpenClub,
                icon: const Icon(Icons.shield_outlined),
                label: const Text('Enter club'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenCompetitions,
                icon: const Icon(Icons.stadium_outlined),
                label: const Text('Play now'),
              ),
              if (onOpenWallet != null)
                FilledButton.tonalIcon(
                  onPressed: onOpenWallet,
                  icon: const Icon(Icons.account_balance_wallet_outlined),
                  label: const Text('Capital room'),
                ),
              if (!isAuthenticated && onOpenLogin != null)
                OutlinedButton(
                  onPressed: onOpenLogin,
                  child: const Text('Sign in for alerts'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HomeRuntimeSignalPanel extends StatelessWidget {
  const _HomeRuntimeSignalPanel({
    required this.backendMode,
    required this.apiHostLabel,
    required this.narrative,
    required this.isAuthenticated,
    required this.hasClubScope,
    required this.capitalLabel,
    required this.isSyncing,
  });

  final GteBackendMode backendMode;
  final String apiHostLabel;
  final String narrative;
  final bool isAuthenticated;
  final bool hasClubScope;
  final String capitalLabel;
  final bool isSyncing;

  @override
  Widget build(BuildContext context) {
    final bool liveMode = backendMode == GteBackendMode.live;
    final Color accent =
        liveMode ? GteShellTheme.accentCapital : GteShellTheme.accentWarm;
    return GteSurfacePanel(
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'LIVE RUNTIME SIGNAL',
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(color: accent, letterSpacing: 1.1),
          ),
          const SizedBox(height: 10),
          Text(
            liveMode
                ? 'This shell is riding the live GTEX stack.'
                : 'This shell is running a non-live runtime path.',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(narrative, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Runtime',
                value: _runtimeLabel(),
                positive: liveMode,
              ),
              GteMetricChip(
                label: 'API Host',
                value: apiHostLabel,
                positive: true,
              ),
              GteMetricChip(
                label: 'Access',
                value: isAuthenticated ? 'Signed in' : 'Guest',
                positive: isAuthenticated,
              ),
              GteMetricChip(
                label: 'Club Scope',
                value: hasClubScope ? 'Club ready' : 'Onboarding',
                positive: hasClubScope,
              ),
              GteMetricChip(
                label: 'Capital',
                value: capitalLabel,
                positive: true,
              ),
              GteMetricChip(
                label: 'Sync Rail',
                value: isSyncing ? 'Syncing' : 'Stable',
                positive: !isSyncing,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _runtimeLabel() {
    switch (backendMode) {
      case GteBackendMode.live:
        return 'Live';
      case GteBackendMode.fixture:
        return 'Fixture';
      case GteBackendMode.liveThenFixture:
        return 'Hybrid';
    }
  }
}

class _HomeStatusPill extends StatelessWidget {
  const _HomeStatusPill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: color,
          letterSpacing: 1,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _HomeSignalCard extends StatelessWidget {
  const _HomeSignalCard({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: accent.withValues(alpha: 0.10),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: accent),
          ),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}

class _HomeQuickActionsStrip extends StatelessWidget {
  const _HomeQuickActionsStrip({
    required this.isAuthenticated,
    required this.onOpenMarket,
    required this.onOpenCompetitions,
    required this.onOpenReplays,
    this.onOpenLogin,
  });

  final bool isAuthenticated;
  final VoidCallback? onOpenMarket;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenReplays;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columnCount =
            constraints.maxWidth >= 1220
                ? 3
                : constraints.maxWidth >= 760
                ? 2
                : 1;
        final List<Widget> cards = <Widget>[
          _HomeActionCard(
            eyebrow: 'PLAY',
            title: 'Jump into matchday',
            detail:
                'Fixtures, cups, and live football stories stay in one lane so the next whistle is obvious.',
            icon: Icons.stadium_outlined,
            accent: GteShellTheme.accentArena,
            badge: 'Live',
            emphasized: true,
            actionLabel: 'Play now',
            onTap: onOpenCompetitions,
          ),
          _HomeActionCard(
            eyebrow: 'MARKET',
            title: 'Trade players + regens',
            detail:
                isAuthenticated
                    ? 'Open the player market to scout real players, regen upside, and the current quote tape from one execution lane.'
                    : 'The player market is visible in guest mode. Sign in when you are ready to buy, fund GTEX Coin, and hold assets.',
            icon: Icons.person_search_outlined,
            accent: GteShellTheme.accent,
            badge: 'Live',
            actionLabel:
                isAuthenticated ? 'Open player market' : 'Preview market',
            onTap: onOpenMarket ?? onOpenLogin,
          ),
          _HomeActionCard(
            eyebrow: isAuthenticated ? 'MATCHDAY' : 'ACCESS',
            title:
                isAuthenticated
                    ? 'Open the live match hub'
                    : 'Create or sign in',
            detail:
                isAuthenticated
                    ? '2D, broadcast, and Flutter 3D lanes stay one route away from Home instead of hiding behind replay-only detours.'
                    : 'Open the auth lane to create an account, fund GTEX Coin, buy players, and bind a real club workspace.',
            icon:
                isAuthenticated
                    ? Icons.live_tv_outlined
                    : Icons.lock_open_outlined,
            accent:
                isAuthenticated
                    ? GteShellTheme.accentArena
                    : GteShellTheme.accentCapital,
            badge: isAuthenticated ? 'Tap' : 'Secure',
            actionLabel: isAuthenticated ? 'Open matchday' : 'Create account',
            onTap: isAuthenticated ? onOpenReplays : onOpenLogin,
          ),
        ];
        if (columnCount == 1) {
          return Column(
            children: cards
                .map(
                  (Widget child) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: child,
                  ),
                )
                .toList(growable: false),
          );
        }
        return Row(
          children: cards
              .map(
                (Widget child) => Expanded(
                  child: Padding(
                    padding: EdgeInsets.only(
                      right: child == cards.last ? 0 : 12,
                    ),
                    child: child,
                  ),
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _HomeActionCard extends StatelessWidget {
  const _HomeActionCard({
    required this.eyebrow,
    required this.title,
    required this.detail,
    required this.icon,
    required this.accent,
    required this.badge,
    required this.actionLabel,
    this.emphasized = false,
    this.onTap,
  });

  final String eyebrow;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
  final String badge;
  final String actionLabel;
  final bool emphasized;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accent,
      emphasized: emphasized,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: accent.withValues(alpha: 0.18)),
                ),
                child: Icon(icon, color: accent, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  eyebrow,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: accent,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(detail, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 14),
          Text(
            actionLabel,
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(color: accent),
          ),
        ],
      ),
    );
  }
}

class _HomeJourneyPanel extends StatelessWidget {
  const _HomeJourneyPanel({
    required this.isAuthenticated,
    required this.clubName,
    required this.notificationCount,
    required this.openCompetitionCount,
    required this.onOpenCompetitions,
    required this.onOpenClub,
    this.onOpenLogin,
  });

  final bool isAuthenticated;
  final String clubName;
  final int notificationCount;
  final int openCompetitionCount;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenClub;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    final String title =
        isAuthenticated
            ? 'Next best moves for $clubName'
            : 'Guest mode is polished, but your account is still on the touchline';
    final String message =
        isAuthenticated
            ? 'There are $openCompetitionCount open competition lanes and $notificationCount alerts waiting. Use Home to move with intent instead of bouncing between tabs.'
            : 'Browse the shell, inspect market and arena context, then sign in when you are ready to trade, fund, and save club changes.';
    return GteSurfacePanel(
      accentColor:
          isAuthenticated ? GteShellTheme.accent : GteShellTheme.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(message, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonal(
                onPressed: onOpenCompetitions,
                child: Text(
                  isAuthenticated
                      ? 'See open competitions'
                      : 'Preview live match center',
                ),
              ),
              FilledButton.tonal(
                onPressed: onOpenClub,
                child: const Text('Open club lane'),
              ),
              if (!isAuthenticated && onOpenLogin != null)
                FilledButton(
                  onPressed: onOpenLogin,
                  child: const Text('Unlock account'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HomeRegenUniverseSection extends StatelessWidget {
  const _HomeRegenUniverseSection({
    required this.controller,
    required this.onRetry,
    required this.onOpenNationalTeams,
    required this.onOpenWorldRegens,
  });

  final RegenUniverseController controller;
  final Future<void> Function() onRetry;
  final VoidCallback onOpenNationalTeams;
  final VoidCallback onOpenWorldRegens;

  @override
  Widget build(BuildContext context) {
    final RegenGenerationTracking? tracking = controller.tracking;
    final List<NationalRegenSeed> nationalRegens = controller.nationalRegens
        .take(4)
        .toList(growable: false);
    final RegenGenerationTrackingEntry? leadingCountry =
        tracking == null || tracking.countryDistribution.isEmpty
            ? null
            : tracking.countryDistribution.first;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const _HomeSectionHeading(
          eyebrow: 'REGEN UNIVERSE',
          title: 'The talent map keeps producing new names and new stories.',
          detail:
              'Rising stars surface the best prospects, national-team pools expose pre-seeded regens, and world context keeps club-generated pathways visible.',
        ),
        const SizedBox(height: 14),
        GteSurfacePanel(
          accentColor: GteShellTheme.accent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'National seeds and club regen routes',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                'National teams opens the pre-seeded U17 pool. World context keeps club-generated regen discovery, scouting, and tracking in one visible route.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  FilledButton.tonalIcon(
                    onPressed: onOpenNationalTeams,
                    icon: const Icon(Icons.flag_outlined),
                    label: const Text('National regen pool'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: onOpenWorldRegens,
                    icon: const Icon(Icons.public_outlined),
                    label: const Text('Open world regen desk'),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  _RegenMetaChip(
                    label:
                        '${nationalRegens.length} visible national pre-seeds',
                  ),
                  if (tracking != null)
                    _RegenMetaChip(
                      label:
                          '${tracking.totalSeededPlayers} total seeded players tracked',
                    ),
                  if (leadingCountry != null)
                    _RegenMetaChip(
                      label:
                          '${leadingCountry.bucket}: ${leadingCountry.count} tracked',
                    ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final int columnCount = constraints.maxWidth >= 1100 ? 2 : 1;
            final double spacing = 16;
            final double cardWidth =
                (constraints.maxWidth - (spacing * (columnCount - 1))) /
                columnCount;
            return Wrap(
              spacing: spacing,
              runSpacing: spacing,
              children: <Widget>[
                SizedBox(
                  width: cardWidth,
                  child: _HomeRegenRisingStarsPanel(
                    controller: controller,
                    onRetry: onRetry,
                  ),
                ),
                SizedBox(
                  width: cardWidth,
                  child: _HomeScoutingFeedPanel(
                    controller: controller,
                    onRetry: onRetry,
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _HomeRegenRisingStarsPanel extends StatelessWidget {
  const _HomeRegenRisingStarsPanel({
    required this.controller,
    required this.onRetry,
  });

  final RegenUniverseController controller;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final List<RegenRisingStar> stars = controller.risingStars
        .take(4)
        .toList(growable: false);
    return GteSurfacePanel(
      key: const Key('home-regen-rising-stars'),
      emphasized: stars.isNotEmpty,
      accentColor: GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _RegenPanelHeader(
            title: 'RISING STARS',
            subtitle: 'Ages 15-21 with the strongest upside curves.',
            isLoading: controller.isLoading,
          ),
          const SizedBox(height: 16),
          if (stars.isEmpty)
            _RegenEmptyState(
              icon:
                  controller.errorMessage == null
                      ? Icons.radar_outlined
                      : Icons.error_outline,
              message:
                  controller.errorMessage ??
                  (controller.isLoading
                      ? 'Scanning academy pipelines and national pools.'
                      : 'No rising stars are visible yet.'),
              actionLabel: controller.errorMessage == null ? null : 'Retry',
              onAction:
                  controller.errorMessage == null
                      ? null
                      : () {
                        onRetry();
                      },
            )
          else
            ...stars.map(
              (RegenRisingStar star) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: _RegenRisingStarTile(star: star),
              ),
            ),
        ],
      ),
    );
  }
}

class _HomeScoutingFeedPanel extends StatelessWidget {
  const _HomeScoutingFeedPanel({
    required this.controller,
    required this.onRetry,
  });

  final RegenUniverseController controller;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final List<RegenScoutingFeedItem> feed = controller.scoutingFeed
        .take(4)
        .toList(growable: false);
    return GteSurfacePanel(
      key: const Key('home-regen-scouting-feed'),
      accentColor: GteShellTheme.accentWarm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _RegenPanelHeader(
            title: 'SCOUTING FEED',
            subtitle: 'Fresh discoveries, spikes, and watchlist movement.',
            isLoading: controller.isLoading,
          ),
          const SizedBox(height: 16),
          if (feed.isEmpty)
            _RegenEmptyState(
              icon:
                  controller.errorMessage == null
                      ? Icons.travel_explore_outlined
                      : Icons.error_outline,
              message:
                  controller.errorMessage ??
                  (controller.isLoading
                      ? 'Refreshing the live scouting wire.'
                      : 'No scouting updates are in the feed yet.'),
              actionLabel: controller.errorMessage == null ? null : 'Retry',
              onAction:
                  controller.errorMessage == null
                      ? null
                      : () {
                        onRetry();
                      },
            )
          else
            ...feed.map(
              (RegenScoutingFeedItem item) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: _RegenScoutingFeedTile(item: item),
              ),
            ),
        ],
      ),
    );
  }
}

class _RegenPanelHeader extends StatelessWidget {
  const _RegenPanelHeader({
    required this.title,
    required this.subtitle,
    required this.isLoading,
  });

  final String title;
  final String subtitle;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        if (isLoading)
          Text(
            'SYNCING',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: GteShellTheme.accent,
              letterSpacing: 0.8,
            ),
          ),
      ],
    );
  }
}

class _RegenEmptyState extends StatelessWidget {
  const _RegenEmptyState({
    required this.icon,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon, color: GteShellTheme.accentWarm),
        const SizedBox(height: 12),
        Text(message, style: Theme.of(context).textTheme.bodyMedium),
        if (actionLabel != null && onAction != null) ...<Widget>[
          const SizedBox(height: 12),
          FilledButton.tonal(onPressed: onAction, child: Text(actionLabel!)),
        ],
      ],
    );
  }
}

class _RegenRisingStarTile extends StatelessWidget {
  const _RegenRisingStarTile({required this.star});

  final RegenRisingStar star;

  @override
  Widget build(BuildContext context) {
    final RegenUniversePlayer player = star.player;
    final List<String> badges = <String>[
      star.momentumLabel,
      _humanizeRegenSource(player.sourceType),
      ...star.badges.take(2),
    ].where((String value) => value.trim().isNotEmpty).toList(growable: false);
    final String nationality = player.nationalityCode ?? player.nationality;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: GteShellTheme.accent.withValues(alpha: 0.18)),
        color: Colors.black.withValues(alpha: 0.08),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      player.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${player.age} | $nationality | ${player.position}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              _RegenScoreBadge(
                label: 'OVR',
                value: player.currentRating.toString(),
              ),
              const SizedBox(width: 8),
              _RegenScoreBadge(
                label: 'POT',
                value: player.potential.toString(),
              ),
            ],
          ),
          if (star.storySnippet != null && star.storySnippet!.trim().isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                star.storySnippet!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: badges
                .map((String badge) => _RegenMetaChip(label: badge))
                .toList(growable: false),
          ),
          if (star.marketValueCoin != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              gteFormatCredits(star.marketValueCoin!.toDouble()),
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(color: GteShellTheme.accentWarm),
            ),
          ],
        ],
      ),
    );
  }
}

class _RegenScoutingFeedTile extends StatelessWidget {
  const _RegenScoutingFeedTile({required this.item});

  final RegenScoutingFeedItem item;

  @override
  Widget build(BuildContext context) {
    final RegenUniversePlayer? player = item.player;
    final List<String> badges = <String>[
      _humanizeSlug(item.feedType),
      if (player != null) _humanizeRegenSource(player.sourceType),
      ...item.badges.take(2).map(_humanizeSlug),
    ].where((String value) => value.trim().isNotEmpty).toList(growable: false);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: GteShellTheme.accentWarm.withValues(alpha: 0.18),
        ),
        color: Colors.black.withValues(alpha: 0.08),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Padding(
                padding: EdgeInsets.only(top: 2),
                child: Icon(
                  Icons.flash_on_outlined,
                  color: GteShellTheme.accentWarm,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      item.title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      gteFormatRelativeTime(item.occurredAt),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GteShellTheme.accent,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(item.summary, style: Theme.of(context).textTheme.bodyMedium),
          if (player != null) ...<Widget>[
            const SizedBox(height: 10),
            Text(
              '${player.name} | ${player.age} | ${player.position} | ${player.potential} POT | ${_humanizeRegenSource(player.sourceType)}',
              style: Theme.of(context).textTheme.labelLarge,
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: badges
                .map((String badge) => _RegenMetaChip(label: badge))
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class _RegenScoreBadge extends StatelessWidget {
  const _RegenScoreBadge({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: GteShellTheme.accent.withValues(alpha: 0.12),
        border: Border.all(color: GteShellTheme.accent.withValues(alpha: 0.2)),
      ),
      child: Column(
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelSmall?.copyWith(letterSpacing: 0.7),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _RegenMetaChip extends StatelessWidget {
  const _RegenMetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(label, style: Theme.of(context).textTheme.labelMedium),
    );
  }
}

String _humanizeSlug(String value) {
  final String normalized = value.trim();
  if (normalized.isEmpty) {
    return '';
  }
  final String spaced = normalized.replaceAll('_', ' ');
  return spaced[0].toUpperCase() + spaced.substring(1);
}

String _humanizeRegenSource(String value) {
  final String normalized = value.trim().toLowerCase();
  switch (normalized) {
    case 'national_seed':
      return 'National pre-seed';
    case 'legendary_seed':
      return 'Legendary pre-seed';
    case 'regen':
      return 'Club/world regen';
    default:
      return _humanizeSlug(value);
  }
}

class _HomeSectionHeading extends StatelessWidget {
  const _HomeSectionHeading({
    required this.eyebrow,
    required this.title,
    required this.detail,
  });

  final String eyebrow;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          eyebrow,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: GteShellTheme.accent,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: 12),
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text(detail, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}

class _InlineWarning extends StatelessWidget {
  const _InlineWarning({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Icon(Icons.info_outline, color: GteShellTheme.accentWarm),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(message, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class _HomeLoadingView extends StatelessWidget {
  const _HomeLoadingView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: const <Widget>[
        GteSurfacePanel(child: SizedBox(height: 170)),
        SizedBox(height: 20),
        GteSurfacePanel(child: SizedBox(height: 240)),
        SizedBox(height: 20),
        GteSurfacePanel(child: SizedBox(height: 180)),
      ],
    );
  }
}

class _HomeReplayHubScreen extends StatelessWidget {
  const _HomeReplayHubScreen({required this.clubName, required this.replays});

  final String clubName;
  final List<_HomeReplayEntry> replays;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Matchday stories')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '$clubName matchday deck',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Matchday cards follow the same club story Home is surfacing: recent honors, reputation spikes, and the moments worth revisiting.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            ...replays.map(
              (_HomeReplayEntry replay) => Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        replay.title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        replay.summary,
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        replay.caption,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: <Widget>[
                          _ReplayMetaChip(
                            label: 'When',
                            value: _formatDateLabel(replay.occurredAt),
                          ),
                          _ReplayMetaChip(
                            label: 'Track',
                            value: replay.trackLabel,
                          ),
                          _ReplayMetaChip(
                            label: 'Focus',
                            value: replay.focusLabel,
                          ),
                        ],
                      ),
                      if (replay.highlights.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 16),
                        ...replay.highlights
                            .take(3)
                            .map(
                              (String line) => Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Text(
                                  line,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ),
                            ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReplayMetaChip extends StatelessWidget {
  const _ReplayMetaChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.82),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _HomeTacticsScreen extends StatelessWidget {
  const _HomeTacticsScreen({
    required this.clubName,
    required this.nextMatch,
    required this.tacticalNotes,
  });

  final String clubName;
  final _HomeCardData nextMatch;
  final List<String> tacticalNotes;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Tactics')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '$clubName match board',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Home tactics stays lightweight: shape, match rhythm, and the tactical cues attached to the next live moment on the club calendar.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            HomeSectionCard(
              eyebrow: nextMatch.eyebrow,
              title: nextMatch.title,
              summary: nextMatch.summary,
              detail: nextMatch.detail,
              icon: Icons.sports_soccer_outlined,
              accent: GteShellTheme.accent,
              stats: nextMatch.stats,
              highlights: const <String>[],
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Tactical cues',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 14),
                  ...tacticalNotes.map(
                    (String note) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          const Padding(
                            padding: EdgeInsets.only(top: 2),
                            child: Icon(
                              Icons.adjust_outlined,
                              size: 18,
                              color: GteShellTheme.accentWarm,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              note,
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

enum _HomeLinkTarget { competitions, replays, club, trophies, tactics }

enum _FeaturedEventType { worldSuperCup, championsLeague, league, fastCup }

class _HomeIdentity {
  const _HomeIdentity({
    required this.userId,
    required this.userName,
    required this.clubId,
    required this.clubName,
  });

  final String userId;
  final String? userName;
  final String? clubId;
  final String? clubName;
}

class _HomeSnapshot {
  const _HomeSnapshot({
    required this.heroTitle,
    required this.heroSubtitle,
    required this.prestigeLabel,
    required this.totalHonors,
    required this.openCompetitionCount,
    required this.notificationCount,
    required this.featuredBanner,
    required this.nextMatch,
    required this.leagueSnapshot,
    required this.championsLeagueStatus,
    required this.fastCupCountdown,
    required this.recentReplay,
    required this.notificationsSummary,
    required this.replays,
    required this.tacticalNotes,
  });

  final String heroTitle;
  final String heroSubtitle;
  final String prestigeLabel;
  final int totalHonors;
  final int openCompetitionCount;
  final int notificationCount;
  final _HomeBannerData featuredBanner;
  final _HomeCardData nextMatch;
  final _HomeCardData leagueSnapshot;
  final _HomeCardData championsLeagueStatus;
  final _HomeCardData fastCupCountdown;
  final _HomeCardData recentReplay;
  final _HomeCardData notificationsSummary;
  final List<_HomeReplayEntry> replays;
  final List<String> tacticalNotes;

  factory _HomeSnapshot.fromSources({
    required String clubName,
    required bool isAuthenticated,
    required String userLabel,
    required ClubDashboardData? clubData,
    required List<CompetitionSummary> competitions,
  }) {
    final String resolvedClubName = clubData?.clubName ?? clubName;
    final DateTime now = DateTime.now().toUtc();
    final CompetitionSummary? featuredLeague = _pickCompetition(
      competitions,
      CompetitionFormat.league,
    );
    final CompetitionSummary? featuredCup = _pickCompetition(
      competitions,
      CompetitionFormat.cup,
    );
    final TrophyItemDto? worldSuperCup = _latestHonor(
      clubData?.trophyCabinet.recentHonors,
      (TrophyItemDto item) => item.isWorldSuperCup,
    );
    final TrophyItemDto? championsLeague = _latestHonor(
      clubData?.trophyCabinet.recentHonors,
      (TrophyItemDto item) => item.trophyType == 'champions_league',
    );
    final TrophyItemDto? leagueHonor = _latestHonor(
      clubData?.trophyCabinet.recentHonors,
      (TrophyItemDto item) =>
          item.trophyType == 'league_title' ||
          item.trophyType == 'league_runner_up',
    );
    final TrophyItemDto? fastCupHonor = _latestHonor(
      clubData?.trophyCabinet.recentHonors,
      (TrophyItemDto item) => item.trophyType == 'fast_cup',
    );
    final DynastyProfileDto? dynasty = clubData?.dynastyProfile;
    final DynastySeasonSummaryDto? latestSeason =
        dynasty == null || dynasty.lastFourSeasonSummary.isEmpty
            ? null
            : dynasty.lastFourSeasonSummary.last;
    final _HomeMatchPreview matchPreview = _buildNextMatch(
      clubName: resolvedClubName,
      league: featuredLeague,
      dynasty: dynasty,
      now: now,
    );
    final DateTime fastCupStart = _nextFastCupWindow(now);
    final List<_HomeReplayEntry> replays = _buildReplayEntries(
      clubData: clubData,
      resolvedClubName: resolvedClubName,
    );
    final _HomeBannerData featuredBanner = _buildFeaturedBanner(
      clubName: resolvedClubName,
      dynasty: dynasty,
      latestSeason: latestSeason,
      featuredLeague: featuredLeague,
      featuredCup: featuredCup,
      worldSuperCup: worldSuperCup,
      championsLeague: championsLeague,
      leagueHonor: leagueHonor,
      fastCupHonor: fastCupHonor,
    );
    final List<String> tacticalNotes = _buildTacticalNotes(
      clubName: resolvedClubName,
      featuredBanner: featuredBanner,
      matchPreview: matchPreview,
      featuredCup: featuredCup,
    );
    final List<String> notifications = _buildNotifications(
      clubName: resolvedClubName,
      isAuthenticated: isAuthenticated,
      featuredBanner: featuredBanner,
      league: featuredLeague,
      fastCupStart: fastCupStart,
      matchPreview: matchPreview,
      replays: replays,
    );
    final int totalHonors = clubData?.trophyCabinet.totalHonorsCount ?? 0;
    final int openCompetitionCount =
        competitions
            .where(
              (CompetitionSummary item) =>
                  item.status == CompetitionStatus.openForJoin,
            )
            .length;
    final String prestigeLabel =
        clubData?.reputation.profile.currentPrestigeTier.label ?? 'Preview';
    return _HomeSnapshot(
      heroTitle:
          isAuthenticated
              ? '$userLabel, the exchange is moving.'
              : 'Home is ready for $resolvedClubName.',
      heroSubtitle:
          'Next match, cups, matchday stories, and club momentum are all live from Home.',
      prestigeLabel: prestigeLabel,
      totalHonors: totalHonors,
      openCompetitionCount: openCompetitionCount,
      notificationCount: notifications.length,
      featuredBanner: featuredBanner,
      nextMatch: _HomeCardData(
        eyebrow: 'Next Match',
        title: matchPreview.opponent,
        summary:
            '${matchPreview.stageLabel} is ${_relativeLabel(matchPreview.kickoff, now)}.',
        detail:
            '$resolvedClubName go in with a ${matchPreview.planLabel.toLowerCase()} and ${matchPreview.venueLabel.toLowerCase()}.',
        icon: Icons.sports_soccer_outlined,
        accent: GteShellTheme.accent,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>(
            'Kickoff',
            _formatDayTime(matchPreview.kickoff),
          ),
          MapEntry<String, String>('Venue', matchPreview.venueLabel),
          MapEntry<String, String>('Plan', matchPreview.planLabel),
        ],
        highlights: const <String>[],
        actionLabel: 'Open club',
        target: _HomeLinkTarget.club,
      ),
      leagueSnapshot: _HomeCardData(
        eyebrow: 'League Snapshot',
        title: featuredLeague?.name ?? 'Domestic table pulse',
        summary:
            latestSeason?.leagueFinish != null
                ? '$resolvedClubName closed ${latestSeason!.seasonLabel} in ${_ordinal(latestSeason.leagueFinish!)} place.'
                : 'League traction is building and the table is moving again.',
        detail:
            featuredLeague == null
                ? 'Competition discovery has no league feed yet, but Home is holding the domestic lane open.'
                : '${featuredLeague.participantCount}/${featuredLeague.capacity} entries are live with ${_competitionStatusLabel(featuredLeague.status).toLowerCase()} status.',
        icon: Icons.table_chart_outlined,
        accent: GteShellTheme.accentWarm,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>(
            'Finish',
            latestSeason?.leagueFinish == null
                ? '--'
                : _ordinal(latestSeason!.leagueFinish!),
          ),
          MapEntry<String, String>(
            'Grid',
            featuredLeague == null
                ? '--'
                : '${featuredLeague.participantCount}/${featuredLeague.capacity}',
          ),
          MapEntry<String, String>(
            'Entry',
            featuredLeague == null
                ? '--'
                : _formatCompetitionAmount(
                  featuredLeague.entryFee,
                  featuredLeague.currency,
                ),
          ),
        ],
        highlights: <String>[
          if (featuredLeague != null)
            '${featuredLeague.creatorLabel} is driving the current league pulse.',
          if (latestSeason?.leagueTitle == true)
            'League-winning form is still the anchor behind the badge momentum.',
          if (latestSeason?.topFourFinish == true)
            'Top-four security keeps the domestic story warm for the next cycle.',
        ],
        actionLabel: 'Open competitions',
        target: _HomeLinkTarget.competitions,
      ),
      championsLeagueStatus: _HomeCardData(
        eyebrow: 'Champions League Status',
        title:
            championsLeague != null
                ? 'Continental crown still visible'
                : latestSeason?.topFourFinish == true
                ? 'Qualification line protected'
                : 'Continental push is live',
        summary:
            championsLeague != null
                ? championsLeague.finalResultSummary
                : latestSeason?.championsLeagueTitle == true
                ? 'Champions League silverware pushed the club into the elite conversation.'
                : latestSeason?.topFourFinish == true
                ? 'League placement kept Champions League access alive for the next run.'
                : 'The next continental step still runs through league control and trophy nights.',
        detail:
            _firstReason(dynasty?.reasons, 'Champions League') ??
            '${dynasty?.currentEraLabel.label ?? 'Club identity'} is shaping the continental case.',
        icon: Icons.public_outlined,
        accent: GteShellTheme.accentWarm,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>(
            'Status',
            championsLeague != null
                ? 'Champion'
                : latestSeason?.topFourFinish == true
                ? 'Qualified'
                : 'Chasing',
          ),
          MapEntry<String, String>(
            'Era',
            dynasty?.currentEraLabel.label ?? 'No dynasty yet',
          ),
          MapEntry<String, String>(
            'Titles',
            _countHonors(
              clubData?.trophyCabinet.recentHonors,
              (TrophyItemDto item) => item.trophyType == 'champions_league',
            ).toString(),
          ),
        ],
        highlights: <String>[
          if (latestSeason?.championsLeagueTitle == true)
            'Last campaign ended with a full continental crown.',
          if (latestSeason?.topFourFinish == true)
            'Top-four league work held onto the next Champions League spot.',
          if (dynasty != null && dynasty.reasons.isNotEmpty)
            dynasty.reasons.first,
        ],
        actionLabel: 'Open trophies',
        target: _HomeLinkTarget.trophies,
      ),
      fastCupCountdown: _HomeCardData(
        eyebrow: 'Next GTEX Fast Cup',
        title: 'Countdown ${_formatCountdown(fastCupStart.difference(now))}',
        summary:
            'The next Fast Cup window opens ${_formatDayTime(fastCupStart)} and Home is keeping the cup lane visible.',
        detail:
            featuredCup == null
                ? 'No cup feed is active yet, so Home is anchoring the next GTEX Fast Cup window from the shared schedule.'
                : '${featuredCup.name} is the current cup reference with ${_spotsLabel(featuredCup)} still moving.',
        icon: Icons.timer_outlined,
        accent: GteShellTheme.positive,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>('Starts', _formatDayTime(fastCupStart)),
          MapEntry<String, String>(
            'Format',
            featuredCup?.safeFormatLabel ?? 'Skill cup',
          ),
          MapEntry<String, String>(
            'Spots',
            featuredCup == null ? '--' : _spotsLabel(featuredCup),
          ),
        ],
        highlights: <String>[
          if (fastCupHonor != null)
            'Latest Fast Cup memory: ${fastCupHonor.finalResultSummary}.',
          if (featuredCup != null)
            '${featuredCup.creatorLabel} owns the current cup traffic.',
          'Fast Cup windows reward quick rotation and sharp restart legs.',
        ],
        actionLabel: 'Open competitions',
        target: _HomeLinkTarget.competitions,
      ),
      recentReplay: _HomeCardData(
        eyebrow: 'Matchday brief',
        title: replays.first.title,
        summary: replays.first.summary,
        detail: replays.first.caption,
        icon: Icons.ondemand_video_outlined,
        accent: GteShellTheme.accent,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>(
            'When',
            _formatDateLabel(replays.first.occurredAt),
          ),
          MapEntry<String, String>('Track', replays.first.trackLabel),
          MapEntry<String, String>('Focus', replays.first.focusLabel),
        ],
        highlights: replays.first.highlights,
        actionLabel: 'Open matchday',
        target: _HomeLinkTarget.replays,
      ),
      notificationsSummary: _HomeCardData(
        eyebrow: 'Notifications Summary',
        title: '${notifications.length} fresh signals',
        summary:
            'Club, competition, and matchday updates are grouped into one Home queue so the next decision is immediate.',
        detail:
            isAuthenticated
                ? 'Signed in sessions keep the club pulse and competition pulse aligned.'
                : 'Signed-out mode stays in preview, but the club pulse is still readable.',
        icon: Icons.notifications_active_outlined,
        accent: GteShellTheme.positive,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>(
            'Club',
            (clubData?.reputation.recentEvents.length ?? 0).toString(),
          ),
          MapEntry<String, String>(
            'Cups',
            competitions
                .where((CompetitionSummary item) => item.isCup)
                .length
                .toString(),
          ),
          MapEntry<String, String>(
            'Mode',
            isAuthenticated ? 'Live' : 'Preview',
          ),
        ],
        highlights: notifications,
        actionLabel: 'Open tactics',
        target: _HomeLinkTarget.tactics,
      ),
      replays: replays,
      tacticalNotes: tacticalNotes,
    );
  }
}

class _HomeBannerData {
  const _HomeBannerData({
    required this.type,
    required this.label,
    required this.title,
    required this.summary,
    required this.body,
    required this.icon,
    required this.gradientColors,
    required this.stats,
    required this.actionLabel,
    required this.target,
  });

  final _FeaturedEventType type;
  final String label;
  final String title;
  final String summary;
  final String body;
  final IconData icon;
  final List<Color> gradientColors;
  final List<MapEntry<String, String>> stats;
  final String actionLabel;
  final _HomeLinkTarget target;
}

class _HomeCardData {
  const _HomeCardData({
    required this.eyebrow,
    required this.title,
    required this.summary,
    required this.icon,
    required this.accent,
    required this.stats,
    required this.highlights,
    required this.actionLabel,
    required this.target,
    this.detail,
  });

  final String eyebrow;
  final String title;
  final String summary;
  final String? detail;
  final IconData icon;
  final Color accent;
  final List<MapEntry<String, String>> stats;
  final List<String> highlights;
  final String actionLabel;
  final _HomeLinkTarget target;
}

class _HomeMatchPreview {
  const _HomeMatchPreview({
    required this.opponent,
    required this.stageLabel,
    required this.kickoff,
    required this.venueLabel,
    required this.planLabel,
  });

  final String opponent;
  final String stageLabel;
  final DateTime kickoff;
  final String venueLabel;
  final String planLabel;
}

class _HomeReplayEntry {
  const _HomeReplayEntry({
    required this.title,
    required this.summary,
    required this.caption,
    required this.trackLabel,
    required this.focusLabel,
    required this.occurredAt,
    required this.highlights,
  });

  final String title;
  final String summary;
  final String caption;
  final String trackLabel;
  final String focusLabel;
  final DateTime occurredAt;
  final List<String> highlights;
}

_HomeBannerData _buildFeaturedBanner({
  required String clubName,
  required DynastyProfileDto? dynasty,
  required DynastySeasonSummaryDto? latestSeason,
  required CompetitionSummary? featuredLeague,
  required CompetitionSummary? featuredCup,
  required TrophyItemDto? worldSuperCup,
  required TrophyItemDto? championsLeague,
  required TrophyItemDto? leagueHonor,
  required TrophyItemDto? fastCupHonor,
}) {
  if (worldSuperCup != null ||
      latestSeason?.worldSuperCupWinner == true ||
      latestSeason?.worldSuperCupQualified == true) {
    return _HomeBannerData(
      type: _FeaturedEventType.worldSuperCup,
      label: 'World Super Cup Banner',
      title: 'World Super Cup pressure is back on $clubName.',
      summary:
          worldSuperCup?.finalResultSummary ??
          'The latest cycle kept the club in the rarest global conversation.',
      body:
          worldSuperCup != null
              ? '${worldSuperCup.seasonLabel} put the badge on the world stage again.'
              : 'World Super Cup qualification sits above every other Home signal, so it moves straight to the top of the banner stack.',
      icon: Icons.language_outlined,
      gradientColors: const <Color>[
        Color(0xFF302107),
        Color(0xFF17120B),
        Color(0xFF111827),
      ],
      stats: <MapEntry<String, String>>[
        MapEntry<String, String>(
          'Status',
          latestSeason?.worldSuperCupWinner == true ? 'Winner' : 'Qualified',
        ),
        MapEntry<String, String>(
          'Dynasty',
          dynasty?.currentEraLabel.label ?? 'No dynasty yet',
        ),
        MapEntry<String, String>(
          'Season',
          worldSuperCup?.seasonLabel ?? latestSeason?.seasonLabel ?? '--',
        ),
      ],
      actionLabel: 'Open trophies',
      target: _HomeLinkTarget.trophies,
    );
  }
  if (championsLeague != null || latestSeason?.championsLeagueTitle == true) {
    return _HomeBannerData(
      type: _FeaturedEventType.championsLeague,
      label: 'Champions League Status',
      title: 'Champions League nights still define the crest.',
      summary:
          championsLeague?.finalResultSummary ??
          'Continental silverware is the strongest active story behind the club right now.',
      body:
          _firstReason(dynasty?.reasons, 'Champions League') ??
          'When no World Super Cup signal is active, Champions League momentum owns the Home banner.',
      icon: Icons.public_outlined,
      gradientColors: const <Color>[
        Color(0xFF2E1D04),
        Color(0xFF151313),
        Color(0xFF111827),
      ],
      stats: <MapEntry<String, String>>[
        MapEntry<String, String>('Status', 'Continental focus'),
        MapEntry<String, String>(
          'Era',
          dynasty?.currentEraLabel.label ?? 'Building',
        ),
        MapEntry<String, String>(
          'Season',
          championsLeague?.seasonLabel ?? latestSeason?.seasonLabel ?? '--',
        ),
      ],
      actionLabel: 'Open trophies',
      target: _HomeLinkTarget.trophies,
    );
  }
  if (leagueHonor != null ||
      latestSeason?.leagueFinish != null ||
      featuredLeague != null) {
    return _HomeBannerData(
      type: _FeaturedEventType.league,
      label: 'League Snapshot',
      title: 'League form is carrying the Home page.',
      summary:
          leagueHonor?.finalResultSummary ??
          (latestSeason?.leagueFinish != null
              ? 'Latest domestic finish landed at ${_ordinal(latestSeason!.leagueFinish!)}.'
              : 'The next league window is the strongest active route on the board.'),
      body:
          featuredLeague == null
              ? 'League momentum outranks Fast Cup promotion in the banner stack whenever the domestic signal is active.'
              : '${featuredLeague.name} is the current league reference point with ${featuredLeague.participantCount}/${featuredLeague.capacity} entries already live.',
      icon: Icons.stadium_outlined,
      gradientColors: const <Color>[
        Color(0xFF0D2C20),
        Color(0xFF111827),
        Color(0xFF0D1724),
      ],
      stats: <MapEntry<String, String>>[
        MapEntry<String, String>(
          'Finish',
          latestSeason?.leagueFinish == null
              ? '--'
              : _ordinal(latestSeason!.leagueFinish!),
        ),
        MapEntry<String, String>(
          'Competition',
          featuredLeague?.safeFormatLabel ?? 'League pulse',
        ),
        MapEntry<String, String>(
          'Update',
          featuredLeague == null
              ? '--'
              : _formatDateLabel(featuredLeague.updatedAt),
        ),
      ],
      actionLabel: 'Open competitions',
      target: _HomeLinkTarget.competitions,
    );
  }
  return _HomeBannerData(
    type: _FeaturedEventType.fastCup,
    label: 'Fast Cup Signal',
    title: 'Fast Cup countdown takes the banner slot.',
    summary:
        fastCupHonor?.finalResultSummary ??
        'No world, continental, or league headline is stronger right now, so the Fast Cup window moves to the top.',
    body:
        featuredCup == null
            ? 'The GTEX Fast Cup keeps Home alive when the rest of the trophy ladder is quiet.'
            : '${featuredCup.name} is the cup traffic Home is leaning on until the next bigger event lands.',
    icon: Icons.flash_on_outlined,
    gradientColors: const <Color>[
      Color(0xFF08242A),
      Color(0xFF111827),
      Color(0xFF0D1724),
    ],
    stats: <MapEntry<String, String>>[
      MapEntry<String, String>('Priority', 'Fast Cup'),
      MapEntry<String, String>(
        'Format',
        featuredCup?.safeFormatLabel ?? 'Skill cup',
      ),
      MapEntry<String, String>(
        'Focus',
        fastCupHonor == null ? 'Upcoming window' : 'Recent winner',
      ),
    ],
    actionLabel: 'Open competitions',
    target: _HomeLinkTarget.competitions,
  );
}

_HomeMatchPreview _buildNextMatch({
  required String clubName,
  required CompetitionSummary? league,
  required DynastyProfileDto? dynasty,
  required DateTime now,
}) {
  const List<String> opponents = <String>[
    'Apex Harbor SC',
    'Golden Coast Union',
    'Metro Atlas',
    'Blue Meridian',
    'Capital Forge',
    'Red Summit',
  ];
  const List<String> venues = <String>[
    'Harbor Dome',
    'Lagoon Arena',
    'Summit Park',
    'Northlight Field',
    'Capital Terrace',
    'Meridian Bowl',
  ];
  final int seed = clubName.runes.fold<int>(
    0,
    (int sum, int rune) => sum + rune,
  );
  final DateTime kickoff = _nextKickoff(now, seed);
  final String planLabel = _tacticPlanLabel(dynasty?.currentEraLabel);
  final int matchday = 24 + (seed % 8);
  return _HomeMatchPreview(
    opponent: opponents[seed % opponents.length],
    stageLabel:
        league == null
            ? 'Club showcase fixture'
            : '${league.name} • Matchday $matchday',
    kickoff: kickoff,
    venueLabel: venues[seed % venues.length],
    planLabel: planLabel,
  );
}

List<_HomeReplayEntry> _buildReplayEntries({
  required ClubDashboardData? clubData,
  required String resolvedClubName,
}) {
  final List<_HomeReplayEntry> entries = <_HomeReplayEntry>[];
  if (clubData != null) {
    for (final TrophyItemDto honor in clubData.trophyCabinet.recentHonors.take(
      3,
    )) {
      entries.add(
        _HomeReplayEntry(
          title: '${honor.trophyName} story',
          summary: honor.finalResultSummary,
          caption: '${honor.seasonLabel} • ${honor.competitionRegion}',
          trackLabel:
              honor.isWorldSuperCup
                  ? 'World stage'
                  : honor.trophyType == 'champions_league'
                  ? 'Continental'
                  : 'Club legacy',
          focusLabel: honor.prestigeLabel,
          occurredAt: honor.earnedAt,
          highlights: <String>[
            if (honor.captainName != null) 'Captain: ${honor.captainName}',
            if (honor.topPerformerName != null)
              'Top performer: ${honor.topPerformerName}',
            'Competition tier: ${honor.competitionTier}',
          ],
        ),
      );
    }
    for (final ReputationEventDto event in clubData.reputation.recentEvents
        .take(2)) {
      entries.add(
        _HomeReplayEntry(
          title: '${event.title} story',
          summary: event.description,
          caption: event.seasonLabel,
          trackLabel: event.category.label,
          focusLabel: event.delta >= 0 ? '+${event.delta}' : '${event.delta}',
          occurredAt: event.occurredAt,
          highlights: <String>[
            'Category: ${event.category.label}',
            'Score impact: ${event.delta >= 0 ? '+' : ''}${event.delta}',
            if (event.badges.isNotEmpty)
              'Badges: ${event.badges.take(2).join(', ')}',
          ],
        ),
      );
    }
  }
  if (entries.isEmpty) {
    entries.add(
      _HomeReplayEntry(
        title: '$resolvedClubName matchday hub',
        summary:
            'Home will pin the strongest matchday card here once the next club moment lands.',
        caption: 'Club pulse',
        trackLabel: 'Home',
        focusLabel: 'Preview',
        occurredAt: DateTime.now().toUtc(),
        highlights: const <String>[
          'Matchday cards are ready for trophies, league swings, and prestige spikes.',
        ],
      ),
    );
  }
  entries.sort(
    (_HomeReplayEntry left, _HomeReplayEntry right) =>
        right.occurredAt.compareTo(left.occurredAt),
  );
  return entries.take(4).toList(growable: false);
}

List<String> _buildTacticalNotes({
  required String clubName,
  required _HomeBannerData featuredBanner,
  required _HomeMatchPreview matchPreview,
  required CompetitionSummary? featuredCup,
}) {
  late final String eventNote;
  switch (featuredBanner.type) {
    case _FeaturedEventType.worldSuperCup:
      eventNote =
          'Global-trophy pressure means wide rotations stay fresh and the press should not empty the midfield too early.';
      break;
    case _FeaturedEventType.championsLeague:
      eventNote =
          'Continental rhythm favors patient buildup, especially once the first high press is broken.';
      break;
    case _FeaturedEventType.league:
      eventNote =
          'League nights reward repeatable shape more than chaos. Keep the back line compact and let the match tilt slowly.';
      break;
    case _FeaturedEventType.fastCup:
      eventNote =
          'Fast Cup windows reward quick restarts and direct transitions. Restart focus should be high all week.';
      break;
  }
  final List<String> notes = <String>[
    '$clubName should open with ${matchPreview.planLabel.toLowerCase()} against ${matchPreview.opponent}.',
    eventNote,
    if (featuredCup != null)
      '${featuredCup.name} is active, so set-piece reps and late-game legs should stay in the weekly split.',
  ];
  return notes.take(3).toList(growable: false);
}

List<String> _buildNotifications({
  required String clubName,
  required bool isAuthenticated,
  required _HomeBannerData featuredBanner,
  required CompetitionSummary? league,
  required DateTime fastCupStart,
  required _HomeMatchPreview matchPreview,
  required List<_HomeReplayEntry> replays,
}) {
  return <String>[
    '${featuredBanner.label} moved to the top of Home for $clubName.',
    if (league != null)
      '${league.name} is ${_competitionStatusLabel(league.status).toLowerCase()} with ${_spotsLabel(league)} still moving.',
    'Fast Cup countdown is live for ${_formatDayTime(fastCupStart)}.',
    '${matchPreview.stageLabel} locks in ${_relativeLabel(matchPreview.kickoff, DateTime.now().toUtc())}.',
    'Matchday stack refreshed with ${replays.first.title}.',
    isAuthenticated
        ? 'Live session is active for club and competition actions.'
        : 'Sign in to turn preview signals into live account alerts.',
  ].take(3).toList(growable: false);
}

CompetitionSummary? _pickCompetition(
  List<CompetitionSummary> competitions,
  CompetitionFormat format,
) {
  final List<CompetitionSummary> matches = competitions
      .where((CompetitionSummary item) => item.format == format)
      .toList(growable: true);
  if (matches.isEmpty) {
    return null;
  }
  matches.sort((CompetitionSummary left, CompetitionSummary right) {
    final int statusCompare = _competitionPriority(
      right.status,
    ).compareTo(_competitionPriority(left.status));
    if (statusCompare != 0) {
      return statusCompare;
    }
    final int fillCompare = right.fillRate.compareTo(left.fillRate);
    if (fillCompare != 0) {
      return fillCompare;
    }
    return right.updatedAt.compareTo(left.updatedAt);
  });
  return matches.first;
}

int _competitionPriority(CompetitionStatus status) {
  switch (status) {
    case CompetitionStatus.openForJoin:
      return 4;
    case CompetitionStatus.inProgress:
      return 3;
    case CompetitionStatus.filled:
      return 2;
    case CompetitionStatus.published:
      return 1;
    case CompetitionStatus.locked:
    case CompetitionStatus.completed:
    case CompetitionStatus.draft:
    case CompetitionStatus.cancelled:
    case CompetitionStatus.refunded:
    case CompetitionStatus.disputed:
      return 0;
  }
}

TrophyItemDto? _latestHonor(
  List<TrophyItemDto>? honors,
  bool Function(TrophyItemDto item) predicate,
) {
  if (honors == null) {
    return null;
  }
  final List<TrophyItemDto> matches = honors
      .where(predicate)
      .toList(growable: true);
  if (matches.isEmpty) {
    return null;
  }
  matches.sort(
    (TrophyItemDto left, TrophyItemDto right) =>
        right.earnedAt.compareTo(left.earnedAt),
  );
  return matches.first;
}

int _countHonors(
  List<TrophyItemDto>? honors,
  bool Function(TrophyItemDto item) predicate,
) {
  if (honors == null) {
    return 0;
  }
  return honors.where(predicate).length;
}

String? _firstReason(List<String>? reasons, String needle) {
  if (reasons == null) {
    return null;
  }
  for (final String reason in reasons) {
    if (reason.toLowerCase().contains(needle.toLowerCase())) {
      return reason;
    }
  }
  return reasons.isEmpty ? null : reasons.first;
}

DateTime _nextKickoff(DateTime now, int seed) {
  final DateTime sameDay = DateTime.utc(
    now.year,
    now.month,
    now.day,
    18 + (seed % 4),
    30,
  );
  if (sameDay.isAfter(now)) {
    return sameDay;
  }
  return sameDay.add(Duration(days: 1 + (seed % 2)));
}

DateTime _nextFastCupWindow(DateTime now) {
  final DateTime seed = DateTime.utc(now.year, now.month, now.day, 20);
  int daysUntilFriday = DateTime.friday - seed.weekday;
  if (daysUntilFriday < 0) {
    daysUntilFriday += 7;
  }
  DateTime next = seed.add(Duration(days: daysUntilFriday));
  if (!next.isAfter(now)) {
    next = next.add(const Duration(days: 7));
  }
  return next;
}

String _tacticPlanLabel(DynastyEraType? era) {
  if (era == null) {
    return 'Keep the structure tidy';
  }
  switch (era) {
    case DynastyEraType.globalDynasty:
      return 'Control tempo late';
    case DynastyEraType.continentalDynasty:
      return 'Attack the half-spaces';
    case DynastyEraType.dominantEra:
      return 'Press high early';
    case DynastyEraType.emergingPower:
      return 'Break fast in transition';
    case DynastyEraType.fallenGiant:
      return 'Stay compact and selective';
    case DynastyEraType.none:
      return 'Keep the structure tidy';
  }
}

String _relativeLabel(DateTime target, DateTime now) {
  final Duration difference = target.difference(now);
  if (difference.inHours < 1) {
    return 'within the hour';
  }
  if (difference.inHours < 24) {
    return 'in ${difference.inHours}h';
  }
  return 'in ${difference.inDays}d';
}

String _formatCountdown(Duration difference) {
  final Duration safe = difference.isNegative ? Duration.zero : difference;
  final int days = safe.inDays;
  final int hours = safe.inHours.remainder(24);
  final int minutes = safe.inMinutes.remainder(60);
  if (days > 0) {
    return '${days}d ${hours}h';
  }
  if (hours > 0) {
    return '${hours}h ${minutes}m';
  }
  return '${minutes}m';
}

String _formatDateLabel(DateTime value) {
  const List<String> months = <String>[
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  final DateTime utc = value.toUtc();
  return '${months[utc.month - 1]} ${utc.day}';
}

String _formatDayTime(DateTime value) {
  const List<String> weekdays = <String>[
    'Mon',
    'Tue',
    'Wed',
    'Thu',
    'Fri',
    'Sat',
    'Sun',
  ];
  final DateTime utc = value.toUtc();
  final String hour = utc.hour.toString().padLeft(2, '0');
  final String minute = utc.minute.toString().padLeft(2, '0');
  return '${weekdays[utc.weekday - 1]} $hour:$minute UTC';
}

String _ordinal(int value) {
  if (value % 100 >= 11 && value % 100 <= 13) {
    return '${value}th';
  }
  switch (value % 10) {
    case 1:
      return '${value}st';
    case 2:
      return '${value}nd';
    case 3:
      return '${value}rd';
    default:
      return '${value}th';
  }
}

String _formatCompetitionAmount(double value, String currency) {
  if (currency.toLowerCase() == 'credit') {
    return gteFormatCredits(value);
  }
  if (currency.toLowerCase() == 'coin') {
    return gteFormatFanCoins(value);
  }
  final bool whole = value == value.roundToDouble();
  final String amount = value.toStringAsFixed(whole ? 0 : 2);
  return '$amount ${currency.toUpperCase()}';
}

String _competitionStatusLabel(CompetitionStatus status) {
  return status.name
      .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (Match match) {
        return '${match.group(1)} ${match.group(2)}';
      })
      .replaceAll('_', ' ');
}

String _spotsLabel(CompetitionSummary competition) {
  final int remaining = competition.capacity - competition.participantCount;
  if (remaining <= 0) {
    return 'Full';
  }
  return '$remaining left';
}

class _HomeExpansionLanesPanel extends StatelessWidget {
  const _HomeExpansionLanesPanel({
    required this.isAdmin,
    required this.onOpenStreamerTournaments,
    required this.onOpenNationsCup,
    required this.onOpenWorld,
    required this.onOpenTransferCenter,
    required this.onOpenPlayerCards,
    required this.onOpenCreatorShareMarket,
    required this.onOpenClubSaleMarket,
    required this.onOpenCreatorStadium,
    required this.onOpenBroadcastDesk,
    required this.onOpenGtexJackpot,
    required this.onOpenClubAiAssistant,
    required this.onOpenFinanceAdmin,
    required this.onOpenGiftStabilizer,
  });

  final bool isAdmin;
  final VoidCallback onOpenStreamerTournaments;
  final VoidCallback onOpenNationsCup;
  final VoidCallback onOpenWorld;
  final VoidCallback onOpenTransferCenter;
  final VoidCallback onOpenPlayerCards;
  final VoidCallback onOpenCreatorShareMarket;
  final VoidCallback onOpenClubSaleMarket;
  final VoidCallback onOpenCreatorStadium;
  final VoidCallback onOpenBroadcastDesk;
  final VoidCallback onOpenGtexJackpot;
  final VoidCallback onOpenClubAiAssistant;
  final VoidCallback onOpenFinanceAdmin;
  final VoidCallback onOpenGiftStabilizer;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Expansion lanes',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Secondary routes stay reachable from Home without crowding the main shell or touching guarded club flows.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          _HomeRouteGroup(
            title: 'Play',
            actions: <Widget>[
              _HomeRouteButton(
                label: 'Streamer tournaments',
                icon: Icons.live_tv_outlined,
                onPressed: onOpenStreamerTournaments,
              ),
              _HomeRouteButton(
                label: 'Fan predictions (live match only)',
                icon: Icons.insights_outlined,
                onPressed: null,
              ),
              _HomeRouteButton(
                label: 'Nations cup',
                icon: Icons.flag_outlined,
                onPressed: onOpenNationsCup,
              ),
              _HomeRouteButton(
                label: 'World simulation',
                icon: Icons.public_outlined,
                onPressed: onOpenWorld,
              ),
              _HomeRouteButton(
                label: 'Transfer center',
                icon: Icons.event_note_outlined,
                onPressed: onOpenTransferCenter,
              ),
              _HomeRouteButton(
                label: 'Broadcast desk',
                icon: Icons.podcasts_outlined,
                onPressed: onOpenBroadcastDesk,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Fan predictions unlock from live-match routes after a canonical match id is present.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 14),
          _HomeRouteGroup(
            title: 'Market',
            actions: <Widget>[
              _HomeRouteButton(
                label: 'Player cards',
                icon: Icons.style_outlined,
                onPressed: onOpenPlayerCards,
              ),
              _HomeRouteButton(
                label: 'Creator shares',
                icon: Icons.candlestick_chart_outlined,
                onPressed: onOpenCreatorShareMarket,
              ),
              _HomeRouteButton(
                label: 'Club sale market',
                icon: Icons.storefront_outlined,
                onPressed: onOpenClubSaleMarket,
              ),
              _HomeRouteButton(
                label: 'GTEX jackpot',
                icon: Icons.celebration_outlined,
                onPressed: onOpenGtexJackpot,
              ),
            ],
          ),
          const SizedBox(height: 14),
          _HomeRouteGroup(
            title: 'Club / Creator',
            actions: <Widget>[
              _HomeRouteButton(
                label: 'Club AI assistant',
                icon: Icons.smart_toy_outlined,
                onPressed: onOpenClubAiAssistant,
              ),
              _HomeRouteButton(
                label: 'Creator stadium',
                icon: Icons.stadium_outlined,
                onPressed: onOpenCreatorStadium,
              ),
            ],
          ),
          if (isAdmin) ...<Widget>[
            const SizedBox(height: 14),
            _HomeRouteGroup(
              title: 'Admin',
              actions: <Widget>[
                _HomeRouteButton(
                  label: 'League finance',
                  icon: Icons.account_balance_outlined,
                  onPressed: onOpenFinanceAdmin,
                ),
                _HomeRouteButton(
                  label: 'Gift stabilizer',
                  icon: Icons.tune_outlined,
                  onPressed: onOpenGiftStabilizer,
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _HomeRouteGroup extends StatelessWidget {
  const _HomeRouteGroup({required this.title, required this.actions});

  final String title;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 10),
        Wrap(spacing: 12, runSpacing: 12, children: actions),
      ],
    );
  }
}

class _HomeRouteButton extends StatelessWidget {
  const _HomeRouteButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton.tonalIcon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }
}

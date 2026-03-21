import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/clubs/club_profile_screen.dart';
import 'package:gte_frontend/screens/clubs/club_trophy_cabinet_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_discovery_screen.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import 'widgets/home_featured_event_banner.dart';
import 'widgets/home_section_card.dart';

class HomeDashboardScreen extends StatefulWidget {
  const HomeDashboardScreen({
    super.key,
    required this.exchangeController,
    required this.apiBaseUrl,
    required this.backendMode,
    this.onOpenLogin,
    this.clubId,
    this.clubName,
    this.onOpenClubTab,
    this.onOpenCompetitionsTab,
    this.onOpenClubSubtab,
  });

  final GteExchangeController exchangeController;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final VoidCallback? onOpenLogin;
  final String? clubId;
  final String? clubName;
  final VoidCallback? onOpenClubTab;
  final VoidCallback? onOpenCompetitionsTab;
  final ValueChanged<ClubNavigationTab>? onOpenClubSubtab;

  @override
  State<HomeDashboardScreen> createState() => _HomeDashboardScreenState();
}

class _HomeDashboardScreenState extends State<HomeDashboardScreen> {
  late ClubController _clubController;
  late CompetitionController _competitionController;
  late String _userId;
  late String? _userName;
  late String _clubId;
  late String _clubName;

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
    _clubController.dispose();
    _competitionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge(
        <Listenable>[
          widget.exchangeController,
          _clubController,
          _competitionController,
        ],
      ),
      builder: (BuildContext context, Widget? child) {
        final ClubDashboardData? clubData = _clubController.data;
        final bool waitingForFirstFrame = clubData == null &&
            _competitionController.competitions.isEmpty &&
            (_clubController.isLoading ||
                _competitionController.isLoadingDiscovery);
        if (waitingForFirstFrame) {
          return const _HomeLoadingView();
        }

        if (clubData == null &&
            _competitionController.competitions.isEmpty &&
            _clubController.errorMessage != null &&
            _competitionController.discoveryError != null) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Home is unavailable',
              message:
                  '${_clubController.errorMessage!} ${_competitionController.discoveryError!}',
              actionLabel: 'Retry',
              onAction: _refresh,
              icon: Icons.home_outlined,
            ),
          );
        }

        final _HomeSnapshot snapshot = _HomeSnapshot.fromSources(
          clubName: _clubName,
          isAuthenticated: widget.exchangeController.isAuthenticated,
          userLabel: _displayUserLabel(),
          clubData: clubData,
          competitions: _competitionController.competitions,
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
                  title: snapshot.heroTitle,
                  subtitle: snapshot.heroSubtitle,
                  isAuthenticated: widget.exchangeController.isAuthenticated,
                  onOpenClub: () => _openTarget(_HomeLinkTarget.club),
                  onOpenCompetitions: () =>
                      _openTarget(_HomeLinkTarget.competitions),
                  onOpenReplays: () => _openTarget(_HomeLinkTarget.replays),
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
                      label: 'Open comps',
                      value: snapshot.openCompetitionCount.toString(),
                    ),
                    GteMetricChip(
                      label: 'Alerts',
                      value: snapshot.notificationCount.toString(),
                      positive: snapshot.notificationCount >= 3,
                    ),
                  ],
                ),
                GteSyncStatusCard(
                  title: 'App-wide premium sync',
                  status: widget.exchangeController.isAuthenticated
                      ? 'Market, play, hub, club, and capital layers are stitched into one premium shell.'
                      : 'Preview mode is live. Sign in to unlock trading, capital execution, and writable club actions.',
                  syncedAt: widget.exchangeController.marketSyncedAt,
                  accent: GteShellTheme.accent,
                  isRefreshing: _clubController.isLoading ||
                      _competitionController.isLoadingDiscovery,
                  onRefresh: _refresh,
                ),
                if (_clubController.errorMessage != null ||
                    _competitionController.discoveryError != null) ...<Widget>[
                  const SizedBox(height: 18),
                  _InlineWarning(
                    message: <String>[
                      if (_clubController.errorMessage != null)
                        _clubController.errorMessage!,
                      if (_competitionController.discoveryError != null)
                        _competitionController.discoveryError!,
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
                    final int columnCount = constraints.maxWidth >= 1220
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
                  onOpenClub: () => _openTarget(_HomeLinkTarget.club),
                  onOpenCompetitions: () =>
                      _openTarget(_HomeLinkTarget.competitions),
                  onOpenReplays: () => _openTarget(_HomeLinkTarget.replays),
                  onOpenLogin: widget.onOpenLogin,
                ),
                const SizedBox(height: 16),
                _HomeJourneyPanel(
                  isAuthenticated: widget.exchangeController.isAuthenticated,
                  clubName: _clubName,
                  notificationCount: snapshot.notificationCount,
                  openCompetitionCount: snapshot.openCompetitionCount,
                  onOpenCompetitions: () =>
                      _openTarget(_HomeLinkTarget.competitions),
                  onOpenClub: () => _openTarget(_HomeLinkTarget.club),
                  onOpenLogin: widget.onOpenLogin,
                ),
                const SizedBox(height: 20),
                _HomeSectionHeading(
                  eyebrow: 'QUIETER SIGNALS',
                  title:
                      'Replays and alerts still matter, just without hijacking the dashboard.',
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
    await Future.wait<void>(
      <Future<void>>[
        _clubController.refresh(),
        _competitionController.loadDiscovery(),
      ],
    );
    _primeTradingSummary();
  }

  void _createControllers() {
    final _HomeIdentity identity = _deriveIdentity();
    _userId = identity.userId;
    _userName = identity.userName;
    _clubId = identity.clubId;
    _clubName = identity.clubName;
    _clubController = ClubController.standard(
      clubId: _clubId,
      clubName: _clubName,
      baseUrl: widget.apiBaseUrl,
      backendMode: widget.backendMode,
    );
    _competitionController = CompetitionController(
      api: CompetitionApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: widget.backendMode,
      ),
      currentUserId: _userId,
      currentUserName: _userName,
    );
    _clubController.ensureLoaded();
    _competitionController.bootstrap();
  }

  void _recreateControllers() {
    final ClubController previousClub = _clubController;
    final CompetitionController previousCompetition = _competitionController;
    _createControllers();
    previousClub.dispose();
    previousCompetition.dispose();
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
      _competitionController.updateCurrentUser(
        userId: _userId,
        userName: _userName,
      );
      _competitionController.loadDiscovery();
    }
    if (next.clubId != _clubId || next.clubName != _clubName) {
      final ClubController previousClub = _clubController;
      _clubId = next.clubId;
      _clubName = next.clubName;
      _clubController = ClubController.standard(
        clubId: _clubId,
        clubName: _clubName,
        baseUrl: widget.apiBaseUrl,
        backendMode: widget.backendMode,
      );
      _clubController.ensureLoaded();
      previousClub.dispose();
      if (mounted) {
        setState(() {});
      }
    }
    _primeTradingSummary();
  }

  void _primeTradingSummary() {
    if (!widget.exchangeController.isAuthenticated ||
        widget.exchangeController.hasLoadedOrders ||
        widget.exchangeController.isLoadingOrders) {
      return;
    }
    widget.exchangeController.loadOrders();
  }

  _HomeIdentity _deriveIdentity() {
    final dynamic session = widget.exchangeController.session;
    final String? displayName = session?.user.displayName?.trim();
    final String username = session?.user.username.trim() ?? '';
    final String sessionUserId = session?.user.id.trim() ?? '';
    final String userId =
        sessionUserId.isNotEmpty ? sessionUserId : 'demo-user';
    final String? userName = displayName?.isNotEmpty == true
        ? displayName
        : username.isNotEmpty
            ? username
            : null;
    final String clubName = widget.clubName?.trim().isNotEmpty == true
        ? widget.clubName!.trim()
        : displayName?.isNotEmpty == true
            ? displayName!
            : username.isNotEmpty
                ? username
                : 'Royal Lagos FC';
    final String clubId = widget.clubId?.trim().isNotEmpty == true
        ? widget.clubId!.trim()
        : _slugifyClub(clubName);
    return _HomeIdentity(
      userId: userId,
      userName: userName,
      clubId: clubId,
      clubName: clubName,
    );
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
    return 'Demo Fan';
  }

  String _slugifyClub(String raw) {
    final String slug = raw
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
    return slug.isEmpty ? 'royal-lagos-fc' : slug;
  }

  Future<void> _openTarget(_HomeLinkTarget target) async {
    if (target == _HomeLinkTarget.club) {
      if (widget.onOpenClubTab != null) {
        widget.onOpenClubTab!();
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => ClubProfileScreen(
            clubId: _clubId,
            clubName: _clubName,
            controller: _clubController,
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
          builder: (BuildContext context) => CompetitionDiscoveryScreen(
            controller: _competitionController,
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
          builder: (BuildContext context) =>
              ClubTrophyCabinetScreen(controller: _clubController),
        ),
      );
      return;
    }
    final _HomeSnapshot snapshot = _HomeSnapshot.fromSources(
      clubName: _clubName,
      isAuthenticated: widget.exchangeController.isAuthenticated,
      userLabel: _displayUserLabel(),
      clubData: _clubController.data,
      competitions: _competitionController.competitions,
    );
    if (target == _HomeLinkTarget.replays) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => _HomeReplayHubScreen(
            clubName: _clubName,
            replays: snapshot.replays,
          ),
        ),
      );
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => _HomeTacticsScreen(
          clubName: _clubName,
          nextMatch: snapshot.nextMatch,
          tacticalNotes: snapshot.tacticalNotes,
        ),
      ),
    );
  }

  Future<void> _ensureClubLoaded() async {
    if (_clubController.hasData) {
      return;
    }
    if (!_clubController.isLoading) {
      await _clubController.load();
      return;
    }
    while (_clubController.isLoading && mounted) {
      await Future<void>.delayed(const Duration(milliseconds: 60));
    }
  }
}

class _HomeHeroPanel extends StatelessWidget {
  const _HomeHeroPanel({
    required this.title,
    required this.subtitle,
    required this.chips,
    required this.isAuthenticated,
    required this.onOpenClub,
    required this.onOpenCompetitions,
    required this.onOpenReplays,
    this.onOpenLogin,
  });

  final String title;
  final String subtitle;
  final List<Widget> chips;
  final bool isAuthenticated;
  final VoidCallback onOpenClub;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenReplays;
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
          Text(title, style: Theme.of(context).textTheme.displaySmall),
          const SizedBox(height: 8),
          Text(subtitle, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: chips,
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton(
                onPressed: onOpenClub,
                child: const Text('Open club'),
              ),
              FilledButton.tonal(
                onPressed: onOpenCompetitions,
                child: const Text('Browse competitions'),
              ),
              FilledButton.tonal(
                onPressed: onOpenReplays,
                child: const Text('Recent replays'),
              ),
              if (!isAuthenticated && onOpenLogin != null)
                OutlinedButton(
                  onPressed: onOpenLogin,
                  child: const Text('Sign in for live alerts'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HomeQuickActionsStrip extends StatelessWidget {
  const _HomeQuickActionsStrip({
    required this.isAuthenticated,
    required this.onOpenClub,
    required this.onOpenCompetitions,
    required this.onOpenReplays,
    this.onOpenLogin,
  });

  final bool isAuthenticated;
  final VoidCallback onOpenClub;
  final VoidCallback onOpenCompetitions;
  final VoidCallback onOpenReplays;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool singleColumn = constraints.maxWidth < 820;
        final List<Widget> cards = <Widget>[
          _HomeActionCard(
            eyebrow: 'CLUB',
            title: 'Shape the identity lane',
            detail:
                'Update club surfaces, trophies, and the institutional story that powers the rest of GTEX.',
            icon: Icons.shield_outlined,
            accent: GteShellTheme.accent,
            actionLabel: 'Open club',
            onTap: onOpenClub,
          ),
          _HomeActionCard(
            eyebrow: 'ARENA',
            title: 'Jump into live match center',
            detail:
                'Browse live now, up next, and replay routes without digging through layers.',
            icon: Icons.stadium_outlined,
            accent: GteShellTheme.accentArena,
            actionLabel: 'Open arena',
            onTap: onOpenCompetitions,
          ),
          _HomeActionCard(
            eyebrow: isAuthenticated ? 'REPLAYS' : 'UNLOCK',
            title: isAuthenticated
                ? 'Return to the storylines'
                : 'Sign in for execution',
            detail: isAuthenticated
                ? 'Recent match stories, turning points, and notifications stay one tap away.'
                : 'Guest mode previews the shell. Sign in to unlock wallet, order rails, and writable club actions.',
            icon: isAuthenticated
                ? Icons.play_circle_outline
                : Icons.lock_open_outlined,
            accent: isAuthenticated
                ? GteShellTheme.accentWarm
                : GteShellTheme.accentCapital,
            actionLabel: isAuthenticated ? 'Open replays' : 'Sign in',
            onTap: isAuthenticated ? onOpenReplays : onOpenLogin,
          ),
        ];
        if (singleColumn) {
          return Column(
            children: cards
                .map((Widget child) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: child,
                    ))
                .toList(growable: false),
          );
        }
        return Row(
          children: cards
              .map(
                (Widget child) => Expanded(
                  child: Padding(
                    padding:
                        EdgeInsets.only(right: child == cards.last ? 0 : 12),
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
    required this.actionLabel,
    this.onTap,
  });

  final String eyebrow;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
  final String actionLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: accent,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(16),
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
          Text(actionLabel,
              style: Theme.of(context)
                  .textTheme
                  .labelLarge
                  ?.copyWith(color: accent)),
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
    final String title = isAuthenticated
        ? 'Next best moves for $clubName'
        : 'Guest mode is polished, but your account is still on the touchline';
    final String message = isAuthenticated
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
                child: Text(isAuthenticated
                    ? 'See open competitions'
                    : 'Preview live match center'),
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
        const SizedBox(height: 8),
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        Text(detail, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}

class _InlineWarning extends StatelessWidget {
  const _InlineWarning({
    required this.message,
  });

  final String message;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Icon(
              Icons.info_outline,
              color: GteShellTheme.accentWarm,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
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
  const _HomeReplayHubScreen({
    required this.clubName,
    required this.replays,
  });

  final String clubName;
  final List<_HomeReplayEntry> replays;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Recent replays'),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '$clubName replay deck',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Replay cards follow the same club story Home is surfacing: recent honors, reputation spikes, and the moments worth replaying again.',
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
                        ...replay.highlights.take(3).map(
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
  const _ReplayMetaChip({
    required this.label,
    required this.value,
  });

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
        appBar: AppBar(
          title: const Text('Tactics'),
        ),
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

enum _HomeLinkTarget {
  competitions,
  replays,
  club,
  trophies,
  tactics,
}

enum _FeaturedEventType {
  worldSuperCup,
  championsLeague,
  league,
  fastCup,
}

class _HomeIdentity {
  const _HomeIdentity({
    required this.userId,
    required this.userName,
    required this.clubId,
    required this.clubName,
  });

  final String userId;
  final String? userName;
  final String clubId;
  final String clubName;
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
    final CompetitionSummary? featuredLeague =
        _pickCompetition(competitions, CompetitionFormat.league);
    final CompetitionSummary? featuredCup =
        _pickCompetition(competitions, CompetitionFormat.cup);
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
    final int openCompetitionCount = competitions
        .where(
          (CompetitionSummary item) =>
              item.status == CompetitionStatus.openForJoin,
        )
        .length;
    final String prestigeLabel =
        clubData?.reputation.profile.currentPrestigeTier.label ?? 'Preview';
    return _HomeSnapshot(
      heroTitle: isAuthenticated
          ? '$userLabel, the exchange is moving.'
          : 'Home is ready for $resolvedClubName.',
      heroSubtitle:
          'Next match, cups, replays, and club momentum are stitched into one home surface so the app feels active before you drill down.',
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
              'Kickoff', _formatDayTime(matchPreview.kickoff)),
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
        summary: latestSeason?.leagueFinish != null
            ? '$resolvedClubName closed ${latestSeason!.seasonLabel} in ${_ordinal(latestSeason.leagueFinish!)} place.'
            : 'League traction is building and the table is moving again.',
        detail: featuredLeague == null
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
        title: championsLeague != null
            ? 'Continental crown still visible'
            : latestSeason?.topFourFinish == true
                ? 'Qualification line protected'
                : 'Continental push is live',
        summary: championsLeague != null
            ? championsLeague.finalResultSummary
            : latestSeason?.championsLeagueTitle == true
                ? 'Champions League silverware pushed the club into the elite conversation.'
                : latestSeason?.topFourFinish == true
                    ? 'League placement kept Champions League access alive for the next run.'
                    : 'The next continental step still runs through league control and trophy nights.',
        detail: _firstReason(
              dynasty?.reasons,
              'Champions League',
            ) ??
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
            'Top-four league work preserved the next Champions League lane.',
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
        detail: featuredCup == null
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
        eyebrow: 'Recent Replay',
        title: replays.first.title,
        summary: replays.first.summary,
        detail: replays.first.caption,
        icon: Icons.ondemand_video_outlined,
        accent: GteShellTheme.accent,
        stats: <MapEntry<String, String>>[
          MapEntry<String, String>(
              'When', _formatDateLabel(replays.first.occurredAt)),
          MapEntry<String, String>('Track', replays.first.trackLabel),
          MapEntry<String, String>('Focus', replays.first.focusLabel),
        ],
        highlights: replays.first.highlights,
        actionLabel: 'Open replays',
        target: _HomeLinkTarget.replays,
      ),
      notificationsSummary: _HomeCardData(
        eyebrow: 'Notifications Summary',
        title: '${notifications.length} fresh signals',
        summary:
            'Club, competition, and replay updates are grouped into one Home queue so the next decision is immediate.',
        detail: isAuthenticated
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
      summary: worldSuperCup?.finalResultSummary ??
          'The latest cycle kept the club in the rarest global conversation.',
      body: worldSuperCup != null
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
      summary: championsLeague?.finalResultSummary ??
          'Continental silverware is the strongest active story behind the club right now.',
      body: _firstReason(dynasty?.reasons, 'Champions League') ??
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
      summary: leagueHonor?.finalResultSummary ??
          (latestSeason?.leagueFinish != null
              ? 'Latest domestic finish landed at ${_ordinal(latestSeason!.leagueFinish!)}.'
              : 'The next league window is the strongest active route on the board.'),
      body: featuredLeague == null
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
    summary: fastCupHonor?.finalResultSummary ??
        'No world, continental, or league headline is stronger right now, so the Fast Cup window moves to the top.',
    body: featuredCup == null
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
  final int seed =
      clubName.runes.fold<int>(0, (int sum, int rune) => sum + rune);
  final DateTime kickoff = _nextKickoff(now, seed);
  final String planLabel = _tacticPlanLabel(dynasty?.currentEraLabel);
  final int matchday = 24 + (seed % 8);
  return _HomeMatchPreview(
    opponent: opponents[seed % opponents.length],
    stageLabel: league == null
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
    for (final TrophyItemDto honor
        in clubData.trophyCabinet.recentHonors.take(3)) {
      entries.add(
        _HomeReplayEntry(
          title: '${honor.trophyName} replay',
          summary: honor.finalResultSummary,
          caption: '${honor.seasonLabel} • ${honor.competitionRegion}',
          trackLabel: honor.isWorldSuperCup
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
    for (final ReputationEventDto event
        in clubData.reputation.recentEvents.take(2)) {
      entries.add(
        _HomeReplayEntry(
          title: '${event.title} replay',
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
        title: '$resolvedClubName replay hub',
        summary:
            'Home will pin the strongest replay card here once the next club moment lands.',
        caption: 'Club pulse',
        trackLabel: 'Home',
        focusLabel: 'Preview',
        occurredAt: DateTime.now().toUtc(),
        highlights: const <String>[
          'Replay cards are ready for trophies, league swings, and prestige spikes.',
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
    'Replay stack refreshed with ${replays.first.title}.',
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
    final int statusCompare = _competitionPriority(right.status)
        .compareTo(_competitionPriority(left.status));
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
  final List<TrophyItemDto> matches =
      honors.where(predicate).toList(growable: true);
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
  return status.name.replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (Match match) {
    return '${match.group(1)} ${match.group(2)}';
  }).replaceAll('_', ' ');
}

String _spotsLabel(CompetitionSummary competition) {
  final int remaining = competition.capacity - competition.participantCount;
  if (remaining <= 0) {
    return 'Full';
  }
  return '$remaining left';
}

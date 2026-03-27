import 'dart:async';

import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../core/debouncer.dart';
import '../data/agent_marketplace_api.dart';
import '../data/agent_marketplace_models.dart';
import '../data/gte_exchange_models.dart';
import '../data/player_match_service.dart';
import '../domain/match/match_weight_presets.dart';
import '../domain/match/match_weights.dart';
import '../features/app_routes/gte_navigation_helpers.dart';
import '../features/app_routes/gte_route_data.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
import '../screens/agent_conversation_screen.dart';
import '../screens/agent_conversations_screen.dart';
import '../screens/notifications/gte_notifications_screen.dart';
import '../services/avatar_mapper.dart';
import '../widgets/agent_conversation_compose_sheet.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/market/match_weights_sheet.dart';
import '../widgets/market/player_market_avatar.dart';

const Color _canvas = Color(0xFFF4F0E8);
const Color _surface = Color(0xFFFFFCF8);
const Color _surfaceSoft = Color(0xFFF1EBE2);
const Color _line = Color(0xFFE5DBCE);
const Color _lineStrong = Color(0xFFD8C9B9);
const Color _text = Color(0xFF211C16);
const Color _muted = Color(0xFF7B7469);
const Color _accent = Color(0xFFB96B2C);
const Color _accentSoft = Color(0xFFF2E2D1);
const Color _positive = Color(0xFF227A5B);
const Color _negative = Color(0xFFBA5445);
const Color _neutral = Color(0xFF5C6470);
const double _marketLoadMoreThreshold = 320;
const int _minSelectableAge = 18;
const int _maxSelectableAge = 40;
const String _freeAgentAvailability = 'free_agent';

class GteMarketPlayersScreen extends StatefulWidget {
  const GteMarketPlayersScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.navigationDependencies,
    this.matchService,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GteNavigationDependencies? navigationDependencies;
  final GtePlayerMatchService? matchService;

  @override
  State<GteMarketPlayersScreen> createState() => _GteMarketPlayersScreenState();
}

class _GteMarketPlayersScreenState extends State<GteMarketPlayersScreen> {
  late final ScrollController _scrollController;
  late final TextEditingController _searchController;
  late final Debouncer _searchDebouncer;
  late GtePlayerMatchService _matchService;
  GteScoutMatchFilters _matchFilters =
      const GteScoutMatchFilters.defaultBrief();
  List<GtePlayerMatchResult> _matches = const <GtePlayerMatchResult>[];
  bool _isLoadingMatches = false;
  bool _isSyncingSearchController = false;
  String? _matchError;
  String _lastMatchSeed = '';

  @override
  void initState() {
    super.initState();
    _matchService = widget.matchService ??
        GtePlayerMatchService(api: widget.controller.api);
    _scrollController = ScrollController()..addListener(_handleScroll);
    _searchDebouncer = Debouncer(milliseconds: 400);
    _searchController =
        TextEditingController(text: widget.controller.marketSearch);
    _searchController.addListener(_handleSearchChanged);
    widget.controller.addListener(_handleMarketStateChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _maybeLoadMore();
      _refreshMatchesIfNeeded(force: true);
    });
  }

  @override
  void didUpdateWidget(covariant GteMarketPlayersScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller == widget.controller) {
      return;
    }
    oldWidget.controller.removeListener(_handleMarketStateChanged);
    widget.controller.addListener(_handleMarketStateChanged);
    _matchService = widget.matchService ??
        GtePlayerMatchService(api: widget.controller.api);
    _lastMatchSeed = '';
    final String nextSearch = widget.controller.marketSearch;
    _syncSearchControllerText(nextSearch);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _maybeLoadMore();
      _refreshMatchesIfNeeded(force: true);
    });
  }

  @override
  void dispose() {
    widget.controller.removeListener(_handleMarketStateChanged);
    _scrollController.removeListener(_handleScroll);
    _scrollController.dispose();
    _searchController.removeListener(_handleSearchChanged);
    _searchDebouncer.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final List<GteMarketPlayerListItem> players = widget.controller.players;
        final bool isLoadingInitial = widget.controller.isLoadingMarket &&
            widget.controller.players.isEmpty;
        return Material(
          color: _canvas,
          child: RefreshIndicator(
            color: _accent,
            backgroundColor: Colors.white,
            onRefresh: _refresh,
            child: SingleChildScrollView(
              key: const ValueKey<String>('discover-player-scroll'),
              controller: _scrollController,
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      _buildHeader(context),
                      const SizedBox(height: 18),
                      _buildSearchBar(),
                      const SizedBox(height: 14),
                      _buildFilterRow(),
                      const SizedBox(height: 18),
                      _buildTopMatchesSection(),
                      const SizedBox(height: 20),
                      _buildSectionHeader(players.length),
                      const SizedBox(height: 16),
                      if (!widget.controller.isAuthenticated) ...<Widget>[
                        _buildGuestBanner(),
                        const SizedBox(height: 16),
                      ],
                      if (isLoadingInitial)
                        _buildSkeletonGrid()
                      else if (widget.controller.marketError != null &&
                          widget.controller.players.isEmpty)
                        _buildStateCard(
                          icon: Icons.warning_amber_rounded,
                          title: 'Player discovery unavailable',
                          message:
                              'The latest scout board could not be loaded. ${widget.controller.marketError!}',
                          actionLabel: 'Retry',
                          onAction: _refresh,
                        )
                      else if (players.isEmpty)
                        _buildStateCard(
                          icon: Icons.search_off_rounded,
                          title: 'No players match your criteria',
                          message: _emptyStateMessage,
                          actionLabel:
                              _hasActiveFilters ? 'Clear filters' : 'Refresh',
                          onAction:
                              _hasActiveFilters ? _showAllPlayers : _refresh,
                        )
                      else
                        GridView.builder(
                          key: const ValueKey<String>('discover-player-grid'),
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: players.length,
                          gridDelegate:
                              const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            crossAxisSpacing: 14,
                            mainAxisSpacing: 14,
                            mainAxisExtent: 430,
                          ),
                          itemBuilder: (BuildContext context, int index) =>
                              _buildPlayerCard(players[index]),
                        ),
                      if (widget.controller.marketError != null &&
                          widget.controller.players.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 16),
                        _buildNotice(
                          'Showing the latest confirmed discovery board. ${widget.controller.marketError!}',
                        ),
                      ] else if (widget
                          .controller.isLoadingMoreMarket) ...<Widget>[
                        const SizedBox(height: 18),
                        _buildBottomLoader(),
                      ] else if (!widget.controller.hasMorePlayers &&
                          widget.controller.players.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 18),
                        _buildMarketEndState(),
                      ],
                      if (widget.navigationDependencies != null) ...<Widget>[
                        const SizedBox(height: 24),
                        _MarketRoutePanel(
                          onOpenPlayerCards: () => _openFeatureRoute(
                            const PlayerCardsBrowseRouteData(),
                          ),
                          onOpenCreatorShareMarket:
                              _openCreatorShareMarketRoute,
                          onOpenClubSaleMarket: () => _openFeatureRoute(
                            const ClubSaleMarketListingsRouteData(),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  PlayerFilter get _draftMarketFilter => widget.controller.marketFilter
      .copyWith(search: _normalizeFilterValue(_searchController.text))
      .normalized();

  bool get _hasPendingSearch =>
      _normalizeFilterValue(_searchController.text) !=
      widget.controller.marketFilter.search;

  bool get _hasActiveFilters => _draftMarketFilter.hasActiveFilters;

  String get _emptyStateMessage {
    if (_hasPendingSearch || _hasActiveFilters) {
      return 'Try adjusting your search or clearing the active filters.';
    }
    return 'Pull to refresh and try again.';
  }

  List<String> get _positionOptions => _mergeOptions(
        values: widget.controller.players.map(
          (GteMarketPlayerListItem player) => player.position,
        ),
        seed: const <String>[
          'GK',
          'CB',
          'LB',
          'RB',
          'DM',
          'CM',
          'AM',
          'LW',
          'RW',
          'ST',
        ],
        selectedValue: _draftMarketFilter.position,
      );

  List<String> get _countryOptions => _mergeOptions(
        values: widget.controller.players.map(
          (GteMarketPlayerListItem player) => player.nationality,
        ),
        selectedValue: _draftMarketFilter.country,
      );

  Widget _buildHeader(BuildContext context) {
    final String rawName =
        widget.controller.session?.user.displayName?.trim().isNotEmpty == true
            ? widget.controller.session!.user.displayName!.trim()
            : widget.controller.session?.user.username.trim() ?? 'Guest';
    final List<String> parts = rawName
        .split(RegExp(r'\s+'))
        .where((String part) => part.isNotEmpty)
        .toList(growable: false);
    final String initials = parts.isEmpty
        ? 'G'
        : parts.length == 1
            ? parts.first.substring(0, 1).toUpperCase()
            : '${parts.first.substring(0, 1)}${parts.last.substring(0, 1)}'
                .toUpperCase();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              GestureDetector(
                onTap: widget.controller.isAuthenticated
                    ? null
                    : widget.onOpenLogin,
                child: CircleAvatar(
                  radius: 24,
                  backgroundColor: _accentSoft,
                  foregroundColor: _text,
                  child: Text(initials),
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  IconButton(
                    tooltip: 'Conversations',
                    onPressed: _openConversationInbox,
                    icon: const Icon(
                      Icons.forum_outlined,
                      color: _text,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Notifications',
                    onPressed: _openNotifications,
                    icon: const Icon(
                      Icons.notifications_none_rounded,
                      color: _text,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'Welcome back,',
            style: TextStyle(
              color: _muted,
              fontSize: 15,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Scout Talent',
            style: TextStyle(
              color: _text,
              fontSize: 28,
              fontWeight: FontWeight.w800,
              height: 1.0,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            widget.controller.marketSyncedAt == null
                ? 'Search the latest player board, compare clubs, and move into profiles fast.'
                : 'Updated ${gteFormatRelativeTime(widget.controller.marketSyncedAt)}',
            style: const TextStyle(color: _muted),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return TextField(
      controller: _searchController,
      textInputAction: TextInputAction.search,
      onSubmitted: (_) => _refresh(),
      decoration: InputDecoration(
        hintText: 'Search players, clubs...',
        filled: true,
        fillColor: _surface,
        prefixIcon: const Icon(Icons.search, color: _muted),
        suffixIconConstraints: const BoxConstraints(minWidth: 96),
        suffixIcon: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            if (_searchController.text.trim().isNotEmpty)
              IconButton(
                tooltip: 'Clear search',
                onPressed: _clearSearch,
                icon: const Icon(Icons.close_rounded),
              ),
            IconButton(
              tooltip: 'Filters',
              onPressed: _openFilterMenu,
              icon: const Icon(Icons.tune_rounded),
            ),
          ],
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: _line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: _accent, width: 1.3),
        ),
      ),
    );
  }

  Widget _buildFilterRow() {
    final PlayerFilter filter = _draftMarketFilter;
    return SizedBox(
      height: 42,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: <Widget>[
          _FilterChipButton(
            label: filter.position == null
                ? 'Position'
                : 'Position: ${filter.position}',
            active: filter.position != null,
            onTap: _pickPositionFilter,
          ),
          _FilterChipButton(
            label: filter.minAge == null && filter.maxAge == null
                ? 'Age'
                : 'Age: ${_ageLabel(filter)}',
            active: filter.minAge != null || filter.maxAge != null,
            onTap: _pickAgeFilter,
          ),
          _FilterChipButton(
            label: filter.country == null
                ? 'Country'
                : 'Country: ${filter.country}',
            active: filter.country != null,
            onTap: _pickCountryFilter,
          ),
          _FilterChipButton(
            label: filter.availability == null
                ? 'Availability'
                : 'Availability: ${_availabilityLabel(filter.availability)}',
            active: filter.availability != null,
            onTap: _pickAvailabilityFilter,
          ),
        ],
      ),
    );
  }

  Widget _buildTopMatchesSection() {
    final bool isWaitingForMarket =
        widget.controller.players.isEmpty && widget.controller.isLoadingMarket;
    final MatchWeightPreset? activePreset =
        MatchWeightPresets.resolve(widget.controller.weights);
    return Container(
      key: const ValueKey<String>('top-matches-section'),
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'Top Matches',
            style: TextStyle(
              color: _text,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Ranked players with explainable scoring against the active scout brief.',
            style: TextStyle(color: _muted),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: _openMatchBriefSheet,
                icon: const Icon(Icons.tune_rounded),
                label: const Text('Scout brief'),
              ),
              FilledButton.tonalIcon(
                onPressed: _openMatchWeightsSheet,
                icon: const Icon(Icons.equalizer_rounded),
                label: const Text('Weights'),
              ),
              _MatchSummaryChip(
                label: '${activePreset?.badgeLabel ?? 'Custom Mix'} Mode',
                color: _accent,
                backgroundColor: _accentSoft,
              ),
            ],
          ),
          const SizedBox(height: 14),
          _buildMatchSummaryBar(),
          const SizedBox(height: 16),
          if (_matchError != null && _matches.isEmpty)
            _buildStateCard(
              icon: Icons.auto_fix_high_rounded,
              title: 'Match engine unavailable',
              message:
                  'The local ranking pass could not be completed. $_matchError',
              actionLabel: 'Retry',
              onAction: () => _refreshMatchesIfNeeded(force: true),
            )
          else if (_isLoadingMatches || isWaitingForMarket)
            _buildMatchSkeletonList()
          else if (_matches.isEmpty)
            _buildStateCard(
              icon: Icons.manage_search_rounded,
              title: 'No ranked fits yet',
              message:
                  'Adjust the scout brief or refresh the market to generate ranked matches.',
              actionLabel: 'Refresh matches',
              onAction: () => _refreshMatchesIfNeeded(force: true),
            )
          else
            Column(
              children: _matches
                  .take(3)
                  .map(
                    (GtePlayerMatchResult match) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _buildMatchCard(match),
                    ),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }

  Widget _buildMatchSummaryBar() {
    final List<String> labels = _matchFilters.summaryLabels();
    final MatchWeightPreset? activePreset =
        MatchWeightPresets.resolve(widget.controller.weights);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _accentSoft,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          const _MatchSummaryChip(
            label: 'Scout brief',
            color: _text,
            backgroundColor: Colors.white,
          ),
          _MatchSummaryChip(
            label: activePreset?.badgeLabel ?? 'Custom Mix',
            color: _accent,
            backgroundColor: Colors.white.withValues(alpha: 0.9),
          ),
          ...labels.map(
            (String label) => _MatchSummaryChip(
              label: label,
              color: _accent,
              backgroundColor: Colors.white.withValues(alpha: 0.9),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(int visibleCount) {
    final String subtitle = _hasActiveFilters
        ? '$visibleCount players match the active filters'
        : '$visibleCount players visible on the current scout board';
    return Row(
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'Discover Players',
                style: TextStyle(
                  color: _text,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: const TextStyle(color: _muted),
              ),
            ],
          ),
        ),
        if (_hasActiveFilters) ...<Widget>[
          const SizedBox(width: 12),
          TextButton(
            onPressed: _showAllPlayers,
            child: const Text('Clear'),
          ),
        ],
      ],
    );
  }

  Widget _buildGuestBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _line),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.login_rounded, color: _accent),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'Guests can scout the market. Sign in to unlock trading, orders, and wallet-aware flows.',
              style: TextStyle(color: _muted),
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.tonal(
            onPressed: widget.onOpenLogin,
            child: const Text('Sign in'),
          ),
        ],
      ),
    );
  }

  Widget _buildNotice(String message) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _line),
      ),
      child: Text(message, style: const TextStyle(color: _muted)),
    );
  }

  Widget _buildStateCard({
    required IconData icon,
    required String title,
    required String message,
    bool isLoading = false,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: _accent, size: 28),
          const SizedBox(height: 14),
          Text(
            title,
            style: const TextStyle(
              color: _text,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(message, style: const TextStyle(color: _muted)),
          if (isLoading) ...<Widget>[
            const SizedBox(height: 16),
            const LinearProgressIndicator(color: _accent),
          ] else if (actionLabel != null && onAction != null) ...<Widget>[
            const SizedBox(height: 16),
            FilledButton.tonal(onPressed: onAction, child: Text(actionLabel)),
          ],
        ],
      ),
    );
  }

  Widget _buildSkeletonGrid() {
    return GridView.builder(
      key: const ValueKey<String>('discover-player-grid-skeleton'),
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: 6,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 14,
        mainAxisSpacing: 14,
        mainAxisExtent: 380,
      ),
      itemBuilder: (BuildContext context, int index) => _buildSkeletonCard(),
    );
  }

  Widget _buildSkeletonCard() {
    return Container(
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            height: 112,
            decoration: BoxDecoration(
              color: _accentSoft,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(24),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _skeletonLine(width: 120, height: 18),
                const SizedBox(height: 8),
                _skeletonLine(width: 88),
                const SizedBox(height: 12),
                Row(
                  children: <Widget>[
                    Expanded(child: _skeletonTile()),
                    const SizedBox(width: 8),
                    Expanded(child: _skeletonTile()),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  height: 44,
                  decoration: BoxDecoration(
                    color: _surfaceSoft,
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMatchSkeletonList() {
    return Column(
      children: List<Widget>.generate(
        3,
        (int index) => Padding(
          padding: EdgeInsets.only(bottom: index == 2 ? 0 : 12),
          child: Container(
            height: 208,
            decoration: BoxDecoration(
              color: _surfaceSoft,
              borderRadius: BorderRadius.circular(22),
            ),
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.8),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          _skeletonLine(width: 132, height: 16),
                          const SizedBox(height: 8),
                          _skeletonLine(width: 84),
                        ],
                      ),
                    ),
                    _skeletonLine(width: 56, height: 34),
                  ],
                ),
                const SizedBox(height: 16),
                _skeletonLine(width: 180),
                const SizedBox(height: 10),
                _skeletonLine(width: 148),
                const SizedBox(height: 18),
                Row(
                  children: <Widget>[
                    Expanded(child: _skeletonTile()),
                    const SizedBox(width: 8),
                    Expanded(child: _skeletonTile()),
                    const SizedBox(width: 8),
                    Expanded(child: _skeletonTile()),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMatchCard(GtePlayerMatchResult match) {
    final avatar = AvatarMapper.fromMarketListItem(match.player);
    final Color scoreColor = _matchScoreColor(match.score);
    final String club = match.player.currentClubName ?? 'Open market profile';
    final List<String> fitTags = <String>[
      if (match.preferredFoot != null) '${match.preferredFoot} foot',
      if (match.heightMeters != null)
        '${match.heightMeters!.toStringAsFixed(2)}m',
      if (match.isFreeAgent) 'Free agent',
    ];

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: _line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              PlayerMarketAvatar(avatar: avatar, size: 56),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      match.player.playerName,
                      style: const TextStyle(
                        color: _text,
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${match.player.position ?? 'Player'}  •  ${match.player.nationality ?? 'Global'}  •  ${match.player.age}',
                      style: const TextStyle(color: _muted),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              _MatchScoreBadge(score: match.score, color: scoreColor),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'Why this fits',
            style: TextStyle(
              color: _text,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          ...match.reasons.take(4).map(
                (String reason) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Icon(
                        Icons.check_circle_rounded,
                        size: 18,
                        color: scoreColor,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          reason,
                          style: const TextStyle(color: _muted),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _smallBadge(club, color: _neutral),
              ...fitTags.map(
                (String tag) => _smallBadge(tag, color: scoreColor),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => widget.onOpenPlayer(match.player.playerId),
              style: FilledButton.styleFrom(
                backgroundColor: _text,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text('View Profile'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlayerCard(GteMarketPlayerListItem player) {
    final Color movementColor = player.movementPct == null
        ? _neutral
        : player.isRising
            ? _positive
            : _negative;
    final avatar = AvatarMapper.fromMarketListItem(player);
    final String country = player.nationality ?? 'Global';
    final String club = player.currentClubName ?? 'Open market profile';
    final bool canContact =
        player.agentUserId.trim().isNotEmpty && player.isAvailable;
    return Material(
      color: _surface,
      borderRadius: BorderRadius.circular(24),
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: () => widget.onOpenPlayer(player.playerId),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: _line),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                height: 112,
                decoration: BoxDecoration(
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(24),
                  ),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      movementColor.withValues(alpha: 0.14),
                      _accentSoft,
                    ],
                  ),
                ),
                child: Stack(
                  children: <Widget>[
                    Positioned(
                      top: 14,
                      right: 14,
                      child: _smallBadge(player.position ?? 'Player'),
                    ),
                    Positioned(
                      top: 14,
                      left: 14,
                      child: _smallBadge(
                        player.availabilityLabel,
                        color: player.isAvailable ? _positive : _neutral,
                      ),
                    ),
                    Center(
                      child: PlayerMarketAvatar(avatar: avatar, size: 88),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 14, 14, 16),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          player.playerName,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: _text,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${_flagEmoji(country)} $country',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: _muted),
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: <Widget>[
                            _smallBadge(
                              gteAskingTypeLabel(player.askingType),
                              color: _accent,
                            ),
                            _smallBadge(
                              'Agent: ${player.agentName}',
                              color: _neutral,
                            ),
                          ],
                        ),
                        if (player.marketplaceNote != null &&
                            player.marketplaceNote!
                                .trim()
                                .isNotEmpty) ...<Widget>[
                          const SizedBox(height: 10),
                          Text(
                            player.marketplaceNote!,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: _muted, height: 1.3),
                          ),
                        ],
                        const SizedBox(height: 12),
                        Row(
                          children: <Widget>[
                            Expanded(
                              child: _statTile(
                                'Age',
                                '${player.age}',
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: _statTile(
                                'Club',
                                club,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: <Widget>[
                            Expanded(
                              child: FilledButton(
                                onPressed: () =>
                                    widget.onOpenPlayer(player.playerId),
                                style: FilledButton.styleFrom(
                                  backgroundColor: _text,
                                  foregroundColor: Colors.white,
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 12),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                ),
                                child: const Text('View Profile'),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: OutlinedButton(
                                onPressed: canContact
                                    ? () => _contactAgentFromCard(player)
                                    : null,
                                style: OutlinedButton.styleFrom(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 12),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                ),
                                child: const Text('Contact Agent'),
                              ),
                            ),
                          ],
                        ),
                        if (!canContact) ...<Widget>[
                          const SizedBox(height: 8),
                          const Text(
                            'Marketplace messaging opens once a live agent listing is active.',
                            style: TextStyle(color: _muted, fontSize: 12),
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
      ),
    );
  }

  Widget _smallBadge(String label, {Color color = _accent}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w700),
      ),
    );
  }

  Widget _statTile(String label, String value) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: _surfaceSoft,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: const TextStyle(color: _muted, fontSize: 12)),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: _text, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomLoader() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          CircularProgressIndicator(color: _accent),
          SizedBox(height: 10),
          Text(
            'Loading more players',
            style: TextStyle(color: _muted, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildMarketEndState() {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: _surface,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: _line),
        ),
        child: const Text(
          'No more players',
          style: TextStyle(color: _muted, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Widget _skeletonTile() {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: _surfaceSoft,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _skeletonLine(width: 28, height: 10),
          const SizedBox(height: 6),
          _skeletonLine(width: 56),
        ],
      ),
    );
  }

  Widget _skeletonLine({
    required double width,
    double height = 14,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: _surfaceSoft,
        borderRadius: BorderRadius.circular(999),
      ),
    );
  }

  AgentMarketplaceApi _marketplaceApi() {
    return AgentMarketplaceApi(
      config: widget.controller.api.config,
      transport: widget.controller.api.transport,
      accessToken: widget.controller.accessToken,
      mode: widget.controller.api.config.mode,
    );
  }

  Future<void> _openConversationInbox() async {
    if (!widget.controller.isAuthenticated) {
      widget.onOpenLogin();
      return;
    }
    final String? currentUserId = widget.controller.session?.user.id;
    if (currentUserId == null || currentUserId.isEmpty || !mounted) {
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => AgentConversationsScreen(
          api: _marketplaceApi(),
          currentUserId: currentUserId,
        ),
      ),
    );
  }

  Future<void> _contactAgentFromCard(GteMarketPlayerListItem player) async {
    if (!widget.controller.isAuthenticated) {
      widget.onOpenLogin();
      return;
    }
    final String? currentUserId = widget.controller.session?.user.id;
    if (currentUserId == null || currentUserId.isEmpty) {
      return;
    }
    final String? message = await showAgentConversationComposer(
      context,
      playerName: player.playerName,
      askingType: player.askingType,
    );
    if (!mounted || message == null) {
      return;
    }
    try {
      final GteConversationDetail detail = await _marketplaceApi()
          .startConversation(playerId: player.playerId, message: message);
      if (!mounted) {
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => AgentConversationScreen(
            api: _marketplaceApi(),
            currentUserId: currentUserId,
            initialDetail: detail,
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _refresh() {
    return widget.controller
        .loadMarket(
          filter: _draftMarketFilter,
          reset: true,
        )
        .then((_) => _refreshMatchesIfNeeded(force: true));
  }

  void _handleScroll() {
    _maybeLoadMore();
  }

  void _handleMarketStateChanged() {
    if (!mounted) {
      return;
    }
    _syncSearchControllerText(widget.controller.marketSearch);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _maybeLoadMore();
      if (_lastMatchSeed.isEmpty) {
        _refreshMatchesIfNeeded();
      }
    });
  }

  void _maybeLoadMore() {
    if (!mounted ||
        !_scrollController.hasClients ||
        _hasPendingSearch ||
        widget.controller.isLoadingMarket ||
        widget.controller.isLoadingMoreMarket ||
        !widget.controller.hasMorePlayers) {
      return;
    }
    final ScrollPosition position = _scrollController.position;
    if (!position.hasContentDimensions ||
        position.extentAfter > _marketLoadMoreThreshold) {
      return;
    }
    unawaited(
      widget.controller.loadMarket(
        filter: widget.controller.marketFilter,
        reset: false,
      ),
    );
  }

  void _handleSearchChanged() {
    if (!mounted) {
      return;
    }
    setState(() {});
    if (_isSyncingSearchController) {
      return;
    }
    _searchDebouncer.run(() {
      if (!mounted) {
        return;
      }
      unawaited(_applyMarketFilter(_draftMarketFilter));
    });
  }

  void _clearSearch() {
    if (_searchController.text.isEmpty &&
        (widget.controller.marketFilter.search?.isEmpty ?? true)) {
      return;
    }
    _searchController.clear();
    unawaited(_applyMarketFilter(_draftMarketFilter));
  }

  void _showAllPlayers() {
    _syncSearchControllerText('');
    unawaited(_applyMarketFilter(const PlayerFilter()));
  }

  void _refreshMatchesIfNeeded({bool force = false}) {
    final List<GteMarketPlayerListItem> players = widget.controller.players;
    if (players.isEmpty) {
      if (_matches.isNotEmpty || _matchError != null || _isLoadingMatches) {
        setState(() {
          _matches = const <GtePlayerMatchResult>[];
          _matchError = null;
          _isLoadingMatches = false;
        });
      }
      _lastMatchSeed = '';
      return;
    }
    final String seed =
        '${players.map((GteMarketPlayerListItem player) => player.playerId).join('|')}::${_matchFilters.cacheKey}::${widget.controller.weights.cacheKey}';
    if (!force && seed == _lastMatchSeed) {
      return;
    }
    _lastMatchSeed = seed;
    unawaited(_loadMatches(seed));
  }

  Future<void> _loadMatches(String seed) async {
    if (mounted) {
      setState(() {
        _isLoadingMatches = true;
        _matchError = null;
      });
    }
    try {
      final List<GtePlayerMatchResult> matches = await _matchService.getMatches(
        players: widget.controller.players,
        filters: _matchFilters,
        weights: widget.controller.weights,
        limit: 6,
      );
      if (!mounted || seed != _lastMatchSeed) {
        return;
      }
      setState(() {
        _matches = matches;
      });
    } catch (error) {
      if (!mounted || seed != _lastMatchSeed) {
        return;
      }
      setState(() {
        _matchError = error.toString();
      });
    } finally {
      if (mounted && seed == _lastMatchSeed) {
        setState(() {
          _isLoadingMatches = false;
        });
      }
    }
  }

  Future<void> _applyMarketFilter(PlayerFilter filter) async {
    final PlayerFilter normalizedFilter = filter.normalized();
    if (widget.controller.marketPage != null &&
        normalizedFilter == widget.controller.marketFilter) {
      return;
    }
    await widget.controller.loadMarket(
      filter: normalizedFilter,
      reset: true,
    );
    _refreshMatchesIfNeeded(force: true);
  }

  void _syncSearchControllerText(String value) {
    if (_searchController.text == value) {
      return;
    }
    _isSyncingSearchController = true;
    _searchController.value = TextEditingValue(
      text: value,
      selection: TextSelection.collapsed(offset: value.length),
    );
    _isSyncingSearchController = false;
  }

  List<String> _mergeOptions({
    required Iterable<String?> values,
    Iterable<String> seed = const <String>[],
    String? selectedValue,
  }) {
    final Set<String> deduped = <String>{};
    for (final String value in seed) {
      final String? normalized = _normalizeFilterValue(value);
      if (normalized != null) {
        deduped.add(normalized);
      }
    }
    for (final String? value in values) {
      final String? normalized = _normalizeFilterValue(value);
      if (normalized != null) {
        deduped.add(normalized);
      }
    }
    final String? normalizedSelected = _normalizeFilterValue(selectedValue);
    if (normalizedSelected != null) {
      deduped.add(normalizedSelected);
    }
    final List<String> options = deduped.toList(growable: false);
    options.sort((String left, String right) {
      return left.toLowerCase().compareTo(right.toLowerCase());
    });
    return options;
  }

  Future<void> _openNotifications() {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            GteNotificationsScreen(controller: widget.controller),
      ),
    );
  }

  Future<void> _openFilterMenu() async {
    final PlayerFilter filter = _draftMarketFilter;
    await showModalBottomSheet<void>(
      context: context,
      builder: (BuildContext context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              ListTile(
                title: const Text('Position'),
                subtitle: Text(filter.position ?? 'All positions'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.of(context).pop();
                  _pickPositionFilter();
                },
              ),
              ListTile(
                title: const Text('Age'),
                subtitle: Text(_ageLabel(filter)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.of(context).pop();
                  _pickAgeFilter();
                },
              ),
              ListTile(
                title: const Text('Country'),
                subtitle: Text(filter.country ?? 'All countries'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.of(context).pop();
                  _pickCountryFilter();
                },
              ),
              ListTile(
                title: const Text('Availability'),
                subtitle: Text(_availabilityLabel(filter.availability)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.of(context).pop();
                  _pickAvailabilityFilter();
                },
              ),
              if (_hasActiveFilters)
                ListTile(
                  title: const Text('Reset filters'),
                  leading: const Icon(Icons.refresh_rounded),
                  onTap: () {
                    Navigator.of(context).pop();
                    _showAllPlayers();
                  },
                ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _pickAgeFilter() async {
    final PlayerFilter filter = _draftMarketFilter;
    final int initialMin = (filter.minAge ?? _minSelectableAge)
        .clamp(_minSelectableAge, _maxSelectableAge);
    final int initialMax = (filter.maxAge ?? _maxSelectableAge)
        .clamp(_minSelectableAge, _maxSelectableAge);
    final RangeValues initialRange = initialMin <= initialMax
        ? RangeValues(initialMin.toDouble(), initialMax.toDouble())
        : RangeValues(initialMax.toDouble(), initialMin.toDouble());
    final _AgeRangeSelection? next =
        await showModalBottomSheet<_AgeRangeSelection>(
      context: context,
      builder: (BuildContext context) {
        RangeValues draftRange = initialRange;
        return SafeArea(
          child: StatefulBuilder(
            builder: (BuildContext context, StateSetter setModalState) {
              return Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text(
                      'Age range',
                      style: TextStyle(
                        color: _text,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '${draftRange.start.round()} - ${draftRange.end.round()}',
                      style: const TextStyle(
                        color: _muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    RangeSlider(
                      values: draftRange,
                      min: _minSelectableAge.toDouble(),
                      max: _maxSelectableAge.toDouble(),
                      divisions: _maxSelectableAge - _minSelectableAge,
                      labels: RangeLabels(
                        '${draftRange.start.round()}',
                        '${draftRange.end.round()}',
                      ),
                      onChanged: (RangeValues nextRange) {
                        setModalState(() {
                          draftRange = nextRange;
                        });
                      },
                    ),
                    Row(
                      children: <Widget>[
                        TextButton(
                          onPressed: () {
                            Navigator.of(context).pop(
                              const _AgeRangeSelection.clear(),
                            );
                          },
                          child: const Text('Clear'),
                        ),
                        const Spacer(),
                        FilledButton(
                          onPressed: () {
                            Navigator.of(context).pop(
                              _AgeRangeSelection(
                                minAge: draftRange.start.round(),
                                maxAge: draftRange.end.round(),
                              ),
                            );
                          },
                          child: const Text('Apply'),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
    if (!mounted || next == null) {
      return;
    }
    unawaited(
      _applyMarketFilter(
        _draftMarketFilter.copyWith(
          minAge: next.clear ? null : next.minAge,
          maxAge: next.clear ? null : next.maxAge,
        ),
      ),
    );
  }

  Future<void> _pickAvailabilityFilter() async {
    final String? next = await showModalBottomSheet<String?>(
      context: context,
      builder: (BuildContext context) {
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: <Widget>[
              ListTile(
                leading: Icon(
                  _draftMarketFilter.availability == null
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                ),
                title: const Text('Any player'),
                onTap: () => Navigator.of(context).pop(),
              ),
              ListTile(
                leading: Icon(
                  _draftMarketFilter.availability == _freeAgentAvailability
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                ),
                title: const Text('Free agent'),
                onTap: () => Navigator.of(context).pop(_freeAgentAvailability),
              ),
            ],
          ),
        );
      },
    );
    if (!mounted) {
      return;
    }
    unawaited(
      _applyMarketFilter(
        _draftMarketFilter.copyWith(availability: next),
      ),
    );
  }

  Future<void> _pickPositionFilter() async {
    final String? next = await _showOptionSelector(
      title: 'Position',
      allLabel: 'All positions',
      currentValue: _draftMarketFilter.position,
      options: _positionOptions,
    );
    if (!mounted) {
      return;
    }
    unawaited(
      _applyMarketFilter(
        _draftMarketFilter.copyWith(position: next),
      ),
    );
  }

  Future<void> _pickCountryFilter() async {
    final String? next = await _showOptionSelector(
      title: 'Country',
      allLabel: 'All countries',
      currentValue: _draftMarketFilter.country,
      options: _countryOptions,
      searchable: true,
      leadingBuilder: (String value) => Text(
        _flagEmoji(value),
        style: const TextStyle(fontSize: 20),
      ),
    );
    if (!mounted) {
      return;
    }
    unawaited(
      _applyMarketFilter(
        _draftMarketFilter.copyWith(country: next),
      ),
    );
  }

  Future<String?> _showOptionSelector({
    required String title,
    required String allLabel,
    required String? currentValue,
    required List<String> options,
    bool searchable = false,
    Widget Function(String value)? leadingBuilder,
  }) async {
    final String? next = await showModalBottomSheet<String?>(
      context: context,
      builder: (BuildContext context) {
        String query = '';
        return SafeArea(
          child: StatefulBuilder(
            builder: (BuildContext context, StateSetter setModalState) {
              final List<String> visibleOptions = options.where((String value) {
                if (query.isEmpty) {
                  return true;
                }
                return value.toLowerCase().contains(query.toLowerCase());
              }).toList(growable: false);
              return SizedBox(
                height: searchable ? 480 : 420,
                child: Column(
                  children: <Widget>[
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                      child: Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              title,
                              style: const TextStyle(
                                color: _text,
                                fontSize: 20,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          IconButton(
                            onPressed: () => Navigator.of(context).pop(),
                            icon: const Icon(Icons.close_rounded),
                          ),
                        ],
                      ),
                    ),
                    if (searchable)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                        child: TextField(
                          autofocus: true,
                          decoration: InputDecoration(
                            hintText: 'Search $title',
                            prefixIcon: const Icon(Icons.search, color: _muted),
                            filled: true,
                            fillColor: _surface,
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide: const BorderSide(color: _line),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide:
                                  const BorderSide(color: _accent, width: 1.2),
                            ),
                          ),
                          onChanged: (String value) {
                            setModalState(() {
                              query = value.trim();
                            });
                          },
                        ),
                      ),
                    Expanded(
                      child: ListView(
                        shrinkWrap: true,
                        children: <Widget>[
                          ListTile(
                            leading: const Icon(Icons.public_rounded),
                            title: Text(allLabel),
                            trailing: Icon(
                              currentValue == null
                                  ? Icons.radio_button_checked
                                  : Icons.radio_button_unchecked,
                            ),
                            onTap: () => Navigator.of(context).pop(),
                          ),
                          ...visibleOptions.map(
                            (String value) => ListTile(
                              leading: leadingBuilder?.call(value),
                              title: Text(value),
                              trailing: Icon(
                                value == currentValue
                                    ? Icons.radio_button_checked
                                    : Icons.radio_button_unchecked,
                              ),
                              onTap: () => Navigator.of(context).pop(value),
                            ),
                          ),
                          if (visibleOptions.isEmpty)
                            const ListTile(
                              title: Text(
                                'No options match this search.',
                                style: TextStyle(color: _muted),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
    return next;
  }

  Future<void> _openMatchBriefSheet() async {
    final List<String> positions = <String>{
      'ST',
      'RW',
      'LW',
      'AM',
      'CM',
      'DM',
      'CB',
      'RB',
      'LB',
      ..._mergeOptions(
        values: widget.controller.players
            .map((GteMarketPlayerListItem player) => player.position),
      ),
    }.toList(growable: false)
      ..sort();
    final List<String> countries = _mergeOptions(
      values: widget.controller.players
          .map((GteMarketPlayerListItem player) => player.nationality),
    );

    String? draftPosition = _matchFilters.position;
    String? draftCountry = _matchFilters.country;
    String? draftPreferredFoot = _matchFilters.preferredFoot;
    double? draftMinHeight = _matchFilters.minHeightMeters;
    final TextEditingController minAgeController = TextEditingController(
      text: _matchFilters.minAge?.toString() ?? '',
    );
    final TextEditingController maxAgeController = TextEditingController(
      text: _matchFilters.maxAge?.toString() ?? '',
    );

    final GteScoutMatchFilters? nextFilters =
        await showModalBottomSheet<GteScoutMatchFilters>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setModalState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                16,
                16,
                16,
                16 + MediaQuery.of(context).viewInsets.bottom,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text(
                      'Scout Brief',
                      style: TextStyle(
                        color: _text,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Adjust the weighted fit inputs used by the local match engine.',
                      style: TextStyle(color: _muted),
                    ),
                    const SizedBox(height: 18),
                    DropdownButtonFormField<String>(
                      initialValue: draftPosition,
                      decoration: const InputDecoration(labelText: 'Position'),
                      items: <DropdownMenuItem<String>>[
                        const DropdownMenuItem<String>(
                          value: null,
                          child: Text('Any position'),
                        ),
                        ...positions.map(
                          (String value) => DropdownMenuItem<String>(
                            value: value,
                            child: Text(value),
                          ),
                        ),
                      ],
                      onChanged: (String? value) {
                        setModalState(() {
                          draftPosition = value;
                        });
                      },
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: TextField(
                            controller: minAgeController,
                            keyboardType: TextInputType.number,
                            decoration:
                                const InputDecoration(labelText: 'Min age'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: maxAgeController,
                            keyboardType: TextInputType.number,
                            decoration:
                                const InputDecoration(labelText: 'Max age'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: draftCountry,
                      decoration: const InputDecoration(labelText: 'Country'),
                      items: <DropdownMenuItem<String>>[
                        const DropdownMenuItem<String>(
                          value: null,
                          child: Text('Any country'),
                        ),
                        ...countries.map(
                          (String value) => DropdownMenuItem<String>(
                            value: value,
                            child: Text(value),
                          ),
                        ),
                      ],
                      onChanged: (String? value) {
                        setModalState(() {
                          draftCountry = value;
                        });
                      },
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: draftPreferredFoot,
                      decoration:
                          const InputDecoration(labelText: 'Preferred foot'),
                      items: const <DropdownMenuItem<String>>[
                        DropdownMenuItem<String>(
                          value: null,
                          child: Text('Any foot'),
                        ),
                        DropdownMenuItem<String>(
                          value: 'Right',
                          child: Text('Right'),
                        ),
                        DropdownMenuItem<String>(
                          value: 'Left',
                          child: Text('Left'),
                        ),
                      ],
                      onChanged: (String? value) {
                        setModalState(() {
                          draftPreferredFoot = value;
                        });
                      },
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<double>(
                      initialValue: draftMinHeight,
                      decoration:
                          const InputDecoration(labelText: 'Minimum height'),
                      items: const <DropdownMenuItem<double>>[
                        DropdownMenuItem<double>(
                          value: null,
                          child: Text('Any height'),
                        ),
                        DropdownMenuItem<double>(
                          value: 1.7,
                          child: Text('1.70m'),
                        ),
                        DropdownMenuItem<double>(
                          value: 1.75,
                          child: Text('1.75m'),
                        ),
                        DropdownMenuItem<double>(
                          value: 1.8,
                          child: Text('1.80m'),
                        ),
                        DropdownMenuItem<double>(
                          value: 1.85,
                          child: Text('1.85m'),
                        ),
                        DropdownMenuItem<double>(
                          value: 1.9,
                          child: Text('1.90m'),
                        ),
                      ],
                      onChanged: (double? value) {
                        setModalState(() {
                          draftMinHeight = value;
                        });
                      },
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: <Widget>[
                        TextButton(
                          onPressed: () {
                            Navigator.of(context).pop(
                              const GteScoutMatchFilters.defaultBrief(),
                            );
                          },
                          child: const Text('Reset to MVP'),
                        ),
                        const Spacer(),
                        FilledButton(
                          onPressed: () {
                            Navigator.of(context).pop(
                              GteScoutMatchFilters(
                                position: draftPosition,
                                minAge:
                                    int.tryParse(minAgeController.text.trim()),
                                maxAge:
                                    int.tryParse(maxAgeController.text.trim()),
                                country: draftCountry,
                                preferredFoot: draftPreferredFoot,
                                minHeightMeters: draftMinHeight,
                              ),
                            );
                          },
                          child: const Text('Apply'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    minAgeController.dispose();
    maxAgeController.dispose();

    if (!mounted || nextFilters == null) {
      return;
    }
    setState(() {
      _matchFilters = nextFilters;
    });
    _refreshMatchesIfNeeded(force: true);
  }

  Future<void> _openMatchWeightsSheet() async {
    final MatchWeights? nextWeights = await showModalBottomSheet<MatchWeights>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return MatchWeightsSheet(
          initial: widget.controller.weights,
          onApply: (MatchWeights weights) {
            Navigator.of(context).pop(weights);
          },
        );
      },
    );
    if (!mounted || nextWeights == null) {
      return;
    }
    widget.controller.updateWeights(nextWeights);
    _refreshMatchesIfNeeded(force: true);
  }

  Future<void> _openCreatorShareMarketRoute() async {
    final String? clubId = widget.navigationDependencies?.currentClubId?.trim();
    if (clubId == null || clubId.isEmpty) {
      await _showRouteRequirementDialog(
        title: 'Club selection required',
        message:
            'Creator-share market routes are club-scoped and stay blocked until the session exposes a canonical current club id.',
      );
      return;
    }
    await _openFeatureRoute(
      CreatorShareMarketClubRouteData(
        clubId: clubId,
        clubName: widget.navigationDependencies?.currentClubName,
      ),
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
}

String _ageLabel(PlayerFilter filter) {
  final int? minAge = filter.minAge;
  final int? maxAge = filter.maxAge;
  if (minAge == null && maxAge == null) {
    return 'Any age';
  }
  return '${minAge ?? _minSelectableAge} - ${maxAge ?? _maxSelectableAge}';
}

String _availabilityLabel(String? value) {
  if (value == _freeAgentAvailability) {
    return 'Free agent';
  }
  return 'Any player';
}

String? _normalizeFilterValue(String? value) {
  if (value == null) {
    return null;
  }
  final String trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

String _flagEmoji(String country) {
  const Map<String, String> flags = <String, String>{
    'argentina': '🇦🇷',
    'brazil': '🇧🇷',
    'england': '🇬🇧',
    'france': '🇫🇷',
    'germany': '🇩🇪',
    'ghana': '🇬🇭',
    'italy': '🇮🇹',
    'japan': '🇯🇵',
    'morocco': '🇲🇦',
    'netherlands': '🇳🇱',
    'nigeria': '🇳🇬',
    'portugal': '🇵🇹',
    'senegal': '🇸🇳',
    'spain': '🇪🇸',
    'united states': '🇺🇸',
    'usa': '🇺🇸',
  };
  return flags[country.trim().toLowerCase()] ?? '🌍';
}

Color _matchScoreColor(double score) {
  if (score >= 0.9) {
    return _positive;
  }
  if (score >= 0.7) {
    return _accent;
  }
  return _neutral;
}

class _AgeRangeSelection {
  const _AgeRangeSelection({
    required this.minAge,
    required this.maxAge,
  }) : clear = false;

  const _AgeRangeSelection.clear()
      : minAge = null,
        maxAge = null,
        clear = true;

  final int? minAge;
  final int? maxAge;
  final bool clear;
}

class _FilterChipButton extends StatelessWidget {
  const _FilterChipButton({
    required this.label,
    required this.onTap,
    this.active = false,
  });

  final String label;
  final VoidCallback onTap;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: InputChip(
        label: Text(label),
        selected: active,
        backgroundColor: Colors.white,
        selectedColor: _accentSoft,
        side: BorderSide(color: active ? _lineStrong : _line),
        onPressed: onTap,
      ),
    );
  }
}

class _MatchSummaryChip extends StatelessWidget {
  const _MatchSummaryChip({
    required this.label,
    required this.color,
    required this.backgroundColor,
  });

  final String label;
  final Color color;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _MatchScoreBadge extends StatelessWidget {
  const _MatchScoreBadge({
    required this.score,
    required this.color,
  });

  final double score;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final int percentage = (score * 100).round().clamp(0, 100);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: <Widget>[
          Text(
            '$percentage%',
            style: TextStyle(
              color: color,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            'Match Score',
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _MarketRoutePanel extends StatelessWidget {
  const _MarketRoutePanel({
    required this.onOpenPlayerCards,
    required this.onOpenCreatorShareMarket,
    required this.onOpenClubSaleMarket,
  });

  final VoidCallback onOpenPlayerCards;
  final VoidCallback onOpenCreatorShareMarket;
  final VoidCallback onOpenClubSaleMarket;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: _line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'Market extensions',
            style: TextStyle(
              color: _text,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Card, creator-share, and club-sale routes stay adjacent to discovery instead of becoming extra shell tabs.',
            style: TextStyle(color: _muted),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onOpenPlayerCards,
                icon: const Icon(Icons.style_outlined),
                label: const Text('Player cards'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenCreatorShareMarket,
                icon: const Icon(Icons.candlestick_chart_outlined),
                label: const Text('Creator shares'),
              ),
              FilledButton.tonalIcon(
                onPressed: onOpenClubSaleMarket,
                icon: const Icon(Icons.storefront_outlined),
                label: const Text('Club sale market'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

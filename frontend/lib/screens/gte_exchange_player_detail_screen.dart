import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../data/agent_marketplace_api.dart';
import '../data/agent_marketplace_models.dart';
import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';
import '../models/player_avatar.dart';
import '../providers/gte_exchange_controller.dart';
import '../screens/agent_conversation_screen.dart';
import '../services/avatar_mapper.dart';
import '../widgets/agent_conversation_compose_sheet.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_order_detail_card.dart';
import '../widgets/gte_order_ticket_sheet.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_trend_strip.dart';
import '../widgets/market/player_market_avatar.dart';

class GteExchangePlayerDetailScreen extends StatefulWidget {
  const GteExchangePlayerDetailScreen({
    super.key,
    required this.controller,
    required this.playerId,
    required this.onRequireLogin,
  });

  final GteExchangeController controller;
  final String playerId;
  final VoidCallback onRequireLogin;

  @override
  State<GteExchangePlayerDetailScreen> createState() =>
      _GteExchangePlayerDetailScreenState();
}

class _GteExchangePlayerDetailScreenState
    extends State<GteExchangePlayerDetailScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    widget.controller.openPlayer(widget.playerId);
  }

  @override
  void didUpdateWidget(covariant GteExchangePlayerDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.playerId != widget.playerId) {
      _tabController.index = 0;
      widget.controller.openPlayer(widget.playerId);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  AgentMarketplaceApi _marketplaceApi() {
    return AgentMarketplaceApi(
      config: widget.controller.api.config,
      transport: widget.controller.api.transport,
      accessToken: widget.controller.accessToken,
      mode: widget.controller.api.config.mode,
    );
  }

  GteMarketPlayerListItem? _marketplaceListingForCurrentPlayer() {
    for (final GteMarketPlayerListItem player in widget.controller.players) {
      if (player.playerId == widget.playerId) {
        return player;
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            final GtePlayerMarketSnapshot? snapshot =
                widget.controller.selectedPlayer;
            final bool hasExpectedSnapshot =
                snapshot != null && snapshot.detail.playerId == widget.playerId;

            if (!hasExpectedSnapshot && widget.controller.isLoadingPlayer) {
              return SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: GteStatePanel(
                    eyebrow: 'PLAYER PROFILE',
                    title: 'Loading player dossier',
                    message:
                        'Identity, availability, market context, and career history are being assembled.',
                    icon: Icons.person_search_outlined,
                    accentColor: GteShellTheme.accent,
                    isLoading: true,
                  ),
                ),
              );
            }

            if (!hasExpectedSnapshot) {
              return SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: GteStatePanel(
                    title: 'Player unavailable',
                    message:
                        widget.controller.playerError ??
                        'Unable to load this player.',
                    actionLabel: 'Retry',
                    onAction: _refreshSnapshot,
                    icon: Icons.person_off_outlined,
                  ),
                ),
              );
            }

            final PlayerProfile profile = _resolvedProfile(snapshot);
            final GteOrderRecord? order = widget.controller.orderForPlayer(
              widget.playerId,
            );
            return RefreshIndicator(
              onRefresh: _refreshSnapshot,
              notificationPredicate:
                  (ScrollNotification notification) => notification.depth == 0,
              child: NestedScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                headerSliverBuilder: (
                  BuildContext context,
                  bool innerBoxIsScrolled,
                ) {
                  return <Widget>[
                    SliverToBoxAdapter(
                      child: _buildHeader(context, snapshot, profile, order),
                    ),
                    SliverPersistentHeader(
                      pinned: true,
                      delegate: _StickyTabBarDelegate(
                        child: _ProfileTabBar(tabController: _tabController),
                      ),
                    ),
                  ];
                },
                body: TabBarView(
                  controller: _tabController,
                  children: <Widget>[
                    _ProfileTabList(
                      key: PageStorageKey<String>(
                        'overview-${widget.playerId}',
                      ),
                      children: _buildOverviewTab(snapshot, profile, order),
                    ),
                    _ProfileTabList(
                      key: PageStorageKey<String>('stats-${widget.playerId}'),
                      children: _buildStatsTab(snapshot, profile),
                    ),
                    _ProfileTabList(
                      key: PageStorageKey<String>('career-${widget.playerId}'),
                      children: _buildCareerTab(snapshot, profile),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    GtePlayerMarketSnapshot snapshot,
    PlayerProfile profile,
    GteOrderRecord? order,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _HeroSection(
          avatar: AvatarMapper.fromMarketIdentity(
            snapshot.detail.identity,
            playerId: snapshot.detail.playerId,
          ),
          identity: snapshot.detail.identity,
          availability: _availabilityFor(snapshot),
          clubLabel: _clubLabel(snapshot),
          isShortlisted: widget.controller.isPlayerShortlisted(widget.playerId),
          onBack: () {
            if (Navigator.of(context).canPop()) {
              Navigator.of(context).pop();
            }
          },
          onToggleShortlist: _toggleShortlist,
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
          child: _QuickInfoStrip(
            items: <_QuickInfoItem>[
              _QuickInfoItem(
                label: 'Age',
                value: snapshot.detail.identity.age.toString(),
              ),
              _QuickInfoItem(
                label: 'Height',
                value: _heightLabel(snapshot.detail.identity),
              ),
              _QuickInfoItem(
                label: 'Foot',
                value: snapshot.detail.identity.preferredFoot ?? 'Unknown',
              ),
              _QuickInfoItem(label: 'Club', value: _clubLabel(snapshot)),
              _QuickInfoItem(
                label: 'Country',
                value: _countryLabel(snapshot.detail.identity),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          child: _TopStatStrip(
            cards: <_ProfileStatCardData>[
              _ProfileStatCardData(
                label: 'Current value',
                value: gteFormatNullableCredits(
                  snapshot.detail.value.currentValueCredits,
                ),
                accent: GteShellTheme.accent,
              ),
              _ProfileStatCardData(
                label: 'Trend score',
                value:
                    snapshot.detail.trend.trendScore?.toStringAsFixed(1) ??
                    '--',
                accent: const Color(0xFF8EE6C7),
              ),
              _ProfileStatCardData(
                label: 'Average rating',
                value:
                    snapshot.detail.trend.averageRating?.toStringAsFixed(1) ??
                    '--',
                accent: const Color(0xFF89B6FF),
              ),
              _ProfileStatCardData(
                label: 'Availability',
                value: _availabilityFor(snapshot).label,
                accent:
                    _availabilityFor(snapshot).available
                        ? GteShellTheme.positive
                        : GteShellTheme.warning,
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          child: _ActionBar(
            isScouted: widget.controller.isPlayerScouted(widget.playerId),
            isShortlisted: widget.controller.isPlayerShortlisted(
              widget.playerId,
            ),
            onScoutPlayer: () => _handleScoutPlayer(snapshot),
            onToggleShortlist: _toggleShortlist,
            onContactAgent: () => _handleContactAgent(snapshot),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildOverviewTab(
    GtePlayerMarketSnapshot snapshot,
    PlayerProfile profile,
    GteOrderRecord? order,
  ) {
    final GteMarketPlayerListItem? marketplaceListing =
        _marketplaceListingForCurrentPlayer();
    final List<Widget> children = <Widget>[
      if (widget.controller.isLoadingPlayer)
        const LinearProgressIndicator(minHeight: 3),
      if (widget.controller.playerError != null)
        _StatusNotice(
          icon: Icons.warning_amber_rounded,
          message:
              'Player refresh did not complete. ${widget.controller.playerError!}',
        ),
      if (widget.controller.playerProfileError != null)
        _StatusNotice(
          icon: Icons.description_outlined,
          message:
              'Career and scouting notes are unavailable right now. ${widget.controller.playerProfileError!}',
        ),
      _ProfileSectionCard(
        title: 'Scouting report',
        child: Text(
          profile.scoutingReport,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
      _ProfileSectionCard(
        title: 'Transfer signal',
        child: Text(
          profile.transferSignal,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
      _ProfileSectionCard(
        title: 'Bio',
        child: Text(
          _bioText(snapshot),
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
      _ProfileSectionCard(
        title: 'Playing style',
        child: Text(
          _playingStyleText(snapshot),
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
      _ProfileSectionCard(
        title: 'Strengths',
        child: Wrap(
          spacing: 10,
          runSpacing: 10,
          children: _strengthTags(snapshot)
              .map((String item) => _TagChip(label: item, positive: true))
              .toList(growable: false),
        ),
      ),
      _ProfileSectionCard(
        title: 'Weaknesses',
        child: Wrap(
          spacing: 10,
          runSpacing: 10,
          children: _weaknessTags(
            snapshot,
          ).map((String item) => _TagChip(label: item)).toList(growable: false),
        ),
      ),
      _ProfileSectionCard(
        title: 'Current situation',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _TagChip(
                  label: _availabilityFor(snapshot).label,
                  positive: _availabilityFor(snapshot).available,
                ),
                if (_transferStatusFor(snapshot).windowLabel != null)
                  _TagChip(label: _transferStatusFor(snapshot).windowLabel!),
                _TagChip(
                  label:
                      _transferStatusFor(snapshot).eligible
                          ? 'Transfer eligible'
                          : 'Transfer locked',
                  positive: _transferStatusFor(snapshot).eligible,
                ),
                if (_agencyFor(snapshot)?.transferStanceLabel != null)
                  _TagChip(label: _agencyFor(snapshot)!.transferStanceLabel),
                if (marketplaceListing != null) ...<Widget>[
                  _TagChip(
                    label: marketplaceListing.availabilityLabel,
                    positive: marketplaceListing.isAvailable,
                  ),
                  _TagChip(
                    label: gteAskingTypeLabel(marketplaceListing.askingType),
                  ),
                  _TagChip(label: 'Agent: ${marketplaceListing.agentName}'),
                ],
              ],
            ),
            if (_transferStatusFor(snapshot).reason != null) ...<Widget>[
              const SizedBox(height: 14),
              Text(
                _transferStatusFor(snapshot).reason!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            if (marketplaceListing?.marketplaceNote != null &&
                marketplaceListing!.marketplaceNote!
                    .trim()
                    .isNotEmpty) ...<Widget>[
              const SizedBox(height: 14),
              Text(
                marketplaceListing.marketplaceNote!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ],
        ),
      ),
      if (widget.controller.orderError != null)
        _StatusNotice(
          icon: Icons.warning_amber_rounded,
          message: widget.controller.orderError!,
        ),
      _buildMarketActionCard(snapshot, order),
    ];
    return children;
  }

  List<Widget> _buildStatsTab(
    GtePlayerMarketSnapshot snapshot,
    PlayerProfile profile,
  ) {
    final GteCareerTotals? totals = snapshot.overview?.careerSummary.totals;
    final List<GteSeasonProgression> seasons =
        snapshot.overview?.careerSummary.seasonalProgression ??
        const <GteSeasonProgression>[];
    final String position = _positionLabel(snapshot);
    return <Widget>[
      GteSurfacePanel(
        emphasized: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Profile indicators',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              'The profile feed keeps the football read visible alongside the market layer.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: profile.statBlocks
                  .map((String item) => _TagChip(label: item, positive: true))
                  .toList(growable: false),
            ),
          ],
        ),
      ),
      GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('Trend view', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
              'Value and GSI strips give the profile a compact production pulse.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Text('Value trend', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            GteTrendStrip(points: profile.snapshot.valueTrend),
            const SizedBox(height: 16),
            Text('GSI trend', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            GteTrendStrip(points: profile.gsiTrend),
          ],
        ),
      ),
      GteSurfacePanel(
        emphasized: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Season output',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              'Core production indicators stay readable at a glance, with bar weight giving each metric some visual hierarchy.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 14,
              runSpacing: 14,
              children: <Widget>[
                _StatMeterCard(
                  label: 'Matches',
                  value: totals?.appearances ?? 0,
                  progress: _matchProgress(totals?.appearances ?? 0),
                  accent: GteShellTheme.accent,
                ),
                _StatMeterCard(
                  label: 'Goals',
                  value: totals?.goals ?? 0,
                  progress: _goalProgress(position, totals?.goals ?? 0),
                  accent: const Color(0xFF8EE6C7),
                ),
                _StatMeterCard(
                  label: 'Assists',
                  value: totals?.assists ?? 0,
                  progress: _assistProgress(position, totals?.assists ?? 0),
                  accent: const Color(0xFF89B6FF),
                ),
                _StatMeterCard(
                  label: 'Minutes played',
                  value: totals?.minutes ?? 0,
                  suffix: 'min',
                  progress: _minutesProgress(totals?.minutes ?? 0),
                  accent: const Color(0xFFFFC77D),
                ),
              ],
            ),
          ],
        ),
      ),
      GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Season progression',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              'Recent seasons summarize usage, end product, and minutes without losing the profile feel.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            if (seasons.isEmpty)
              const GteStatePanel(
                title: 'No seasonal progression available',
                message:
                    'This player does not yet expose season-by-season output in the current data source.',
                icon: Icons.bar_chart_outlined,
              )
            else
              ...seasons.map(
                (GteSeasonProgression season) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: _SeasonProgressRow(
                    season: season,
                    progress: _matchProgress(season.appearances),
                  ),
                ),
              ),
          ],
        ),
      ),
      GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('Market pulse', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
              'Profile mode still keeps the current market read nearby for scouts who care about both football context and pricing temperature.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _TagChip(
                  label: gteFormatNullableMovement(
                    snapshot.detail.value.movementPct,
                  ),
                  positive: (snapshot.detail.value.movementPct ?? 0) >= 0,
                ),
                _TagChip(
                  label:
                      'Interest ${snapshot.detail.trend.marketInterestScore ?? '--'}',
                ),
                _TagChip(
                  label:
                      'Liquidity ${(snapshot.detail.marketProfile.liquidityBand ?? 'forming').toUpperCase()}',
                ),
                _TagChip(
                  label:
                      'Trend ${snapshot.detail.trend.trendScore?.toStringAsFixed(1) ?? '--'}',
                ),
              ],
            ),
          ],
        ),
      ),
    ];
  }

  List<Widget> _buildCareerTab(
    GtePlayerMarketSnapshot snapshot,
    PlayerProfile profile,
  ) {
    final List<GteCareerEntry> entries = _careerEntries(snapshot);
    return <Widget>[
      GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Honors and milestones',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              'Production-ready profile mode keeps the quick career summary close to the timeline.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            if (profile.awards.isEmpty)
              const Text('No honors are available in the current profile.')
            else
              ...profile.awards.map(
                (String award) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Padding(
                        padding: EdgeInsets.only(top: 4),
                        child: Icon(Icons.workspace_premium_outlined, size: 16),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          award,
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
      GteSurfacePanel(
        emphasized: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('Career path', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
              snapshot.overview?.careerSummary.currentCompetitionName ??
                  'The timeline below tracks the player through recent seasons and roles.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _TagChip(label: _clubLabel(snapshot), positive: true),
                _TagChip(
                  label: _availabilityFor(snapshot).label,
                  positive: _availabilityFor(snapshot).available,
                ),
                if (_transferStatusFor(snapshot).windowLabel != null)
                  _TagChip(label: _transferStatusFor(snapshot).windowLabel!),
              ],
            ),
          ],
        ),
      ),
      if (entries.isEmpty)
        const GteStatePanel(
          title: 'Career history unavailable',
          message:
              'No club timeline is available for this player in the current source.',
          icon: Icons.timeline_outlined,
        )
      else
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Timeline', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 16),
              ...entries.asMap().entries.map(
                (MapEntry<int, GteCareerEntry> entry) => _CareerTimelineItem(
                  item: entry.value,
                  isLast: entry.key == entries.length - 1,
                ),
              ),
            ],
          ),
        ),
    ];
  }

  Widget _buildMarketActionCard(
    GtePlayerMarketSnapshot snapshot,
    GteOrderRecord? order,
  ) {
    if (order != null) {
      return GteOrderDetailCard(
        order: order,
        playerLabel: snapshot.detail.identity.playerName,
        isRefreshing: widget.controller.isRefreshingOrder,
        isCancelling: widget.controller.isCancellingOrder,
        onRefresh: () => _refreshOrder(order),
        onCancel: () => _cancelOrder(order),
      );
    }

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Market action', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            widget.controller.isAuthenticated
                ? 'The profile stays scout-first, but the trading ticket is still one step away when you want to move from observation to execution.'
                : 'Sign in to unlock wallet-aware order entry, refresh live order state, and manage tickets for this player.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          Row(
            children: <Widget>[
              Expanded(
                child: FilledButton.icon(
                  onPressed:
                      widget.controller.isAuthenticated
                          ? _openTicket
                          : widget.onRequireLogin,
                  icon: Icon(
                    widget.controller.isAuthenticated
                        ? Icons.candlestick_chart
                        : Icons.login,
                  ),
                  label: Text(
                    widget.controller.isAuthenticated
                        ? 'Open order ticket'
                        : 'Sign in to trade',
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _refreshSnapshot,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Refresh profile'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _handleScoutPlayer(GtePlayerMarketSnapshot snapshot) async {
    widget.controller.toggleScouted(widget.playerId);
    if (_tabController.index != 0) {
      _tabController.animateTo(0);
    }
    _showMessage(
      widget.controller.isPlayerScouted(widget.playerId)
          ? 'Added ${snapshot.detail.identity.playerName} to your scouting board.'
          : 'Removed ${snapshot.detail.identity.playerName} from your scouting board.',
    );
  }

  void _toggleShortlist() {
    widget.controller.toggleShortlist(widget.playerId);
    _showMessage(
      widget.controller.isPlayerShortlisted(widget.playerId)
          ? 'Player added to shortlist.'
          : 'Player removed from shortlist.',
    );
  }

  Future<void> _handleContactAgent(GtePlayerMarketSnapshot snapshot) async {
    final GteMarketPlayerListItem? marketplaceListing =
        _marketplaceListingForCurrentPlayer();
    if (!widget.controller.isAuthenticated) {
      widget.onRequireLogin();
      return;
    }
    if (marketplaceListing == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'This player is not currently listed in the agent marketplace.',
          ),
        ),
      );
      return;
    }
    final String? currentUserId = widget.controller.session?.user.id;
    if (currentUserId == null || currentUserId.isEmpty) {
      widget.onRequireLogin();
      return;
    }
    final String? message = await showAgentConversationComposer(
      context,
      playerName: snapshot.detail.identity.playerName,
      askingType: marketplaceListing.askingType,
    );
    if (!mounted || message == null) {
      return;
    }
    try {
      final GteConversationDetail detail = await _marketplaceApi()
          .startConversation(playerId: widget.playerId, message: message);
      if (!mounted) {
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) => AgentConversationScreen(
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
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
    }
  }

  Future<void> _openTicket() async {
    final GtePlayerMarketSnapshot? snapshot = widget.controller.selectedPlayer;
    if (snapshot == null) {
      return;
    }
    final GteOrderRecord? order = await showModalBottomSheet<GteOrderRecord>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return GteOrderTicketSheet(
          controller: widget.controller,
          snapshot: snapshot,
        );
      },
    );
    if (!mounted || order == null) {
      return;
    }
    _showMessage('Order accepted for ${snapshot.detail.identity.playerName}.');
  }

  Future<void> _refreshSnapshot() async {
    await Future.wait<void>(<Future<void>>[
      widget.controller.openPlayer(
        widget.playerId,
        interval: widget.controller.selectedCandleInterval,
      ),
      if (widget.controller.isAuthenticated) widget.controller.refreshAccount(),
    ]);
  }

  Future<void> _refreshOrder(GteOrderRecord order) async {
    final GteOrderRecord? refreshed = await widget.controller.refreshOrder(
      order.id,
    );
    if (!mounted || refreshed == null) {
      return;
    }
    _showMessage(
      'Order status refreshed: ${gteFormatOrderStatus(refreshed.status.name)}.',
    );
  }

  Future<void> _cancelOrder(GteOrderRecord order) async {
    final GteOrderRecord? cancelled = await widget.controller.cancelOrder(
      order.id,
    );
    if (!mounted || cancelled == null) {
      return;
    }
    _showMessage(
      'Order updated: ${gteFormatOrderStatus(cancelled.status.name)}.',
    );
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  PlayerProfile _resolvedProfile(GtePlayerMarketSnapshot snapshot) {
    final PlayerProfile? selectedProfile = widget.controller.selectedProfile;
    if (selectedProfile != null &&
        selectedProfile.snapshot.id == snapshot.detail.playerId) {
      return selectedProfile;
    }

    final List<TrendPoint> valueTrend = snapshot.candles.candles
        .take(6)
        .map(
          (GteMarketCandle candle) => TrendPoint(
            label: candle.timestamp.month.toString().padLeft(2, '0'),
            value: candle.close,
          ),
        )
        .toList(growable: false);
    final List<String> highlights = <String>[
      ...snapshot.detail.trend.drivers,
      if ((snapshot.detail.value.movementPct ?? 0) != 0)
        'Market move ${gteFormatNullableMovement(snapshot.detail.value.movementPct)}',
      if (snapshot.detail.marketProfile.liquidityBand != null)
        'Liquidity ${(snapshot.detail.marketProfile.liquidityBand ?? '').toUpperCase()}',
    ];

    return PlayerProfile(
      snapshot: PlayerSnapshot(
        id: snapshot.detail.playerId,
        name: snapshot.detail.identity.playerName,
        club: _clubLabel(snapshot),
        nation: snapshot.detail.identity.nationality ?? 'Unknown',
        position: _positionLabel(snapshot),
        age: snapshot.detail.identity.age,
        marketCredits: (snapshot.detail.value.currentValueCredits ?? 0).round(),
        gsi: snapshot.detail.trend.globalScoutingIndex.round(),
        formRating: snapshot.detail.trend.averageRating ?? 0,
        valueDeltaPct: (snapshot.detail.value.movementPct ?? 0) * 100,
        valueTrend: valueTrend,
        recentHighlights: highlights,
        isFollowed: widget.controller.isPlayerScouted(widget.playerId),
        isShortlisted: widget.controller.isPlayerShortlisted(widget.playerId),
      ),
      gsiTrend:
          valueTrend.isEmpty
              ? <TrendPoint>[
                TrendPoint(
                  label: 'Now',
                  value: snapshot.detail.trend.globalScoutingIndex,
                ),
              ]
              : valueTrend,
      awards: <String>[
        if (snapshot.overview?.careerSummary.currentCompetitionName != null)
          snapshot.overview!.careerSummary.currentCompetitionName!,
        if (_availabilityFor(snapshot).label.isNotEmpty)
          'Availability: ${_availabilityFor(snapshot).label}',
        if (_transferStatusFor(snapshot).windowLabel != null)
          'Window: ${_transferStatusFor(snapshot).windowLabel!}',
      ],
      statBlocks: <String>[
        'Trend ${snapshot.detail.trend.trendScore?.toStringAsFixed(1) ?? '--'}',
        'Interest ${snapshot.detail.trend.marketInterestScore ?? '--'}',
        'Rating ${snapshot.detail.trend.averageRating?.toStringAsFixed(1) ?? '--'}',
        'Value ${gteFormatNullableCredits(snapshot.detail.value.currentValueCredits)}',
      ],
      scoutingReport: _playingStyleText(snapshot),
      transferSignal:
          _transferStatusFor(snapshot).reason?.trim().isNotEmpty == true
              ? _transferStatusFor(snapshot).reason!
              : 'Transfer posture is still being clarified for this player.',
      ticker: snapshot.ticker,
      orderBook: snapshot.orderBook,
      candles: snapshot.candles,
    );
  }

  GteLifecycleBadgeView _availabilityFor(GtePlayerMarketSnapshot snapshot) {
    return snapshot.overview?.availabilityBadge ??
        snapshot.lifecycle?.availabilityBadge ??
        const GteLifecycleBadgeView(
          status: 'available',
          label: 'Available',
          available: true,
        );
  }

  GteTransferStatusView _transferStatusFor(GtePlayerMarketSnapshot snapshot) {
    return snapshot.overview?.transferStatus ??
        snapshot.lifecycle?.transferStatus ??
        const GteTransferStatusView(windowOpen: false, eligible: false);
  }

  GtePlayerAgencySummary? _agencyFor(GtePlayerMarketSnapshot snapshot) {
    return snapshot.overview?.agencySummary ??
        snapshot.lifecycle?.agencySummary;
  }

  List<GteCareerEntry> _careerEntries(GtePlayerMarketSnapshot snapshot) {
    final List<GteCareerEntry> entries = snapshot.careerEntries.toList(
      growable: false,
    );
    if (entries.isNotEmpty) {
      return entries;
    }
    return const <GteCareerEntry>[];
  }

  String _bioText(GtePlayerMarketSnapshot snapshot) {
    final GteMarketPlayerIdentity identity = snapshot.detail.identity;
    final GtePlayerOverview? overview = snapshot.overview;
    final GteTransferStatusView transferStatus = _transferStatusFor(snapshot);
    final String competition =
        overview?.careerSummary.currentCompetitionName ??
        identity.currentCompetitionName ??
        '';
    final String competitionText =
        competition.isEmpty ? '' : ' in $competition';
    final String availabilityText =
        _availabilityFor(snapshot).available
            ? 'Currently available for selection.'
            : '${_availabilityFor(snapshot).label} at the moment.';
    final String transferText =
        transferStatus.reason?.trim().isNotEmpty == true
            ? transferStatus.reason!.trim()
            : 'Transfer posture is still being clarified.';
    return '${identity.playerName} is a ${_positionLabel(snapshot)} profile, aged ${identity.age}, operating from ${_clubLabel(snapshot)}$competitionText. $availabilityText $transferText';
  }

  String _playingStyleText(GtePlayerMarketSnapshot snapshot) {
    final String position = _positionLabel(snapshot).toUpperCase();
    final List<String> drivers = snapshot.detail.trend.drivers;
    final String driverText =
        drivers.isEmpty
            ? 'Recent scouting and market signals remain balanced.'
            : 'Recent drivers point to ${drivers.take(2).join(' and ').toLowerCase()}.';
    if (position.contains('GK')) {
      return 'Goalkeeper profile built around command of the box, clean handling, and keeping the defensive line calm under pressure. $driverText';
    }
    if (position.contains('CB') ||
        position.contains('LB') ||
        position.contains('RB') ||
        position.contains('WB')) {
      return 'Defensive profile that values body control, duel timing, and calm distribution once possession is secured. $driverText';
    }
    if (position.contains('DM') ||
        position.contains('CM') ||
        position.contains('AM') ||
        position.contains('LM') ||
        position.contains('RM')) {
      return 'Midfield profile that wants touches, can progress the ball, and shapes the rhythm between buildup and final-third actions. $driverText';
    }
    return 'Attacking profile that leans on direct running, penalty-box presence, and quick separation when the game opens up. $driverText';
  }

  List<String> _strengthTags(GtePlayerMarketSnapshot snapshot) {
    final String position = _positionLabel(snapshot).toUpperCase();
    final List<String> tags = <String>[];
    if (position.contains('GK')) {
      tags.addAll(<String>[
        'Shot stopping',
        'Box command',
        'Calm distribution',
      ]);
    } else if (position.contains('CB') ||
        position.contains('LB') ||
        position.contains('RB') ||
        position.contains('WB')) {
      tags.addAll(<String>['Duel timing', 'Recovery speed', 'Defensive shape']);
    } else if (position.contains('DM') ||
        position.contains('CM') ||
        position.contains('AM') ||
        position.contains('LM') ||
        position.contains('RM')) {
      tags.addAll(<String>[
        'Press resistance',
        'Progressive carrying',
        'Game control',
      ]);
    } else {
      tags.addAll(<String>[
        'Box movement',
        'Explosive running',
        'Chance conversion',
      ]);
    }
    if ((snapshot.detail.value.movementPct ?? 0) > 0) {
      tags.add('Positive momentum');
    }
    if ((snapshot.detail.trend.marketInterestScore ?? 0) >= 70) {
      tags.add('Strong demand');
    }
    return tags.take(5).toList(growable: false);
  }

  List<String> _weaknessTags(GtePlayerMarketSnapshot snapshot) {
    final List<String> tags = <String>[];
    final GteTransferStatusView transferStatus = _transferStatusFor(snapshot);
    if (!_availabilityFor(snapshot).available) {
      tags.add('Availability risk');
    }
    if (!transferStatus.eligible) {
      tags.add('Transfer locked');
    }
    if ((snapshot.detail.marketProfile.tradeTrustScore ?? 0) < 6) {
      tags.add('Thin price discovery');
    }
    if ((snapshot.detail.value.movementPct ?? 0) < 0) {
      tags.add('Recent value dip');
    }
    if ((snapshot.overview?.careerSummary.totals.assists ?? 0) == 0 &&
        !_positionLabel(snapshot).toUpperCase().contains('GK')) {
      tags.add('Limited assist output');
    }
    if (tags.isEmpty) {
      tags.addAll(<String>['Data still forming', 'Needs more match sample']);
    }
    return tags.take(4).toList(growable: false);
  }

  String _clubLabel(GtePlayerMarketSnapshot snapshot) {
    final String? currentClub =
        snapshot.overview?.careerSummary.currentClubName ??
        snapshot.detail.identity.currentClubName;
    if (currentClub != null && currentClub.trim().isNotEmpty) {
      return currentClub.trim();
    }
    if (_agencyFor(snapshot)?.freeAgent == true) {
      return 'Free Agent';
    }
    return 'Independent';
  }

  String _positionLabel(GtePlayerMarketSnapshot snapshot) {
    return snapshot.overview?.position ??
        snapshot.detail.identity.position ??
        'Player';
  }

  String _countryLabel(GteMarketPlayerIdentity identity) {
    final String? country = identity.nationality?.trim();
    if (country == null || country.isEmpty) {
      return 'Unknown';
    }
    final String? code = identity.nationalityCode?.trim();
    if (code == null || code.isEmpty) {
      return country;
    }
    return '$country ($code)';
  }

  String _heightLabel(GteMarketPlayerIdentity identity) {
    final int? heightCm = identity.heightCm;
    if (heightCm == null || heightCm <= 0) {
      return '--';
    }
    return '${(heightCm / 100).toStringAsFixed(2)}m';
  }

  double _matchProgress(int matches) => _scaledProgress(matches, 60);

  double _goalProgress(String position, int goals) {
    final String normalized = position.toUpperCase();
    if (normalized.contains('GK')) {
      return _scaledProgress(goals, 3);
    }
    if (normalized.contains('CB') ||
        normalized.contains('LB') ||
        normalized.contains('RB') ||
        normalized.contains('WB')) {
      return _scaledProgress(goals, 10);
    }
    if (normalized.contains('DM') ||
        normalized.contains('CM') ||
        normalized.contains('AM') ||
        normalized.contains('LM') ||
        normalized.contains('RM')) {
      return _scaledProgress(goals, 18);
    }
    return _scaledProgress(goals, 30);
  }

  double _assistProgress(String position, int assists) {
    final String normalized = position.toUpperCase();
    if (normalized.contains('GK')) {
      return _scaledProgress(assists, 3);
    }
    if (normalized.contains('DM') ||
        normalized.contains('CM') ||
        normalized.contains('AM') ||
        normalized.contains('LM') ||
        normalized.contains('RM')) {
      return _scaledProgress(assists, 18);
    }
    return _scaledProgress(assists, 14);
  }

  double _minutesProgress(int minutes) => _scaledProgress(minutes, 4200);

  double _scaledProgress(int value, int ceiling) {
    if (ceiling <= 0) {
      return 0;
    }
    return (value / ceiling).clamp(0, 1).toDouble();
  }
}

class _HeroSection extends StatelessWidget {
  const _HeroSection({
    required this.avatar,
    required this.identity,
    required this.availability,
    required this.clubLabel,
    required this.isShortlisted,
    required this.onBack,
    required this.onToggleShortlist,
  });

  final PlayerAvatar avatar;
  final GteMarketPlayerIdentity identity;
  final GteLifecycleBadgeView availability;
  final String clubLabel;
  final bool isShortlisted;
  final VoidCallback onBack;
  final VoidCallback onToggleShortlist;

  @override
  Widget build(BuildContext context) {
    final double topInset = MediaQuery.of(context).padding.top;
    return SizedBox(
      height: 312 + topInset,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          _HeroMedia(identity: identity, avatar: avatar),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: <Color>[
                  Colors.black.withValues(alpha: 0.16),
                  Colors.black.withValues(alpha: 0.08),
                  Colors.black.withValues(alpha: 0.72),
                  Colors.black.withValues(alpha: 0.92),
                ],
                stops: const <double>[0, 0.28, 0.72, 1],
              ),
            ),
          ),
          Positioned(
            top: topInset + 14,
            left: 16,
            child: IconButton.filledTonal(
              onPressed: onBack,
              icon: const Icon(Icons.arrow_back_rounded),
            ),
          ),
          Positioned(
            top: topInset + 14,
            right: 16,
            child: IconButton.filledTonal(
              onPressed: onToggleShortlist,
              icon: Icon(
                isShortlisted ? Icons.star_rounded : Icons.star_border_rounded,
                color: isShortlisted ? GteShellTheme.accent : null,
              ),
            ),
          ),
          Positioned(
            left: 20,
            right: 20,
            bottom: 22,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    _HeroBadge(label: identity.position ?? 'Player'),
                    _HeroBadge(
                      label: availability.label,
                      backgroundColor:
                          availability.available
                              ? GteShellTheme.positive.withValues(alpha: 0.18)
                              : GteShellTheme.warning.withValues(alpha: 0.18),
                      borderColor:
                          availability.available
                              ? GteShellTheme.positive.withValues(alpha: 0.3)
                              : GteShellTheme.warning.withValues(alpha: 0.3),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  identity.playerName,
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    color: Colors.white,
                    fontSize: 38,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  clubLabel,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Colors.white.withValues(alpha: 0.86),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroMedia extends StatelessWidget {
  const _HeroMedia({required this.identity, required this.avatar});

  final GteMarketPlayerIdentity identity;
  final PlayerAvatar avatar;

  @override
  Widget build(BuildContext context) {
    final String? imageUrl = identity.imageUrl?.trim();
    if (imageUrl != null && imageUrl.isNotEmpty) {
      return Image.network(
        imageUrl,
        fit: BoxFit.cover,
        errorBuilder: (
          BuildContext context,
          Object error,
          StackTrace? stackTrace,
        ) {
          return _HeroAvatarFallback(avatar: avatar);
        },
      );
    }
    return _HeroAvatarFallback(avatar: avatar);
  }
}

class _HeroAvatarFallback extends StatelessWidget {
  const _HeroAvatarFallback({required this.avatar});

  final PlayerAvatar avatar;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFF20150E),
            Color(0xFF352213),
            Color(0xFF0E0A07),
          ],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Positioned(
            right: -40,
            top: -30,
            child: IgnorePointer(
              child: Container(
                width: 220,
                height: 220,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: GteShellTheme.accent.withValues(alpha: 0.08),
                ),
              ),
            ),
          ),
          Positioned(
            left: -20,
            bottom: -30,
            child: IgnorePointer(
              child: Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF8EE6C7).withValues(alpha: 0.08),
                ),
              ),
            ),
          ),
          Align(
            alignment: Alignment.center,
            child: PlayerMarketAvatar(
              avatar: avatar,
              size: 172,
              mode: AvatarMode.profile,
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickInfoStrip extends StatelessWidget {
  const _QuickInfoStrip({required this.items});

  final List<_QuickInfoItem> items;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      child: Wrap(
        spacing: 18,
        runSpacing: 14,
        children: items
            .map((_QuickInfoItem item) => _QuickInfoCell(item: item))
            .toList(growable: false),
      ),
    );
  }
}

class _TopStatStrip extends StatelessWidget {
  const _TopStatStrip({required this.cards});

  final List<_ProfileStatCardData> cards;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 700;
        if (stacked) {
          return Column(
            children: cards
                .map(
                  (_ProfileStatCardData card) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _ProfileStatCard(data: card),
                  ),
                )
                .toList(growable: false),
          );
        }
        return Row(
          children: cards
              .asMap()
              .entries
              .map((MapEntry<int, _ProfileStatCardData> entry) {
                return Expanded(
                  child: Padding(
                    padding: EdgeInsets.only(left: entry.key == 0 ? 0 : 12),
                    child: _ProfileStatCard(data: entry.value),
                  ),
                );
              })
              .toList(growable: false),
        );
      },
    );
  }
}

class _ActionBar extends StatelessWidget {
  const _ActionBar({
    required this.isScouted,
    required this.isShortlisted,
    required this.onScoutPlayer,
    required this.onToggleShortlist,
    required this.onContactAgent,
  });

  final bool isScouted;
  final bool isShortlisted;
  final VoidCallback onScoutPlayer;
  final VoidCallback onToggleShortlist;
  final VoidCallback onContactAgent;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 760;
        final List<Widget> buttons = <Widget>[
          FilledButton.icon(
            onPressed: onScoutPlayer,
            icon: Icon(isScouted ? Icons.radar_rounded : Icons.search_rounded),
            label: Text(isScouted ? 'Scouting' : 'Scout Player'),
          ),
          OutlinedButton.icon(
            onPressed: onToggleShortlist,
            icon: Icon(
              isShortlisted ? Icons.star_rounded : Icons.star_border_rounded,
            ),
            label: Text(isShortlisted ? 'Shortlisted' : 'Add to Shortlist'),
          ),
          OutlinedButton.icon(
            onPressed: onContactAgent,
            icon: const Icon(Icons.mail_outline_rounded),
            label: const Text('Contact Agent'),
          ),
        ];

        if (stacked) {
          return Column(
            children: buttons
                .map(
                  (Widget button) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: SizedBox(width: double.infinity, child: button),
                  ),
                )
                .toList(growable: false),
          );
        }

        return Row(
          children: buttons
              .asMap()
              .entries
              .map((MapEntry<int, Widget> entry) {
                return Expanded(
                  child: Padding(
                    padding: EdgeInsets.only(left: entry.key == 0 ? 0 : 12),
                    child: entry.value,
                  ),
                );
              })
              .toList(growable: false),
        );
      },
    );
  }
}

class _ProfileTabBar extends StatelessWidget {
  const _ProfileTabBar({required this.tabController});

  final TabController tabController;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Color.alphaBlend(
        Colors.black.withValues(alpha: 0.16),
        GteShellTheme.background,
      ),
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 10),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: TabBar(
          controller: tabController,
          dividerColor: Colors.transparent,
          indicator: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: GteShellTheme.accent.withValues(alpha: 0.14),
            border: Border.all(
              color: GteShellTheme.accent.withValues(alpha: 0.22),
            ),
          ),
          labelColor: GteShellTheme.textPrimary,
          unselectedLabelColor: GteShellTheme.textMuted,
          tabs: const <Widget>[
            Tab(text: 'Overview'),
            Tab(text: 'Stats'),
            Tab(text: 'Career'),
          ],
        ),
      ),
    );
  }
}

class _ProfileTabList extends StatelessWidget {
  const _ProfileTabList({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
      itemBuilder: (BuildContext context, int index) => children[index],
      separatorBuilder:
          (BuildContext context, int index) => const SizedBox(height: 16),
      itemCount: children.length,
    );
  }
}

class _ProfileSectionCard extends StatelessWidget {
  const _ProfileSectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class _StatMeterCard extends StatelessWidget {
  const _StatMeterCard({
    required this.label,
    required this.value,
    required this.progress,
    required this.accent,
    this.suffix,
  });

  final String label;
  final int value;
  final double progress;
  final Color accent;
  final String? suffix;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: GteSurfacePanel(
        padding: const EdgeInsets.all(16),
        accentColor: accent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 8),
            Text(
              suffix == null ? '$value' : '$value $suffix',
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(color: accent),
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 8,
                backgroundColor: Colors.white.withValues(alpha: 0.06),
                valueColor: AlwaysStoppedAnimation<Color>(accent),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SeasonProgressRow extends StatelessWidget {
  const _SeasonProgressRow({required this.season, required this.progress});

  final GteSeasonProgression season;
  final double progress;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.03),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  season.seasonLabel,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              if (season.averageRating != null)
                Text(
                  season.averageRating!.toStringAsFixed(1),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${season.appearances} matches  |  ${season.goals} goals  |  ${season.assists} assists  |  ${season.minutes} min',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 7,
              backgroundColor: Colors.white.withValues(alpha: 0.06),
              valueColor: const AlwaysStoppedAnimation<Color>(
                GteShellTheme.accent,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CareerTimelineItem extends StatelessWidget {
  const _CareerTimelineItem({required this.item, required this.isLast});

  final GteCareerEntry item;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SizedBox(
          width: 86,
          child: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              item.seasonLabel,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ),
        SizedBox(
          width: 28,
          child: Column(
            children: <Widget>[
              Container(
                width: 14,
                height: 14,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: GteShellTheme.accent,
                  border: Border.all(
                    color: GteShellTheme.accentWarm.withValues(alpha: 0.5),
                    width: 3,
                  ),
                ),
              ),
              if (!isLast)
                Container(
                  width: 2,
                  height: 92,
                  color: Colors.white.withValues(alpha: 0.08),
                ),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                color: Colors.white.withValues(alpha: 0.03),
                border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    item.clubName,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  if (item.squadRole != null) ...<Widget>[
                    const SizedBox(height: 4),
                    Text(
                      item.squadRole!,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 10),
                  Text(
                    '${item.appearances} apps  |  ${item.goals} goals  |  ${item.assists} assists',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (item.notes != null &&
                      item.notes!.trim().isNotEmpty) ...<Widget>[
                    const SizedBox(height: 10),
                    Text(
                      item.notes!,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _HeroBadge extends StatelessWidget {
  const _HeroBadge({
    required this.label,
    this.backgroundColor,
    this.borderColor,
  });

  final String label;
  final Color? backgroundColor;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: backgroundColor ?? Colors.white.withValues(alpha: 0.14),
        border: Border.all(
          color: borderColor ?? Colors.white.withValues(alpha: 0.18),
        ),
      ),
      child: Text(
        label,
        style: Theme.of(
          context,
        ).textTheme.labelLarge?.copyWith(color: Colors.white),
      ),
    );
  }
}

class _TagChip extends StatelessWidget {
  const _TagChip({required this.label, this.positive = false});

  final String label;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        positive ? GteShellTheme.positive : GteShellTheme.textMuted;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: positive ? 0.14 : 0.08),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: positive ? GteShellTheme.textPrimary : accent,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _StatusNotice extends StatelessWidget {
  const _StatusNotice({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon, size: 18, color: GteShellTheme.warning),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(message, style: Theme.of(context).textTheme.bodySmall),
          ),
        ],
      ),
    );
  }
}

class _ProfileStatCard extends StatelessWidget {
  const _ProfileStatCard({required this.data});

  final _ProfileStatCardData data;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.all(16),
      accentColor: data.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(data.label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 8),
          Text(
            data.value,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(color: data.accent),
          ),
        ],
      ),
    );
  }
}

class _QuickInfoCell extends StatelessWidget {
  const _QuickInfoCell({required this.item});

  final _QuickInfoItem item;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 92),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(item.label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(item.value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _StickyTabBarDelegate extends SliverPersistentHeaderDelegate {
  const _StickyTabBarDelegate({required this.child});

  final Widget child;

  @override
  double get minExtent => 74;

  @override
  double get maxExtent => 74;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return child;
  }

  @override
  bool shouldRebuild(covariant _StickyTabBarDelegate oldDelegate) {
    return oldDelegate.child != child;
  }
}

class _QuickInfoItem {
  const _QuickInfoItem({required this.label, required this.value});

  final String label;
  final String value;
}

class _ProfileStatCardData {
  const _ProfileStatCardData({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;
}

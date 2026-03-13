import 'package:flutter/material.dart';

import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_formatters.dart';
import '../widgets/gte_metric_chip.dart';
import '../widgets/gte_order_detail_card.dart';
import '../widgets/gte_order_ticket_sheet.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gte_trend_strip.dart';
import '../widgets/gtex_branding.dart';

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
    extends State<GteExchangePlayerDetailScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.openPlayer(widget.playerId);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Player detail'),
          actions: <Widget>[
            IconButton(
              onPressed: () {
                _refreshSnapshot();
              },
              icon: const Icon(Icons.refresh),
              tooltip: 'Refresh player',
            ),
          ],
        ),
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            final GtePlayerMarketSnapshot? snapshot =
                widget.controller.selectedPlayer;
            final bool isExpectedPlayer =
                snapshot != null && snapshot.detail.playerId == widget.playerId;

            if (!isExpectedPlayer && widget.controller.isLoadingPlayer) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'TRADING FLOOR',
                  title: 'Loading player market intelligence',
                  message: 'Price formation, liquidity cues, and recent execution context are being assembled for this asset.',
                  icon: Icons.candlestick_chart,
                  accentColor: GteShellTheme.accent,
                  isLoading: true,
                ),
              );
            }

            if (!isExpectedPlayer) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Player unavailable',
                  message: widget.controller.playerError ??
                      'Unable to load this player.',
                  actionLabel: 'Retry',
                  onAction: () {
                    _refreshSnapshot();
                  },
                  icon: Icons.person_off,
                ),
              );
            }

            final GteOrderRecord? order =
                widget.controller.orderForPlayer(widget.playerId);
            return RefreshIndicator(
              onRefresh: _refreshSnapshot,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    if (widget.controller.isLoadingPlayer) ...<Widget>[
                      const LinearProgressIndicator(),
                      const SizedBox(height: 16),
                    ],
                    if (widget.controller.playerError != null) ...<Widget>[
                      _InlineNotice(
                        icon: Icons.warning_amber_rounded,
                        message:
                            'Some live market data failed to refresh. Showing the latest successful snapshot instead. ${widget.controller.playerError!}',
                      ),
                      const SizedBox(height: 20),
                    ],
                    _buildHero(context, snapshot, order),
                    const SizedBox(height: 20),
                    const GtexSectionHeader(
                      eyebrow: 'MARKET INTELLIGENCE',
                      title: 'Know what is model-led, quote-led, and actually executable.',
                      description: 'Player detail should read like an asset intelligence screen. These panels explain whether price confidence is real, fragile, or still forming.',
                      accent: GteShellTheme.accent,
                    ),
                    const SizedBox(height: 14),
                    _buildMarketEdge(context, snapshot),
                    if (snapshot.lifecycle != null) ...<Widget>[
                      const SizedBox(height: 20),
                      _buildLifecycleSurface(context, snapshot.lifecycle!),
                    ],
                    const SizedBox(height: 20),
                    const GtexSectionHeader(
                      eyebrow: 'PRICE FORMATION',
                      title: 'Read the quote, the history, and the visible depth together.',
                      description: 'The market lane stays compact but explicit. Sparse history, one-sided books, and indicative fills are called out instead of hidden.',
                      accent: GteShellTheme.accent,
                    ),
                    const SizedBox(height: 14),
                    _buildTicker(context, snapshot),
                    const SizedBox(height: 20),
                    _buildCandles(context, snapshot),
                    const SizedBox(height: 20),
                    _buildOrderBook(context, snapshot),
                    const SizedBox(height: 20),
                    if (widget.controller.orderError != null) ...<Widget>[
                      _InlineNotice(
                        icon: Icons.warning_amber_rounded,
                        message: widget.controller.orderError!,
                      ),
                      const SizedBox(height: 20),
                    ],
                    if (order != null)
                      GteOrderDetailCard(
                        order: order,
                        playerLabel: snapshot.detail.identity.playerName,
                        isRefreshing: widget.controller.isRefreshingOrder,
                        isCancelling: widget.controller.isCancellingOrder,
                        onRefresh: () {
                          _refreshOrder(order);
                        },
                        onCancel: () {
                          _cancelOrder(order);
                        },
                      )
                    else if (widget.controller.isAuthenticated)
                      GteStatePanel(
                        title: 'No orders for this player',
                        message:
                            'This player has no open or recent orders in the current session.',
                        actionLabel: 'Place order',
                        onAction: () {
                          _openTicket();
                        },
                        icon: Icons.add_chart_outlined,
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

  Widget _buildHero(
    BuildContext context,
    GtePlayerMarketSnapshot snapshot,
    GteOrderRecord? order,
  ) {
    final GteMarketPlayerIdentity identity = snapshot.detail.identity;
    final GteMarketPlayerValue value = snapshot.detail.value;
    final GteMarketPlayerTrend trend = snapshot.detail.trend;
    final GtePortfolioHolding? holding = _holdingFor(widget.playerId);
    final GteMarketPlayerMarketProfile marketProfile = snapshot.detail.marketProfile;
    final List<String> identityLine = <String>[
      if (identity.currentClubName != null) identity.currentClubName!,
      if (identity.nationality != null) identity.nationality!,
      if (identity.position != null) identity.position!,
      'Age ${identity.age}',
    ];

    return GteSurfacePanel(
      emphasized: true,
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
                    Text(identity.playerName,
                        style: Theme.of(context).textTheme.displaySmall),
                    const SizedBox(height: 8),
                    Text(
                      identityLine.join(' | '),
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    if (identity.currentCompetitionName != null) ...<Widget>[
                      const SizedBox(height: 6),
                      Text(
                        identity.currentCompetitionName!,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 16),
              FilledButton(
                onPressed: widget.controller.isAuthenticated
                    ? () {
                        _openTicket();
                      }
                    : widget.onRequireLogin,
                child: Text(
                  widget.controller.isAuthenticated
                      ? 'Place order'
                      : 'Sign in to trade',
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Current value',
                value: gteFormatCredits(value.currentValueCredits),
              ),
              GteMetricChip(
                label: 'Movement',
                value: gteFormatMovement(value.movementPct),
                positive: value.movementPct >= 0,
              ),
              GteMetricChip(
                label: 'Trend score',
                value: trend.trendScore.toStringAsFixed(1),
              ),
              GteMetricChip(
                label: 'Interest',
                value: trend.marketInterestScore.toString(),
              ),
              GteMetricChip(
                label: 'Liquidity',
                value: (marketProfile.liquidityBand ?? 'forming').toUpperCase(),
              ),
              GteMetricChip(
                label: 'Trust',
                value: marketProfile.tradeTrustScore?.toStringAsFixed(1) ?? '--',
              ),
              GteMetricChip(
                label: 'Reference',
                value: gteFormatNullableCredits(
                    snapshot.ticker.referencePrice ??
                        value.currentValueCredits),
              ),
              if (widget.controller.walletSummary != null)
                GteMetricChip(
                  label: 'Cash',
                  value: gteFormatCredits(
                      widget.controller.walletSummary!.availableBalance),
                ),
              if (holding != null)
                GteMetricChip(
                  label: 'Owned',
                  value: holding.quantity.toStringAsFixed(2),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: Colors.white.withValues(alpha: 0.03),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                _DetailSignalChip(
                  label: 'Executable zone',
                  value: marketProfile.quotedMarketPriceCredits == null ? 'Indicative only' : gteFormatNullableCredits(marketProfile.quotedMarketPriceCredits),
                  accent: GteShellTheme.accent,
                ),
                _DetailSignalChip(
                  label: 'Trusted trade',
                  value: gteFormatNullableCredits(marketProfile.trustedTradePriceCredits),
                  accent: GteShellTheme.accentWarm,
                ),
                _DetailSignalChip(
                  label: 'Holders',
                  value: marketProfile.holderCount?.toString() ?? '--',
                  accent: GteShellTheme.accentCapital,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            order == null
                ? (widget.controller.isAuthenticated
                    ? 'No active order for this player yet. Use the ticket when the pricing stack and visible depth line up with your conviction.'
                    : 'Sign in to place, track, and cancel orders once the pricing stack looks good enough to trust.')
                : 'Latest order is ${gteFormatOrderStatus(order.status.name)} for ${order.quantity.toStringAsFixed(2)} units, with the execution story preserved below.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }

  Widget _buildMarketEdge(BuildContext context, GtePlayerMarketSnapshot snapshot) {
    final GteMarketPlayerMarketProfile profile = snapshot.detail.marketProfile;
    final GteMarketPlayerValue value = snapshot.detail.value;
    final List<Widget> cards = <Widget>[
      _MarketEdgeCard(
        title: 'Pricing stack',
        body: 'Separate indicative values from executable prices so the user can tell the difference between model confidence and tradable reality.',
        pills: <Widget>[
          GteMetricChip(label: 'Current', value: gteFormatCredits(value.currentValueCredits)),
          GteMetricChip(label: 'Football truth', value: gteFormatNullableCredits(value.footballTruthValueCredits)),
          GteMetricChip(label: 'Signal value', value: gteFormatNullableCredits(value.marketSignalValueCredits)),
        ],
      ),
      _MarketEdgeCard(
        title: 'Liquidity map',
        body: profile.quotedMarketPriceCredits == null
            ? 'The book is still forming. Treat this as a scouting screen until executable prices appear.'
            : 'Executable prices are visible. Use the ticket to compare quote quality with your available balance.',
        pills: <Widget>[
          GteMetricChip(label: 'Band', value: (profile.liquidityBand ?? 'forming').toUpperCase()),
          GteMetricChip(label: 'Supply', value: (profile.supplyTier ?? 'emerging').toUpperCase()),
          GteMetricChip(label: 'Top 3 share', value: profile.top3HolderSharePct == null ? '--' : '${profile.top3HolderSharePct!.toStringAsFixed(0)}%'),
        ],
      ),
      _MarketEdgeCard(
        title: 'Trading note',
        body: profile.tradeTrustScore != null && profile.tradeTrustScore! >= 7
            ? 'Trust is healthy enough for cleaner execution cues.'
            : 'Trust is still developing. Check spread, visible depth, and order book balance before stepping in.',
        pills: <Widget>[
          GteMetricChip(label: 'Trust score', value: profile.tradeTrustScore?.toStringAsFixed(1) ?? '--'),
          GteMetricChip(label: 'Snapshot mark', value: gteFormatNullableCredits(profile.snapshotMarketPriceCredits)),
          GteMetricChip(label: 'Published card', value: gteFormatNullableCredits(value.publishedCardValueCredits)),
        ],
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text('Market edge', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text(
          'This layer explains whether the displayed price is model-led, quote-led, or genuinely executable.',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 14),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool stacked = constraints.maxWidth < 920;
            if (stacked) {
              return Column(
                children: cards
                    .map((Widget card) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: card,
                        ))
                    .toList(growable: false),
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                for (int index = 0; index < cards.length; index++) ...<Widget>[
                  Expanded(child: cards[index]),
                  if (index != cards.length - 1) const SizedBox(width: 12),
                ],
              ],
            );
          },
        ),
      ],
    );
  }



  Widget _buildLifecycleSurface(
    BuildContext context,
    GtePlayerLifecycleSnapshot lifecycle,
  ) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Lifecycle snapshot', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GteMetricChip(
                label: 'Availability',
                value: lifecycle.availabilityBadge.label,
                positive: lifecycle.availabilityBadge.available,
              ),
              if (lifecycle.contractBadge != null)
                GteMetricChip(
                  label: 'Contract',
                  value: lifecycle.contractBadge!.label,
                  positive: true,
                ),
              GteMetricChip(
                label: 'Transfer',
                value: lifecycle.transferStatus.eligible ? 'Eligible' : 'Locked',
                positive: lifecycle.transferStatus.eligible,
              ),
            ],
          ),
          if (lifecycle.recentEvents.isNotEmpty) ...<Widget>[
            const SizedBox(height: 16),
            Text('Recent lifecycle events', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...lifecycle.recentEvents.take(3).map((GteLifecycleEventItem event) {
              final String dateLabel = event.occurredOn == null
                  ? ''
                  : '${event.occurredOn!.year}-${event.occurredOn!.month.toString().padLeft(2, '0')}-${event.occurredOn!.day.toString().padLeft(2, '0')}';
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Padding(
                      padding: EdgeInsets.only(top: 3),
                      child: Icon(Icons.timeline_outlined, size: 16),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        dateLabel.isEmpty ? event.summary : '$dateLabel · ${event.summary}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ],
      ),
    );
  }

  Widget _buildTicker(BuildContext context, GtePlayerMarketSnapshot snapshot) {
    final bool hasLiveQuote = snapshot.ticker.lastPrice != null ||
        snapshot.ticker.bestBid != null ||
        snapshot.ticker.bestAsk != null ||
        snapshot.ticker.referencePrice != null;
    final bool hasThinQuote =
        snapshot.ticker.bestBid == null || snapshot.ticker.bestAsk == null;

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Ticker', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'Falls back to reference values when the live quote is sparse.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          if (!hasLiveQuote)
            const GteStatePanel(
              title: 'Quote still forming',
              message:
                  'No last trade, bid, or ask is available yet. Pull to refresh and try again.',
              icon: Icons.show_chart_outlined,
            )
          else
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GteMetricChip(
                  label: 'Last',
                  value: gteFormatNullableCredits(snapshot.ticker.lastPrice),
                ),
                GteMetricChip(
                  label: 'Best bid',
                  value: gteFormatNullableCredits(snapshot.ticker.bestBid),
                ),
                GteMetricChip(
                  label: 'Best ask',
                  value: gteFormatNullableCredits(snapshot.ticker.bestAsk),
                ),
                GteMetricChip(
                  label: 'Mid',
                  value: gteFormatNullableCredits(snapshot.ticker.midPrice),
                ),
                GteMetricChip(
                  label: 'Spread',
                  value: gteFormatNullableCredits(snapshot.ticker.spread),
                ),
                GteMetricChip(
                  label: 'Day change',
                  value:
                      gteFormatMovement(snapshot.ticker.dayChangePercent / 100),
                  positive: snapshot.ticker.dayChangePercent >= 0,
                ),
                GteMetricChip(
                  label: '24h volume',
                  value: snapshot.ticker.volume24h.toStringAsFixed(1),
                ),
              ],
            ),
          if (hasLiveQuote && hasThinQuote) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'One side of the quote is empty, so reference pricing is filling the gaps.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCandles(BuildContext context, GtePlayerMarketSnapshot snapshot) {
    final List<GteMarketCandle> candles = snapshot.candles.candles;
    final List<TrendPoint> points = candles
        .map(
          (GteMarketCandle candle) => TrendPoint(
            label: _labelForCandle(candle.timestamp, snapshot.candles.interval),
            value: candle.close,
          ),
        )
        .toList(growable: false);

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text('Candles',
                    style: Theme.of(context).textTheme.headlineSmall),
              ),
              Flexible(
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.end,
                  children: <String>['1m', '5m', '15m', '1h', '1d']
                      .map(
                        (String interval) => ChoiceChip(
                          label: Text(interval),
                          selected: interval ==
                              widget.controller.selectedCandleInterval,
                          onSelected: (bool selected) {
                            if (selected) {
                              widget.controller.changeCandleInterval(interval);
                            }
                          },
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (candles.isEmpty)
            const GteStatePanel(
              title: 'No candle history yet',
              message:
                  'This player has not produced enough market history for the selected interval.',
              icon: Icons.timeline_outlined,
            )
          else if (candles.length == 1) ...<Widget>[
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GteMetricChip(
                  label: 'Only close',
                  value: gteFormatCredits(candles.single.close),
                ),
                GteMetricChip(
                  label: 'Volume',
                  value: candles.single.volume.toStringAsFixed(1),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Only one candle is available for this interval, so the chart has been replaced by a single close value.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ] else ...<Widget>[
            GteTrendStrip(points: points),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                GteMetricChip(
                  label: 'Latest close',
                  value: gteFormatCredits(candles.last.close),
                ),
                GteMetricChip(
                  label: 'High',
                  value: gteFormatCredits(
                    candles
                        .map((GteMarketCandle candle) => candle.high)
                        .reduce(_maxValue),
                  ),
                ),
                GteMetricChip(
                  label: 'Low',
                  value: gteFormatCredits(
                    candles
                        .map((GteMarketCandle candle) => candle.low)
                        .reduce(_minValue),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Latest close ${gteFormatCredits(candles.last.close)} at ${gteFormatDateTime(candles.last.timestamp)}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (candles.length < 4) ...<Widget>[
              const SizedBox(height: 12),
              Text(
                'History is still sparse for this interval, so expect the chart to look thin until more ticks land.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildOrderBook(
      BuildContext context, GtePlayerMarketSnapshot snapshot) {
    final bool hasVisibleLevels = snapshot.orderBook.bids.isNotEmpty ||
        snapshot.orderBook.asks.isNotEmpty;
    final bool isOneSided =
        snapshot.orderBook.bids.isEmpty || snapshot.orderBook.asks.isEmpty;

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text('Order book',
                    style: Theme.of(context).textTheme.headlineSmall),
              ),
              Text(
                gteFormatDateTime(snapshot.orderBook.generatedAt),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Visible levels only. Empty sides are expected in a thin demo market.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (!hasVisibleLevels)
            const GteStatePanel(
              title: 'No visible levels',
              message:
                  'The book is currently empty on both sides for this player.',
              icon: Icons.import_export_outlined,
            )
          else ...<Widget>[
            if (isOneSided) ...<Widget>[
              const _InlineNotice(
                icon: Icons.compare_arrows,
                message:
                    'This player is trading as a thin market right now, so one side of the book is empty.',
              ),
              const SizedBox(height: 16),
            ],
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool isWide = constraints.maxWidth >= 760;
                final Widget bids = _OrderBookColumn(
                  title: 'Bids',
                  levels: snapshot.orderBook.bids,
                );
                final Widget asks = _OrderBookColumn(
                  title: 'Asks',
                  levels: snapshot.orderBook.asks,
                );
                if (isWide) {
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(child: bids),
                      const SizedBox(width: 20),
                      Expanded(child: asks),
                    ],
                  );
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    bids,
                    const SizedBox(height: 20),
                    asks,
                  ],
                );
              },
            ),
          ],
        ],
      ),
    );
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
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content:
            Text('Order accepted for ${snapshot.detail.identity.playerName}.'),
      ),
    );
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
    final GteOrderRecord? refreshed =
        await widget.controller.refreshOrder(order.id);
    if (!mounted || refreshed == null) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
            'Order status refreshed: ${gteFormatOrderStatus(refreshed.status.name)}.'),
      ),
    );
  }

  Future<void> _cancelOrder(GteOrderRecord order) async {
    final GteOrderRecord? cancelled =
        await widget.controller.cancelOrder(order.id);
    if (!mounted || cancelled == null) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
            'Order updated: ${gteFormatOrderStatus(cancelled.status.name)}.'),
      ),
    );
  }

  GtePortfolioHolding? _holdingFor(String playerId) {
    final GtePortfolioView? portfolio = widget.controller.portfolio;
    if (portfolio == null) {
      return null;
    }
    for (final GtePortfolioHolding holding in portfolio.holdings) {
      if (holding.playerId == playerId) {
        return holding;
      }
    }
    return null;
  }

  String _labelForCandle(DateTime timestamp, String interval) {
    if (interval == '1d') {
      return timestamp.day.toString().padLeft(2, '0');
    }
    return timestamp.hour.toString().padLeft(2, '0');
  }
}

class _DetailSignalChip extends StatelessWidget {
  const _DetailSignalChip({
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
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: accent.withValues(alpha: 0.08),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: accent)),
        ],
      ),
    );
  }
}

class _MarketEdgeCard extends StatelessWidget {
  const _MarketEdgeCard({
    required this.title,
    required this.body,
    required this.pills,
  });

  final String title;
  final String body;
  final List<Widget> pills;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(body, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 12),
          Wrap(spacing: 10, runSpacing: 10, children: pills),
        ],
      ),
    );
  }
}


class _OrderBookColumn extends StatelessWidget {
  const _OrderBookColumn({
    required this.title,
    required this.levels,
  });

  final String title;
  final List<GteOrderBookLevel> levels;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 14),
        if (levels.isEmpty)
          Text('No visible levels.',
              style: Theme.of(context).textTheme.bodyMedium)
        else ...<Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text('Price',
                    style: Theme.of(context).textTheme.bodyMedium),
              ),
              Expanded(
                child:
                    Text('Qty', style: Theme.of(context).textTheme.bodyMedium),
              ),
              Expanded(
                child: Text('Orders',
                    style: Theme.of(context).textTheme.bodyMedium),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...levels.map(
            (GteOrderBookLevel level) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: <Widget>[
                  Expanded(child: Text(gteFormatCredits(level.price))),
                  Expanded(child: Text(level.quantity.toStringAsFixed(2))),
                  Expanded(child: Text(level.orderCount.toString())),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({
    required this.icon,
    required this.message,
  });

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon),
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

double _maxValue(double left, double right) => left > right ? left : right;

double _minValue(double left, double right) => left < right ? left : right;

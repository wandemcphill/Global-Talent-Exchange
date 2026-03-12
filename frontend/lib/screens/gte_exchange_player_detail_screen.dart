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
              return const Center(child: CircularProgressIndicator());
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
          Text(
            order == null
                ? (widget.controller.isAuthenticated
                    ? 'No active order for this player yet.'
                    : 'Sign in to place, track, and cancel orders.')
                : 'Latest order is ${gteFormatOrderStatus(order.status.name)} for ${order.quantity.toStringAsFixed(2)} units.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
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

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
import 'gte_surface_panel.dart';

/// Ticket for trading player shares on the canonical System A market.
///
/// System A fills instantly against `PlayerShareMarket` at
/// `share_price_coin`, so there is no limit price, no order book and no
/// pending state: the trade either settles or it does not. The price shown
/// here is the tradable price in GTEX Coin - never a valuation.
class GteOrderTicketSheet extends StatefulWidget {
  const GteOrderTicketSheet({
    super.key,
    required this.controller,
    required this.snapshot,
  });

  final GteExchangeController controller;
  final GtePlayerMarketSnapshot snapshot;

  @override
  State<GteOrderTicketSheet> createState() => _GteOrderTicketSheetState();
}

class _GteOrderTicketSheetState extends State<GteOrderTicketSheet> {
  late final TextEditingController _quantityController;
  GteOrderSide _side = GteOrderSide.buy;
  String? _validationMessage;

  /// Idempotency key for the trade currently being attempted.
  ///
  /// Minted once when the user submits and deliberately *kept* while that
  /// attempt keeps failing, so tapping submit again after a timeout replays the
  /// original trade on the server rather than executing a second one. It is
  /// cleared only once a trade settles, or when the user changes what they are
  /// asking for - either of which makes the next submit a genuinely new trade.
  String? _pendingIdempotencyKey;
  int _tradeAttemptSequence = 0;

  @override
  void initState() {
    super.initState();
    _quantityController = TextEditingController(text: '1');
  }

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  /// The tradable price, or null when this player has no issued share market.
  double? get _sharePriceCoin =>
      widget.snapshot.detail.marketProfile.sharePriceCoin;

  bool get _marketAvailable {
    final double? price = _sharePriceCoin;
    return price != null && price > 0;
  }

  @override
  Widget build(BuildContext context) {
    final EdgeInsets viewInsets = MediaQuery.of(context).viewInsets;
    final GtePortfolioHolding? holding = _holdingForPlayer();
    final int? shareCount = int.tryParse(_quantityController.text.trim());
    final double? price = _sharePriceCoin;
    final double? estimatedTotal =
        shareCount != null && shareCount > 0 && price != null
            ? shareCount * price
            : null;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, 20, 20, viewInsets.bottom + 20),
        child: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            return SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Trade shares',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.snapshot.detail.identity.playerName,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  GteSurfacePanel(
                    padding: const EdgeInsets.all(16),
                    emphasized: true,
                    child: Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GteMetricChip(
                          label: 'Available GTEX Coin',
                          value: widget.controller.walletSummary == null
                              ? '--'
                              : gteFormatCredits(widget
                                  .controller.walletSummary!.availableBalance),
                        ),
                        GteMetricChip(
                          label: 'Shares owned',
                          value: _ownershipLabel(holding),
                        ),
                        GteMetricChip(
                          label: 'Share price',
                          value: price == null
                              ? 'Unavailable'
                              : gteFormatCredits(price),
                        ),
                        GteMetricChip(
                          label: 'Est. total',
                          value: estimatedTotal == null
                              ? '--'
                              : gteFormatCredits(estimatedTotal),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  SegmentedButton<GteOrderSide>(
                    segments: const <ButtonSegment<GteOrderSide>>[
                      ButtonSegment<GteOrderSide>(
                        value: GteOrderSide.buy,
                        label: Text('Buy'),
                      ),
                      ButtonSegment<GteOrderSide>(
                        value: GteOrderSide.sell,
                        label: Text('Sell'),
                      ),
                    ],
                    selected: <GteOrderSide>{_side},
                    onSelectionChanged: (Set<GteOrderSide> selection) {
                      setState(() {
                        _side = selection.first;
                        _validationMessage = null;
                        // A different side is a different trade.
                        _pendingIdempotencyKey = null;
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _side == GteOrderSide.buy
                        ? 'Buys settle immediately at the current share price. '
                            'The final amount charged is set by the server.'
                        : 'Sells settle immediately from the shares you own. '
                            'The final amount credited is set by the server.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _quantityController,
                    enabled: !widget.controller.isSubmittingOrder,
                    keyboardType: TextInputType.number,
                    inputFormatters: <TextInputFormatter>[
                      FilteringTextInputFormatter.digitsOnly,
                    ],
                    textInputAction: TextInputAction.done,
                    decoration: const InputDecoration(
                      labelText: 'Shares',
                      hintText: '1',
                      helperText: 'Whole shares only.',
                    ),
                    onSubmitted: (_) => _submit(),
                    onChanged: (_) {
                      setState(() {
                        _validationMessage = null;
                        // A different quantity is a different trade.
                        _pendingIdempotencyKey = null;
                      });
                    },
                  ),
                  if (!_marketAvailable) ...<Widget>[
                    const SizedBox(height: 12),
                    Text(
                      'This player has no share market yet, so there is no '
                      'price to trade at.',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  if (widget.controller.isSubmittingOrder) ...<Widget>[
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(),
                    const SizedBox(height: 8),
                    Text(
                      'Settling with the server...',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  if (_validationMessage != null ||
                      widget.controller.orderError != null) ...<Widget>[
                    const SizedBox(height: 12),
                    Text(
                      _validationMessage ?? widget.controller.orderError!,
                      style:
                          TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                    if (_validationMessage == null &&
                        _pendingIdempotencyKey != null) ...<Widget>[
                      const SizedBox(height: 4),
                      Text(
                        'Retrying is safe: it will not place a second trade.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                  const SizedBox(height: 20),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: OutlinedButton(
                          onPressed: widget.controller.isSubmittingOrder
                              ? null
                              : () => Navigator.of(context).pop(),
                          child: const Text('Close'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed: widget.controller.isSubmittingOrder ||
                                  !_marketAvailable
                              ? null
                              : _submit,
                          child: Text(_submitLabel()),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  String _submitLabel() {
    if (widget.controller.isSubmittingOrder) {
      return 'Settling...';
    }
    if (_pendingIdempotencyKey != null) {
      return 'Retry ${_side == GteOrderSide.buy ? 'buy' : 'sell'}';
    }
    return _side == GteOrderSide.buy ? 'Buy shares' : 'Sell shares';
  }

  /// Ownership must never be fabricated: a signed-out or unloaded portfolio is
  /// unknown, which is not the same as owning none.
  String _ownershipLabel(GtePortfolioHolding? holding) {
    if (!widget.controller.isAuthenticated) {
      return 'Sign in';
    }
    if (widget.controller.portfolio == null) {
      return 'Unavailable';
    }
    return holding == null ? '0' : holding.quantity.round().toString();
  }

  Future<void> _submit() async {
    final int? shareCount = int.tryParse(_quantityController.text.trim());
    if (shareCount == null || shareCount <= 0) {
      setState(() {
        _validationMessage = 'Enter a whole number of shares above zero.';
      });
      return;
    }
    if (!_marketAvailable) {
      setState(() {
        _validationMessage = 'This player has no tradable share market.';
      });
      return;
    }

    // Reuse the key while an attempt is outstanding so a retry after a timeout
    // replays the original trade; mint a new one for a genuinely new trade.
    final String idempotencyKey = _pendingIdempotencyKey ??=
        'gtex-trade-${widget.snapshot.detail.playerId}-'
            '${_side.name}-$shareCount-'
            '${DateTime.now().microsecondsSinceEpoch}-'
            '${++_tradeAttemptSequence}';

    setState(() {
      _validationMessage = null;
    });

    final GtePlayerShareTradeResult? result =
        await widget.controller.tradePlayerShares(
      playerId: widget.snapshot.detail.playerId,
      side: _side,
      shareCount: shareCount,
      idempotencyKey: idempotencyKey,
    );
    if (!mounted) {
      return;
    }
    if (result != null) {
      // Settled: the next submit is a new trade.
      _pendingIdempotencyKey = null;
      Navigator.of(context).pop(result);
    }
  }

  GtePortfolioHolding? _holdingForPlayer() {
    final GtePortfolioView? portfolio = widget.controller.portfolio;
    if (portfolio == null) {
      return null;
    }
    for (final GtePortfolioHolding holding in portfolio.holdings) {
      if (holding.playerId == widget.snapshot.detail.playerId) {
        return holding;
      }
    }
    return null;
  }
}

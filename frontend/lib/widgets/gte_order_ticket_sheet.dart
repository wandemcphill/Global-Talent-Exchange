import 'package:flutter/material.dart';

import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
import 'gte_surface_panel.dart';

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
  late final TextEditingController _priceController;
  GteOrderSide _side = GteOrderSide.buy;
  String? _validationMessage;

  @override
  void initState() {
    super.initState();
    _quantityController = TextEditingController(text: '1.0000');
    _priceController = TextEditingController(text: _defaultPriceFor(_side));
  }

  @override
  void dispose() {
    _quantityController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final EdgeInsets viewInsets = MediaQuery.of(context).viewInsets;
    final GtePortfolioHolding? holding = _holdingForPlayer();
    final double? quantity = double.tryParse(_quantityController.text.trim());
    final String rawPrice = _priceController.text.trim();
    final double? maxPrice =
        rawPrice.isEmpty ? null : double.tryParse(rawPrice);
    final double? referencePrice = _quoteFor(_side);
    final double? pricedAt = maxPrice ?? referencePrice;
    final double? estimatedNotional =
        quantity != null && quantity > 0 && pricedAt != null
            ? quantity * pricedAt
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
                  Text('Place order',
                      style: Theme.of(context).textTheme.headlineSmall),
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
                          label: 'Available cash',
                          value: widget.controller.walletSummary == null
                              ? '--'
                              : gteFormatCredits(widget
                                  .controller.walletSummary!.availableBalance),
                        ),
                        GteMetricChip(
                          label: 'Owned quantity',
                          value: holding == null
                              ? '0.00'
                              : holding.quantity.toStringAsFixed(2),
                        ),
                        GteMetricChip(
                          label: 'Reference',
                          value: gteFormatNullableCredits(referencePrice),
                        ),
                        GteMetricChip(
                          label: 'Est. notional',
                          value: estimatedNotional == null
                              ? '--'
                              : gteFormatCredits(estimatedNotional),
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
                        _priceController.text = _defaultPriceFor(_side);
                        _validationMessage = null;
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _side == GteOrderSide.buy
                        ? 'Buy orders reserve cash immediately when a max price is provided.'
                        : 'Sell orders rely on owned units already visible in the portfolio.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _quantityController,
                    enabled: !widget.controller.isSubmittingOrder,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Quantity',
                      hintText: '1.0000',
                    ),
                    onChanged: (_) {
                      setState(() {
                        _validationMessage = null;
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _priceController,
                    enabled: !widget.controller.isSubmittingOrder,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    textInputAction: TextInputAction.done,
                    decoration: const InputDecoration(
                      labelText: 'Max price (optional)',
                      hintText: '78.0000',
                      helperText:
                          'Leave blank to submit without a guard price.',
                    ),
                    onSubmitted: (_) => _submit(),
                    onChanged: (_) {
                      setState(() {
                        _validationMessage = null;
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Bid ${gteFormatNullableCredits(widget.snapshot.ticker.bestBid)} / Ask ${gteFormatNullableCredits(widget.snapshot.ticker.bestAsk)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (estimatedNotional != null) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      _side == GteOrderSide.buy
                          ? 'Estimated reserve ${gteFormatCredits(estimatedNotional)} at submission.'
                          : 'Estimated trade value ${gteFormatCredits(estimatedNotional)} at the current quote.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  if (widget.controller.isSubmittingOrder) ...<Widget>[
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(),
                  ],
                  if (_validationMessage != null ||
                      widget.controller.orderError != null) ...<Widget>[
                    const SizedBox(height: 12),
                    Text(
                      _validationMessage ?? widget.controller.orderError!,
                      style:
                          TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
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
                          onPressed: widget.controller.isSubmittingOrder
                              ? null
                              : () {
                                  _submit();
                                },
                          child: Text(
                            widget.controller.isSubmittingOrder
                                ? 'Submitting...'
                                : 'Submit order',
                          ),
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

  Future<void> _submit() async {
    final double? quantity = double.tryParse(_quantityController.text.trim());
    final String rawPrice = _priceController.text.trim();
    final double? maxPrice =
        rawPrice.isEmpty ? null : double.tryParse(rawPrice);
    if (quantity == null || quantity <= 0) {
      setState(() {
        _validationMessage = 'Enter a quantity above zero.';
      });
      return;
    }
    if (rawPrice.isNotEmpty && (maxPrice == null || maxPrice <= 0)) {
      setState(() {
        _validationMessage =
            'Enter a valid max price or leave the field blank.';
      });
      return;
    }

    setState(() {
      _validationMessage = null;
    });
    final GteOrderRecord? order = await widget.controller.placeOrder(
      playerId: widget.snapshot.detail.playerId,
      side: _side,
      quantity: quantity,
      maxPrice: maxPrice,
    );
    if (!mounted) {
      return;
    }
    if (order != null) {
      Navigator.of(context).pop(order);
    }
  }

  String _defaultPriceFor(GteOrderSide side) {
    final double? quote = _quoteFor(side);
    if (quote == null) {
      return '';
    }
    return quote.toStringAsFixed(4);
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

  double? _quoteFor(GteOrderSide side) {
    return side == GteOrderSide.buy
        ? widget.snapshot.ticker.bestAsk ??
            widget.snapshot.ticker.referencePrice
        : widget.snapshot.ticker.bestBid ??
            widget.snapshot.ticker.referencePrice;
  }
}

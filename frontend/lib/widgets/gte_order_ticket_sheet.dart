import 'package:flutter/material.dart';

import '../data/gte_exchange_models.dart';
import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';
import 'gte_formatters.dart';
import 'gte_metric_chip.dart';
import 'gte_surface_panel.dart';

/// Whole-player acquisition surface.
///
/// The legacy service/API still carries its historic share-count field for
/// backwards compatibility, but this screen never exposes quantity selection,
/// buy/sell switching, resale, price history, or trading terminology. Every
/// successful request asks the server to acquire exactly one unit.
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
  String? _validationMessage;
  String? _pendingIdempotencyKey;
  int _attemptSequence = 0;

  double? get _acquisitionPrice => widget.snapshot.detail.marketProfile.sharePriceCoin;

  bool get _marketAvailable {
    final double? price = _acquisitionPrice;
    return price != null && price > 0;
  }

  GtePortfolioHolding? _holdingForPlayer() {
    final GtePortfolioView? portfolio = widget.controller.portfolio;
    if (portfolio == null) return null;
    for (final GtePortfolioHolding holding in portfolio.holdings) {
      if (holding.playerId == widget.snapshot.detail.playerId) return holding;
    }
    return null;
  }

  bool get _alreadyOwned => (_holdingForPlayer()?.quantity ?? 0) > 0;

  @override
  Widget build(BuildContext context) {
    final EdgeInsets viewInsets = MediaQuery.of(context).viewInsets;
    final Size viewport = MediaQuery.sizeOf(context);
    final double maxBodyHeight =
        (viewport.height - viewInsets.bottom - 40).clamp(280.0, viewport.height);
    final double? price = _acquisitionPrice;
    final bool owned = _alreadyOwned;
    final bool canAcquire = _marketAvailable &&
        !owned &&
        widget.controller.isAuthenticated &&
        !widget.controller.isSubmittingOrder;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, 20, 20, viewInsets.bottom + 20),
        child: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            return ConstrainedBox(
              constraints: BoxConstraints(maxHeight: maxBodyHeight),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            widget.controller.isAuthenticated
                                ? 'Acquire player'
                                : 'Player acquisition',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            widget.snapshot.detail.identity.playerName,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'One complete player unit. Each account can acquire this player only once.',
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
                                  label: 'Acquisition price',
                                  value: price == null
                                      ? 'Unavailable'
                                      : '${gteFormatCredits(price)} GTX',
                                ),
                                GteMetricChip(
                                  label: 'Units owned',
                                  value: _ownershipLabel(_holdingForPlayer()),
                                ),
                                GteMetricChip(
                                  label: 'Available GTEX Coin',
                                  value: widget.controller.walletSummary == null
                                      ? '--'
                                      : gteFormatCredits(widget.controller
                                          .walletSummary!.availableBalance),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 14),
                          if (owned)
                            Text(
                              'You already own this player. A second unit cannot be acquired by the same account.',
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            )
                          else if (!widget.controller.isAuthenticated)
                            const Text('Sign in to acquire this player.')
                          else if (!_marketAvailable)
                            Text(
                              'This player is not currently available to acquire.',
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                          if (_validationMessage != null ||
                              widget.controller.orderError != null) ...<Widget>[
                            const SizedBox(height: 12),
                            Text(
                              _validationMessage ?? widget.controller.orderError!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                            if (_pendingIdempotencyKey != null) ...<Widget>[
                              const SizedBox(height: 4),
                              Text(
                                'Retrying the same request will not create a second acquisition.',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ],
                          if (widget.controller.isSubmittingOrder) ...<Widget>[
                            const SizedBox(height: 12),
                            const LinearProgressIndicator(),
                            const SizedBox(height: 8),
                            Text(
                              'Confirming acquisition...',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                          const SizedBox(height: 12),
                          Text(
                            'Player acquisitions are individual in-game assets. They are not fractional units and cannot be resold through a player trading market.',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ),
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
                          onPressed: canAcquire ? _submit : null,
                          child: Text(_submitLabel(owned)),
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

  String _submitLabel(bool owned) {
    if (widget.controller.isSubmittingOrder) return 'Confirming...';
    if (!widget.controller.isAuthenticated) return 'Sign in to acquire';
    if (owned) return 'Already acquired';
    if (!_marketAvailable) return 'Unavailable';
    if (_pendingIdempotencyKey != null) return 'Retry acquisition';
    return 'Acquire player';
  }

  String _ownershipLabel(GtePortfolioHolding? holding) {
    if (!widget.controller.isAuthenticated) return 'Sign in';
    if (widget.controller.portfolio == null) return 'Unavailable';
    return holding == null || holding.quantity <= 0 ? '0 of 1' : '1 of 1';
  }

  Future<void> _submit() async {
    if (_alreadyOwned) {
      setState(() {
        _validationMessage = 'You already own this player.';
      });
      return;
    }
    if (!_marketAvailable) {
      setState(() {
        _validationMessage = 'This player is not currently available to acquire.';
      });
      return;
    }

    final String idempotencyKey = _pendingIdempotencyKey ??=
        'gtex-acquire-${widget.snapshot.detail.playerId}-'
        '${DateTime.now().microsecondsSinceEpoch}-'
        '${++_attemptSequence}';

    setState(() {
      _validationMessage = null;
    });

    final GtePlayerShareTradeResult? result =
        await widget.controller.tradePlayerShares(
      playerId: widget.snapshot.detail.playerId,
      side: GteOrderSide.buy,
      shareCount: 1,
      idempotencyKey: idempotencyKey,
    );
    if (!mounted) return;
    if (result != null) {
      _pendingIdempotencyKey = null;
      Navigator.of(context).pop(result);
    }
  }
}

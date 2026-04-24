import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/regen_creation_api.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:url_launcher/url_launcher.dart';

class RequestSonScreen extends StatefulWidget {
  const RequestSonScreen({
    super.key,
    required this.apiBaseUrl,
    required this.backendMode,
    this.onOrderGenerated,
  });

  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final Future<void> Function()? onOrderGenerated;

  @override
  State<RequestSonScreen> createState() => _RequestSonScreenState();
}

class _RequestSonScreenState extends State<RequestSonScreen> {
  static const List<String> _positions = <String>[
    'GK',
    'CB',
    'RB',
    'LB',
    'DM',
    'CM',
    'AM',
    'RW',
    'LW',
    'ST',
  ];

  late final RegenCreationApi _api;
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();

  RequestSonOptions? _options;
  List<RegenCreationOrder> _orders = const <RegenCreationOrder>[];
  RegenCreationOrder? _activeOrder;
  String? _parentPlayerId;
  String? _position;
  String _paymentMethod = 'wallet';
  bool _loading = true;
  bool _submitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _api = RegenCreationApi.standard(
      baseUrl: widget.apiBaseUrl,
      mode: widget.backendMode,
    );
    _reload();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _countryController.dispose();
    super.dispose();
  }

  double get _quotedAmount {
    final RegenCreationPricing? pricing = _options?.pricing;
    if (pricing == null) {
      return 0;
    }
    double total = pricing.baseCostCoin;
    if (_nameController.text.trim().isNotEmpty) {
      total += pricing.nameCostCoin;
    }
    if (_countryController.text.trim().isNotEmpty ||
        (_position ?? '').trim().isNotEmpty) {
      total += pricing.customizationCostCoin;
    }
    return total;
  }

  Future<void> _reload({String? activeOrderId}) async {
    setState(() {
      _loading = _options == null;
      _errorMessage = null;
    });
    try {
      final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
        _api.fetchRequestSonOptions(),
        _api.listCreationOrders(limit: 12),
      ]);
      final RequestSonOptions options = payload[0] as RequestSonOptions;
      final List<RegenCreationOrder> orders =
          (payload[1] as RegenCreationOrderList).items;
      final RegenCreationOrder? selected = _pickOrder(
        orders,
        activeOrderId ?? _activeOrder?.id,
      );
      final RegenCreationOrder? hydrated =
          selected == null ? null : await _api.fetchCreationOrder(selected.id);
      if (!mounted) {
        return;
      }
      setState(() {
        _options = options;
        _orders = orders;
        _activeOrder = hydrated;
        _parentPlayerId = _resolveParent(options);
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = AppFeedback.messageFor(
          error,
          fallback: 'Unable to load request-son tools right now.',
        );
        _loading = false;
      });
    }
  }

  String? _resolveParent(RequestSonOptions options) {
    final String? current = _parentPlayerId;
    if (current != null &&
        options.eligibleParents.any(
          (RegenCreationParentPlayer parent) => parent.playerId == current,
        )) {
      return current;
    }
    return options.eligibleParents.isEmpty
        ? null
        : options.eligibleParents.first.playerId;
  }

  RegenCreationOrder? _pickOrder(
    List<RegenCreationOrder> orders,
    String? orderId,
  ) {
    if (orderId != null) {
      for (final RegenCreationOrder order in orders) {
        if (order.id == orderId) {
          return order;
        }
      }
    }
    return orders.isEmpty ? null : orders.first;
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      await action();
    } catch (error) {
      if (!mounted) {
        return;
      }
      final String message = AppFeedback.messageFor(
        error,
        fallback: 'Unable to complete this request right now.',
      );
      setState(() {
        _errorMessage = message;
      });
      AppFeedback.showError(context, error, fallback: message);
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  Future<void> _createOrder() async {
    final String? parentPlayerId = _parentPlayerId;
    if (parentPlayerId == null || parentPlayerId.isEmpty) {
      setState(() {
        _errorMessage = 'Select a parent player before you continue.';
      });
      return;
    }
    await _run(() async {
      RegenCreationOrder order = await _api.createRequestSonOrder(
        RequestSonOrderDraft(
          parentPlayerId: parentPlayerId,
          paymentMethod: _paymentMethod,
          requestedName: _nameController.text,
          requestedCountryCode: _countryController.text,
          requestedPosition: _position,
        ),
      );
      if (order.usesWallet) {
        order = await _api.payWithWallet(order.id);
        await widget.onOrderGenerated?.call();
        if (mounted) {
          AppFeedback.showSuccess(
            context,
            'Wallet payment settled and your requested son is live.',
          );
        }
      } else if (mounted) {
        AppFeedback.showSuccess(
          context,
          'Order created. Complete KoraPay, then return here to verify and generate.',
        );
      }
      await _reload(activeOrderId: order.id);
    });
  }

  Future<void> _payWithWallet() async {
    final RegenCreationOrder? order = _activeOrder;
    if (order == null) {
      return;
    }
    await _run(() async {
      final RegenCreationOrder paidOrder = await _api.payWithWallet(order.id);
      await widget.onOrderGenerated?.call();
      if (mounted) {
        AppFeedback.showSuccess(
          context,
          'Wallet payment settled and your requested son is live.',
        );
      }
      await _reload(activeOrderId: paidOrder.id);
    });
  }

  Future<void> _verifyAndGenerate() async {
    final RegenCreationOrder? order = _activeOrder;
    if (order == null) {
      return;
    }
    await _run(() async {
      final RegenCreationOrder generatedOrder = await _api.generateAfterPayment(
        order.id,
      );
      await widget.onOrderGenerated?.call();
      if (mounted) {
        AppFeedback.showSuccess(
          context,
          'Payment verified and your requested son is now live.',
        );
      }
      await _reload(activeOrderId: generatedOrder.id);
    });
  }

  Future<void> _openPaymentLink() async {
    final Uri? uri = Uri.tryParse(_activeOrder?.paymentLink ?? '');
    if (uri == null || !uri.hasScheme) {
      setState(() {
        _errorMessage = 'This order does not have a valid payment link yet.';
      });
      return;
    }
    final bool launched = await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    );
    if (!launched && mounted) {
      AppFeedback.showError(
        context,
        const GteApiException(
          type: GteApiErrorType.unavailable,
          message: 'Unable to open the payment page.',
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final RequestSonOptions? options = _options;
    return Scaffold(
      appBar: AppBar(title: const Text('Request a son')),
      body:
          _loading && options == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                onRefresh: () => _reload(activeOrderId: _activeOrder?.id),
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      if (_submitting) const LinearProgressIndicator(),
                      if (_submitting) const SizedBox(height: 14),
                      if (_errorMessage != null) ...<Widget>[
                        GteStatePanel(
                          title: 'Request-son flow needs attention',
                          message: _errorMessage!,
                          actionLabel: 'Reload',
                          onAction:
                              () => _reload(activeOrderId: _activeOrder?.id),
                          icon: Icons.priority_high_outlined,
                        ),
                        const SizedBox(height: 14),
                      ],
                      if (options == null)
                        GteStatePanel(
                          title: 'Request-son tools are unavailable',
                          message:
                              'The live backend did not return the request-son options yet.',
                          actionLabel: 'Retry',
                          onAction: _reload,
                          icon: Icons.person_search_outlined,
                        )
                      else ...<Widget>[
                        GteSurfacePanel(
                          emphasized: true,
                          accentColor: GteShellTheme.accentWarm,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                options.clubName,
                                style:
                                    Theme.of(context).textTheme.headlineSmall,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Create a payment-gated request-son order tied to a live parent player from your club.',
                                style: Theme.of(context).textTheme.bodyLarge,
                              ),
                              const SizedBox(height: 14),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: <Widget>[
                                  GteMetricChip(
                                    label: 'Eligible parents',
                                    value:
                                        options.eligibleParents.length
                                            .toString(),
                                  ),
                                  GteMetricChip(
                                    label: 'Base request',
                                    value: gteFormatCredits(
                                      options.pricing.baseCostCoin,
                                    ),
                                  ),
                                  GteMetricChip(
                                    label: 'Current quote',
                                    value: gteFormatCredits(_quotedAmount),
                                    positive: true,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        if (options.eligibleParents.isEmpty)
                          GteStatePanel(
                            title: 'No eligible parent players yet',
                            message:
                                'Request-son orders need a player already attached to your club or legacy source pool.',
                            actionLabel: 'Refresh squad',
                            onAction: _reload,
                            icon: Icons.groups_2_outlined,
                          )
                        else
                          GteSurfacePanel(
                            accentColor: GteShellTheme.accent,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                DropdownButtonFormField<String>(
                                  value: _parentPlayerId,
                                  decoration: const InputDecoration(
                                    labelText: 'Parent player',
                                    border: OutlineInputBorder(),
                                  ),
                                  items: options.eligibleParents
                                      .map((RegenCreationParentPlayer parent) {
                                        return DropdownMenuItem<String>(
                                          value: parent.playerId,
                                          child: Text(
                                            '${parent.fullName} / ${parent.position ?? 'N/A'} / ${parent.countryCode ?? '---'}',
                                          ),
                                        );
                                      })
                                      .toList(growable: false),
                                  onChanged:
                                      _submitting
                                          ? null
                                          : (String? value) => setState(
                                            () => _parentPlayerId = value,
                                          ),
                                ),
                                const SizedBox(height: 14),
                                TextField(
                                  controller: _nameController,
                                  enabled: !_submitting,
                                  textCapitalization: TextCapitalization.words,
                                  decoration: const InputDecoration(
                                    labelText: 'Requested name (optional)',
                                    border: OutlineInputBorder(),
                                  ),
                                  onChanged: (_) => setState(() {}),
                                ),
                                const SizedBox(height: 14),
                                Row(
                                  children: <Widget>[
                                    Expanded(
                                      child: TextField(
                                        controller: _countryController,
                                        enabled: !_submitting,
                                        maxLength: 8,
                                        textCapitalization:
                                            TextCapitalization.characters,
                                        decoration: const InputDecoration(
                                          labelText: 'Country code (optional)',
                                          border: OutlineInputBorder(),
                                          counterText: '',
                                        ),
                                        onChanged: (_) => setState(() {}),
                                      ),
                                    ),
                                    const SizedBox(width: 14),
                                    Expanded(
                                      child: DropdownButtonFormField<String?>(
                                        value: _position,
                                        decoration: const InputDecoration(
                                          labelText: 'Position (optional)',
                                          border: OutlineInputBorder(),
                                        ),
                                        items: <DropdownMenuItem<String?>>[
                                          const DropdownMenuItem<String?>(
                                            value: null,
                                            child: Text('Any position'),
                                          ),
                                          ..._positions.map(
                                            (String position) =>
                                                DropdownMenuItem<String?>(
                                                  value: position,
                                                  child: Text(position),
                                                ),
                                          ),
                                        ],
                                        onChanged:
                                            _submitting
                                                ? null
                                                : (String? value) => setState(
                                                  () => _position = value,
                                                ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 14),
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 10,
                                  children: <Widget>[
                                    ChoiceChip(
                                      label: const Text('Wallet'),
                                      selected: _paymentMethod == 'wallet',
                                      onSelected:
                                          _submitting
                                              ? null
                                              : (_) => setState(
                                                () => _paymentMethod = 'wallet',
                                              ),
                                    ),
                                    ChoiceChip(
                                      label: const Text('KoraPay'),
                                      selected: _paymentMethod == 'korapay',
                                      onSelected:
                                          _submitting
                                              ? null
                                              : (_) => setState(
                                                () =>
                                                    _paymentMethod = 'korapay',
                                              ),
                                    ),
                                    GteMetricChip(
                                      label: 'Quote',
                                      value: gteFormatCredits(_quotedAmount),
                                      positive: true,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                FilledButton.icon(
                                  onPressed: _submitting ? null : _createOrder,
                                  icon: Icon(
                                    _paymentMethod == 'wallet'
                                        ? Icons.wallet_outlined
                                        : Icons.open_in_new_outlined,
                                  ),
                                  label: Text(
                                    _paymentMethod == 'wallet'
                                        ? 'Create and pay with wallet'
                                        : 'Create KoraPay order',
                                  ),
                                ),
                              ],
                            ),
                          ),
                        if (_activeOrder != null) ...<Widget>[
                          const SizedBox(height: 16),
                          _buildOrderPanel(_activeOrder!),
                        ],
                        const SizedBox(height: 16),
                        _buildOrdersPanel(),
                      ],
                    ],
                  ),
                ),
              ),
    );
  }

  Widget _buildOrderPanel(RegenCreationOrder order) {
    final List<Widget> actions = <Widget>[
      FilledButton.tonalIcon(
        onPressed: _submitting ? null : () => _reload(activeOrderId: order.id),
        icon: const Icon(Icons.sync_outlined),
        label: const Text('Refresh status'),
      ),
    ];
    if (order.isPendingPayment && order.usesWallet) {
      actions.add(
        FilledButton.icon(
          onPressed: _submitting ? null : _payWithWallet,
          icon: const Icon(Icons.wallet_outlined),
          label: const Text('Pay with wallet'),
        ),
      );
    }
    if (order.usesKorapay && (order.paymentLink ?? '').isNotEmpty) {
      actions.add(
        FilledButton.tonalIcon(
          onPressed: _submitting ? null : _openPaymentLink,
          icon: const Icon(Icons.open_in_new_outlined),
          label: Text(order.mockPayment ? 'Open mock payment' : 'Open KoraPay'),
        ),
      );
    }
    if (!order.isGenerated && (order.usesKorapay || order.status == 'paid')) {
      actions.add(
        FilledButton.icon(
          onPressed: _submitting ? null : _verifyAndGenerate,
          icon: const Icon(Icons.verified_outlined),
          label: const Text('Verify and generate'),
        ),
      );
    }
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  'Latest request-son order',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              _statusPill(order.status),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Status',
                value: gteFormatOrderStatus(order.status),
              ),
              GteMetricChip(
                label: 'Payment',
                value: order.paymentMethod.toUpperCase(),
              ),
              GteMetricChip(
                label: 'Price',
                value: gteFormatCredits(order.amountCoin),
                positive: true,
              ),
              GteMetricChip(
                label: 'Created',
                value: gteFormatRelativeTime(order.createdAt),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(spacing: 10, runSpacing: 10, children: actions),
          if (order.generatedPlayer != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentWarm,
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  GteMetricChip(
                    label: 'Generated son',
                    value: order.generatedPlayer!.fullName,
                  ),
                  GteMetricChip(
                    label: 'Age',
                    value: order.generatedPlayer!.age.toString(),
                  ),
                  GteMetricChip(
                    label: 'Position',
                    value: order.generatedPlayer!.position,
                  ),
                  GteMetricChip(
                    label: 'Current',
                    value: order.generatedPlayer!.currentRating.toString(),
                  ),
                  GteMetricChip(
                    label: 'Potential',
                    value: order.generatedPlayer!.potentialRating.toString(),
                    positive: true,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildOrdersPanel() {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentWarm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Recent creation orders',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          if (_orders.isEmpty)
            const Text('No creation orders yet.')
          else
            Column(
              children: _orders
                  .map((RegenCreationOrder order) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(16),
                          onTap:
                              _submitting
                                  ? null
                                  : () => _reload(activeOrderId: order.id),
                          child: Ink(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color:
                                    order.id == _activeOrder?.id
                                        ? GteShellTheme.accent.withValues(
                                          alpha: 0.5,
                                        )
                                        : Colors.white.withValues(alpha: 0.12),
                              ),
                            ),
                            child: Row(
                              children: <Widget>[
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: <Widget>[
                                      Text(
                                        order.requestedName ??
                                            'Auto-generated identity',
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.titleMedium,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${order.paymentMethod.toUpperCase()} / ${gteFormatCredits(order.amountCoin)} / ${gteFormatRelativeTime(order.createdAt)}',
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.bodySmall,
                                      ),
                                    ],
                                  ),
                                ),
                                _statusPill(order.status),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  })
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }

  Widget _statusPill(String status) {
    final Color color = switch (status) {
      'generated' => const Color(0xFF2CB67D),
      'paid' => const Color(0xFFF5B400),
      'failed' => const Color(0xFFE45858),
      'refunded' => const Color(0xFF7F5AF0),
      _ => const Color(0xFF3DA9FC),
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.48)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(
          gteFormatOrderStatus(status),
          style: Theme.of(context).textTheme.labelLarge,
        ),
      ),
    );
  }
}

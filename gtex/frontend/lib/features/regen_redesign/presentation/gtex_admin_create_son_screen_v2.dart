import 'package:flutter/material.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_regen_repository.dart';
import '../models/gtex_regen_models.dart';

class GtexAdminCreateSonScreenV2 extends StatefulWidget {
  const GtexAdminCreateSonScreenV2({
    super.key,
    this.repository,
    this.initialData,
    this.embedded = false,
    this.allowFixtureData = false,
  });

  final GtexRegenRepository? repository;
  final GtexRegenWorldData? initialData;
  final bool embedded;
  final bool allowFixtureData;

  @override
  State<GtexAdminCreateSonScreenV2> createState() =>
      _GtexAdminCreateSonScreenV2State();
}

class _GtexAdminCreateSonScreenV2State
    extends State<GtexAdminCreateSonScreenV2> {
  late Future<List<RegenCreationOrder>> _ordersFuture;
  String _queue = 'Pending';
  String? _selectedOrderId;
  bool _mutating = false;
  String? _actionError;

  GtexRegenRepository? get _repository =>
      widget.repository ??
      (widget.allowFixtureData ? const DemoGtexRegenRepository() : null);

  @override
  void initState() {
    super.initState();
    _ordersFuture = _loadOrders();
  }

  Future<List<RegenCreationOrder>> _loadOrders() {
    final GtexRegenRepository? repository = _repository;
    if (repository == null) {
      return Future<List<RegenCreationOrder>>.error(
        StateError('Live admin Create-a-Son repository is required.'),
      );
    }
    return repository.listCreationOrders(limit: 40);
  }

  void _reload() {
    setState(() {
      _actionError = null;
      _ordersFuture = _loadOrders();
    });
  }

  String _queueLabelForStatus(String status) {
    switch (status) {
      case 'pending_payment':
      case 'payment_pending':
        return 'Pending';
      case 'paid':
      case 'generating':
      case 'paid_generating':
        return 'Ready to generate';
      case 'generated':
        return 'Generated';
      case 'failed':
      case 'refunded':
        return 'Failed';
      default:
        return status;
    }
  }

  bool _matchesQueue(RegenCreationOrder order) {
    switch (_queue) {
      case 'Pending':
        return order.status == 'pending_payment' ||
            order.status == 'payment_pending';
      case 'Ready to generate':
        return order.status == 'paid' ||
            order.status == 'generating' ||
            order.status == 'paid_generating';
      case 'Generated':
        return order.status == 'generated';
      case 'Failed':
        return order.status == 'failed' || order.status == 'refunded';
      default:
        return true;
    }
  }

  GtexParentPlayer? _parentFor(
    GtexRegenWorldData? data,
    RegenCreationOrder order,
  ) {
    if (data == null || order.parentPlayerId == null) {
      return null;
    }
    for (final GtexParentPlayer parent in data.parentPlayers) {
      if (parent.id == order.parentPlayerId) {
        return parent;
      }
    }
    return null;
  }

  Future<void> _pay(RegenCreationOrder order) async {
    final GtexRegenRepository? repository = _repository;
    if (repository == null || _mutating) {
      return;
    }
    setState(() {
      _mutating = true;
      _actionError = null;
    });
    try {
      final RegenCreationOrder updated = await repository.payCreationOrder(
        order.id,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _selectedOrderId = updated.id;
        _ordersFuture = _loadOrders();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _actionError = error.toString());
    } finally {
      if (mounted) {
        setState(() => _mutating = false);
      }
    }
  }

  Future<void> _generate(RegenCreationOrder order) async {
    final GtexRegenRepository? repository = _repository;
    if (repository == null || _mutating) {
      return;
    }
    setState(() {
      _mutating = true;
      _actionError = null;
    });
    try {
      final RegenCreationOrder updated = await repository.generateCreationOrder(
        order.id,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _selectedOrderId = updated.id;
        _queue = 'Generated';
        _ordersFuture = _loadOrders();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _actionError = error.toString());
    } finally {
      if (mounted) {
        setState(() => _mutating = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final Widget body = FutureBuilder<List<RegenCreationOrder>>(
      future: _ordersFuture,
      builder: (
        BuildContext context,
        AsyncSnapshot<List<RegenCreationOrder>> snapshot,
      ) {
        if (_repository == null) {
          return const GtexEmptyState(
            title: 'Admin Create-a-Son queue unavailable',
            message:
                'Sign in with an authenticated regen repository to load live Create-a-Son orders.',
            icon: Icons.admin_panel_settings_rounded,
            accent: GtexColors.cyan,
          );
        }
        if (snapshot.hasError) {
          return GtexEmptyState(
            title: 'Create-a-Son queue failed to load',
            message: snapshot.error.toString(),
            icon: Icons.warning_amber_rounded,
            accent: GtexColors.red,
            actionLabel: 'Retry queue',
            onAction: _reload,
          );
        }
        if (!snapshot.hasData) {
          return const Center(
            child: CircularProgressIndicator(color: GtexColors.cyan),
          );
        }

        final List<RegenCreationOrder> allOrders = snapshot.data!;
        final List<RegenCreationOrder> orders =
            allOrders.where(_matchesQueue).toList(growable: false);
        if (allOrders.isEmpty) {
          return const GtexEmptyState(
            title: 'No Create-a-Son orders yet',
            message:
                'Live request-son orders for this account will appear here once players submit them.',
            icon: Icons.inbox_outlined,
            accent: GtexColors.cyan,
          );
        }
        if (orders.isEmpty) {
          return GtexEmptyState(
            title: 'No $_queue orders',
            message:
                'Switch queue filters to inspect pending payment, paid, generated, or failed Create-a-Son orders.',
            icon: Icons.filter_alt_outlined,
            accent: GtexColors.cyan,
            actionLabel: 'Show pending',
            onAction: () => setState(() => _queue = 'Pending'),
          );
        }

        final String selectedId = _selectedOrderId ?? orders.first.id;
        final RegenCreationOrder selected = orders.firstWhere(
          (RegenCreationOrder order) => order.id == selectedId,
          orElse: () => orders.first,
        );
        final GtexParentPlayer? parent = _parentFor(
          widget.initialData,
          selected,
        );

        return GtexMasterDetailScaffold(
          title: 'Admin Create-a-Son',
          subtitle:
              'Operational queue for live Create-a-Son orders: payment, generation, and status inspection.',
          accent: GtexColors.cyan,
          leftPanel: _AdminQueuePanel(
            queue: _queue,
            orders: orders,
            selectedOrderId: selected.id,
            queueLabelForStatus: _queueLabelForStatus,
            onQueueChanged: (String value) => setState(() {
              _queue = value;
              _selectedOrderId = null;
            }),
            onOrderSelected:
                (String value) => setState(() => _selectedOrderId = value),
          ),
          detail: _AdminOrderDetail(
            order: selected,
            parent: parent,
            statusLabel: _queueLabelForStatus(selected.status),
          ),
          rightPanel: _AdminActionPanel(
            order: selected,
            mutating: _mutating,
            error: _actionError,
            onPay: selected.isPendingPayment ? () => _pay(selected) : null,
            onGenerate:
                selected.status == 'paid' || selected.status == 'generating'
                    ? () => _generate(selected)
                    : null,
            onRefresh: _reload,
          ),
          rightPanelWidth: 360,
        );
      },
    );
    if (widget.embedded) {
      return body;
    }
    return Scaffold(
      backgroundColor: GtexColors.stadiumBlack,
      body: SafeArea(child: body),
    );
  }
}

class _AdminQueuePanel extends StatelessWidget {
  const _AdminQueuePanel({
    required this.queue,
    required this.orders,
    required this.selectedOrderId,
    required this.queueLabelForStatus,
    required this.onQueueChanged,
    required this.onOrderSelected,
  });

  final String queue;
  final List<RegenCreationOrder> orders;
  final String selectedOrderId;
  final String Function(String status) queueLabelForStatus;
  final ValueChanged<String> onQueueChanged;
  final ValueChanged<String> onOrderSelected;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Queues',
          subtitle: 'Filter live Create-a-Son work without flooding the desk.',
          accent: GtexColors.cyan,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children:
                <String>[
                      'Pending',
                      'Ready to generate',
                      'Generated',
                      'Failed',
                    ]
                    .map((String item) {
                      return ChoiceChip(
                        label: Text(item),
                        selected: queue == item,
                        onSelected: (_) => onQueueChanged(item),
                      );
                    })
                    .toList(growable: false),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        ...orders.map((RegenCreationOrder order) {
          return GtexPanel(
            margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
            padding: const EdgeInsets.all(GtexSpacing.sm),
            accent: GtexColors.cyan,
            isSelected: order.id == selectedOrderId,
            onTap: () => onOrderSelected(order.id),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        order.requestedName?.trim().isNotEmpty == true
                            ? order.requestedName!.trim()
                            : 'Unnamed son request',
                        style: const TextStyle(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    GtexStatusChip(
                      label: queueLabelForStatus(order.status),
                      color: GtexColors.cyan,
                      compact: true,
                    ),
                  ],
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  '${order.amountCoin.toStringAsFixed(0)} coin • ${order.paymentMethod}',
                  style: const TextStyle(color: GtexColors.textMuted),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }
}

class _AdminOrderDetail extends StatelessWidget {
  const _AdminOrderDetail({
    required this.order,
    required this.parent,
    required this.statusLabel,
  });

  final RegenCreationOrder order;
  final GtexParentPlayer? parent;
  final String statusLabel;

  @override
  Widget build(BuildContext context) {
    final String title =
        order.requestedName?.trim().isNotEmpty == true
            ? order.requestedName!.trim()
            : 'Create-a-Son order';
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: title,
          subtitle: 'Order ${order.id}',
          accent: GtexColors.cyan,
          trailing: GtexStatusChip(label: statusLabel, color: GtexColors.cyan),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: GtexMetricTile(
                      label: 'Amount',
                      value: '${order.amountCoin.toStringAsFixed(0)} coin',
                      accent: GtexColors.gold,
                    ),
                  ),
                  const SizedBox(width: GtexSpacing.sm),
                  Expanded(
                    child: GtexMetricTile(
                      label: 'Payment',
                      value: order.paymentMethod,
                      accent: GtexColors.cyan,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              Text(
                'Parent player',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: GtexSpacing.xs),
              Text(
                parent == null
                    ? (order.parentPlayerId ?? 'Parent not attached')
                    : '${parent!.name} • ${parent!.clubName} • ${parent!.position} • ${parent!.countryCode}',
                style: const TextStyle(color: GtexColors.textSecondary),
              ),
              if (order.requestedPosition != null ||
                  order.requestedCountryCode != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.md),
                Text(
                  'Requested traits',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  <String>[
                    if (order.requestedPosition != null)
                      order.requestedPosition!,
                    if (order.requestedCountryCode != null)
                      order.requestedCountryCode!,
                  ].join(' • '),
                  style: const TextStyle(color: GtexColors.textSecondary),
                ),
              ],
              if (order.generatedPlayer != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.md),
                Text(
                  'Generated regen',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  '${order.generatedPlayer!.fullName} • ${order.generatedPlayer!.position} • OVR ${order.generatedPlayer!.currentRating}',
                  style: const TextStyle(color: GtexColors.textSecondary),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _AdminActionPanel extends StatelessWidget {
  const _AdminActionPanel({
    required this.order,
    required this.mutating,
    required this.error,
    required this.onPay,
    required this.onGenerate,
    required this.onRefresh,
  });

  final RegenCreationOrder order;
  final bool mutating;
  final String? error;
  final VoidCallback? onPay;
  final VoidCallback? onGenerate;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Order actions',
          subtitle:
              'Pay and generate use the audited Create-a-Son endpoints. There is no silent client-only approval path.',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (error != null) ...<Widget>[
                Text(
                  error!,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GtexColors.red,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: GtexSpacing.md),
              ],
              GtexActionButton(
                label: 'Pay with wallet',
                icon: Icons.account_balance_wallet_outlined,
                onPressed: mutating ? null : onPay,
                accent: GtexColors.gold,
                secondary: onPay == null,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Generate after payment',
                icon: Icons.auto_awesome_outlined,
                onPressed: mutating ? null : onGenerate,
                accent: GtexColors.pitch,
                secondary: onGenerate == null,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Refresh queue',
                icon: Icons.refresh,
                onPressed: mutating ? null : onRefresh,
                accent: GtexColors.cyan,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.md),
              Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexStatusChip(
                    label: order.status.toUpperCase(),
                    color: GtexColors.cyan,
                  ),
                  if (order.paidAt != null)
                    const GtexStatusChip(
                      label: 'PAID',
                      color: GtexColors.gold,
                    ),
                  if (order.generatedAt != null)
                    const GtexStatusChip(
                      label: 'GENERATED',
                      color: GtexColors.pitch,
                    ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Audit trail',
          accent: GtexColors.purple,
          child: Text(
            <String>[
              'Created ${order.createdAt.toIso8601String()}',
              if (order.paidAt != null)
                'Paid ${order.paidAt!.toIso8601String()}',
              if (order.generatedAt != null)
                'Generated ${order.generatedAt!.toIso8601String()}',
              if (order.paymentReference != null)
                'Reference ${order.paymentReference}',
            ].join('\n'),
            style: const TextStyle(color: GtexColors.textSecondary, height: 1.45),
          ),
        ),
      ],
    );
  }
}

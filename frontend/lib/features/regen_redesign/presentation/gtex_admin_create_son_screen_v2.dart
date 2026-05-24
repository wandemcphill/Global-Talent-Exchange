import 'package:flutter/material.dart';
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
  late Future<GtexRegenWorldData> _future;
  String _queue = 'Pending';
  String _selectedOrderId = 'order-001';

  GtexRegenRepository? get _repository =>
      widget.repository ??
      (widget.allowFixtureData ? const DemoGtexRegenRepository() : null);

  @override
  void initState() {
    super.initState();
    final GtexRegenRepository? repository = _repository;
    _future =
        widget.initialData == null
            ? repository == null
                ? Future<GtexRegenWorldData>.error(
                  StateError('Live admin Create-a-Son repository is required.'),
                )
                : repository.loadWorld()
            : Future<GtexRegenWorldData>.value(widget.initialData);
  }

  @override
  Widget build(BuildContext context) {
    final Widget body = FutureBuilder<GtexRegenWorldData>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<GtexRegenWorldData> snapshot,
      ) {
        final GtexRegenWorldData? data = snapshot.data;
        if (!widget.allowFixtureData) {
          return const GtexEmptyState(
            title: 'Admin Create-a-Son queue unavailable',
            message:
                'The live Create-a-Son order queue is not mounted for this surface yet.',
            icon: Icons.admin_panel_settings_rounded,
            accent: GtexColors.cyan,
          );
        }
        if (data == null) {
          return const Center(
            child: CircularProgressIndicator(color: GtexColors.cyan),
          );
        }
        final List<_AdminSonOrder> orders = _demoOrders(data);
        final _AdminSonOrder selected = orders.firstWhere(
          (_AdminSonOrder order) => order.id == _selectedOrderId,
          orElse: () => orders.first,
        );
        return GtexMasterDetailScaffold(
          title: 'Admin Create-a-Son',
          subtitle:
              'Operational queue for custom regen requests, special pricing, approvals, and manual generation control.',
          accent: GtexColors.cyan,
          leftPanel: _AdminQueuePanel(
            queue: _queue,
            orders: orders,
            selectedOrderId: _selectedOrderId,
            onQueueChanged: (String value) => setState(() => _queue = value),
            onOrderSelected:
                (String value) => setState(() => _selectedOrderId = value),
          ),
          detail: _AdminOrderDetail(order: selected),
          rightPanel: _AdminActionPanel(order: selected),
          rightPanelWidth: 360,
        );
      },
    );
    if (widget.embedded) return body;
    return Scaffold(
      backgroundColor: GtexColors.stadiumBlack,
      body: SafeArea(child: body),
    );
  }

  List<_AdminSonOrder> _demoOrders(GtexRegenWorldData data) {
    final List<GtexParentPlayer> parents = data.parentPlayers;
    return <_AdminSonOrder>[
      _AdminSonOrder(
        id: 'order-001',
        userName: 'Club Owner Ayo',
        parent: parents[0],
        status: 'Pending',
        requestedName: 'Adebayo Jr',
        specialRequest:
            'Explosive striker, high flair, future Nigeria captain.',
        amountCoin: 20500,
      ),
      _AdminSonOrder(
        id: 'order-002',
        userName: 'Paris Forge',
        parent: parents[1],
        status: 'Pricing Review',
        requestedName: 'Theo II',
        specialRequest:
            'Deep lying playmaker with high loyalty and calm personality.',
        amountCoin: 18000,
      ),
      _AdminSonOrder(
        id: 'order-003',
        userName: 'Rio Galaxy',
        parent: parents[2],
        status: 'Generated',
        requestedName: 'Lucasito Reyes',
        specialRequest: 'Left footed winger with showman trait.',
        amountCoin: 22500,
      ),
    ];
  }
}

class _AdminSonOrder {
  const _AdminSonOrder({
    required this.id,
    required this.userName,
    required this.parent,
    required this.status,
    required this.requestedName,
    required this.specialRequest,
    required this.amountCoin,
  });

  final String id;
  final String userName;
  final GtexParentPlayer parent;
  final String status;
  final String requestedName;
  final String specialRequest;
  final double amountCoin;
}

class _AdminQueuePanel extends StatelessWidget {
  const _AdminQueuePanel({
    required this.queue,
    required this.orders,
    required this.selectedOrderId,
    required this.onQueueChanged,
    required this.onOrderSelected,
  });

  final String queue;
  final List<_AdminSonOrder> orders;
  final String selectedOrderId;
  final ValueChanged<String> onQueueChanged;
  final ValueChanged<String> onOrderSelected;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Queues',
          subtitle: 'Filter operational work without flooding the screen.',
          accent: GtexColors.cyan,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <String>[
                  'Pending',
                  'Pricing Review',
                  'Generated',
                  'Rejected',
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
        ...orders.map((_AdminSonOrder order) {
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
                        order.requestedName,
                        style: const TextStyle(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    GtexStatusChip(
                      label: order.status,
                      color: GtexColors.cyan,
                      compact: true,
                    ),
                  ],
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  order.userName,
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
  const _AdminOrderDetail({required this.order});

  final _AdminSonOrder order;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: order.requestedName,
          subtitle: 'Requested by ${order.userName}',
          accent: GtexColors.cyan,
          trailing: GtexStatusChip(label: order.status, color: GtexColors.cyan),
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
                      label: 'Parent',
                      value: order.parent.rating.toString(),
                      delta: 'OVR',
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
                '${order.parent.name} • ${order.parent.clubName} • ${order.parent.position} • ${order.parent.countryCode}',
                style: const TextStyle(color: GtexColors.textSecondary),
              ),
              const SizedBox(height: GtexSpacing.md),
              Text(
                'Special request',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: GtexSpacing.xs),
              Text(
                order.specialRequest,
                style: const TextStyle(
                  color: GtexColors.textSecondary,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _AdminActionPanel extends StatelessWidget {
  const _AdminActionPanel({required this.order});

  final _AdminSonOrder order;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Admin actions',
          subtitle:
              'Order review is visible; generation mutations stay locked until audited admin endpoints are mounted.',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Order ${order.id} is ready for inspection with pricing, parent profile, and special request context. Approval, price adjustment, clarification, and rejection actions are intentionally read-only in this shell until the backend review adapter is mounted.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GtexColors.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: GtexSpacing.md),
              const Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexStatusChip(label: 'READ ONLY', color: GtexColors.cyan),
                  GtexStatusChip(
                    label: 'PRICING READY',
                    color: GtexColors.gold,
                  ),
                  GtexStatusChip(
                    label: 'REVIEW ENDPOINT LOCKED',
                    color: GtexColors.red,
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
          child: const Text(
            'Payment received → pricing checked → awaiting generation approval.',
            style: TextStyle(color: GtexColors.textSecondary),
          ),
        ),
      ],
    );
  }
}

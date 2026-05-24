import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_regen_repository.dart';
import '../models/gtex_regen_models.dart';

class GtexCreateSonScreenV2 extends StatefulWidget {
  const GtexCreateSonScreenV2({
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
  State<GtexCreateSonScreenV2> createState() => _GtexCreateSonScreenV2State();
}

class _GtexCreateSonScreenV2State extends State<GtexCreateSonScreenV2> {
  late Future<GtexRegenWorldData> _future;
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _specialController = TextEditingController();
  String? _parentPlayerId;
  String _position = 'ST';
  String _paymentMethod = 'wallet';
  GtexCreateSonOrder? _createdOrder;
  bool _submitting = false;

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
                  StateError('Live Create-a-Son repository is required.'),
                )
                : repository.loadWorld()
            : Future<GtexRegenWorldData>.value(widget.initialData);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _countryController.dispose();
    _specialController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final Widget body = FutureBuilder<GtexRegenWorldData>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<GtexRegenWorldData> snapshot,
      ) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(
            child: CircularProgressIndicator(color: GtexColors.gold),
          );
        }
        if (!snapshot.hasData) {
          return const GtexEmptyState(
            title: 'Create-a-Son unavailable',
            message: 'The live Create-a-Son flow could not load right now.',
            icon: Icons.family_restroom,
            accent: GtexColors.gold,
          );
        }
        final GtexRegenWorldData data = snapshot.data!;
        _parentPlayerId ??=
            data.parentPlayers.isNotEmpty ? data.parentPlayers.first.id : null;
        return GtexMasterDetailScaffold(
          title: 'Create a Son',
          subtitle:
              'A premium GTEX regen request flow tied to an eligible parent player, special requests, pricing, and payment.',
          accent: GtexColors.gold,
          leftPanel: _CreateSonLeftPanel(
            parents: data.parentPlayers,
            selectedParentId: _parentPlayerId,
            onParentChanged:
                (String id) => setState(() => _parentPlayerId = id),
          ),
          detail: _CreateSonForm(
            nameController: _nameController,
            countryController: _countryController,
            specialController: _specialController,
            position: _position,
            paymentMethod: _paymentMethod,
            positions: _positions,
            onPositionChanged:
                (String value) => setState(() => _position = value),
            onPaymentChanged:
                (String value) => setState(() => _paymentMethod = value),
            onChanged: () => setState(() {}),
          ),
          rightPanel: _CreateSonSummary(
            pricing: data.pricing,
            draft: _draft,
            createdOrder: _createdOrder,
            submitting: _submitting,
            onSubmit:
                _parentPlayerId == null || _repository == null
                    ? null
                    : () => _submit(data),
          ),
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

  GtexCreateSonDraft get _draft => GtexCreateSonDraft(
    parentPlayerId: _parentPlayerId ?? '',
    paymentMethod: _paymentMethod,
    requestedName: _nameController.text,
    requestedCountryCode: _countryController.text,
    requestedPosition: _position,
    specialRequest: _specialController.text,
  );

  Future<void> _submit(GtexRegenWorldData data) async {
    final GtexRegenRepository? repository = _repository;
    if (repository == null) {
      return;
    }
    setState(() => _submitting = true);
    try {
      final GtexCreateSonOrder order = await repository.createSon(_draft);
      if (!mounted) return;
      setState(() => _createdOrder = order);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Create-a-Son order ${order.status}')),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class _CreateSonLeftPanel extends StatelessWidget {
  const _CreateSonLeftPanel({
    required this.parents,
    required this.selectedParentId,
    required this.onParentChanged,
  });

  final List<GtexParentPlayer> parents;
  final String? selectedParentId;
  final ValueChanged<String> onParentChanged;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Eligible parents',
          subtitle:
              'Select the player line your custom regen will inherit from.',
          accent: GtexColors.gold,
          child: Column(
            children: parents
                .map((GtexParentPlayer parent) {
                  final bool selected = parent.id == selectedParentId;
                  return GtexPanel(
                    margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
                    padding: const EdgeInsets.all(GtexSpacing.sm),
                    accent: GtexColors.gold,
                    isSelected: selected,
                    onTap: () => onParentChanged(parent.id),
                    child: Row(
                      children: <Widget>[
                        CircleAvatar(
                          backgroundColor: GtexColors.gold.withValues(
                            alpha: 0.16,
                          ),
                          child: Text(
                            parent.position,
                            style: const TextStyle(
                              color: GtexColors.gold,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        const SizedBox(width: GtexSpacing.sm),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                parent.name,
                                style: const TextStyle(
                                  color: GtexColors.text,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              Text(
                                '${parent.clubName} • ${parent.countryCode} • ${parent.rating} OVR',
                                style: const TextStyle(
                                  color: GtexColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                })
                .toList(growable: false),
          ),
        ),
      ],
    );
  }
}

class _CreateSonForm extends StatelessWidget {
  const _CreateSonForm({
    required this.nameController,
    required this.countryController,
    required this.specialController,
    required this.position,
    required this.paymentMethod,
    required this.positions,
    required this.onPositionChanged,
    required this.onPaymentChanged,
    required this.onChanged,
  });

  final TextEditingController nameController;
  final TextEditingController countryController;
  final TextEditingController specialController;
  final String position;
  final String paymentMethod;
  final List<String> positions;
  final ValueChanged<String> onPositionChanged;
  final ValueChanged<String> onPaymentChanged;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: 'Custom regen request',
          subtitle:
              'These choices map to the current live request draft and pricing logic.',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _LabeledTextField(
                label: 'Requested name',
                hint: 'e.g. Kelechi Junior',
                controller: nameController,
                onChanged: onChanged,
              ),
              const SizedBox(height: GtexSpacing.md),
              _LabeledTextField(
                label: 'Requested country code',
                hint: 'e.g. NGA',
                controller: countryController,
                onChanged: onChanged,
              ),
              const SizedBox(height: GtexSpacing.md),
              Text(
                'Preferred position',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: GtexSpacing.xs),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: positions
                    .map((String item) {
                      return ChoiceChip(
                        label: Text(item),
                        selected: position == item,
                        onSelected: (_) => onPositionChanged(item),
                        selectedColor: GtexColors.gold.withValues(alpha: 0.28),
                        backgroundColor: GtexColors.panelStrong,
                        labelStyle: TextStyle(
                          color:
                              position == item
                                  ? GtexColors.text
                                  : GtexColors.textSecondary,
                          fontWeight: FontWeight.w900,
                        ),
                      );
                    })
                    .toList(growable: false),
              ),
              const SizedBox(height: GtexSpacing.md),
              _LabeledTextField(
                label: 'Special request',
                hint: 'Personality, playing style, shirt number, story...',
                controller: specialController,
                onChanged: onChanged,
                maxLines: 5,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Payment method',
          subtitle:
              'Wallet is the fastest route; external payment can stay pending until verified.',
          accent: GtexColors.cyan,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              ChoiceChip(
                label: const Text('Wallet'),
                selected: paymentMethod == 'wallet',
                onSelected: (_) => onPaymentChanged('wallet'),
              ),
              ChoiceChip(
                label: const Text('External payment'),
                selected: paymentMethod == 'external',
                onSelected: (_) => onPaymentChanged('external'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _CreateSonSummary extends StatelessWidget {
  const _CreateSonSummary({
    required this.pricing,
    required this.draft,
    required this.createdOrder,
    required this.submitting,
    required this.onSubmit,
  });

  final GtexCreateSonPricing pricing;
  final GtexCreateSonDraft draft;
  final GtexCreateSonOrder? createdOrder;
  final bool submitting;
  final VoidCallback? onSubmit;

  @override
  Widget build(BuildContext context) {
    final double total = draft.estimateCost(pricing);
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Price quote',
          subtitle:
              'Visible before payment so the user understands every customization cost.',
          accent: GtexColors.gold,
          child: Column(
            children: <Widget>[
              _CostLine(
                label: 'Base Create-a-Son',
                amount: pricing.baseCostCoin,
              ),
              if ((draft.requestedName ?? '').trim().isNotEmpty)
                _CostLine(
                  label: 'Name customization',
                  amount: pricing.nameCustomizationCoin,
                ),
              if ((draft.requestedCountryCode ?? '').trim().isNotEmpty)
                _CostLine(
                  label: 'Nationality customization',
                  amount: pricing.nationalityCustomizationCoin,
                ),
              if ((draft.requestedPosition ?? '').trim().isNotEmpty)
                _CostLine(
                  label: 'Position customization',
                  amount: pricing.positionCustomizationCoin,
                ),
              if ((draft.specialRequest ?? '').trim().isNotEmpty)
                _CostLine(
                  label: 'Special request minimum',
                  amount: pricing.specialRequestMinimumCoin,
                ),
              const Divider(color: GtexColors.line),
              Row(
                children: <Widget>[
                  const Expanded(
                    child: Text(
                      'Total',
                      style: TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  Text(
                    '${total.toStringAsFixed(0)} coin',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: GtexColors.gold,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              GtexActionButton(
                label: submitting ? 'Submitting...' : 'Create order',
                icon: Icons.payments,
                accent: GtexColors.gold,
                onPressed: submitting ? null : onSubmit,
              ),
            ],
          ),
        ),
        if (createdOrder != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Latest order',
            subtitle: createdOrder!.createdAtLabel,
            accent: GtexColors.mint,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GtexStatusChip(
                  label: createdOrder!.status,
                  color: GtexColors.mint,
                ),
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  'Parent: ${createdOrder!.parentPlayerName}',
                  style: const TextStyle(color: GtexColors.textSecondary),
                ),
                Text(
                  'Amount: ${createdOrder!.amountCoin.toStringAsFixed(0)} coin',
                  style: const TextStyle(color: GtexColors.textSecondary),
                ),
                if (createdOrder!.generatedRegenName != null)
                  Text(
                    'Generated: ${createdOrder!.generatedRegenName}',
                    style: const TextStyle(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _LabeledTextField extends StatelessWidget {
  const _LabeledTextField({
    required this.label,
    required this.hint,
    required this.controller,
    required this.onChanged,
    this.maxLines = 1,
  });

  final String label;
  final String hint;
  final TextEditingController controller;
  final VoidCallback onChanged;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        TextField(
          controller: controller,
          maxLines: maxLines,
          onChanged: (_) => onChanged(),
          style: const TextStyle(
            color: GtexColors.text,
            fontWeight: FontWeight.w700,
          ),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: GtexColors.panelStrong,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
            ),
          ),
        ),
      ],
    );
  }
}

class _CostLine extends StatelessWidget {
  const _CostLine({required this.label, required this.amount});

  final String label;
  final double amount;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.xs),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Text(
            '${amount.toStringAsFixed(0)} coin',
            style: const TextStyle(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

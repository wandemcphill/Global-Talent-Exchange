import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/gift_economy_admin_models.dart';
import 'gift_economy_admin_controller.dart';

class GiftEconomyAdminScreen extends StatefulWidget {
  const GiftEconomyAdminScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.onOpenLogin,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final VoidCallback? onOpenLogin;

  @override
  State<GiftEconomyAdminScreen> createState() => _GiftEconomyAdminScreenState();
}

class _GiftEconomyAdminScreenState extends State<GiftEconomyAdminScreen> {
  late final GiftEconomyAdminController _controller;

  bool get _isAuthenticated => widget.accessToken?.trim().isNotEmpty == true;
  bool get _isAdmin => <String>{
    'admin',
    'super_admin',
  }.contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = GiftEconomyAdminController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    if (_isAdmin) {
      _load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!_isAdmin) {
      return;
    }
    await _controller.loadCatalog();
    await _controller.loadRules();
    await _controller.loadBurnEvents();
    await _controller.loadGiftAdminEvents();
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    await action();
    if (!mounted) {
      return;
    }
    final String? error = _controller.actionError;
    if (error != null && error.trim().isNotEmpty) {
      AppFeedback.showError(context, error);
    } else {
      AppFeedback.showSuccess(context, success);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAuthenticated) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Gift stabilizer')),
          body: Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Sign in required',
              message:
                  'Gift catalog, revenue-share rules, combo rules, and burn-event controls require an authenticated admin session.',
              actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
              onAction: widget.onOpenLogin,
              icon: Icons.lock_outline,
            ),
          ),
        ),
      );
    }
    if (!_isAdmin) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Gift stabilizer')),
          body: const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Admin permission required',
              message:
                  'Gift stabilizer controls are only exposed to admin roles.',
              icon: Icons.admin_panel_settings_outlined,
            ),
          ),
        ),
      );
    }

    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Gift stabilizer'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentAdmin,
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Gift economy stabilizer',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Catalog pricing, revenue-share rules, combo amplification, and burn-event visibility stay in the canonical admin lane.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Catalog',
                              value: _controller.catalog.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Revenue rules',
                              value:
                                  _controller.revenueShareRules.length
                                      .toString(),
                            ),
                            GteMetricChip(
                              label: 'Burn events',
                              value: _controller.burnEvents.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Award packs',
                              value:
                                  _controller.catalog
                                      .where(
                                        (GiftCatalogItem item) =>
                                            item.isAwardPack,
                                      )
                                      .length
                                      .toString(),
                            ),
                            GteMetricChip(
                              label: 'Gift events',
                              value: _controller.giftEvents.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Abuse flags',
                              value:
                                  _controller.giftAbuseFlags.length.toString(),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed: _upsertCatalog,
                              icon: const Icon(Icons.card_giftcard_outlined),
                              label: const Text('Catalog item'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: _upsertRevenueRule,
                              icon: const Icon(Icons.pie_chart_outline),
                              label: const Text('Revenue rule'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: _upsertComboRule,
                              icon: const Icon(Icons.auto_awesome_outlined),
                              label: const Text('Combo rule'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  _SimpleListCard(
                    title: 'Gift catalog',
                    lines: _controller.catalog
                        .map(
                          (GiftCatalogItem item) =>
                              '${item.displayName} | ${item.rarity} | ${gteFormatFanCoin(item.fancoinPrice)} | ${item.isAwardPack ? 'award pack' : 'standard'} | legal ${item.legalStatus}',
                        )
                        .toList(growable: false),
                    loading: _controller.isLoadingCatalog,
                    error: _controller.catalogError,
                  ),
                  const SizedBox(height: 18),
                  _GiftEventListCard(
                    title: 'Gift events',
                    events: _controller.giftEvents,
                    flags: const <GiftAbuseFlag>[],
                    loading: _controller.isLoadingGiftEvents,
                    error: _controller.giftEventsError,
                    onRefund:
                        _controller.isRefundingGiftEvent
                            ? null
                            : (GiftEvent event) => _run(
                              () => _controller.refundGiftEvent(event.id),
                              'Gift event refunded.',
                            ),
                  ),
                  const SizedBox(height: 18),
                  _GiftEventListCard(
                    title: 'Gift abuse flags',
                    events: const <GiftEvent>[],
                    flags: _controller.giftAbuseFlags,
                    loading: _controller.isLoadingGiftEvents,
                    error: _controller.giftEventsError,
                    onRefund: null,
                  ),
                  const SizedBox(height: 18),
                  _SimpleListCard(
                    title: 'Revenue share rules',
                    lines: _controller.revenueShareRules
                        .map(
                          (RevenueShareRule item) =>
                              '${item.title} | ${item.scope} | platform ${_formatBps(item.platformShareBps)} | creator ${_formatBps(item.creatorShareBps)} | recipient ${_formatBps(item.recipientShareBps ?? 0)} | burn ${_formatBps(item.burnBps)}',
                        )
                        .toList(growable: false),
                    loading: _controller.isLoadingRules,
                    error: _controller.rulesError,
                  ),
                  const SizedBox(height: 18),
                  _SimpleListCard(
                    title: 'Burn events',
                    lines: _controller.burnEvents
                        .map(
                          (EconomyBurnEvent item) =>
                              '${item.sourceType} | ${item.amount} ${item.unit} | ${item.reason}',
                        )
                        .toList(growable: false),
                    loading: _controller.isLoadingBurnEvents,
                    error: _controller.burnEventsError,
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Future<void> _upsertCatalog() async {
    await showGteFormSheet(
      context,
      title: 'Upsert gift catalog item',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'key', label: 'Key'),
        GteFormFieldSpec(key: 'name', label: 'Display name'),
        GteFormFieldSpec(key: 'fallback', label: 'Fallback display name'),
        GteFormFieldSpec(key: 'tier', label: 'Tier'),
        GteFormFieldSpec(key: 'rarity', label: 'Rarity'),
        GteFormFieldSpec(key: 'price', label: 'Fancoin price'),
        GteFormFieldSpec(key: 'animation', label: 'Animation key'),
        GteFormFieldSpec(key: 'legal', label: 'Legal status'),
        GteFormFieldSpec(key: 'award', label: 'Award pack? true/false'),
      ],
      onSubmit: (Map<String, String> values) async {
        final double? price = double.tryParse(values['price'] ?? '');
        if ((values['key'] ?? '').isEmpty ||
            (values['name'] ?? '').isEmpty ||
            (values['tier'] ?? '').isEmpty ||
            price == null) {
          AppFeedback.showError(context, 'Enter valid catalog values.');
          return false;
        }
        await _run(
          () => _controller.upsertCatalogItem(
            GiftCatalogItemUpsertRequest(
              key: values['key']!,
              displayName: values['name']!,
              fallbackDisplayName:
                  (values['fallback'] ?? '').trim().isEmpty
                      ? null
                      : values['fallback']!.trim(),
              tier: values['tier']!,
              rarity:
                  (values['rarity'] ?? '').trim().isEmpty
                      ? values['tier']!
                      : values['rarity']!.trim(),
              fancoinPrice: price,
              animationKey:
                  (values['animation'] ?? '').trim().isEmpty
                      ? null
                      : values['animation']!.trim(),
              legalStatus:
                  (values['legal'] ?? '').trim().isEmpty
                      ? 'safe'
                      : values['legal']!.trim(),
              isAwardPack:
                  (values['award'] ?? '').trim().toLowerCase() == 'true',
            ),
          ),
          'Catalog item saved.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _upsertRevenueRule() async {
    await showGteFormSheet(
      context,
      title: 'Upsert revenue rule',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'key', label: 'Rule key'),
        GteFormFieldSpec(key: 'scope', label: 'Scope'),
        GteFormFieldSpec(key: 'title', label: 'Title'),
        GteFormFieldSpec(key: 'platform', label: 'Platform bps'),
        GteFormFieldSpec(key: 'creator', label: 'Creator bps'),
        GteFormFieldSpec(key: 'recipient', label: 'Recipient bps'),
        GteFormFieldSpec(key: 'burn', label: 'Burn bps'),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? platform = int.tryParse(values['platform'] ?? '');
        final int? creator = int.tryParse(values['creator'] ?? '');
        final int? recipient =
            (values['recipient'] ?? '').trim().isEmpty
                ? null
                : int.tryParse(values['recipient'] ?? '');
        final int? burn =
            (values['burn'] ?? '').trim().isEmpty
                ? 0
                : int.tryParse(values['burn'] ?? '');
        if ((values['key'] ?? '').isEmpty ||
            (values['scope'] ?? '').isEmpty ||
            (values['title'] ?? '').isEmpty ||
            platform == null ||
            creator == null ||
            burn == null ||
            ((values['recipient'] ?? '').trim().isNotEmpty &&
                recipient == null)) {
          AppFeedback.showError(context, 'Enter valid revenue-rule values.');
          return false;
        }
        await _run(
          () => _controller.upsertRevenueShareRule(
            RevenueShareRuleUpsertRequest(
              ruleKey: values['key']!,
              scope: values['scope']!,
              title: values['title']!,
              platformShareBps: platform,
              creatorShareBps: creator,
              recipientShareBps: recipient,
              burnBps: burn,
            ),
          ),
          'Revenue rule saved.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _upsertComboRule() async {
    await showGteFormSheet(
      context,
      title: 'Upsert combo rule',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'key', label: 'Rule key'),
        GteFormFieldSpec(key: 'title', label: 'Title'),
        GteFormFieldSpec(key: 'count', label: 'Min combo count'),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? count = int.tryParse(values['count'] ?? '');
        if ((values['key'] ?? '').isEmpty ||
            (values['title'] ?? '').isEmpty ||
            count == null) {
          AppFeedback.showError(context, 'Enter valid combo-rule values.');
          return false;
        }
        await _run(
          () => _controller.upsertComboRule(
            GiftComboRuleUpsertRequest(
              ruleKey: values['key']!,
              title: values['title']!,
              minComboCount: count,
            ),
          ),
          'Combo rule saved.',
        );
        return _controller.actionError == null;
      },
    );
  }
}

String _formatBps(int bps) {
  return '${(bps / 100).toStringAsFixed(bps % 100 == 0 ? 0 : 2)}%';
}

class _GiftEventListCard extends StatelessWidget {
  const _GiftEventListCard({
    required this.title,
    required this.events,
    required this.flags,
    required this.loading,
    required this.error,
    required this.onRefund,
  });

  final String title;
  final List<GiftEvent> events;
  final List<GiftAbuseFlag> flags;
  final bool loading;
  final String? error;
  final ValueChanged<GiftEvent>? onRefund;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (loading && events.isEmpty && flags.isEmpty)
            const GteStatePanel(
              title: 'Loading',
              message: 'Gift moderation data is syncing.',
              icon: Icons.hourglass_bottom_outlined,
              isLoading: true,
            )
          else if (error != null && events.isEmpty && flags.isEmpty)
            GteStatePanel(
              title: 'Unavailable',
              message: error!,
              icon: Icons.error_outline,
            )
          else if (events.isEmpty && flags.isEmpty)
            const Text('No records available.')
          else ...<Widget>[
            ...events
                .take(6)
                .map(
                  (GiftEvent event) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            '${event.giftDisplayName} | ${event.rarity} | ${gteFormatFanCoin(event.grossAmount)} | ${event.status} | abuse ${event.abuseStatus}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                        if (onRefund != null && event.status != 'refunded')
                          TextButton.icon(
                            onPressed: () => onRefund!(event),
                            icon: const Icon(Icons.undo_outlined),
                            label: const Text('Refund'),
                          ),
                      ],
                    ),
                  ),
                ),
            ...flags
                .take(6)
                .map(
                  (GiftAbuseFlag flag) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      '${flag.flagType} | ${flag.severity} | ${flag.status} | ${flag.description}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}

class _SimpleListCard extends StatelessWidget {
  const _SimpleListCard({
    required this.title,
    required this.lines,
    required this.loading,
    required this.error,
  });

  final String title;
  final List<String> lines;
  final bool loading;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (loading && lines.isEmpty)
            const GteStatePanel(
              title: 'Loading',
              message: 'Admin data is syncing.',
              icon: Icons.hourglass_bottom_outlined,
              isLoading: true,
            )
          else if (error != null && lines.isEmpty)
            GteStatePanel(
              title: 'Unavailable',
              message: error!,
              icon: Icons.error_outline,
            )
          else if (lines.isEmpty)
            const Text('No records available.')
          else
            ...lines
                .take(6)
                .map(
                  (String line) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      line,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}

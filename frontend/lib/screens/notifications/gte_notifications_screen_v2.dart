import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_models.dart';
import '../../features/engagement_redesign/engagement_controller.dart';
import '../../features/engagement_redesign/engagement_models.dart';
import '../../features/engagement_redesign/engagement_widgets.dart';
import '../../features/global_search_redesign/global_search_models.dart';
import '../../features/launch_control_redesign/launch_control_feature_gate.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../support/gte_support_dispute_screens.dart';
import '../wallet/gte_deposit_history_screen.dart';
import '../wallet/gte_kyc_screen.dart';
import '../wallet/gte_withdrawal_flow_screen.dart';
import '../wallet/gtex_wallet_overview_screen_v2.dart';

class GteNotificationsScreenV2 extends StatefulWidget {
  const GteNotificationsScreenV2({
    super.key,
    this.controller,
    this.exchangeController,
    this.allowFixtureData = false,
  });

  final GtexEngagementController? controller;
  final GteExchangeController? exchangeController;
  final bool allowFixtureData;

  @override
  State<GteNotificationsScreenV2> createState() =>
      _GteNotificationsScreenV2State();
}

class _GteNotificationsScreenV2State extends State<GteNotificationsScreenV2> {
  late final GtexEngagementController _controller;
  final Map<String, GteNotification> _liveNotifications =
      <String, GteNotification>{};
  List<GtexNotificationItem> _items = const <GtexNotificationItem>[];
  GtexNotificationKind? _selectedKind;
  GtexNotificationItem? _selected;
  bool _isLoading = false;
  String? _errorMessage;

  bool get _usesLiveNotifications => widget.exchangeController != null;
  bool get _canUseFixtureData => widget.allowFixtureData;

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? GtexEngagementController();
    if (_usesLiveNotifications) {
      _loadLiveNotifications();
    } else if (_canUseFixtureData) {
      _setItems(_controller.loadDemoNotifications());
    } else {
      _errorMessage =
          'Live notifications require an authenticated exchange controller.';
    }
  }

  @override
  void didUpdateWidget(covariant GteNotificationsScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.exchangeController != widget.exchangeController) {
      if (_usesLiveNotifications) {
        _loadLiveNotifications();
      } else if (_canUseFixtureData) {
        _liveNotifications.clear();
        _setItems(_controller.loadDemoNotifications());
      } else {
        setState(() {
          _liveNotifications.clear();
          _items = const <GtexNotificationItem>[];
          _selected = null;
          _errorMessage =
              'Live notifications require an authenticated exchange controller.';
        });
      }
    }
  }

  Future<void> _loadLiveNotifications() async {
    final GteExchangeController? exchangeController = widget.exchangeController;
    if (exchangeController == null || _isLoading) {
      return;
    }
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final List<GteNotification> notifications =
          await exchangeController.api.listNotifications();
      if (!mounted) {
        return;
      }
      _liveNotifications
        ..clear()
        ..addEntries(
          notifications.map(
            (GteNotification notification) => MapEntry<String, GteNotification>(
              notification.notificationId,
              notification,
            ),
          ),
        );
      _setItems(
        notifications.map(_mapLiveNotification).toList(growable: false),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _setItems(List<GtexNotificationItem> nextItems) {
    final String? selectedId = _selected?.id;
    final GtexNotificationItem? preserved =
        selectedId == null
            ? null
            : nextItems.cast<GtexNotificationItem?>().firstWhere(
              (GtexNotificationItem? item) => item?.id == selectedId,
              orElse: () => null,
            );
    setState(() {
      _items = nextItems;
      _selected = preserved ?? (nextItems.isEmpty ? null : nextItems.first);
    });
  }

  Future<void> _markAllRead() async {
    final GteExchangeController? exchangeController = widget.exchangeController;
    if (exchangeController != null) {
      await exchangeController.api.markAllNotificationsRead();
      await _loadLiveNotifications();
      return;
    }
    if (_canUseFixtureData) {
      _setItems(
        _items
            .map((GtexNotificationItem item) => _copyItem(item, isRead: true))
            .toList(growable: false),
      );
    }
  }

  Future<void> _markSelectedRead() async {
    final GtexNotificationItem? selected = _selected;
    if (selected == null) {
      return;
    }
    final GteExchangeController? exchangeController = widget.exchangeController;
    if (exchangeController != null) {
      await exchangeController.api.markNotificationRead(selected.id);
      await _loadLiveNotifications();
      return;
    }
    if (_canUseFixtureData) {
      _setItems(
        _items
            .map(
              (GtexNotificationItem item) =>
                  item.id == selected.id ? _copyItem(item, isRead: true) : item,
            )
            .toList(growable: false),
      );
    }
  }

  Future<void> _openSelected() async {
    final GtexNotificationItem? selected = _selected;
    final GteExchangeController? exchangeController = widget.exchangeController;
    if (selected == null || exchangeController == null) {
      return;
    }
    final GteNotification? notification = _liveNotifications[selected.id];
    if (notification == null) {
      return;
    }
    if (!notification.isRead) {
      await exchangeController.api.markNotificationRead(
        notification.notificationId,
      );
      await _loadLiveNotifications();
    }
    if (!mounted) {
      return;
    }
    final String? deepLinkRoute = gtexNotificationDeepLinkRoute(
      notification,
      isAdmin: exchangeController.isAdmin,
    );
    if (deepLinkRoute != null) {
      final GtexFeatureGateDecision gate =
          await GtexLaunchControlFeatureGate.resolveRoutePath(
            route: deepLinkRoute,
            baseUrl: exchangeController.api.config.baseUrl,
            backendMode: exchangeController.api.config.mode,
            accessToken: exchangeController.accessToken,
            isAdmin: exchangeController.isAdmin,
          );
      if (!mounted) {
        return;
      }
      if (gate.blocked) {
        AppFeedback.showError(
          context,
          gate.message ??
              'This notification target is not available right now.',
        );
        return;
      }
      context.go(deepLinkRoute);
      return;
    }
    final String topic = (notification.topic ?? '').toLowerCase();
    final String resource = (notification.resourceId ?? '').toLowerCase();
    if (topic.contains('deposit') || resource.startsWith('deposit')) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) =>
                  GteDepositHistoryScreen(controller: exchangeController),
        ),
      );
      return;
    }
    if (topic.contains('withdrawal') ||
        topic.contains('payout') ||
        resource.startsWith('withdrawal') ||
        resource.startsWith('payout')) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) => GteWithdrawalEligibilityScreen(
                controller: exchangeController,
              ),
        ),
      );
      return;
    }
    if (topic.contains('kyc')) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) =>
                  GteKycScreen(controller: exchangeController),
        ),
      );
      return;
    }
    if (topic.contains('dispute')) {
      if (notification.resourceId != null) {
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder:
                (BuildContext context) => GteDisputeThreadScreen(
                  api: exchangeController.api,
                  disputeId: notification.resourceId!,
                ),
          ),
        );
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder:
              (BuildContext context) =>
                  GteDisputeHubScreen(controller: exchangeController),
        ),
      );
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                GtexWalletOverviewScreenV2(controller: exchangeController),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final List<GtexNotificationItem> visible =
        _selectedKind == null
            ? _items
            : _items
                .where(
                  (GtexNotificationItem item) => item.kind == _selectedKind,
                )
                .toList(growable: false);
    final GtexNotificationItem? selected =
        visible.contains(_selected)
            ? _selected
            : (visible.isEmpty ? null : visible.first);

    return GtexMasterDetailScaffold(
      title: 'GTEX Notifications',
      subtitle:
          'Market alerts, club activity, KYC, disputes, competitions and jackpot updates.',
      accent: GtexColors.cyan,
      mobileLeftTitle: 'Notifications',
      actions: <Widget>[
        GtexActionButton(
          label: _isLoading ? 'Syncing' : 'Mark all read',
          icon: Icons.done_all_outlined,
          onPressed: _isLoading ? null : _markAllRead,
          accent: GtexColors.cyan,
          secondary: true,
        ),
        GtexActionButton(
          label: 'Refresh',
          icon: Icons.refresh_outlined,
          onPressed:
              (_usesLiveNotifications || _canUseFixtureData) && !_isLoading
                  ? _loadLiveNotifications
                  : null,
          accent: GtexColors.pitch,
          secondary: true,
        ),
      ],
      leftPanel: _NotificationsLeftPanel(
        items: visible,
        selected: selected,
        selectedKind: _selectedKind,
        onKindChanged:
            (GtexNotificationKind? kind) =>
                setState(() => _selectedKind = kind),
        onSelected:
            (GtexNotificationItem item) => setState(() => _selected = item),
        isLoading: _isLoading,
        errorMessage: _errorMessage,
        onRetry: _loadLiveNotifications,
      ),
      detail:
          selected == null
              ? _NotificationsEmptyState(
                isLoading: _isLoading,
                errorMessage: _errorMessage,
                onRetry: _loadLiveNotifications,
              )
              : _NotificationDetail(item: selected),
      rightPanel:
          selected == null
              ? null
              : _NotificationActions(
                item: selected,
                onOpen: _usesLiveNotifications ? _openSelected : null,
                onMarkRead: _markSelectedRead,
              ),
    );
  }
}

String? gtexNotificationDeepLinkRoute(
  GteNotification notification, {
  required bool isAdmin,
}) {
  final String? rawRoute =
      _firstMetadataString(notification.metadata, const <String>[
        'deep_link_route',
        'deepLinkRoute',
        'deep_link',
        'deepLink',
        'action_route',
        'actionRoute',
        'route',
      ]);
  final String? candidate =
      rawRoute?.trim().isNotEmpty == true
          ? rawRoute!.trim()
          : _fallbackDeepLinkRoute(notification, isAdmin: isAdmin);
  final String trimmed = candidate?.trim() ?? '';
  if (trimmed.isEmpty) {
    return null;
  }
  final Uri? parsed = Uri.tryParse(trimmed);
  if (parsed != null && (parsed.hasScheme || parsed.hasAuthority)) {
    return null;
  }
  final String canonical = gtexCanonicalGlobalSearchRoute(
    trimmed,
    isAdmin: isAdmin,
  );
  if (canonical == '/app/home' && trimmed.toLowerCase().startsWith('/admin')) {
    return null;
  }
  return canonical;
}

String? _fallbackDeepLinkRoute(
  GteNotification notification, {
  required bool isAdmin,
}) {
  final String signal = _notificationSignal(notification);
  if (signal.isEmpty) {
    return null;
  }
  if (signal.contains('feature.flag') ||
      signal.contains('feature flag') ||
      signal.contains('kill_switch') ||
      signal.contains('kill switch') ||
      signal.contains('beta_access') ||
      signal.contains('beta access') ||
      signal.contains('launch control')) {
    return isAdmin ? '/admin/launch-control' : null;
  }
  if (signal.contains('operations.readiness') ||
      signal.contains('operations readiness') ||
      signal.contains('admin ops') ||
      signal.contains('risk ops') ||
      signal.contains('moderation')) {
    return isAdmin ? '/admin/trust-ops' : null;
  }
  if (signal.contains('coin_trader') ||
      signal.contains('coin trader') ||
      signal.contains('liquidity')) {
    return '/app/coin-traders';
  }
  if (signal.contains('card.') ||
      signal.contains('player card') ||
      signal.contains('pack opened') ||
      signal.contains('collectible')) {
    return '/player-cards';
  }
  if (signal.contains('transfer') ||
      signal.contains('offer') ||
      signal.contains('loan') ||
      signal.contains('swap') ||
      signal.contains('market listing')) {
    return '/app/market';
  }
  if (signal.contains('kyc') || signal.contains('verification')) {
    return '/kyc';
  }
  if (signal.contains('dispute') || signal.contains('evidence')) {
    return '/disputes';
  }
  if (signal.contains('wallet') ||
      signal.contains('escrow') ||
      signal.contains('payment') ||
      signal.contains('deposit') ||
      signal.contains('withdraw') ||
      signal.contains('payout') ||
      signal.contains('coins released')) {
    return '/app/wallet';
  }
  if (signal.contains('national.rental') ||
      signal.contains('national rental') ||
      signal.contains('national-team') ||
      signal.contains('national team')) {
    return '/national-team';
  }
  if (signal.contains('federation') ||
      signal.contains('sanction') ||
      signal.contains('governance vote')) {
    return '/world/federations';
  }
  if (signal.contains('award')) {
    return '/world/awards';
  }
  if (signal.contains('regen') ||
      signal.contains('newgen') ||
      signal.contains('academy prospect')) {
    return '/world/regens';
  }
  if (signal.contains('club') ||
      signal.contains('academy') ||
      signal.contains('staff') ||
      signal.contains('sponsor')) {
    return '/app/club';
  }
  if (signal.contains('prediction') ||
      signal.contains('fan war') ||
      signal.contains('fan_war') ||
      signal.contains('gift') ||
      signal.contains('social')) {
    return '/app/community';
  }
  if (signal.contains('broadcast.package') ||
      signal.contains('broadcast package')) {
    return '/broadcast/live';
  }
  if (signal.contains('clip') ||
      signal.contains('highlight') ||
      signal.contains('broadcast')) {
    return '/news';
  }
  if (signal.contains('ticket')) {
    return '/app/play';
  }
  if (signal.contains('competition') ||
      signal.contains('tournament') ||
      signal.contains('fixture') ||
      signal.contains('match')) {
    return '/app/play';
  }
  if (signal.contains('admin')) {
    return isAdmin ? '/admin/trust-ops' : null;
  }
  return null;
}

String _notificationSignal(GteNotification notification) {
  return <String?>[
    notification.topic,
    notification.templateKey,
    notification.resourceId,
    notification.fixtureId,
    notification.competitionId,
    notification.message,
    notification.metadata['event_key']?.toString(),
    notification.metadata['eventKey']?.toString(),
    notification.metadata['resource_type']?.toString(),
    notification.metadata['resourceType']?.toString(),
    notification.metadata['title']?.toString(),
  ].whereType<String>().join(' ').toLowerCase();
}

String? _firstMetadataString(Map<String, Object?> metadata, List<String> keys) {
  for (final String key in keys) {
    final Object? value = metadata[key];
    if (value is String && value.trim().isNotEmpty) {
      return value;
    }
  }
  return null;
}

class _NotificationsLeftPanel extends StatelessWidget {
  const _NotificationsLeftPanel({
    required this.items,
    required this.selected,
    required this.selectedKind,
    required this.onKindChanged,
    required this.onSelected,
    required this.isLoading,
    required this.errorMessage,
    required this.onRetry,
  });

  final List<GtexNotificationItem> items;
  final GtexNotificationItem? selected;
  final GtexNotificationKind? selectedKind;
  final ValueChanged<GtexNotificationKind?> onKindChanged;
  final ValueChanged<GtexNotificationItem> onSelected;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const GtexSearchField(hintText: 'Search notifications'),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            ChoiceChip(
              selected: selectedKind == null,
              label: const Text('All'),
              onSelected: (_) => onKindChanged(null),
            ),
            for (final GtexNotificationKind kind in GtexNotificationKind.values)
              ChoiceChip(
                selected: selectedKind == kind,
                label: Text(kind.name),
                onSelected: (_) => onKindChanged(kind),
              ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(child: _buildListBody()),
      ],
    );
  }

  Widget _buildListBody() {
    if (isLoading && items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (errorMessage != null && items.isEmpty) {
      return GtexEmptyState(
        title: 'Notifications unavailable',
        message: errorMessage!,
        icon: Icons.notifications_off_outlined,
        actionLabel: 'Retry',
        onAction: onRetry,
        accent: GtexColors.red,
      );
    }
    if (items.isEmpty) {
      return const GtexEmptyState(
        title: 'No notifications',
        message: 'Wallet, market, club, and admin alerts will appear here.',
        icon: Icons.notifications_none_outlined,
        accent: GtexColors.cyan,
      );
    }
    return ListView(
      children: <Widget>[
        for (final GtexNotificationItem item in items)
          GtexSectionListTile(
            title: item.title,
            subtitle: item.relatedLabel ?? item.body,
            icon: item.icon,
            accent: notificationColor(item.kind),
            isSelected: item.id == selected?.id,
            onTap: () => onSelected(item),
            trailing:
                item.isRead
                    ? null
                    : Container(
                      width: 9,
                      height: 9,
                      decoration: const BoxDecoration(
                        color: GtexColors.pitch,
                        shape: BoxShape.circle,
                      ),
                    ),
          ),
      ],
    );
  }
}

class _NotificationDetail extends StatelessWidget {
  const _NotificationDetail({required this.item});

  final GtexNotificationItem item;

  @override
  Widget build(BuildContext context) {
    final Color accent = notificationColor(item.kind);
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          accent: accent,
          title: item.title,
          subtitle: item.relatedLabel,
          trailing: GtexStatusChip(
            label: item.kindLabel,
            color: accent,
            icon: item.icon,
          ),
          child: Text(
            item.body,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.45,
            ),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Timeline',
          subtitle: 'Notification audit and next action.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _TimelineRow(
                label: 'Created',
                value: _formatTime(item.createdAt),
              ),
              _TimelineRow(
                label: 'Read state',
                value: item.isRead ? 'Read' : 'Unread',
              ),
              _TimelineRow(
                label: 'Linked area',
                value: item.relatedLabel ?? 'General GTEX',
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _NotificationActions extends StatelessWidget {
  const _NotificationActions({
    required this.item,
    required this.onOpen,
    required this.onMarkRead,
  });

  final GtexNotificationItem item;
  final VoidCallback? onOpen;
  final VoidCallback onMarkRead;

  @override
  Widget build(BuildContext context) {
    final Color accent = notificationColor(item.kind);
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Quick actions',
          subtitle:
              'Route into live GTEX wallet, KYC, dispute, and order flows.',
          accent: accent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label: item.actionLabel ?? 'Open linked item',
                icon: Icons.open_in_new_outlined,
                accent: accent,
                onPressed: onOpen,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Mark as read',
                icon: Icons.check_circle_outline,
                secondary: true,
                accent: accent,
                onPressed: onMarkRead,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Notification settings',
                icon: Icons.tune_outlined,
                secondary: true,
                accent: GtexColors.textSecondary,
                onPressed: () => context.go('/settings'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
            ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _NotificationsEmptyState extends StatelessWidget {
  const _NotificationsEmptyState({
    required this.isLoading,
    required this.errorMessage,
    required this.onRetry,
  });

  final bool isLoading;
  final String? errorMessage;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (errorMessage != null) {
      return GtexEmptyState(
        title: 'Notifications unavailable',
        message: errorMessage!,
        icon: Icons.notifications_off_outlined,
        actionLabel: 'Retry',
        onAction: onRetry,
        accent: GtexColors.red,
      );
    }
    return const GtexEmptyState(
      title: 'No notifications selected',
      message: 'Choose an alert from the left panel to inspect it.',
      icon: Icons.notifications_active_outlined,
      accent: GtexColors.cyan,
    );
  }
}

String _formatTime(DateTime value) {
  final Duration ago = DateTime.now().difference(value);
  if (ago.inMinutes < 60) return '${ago.inMinutes}m ago';
  if (ago.inHours < 24) return '${ago.inHours}h ago';
  return '${ago.inDays}d ago';
}

GtexNotificationItem _copyItem(GtexNotificationItem item, {bool? isRead}) {
  return GtexNotificationItem(
    id: item.id,
    title: item.title,
    body: item.body,
    kind: item.kind,
    createdAt: item.createdAt,
    isRead: isRead ?? item.isRead,
    relatedLabel: item.relatedLabel,
    actionLabel: item.actionLabel,
  );
}

GtexNotificationItem _mapLiveNotification(GteNotification notification) {
  final String signal =
      <String?>[
        notification.topic,
        notification.templateKey,
        notification.resourceId,
        notification.message,
      ].whereType<String>().join(' ').toLowerCase();
  final GtexNotificationKind kind = _kindForSignal(signal);
  final String body =
      notification.message?.trim().isNotEmpty == true
          ? notification.message!.trim()
          : 'GTEX operating update is ready for review.';
  return GtexNotificationItem(
    id: notification.notificationId,
    title: _titleForNotification(kind, notification),
    body: body,
    kind: kind,
    createdAt: notification.createdAt ?? DateTime.now(),
    isRead: notification.isRead,
    relatedLabel: _relatedLabelFor(notification),
    actionLabel: _actionLabelFor(kind),
  );
}

GtexNotificationKind _kindForSignal(String signal) {
  if (signal.contains('kyc') || signal.contains('verification')) {
    return GtexNotificationKind.kyc;
  }
  if (signal.contains('dispute') || signal.contains('evidence')) {
    return GtexNotificationKind.dispute;
  }
  if (signal.contains('jackpot') || signal.contains('winner')) {
    return GtexNotificationKind.jackpot;
  }
  if (signal.contains('regen') || signal.contains('newgen')) {
    return GtexNotificationKind.regen;
  }
  if (signal.contains('wallet') ||
      signal.contains('deposit') ||
      signal.contains('withdraw') ||
      signal.contains('payout') ||
      signal.contains('payment')) {
    return GtexNotificationKind.wallet;
  }
  if (signal.contains('competition') ||
      signal.contains('tournament') ||
      signal.contains('fixture') ||
      signal.contains('match')) {
    return GtexNotificationKind.competition;
  }
  if (signal.contains('club') ||
      signal.contains('share') ||
      signal.contains('follower')) {
    return GtexNotificationKind.club;
  }
  if (signal.contains('market') ||
      signal.contains('transfer') ||
      signal.contains('player') ||
      signal.contains('order') ||
      signal.contains('purchase')) {
    return GtexNotificationKind.market;
  }
  return GtexNotificationKind.system;
}

String _titleForNotification(
  GtexNotificationKind kind,
  GteNotification notification,
) {
  final String? explicitTitle = notification.metadata['title']?.toString();
  if (explicitTitle != null && explicitTitle.trim().isNotEmpty) {
    return explicitTitle.trim();
  }
  final String topic = notification.topic?.trim().replaceAll('_', ' ') ?? '';
  if (topic.isNotEmpty) {
    return topic
        .split(' ')
        .where((String part) => part.isNotEmpty)
        .map(_titleCasePart)
        .join(' ');
  }
  switch (kind) {
    case GtexNotificationKind.market:
      return 'Market update';
    case GtexNotificationKind.club:
      return 'Club update';
    case GtexNotificationKind.competition:
      return 'Competition update';
    case GtexNotificationKind.regen:
      return 'Regen world update';
    case GtexNotificationKind.wallet:
      return 'Wallet update';
    case GtexNotificationKind.kyc:
      return 'KYC update';
    case GtexNotificationKind.dispute:
      return 'Dispute update';
    case GtexNotificationKind.jackpot:
      return 'Jackpot update';
    case GtexNotificationKind.system:
      return 'GTEX update';
  }
}

String _titleCasePart(String part) {
  if (part.isEmpty) {
    return part;
  }
  return '${part.substring(0, 1).toUpperCase()}${part.substring(1)}';
}

String? _relatedLabelFor(GteNotification notification) {
  if (notification.competitionId?.trim().isNotEmpty == true) {
    return 'Competition ${notification.competitionId}';
  }
  if (notification.fixtureId?.trim().isNotEmpty == true) {
    return 'Fixture ${notification.fixtureId}';
  }
  if (notification.resourceId?.trim().isNotEmpty == true) {
    return notification.resourceId;
  }
  return null;
}

String _actionLabelFor(GtexNotificationKind kind) {
  switch (kind) {
    case GtexNotificationKind.kyc:
      return 'Open KYC';
    case GtexNotificationKind.dispute:
      return 'Open dispute';
    case GtexNotificationKind.wallet:
      return 'Open wallet';
    case GtexNotificationKind.market:
      return 'Open market context';
    case GtexNotificationKind.club:
      return 'Open club context';
    case GtexNotificationKind.competition:
      return 'Open competition context';
    case GtexNotificationKind.regen:
      return 'Open regen context';
    case GtexNotificationKind.jackpot:
      return 'Open jackpot context';
    case GtexNotificationKind.system:
      return 'Open GTEX context';
  }
}

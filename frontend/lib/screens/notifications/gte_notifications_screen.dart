import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../support/gte_support_dispute_screens.dart';
import '../wallet/gte_deposit_history_screen.dart';
import '../wallet/gte_kyc_screen.dart';
import '../wallet/gte_wallet_overview_screen.dart';
import '../wallet/gte_withdrawal_flow_screen.dart';

class GteNotificationsScreen extends StatefulWidget {
  const GteNotificationsScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteNotificationsScreen> createState() => _GteNotificationsScreenState();
}

class _GteNotificationsScreenState extends State<GteNotificationsScreen> {
  late Future<List<GteNotification>> _notificationsFuture;

  @override
  void initState() {
    super.initState();
    _notificationsFuture = widget.controller.api.listNotifications();
  }

  Future<void> _refresh() async {
    setState(() {
      _notificationsFuture = widget.controller.api.listNotifications();
    });
  }

  Future<void> _markAllRead() async {
    await widget.controller.api.markAllNotificationsRead();
    await _refresh();
  }

  Future<void> _openNotification(GteNotification notification) async {
    if (!notification.isRead) {
      await widget.controller.api
          .markNotificationRead(notification.notificationId);
    }
    if (!mounted) {
      return;
    }
    final String topic = (notification.topic ?? '').toLowerCase();
    final String resource = (notification.resourceId ?? '').toLowerCase();
    if (topic.contains('deposit') || resource.startsWith('deposit')) {
      Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) =>
              GteDepositHistoryScreen(controller: widget.controller),
        ),
      );
      return;
    }
    if (topic.contains('withdrawal') || topic.contains('payout')) {
      Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) =>
              GteWithdrawalEligibilityScreen(controller: widget.controller),
        ),
      );
      return;
    }
    if (topic.contains('kyc')) {
      Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) =>
              GteKycScreen(controller: widget.controller),
        ),
      );
      return;
    }
    if (topic.contains('dispute')) {
      if (notification.resourceId != null) {
        Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (BuildContext context) => GteDisputeThreadScreen(
              api: widget.controller.api,
              disputeId: notification.resourceId!,
            ),
          ),
        );
        return;
      }
      Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) =>
              GteDisputeHubScreen(controller: widget.controller),
        ),
      );
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            GteWalletOverviewScreen(controller: widget.controller),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
          TextButton(
            onPressed: _markAllRead,
            child: const Text('Mark all read'),
          ),
        ],
      ),
      body: FutureBuilder<List<GteNotification>>(
        future: _notificationsFuture,
        builder: (BuildContext context,
            AsyncSnapshot<List<GteNotification>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final List<GteNotification> notifications =
              snapshot.data ?? <GteNotification>[];
          if (notifications.isEmpty) {
            return const Center(
              child: GteStatePanel(
                title: 'No notifications yet',
                message: 'Wallet events and admin updates will appear here.',
                icon: Icons.notifications_none_outlined,
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: notifications.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                final GteNotification notification = notifications[index];
                final Color accent = notification.isRead
                    ? GteShellTheme.stroke
                    : GteShellTheme.accentCapital;
                return GteSurfacePanel(
                  emphasized: !notification.isRead,
                  accentColor: accent,
                  onTap: () => _openNotification(notification),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        notification.message ?? 'New notification',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        gteFormatDateTime(notification.createdAt),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        notification.isRead ? 'Read' : 'Unread',
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: accent),
                      ),
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

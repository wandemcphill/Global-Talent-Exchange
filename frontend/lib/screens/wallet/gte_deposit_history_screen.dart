import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../support/gte_support_dispute_screens.dart';
import 'gte_funding_flow_screen.dart';

class GteDepositHistoryScreen extends StatefulWidget {
  const GteDepositHistoryScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteDepositHistoryScreen> createState() =>
      _GteDepositHistoryScreenState();
}

class _GteDepositHistoryScreenState extends State<GteDepositHistoryScreen> {
  late Future<List<GteDepositRequest>> _depositsFuture;

  @override
  void initState() {
    super.initState();
    _depositsFuture = widget.controller.api.listDepositRequests();
  }

  Future<void> _refresh() async {
    setState(() {
      _depositsFuture = widget.controller.api.listDepositRequests();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Deposit history'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<List<GteDepositRequest>>(
        future: _depositsFuture,
        builder: (BuildContext context,
            AsyncSnapshot<List<GteDepositRequest>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final List<GteDepositRequest> deposits = snapshot.data ?? <GteDepositRequest>[];
          if (deposits.isEmpty) {
            return const Center(
              child: GteStatePanel(
                title: 'No deposits yet',
                message: 'Create a funding request to start crediting your wallet.',
                icon: Icons.account_balance_wallet_outlined,
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: deposits.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                final GteDepositRequest deposit = deposits[index];
                return GteSurfacePanel(
                  accentColor: GteShellTheme.accentCapital,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(deposit.reference,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 6),
                      Text(
                        'Status: ${gteFormatOrderStatus(_depositStatusLabel(deposit.status))}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)} • ${gteFormatCredits(deposit.amountCoin)}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Created ${gteFormatDateTime(deposit.createdAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        children: <Widget>[
                          OutlinedButton(
                            onPressed: () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GteDepositInstructionsScreen(
                                    controller: widget.controller,
                                    deposit: deposit,
                                  ),
                                ),
                              );
                            },
                            child: const Text('View instructions'),
                          ),
                          OutlinedButton(
                            onPressed: () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GteDisputeCreateScreen(
                                    controller: widget.controller,
                                    reference: deposit.reference,
                                    resourceId: deposit.id,
                                    resourceType: 'deposit',
                                  ),
                                ),
                              );
                            },
                            child: const Text('Open dispute'),
                          ),
                        ],
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

String _depositStatusLabel(GteDepositStatus status) {
  switch (status) {
    case GteDepositStatus.awaitingPayment:
      return 'awaiting_payment';
    case GteDepositStatus.paymentSubmitted:
      return 'payment_submitted';
    case GteDepositStatus.underReview:
      return 'under_review';
    case GteDepositStatus.confirmed:
      return 'confirmed';
    case GteDepositStatus.rejected:
      return 'rejected';
    case GteDepositStatus.expired:
      return 'expired';
    case GteDepositStatus.disputed:
      return 'disputed';
  }
}
